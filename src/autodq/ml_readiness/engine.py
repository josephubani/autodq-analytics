import pandas as pd

from autodq.ml_readiness.models import MLReadinessIssue, MLReadinessReport


class MLReadinessEngine:
    """
    Evaluates whether a dataset is ready for machine learning.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        target: str | None = None,
        diagnosis_report=None,
        statistics_report=None,
        interpretation_report=None,
        correlation_report=None,
    ) -> MLReadinessReport:
        issues: list[MLReadinessIssue] = []
        strengths: list[str] = []

        score = 100.0

        rows, columns = df.shape

        if rows >= 1000:
            strengths.append("Dataset has enough rows for basic machine learning experimentation.")
        else:
            score -= 10
            issues.append(
                MLReadinessIssue(
                    issue_type="small_dataset",
                    severity="medium",
                    message=f"Dataset has only {rows} rows.",
                    recommendation="Use simpler models, cross-validation, or collect more data.",
                    confidence=0.85,
                )
            )

        missing_count = int(df.isna().sum().sum())
        if missing_count == 0:
            strengths.append("No missing values detected.")
        else:
            missing_ratio = missing_count / max(rows * columns, 1)
            penalty = min(20, missing_ratio * 100)
            score -= penalty
            issues.append(
                MLReadinessIssue(
                    issue_type="missing_values",
                    severity="medium" if missing_ratio < 0.1 else "high",
                    message=f"{missing_count} missing values detected.",
                    recommendation="Handle missing values before training models.",
                    confidence=0.95,
                )
            )

        duplicate_count = int(df.duplicated().sum())
        if duplicate_count == 0:
            strengths.append("No duplicate rows detected.")
        else:
            score -= min(10, duplicate_count / max(rows, 1) * 100)
            issues.append(
                MLReadinessIssue(
                    issue_type="duplicate_rows",
                    severity="medium",
                    message=f"{duplicate_count} duplicate row(s) detected.",
                    recommendation="Remove duplicates unless repeated records are valid events.",
                    confidence=0.9,
                )
            )

        numeric_columns = list(df.select_dtypes(include="number").columns)
        categorical_columns = list(df.select_dtypes(include=["object", "category", "string"]).columns)

        if numeric_columns:
            strengths.append(f"{len(numeric_columns)} numeric feature(s) available.")
        else:
            score -= 10
            issues.append(
                MLReadinessIssue(
                    issue_type="no_numeric_features",
                    severity="medium",
                    message="No numeric columns detected.",
                    recommendation="Encode categorical variables or add numeric features.",
                    confidence=0.85,
                )
            )

        if categorical_columns:
            strengths.append(f"{len(categorical_columns)} categorical/text feature(s) available.")
            issues.append(
                MLReadinessIssue(
                    issue_type="categorical_encoding_required",
                    severity="low",
                    message="Categorical columns must be encoded before most ML models.",
                    recommendation="Use one-hot encoding, ordinal encoding, target encoding, or embeddings depending on the model.",
                    confidence=0.9,
                )
            )

        target_type = self._target_type(df, target)
        recommended_task = self._recommended_task(target_type)
        recommended_models = self._recommended_models(target_type)

        if target is None:
            score -= 10
            issues.append(
                MLReadinessIssue(
                    issue_type="missing_target",
                    severity="medium",
                    message="No target column has been set.",
                    recommendation="Use project.set_target('column_name') for supervised machine learning.",
                    confidence=0.9,
                )
            )
        elif target not in df.columns:
            score -= 20
            issues.append(
                MLReadinessIssue(
                    issue_type="target_not_found",
                    severity="high",
                    message=f"Target column '{target}' was not found in the dataset.",
                    recommendation="Set a valid target column using project.set_target().",
                    confidence=0.95,
                )
            )
        else:
            strengths.append(f"Target column is set to '{target}'.")

        if correlation_report is not None:
            high_corr = [
                rel for rel in correlation_report.relationships
                if abs(rel.correlation) >= 0.9
            ]

            if high_corr:
                score -= min(12, len(high_corr) * 2)
                issues.append(
                    MLReadinessIssue(
                        issue_type="multicollinearity_risk",
                        severity="high",
                        message=f"{len(high_corr)} very strong feature relationship(s) detected.",
                        recommendation="Review highly correlated variables before linear modelling.",
                        confidence=0.9,
                    )
                )
            else:
                strengths.append("No severe multicollinearity detected from correlation intelligence.")

            target_leakage = [
                rel for rel in correlation_report.target_relationships
                if abs(rel.correlation) >= 0.95
            ]

            if target_leakage:
                score -= min(15, len(target_leakage) * 5)
                issues.append(
                    MLReadinessIssue(
                        issue_type="possible_target_leakage",
                        severity="high",
                        message=f"{len(target_leakage)} feature(s) are extremely correlated with the target.",
                        recommendation="Check whether these variables are derived from the target before modelling.",
                        confidence=0.9,
                    )
                )

        if interpretation_report is not None:
            high_skew_count = 0
            high_tail_count = 0

            insights = getattr(interpretation_report, "insights", [])

            for insight in insights:
                insight_type = getattr(insight, "insight_type", None)
                severity = getattr(insight, "severity", None)

                if insight_type == "skewness" and severity == "high":
                    high_skew_count += 1

                if insight_type == "heavy_tail" and severity == "high":
                    high_tail_count += 1

            if high_skew_count:
                score -= min(10, high_skew_count * 1.5)
                issues.append(
                    MLReadinessIssue(
                        issue_type="skewed_features",
                        severity="medium",
                        message=f"{high_skew_count} highly skewed numeric feature(s) detected.",
                        recommendation="Consider robust scaling, log transformation, or tree-based models.",
                        confidence=0.86,
                    )
                )

            if high_tail_count:
                score -= min(10, high_tail_count * 1.5)
                issues.append(
                    MLReadinessIssue(
                        issue_type="heavy_tailed_features",
                        severity="medium",
                        message=f"{high_tail_count} heavy-tailed feature(s) detected.",
                        recommendation="Review outliers and consider robust models or transformations.",
                        confidence=0.86,
                    )
                )

        score = round(max(0, min(100, score)), 2)

        return MLReadinessReport(
            score=score,
            target=target,
            target_type=target_type,
            recommended_task=recommended_task,
            recommended_models=recommended_models,
            issues=issues,
            strengths=strengths,
        )

    def _target_type(self, df: pd.DataFrame, target: str | None) -> str:
        if target is None or target not in df.columns:
            return "unknown"

        series = df[target]

        if pd.api.types.is_numeric_dtype(series):
            unique_count = series.nunique(dropna=True)

            if unique_count <= 10:
                return "numeric_discrete_or_classification"

            return "continuous_numeric"

        unique_count = series.nunique(dropna=True)

        if unique_count <= 20:
            return "categorical_classification"

        return "high_cardinality_text"

    def _recommended_task(self, target_type: str) -> str:
        if target_type == "continuous_numeric":
            return "regression"

        if target_type in ["categorical_classification", "numeric_discrete_or_classification"]:
            return "classification"

        if target_type == "unknown":
            return "unsupervised_or_set_target"

        return "review_target"

    def _recommended_models(self, target_type: str) -> list[str]:
        if target_type == "continuous_numeric":
            return [
                "Random Forest Regressor",
                "Gradient Boosting Regressor",
                "Linear Regression with preprocessing",
                "XGBoost/LightGBM Regressor",
            ]

        if target_type in ["categorical_classification", "numeric_discrete_or_classification"]:
            return [
                "Random Forest Classifier",
                "Gradient Boosting Classifier",
                "Logistic Regression with preprocessing",
                "XGBoost/LightGBM Classifier",
            ]

        return [
            "Clustering",
            "Anomaly Detection",
            "Dimensionality Reduction",
        ]