from autodq.models.recommendations import CleaningRecommendation
from autodq.models.reports import DiagnosisReport


class RecommendationEngine:
    """
    Generates cleaning recommendations from a DiagnosisReport.
    """

    def recommend(self, diagnosis_report: DiagnosisReport) -> list[CleaningRecommendation]:
        recommendations = []

        for issue in diagnosis_report.issues:
            if issue.issue_type == "missing_values":
                recommendations.append(
                    CleaningRecommendation(
                        issue_type="missing_values",
                        strategy="column_specific_imputation",
                        action="Review each affected column and apply mean, median, mode, or removal based on type and missingness severity.",
                        affected_columns=issue.affected_columns,
                        reason="Missing values can reduce model accuracy and distort summaries if not handled correctly.",
                        priority=issue.severity,
                        risk="Wrong imputation may introduce bias or reduce variance.",
                        confidence=0.9,
                    )
                )

            elif issue.issue_type == "duplicate_rows":
                recommendations.append(
                    CleaningRecommendation(
                        issue_type="duplicate_rows",
                        strategy="remove_exact_duplicates",
                        action="Remove exact duplicate rows unless repeated records are valid business events.",
                        affected_columns=[],
                        reason="Exact duplicate records can inflate counts, distort totals, and bias analysis.",
                        priority=issue.severity,
                        risk="If duplicates represent valid repeated events, removing them may lose information.",
                        confidence=0.92,
                    )
                )

            elif issue.issue_type == "outliers":
                recommendations.append(
                    CleaningRecommendation(
                        issue_type="outliers",
                        strategy="review_or_treat_outliers",
                        action="Review outlier columns and consider IQR clipping, winsorization, log transformation, or domain-based validation.",
                        affected_columns=issue.affected_columns,
                        reason="Outliers can distort averages, regression coefficients, visualizations, and model performance.",
                        priority=issue.severity,
                        risk="Some outliers may be valid extreme business events and should not be removed blindly.",
                        confidence=0.85,
                    )
                )

        return recommendations