from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class CorrelationRelationship:
    feature_a: str
    feature_b: str
    correlation: float
    strength: str
    direction: str
    severity: str
    interpretation: str
    recommendation: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "feature_a": self.feature_a,
            "feature_b": self.feature_b,
            "correlation": self.correlation,
            "strength": self.strength,
            "direction": self.direction,
            "severity": self.severity,
            "interpretation": self.interpretation,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class TargetCorrelation:
    feature: str
    target: str
    correlation: float
    strength: str
    direction: str
    interpretation: str
    recommendation: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "target": self.target,
            "correlation": self.correlation,
            "strength": self.strength,
            "direction": self.direction,
            "interpretation": self.interpretation,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class CorrelationReport:
    relationships: list[CorrelationRelationship] = field(default_factory=list)
    target_relationships: list[TargetCorrelation] = field(default_factory=list)
    matrix: dict | None = None
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)

    @property
    def target_relationship_count(self) -> int:
        return len(self.target_relationships)

    def to_dict(self) -> dict:
        return {
            "relationship_count": self.relationship_count,
            "target_relationship_count": self.target_relationship_count,
            "generated_at": self.generated_at.isoformat(),
            "matrix": self.matrix,
            "relationships": [
                relationship.to_dict()
                for relationship in self.relationships
            ],
            "target_relationships": [
                relationship.to_dict()
                for relationship in self.target_relationships
            ],
        }