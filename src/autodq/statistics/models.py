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


@dataclass(slots=True)
class StatisticsSummary:
    """
    Overall dataset statistical summary.
    """

    numeric_columns: int

    categorical_columns: int

    datetime_columns: int

    analyzed_columns: int


@dataclass(slots=True)
class StatisticsReport:
    """
    Complete Statistics Engine output.
    """

    descriptive: dict[str, ColumnStatistics] = field(default_factory=dict)

    summary: StatisticsSummary | None = None

    generated_at: datetime = field(default_factory=datetime.now)