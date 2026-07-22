from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


@dataclass(slots=True)
class WorkspaceDataset:
    name: str
    file: str
    source_path: str | None
    is_primary: bool
    rows: int
    columns: int
    dtypes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "file": self.file,
            "source_path": self.source_path,
            "is_primary": self.is_primary,
            "rows": self.rows,
            "columns": self.columns,
            "dtypes": self.dtypes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceDataset":
        if not isinstance(data, dict):
            raise ValueError("Workspace dataset entry must be a dictionary.")

        dtypes = data.get("dtypes", {})

        if not isinstance(dtypes, dict):
            raise ValueError("Workspace dataset dtypes must be a dictionary.")

        try:
            dataset = cls(
                name=str(data["name"]),
                file=str(data["file"]),
                source_path=(
                    str(data["source_path"])
                    if data.get("source_path") is not None
                    else None
                ),
                is_primary=bool(data.get("is_primary", False)),
                rows=int(data.get("rows", 0)),
                columns=int(data.get("columns", 0)),
                dtypes={
                    str(key): str(value)
                    for key, value in dtypes.items()
                },
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Invalid workspace dataset entry.") from error

        if not dataset.name or not dataset.file:
            raise ValueError(
                "Workspace dataset name and file cannot be empty."
            )

        if dataset.rows < 0 or dataset.columns < 0:
            raise ValueError(
                "Workspace dataset dimensions cannot be negative."
            )

        return dataset


@dataclass(slots=True)
class WorkspaceManifest:
    CURRENT_FORMAT_VERSION: ClassVar[int] = 1

    format_version: int
    workspace_id: str
    name: str
    created_at: str
    updated_at: str
    target: str | None
    active_dataset: str
    datasets: list[WorkspaceDataset] = field(default_factory=list)
    active_model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": self.format_version,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "target": self.target,
            "active_dataset": self.active_dataset,
            "active_model": self.active_model,
            "datasets": [item.to_dict() for item in self.datasets],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceManifest":
        if not isinstance(data, dict):
            raise ValueError("Workspace manifest must be a dictionary.")

        required = (
            "format_version",
            "workspace_id",
            "name",
            "created_at",
            "updated_at",
            "active_dataset",
            "datasets",
        )
        missing = [key for key in required if key not in data]

        if missing:
            raise ValueError(
                "Invalid workspace manifest. Missing fields: "
                f"{', '.join(missing)}"
            )

        datasets = data["datasets"]
        metadata = data.get("metadata", {})

        if not isinstance(datasets, list):
            raise ValueError("Workspace manifest datasets must be a list.")

        if not isinstance(metadata, dict):
            raise ValueError(
                "Workspace manifest metadata must be a dictionary."
            )

        try:
            manifest = cls(
                format_version=int(data["format_version"]),
                workspace_id=str(data["workspace_id"]),
                name=str(data["name"]),
                created_at=str(data["created_at"]),
                updated_at=str(data["updated_at"]),
                target=(
                    str(data["target"])
                    if data.get("target") is not None
                    else None
                ),
                active_dataset=str(data["active_dataset"]),
                active_model=(
                    str(data["active_model"])
                    if data.get("active_model") is not None
                    else None
                ),
                datasets=[
                    WorkspaceDataset.from_dict(item)
                    for item in datasets
                ],
                metadata=dict(metadata),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("Invalid workspace manifest data.") from error

        if manifest.format_version != cls.CURRENT_FORMAT_VERSION:
            raise ValueError(
                "Unsupported workspace format version: "
                f"{manifest.format_version}. Supported version: "
                f"{cls.CURRENT_FORMAT_VERSION}."
            )

        if not manifest.datasets:
            raise ValueError(
                "Invalid workspace manifest: datasets is empty."
            )

        dataset_names = [item.name for item in manifest.datasets]

        if len(dataset_names) != len(set(dataset_names)):
            raise ValueError(
                "Invalid workspace manifest: dataset names must be unique."
            )

        dataset_files = [item.file for item in manifest.datasets]

        if len(dataset_files) != len(set(dataset_files)):
            raise ValueError(
                "Invalid workspace manifest: dataset files must be unique."
            )

        if manifest.active_dataset not in set(dataset_names):
            raise ValueError(
                "Invalid workspace manifest: active_dataset is not "
                "registered."
            )

        primary_datasets = [
            item.name for item in manifest.datasets if item.is_primary
        ]

        if primary_datasets != [manifest.active_dataset]:
            raise ValueError(
                "Invalid workspace manifest: exactly one primary dataset "
                "must match active_dataset."
            )

        return manifest


@dataclass(slots=True)
class WorkspaceContext:
    path: Path
    manifest: WorkspaceManifest

    @property
    def datasets_dir(self) -> Path:
        return self.path / "datasets"

    @property
    def models_dir(self) -> Path:
        return self.path / "models"

    @property
    def reports_dir(self) -> Path:
        return self.path / "reports"

    @property
    def visualizations_dir(self) -> Path:
        return self.path / "visualizations"

    @property
    def exports_dir(self) -> Path:
        return self.path / "exports"

    @property
    def logs_dir(self) -> Path:
        return self.path / "logs"

    @property
    def session_path(self) -> Path:
        return self.path / "session.json"

    @property
    def manifest_path(self) -> Path:
        return self.path / "workspace.json"


@dataclass(slots=True)
class WorkspaceSummary:
    workspace_id: str
    name: str
    path: Path
    updated_at: str
    target: str | None
    active_dataset: str
    dataset_count: int
    has_model: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "path": str(self.path),
            "updated_at": self.updated_at,
            "target": self.target,
            "active_dataset": self.active_dataset,
            "dataset_count": self.dataset_count,
            "has_model": self.has_model,
        }
