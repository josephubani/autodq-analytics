from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class AutoDQState:
    dataset_path: Path
    target: str | None = None

    data: pd.DataFrame | None = None
    cleaned_data: pd.DataFrame | None = None

    profile_report: dict | None = None
    diagnosis_report = None
    recommendations = None
    decision_plan = None
    preview_report = None
    knowledge_rules = None
    statistics_report = None
    interpretation_report = None
    cleaning_report = None
    validation_report = None
    visualization_report = None
    correlation_report = None
    ml_readiness_report = None
    feature_report = None

    def reset_outputs(self) -> None:
        self.profile_report = None
        self.diagnosis_report = None
        self.recommendations = None
        self.decision_plan = None
        self.preview_report = None
        self.knowledge_rules = None
        self.statistics_report = None
        self.interpretation_report = None
        self.cleaning_report = None
        self.cleaned_data = None
        self.validation_report = None
        self.visualization_report = None
        self.correlation_report = None
        self.ml_readiness_report = None
        self.feature_report = None

    def reset_all(self, dataset_path: str | Path) -> None:
        self.dataset_path = Path(dataset_path)
        self.data = None
        self.cleaned_data = None
        self.reset_outputs()