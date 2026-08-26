from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from autodq.commands.models import serializable_value


PIPELINE_SCHEMA_VERSION = "1.0"
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PipelineExitCode(IntEnum):
    """Stable process exit codes for schedulers and pipeline orchestrators."""

    SUCCESS = 0
    WORKFLOW_FAILED = 1
    CONFIGURATION_ERROR = 2
    INTERNAL_ERROR = 3


@dataclass(slots=True)
class PipelineRunSpec:
    """Serializable instructions for one headless ADQL workflow run."""

    workflow: str
    dataset: str | None = None
    target: str | None = None
    cell: int | None = None
    through_cell: int | None = None
    continue_on_error: bool = False
    working_directory: str | None = None
    result_path: str | None = None
    overwrite_result: bool = False
    run_id: str = field(default_factory=lambda: uuid4().hex)
    metadata: dict[str, Any] = field(default_factory=dict)
    max_log_characters: int = 100_000

    def __post_init__(self) -> None:
        self.workflow = self._required_text(self.workflow, "workflow")
        self.run_id = self._required_text(self.run_id, "run_id")

        if not _RUN_ID_PATTERN.fullmatch(self.run_id):
            raise ValueError(
                "run_id must begin with a letter or number and contain only "
                "letters, numbers, periods, underscores, or hyphens (maximum "
                "128 characters)."
            )

        if self.dataset is not None:
            self.dataset = self._required_text(self.dataset, "dataset")

        if self.target is not None:
            self.target = self._required_text(self.target, "target")

        if self.working_directory is not None:
            self.working_directory = self._required_text(
                self.working_directory,
                "working_directory",
            )

        if self.result_path is not None:
            self.result_path = self._required_text(
                self.result_path,
                "result_path",
            )

        for label, value in (
            ("cell", self.cell),
            ("through_cell", self.through_cell),
        ):
            if value is not None and (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 1
            ):
                raise ValueError(f"{label} must be a positive integer.")

        if self.cell is not None and self.through_cell is not None:
            raise ValueError("Use either cell or through_cell, not both.")

        if not isinstance(self.continue_on_error, bool):
            raise TypeError("continue_on_error must be a boolean.")

        if not isinstance(self.overwrite_result, bool):
            raise TypeError("overwrite_result must be a boolean.")

        if (
            not isinstance(self.max_log_characters, int)
            or isinstance(self.max_log_characters, bool)
            or not 1_000 <= self.max_log_characters <= 1_000_000
        ):
            raise ValueError(
                "max_log_characters must be between 1,000 and 1,000,000."
            )

        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary.")

        self.metadata = serializable_value(dict(self.metadata))
        json.dumps(self.metadata, ensure_ascii=False)

    @staticmethod
    def _required_text(value: Any, label: str) -> str:
        if not isinstance(value, (str, Path)):
            raise TypeError(f"{label} must be a string or path.")

        normalized = str(value).strip()

        if not normalized:
            raise ValueError(f"{label} cannot be empty.")

        return normalized

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "workflow": self.workflow,
            "dataset": self.dataset,
            "target": self.target,
            "cell": self.cell,
            "through_cell": self.through_cell,
            "continue_on_error": self.continue_on_error,
            "working_directory": self.working_directory,
            "result_path": self.result_path,
            "overwrite_result": self.overwrite_result,
            "run_id": self.run_id,
            "metadata": serializable_value(self.metadata),
            "max_log_characters": self.max_log_characters,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PipelineRunSpec":
        if not isinstance(payload, dict):
            raise TypeError("Pipeline run specification must be a dictionary.")

        values = dict(payload)
        schema_version = str(
            values.pop("schema_version", PIPELINE_SCHEMA_VERSION)
        )

        if schema_version != PIPELINE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported pipeline schema version {schema_version}; "
                f"expected {PIPELINE_SCHEMA_VERSION}."
            )

        allowed = {
            "workflow",
            "dataset",
            "target",
            "cell",
            "through_cell",
            "continue_on_error",
            "working_directory",
            "result_path",
            "overwrite_result",
            "run_id",
            "metadata",
            "max_log_characters",
        }
        unknown = sorted(set(values) - allowed)

        if unknown:
            raise ValueError(
                "Unknown pipeline run option(s): " + ", ".join(unknown)
            )

        try:
            return cls(**values)
        except TypeError as error:
            if "workflow" not in values:
                raise ValueError(
                    "Pipeline run specification requires workflow."
                ) from error
            raise

    @classmethod
    def from_json(cls, path: str | Path) -> "PipelineRunSpec":
        source = Path(path).expanduser().resolve()
        payload = json.loads(source.read_text(encoding="utf-8"))

        if not isinstance(payload, dict):
            raise ValueError("Pipeline specification JSON must contain an object.")

        if payload.get("working_directory") is None:
            payload["working_directory"] = str(source.parent)

        return cls.from_dict(payload)


