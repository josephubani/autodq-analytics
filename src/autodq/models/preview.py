from dataclasses import dataclass, field
from typing import Any


@dataclass
class PreviewAction:
    action_id: int
    issue_type: str
    strategy: str
    details: dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "issue_type": self.issue_type,
            "strategy": self.strategy,
            "details": self.details,
        }


@dataclass
class PreviewReport:
    actions: list[PreviewAction] = field(default_factory=list)

    @property
    def action_count(self) -> int:
        return len(self.actions)

    def to_dict(self) -> dict:
        return {
            "action_count": self.action_count,
            "actions": [action.to_dict() for action in self.actions],
        }