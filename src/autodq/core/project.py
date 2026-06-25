from pathlib import Path

import pandas as pd

from autodq.core.session import AutoDQSession
from autodq.decision.engine import DecisionEngine
from autodq.diagnosis.engine import run_diagnosis
from autodq.io.loaders import load_dataset
from autodq.preview.engine import PreviewEngine
from autodq.profiling.profiler import generate_profile
from autodq.recommendations.engine import RecommendationEngine
from autodq.renderers.console.diagnosis import ConsoleDiagnosisRenderer
from autodq.renderers.console.preview import ConsolePreviewRenderer
from autodq.renderers.console.profile import ConsoleProfileRenderer
from autodq.renderers.console.recommendations import ConsoleRecommendationRenderer


class AutoDQ:
    """
    Main project controller for AutoDQ Analytics.
    """

    def __init__(self, dataset_path: str, target: str | None = None):
        self.dataset_path = Path(dataset_path)
        self.target = target

        self.data: pd.DataFrame | None = None
        self.profile_report: dict | None = None
        self.diagnosis_report = None
        self.recommendations = None
        self.decision_plan = None
        self.previews = None

        self.session = AutoDQSession(dataset_path=str(self.dataset_path))

    def _reset_outputs(self) -> None:
        self.profile_report = None
        self.diagnosis_report = None
        self.recommendations = None
        self.decision_plan = None
        self.previews = None

    def load(self) -> pd.DataFrame:
        self.data = load_dataset(self.dataset_path)

        self.session.log(
            step="load",
            message="Dataset loaded successfully.",
            metadata={"rows": len(self.data), "columns": len(self.data.columns)},
        )

        return self.data

    def change_dataset(self, dataset_path: str) -> pd.DataFrame:
        self.dataset_path = Path(dataset_path)
        self.data = None
        self._reset_outputs()

        self.session = AutoDQSession(dataset_path=str(self.dataset_path))
        self.session.log(
            step="change_dataset",
            message="Dataset path changed and project state reset.",
            metadata={"dataset_path": str(self.dataset_path)},
        )

        return self.load()

    def set_target(self, target: str) -> None:
        self.target = target

        self.session.log(
            step="set_target",
            message="Target column updated.",
            metadata={"target": target},
        )

    def set_type(self, column: str, dtype: str) -> None:
        if self.data is None:
            self.load()

        if column not in self.data.columns:
            raise ValueError(f"Column not found: {column}")

        dtype_normalized = dtype.lower().strip()

        if dtype_normalized == "datetime":
            self.data[column] = pd.to_datetime(self.data[column], errors="coerce")

        elif dtype_normalized in ["str", "string", "text"]:
            self.data[column] = self.data[column].astype(str)

        elif dtype_normalized in ["int", "integer"]:
            self.data[column] = pd.to_numeric(
                self.data[column],
                errors="coerce",
            ).astype("Int64")

        elif dtype_normalized in ["float", "numeric", "number"]:
            self.data[column] = pd.to_numeric(self.data[column], errors="coerce")

        elif dtype_normalized in ["category", "categorical"]:
            self.data[column] = self.data[column].astype("category")

        else:
            raise ValueError(
                f"Unsupported dtype: {dtype}. "
                "Supported: datetime, string, int, float, category"
            )

        self._reset_outputs()

        self.session.log(
            step="set_type",
            message="Column data type manually updated.",
            metadata={"column": column, "dtype": dtype_normalized},
        )

    def profile(self) -> dict:
        if self.data is None:
            self.load()

        self.profile_report = generate_profile(
            self.data,
            dataset_path=str(self.dataset_path),
        )

        self.session.log(
            step="profile",
            message="Dataset profile generated.",
            metadata={
                "rows": self.profile_report["rows"],
                "columns": self.profile_report["columns"],
            },
        )

        return self.profile_report

    def diagnose(self):
        if self.data is None:
            self.load()

        self.diagnosis_report = run_diagnosis(self.data)

        self.session.log(
            step="diagnose",
            message="Data quality diagnosis completed.",
            metadata={
                "issue_count": self.diagnosis_report.issue_count,
                "quality_score": self.diagnosis_report.quality_score,
            },
        )

        return self.diagnosis_report

    def recommend(self):
        if self.diagnosis_report is None:
            self.diagnose()

        engine = RecommendationEngine()
        self.recommendations = engine.recommend(self.diagnosis_report)

        self.session.log(
            step="recommend",
            message="Cleaning recommendations generated.",
            metadata={"recommendation_count": len(self.recommendations)},
        )

        return self.recommendations

    def decide(self):
        if self.recommendations is None:
            self.recommend()

        engine = DecisionEngine()
        self.decision_plan = engine.build_plan(self.recommendations)

        self.session.log(
            step="decide",
            message="Decision plan created.",
            metadata={"action_count": self.decision_plan.action_count},
        )

        return self.decision_plan

    def preview(self):
        if self.data is None:
            self.load()

        if self.decision_plan is None:
            self.decide()

        engine = PreviewEngine()
        self.previews = engine.preview(self.data, self.decision_plan)

        self.session.log(
            step="preview",
            message="Cleaning preview generated.",
            metadata={"preview_actions": self.previews.action_count},
        )

        return self.previews

    def show_profile(self) -> None:
        if self.profile_report is None:
            self.profile()

        ConsoleProfileRenderer.render(self.profile_report)

    def show_diagnosis(self) -> None:
        if self.diagnosis_report is None:
            self.diagnose()

        ConsoleDiagnosisRenderer.render(self.diagnosis_report)

    def show_recommendations(self) -> None:
        if self.recommendations is None:
            self.recommend()

        ConsoleRecommendationRenderer.render(self.recommendations)

    def show_preview(self) -> None:
        if self.previews is None:
            self.preview()

        ConsolePreviewRenderer.render(self.previews)

    def show_session(self) -> None:
        self.session.summary()