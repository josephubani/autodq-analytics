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
    confidence: float | None = None
    uncertainty: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    interval_width: float | None = None
    confidence_level: float | None = None
    class_probabilities: dict[str, float] = field(default_factory=dict)
    prediction_margin: float | None = None
    entropy: float | None = None
    low_confidence: bool | None = None
    uncertainty_method: str | None = None
    top_features: list[str] = field(default_factory=list)
    explanation: str | None = None

    def to_dict(self) -> dict:
        return {
            "row_id": self.row_id,
            "actual": self.actual,
            "predicted": self.predicted,
            "residual": self.residual,
            "absolute_error": self.absolute_error,
            "percent_error": self.percent_error,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "interval_width": self.interval_width,
            "confidence_level": self.confidence_level,
            "class_probabilities": self.class_probabilities,
            "prediction_margin": self.prediction_margin,
            "entropy": self.entropy,
            "low_confidence": self.low_confidence,
            "uncertainty_method": self.uncertainty_method,
            "top_features": self.top_features,
            "explanation": self.explanation,
        }


@dataclass(slots=True)
class PredictionReport:
    target: str
    problem_type: str
    algorithm: str
    predictions: list[PredictionResult] = field(default_factory=list)
    total_predictions: int = 0
    warnings: list[str] = field(default_factory=list)
    uncertainty_requested: bool = False
    uncertainty_available: bool = False
    uncertainty_method: str | None = None
    confidence_level: float | None = None
    calibration_size: int = 0
    calibration_metrics: dict[str, float] = field(default_factory=dict)
    empirical_coverage: float | None = None
    mean_interval_width: float | None = None
    mean_confidence: float | None = None
    low_confidence_count: int = 0
    low_confidence_threshold: float | None = None
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def prediction_count(self) -> int:
        return self.total_predictions or len(self.predictions)

    @property
    def sample_count(self) -> int:
        return len(self.predictions)

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "problem_type": self.problem_type,
            "algorithm": self.algorithm,
            "prediction_count": self.prediction_count,
            "sample_count": self.sample_count,
            "warnings": self.warnings,
            "uncertainty_requested": self.uncertainty_requested,
            "uncertainty_available": self.uncertainty_available,
            "uncertainty_method": self.uncertainty_method,
            "confidence_level": self.confidence_level,
            "calibration_size": self.calibration_size,
            "calibration_metrics": self.calibration_metrics,
            "empirical_coverage": self.empirical_coverage,
            "mean_interval_width": self.mean_interval_width,
            "mean_confidence": self.mean_confidence,
            "low_confidence_count": self.low_confidence_count,
            "low_confidence_threshold": self.low_confidence_threshold,
            "predictions": [
                prediction.to_dict()
                for prediction in self.predictions
            ],
            "generated_at": self.generated_at.isoformat(),
        }
