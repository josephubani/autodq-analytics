from autodq.statistics.models import ColumnStatistics, DistributionInsight


class DistributionEngine:
    """
    Interprets numeric column distributions using descriptive statistics.
    """

    def analyze(
        self,
        descriptive_stats: dict[str, ColumnStatistics],
    ) -> dict[str, DistributionInsight]:

        results = {}

        for column, stats in descriptive_stats.items():
            skewness = stats.skewness
            kurtosis = stats.kurtosis

            if skewness is None:
                continue

            skewness_level = self._classify_skewness(skewness)
            tail_risk = self._classify_tail_risk(kurtosis)
            distribution_type = self._classify_distribution(skewness, kurtosis)

            results[column] = DistributionInsight(
                column=column,
                distribution_type=distribution_type,
                skewness_level=skewness_level,
                tail_risk=tail_risk,
                explanation=self._build_explanation(
                    column=column,
                    skewness=skewness,
                    kurtosis=kurtosis,
                    skewness_level=skewness_level,
                    tail_risk=tail_risk,
                    distribution_type=distribution_type,
                ),
                confidence=self._estimate_confidence(skewness, kurtosis),
            )

        return results

    def _classify_skewness(self, skewness: float) -> str:
        if abs(skewness) < 0.5:
            return "approximately_symmetric"

        if 0.5 <= skewness < 1:
            return "moderately_right_skewed"

        if skewness >= 1:
            return "highly_right_skewed"

        if -1 < skewness <= -0.5:
            return "moderately_left_skewed"

        return "highly_left_skewed"

    def _classify_tail_risk(self, kurtosis: float | None) -> str:
        if kurtosis is None:
            return "unknown"

        if kurtosis < 1:
            return "low_tail_risk"

        if kurtosis < 3:
            return "moderate_tail_risk"

        return "high_tail_risk"

    def _classify_distribution(
        self,
        skewness: float,
        kurtosis: float | None,
    ) -> str:
        if abs(skewness) < 0.5 and (kurtosis is None or abs(kurtosis) < 1):
            return "approximately_normal"

        if skewness >= 1:
            return "right_skewed_distribution"

        if skewness <= -1:
            return "left_skewed_distribution"

        if kurtosis is not None and kurtosis >= 3:
            return "heavy_tailed_distribution"

        return "non_normal_distribution"

    def _build_explanation(
        self,
        column: str,
        skewness: float,
        kurtosis: float | None,
        skewness_level: str,
        tail_risk: str,
        distribution_type: str,
    ) -> str:
        return (
            f"{column} appears to follow a {distribution_type}. "
            f"Skewness is {round(skewness, 3)}, indicating {skewness_level}. "
            f"Kurtosis is {round(kurtosis, 3) if kurtosis is not None else 'unknown'}, "
            f"suggesting {tail_risk}."
        )

    def _estimate_confidence(
        self,
        skewness: float,
        kurtosis: float | None,
    ) -> float:
        confidence = 0.75

        if abs(skewness) >= 1:
            confidence += 0.12

        if kurtosis is not None and abs(kurtosis) >= 3:
            confidence += 0.08

        return round(min(confidence, 0.95), 2)