from dataclasses import dataclass


@dataclass
class CleaningRecommendation:
    column: str
    issue_type: str
    strategy: str
    reason: str
    risk: str | None = None
    confidence: float | None = None

    def to_dict(self) -> dict:
        return {
            "column": self.column,
            "issue_type": self.issue_type,
            "strategy": self.strategy,
            "reason": self.reason,
            "risk": self.risk,
            "confidence": self.confidence,
        }