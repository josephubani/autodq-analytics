from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from autodq.io.loaders import load_dataset
from autodq.workspaces.models import (
    WorkspaceContext,
    WorkspaceDataset,
    WorkspaceManifest,
    WorkspaceSummary,
)


class WorkspaceManager:
    """Creates and persists isolated AutoDQ workspaces."""

    MANIFEST_FILENAME = "workspace.json"
    SESSION_FILENAME = "session.json"
    REQUIRED_DIRECTORIES = (
        "datasets",
        "models",
        "reports",
        "visualizations",
        "exports",
        "logs",
    )

    def __init__(
        self,
        root: str | Path = ".autodq/workspaces",
    ):
        self.root = Path(root).expanduser().resolve()

    def create(
        self,
        name: str,
        dataset_path: str | Path,
        target: str | None = None,
    ) -> WorkspaceContext:
        workspace_id = self.normalize_id(name)
        workspace_path = self.root / workspace_id

        if workspace_path.exists():
            raise FileExistsError(
                f"Workspace already exists: {workspace_id}"
            )

        source_path = Path(dataset_path).expanduser().resolve()

        if not source_path.is_file():
            raise FileNotFoundError(
                f"Workspace dataset was not found: {source_path}"
            )

        self.root.mkdir(parents=True, exist_ok=True)
        temporary_path = self.root / (
            f".{workspace_id}.tmp-{uuid4().hex}"
        )
        temporary_path.mkdir()

        try:
            for directory in self.REQUIRED_DIRECTORIES:
                (temporary_path / directory).mkdir()

            dataset_suffix = source_path.suffix.lower()

            if dataset_suffix not in {".csv", ".xlsx", ".xls"}:
                raise ValueError(
                    "Workspace datasets must be CSV or Excel files."
                )

            dataset_file = f"datasets/main{dataset_suffix}"
            stored_dataset = temporary_path / dataset_file
            shutil.copy2(source_path, stored_dataset)

            data = load_dataset(stored_dataset)
            now = self._timestamp()
            manifest = WorkspaceManifest(
                format_version=(
                    WorkspaceManifest.CURRENT_FORMAT_VERSION
                ),
                workspace_id=workspace_id,
                name=name.strip(),
                created_at=now,
                updated_at=now,
                target=target,
                active_dataset="main",
                datasets=[
                    WorkspaceDataset(
                        name="main",
                        file=dataset_file,
                        source_path=str(source_path),
                        is_primary=True,
                        rows=len(data),
                        columns=len(data.columns),
                        dtypes={
                            column: str(data[column].dtype)
                            for column in data.columns
                        },
                    )
                ],
            )
            self._write_json(
                temporary_path / self.MANIFEST_FILENAME,
                manifest.to_dict(),
            )
            os.replace(temporary_path, workspace_path)

        except Exception:
            shutil.rmtree(temporary_path, ignore_errors=True)
            raise

        return WorkspaceContext(
            path=workspace_path,
            manifest=manifest,
        )

    def open(self, name_or_path: str | Path) -> WorkspaceContext:
        candidate = Path(name_or_path).expanduser()

        if candidate.is_dir():
            workspace_path = candidate.resolve()
        else:
            workspace_path = (
                self.root / self.normalize_id(str(name_or_path))
            )

        manifest_path = workspace_path / self.MANIFEST_FILENAME

        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"Workspace manifest was not found: {manifest_path}"
            )

        manifest = WorkspaceManifest.from_dict(
            self._read_json(manifest_path)
        )
        context = WorkspaceContext(
            path=workspace_path,
            manifest=manifest,
        )
        self.validate_files(context)
        return context

    def list(self) -> list[WorkspaceSummary]:
        if not self.root.is_dir():
            return []

        summaries = []

        for path in sorted(self.root.iterdir()):
            if not path.is_dir() or path.name.startswith("."):
                continue

            try:
                context = self.open(path)
            except (FileNotFoundError, ValueError):
                continue

            manifest = context.manifest
            summaries.append(
                WorkspaceSummary(
                    workspace_id=manifest.workspace_id,
                    name=manifest.name,
                    path=context.path,
                    updated_at=manifest.updated_at,
                    target=manifest.target,
                    active_dataset=manifest.active_dataset,
                    dataset_count=len(manifest.datasets),
                    has_model=manifest.active_model is not None,
                )
            )

        return summaries

    def save(
        self,
        context: WorkspaceContext,
        dataset_entries,
        target: str | None,
        session: dict[str, Any],
        active_model: Path | None = None,
    ) -> WorkspaceContext:
        self._ensure_context_directories(context)
        previous_datasets = {
            item.name: item
            for item in context.manifest.datasets
        }
        used_files = set()
        stored_datasets = []

        for entry in dataset_entries:
            previous_dataset = previous_datasets.get(entry.name)
            relative_file = (
                previous_dataset.file
                if previous_dataset is not None
                else None
            )

            if (
                relative_file is not None
                and Path(relative_file).suffix.lower() != ".csv"
            ):
                relative_file = None

            if relative_file is None:
                relative_file = self._dataset_file(
                    entry.name,
                    used_files,
                )

            used_files.add(relative_file)
            output_path = self._safe_resolve(
                context.path,
                relative_file,
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = output_path.with_name(
                f".{output_path.name}.tmp-{uuid4().hex}"
            )
            entry.data.to_csv(temporary_path, index=False)
            os.replace(temporary_path, output_path)
            stored_datasets.append(
                WorkspaceDataset(
                    name=entry.name,
                    file=relative_file,
                    source_path=(
                        previous_dataset.source_path
                        if previous_dataset is not None
                        else entry.path
                    ),
                    is_primary=entry.is_primary,
                    rows=entry.rows,
                    columns=entry.columns,
                    dtypes={
                        column: str(entry.data[column].dtype)
                        for column in entry.data.columns
                    },
                )
            )

        primary = next(
            (item for item in stored_datasets if item.is_primary),
            None,
        )

        if primary is None:
            raise ValueError(
                "Workspace cannot be saved without a primary dataset."
            )

        active_model_relative = None

        if active_model is not None:
            active_model_path = active_model.resolve()
            models_root = context.models_dir.resolve()

            if not active_model_path.is_relative_to(models_root):
                raise ValueError(
                    "The active model bundle must be stored inside the "
                    "workspace models directory."
                )

            if not active_model_path.is_dir():
                raise FileNotFoundError(
                    "The active workspace model bundle was not found: "
                    f"{active_model_path}"
                )

            active_model_relative = str(
                active_model_path.relative_to(context.path.resolve())
            )

        manifest = context.manifest
        manifest.updated_at = self._timestamp()
        manifest.target = target
        manifest.active_dataset = primary.name
        manifest.datasets = stored_datasets
        manifest.active_model = active_model_relative
        self._write_json(context.session_path, session)
        self._write_json(
            context.manifest_path,
            manifest.to_dict(),
        )
        context.manifest = manifest
        return context

    def dataset_path(
        self,
        context: WorkspaceContext,
        dataset: WorkspaceDataset,
    ) -> Path:
        path = self._safe_resolve(context.path, dataset.file)

        if not path.is_relative_to(context.datasets_dir.resolve()):
            raise ValueError(
                "Workspace manifest contains an unsafe dataset path."
            )

        return path

    def load_dataset(
        self,
        context: WorkspaceContext,
        dataset: WorkspaceDataset,
    ) -> pd.DataFrame:
        """Load a workspace dataset and restore its persisted dtypes."""
        data = load_dataset(self.dataset_path(context, dataset))

        for column, dtype in dataset.dtypes.items():
            if column not in data.columns or dtype == "object":
                continue

            try:
                if dtype.startswith("datetime"):
                    data[column] = pd.to_datetime(data[column])
                elif dtype.startswith("timedelta"):
                    data[column] = pd.to_timedelta(data[column])
                else:
                    data[column] = data[column].astype(dtype)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Could not restore dtype '{dtype}' for workspace "
                    f"column '{column}'."
                ) from error

        return data

    def model_destination(
        self,
        context: WorkspaceContext,
        name: str,
    ) -> Path:
        """Return a safe model bundle path within a workspace."""
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError(
                "Workspace model_name must be a single directory name."
            )

        return self._safe_resolve(context.models_dir, name)

    def model_path(self, context: WorkspaceContext) -> Path | None:
        if context.manifest.active_model is None:
            return None

        path = self._safe_resolve(
            context.path,
            context.manifest.active_model,
        )

        if not path.is_relative_to(context.models_dir.resolve()):
            raise ValueError(
                "Workspace manifest contains an unsafe model path."
            )

        return path

    def load_session(
        self,
        context: WorkspaceContext,
    ) -> dict[str, Any] | None:
        if not context.session_path.is_file():
            return None

        return self._read_json(context.session_path)

    def validate_files(self, context: WorkspaceContext) -> None:
        for dataset in context.manifest.datasets:
            path = self.dataset_path(context, dataset)

            if not path.is_file():
                raise FileNotFoundError(
                    f"Workspace dataset was not found: {path}"
                )

        model_path = self.model_path(context)

        if model_path is not None and not model_path.is_dir():
            raise FileNotFoundError(
                f"Workspace model bundle was not found: {model_path}"
            )

    @staticmethod
    def normalize_id(name: str) -> str:
        if not name or not str(name).strip():
            raise ValueError("Workspace name cannot be empty.")

        normalized = re.sub(
            r"[^a-z0-9]+",
            "-",
            str(name).strip().lower(),
        ).strip("-")

        if not normalized:
            raise ValueError(
                "Workspace name must contain letters or numbers."
            )

        return normalized[:80]

    def _ensure_context_directories(
        self,
        context: WorkspaceContext,
    ) -> None:
        context.path.mkdir(parents=True, exist_ok=True)

        for directory in self.REQUIRED_DIRECTORIES:
            (context.path / directory).mkdir(exist_ok=True)

    @staticmethod
    def _dataset_file(name: str, used_files: set[str]) -> str:
        base = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            name.strip(),
        ).strip("_") or "dataset"
        candidate = f"datasets/{base}.csv"
        counter = 2

        while candidate in used_files:
            candidate = f"datasets/{base}_{counter}.csv"
            counter += 1

        return candidate

    @staticmethod
    def _safe_resolve(root: Path, relative_path: str) -> Path:
        path = (root / relative_path).resolve()

        if not path.is_relative_to(root.resolve()):
            raise ValueError(
                "Workspace manifest contains an unsafe path."
            )

        return path

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _write_json(
        self,
        path: Path,
        data: dict[str, Any],
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(
            f".{path.name}.tmp-{uuid4().hex}"
        )

        try:
            with temporary_path.open("w", encoding="utf-8") as stream:
                json.dump(
                    data,
                    stream,
                    indent=2,
                    sort_keys=True,
                    default=self._json_default,
                )
                stream.write("\n")

            os.replace(temporary_path, path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as stream:
                return json.load(stream)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Workspace JSON is invalid: {path}"
            ) from error

    @staticmethod
    def _json_default(value):
        if isinstance(value, np.generic):
            return value.item()

        if isinstance(value, (datetime, Path)):
            return str(value)

        raise TypeError(
            f"Object of type {type(value).__name__} is not JSON serializable"
        )
