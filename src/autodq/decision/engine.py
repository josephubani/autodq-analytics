from dataclasses import dataclass

from autodq.models.recommendations import CleaningRecommendation


@dataclass
class DecisionAction:
    action_id: int
    issue_type: str
    strategy: str
    affected_columns: list[str]
    action: str
    reason: str
    priority: str
    risk: str | None = None
    confidence: float | None = None
    status: str = "pending"

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "issue_type": self.issue_type,
            "strategy": self.strategy,
            "affected_columns": self.affected_columns,
            "action": self.action,
            "reason": self.reason,
            "priority": self.priority,
            "risk": self.risk,
            "confidence": self.confidence,
            "status": self.status,
        }


@dataclass
class DecisionPlan:
    actions: list[DecisionAction]

    @property
    def action_count(self) -> int:
        return len(self.actions)

    def to_dict(self) -> dict:
        return {
            "action_count": self.action_count,
            "actions": [action.to_dict() for action in self.actions],
        }


class DecisionEngine:
    """
    Converts recommendations into an executable decision plan.
    """

    def build_plan(self, recommendations: list[CleaningRecommendation]) -> DecisionPlan:
        actions = []

        for index, rec in enumerate(recommendations, start=1):
            actions.append(
                DecisionAction(
                    action_id=index,
                    issue_type=rec.issue_type,
                    strategy=rec.strategy,
                    affected_columns=rec.affected_columns,
                    action=rec.action,
                    reason=rec.reason,
                    priority=rec.priority,
                    risk=rec.risk,
                    confidence=rec.confidence,
                )
            )

        return DecisionPlan(actions=actions)