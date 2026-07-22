from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


@dataclass(slots=True)
class ModelManifest:
    """Portable metadata stored beside a serialized AutoDQ model."""

    CURRENT_FORMAT_VERSION: ClassVar[int] = 1

    format_version: int
    autodq_version: str
    created_at: str
    algorithm: str
    problem_type: str
    target: str
    feature_columns: list[str]
    feature_dtypes: dict[str, str]
    metrics: dict[str, Any]
    runtime: dict[str, Any]
    model_file: str
    model_sha256: str
    model_report: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": self.format_version,
            "autodq_version": self.autodq_version,
            "created_at": self.created_at,
            "algorithm": self.algorithm,
            "problem_type": self.problem_type,
            "target": self.target,
            "feature_columns": self.feature_columns,
            "feature_dtypes": self.feature_dtypes,
            "metrics": self.metrics,
            "runtime": self.runtime,
            "model_file": self.model_file,
            "model_sha256": self.model_sha256,
            "model_report": self.model_report,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelManifest":
        required = (
            "format_version",
            "autodq_version",
            "created_at",
            "algorithm",
            "problem_type",
            "target",
            "feature_columns",
            "feature_dtypes",
            "metrics",
            "runtime",
            "model_file",
            "model_sha256",
        )
        missing = [key for key in required if key not in data]

        if missing:
            raise ValueError(
                "Invalid model manifest. Missing fields: "
                f"{', '.join(missing)}"
            )

        return cls(
            format_version=int(data["format_version"]),
            autodq_version=str(data["autodq_version"]),
            created_at=str(data["created_at"]),
            algorithm=str(data["algorithm"]),
            problem_type=str(data["problem_type"]),
            target=str(data["target"]),
            feature_columns=list(data["feature_columns"]),
            feature_dtypes={
                str(key): str(value)
                for key, value in data["feature_dtypes"].items()
            },
            metrics=dict(data["metrics"]),
            runtime=dict(data["runtime"]),
            model_file=str(data["model_file"]),
            model_sha256=str(data["model_sha256"]),
            model_report=dict(data.get("model_report", {})),
        )


@dataclass(slots=True)
class ModelBundle:
    """A loaded or newly saved model bundle."""

    path: Path
    manifest: ModelManifest
    model_report: Any

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "manifest": self.manifest.to_dict(),
        }
