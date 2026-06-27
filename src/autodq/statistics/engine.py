import pandas as pd

from autodq.statistics.descriptive import DescriptiveStatisticsEngine
from autodq.statistics.distribution import DistributionEngine
from autodq.statistics.models import StatisticsReport, StatisticsSummary


class StatisticsEngine:
    """
    Coordinates statistical analysis for AutoDQ.
    """

    def __init__(self):
        self.descriptive_engine = DescriptiveStatisticsEngine()
        self.distribution_engine = DistributionEngine()

    def analyze(self, df: pd.DataFrame) -> StatisticsReport:
        report = StatisticsReport()

        report.descriptive = self.descriptive_engine.analyze(df)

        report.distributions = self.distribution_engine.analyze(
            report.descriptive
        )

        report.summary = StatisticsSummary(
            numeric_columns=len(df.select_dtypes(include="number").columns),
            categorical_columns=len(
                df.select_dtypes(include=["object", "category"]).columns
            ),
            datetime_columns=len(df.select_dtypes(include="datetime").columns),
            analyzed_columns=len(df.columns),
        )

        return report