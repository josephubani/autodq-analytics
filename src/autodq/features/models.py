from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class FeatureRecommendation:
    feature_name: str
    source_columns: list[str]
    feature_type: str
    formula: str
    reason: str
    priority: str
    executable: bool = False
    confidence: float = 0.8

    def to_dict(self) -> dict:
        return {
            "feature_name": self.feature_name,
            "source_columns": self.source_columns,
            "feature_type": self.feature_type,
            "formula": self.formula,
            "reason": self.reason,
            "priority": self.priority,
            "executable": self.executable,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class FeatureEngineeringReport:
    recommendations: list[FeatureRecommendation] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def recommendation_count(self) -> int:
        return len(self.recommendations)

    def to_dict(self) -> dict:
        return {
            "recommendation_count": self.recommendation_count,
            "generated_at": self.generated_at.isoformat(),
            "recommendations": [
                recommendation.to_dict()
                for recommendation in self.recommendations
            ],
        }