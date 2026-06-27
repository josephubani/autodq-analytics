from autodq.interpretation.models import InterpretationReport
from autodq.interpretation.statistics import StatisticalInterpretationEngine
from autodq.statistics.models import StatisticsReport


class InterpretationEngine:
    """
    Coordinates interpretation of AutoDQ reports.
    """

    def __init__(self):
        self.statistical_engine = StatisticalInterpretationEngine()

    def interpret_statistics(
        self,
        statistics_report: StatisticsReport,
    ) -> InterpretationReport:

        report = InterpretationReport()

        for column, stats in statistics_report.descriptive.items():
            distribution = statistics_report.distributions.get(column)

            insights = self.statistical_engine.interpret_column(
                stats=stats,
                distribution=distribution,
            )

            if insights:
                report.interpretations[column] = insights

        return report