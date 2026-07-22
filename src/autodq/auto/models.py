from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AutoRunConfig:
    mode: str = "review"
    approve_all: bool = False
    apply_cleaning: bool = False
    visualize: bool = True
    apply_features: bool = False
    train_model: bool = False
    generate_predictions: bool = False
    explain_model: bool = False
    algorithm: str = "auto"
    test_size: float = 0.2
    random_state: int = 42
    report_output: str | None = None
    report_style: str = "executive"
    save_workspace: bool = False
    refresh: bool = False
    continue_on_error: bool = False
    raise_on_error: bool = False
    auto_display: bool = True

    @classmethod
    def from_options(
        cls,
        *,
        mode: str = "review",
        approve_all: bool | None = None,
        apply_cleaning: bool | None = None,
        visualize: bool = True,
        apply_features: bool = False,
        train_model: bool | None = None,
        generate_predictions: bool | None = None,
        explain_model: bool | None = None,
        algorithm: str = "auto",
        test_size: float = 0.2,
        random_state: int = 42,
        report_output: str | None = None,
        report_style: str = "executive",
        save_workspace: bool = False,
        refresh: bool = False,
        continue_on_error: bool = False,
        raise_on_error: bool = False,
        auto_display: bool = True,
    ) -> "AutoRunConfig":
        normalized_mode = str(mode).lower().strip()

        if normalized_mode not in {"review", "clean", "full"}:
            raise ValueError("mode must be 'review', 'clean', or 'full'.")

        presets = {
            "review": {
                "approve_all": False,
                "apply_cleaning": False,
                "train_model": False,
                "generate_predictions": False,
                "explain_model": False,
            },
            "clean": {
                "approve_all": True,
                "apply_cleaning": True,
                "train_model": False,
                "generate_predictions": False,
                "explain_model": False,
            },
            "full": {
                "approve_all": True,
                "apply_cleaning": True,
                "train_model": True,
                "generate_predictions": True,
                "explain_model": True,
            },
        }[normalized_mode]
        values = {
            "approve_all": approve_all,
            "apply_cleaning": apply_cleaning,
            "train_model": train_model,
            "generate_predictions": generate_predictions,
            "explain_model": explain_model,
        }

        for name, value in values.items():
            if value is None:
                values[name] = presets[name]

        if not 0 < float(test_size) < 1:
            raise ValueError("test_size must be between 0 and 1.")

        if not isinstance(random_state, int) or isinstance(
            random_state,
            bool,
        ):
            raise ValueError("random_state must be an integer.")

        if report_output is not None and Path(report_output).suffix.lower() not in {
            ".html",
            ".json",
        }:
            raise ValueError("report_output must end with .html or .json.")

        return cls(
            mode=normalized_mode,
            approve_all=bool(values["approve_all"]),
            apply_cleaning=bool(values["apply_cleaning"]),
            visualize=bool(visualize),
            apply_features=bool(apply_features),
            train_model=bool(values["train_model"]),
            generate_predictions=bool(values["generate_predictions"]),
            explain_model=bool(values["explain_model"]),
            algorithm=str(algorithm),
            test_size=float(test_size),
            random_state=random_state,
            report_output=report_output,
            report_style=str(report_style),
            save_workspace=bool(save_workspace),
            refresh=bool(refresh),
            continue_on_error=bool(continue_on_error),
            raise_on_error=bool(raise_on_error),
            auto_display=bool(auto_display),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "approve_all": self.approve_all,
            "apply_cleaning": self.apply_cleaning,
            "visualize": self.visualize,
            "apply_features": self.apply_features,
            "train_model": self.train_model,
            "generate_predictions": self.generate_predictions,
            "explain_model": self.explain_model,
            "algorithm": self.algorithm,
            "test_size": self.test_size,
            "random_state": self.random_state,
            "report_output": self.report_output,
            "report_style": self.report_style,
            "save_workspace": self.save_workspace,
            "refresh": self.refresh,
            "continue_on_error": self.continue_on_error,
            "raise_on_error": self.raise_on_error,
            "auto_display": self.auto_display,
        }


@dataclass(slots=True)
class AutoStageResult:
    name: str
    status: str
    message: str
    duration_seconds: float = 0.0
    summary: dict[str, Any] = field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "duration_seconds": self.duration_seconds,
            "summary": self.summary,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }


@dataclass(slots=True)
class AutoRunResult:
    config: AutoRunConfig
    stages: list[AutoStageResult] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    review: Any | None = field(default=None, repr=False)
    report_path: Path | None = None
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    auto_display: bool = field(default=True, repr=False)

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.stages if item.status == "failed")

    @property
    def completed_count(self) -> int:
        return sum(1 for item in self.stages if item.status == "completed")

    @property
    def reused_count(self) -> int:
        return sum(1 for item in self.stages if item.status == "reused")

    @property
    def skipped_count(self) -> int:
        return sum(1 for item in self.stages if item.status == "skipped")

    @property
    def success(self) -> bool:
        return self.failed_count == 0

    @property
    def halted(self) -> bool:
        return bool(self.stages and self.stages[-1].status == "failed")

    @property
    def duration_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0

        return round(
            (self.finished_at - self.started_at).total_seconds(),
            4,
        )

    def stage(self, name: str) -> AutoStageResult:
        for item in self.stages:
            if item.name == name:
                return item

        raise KeyError(f"Auto stage was not found: {name}")

    def to_dict(self) -> dict[str, Any]:
        review_summary = None

        if self.review is not None:
            review_summary = {
                "action_count": self.review.action_count,
                "pending_count": self.review.pending_count,
                "approved_count": self.review.approved_count,
                "rejected_count": self.review.rejected_count,
                "audit_count": self.review.audit_count,
            }

        return {
            "config": self.config.to_dict(),
            "success": self.success,
            "halted": self.halted,
            "completed_count": self.completed_count,
            "reused_count": self.reused_count,
            "skipped_count": self.skipped_count,
            "failed_count": self.failed_count,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat(),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at is not None
                else None
            ),
            "report_path": (
                str(self.report_path)
                if self.report_path is not None
                else None
            ),
            "next_actions": self.next_actions,
            "review": review_summary,
            "stages": [item.to_dict() for item in self.stages],
        }

    def to_html(self) -> str:
        from autodq.auto.notebook_renderer import AutoNotebookRenderer

        return AutoNotebookRenderer().render(self)

    def show(self) -> "AutoRunResult":
        try:
            from IPython.display import HTML, display
        except ImportError:
            print(self.to_dict())
        else:
            display(HTML(self.to_html()))

        return self

    def _repr_html_(self) -> str | None:
        if not self.auto_display:
            return None

        return self.to_html()


class AutoRunError(RuntimeError):
    def __init__(
        self,
        stage: str,
        message: str,
        result: AutoRunResult,
    ):
        super().__init__(f"project.auto() failed at '{stage}': {message}")
        self.stage = stage
        self.result = result
