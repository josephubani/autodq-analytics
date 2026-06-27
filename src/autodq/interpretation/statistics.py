from autodq.interpretation.models import StatisticalInterpretation
from autodq.statistics.models import ColumnStatistics, DistributionInsight


class StatisticalInterpretationEngine:
    """
    Converts raw statistics into explainable insights.
    """

    def interpret_column(
        self,
        stats: ColumnStatistics,
        distribution: DistributionInsight | None = None,
    ) -> list[StatisticalInterpretation]:

        insights = []

        if stats.mean is not None and stats.median is not None:
            insights.extend(self._interpret_mean_median_gap(stats))

        if stats.skewness is not None:
            insights.extend(self._interpret_skewness(stats, distribution))

        if stats.kurtosis is not None:
            insights.extend(self._interpret_kurtosis(stats))

        if stats.coefficient_variation is not None:
            insights.extend(self._interpret_variability(stats))

        return insights

    def _interpret_mean_median_gap(
        self,
        stats: ColumnStatistics,
    ) -> list[StatisticalInterpretation]:

        if stats.median == 0:
            return []

        gap = stats.mean - stats.median
        relative_gap = abs(gap / stats.median)

        if relative_gap < 0.25:
            return []

        direction = "above" if gap > 0 else "below"

        return [
            StatisticalInterpretation(
                column=stats.column,
                insight_type="mean_median_gap",
                severity="medium" if relative_gap < 1 else "high",
                message=(
                    f"The mean is substantially {direction} the median, "
                    "suggesting an asymmetric distribution."
                ),
                evidence=[
                    f"Mean = {round(stats.mean, 4)}",
                    f"Median = {round(stats.median, 4)}",
                    f"Relative gap = {round(relative_gap * 100, 2)}%",
                ],
                downstream_implications=[
                    "Mean-based summaries may be misleading.",
                    "Median may be more robust for imputation.",
                    "Distribution-sensitive models may require transformation.",
                ],
                confidence=0.85,
            )
        ]

    def _interpret_skewness(
        self,
        stats: ColumnStatistics,
        distribution: DistributionInsight | None,
    ) -> list[StatisticalInterpretation]:

        skewness = stats.skewness

        if abs(skewness) < 0.5:
            return []

        severity = "medium" if abs(skewness) < 1 else "high"

        if skewness > 0:
            direction = "right-skewed"
            implication = "Large values may be pulling the mean upward."
        else:
            direction = "left-skewed"
            implication = "Small values may be pulling the mean downward."

        evidence = [f"Skewness = {round(skewness, 4)}"]

        if distribution is not None:
            evidence.append(f"Distribution type = {distribution.distribution_type}")

        return [
            StatisticalInterpretation(
                column=stats.column,
                insight_type="skewness",
                severity=severity,
                message=f"{stats.column} appears {direction}. {implication}",
                evidence=evidence,
                downstream_implications=[
                    "Median is preferred over mean for imputation.",
                    "Consider transformation before linear modeling.",
                    "Pearson correlation may be less reliable.",
                    "Outlier review is recommended.",
                ],
                confidence=0.9 if abs(skewness) >= 1 else 0.8,
            )
        ]

    def _interpret_kurtosis(
        self,
        stats: ColumnStatistics,
    ) -> list[StatisticalInterpretation]:

        kurtosis = stats.kurtosis

        if kurtosis < 3:
            return []

        return [
            StatisticalInterpretation(
                column=stats.column,
                insight_type="heavy_tail",
                severity="high",
                message=(
                    f"{stats.column} has heavy-tailed behavior, suggesting "
                    "extreme values may strongly influence analysis."
                ),
                evidence=[f"Kurtosis = {round(kurtosis, 4)}"],
                downstream_implications=[
                    "Outlier treatment should be reviewed carefully.",
                    "Robust statistics may be preferred.",
                    "Linear model assumptions may be weakened.",
                ],
                confidence=0.9,
            )
        ]

    def _interpret_variability(
        self,
        stats: ColumnStatistics,
    ) -> list[StatisticalInterpretation]:

        cv = stats.coefficient_variation

        if cv is None or cv < 1:
            return []

        return [
            StatisticalInterpretation(
                column=stats.column,
                insight_type="high_variability",
                severity="medium" if cv < 2 else "high",
                message=(
                    f"{stats.column} has high relative variability compared "
                    "with its mean."
                ),
                evidence=[f"Coefficient of variation = {round(cv, 4)}"],
                downstream_implications=[
                    "Scaling may be useful before modeling.",
                    "Extreme values may influence summaries.",
                    "Variance-sensitive models may require preprocessing.",
                ],
                confidence=0.82,
            )
        ]