from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class ColumnStatistics:
    """
    Descriptive statistics for a single column.
    """

    column: str
    count: int
    missing: int
    missing_percent: float
    mean: float | None = None
    median: float | None = None
    mode: object | None = None
    minimum: float | None = None
    maximum: float | None = None
    variance: float | None = None
    std: float | None = None
    value_range: float | None = None
    iqr: float | None = None
    mad: float | None = None
    coefficient_variation: float | None = None
    skewness: float | None = None
    kurtosis: float | None = None

    def to_dict(self) -> dict:
        return {
            "column": self.column,
            "count": self.count,
            "missing": self.missing,
            "missing_percent": self.missing_percent,
            "mean": self.mean,
            "median": self.median,
            "mode": self.mode,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "variance": self.variance,
            "std": self.std,
            "value_range": self.value_range,
            "iqr": self.iqr,
            "mad": self.mad,
            "coefficient_variation": self.coefficient_variation,
            "skewness": self.skewness,
            "kurtosis": self.kurtosis,
        }


@dataclass(slots=True)
class DistributionInsight:
    """
    Interpretation of a column's statistical distribution.
    """

    column: str
    distribution_type: str
    skewness_level: str
    tail_risk: str
    explanation: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "column": self.column,
            "distribution_type": self.distribution_type,
            "skewness_level": self.skewness_level,
            "tail_risk": self.tail_risk,
            "explanation": self.explanation,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class StatisticsSummary:
    """
    Overall dataset statistical summary.
    """

    numeric_columns: int
    categorical_columns: int
    datetime_columns: int
    analyzed_columns: int

    def to_dict(self) -> dict:
        return {
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "datetime_columns": self.datetime_columns,
            "analyzed_columns": self.analyzed_columns,
        }


@dataclass(slots=True)
class StatisticsReport:
    """
    Complete Statistics Engine output.
    """

    descriptive: dict[str, ColumnStatistics] = field(default_factory=dict)
    distributions: dict[str, DistributionInsight] = field(default_factory=dict)
    summary: StatisticsSummary | None = None
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "descriptive": {
                column: item.to_dict()
                for column, item in self.descriptive.items()
            },
            "distributions": {
                column: item.to_dict()
                for column, item in self.distributions.items()
            },
            "summary": (
                self.summary.to_dict()
                if self.summary is not None
                else None
            ),
            "generated_at": self.generated_at.isoformat(),
        }
