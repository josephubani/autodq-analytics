from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class CleaningActionResult:
    action_id: int
    issue_type: str
    strategy: str
    affected_columns: list[str]
    status: str
    message: str
    rows_before: int | None = None
    rows_after: int | None = None


@dataclass(slots=True)
class CleaningReport:
    actions: list[CleaningActionResult] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def action_count(self) -> int:
        return len(self.actions)

    @property
    def successful_actions(self) -> int:
        return sum(1 for action in self.actions if action.status == "success")

    def to_dict(self) -> dict:
        return {
            "action_count": self.action_count,
            "successful_actions": self.successful_actions,
            "generated_at": self.generated_at.isoformat(),
            "actions": [
                {
                    "action_id": action.action_id,
                    "issue_type": action.issue_type,
                    "strategy": action.strategy,
                    "affected_columns": action.affected_columns,
                    "status": action.status,
                    "message": action.message,
                    "rows_before": action.rows_before,
                    "rows_after": action.rows_after,
                }
                for action in self.actions
            ],
        }