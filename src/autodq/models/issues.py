from dataclasses import dataclass, field


@dataclass
class DataIssue:
    issue_type: str
    severity: str
    message: str
    affected_columns: list[str] = field(default_factory=list)
    recommendation: str | None = None
    confidence: float | None = None

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "message": self.message,
            "affected_columns": self.affected_columns,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
        }