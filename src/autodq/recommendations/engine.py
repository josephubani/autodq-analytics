from autodq.knowledge.engine import KnowledgeEngine
from autodq.models.recommendations import CleaningRecommendation
from autodq.models.reports import DiagnosisReport


class RecommendationEngine:
    """
    Generates cleaning recommendations from a DiagnosisReport,
    enhanced with Knowledge Engine rules.
    """

    def __init__(self, knowledge_engine: KnowledgeEngine | None = None):
        self.knowledge_engine = knowledge_engine or KnowledgeEngine()

    def recommend(self, diagnosis_report: DiagnosisReport) -> list[CleaningRecommendation]:
        recommendations = []

        for issue in diagnosis_report.issues:
            if issue.issue_type == "missing_values":
                recommendations.extend(self._recommend_missing_values(issue))

            elif issue.issue_type == "duplicate_rows":
                recommendations.append(self._recommend_duplicates(issue))

            elif issue.issue_type == "outliers":
                recommendations.extend(self._recommend_outliers(issue))

        return recommendations

    def _recommend_missing_values(self, issue) -> list[CleaningRecommendation]:
        recommendations = []

        for column in issue.affected_columns:
            rule = self.knowledge_engine.get_rule(column)

            if rule and rule.preferred_imputation:
                strategy = rule.preferred_imputation
                reason = (
                    f"{column} matches knowledge rule '{rule.name}'. "
                    f"Preferred imputation is {strategy}."
                )
            else:
                strategy = "review_missing_values"
                reason = (
                    f"No specific knowledge rule found for {column}. "
                    "Review column type and missingness before imputing."
                )

            recommendations.append(
                CleaningRecommendation(
                    issue_type="missing_values",
                    strategy=strategy,
                    action=f"Apply {strategy} strategy to {column}.",
                    affected_columns=[column],
                    reason=reason,
                    priority=issue.severity,
                    risk="Incorrect imputation may introduce bias or distort the distribution.",
                    confidence=0.88 if rule else 0.7,
                )
            )

        return recommendations

    def _recommend_duplicates(self, issue) -> CleaningRecommendation:
        return CleaningRecommendation(
            issue_type="duplicate_rows",
            strategy="remove_exact_duplicates",
            action="Remove exact duplicate rows unless repeated records are valid business events.",
            affected_columns=[],
            reason="Exact duplicate records can inflate counts, distort totals, and bias analysis.",
            priority=issue.severity,
            risk="If duplicates represent valid repeated events, removing them may lose information.",
            confidence=0.92,
        )

    def _recommend_outliers(self, issue) -> list[CleaningRecommendation]:
        recommendations = []

        for column in issue.affected_columns:
            rule = self.knowledge_engine.get_rule(column)

            if rule and rule.preferred_outlier_strategy:
                strategy = rule.preferred_outlier_strategy
                reason = (
                    f"{column} matches knowledge rule '{rule.name}'. "
                    f"Preferred outlier strategy is {strategy}."
                )
            else:
                strategy = "review_or_treat_outliers"
                reason = (
                    f"No specific knowledge rule found for {column}. "
                    "Use statistical and domain review before treating outliers."
                )

            recommendations.append(
                CleaningRecommendation(
                    issue_type="outliers",
                    strategy=strategy,
                    action=f"Review {column} and consider {strategy}.",
                    affected_columns=[column],
                    reason=reason,
                    priority=issue.severity,
                    risk="Some outliers may be valid extreme values and should not be removed blindly.",
                    confidence=0.86 if rule else 0.72,
                )
            )

        return recommendations