from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeRule:
    name: str
    semantic_type: str | None = None
    expected_min: float | None = None
    expected_max: float | None = None
    allow_negative: bool | None = None
    preferred_imputation: str | None = None
    preferred_outlier_strategy: str | None = None
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "semantic_type": self.semantic_type,
            "expected_min": self.expected_min,
            "expected_max": self.expected_max,
            "allow_negative": self.allow_negative,
            "preferred_imputation": self.preferred_imputation,
            "preferred_outlier_strategy": self.preferred_outlier_strategy,
            "notes": self.notes,
            "metadata": self.metadata,
        }