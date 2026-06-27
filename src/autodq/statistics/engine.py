import pandas as pd

from autodq.statistics.descriptive import (
    DescriptiveStatisticsEngine,
)

from autodq.statistics.models import (
    StatisticsReport,
    StatisticsSummary,
)


class StatisticsEngine:

    def __init__(self):

        self.descriptive_engine = (
            DescriptiveStatisticsEngine()
        )

    def analyze(
        self,
        df: pd.DataFrame,
    ) -> StatisticsReport:

        report = StatisticsReport()

        report.descriptive = (
            self.descriptive_engine.analyze(df)
        )

        report.summary = StatisticsSummary(

            numeric_columns=len(
                df.select_dtypes(
                    include="number"
                ).columns
            ),

            categorical_columns=len(
                df.select_dtypes(
                    include=["object", "category"]
                ).columns
            ),

            datetime_columns=len(
                df.select_dtypes(
                    include="datetime"
                ).columns
            ),

            analyzed_columns=len(df.columns),
        )

        return report