from pathlib import Path

import pandas as pd

from autodq.core.session import AutoDQSession
from autodq.core.state import AutoDQState
from autodq.decision.engine import DecisionEngine
from autodq.diagnosis.engine import run_diagnosis
from autodq.io.loaders import load_dataset
from autodq.knowledge.engine import KnowledgeEngine
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
        self.state = AutoDQState(
            dataset_path=Path(dataset_path),
            target=target,
        )

        self.knowledge_engine = KnowledgeEngine()
        self.session = AutoDQSession(dataset_path=str(self.state.dataset_path))

    @property
    def dataset_path(self):
        return self.state.dataset_path

    @property
    def target(self):
        return self.state.target

    @property
    def data(self):
        return self.state.data

    def load(self) -> pd.DataFrame:
        self.state.data = load_dataset(self.state.dataset_path)

        self.session.log(
            step="load",
            message="Dataset loaded successfully.",
            metadata={
                "rows": len(self.state.data),
                "columns": len(self.state.data.columns),
            },
        )

        return self.state.data

    def change_dataset(self, dataset_path: str) -> pd.DataFrame:
        self.state.reset_all(dataset_path)

        self.session = AutoDQSession(dataset_path=str(self.state.dataset_path))
        self.session.log(
            step="change_dataset",
            message="Dataset path changed and project state reset.",
            metadata={"dataset_path": str(self.state.dataset_path)},
        )

        return self.load()

    def set_target(self, target: str) -> None:
        self.state.target = target

        self.session.log(
            step="set_target",
            message="Target column updated.",
            metadata={"target": target},
        )

    def set_type(self, column: str, dtype: str) -> None:
        if self.state.data is None:
            self.load()

        if column not in self.state.data.columns:
            raise ValueError(f"Column not found: {column}")

        dtype_normalized = dtype.lower().strip()

        if dtype_normalized == "datetime":
            self.state.data[column] = pd.to_datetime(
                self.state.data[column],
                errors="coerce",
            )

        elif dtype_normalized in ["str", "string", "text"]:
            self.state.data[column] = self.state.data[column].astype(str)

        elif dtype_normalized in ["int", "integer"]:
            self.state.data[column] = pd.to_numeric(
                self.state.data[column],
                errors="coerce",
            ).astype("Int64")

        elif dtype_normalized in ["float", "numeric", "number"]:
            self.state.data[column] = pd.to_numeric(
                self.state.data[column],
                errors="coerce",
            )

        elif dtype_normalized in ["category", "categorical"]:
            self.state.data[column] = self.state.data[column].astype("category")

        else:
            raise ValueError(
                f"Unsupported dtype: {dtype}. "
                "Supported: datetime, string, int, float, category"
            )

        self.state.reset_outputs()

        self.session.log(
            step="set_type",
            message="Column data type manually updated.",
            metadata={"column": column, "dtype": dtype_normalized},
        )

    def apply_knowledge(self):
        if self.state.data is None:
            self.load()

        self.state.knowledge_rules = self.knowledge_engine.get_rules_for_columns(
            list(self.state.data.columns)
        )

        matched_rules = {
            column: rule.to_dict()
            for column, rule in self.state.knowledge_rules.items()
            if rule is not None
        }

        self.session.log(
            step="knowledge",
            message="Knowledge rules applied to dataset columns.",
            metadata={"matched_columns": list(matched_rules.keys())},
        )

        return self.state.knowledge_rules

    def profile(self) -> dict:
        if self.state.data is None:
            self.load()

        self.state.profile_report = generate_profile(
            self.state.data,
            dataset_path=str(self.state.dataset_path),
        )

        self.session.log(
            step="profile",
            message="Dataset profile generated.",
            metadata={
                "rows": self.state.profile_report["rows"],
                "columns": self.state.profile_report["columns"],
            },
        )

        return self.state.profile_report

    def diagnose(self):
        if self.state.data is None:
            self.load()

        self.state.diagnosis_report = run_diagnosis(self.state.data)

        self.session.log(
            step="diagnose",
            message="Data quality diagnosis completed.",
            metadata={
                "issue_count": self.state.diagnosis_report.issue_count,
                "quality_score": self.state.diagnosis_report.quality_score,
            },
        )

        return self.state.diagnosis_report

    def recommend(self):
        if self.state.diagnosis_report is None:
            self.diagnose()

        engine = RecommendationEngine(self.knowledge_engine)
        self.state.recommendations = engine.recommend(self.state.diagnosis_report)

        self.session.log(
            step="recommend",
            message="Cleaning recommendations generated.",
            metadata={"recommendation_count": len(self.state.recommendations)},
        )

        return self.state.recommendations

    def decide(self):
        if self.state.recommendations is None:
            self.recommend()

        engine = DecisionEngine()
        self.state.decision_plan = engine.build_plan(self.state.recommendations)

        self.session.log(
            step="decide",
            message="Decision plan created.",
            metadata={"action_count": self.state.decision_plan.action_count},
        )

        return self.state.decision_plan

    def preview(self):
        if self.state.data is None:
            self.load()

        if self.state.decision_plan is None:
            self.decide()

        engine = PreviewEngine()
        self.state.preview_report = engine.preview(
            self.state.data,
            self.state.decision_plan,
        )

        self.session.log(
            step="preview",
            message="Cleaning preview generated.",
            metadata={"preview_actions": self.state.preview_report.action_count},
        )

        return self.state.preview_report

    def show_knowledge(self) -> None:
        if not self.state.knowledge_rules:
            self.apply_knowledge()

        print("\n=== AutoDQ Knowledge Layer ===")

        matched = False

        for column, rule in self.state.knowledge_rules.items():
            if rule is None:
                continue

            matched = True
            print(f"\n{column}")
            print(f"  Semantic Type: {rule.semantic_type}")
            print(f"  Preferred Imputation: {rule.preferred_imputation}")
            print(f"  Preferred Outlier Strategy: {rule.preferred_outlier_strategy}")

            if rule.expected_min is not None:
                print(f"  Expected Min: {rule.expected_min}")

            if rule.expected_max is not None:
                print(f"  Expected Max: {rule.expected_max}")

            if rule.allow_negative is not None:
                print(f"  Allow Negative: {rule.allow_negative}")

            if rule.notes:
                print(f"  Notes: {' '.join(rule.notes)}")

        if not matched:
            print("No knowledge rules matched this dataset yet.")

    def show_profile(self) -> None:
        if self.state.profile_report is None:
            self.profile()

        ConsoleProfileRenderer.render(self.state.profile_report)

    def show_diagnosis(self) -> None:
        if self.state.diagnosis_report is None:
            self.diagnose()

        ConsoleDiagnosisRenderer.render(self.state.diagnosis_report)

    def show_recommendations(self) -> None:
        if self.state.recommendations is None:
            self.recommend()

        ConsoleRecommendationRenderer.render(self.state.recommendations)

    def show_preview(self) -> None:
        if self.state.preview_report is None:
            self.preview()

        ConsolePreviewRenderer.render(self.state.preview_report)

    def show_session(self) -> None:
        self.session.summary()