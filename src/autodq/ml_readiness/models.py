from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class MLReadinessIssue:
    issue_type: str
    severity: str
    message: str
    recommendation: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "message": self.message,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class MLReadinessReport:
    score: float
    target: str | None
    target_type: str
    recommended_task: str
    recommended_models: list[str]
    issues: list[MLReadinessIssue] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "target": self.target,
            "target_type": self.target_type,
            "recommended_task": self.recommended_task,
            "recommended_models": self.recommended_models,
            "issue_count": self.issue_count,
            "strengths": self.strengths,
            "issues": [issue.to_dict() for issue in self.issues],
            "generated_at": self.generated_at.isoformat(),
        }