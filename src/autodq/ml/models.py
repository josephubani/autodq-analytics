from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ModelMetrics:
    problem_type: str
    algorithm: str

    mae: float | None = None
    rmse: float | None = None
    r2: float | None = None

    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None

    def to_dict(self) -> dict:
        return {
            "problem_type": self.problem_type,
            "algorithm": self.algorithm,
            "mae": self.mae,
            "rmse": self.rmse,
            "r2": self.r2,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


@dataclass(slots=True)
class FeatureImportance:
    feature: str
    importance: float
    rank: int

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "importance": self.importance,
            "rank": self.rank,
        }


@dataclass(slots=True)
class ModelPrediction:
    actual: Any
    predicted: Any
    residual: float | None = None

    def to_dict(self) -> dict:
        return {
            "actual": self.actual,
            "predicted": self.predicted,
            "residual": self.residual,
        }


@dataclass(slots=True)
class ModelComparisonResult:
    algorithm: str
    problem_type: str
    primary_metric: str
    primary_score: float
    metrics: ModelMetrics
    rank: int = 0

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "problem_type": self.problem_type,
            "primary_metric": self.primary_metric,
            "primary_score": self.primary_score,
            "rank": self.rank,
            "metrics": self.metrics.to_dict(),
        }

@dataclass(slots=True)
class ModelReport:
    target: str
    problem_type: str
    algorithm: str
    metrics: ModelMetrics
    feature_importance: list[FeatureImportance] = field(default_factory=list)
    predictions: list[ModelPrediction] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    model_object: object | None = None
    preprocessing_object: object | None = None
    feature_columns: list[str] = field(default_factory=list)
    feature_dtypes: dict[str, str] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    model_comparison: list[ModelComparisonResult] = field(default_factory=list)

    @property
    def prediction_count(self) -> int:
        return len(self.predictions)

    @property
    def feature_count(self) -> int:
        return len(self.feature_columns)

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "problem_type": self.problem_type,
            "algorithm": self.algorithm,
            "metrics": self.metrics.to_dict(),
            "feature_importance": [
                item.to_dict() for item in self.feature_importance
            ],
            "predictions": [
                item.to_dict() for item in self.predictions
            ],
            "recommendations": self.recommendations,
            "feature_columns": self.feature_columns,
            "feature_dtypes": self.feature_dtypes,
            "prediction_count": self.prediction_count,
            "feature_count": self.feature_count,
            "generated_at": self.generated_at.isoformat(),
            "model_comparison": [
                 item.to_dict() for item in self.model_comparison
             ],
        }
