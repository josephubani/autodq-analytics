from __future__ import annotations

import io
import mimetypes
import platform
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname
from uuid import uuid4

from autodq._version import __version__
from autodq.commands.errors import ADQLError
from autodq.commands.runner import ADQLFileRunner
from autodq.pipeline.connectors import (
    LocalArtifactStore,
    LocalSourceResolver,
    PipelineArtifactStore,
    PipelineSourceResolver,
)
from autodq.pipeline.models import (
    PipelineArtifact,
    PipelineExitCode,
    PipelineRunResult,
    PipelineRunSpec,
)


class PipelineRunner:
    """Execute ADQL through a stable, platform-neutral run contract."""

    def __init__(
        self,
        *,
        adql_runner: ADQLFileRunner | None = None,
        source_resolver: PipelineSourceResolver | None = None,
        artifact_store: PipelineArtifactStore | None = None,
    ):
        self.adql_runner = adql_runner or ADQLFileRunner()
        self.source_resolver = source_resolver or LocalSourceResolver()
        self.artifact_store = artifact_store or LocalArtifactStore()

    def run(self, spec: PipelineRunSpec | dict[str, Any]) -> PipelineRunResult:
        """Run a workflow without leaking notebook output to stdout."""
        if isinstance(spec, dict):
            spec = PipelineRunSpec.from_dict(spec)
        elif not isinstance(spec, PipelineRunSpec):
            raise TypeError("spec must be PipelineRunSpec or a dictionary.")

        result = PipelineRunResult(
            run_id=spec.run_id,
            spec=spec,
            environment=self._environment(),
        )
        result.add_event(
            "run_started",
            "AutoDQ pipeline run started.",
            metadata={"run_id": spec.run_id},
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        working_directory = Path(
            spec.working_directory or Path.cwd()
        ).expanduser().resolve()
        result_destination_ready = False

        try:
            if not working_directory.exists() or not working_directory.is_dir():
                raise FileNotFoundError(
                    f"Pipeline working directory not found: {working_directory}"
                )

            if spec.result_path is not None:
                result.result_uri = self.artifact_store.location(
                    spec.result_path,
                    base_path=working_directory,
                    overwrite=spec.overwrite_result,
                )
                result_destination_ready = True
                result.add_event(
                    "result_destination_ready",
                    "Pipeline result destination was validated.",
                    metadata={"result_uri": result.result_uri},
                )

            workflow = self.source_resolver.resolve(
                spec.workflow,
                base_path=working_directory,
            )
            dataset = (
                self.source_resolver.resolve(
                    spec.dataset,
                    base_path=working_directory,
                )
                if spec.dataset is not None
                else None
            )
            result.workflow_uri = workflow.as_uri()
            result.dataset_uri = dataset.as_uri() if dataset is not None else None
            result.target = spec.target
            result.add_event(
                "inputs_resolved",
                "Pipeline workflow and inputs were resolved.",
                metadata={
                    "workflow_uri": result.workflow_uri,
                    "dataset_uri": result.dataset_uri,
                },
            )

            with redirect_stdout(stdout), redirect_stderr(stderr):
                workflow_result = self.adql_runner.run(
                    workflow,
                    dataset=dataset,
                    target=spec.target,
                    cell=spec.cell,
                    through_cell=spec.through_cell,
                    continue_on_error=spec.continue_on_error,
                    raise_on_error=False,
                    auto_display=False,
                )

            result.workflow_result = workflow_result.to_dict()
            result.metrics = self._metrics(workflow_result)
            result.target = workflow_result.project.target
            result.dataset_uri = Path(
                workflow_result.project.dataset_path
            ).expanduser().resolve().as_uri()
            result.artifacts = self._discover_artifacts(
                workflow_result,
                workflow.parent,
            )
            result.add_event(
                "artifacts_discovered",
                f"Discovered {len(result.artifacts)} pipeline artifact(s).",
                metadata={
                    "artifact_count": len(result.artifacts),
                    "artifact_kinds": sorted(
                        {artifact.kind for artifact in result.artifacts}
                    ),
                },
            )

            if workflow_result.success:
                result.add_event(
                    "run_completed",
                    "AutoDQ pipeline run completed successfully.",
                    metadata=result.metrics,
                )
                result.finish(
                    status="completed",
                    exit_code=PipelineExitCode.SUCCESS,
                )
            else:
                result.add_event(
                    "run_failed",
                    "The ADQL workflow completed with failed statements.",
                    level="error",
                    metadata=result.metrics,
                )
                result.finish(
                    status="failed",
                    exit_code=PipelineExitCode.WORKFLOW_FAILED,
                )
        except (ADQLError, FileNotFoundError, FileExistsError, ValueError, TypeError) as error:
            result.add_event(
                "configuration_error",
                str(error),
                level="error",
            )
            result.finish(
                status="error",
                exit_code=PipelineExitCode.CONFIGURATION_ERROR,
                error=error,
            )
        except Exception as error:  # pragma: no cover - defensive platform boundary
            result.add_event(
                "internal_error",
                str(error),
                level="error",
            )
            result.finish(
                status="error",
                exit_code=PipelineExitCode.INTERNAL_ERROR,
                error=error,
            )

        result.stdout = self._bounded_log(
            stdout.getvalue(),
            spec.max_log_characters,
        )
        result.stderr = self._bounded_log(
            stderr.getvalue(),
            spec.max_log_characters,
        )

        if result.finished_at is None:
            result.finish(
                status="error",
                exit_code=PipelineExitCode.INTERNAL_ERROR,
                error=RuntimeError("Pipeline run ended without a final status."),
            )

        if spec.result_path is not None and result_destination_ready:
            try:
                self.artifact_store.write_json(
                    spec.result_path,
                    result.to_dict(),
                    base_path=working_directory,
                    overwrite=spec.overwrite_result,
                )
            except Exception as error:  # result persistence is part of the run
                result.add_event(
                    "result_write_failed",
                    f"Could not persist the pipeline result: {error}",
                    level="error",
                )
                result.finish(
                    status="error",
                    exit_code=PipelineExitCode.INTERNAL_ERROR,
                    error=error,
                )

        return result

    @classmethod
    def configuration_error(
        cls,
        error: Exception,
        *,
        run_id: str | None = None,
    ) -> PipelineRunResult:
        """Return a structured result when a specification cannot be loaded."""
        result = PipelineRunResult(
            run_id=run_id or uuid4().hex,
            environment=cls._environment(),
        )
        result.add_event(
            "configuration_error",
            str(error),
            level="error",
        )
        result.finish(
            status="error",
            exit_code=PipelineExitCode.CONFIGURATION_ERROR,
            error=error,
        )
        return result

    @staticmethod
    def _environment() -> dict[str, Any]:
        return {
            "autodq_version": __version__,
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
        }

    @staticmethod
    def _metrics(workflow_result) -> dict[str, Any]:
        statement_count = sum(
            cell.result.statement_count for cell in workflow_result.cell_runs
        )
        completed_statements = sum(
            cell.result.completed_count for cell in workflow_result.cell_runs
        )
        failed_statements = sum(
            cell.result.failed_count for cell in workflow_result.cell_runs
        )
        data = workflow_result.project.state.data

        return {
            "cell_count": len(workflow_result.cell_runs),
            "completed_cell_count": workflow_result.completed_cell_count,
            "failed_cell_count": workflow_result.failed_cell_count,
            "statement_count": statement_count,
            "completed_statement_count": completed_statements,
            "failed_statement_count": failed_statements,
            "rows": len(data) if data is not None else 0,
            "columns": len(data.columns) if data is not None else 0,
            "session_event_count": workflow_result.project.session.event_count,
            "duration_seconds": workflow_result.duration_seconds,
        }

    def _discover_artifacts(
        self,
        workflow_result,
        base_path: Path,
    ) -> list[PipelineArtifact]:
        artifacts: list[PipelineArtifact] = []
        seen: set[str] = set()

        for cell_run in workflow_result.cell_runs:
            for statement_result in cell_run.result.results:
                kind = self._artifact_kind(statement_result.statement)

                if kind is None or not statement_result.success:
                    continue

                candidates = self._artifact_candidates(
                    statement_result,
                    base_path,
                )

                for candidate in candidates:
                    try:
                        path = self.source_resolver.resolve(
                            candidate,
                            base_path=base_path,
                        )
                    except (FileNotFoundError, ValueError, TypeError):
                        continue

                    uri = path.as_uri()

                    if uri in seen:
                        continue

                    seen.add(uri)
                    artifacts.append(
                        PipelineArtifact(
                            name=path.name,
                            kind=kind,
                            uri=uri,
                            media_type=self._media_type(path),
                            size_bytes=self._path_size(path),
                            command=statement_result.statement.kind,
                            cell=cell_run.cell.number,
                            statement=(
                                statement_result.statement.statement_number
                            ),
                        )
                    )

        return artifacts

    @staticmethod
    def _artifact_kind(statement) -> str | None:
        kind = statement.kind
        action = str(statement.parameters.get("action", "")).lower()

        if kind == "EXPORT":
            return "dataset"
        if kind == "REPORT":
            return "report"
        if kind == "AUDIT":
            return "audit"
        if kind == "DASHBOARD":
            return "dashboard"
        if kind in {"VISUALIZE", "SHAP"} and statement.parameters.get("save"):
            return "visualization"
        if kind == "GALLERY" and action == "save":
            return "visualization"
        if kind == "MODEL" and action == "save":
            return "model"
        if kind == "AUTO" and statement.parameters.get("report_output"):
            return "report"
        if kind == "ASSERT" and action == "suite_export":
            return "quality_suite"
        if kind == "SCHEMA" and action == "export":
            return "schema_contract"
        if kind == "DRIFT" and action == "baseline_export":
            return "drift_baseline"
        if kind == "WORKSPACE" and action == "save":
            return "workspace"

        return None

    def _artifact_candidates(self, statement_result, base_path: Path) -> list[Any]:
        statement = statement_result.statement
        parameters = statement.parameters
        candidates: list[Any] = []
        parameter_keys = {
            "EXPORT": ("output",),
            "REPORT": ("output",),
            "AUDIT": ("output",),
            "DASHBOARD": ("output",),
            "VISUALIZE": ("save",),
            "SHAP": ("save",),
            "MODEL": ("path",),
            "AUTO": ("report_output",),
            "ASSERT": ("path",),
            "SCHEMA": ("path",),
            "DRIFT": ("path",),
            "GALLERY": ("output_dir",),
            "WORKSPACE": ("workspace_root",),
        }

        for key in parameter_keys.get(statement.kind, ()):
            value = parameters.get(key)
            if value is not None:
                candidates.append(value)

        candidates.extend(self._paths_from_value(statement_result.value))

        resolved: list[Any] = []
        for candidate in candidates:
            if isinstance(candidate, str) and not urlparse(candidate).scheme:
                path = Path(candidate).expanduser()
                if not path.is_absolute():
                    candidate = base_path / path
            resolved.append(candidate)

        return resolved

    def _paths_from_value(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, Path):
            return [value]
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple, set)):
            paths = []
            for item in value:
                paths.extend(self._paths_from_value(item))
            return paths
        if isinstance(value, dict):
            paths = []
            for key, item in value.items():
                normalized = str(key).lower()
                if (
                    normalized in {"path", "output", "output_path", "report_path"}
                    or normalized.endswith("_path")
                    or normalized.endswith("_paths")
                ):
                    paths.extend(self._paths_from_value(item))
            return paths

        paths = []
        for attribute in ("path", "output_path", "report_path", "saved_paths"):
            if hasattr(value, attribute):
                paths.extend(self._paths_from_value(getattr(value, attribute)))
        return paths

    @staticmethod
    def _media_type(path: Path) -> str:
        if path.is_dir():
            return "application/vnd.autodq.bundle"
        return mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    @staticmethod
    def _path_size(path: Path) -> int | None:
        try:
            if path.is_file():
                return path.stat().st_size
            if path.is_dir():
                return sum(
                    item.stat().st_size
                    for item in path.rglob("*")
                    if item.is_file()
                )
        except OSError:
            return None
        return None

    @staticmethod
    def _bounded_log(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value

        omitted = len(value) - limit
        marker = f"\n... [{omitted:,} log character(s) omitted] ...\n"
        content_limit = limit - len(marker)
        head = int(content_limit * 0.7)
        tail = content_limit - head
        return (
            value[:head]
            + marker
            + value[-tail:]
        )

    @staticmethod
    def local_path(uri: str) -> Path:
        """Convert a local file URI returned by the runner into a Path."""
        parsed = urlparse(uri)
        if parsed.scheme != "file":
            raise ValueError("Only file:// pipeline URIs have local paths.")
        return Path(url2pathname(unquote(parsed.path)))


__all__ = ["PipelineRunner"]
