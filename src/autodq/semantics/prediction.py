from dataclasses import dataclass, field


@dataclass
class SemanticPrediction:
    semantic_type: str
    confidence: float
    detector: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "semantic_type": self.semantic_type,
            "confidence": self.confidence,
            "detector": self.detector,
            "evidence": self.evidence,
        }