@dataclass(slots=True)
class PipelineArtifact:
    """A durable output created by an AutoDQ pipeline run."""

    name: str
    kind: str
    uri: str
    media_type: str | None = None
    size_bytes: int | None = None
    command: str | None = None
    cell: int | None = None
    statement: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "uri": self.uri,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "command": self.command,
            "cell": self.cell,
            "statement": self.statement,
            "metadata": serializable_value(self.metadata),
        }


@dataclass(slots=True)
class PipelineEvent:
    """One auditable lifecycle event from a pipeline run."""

    event: str
    message: str
    level: str = "info"
    timestamp: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "message": self.message,
            "level": self.level,
            "timestamp": self.timestamp.isoformat(),
            "metadata": serializable_value(self.metadata),
        }


@dataclass(slots=True)
class PipelineRunResult:
    """Platform-neutral result contract returned to an orchestrator."""

    run_id: str
    spec: PipelineRunSpec | None = None
    status: str = "running"
    exit_code: int = int(PipelineExitCode.INTERNAL_ERROR)
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None
    workflow_uri: str | None = None
    dataset_uri: str | None = None
    result_uri: str | None = None
    target: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: list[PipelineArtifact] = field(default_factory=list)
    events: list[PipelineEvent] = field(default_factory=list)
    workflow_result: dict[str, Any] | None = None
    environment: dict[str, Any] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""
    error_type: str | None = None
    error_message: str | None = None

    @property
    def success(self) -> bool:
        return self.exit_code == int(PipelineExitCode.SUCCESS)

    @property
    def duration_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0

        return round((self.finished_at - self.started_at).total_seconds(), 4)

    def add_event(
        self,
        event: str,
        message: str,
        *,
        level: str = "info",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            PipelineEvent(
                event=event,
                message=message,
                level=level,
                metadata=metadata or {},
            )
        )

    def finish(
        self,
        *,
        status: str,
        exit_code: PipelineExitCode | int,
        error: Exception | None = None,
    ) -> None:
        self.status = status
        self.exit_code = int(exit_code)
        self.finished_at = utc_now()

        if error is not None:
            self.error_type = type(error).__name__
            self.error_message = str(error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PIPELINE_SCHEMA_VERSION,
            "run_id": self.run_id,
            "status": self.status,
            "success": self.success,
            "exit_code": self.exit_code,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at is not None
                else None
            ),
            "duration_seconds": self.duration_seconds,
            "workflow_uri": self.workflow_uri,
            "dataset_uri": self.dataset_uri,
            "result_uri": self.result_uri,
            "target": self.target,
            "metadata": (
                serializable_value(self.spec.metadata)
                if self.spec is not None
                else {}
            ),
            "spec": self.spec.to_dict() if self.spec is not None else None,
            "metrics": serializable_value(self.metrics),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "events": [event.to_dict() for event in self.events],
            "environment": serializable_value(self.environment),
            "logs": {
                "stdout": self.stdout,
                "stderr": self.stderr,
            },
            "error_type": self.error_type,
            "error_message": self.error_message,
            "workflow_result": self.workflow_result,
        }


__all__ = [
    "PIPELINE_SCHEMA_VERSION",
    "PipelineArtifact",
    "PipelineEvent",
    "PipelineExitCode",
    "PipelineRunResult",
    "PipelineRunSpec",
]
