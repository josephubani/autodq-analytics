from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class PredictionResult:
    row_id: int
    predicted: Any
    actual: Any | None = None
    residual: float | None = None
    absolute_error: float | None = None
    percent_error: float | None = None

    def to_dict(self) -> dict:
        return {
            "row_id": self.row_id,
            "actual": self.actual,
            "predicted": self.predicted,
            "residual": self.residual,
            "absolute_error": self.absolute_error,
            "percent_error": self.percent_error,
        }


@dataclass(slots=True)
class PredictionReport:
    target: str
    problem_type: str
    algorithm: str
    predictions: list[PredictionResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def prediction_count(self) -> int:
        return len(self.predictions)

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "problem_type": self.problem_type,
            "algorithm": self.algorithm,
            "prediction_count": self.prediction_count,
            "warnings": self.warnings,
            "predictions": [prediction.to_dict() for prediction in self.predictions],
            "generated_at": self.generated_at.isoformat(),
        }