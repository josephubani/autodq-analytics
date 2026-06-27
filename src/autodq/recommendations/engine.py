from autodq.knowledge.engine import KnowledgeEngine
from autodq.models.recommendations import CleaningRecommendation
from autodq.models.reports import DiagnosisReport


class RecommendationEngine:
    """
    Generates evidence-aware cleaning recommendations.

    Evidence sources:
    - Diagnosis Report
    - Knowledge Engine
    - Statistics Report
    - Interpretation Report
    """

    def __init__(self, knowledge_engine: KnowledgeEngine | None = None):
        self.knowledge_engine = knowledge_engine or KnowledgeEngine()

    def recommend(
        self,
        diagnosis_report: DiagnosisReport,
        statistics_report=None,
        interpretation_report=None,
    ) -> list[CleaningRecommendation]:
        recommendations = []

        for issue in diagnosis_report.issues:
            if issue.issue_type == "missing_values":
                recommendations.extend(
                    self._recommend_missing_values(
                        issue=issue,
                        statistics_report=statistics_report,
                        interpretation_report=interpretation_report,
                    )
                )

            elif issue.issue_type == "duplicate_rows":
                recommendations.append(self._recommend_duplicates(issue))

            elif issue.issue_type == "outliers":
                recommendations.extend(
                    self._recommend_outliers(
                        issue=issue,
                        statistics_report=statistics_report,
                        interpretation_report=interpretation_report,
                    )
                )

        return recommendations

    def _recommend_missing_values(
        self,
        issue,
        statistics_report=None,
        interpretation_report=None,
    ) -> list[CleaningRecommendation]:
        recommendations = []

        for column in issue.affected_columns:
            rule = self.knowledge_engine.get_rule(column)
            column_stats = self._get_column_stats(statistics_report, column)
            column_insights = self._get_column_insights(interpretation_report, column)

            strategy = self._select_missing_strategy(
                column=column,
                rule=rule,
                column_stats=column_stats,
                column_insights=column_insights,
            )

            evidence = self._build_missing_evidence(
                column=column,
                rule=rule,
                column_stats=column_stats,
                column_insights=column_insights,
            )

            confidence = self._fuse_confidence(
                base=0.7,
                has_rule=rule is not None,
                has_stats=column_stats is not None,
                insight_count=len(column_insights),
            )

            recommendations.append(
                CleaningRecommendation(
                    issue_type="missing_values",
                    strategy=strategy,
                    action=f"Apply {strategy} strategy to {column}.",
                    affected_columns=[column],
                    reason=" ".join(evidence),
                    priority=issue.severity,
                    risk="Incorrect imputation may introduce bias or distort the distribution.",
                    confidence=confidence,
                )
            )

        return recommendations

    def _recommend_duplicates(self, issue) -> CleaningRecommendation:
        return CleaningRecommendation(
            issue_type="duplicate_rows",
            strategy="remove_exact_duplicates",
            action="Remove exact duplicate rows unless repeated records are valid business events.",
            affected_columns=[],
            reason=(
                "Diagnosis detected exact duplicate rows. "
                "Exact duplicates can inflate counts, distort totals, and bias analysis."
            ),
            priority=issue.severity,
            risk="If duplicates represent valid repeated events, removing them may lose information.",
            confidence=0.92,
        )

    def _recommend_outliers(
        self,
        issue,
        statistics_report=None,
        interpretation_report=None,
    ) -> list[CleaningRecommendation]:
        recommendations = []

        for column in issue.affected_columns:
            rule = self.knowledge_engine.get_rule(column)
            column_stats = self._get_column_stats(statistics_report, column)
            column_insights = self._get_column_insights(interpretation_report, column)

            if rule and rule.preferred_outlier_strategy:
                strategy = rule.preferred_outlier_strategy
            else:
                strategy = "review_or_treat_outliers"

            evidence = self._build_outlier_evidence(
                column=column,
                rule=rule,
                column_stats=column_stats,
                column_insights=column_insights,
            )

            confidence = self._fuse_confidence(
                base=0.68,
                has_rule=rule is not None,
                has_stats=column_stats is not None,
                insight_count=len(column_insights),
            )

            recommendations.append(
                CleaningRecommendation(
                    issue_type="outliers",
                    strategy=strategy,
                    action=f"Review {column} and consider {strategy}.",
                    affected_columns=[column],
                    reason=" ".join(evidence),
                    priority=issue.severity,
                    risk="Some outliers may be valid extreme values and should not be removed blindly.",
                    confidence=confidence,
                )
            )

        return recommendations

    def _select_missing_strategy(
        self,
        column: str,
        rule,
        column_stats,
        column_insights: list,
    ) -> str:
        if rule and rule.preferred_imputation:
            return rule.preferred_imputation

        has_skewness = self._has_insight(column_insights, "skewness")
        has_heavy_tail = self._has_insight(column_insights, "heavy_tail")

        if column_stats and (has_skewness or has_heavy_tail):
            return "median"

        if column_stats:
            return "mean"

        return "review_missing_values"

    def _build_missing_evidence(
        self,
        column: str,
        rule,
        column_stats,
        column_insights: list,
    ) -> list[str]:
        evidence = []

        evidence.append(f"Diagnosis detected missing values in {column}.")

        if rule and rule.preferred_imputation:
            evidence.append(
                f"Knowledge rule '{rule.name}' recommends {rule.preferred_imputation} imputation."
            )

        if column_stats is not None:
            evidence.append(
                f"Statistics show mean={round(column_stats.mean, 4) if column_stats.mean is not None else 'N/A'} "
                f"and median={round(column_stats.median, 4) if column_stats.median is not None else 'N/A'}."
            )

        for insight in column_insights:
            if insight.insight_type in ["skewness", "mean_median_gap", "heavy_tail"]:
                evidence.append(
                    f"Interpretation: {insight.message}"
                )

        if not evidence:
            evidence.append(
                f"No strong statistical or knowledge evidence found for {column}; manual review is recommended."
            )

        return evidence

    def _build_outlier_evidence(
        self,
        column: str,
        rule,
        column_stats,
        column_insights: list,
    ) -> list[str]:
        evidence = []

        evidence.append(f"Diagnosis detected outlier behavior in {column}.")

        if rule and rule.preferred_outlier_strategy:
            evidence.append(
                f"Knowledge rule '{rule.name}' recommends {rule.preferred_outlier_strategy}."
            )

        if column_stats is not None:
            evidence.append(
                f"Statistics show skewness={round(column_stats.skewness, 4) if column_stats.skewness is not None else 'N/A'} "
                f"and kurtosis={round(column_stats.kurtosis, 4) if column_stats.kurtosis is not None else 'N/A'}."
            )

        for insight in column_insights:
            if insight.insight_type in ["skewness", "heavy_tail", "high_variability"]:
                evidence.append(
                    f"Interpretation: {insight.message}"
                )

        return evidence

    def _get_column_stats(self, statistics_report, column: str):
        if statistics_report is None:
            return None

        return statistics_report.descriptive.get(column)

    def _get_column_insights(self, interpretation_report, column: str) -> list:
        if interpretation_report is None:
            return []

        return interpretation_report.interpretations.get(column, [])

    def _has_insight(self, insights: list, insight_type: str) -> bool:
        return any(insight.insight_type == insight_type for insight in insights)

    def _fuse_confidence(
        self,
        base: float,
        has_rule: bool,
        has_stats: bool,
        insight_count: int,
    ) -> float:
        confidence = base

        if has_rule:
            confidence += 0.1

        if has_stats:
            confidence += 0.08

        if insight_count > 0:
            confidence += min(0.1, insight_count * 0.03)

        return round(min(confidence, 0.97), 2)