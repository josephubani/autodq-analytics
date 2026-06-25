from dataclasses import dataclass


@dataclass
class CleaningRecommendation:
    issue_type: str
    strategy: str
    reason: str
    affected_columns: list[str]
    action: str
    priority: str = "medium"
    risk: str | None = None
    confidence: float | None = None

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type,
            "strategy": self.strategy,
            "reason": self.reason,
            "affected_columns": self.affected_columns,
            "action": self.action,
            "priority": self.priority,
            "risk": self.risk,
            "confidence": self.confidence,
        }