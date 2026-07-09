from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class FeatureContribution:
    feature: str
    contribution: float
    direction: str
    rank: int


@dataclass(slots=True)
class RowExplanation:
    row_id: int
    prediction: object
    top_contributions: list[FeatureContribution] = field(default_factory=list)
    explanation: str | None = None


@dataclass(slots=True)
class ExplainabilityReport:
    algorithm: str
    method: str
    row_explanations: list[RowExplanation] = field(default_factory=list)
    global_features: list[FeatureContribution] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def explanation_count(self) -> int:
        return len(self.row_explanations)