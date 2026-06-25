from pathlib import Path

import pandas as pd

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

    def load(self) -> pd.DataFrame:
        self.data = load_dataset(self.dataset_path)
        return self.data

    def profile(self) -> dict:
        if self.data is None:
            self.load()

        self.profile_report = generate_profile(
            self.data,
            dataset_path=str(self.dataset_path),
        )
        return self.profile_report

    def diagnose(self):
        if self.data is None:
            self.load()

        self.diagnosis_report = run_diagnosis(self.data)
        return self.diagnosis_report

    def recommend(self):
        if self.diagnosis_report is None:
            self.diagnose()

        engine = RecommendationEngine()
        self.recommendations = engine.recommend(self.diagnosis_report)
        return self.recommendations

    def decide(self):
        if self.recommendations is None:
            self.recommend()

        engine = DecisionEngine()
        self.decision_plan = engine.build_plan(self.recommendations)
        return self.decision_plan

    def preview(self):
        if self.data is None:
            self.load()

        if self.decision_plan is None:
            self.decide()

        engine = PreviewEngine()
        self.previews = engine.preview(self.data, self.decision_plan)
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