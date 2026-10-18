"""Project, dataset-version, and local object storage services for Studio."""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.autodq_web.persistence import (
    DEFAULT_STUDIO_HOME,
    DatasetSummary,
    DatasetSnapshotMetadata,
    DatasetVersionSummary,
    ProjectSummary,
    StudioRepository,
    database_url,
    repository_for_url,
)


def object_store_root(
    environ: Mapping[str, str] | None = None,
    *,
    default_home: Path | None = None,
) -> Path:
    values = os.environ if environ is None else environ
    configured = values.get("AUTODQ_OBJECT_STORE_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    home_value = values.get("AUTODQ_STUDIO_HOME", "").strip()
    home = Path(home_value).expanduser() if home_value else default_home
    return (home or DEFAULT_STUDIO_HOME).resolve() / "objects"


class LocalObjectStore:
    """A traversal-safe object store backed by a persistent local directory."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Object storage key escapes the configured root.")
        return path

    def put(self, key: str, payload: bytes) -> Path:
        destination = self.path_for(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
            stream.write(payload)
            temporary = Path(stream.name)
        temporary.replace(destination)
        return destination

    def read(self, key: str) -> bytes:
        return self.path_for(key).read_bytes()


def dataframe_checksum(frame: pd.DataFrame) -> str:
    """Create a stable checksum that includes values, columns, and dtypes."""

    digest = hashlib.sha256()
    digest.update(pd.util.hash_pandas_object(frame, index=True).values.tobytes())
    digest.update("\x1f".join(map(str, frame.columns)).encode("utf-8"))
    digest.update("\x1f".join(map(str, frame.dtypes)).encode("utf-8"))
    return digest.hexdigest()


def frame_to_parquet_bytes(frame: pd.DataFrame) -> bytes:
    stream = io.BytesIO()
    frame.to_parquet(stream, index=False, engine="pyarrow")
    return stream.getvalue()


@dataclass(frozen=True)
class SavedDataset:
    project: ProjectSummary
    dataset_id: str
    dataset_name: str
    stage_checksums: dict[str, str]


@dataclass(frozen=True)
class RestoredProject:
    project: ProjectSummary
    dataset_id: str | None = None
    dataset_name: str | None = None
    original_filename: str | None = None
    target_column: str | None = None
    raw_path: Path | None = None
    current_data: pd.DataFrame | None = None
    cleaned_data: pd.DataFrame | None = None
    engineered_data: pd.DataFrame | None = None
    stage_checksums: dict[str, str] | None = None


class StudioProjectService:
    def __init__(self, repository: StudioRepository, object_store: LocalObjectStore) -> None:
        self.repository = repository
        self.object_store = object_store

    def list_projects(self, *, user_id: str, workspace_id: str) -> tuple[ProjectSummary, ...]:
        return self.repository.list_projects(user_id=user_id, workspace_id=workspace_id)

    def create_project(
        self,
        *,
        user_id: str,
        workspace_id: str,
        name: str,
        description: str | None = None,
    ) -> ProjectSummary:
        return self.repository.create_project(
            user_id=user_id,
            workspace_id=workspace_id,
            name=name,
            description=description,
        )

    def list_datasets(
        self,
        *,
        user_id: str,
        project_id: str,
    ) -> tuple[DatasetSummary, ...]:
        return self.repository.list_datasets(
            user_id=user_id,
            project_id=project_id,
        )

    def save_upload(
        self,
        *,
        user_id: str,
        workspace_id: str,
        project_id: str | None,
        project_name: str,
        dataset_name: str,
        original_filename: str,
        payload: bytes,
        frame: pd.DataFrame,
        target_column: str | None = None,
    ) -> SavedDataset:
        if project_id is None:
            project = self.create_project(
                user_id=user_id,
                workspace_id=workspace_id,
                name=project_name,
            )
        else:
            snapshot = self.repository.project_snapshot_metadata(
                user_id=user_id,
                project_id=project_id,
            )
            project = (
                snapshot.project
                if isinstance(snapshot, DatasetSnapshotMetadata)
                else snapshot
            )
            if project.workspace_id != workspace_id:
                raise PermissionError("The project does not belong to this workspace.")
        dataset = self.repository.create_dataset(
            user_id=user_id,
            project_id=project.id,
            name=dataset_name,
            original_filename=original_filename,
            target_column=target_column,
        )
        suffix = Path(original_filename).suffix.lower()
        checksum = hashlib.sha256(payload).hexdigest()
        storage_key = (
            f"workspaces/{workspace_id}/projects/{project.id}/datasets/"
            f"{dataset.id}/raw/{checksum}{suffix}"
        )
        self.object_store.put(storage_key, payload)
        self.repository.create_dataset_version(
            user_id=user_id,
            dataset_id=dataset.id,
            stage="raw",
            storage_key=storage_key,
            file_format=suffix.lstrip("."),
            checksum=checksum,
            row_count=len(frame),
            column_count=len(frame.columns),
        )
        refreshed = self.repository.project_snapshot_metadata(
            user_id=user_id,
            project_id=project.id,
        )
        assert isinstance(refreshed, DatasetSnapshotMetadata)
        return SavedDataset(
            project=refreshed.project,
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            stage_checksums={"raw": checksum},
        )

    def save_stage(
        self,
        *,
        user_id: str,
        workspace_id: str,
        project_id: str,
        dataset_id: str,
        stage: str,
        frame: pd.DataFrame,
        target_column: str | None,
    ) -> DatasetVersionSummary:
        if stage not in {"current", "cleaned", "engineered"}:
            raise ValueError(f"Unsupported persisted stage: {stage}")
        snapshot = self.repository.project_snapshot_metadata(
            user_id=user_id,
            project_id=project_id,
            dataset_id=dataset_id,
        )
        if not isinstance(snapshot, DatasetSnapshotMetadata):
            raise LookupError("Dataset not found in this project.")
        if snapshot.project.workspace_id != workspace_id:
            raise PermissionError("The project does not belong to this workspace.")
        if snapshot.dataset_id != dataset_id:
            raise LookupError("Dataset not found in this project.")
        checksum = dataframe_checksum(frame)
        previous = self.repository.latest_dataset_version(
            user_id=user_id,
            dataset_id=dataset_id,
            stage=stage,
        )
        self.repository.update_dataset_target(
            user_id=user_id,
            dataset_id=dataset_id,
            target_column=target_column,
        )
        if previous is not None and previous.checksum == checksum:
            return previous

        storage_key = (
            f"workspaces/{workspace_id}/projects/{project_id}/datasets/"
            f"{dataset_id}/{stage}/{checksum}.parquet"
        )
        self.object_store.put(storage_key, frame_to_parquet_bytes(frame))
        return self.repository.create_dataset_version(
            user_id=user_id,
            dataset_id=dataset_id,
            stage=stage,
            storage_key=storage_key,
            file_format="parquet",
            checksum=checksum,
            row_count=len(frame),
            column_count=len(frame.columns),
        )

    def update_target(
        self,
        *,
        user_id: str,
        dataset_id: str,
        target_column: str | None,
    ) -> None:
        self.repository.update_dataset_target(
            user_id=user_id,
            dataset_id=dataset_id,
            target_column=target_column,
        )

    def restore_project(
        self,
        *,
        user_id: str,
        project_id: str,
        dataset_id: str | None = None,
    ) -> RestoredProject:
        metadata = self.repository.project_snapshot_metadata(
            user_id=user_id,
            project_id=project_id,
            dataset_id=dataset_id,
        )
        if isinstance(metadata, ProjectSummary):
            return RestoredProject(project=metadata)

        versions = metadata.versions
        raw = versions.get("raw")
        if raw is None:
            raise RuntimeError("The saved dataset does not have a raw version.")

        if dataset_id is not None:
            self.repository.activate_dataset(
                user_id=user_id,
                project_id=project_id,
                dataset_id=metadata.dataset_id,
            )

        def read_stage(stage: str) -> pd.DataFrame | None:
            version = versions.get(stage)
            if version is None:
                return None
            return pd.read_parquet(self.object_store.path_for(version.storage_key))

        return RestoredProject(
            project=metadata.project,
            dataset_id=metadata.dataset_id,
            dataset_name=metadata.dataset_name,
            original_filename=metadata.original_filename,
            target_column=metadata.target_column,
            raw_path=self.object_store.path_for(raw.storage_key),
            current_data=read_stage("current"),
            cleaned_data=read_stage("cleaned"),
            engineered_data=read_stage("engineered"),
            stage_checksums={stage: version.checksum for stage, version in versions.items()},
        )


@lru_cache(maxsize=8)
def project_service_for(database: str, storage_root: str) -> StudioProjectService:
    return StudioProjectService(
        repository_for_url(database),
        LocalObjectStore(Path(storage_root)),
    )


def project_service() -> StudioProjectService:
    return project_service_for(database_url(), str(object_store_root()))
