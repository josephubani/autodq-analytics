from dataclasses import dataclass, field


@dataclass(slots=True)
class StatisticalInterpretation:
    column: str
    insight_type: str
    severity: str
    message: str
    evidence: list[str] = field(default_factory=list)
    downstream_implications: list[str] = field(default_factory=list)
    confidence: float = 0.75

    def to_dict(self) -> dict:
        return {
            "column": self.column,
            "insight_type": self.insight_type,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
            "downstream_implications": self.downstream_implications,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class InterpretationReport:
    interpretations: dict[str, list[StatisticalInterpretation]] = field(default_factory=dict)

    @property
    def insight_count(self) -> int:
        return sum(len(items) for items in self.interpretations.values())

    def to_dict(self) -> dict:
        return {
            "insight_count": self.insight_count,
            "interpretations": {
                column: [item.to_dict() for item in items]
                for column, items in self.interpretations.items()
            },
        }