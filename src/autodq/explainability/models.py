from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class FeatureContribution:
    """
    Contribution of one transformed feature to a model prediction.
    """

    feature: str
    contribution: float
    direction: str
    rank: int
    feature_value: Any | None = None
    contribution_percent: float | None = None

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "feature_value": self.feature_value,
            "contribution": self.contribution,
            "contribution_percent": self.contribution_percent,
            "direction": self.direction,
            "rank": self.rank,
        }


@dataclass(slots=True)
class RowExplanation:
    """
    Local explanation for one prediction row.
    """

    row_id: int
    prediction: Any
    base_value: float | None = None
    top_contributions: list[FeatureContribution] = field(
        default_factory=list
    )
    positive_contributions: list[FeatureContribution] = field(
        default_factory=list
    )
    negative_contributions: list[FeatureContribution] = field(
        default_factory=list
    )
    explanation: str | None = None

    def to_dict(self) -> dict:
        return {
            "row_id": self.row_id,
            "prediction": self.prediction,
            "base_value": self.base_value,
            "top_contributions": [
                contribution.to_dict()
                for contribution in self.top_contributions
            ],
            "positive_contributions": [
                contribution.to_dict()
                for contribution in self.positive_contributions
            ],
            "negative_contributions": [
                contribution.to_dict()
                for contribution in self.negative_contributions
            ],
            "explanation": self.explanation,
        }


@dataclass(slots=True)
class ExplainabilityReport:
    """
    Structured explainability output for AutoDQ.
    """

    algorithm: str
    method: str
    row_explanations: list[RowExplanation] = field(default_factory=list)
    global_features: list[FeatureContribution] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    feature_names: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def explanation_count(self) -> int:
        return len(self.row_explanations)

    @property
    def global_feature_count(self) -> int:
        return len(self.global_features)

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "method": self.method,
            "explanation_count": self.explanation_count,
            "global_feature_count": self.global_feature_count,
            "feature_names": self.feature_names,
            "warnings": self.warnings,
            "row_explanations": [
                explanation.to_dict()
                for explanation in self.row_explanations
            ],
            "global_features": [
                feature.to_dict()
                for feature in self.global_features
            ],
            "generated_at": self.generated_at.isoformat(),
        }