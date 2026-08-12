from __future__ import annotations

import numpy as np
import pandas as pd

from autodq.ml_readiness.models import (
    MLReadinessComponent,
    MLReadinessIssue,
    MLReadinessReport,
)


class MLReadinessEngine:
    """Evaluate ML readiness through transparent weighted components."""

    TOTAL_POINTS = 100.0
    COMPONENT_WEIGHTS = {
        "sample_sufficiency": 10.0,
        "data_quality": 25.0,
        "feature_readiness": 15.0,
        "target_readiness": 15.0,
        "leakage_safety": 15.0,
        "multicollinearity": 10.0,
        "feature_stability": 10.0,
    }

    def analyze(
        self,
        df: pd.DataFrame,
        target: str | None = None,
        diagnosis_report=None,
        statistics_report=None,
        interpretation_report=None,
        correlation_report=None,
        reference_df: pd.DataFrame | None = None,
        reference_name: str | None = None,
    ) -> MLReadinessReport:
        del statistics_report, correlation_report  # Public compatibility inputs.

        if not isinstance(df, pd.DataFrame):
            raise TypeError("ML readiness requires a pandas DataFrame.")

        issues: list[MLReadinessIssue] = []
        strengths: list[str] = []
        rows, columns = df.shape
        numeric_columns = list(df.select_dtypes(include="number").columns)
        categorical_columns = list(
            df.select_dtypes(include=["object", "category", "string"]).columns
        )
        high_skew_count, high_tail_count = self._interpretation_counts(
            interpretation_report
        )

        components = [
            self._sample_component(rows, issues, strengths),
            self._quality_component(
                df,
                diagnosis_report=diagnosis_report,
                issues=issues,
                strengths=strengths,
            ),
            self._feature_component(
                rows=rows,
                columns=columns,
                numeric_columns=numeric_columns,
                categorical_columns=categorical_columns,
                high_skew_count=high_skew_count,
                high_tail_count=high_tail_count,
                issues=issues,
                strengths=strengths,
            ),
            self._target_component(df, target, issues, strengths),
            self._leakage_component(df, target, issues, strengths),
            self._multicollinearity_component(
                df,
                target,
                issues,
                strengths,
            ),
            self._stability_component(
                df,
                reference_df=reference_df,
                reference_name=reference_name,
                target=target,
                issues=issues,
                strengths=strengths,
            ),
        ]

        earned_points = round(
            sum(component.score for component in components if component.assessed),
            2,
        )
        assessed_points = round(
            sum(
                component.max_score
                for component in components
                if component.assessed
            ),
            2,
        )
        score = round(
            earned_points / assessed_points * 100
            if assessed_points
            else 0.0,
            2,
        )
        assessment_coverage = round(
            assessed_points / self.TOTAL_POINTS * 100,
            2,
        )
        target_type = self._target_type(df, target)

        return MLReadinessReport(
            score=score,
            target=target,
            target_type=target_type,
            recommended_task=self._recommended_task(target_type),
            recommended_models=self._recommended_models(target_type),
            issues=issues,
            strengths=strengths,
            components=components,
            earned_points=earned_points,
            assessed_points=assessed_points,
            total_points=self.TOTAL_POINTS,
            assessment_coverage=assessment_coverage,
            reference_name=reference_name,
        )

    def _sample_component(
        self,
        rows: int,
        issues: list[MLReadinessIssue],
        strengths: list[str],
    ) -> MLReadinessComponent:
        maximum = self.COMPONENT_WEIGHTS["sample_sufficiency"]
        if rows >= 1_000:
            score = maximum
        elif rows >= 500:
            score = 8.0
        elif rows >= 250:
            score = 6.0
        elif rows >= 100:
            score = 4.0
        elif rows >= 50:
            score = 2.0
        else:
            score = 0.0

        deductions = []
        if score == maximum:
            strengths.append(
                "Dataset has enough rows for basic machine learning experimentation."
            )
        else:
            deduction = maximum - score
            deductions.append(
                f"{deduction:.2f} point(s): {rows:,} rows is below the "
                "1,000-row full-credit threshold."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="small_dataset",
                    severity="medium" if rows < 250 else "low",
                    message=f"Dataset has only {rows:,} rows.",
                    recommendation=(
                        "Use simpler models, repeated cross-validation, or collect "
                        "more representative data."
                    ),
                    confidence=0.85,
                )
            )

        return self._component(
            key="sample_sufficiency",
            name="Sample sufficiency",
            score=score,
            maximum=maximum,
            summary=f"{rows:,} rows; full credit begins at 1,000 rows.",
            deductions=deductions,
            metrics={"row_count": rows, "full_credit_rows": 1_000},
            recommendation=(
                "Increase the representative sample size or use validation suited "
                "to small datasets."
                if score < maximum
                else None
            ),
        )

    def _quality_component(
        self,
        df: pd.DataFrame,
        *,
        diagnosis_report,
        issues: list[MLReadinessIssue],
        strengths: list[str],
    ) -> MLReadinessComponent:
        maximum = self.COMPONENT_WEIGHTS["data_quality"]
        rows, columns = df.shape
        total_cells = max(rows * columns, 1)
        missing_count = int(df.isna().sum().sum())
        duplicate_count = int(df.duplicated().sum())
        missing_percentage = missing_count / total_cells * 100
        duplicate_percentage = duplicate_count / max(rows, 1) * 100
        missing_deduction = min(18.0, missing_percentage)
        duplicate_deduction = min(7.0, duplicate_percentage)
        score = maximum - missing_deduction - duplicate_deduction
        deductions = []

        if missing_count:
            deductions.append(
                f"{missing_deduction:.2f} point(s): {missing_count:,} missing "
                f"cell(s), or {missing_percentage:.2f}% of all cells."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="missing_values",
                    severity="medium" if missing_percentage < 10 else "high",
                    message=f"{missing_count:,} missing values detected.",
                    recommendation="Handle missing values before training models.",
                    confidence=0.95,
                )
            )
        else:
            strengths.append("No missing values detected.")

        if duplicate_count:
            deductions.append(
                f"{duplicate_deduction:.2f} point(s): {duplicate_count:,} exact "
                f"duplicate row(s), or {duplicate_percentage:.2f}% of rows."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="duplicate_rows",
                    severity="medium",
                    message=f"{duplicate_count:,} duplicate row(s) detected.",
                    recommendation=(
                        "Remove duplicates unless repeated records are valid events."
                    ),
                    confidence=0.9,
                )
            )
        else:
            strengths.append("No duplicate rows detected.")

        diagnosis_score = getattr(diagnosis_report, "quality_score", None)
        return self._component(
            key="data_quality",
            name="Data quality",
            score=score,
            maximum=maximum,
            summary=(
                "25 points minus missing-cell deductions (up to 18) and "
                "exact-duplicate deductions (up to 7)."
            ),
            deductions=deductions,
            metrics={
                "missing_cells": missing_count,
                "missing_percent": round(missing_percentage, 4),
                "duplicate_rows": duplicate_count,
                "duplicate_percent": round(duplicate_percentage, 4),
                "diagnosis_quality_score": diagnosis_score,
            },
            recommendation=(
                "Resolve material missingness and verify whether duplicate events "
                "are legitimate before modelling."
                if deductions
                else None
            ),
        )

    def _feature_component(
        self,
        *,
        rows: int,
        columns: int,
        numeric_columns: list[str],
        categorical_columns: list[str],
        high_skew_count: int,
        high_tail_count: int,
        issues: list[MLReadinessIssue],
        strengths: list[str],
    ) -> MLReadinessComponent:
        maximum = self.COMPONENT_WEIGHTS["feature_readiness"]
        no_numeric_deduction = 0.0 if numeric_columns else 8.0
        skew_deduction = min(4.0, high_skew_count * 1.0)
        tail_deduction = min(3.0, high_tail_count * 1.0)
        score = maximum - no_numeric_deduction - skew_deduction - tail_deduction
        deductions = []

        if numeric_columns:
            strengths.append(f"{len(numeric_columns)} numeric feature(s) available.")
        else:
            deductions.append("8.00 point(s): no numeric features are available.")
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
            strengths.append(
                f"{len(categorical_columns)} categorical/text feature(s) available."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="categorical_encoding_required",
                    severity="low",
                    message="Categorical columns require model-appropriate encoding.",
                    recommendation=(
                        "Use one-hot, ordinal, target, or embedding-based encoding "
                        "according to the model and feature meaning."
                    ),
                    confidence=0.9,
                )
            )

        if high_skew_count:
            deductions.append(
                f"{skew_deduction:.2f} point(s): {high_skew_count} highly "
                "skewed numeric feature(s)."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="skewed_features",
                    severity="medium",
                    message=(
                        f"{high_skew_count} highly skewed numeric feature(s) detected."
                    ),
                    recommendation=(
                        "Consider robust scaling, transformations, or tree-based models."
                    ),
                    confidence=0.86,
                )
            )

        if high_tail_count:
            deductions.append(
                f"{tail_deduction:.2f} point(s): {high_tail_count} heavy-tailed "
                "numeric feature(s)."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="heavy_tailed_features",
                    severity="medium",
                    message=(
                        f"{high_tail_count} heavy-tailed feature(s) detected."
                    ),
                    recommendation=(
                        "Review outliers and consider robust models or transformations."
                    ),
                    confidence=0.86,
                )
            )

        return self._component(
            key="feature_readiness",
            name="Feature readiness",
            score=score,
            maximum=maximum,
            summary=(
                "15 points minus numeric-availability (up to 8), skew (up to 4), "
                "and heavy-tail (up to 3) deductions."
            ),
            deductions=deductions,
            metrics={
                "row_count": rows,
                "column_count": columns,
                "numeric_features": len(numeric_columns),
                "categorical_features": len(categorical_columns),
                "high_skew_features": high_skew_count,
                "heavy_tailed_features": high_tail_count,
            },
            recommendation=(
                "Transform unstable distributions and define a reproducible "
                "categorical encoding strategy."
                if deductions
                else None
            ),
        )

    def _target_component(
        self,
        df: pd.DataFrame,
        target: str | None,
        issues: list[MLReadinessIssue],
        strengths: list[str],
    ) -> MLReadinessComponent:
        maximum = self.COMPONENT_WEIGHTS["target_readiness"]
        deductions = []
        metrics = {"target": target}

        if target is None:
            score = 5.0
            deductions.append(
                "10.00 point(s): no supervised-learning target is configured."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="missing_target",
                    severity="medium",
                    message="No target column has been set.",
                    recommendation=(
                        "Set a target for supervised learning, or treat this as an "
                        "unsupervised workflow."
                    ),
                    confidence=0.9,
                )
            )
            summary = (
                "5 of 15 points retained because unsupervised modelling remains "
                "possible without a target."
            )
        elif target not in df.columns:
            score = 0.0
            deductions.append(
                f"15.00 point(s): target column {target!r} was not found."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="target_not_found",
                    severity="high",
                    message=f"Target column '{target}' was not found in the dataset.",
                    recommendation="Set a valid target column before modelling.",
                    confidence=0.95,
                )
            )
            summary = "No target-readiness points awarded because the target is invalid."
        else:
            target_series = df[target]
            target_missing = int(target_series.isna().sum())
            target_missing_percent = target_missing / max(len(target_series), 1) * 100
            unique_count = int(target_series.nunique(dropna=True))
            missing_deduction = min(5.0, target_missing_percent / 2)
            constant_deduction = 10.0 if unique_count < 2 else 0.0
            score = maximum - missing_deduction - constant_deduction
            metrics.update(
                {
                    "target_missing": target_missing,
                    "target_missing_percent": round(target_missing_percent, 4),
                    "target_unique_values": unique_count,
                }
            )
            strengths.append(f"Target column is set to '{target}'.")

            if target_missing:
                deductions.append(
                    f"{missing_deduction:.2f} point(s): {target_missing:,} target "
                    f"value(s) are missing ({target_missing_percent:.2f}%)."
                )
                issues.append(
                    MLReadinessIssue(
                        issue_type="missing_target_values",
                        severity="high" if target_missing_percent >= 10 else "medium",
                        message=f"{target_missing:,} target values are missing.",
                        recommendation=(
                            "Exclude unlabeled rows from supervised training or obtain "
                            "reliable labels."
                        ),
                        confidence=0.95,
                    )
                )

            if unique_count < 2:
                deductions.append(
                    "10.00 point(s): the target has fewer than two observed values."
                )
                issues.append(
                    MLReadinessIssue(
                        issue_type="constant_target",
                        severity="high",
                        message="The target does not vary across observed rows.",
                        recommendation="Choose a target with meaningful variation.",
                        confidence=0.98,
                    )
                )

            summary = (
                "15 points minus target missingness (up to 5) and a 10-point "
                "constant-target deduction."
            )

        return self._component(
            key="target_readiness",
            name="Target readiness",
            score=score,
            maximum=maximum,
            summary=summary,
            deductions=deductions,
            metrics=metrics,
            recommendation=(
                "Set and validate a complete, varying target for supervised learning."
                if deductions
                else None
            ),
        )

    def _leakage_component(
        self,
        df: pd.DataFrame,
        target: str | None,
        issues: list[MLReadinessIssue],
        strengths: list[str],
    ) -> MLReadinessComponent:
        maximum = self.COMPONENT_WEIGHTS["leakage_safety"]
        if target is None or target not in df.columns:
            return self._unassessed_component(
                key="leakage_safety",
                name="Leakage safety",
                maximum=maximum,
                summary="A valid target is required to assess target leakage.",
                recommendation="Set a valid target and run READINESS again.",
                metrics={"target": target, "leakage_threshold": 0.95},
            )
        if not pd.api.types.is_numeric_dtype(df[target]):
            return self._unassessed_component(
                key="leakage_safety",
                name="Leakage safety",
                maximum=maximum,
                summary=(
                    "Pearson leakage screening currently requires a numeric target."
                ),
                recommendation=(
                    "Review provenance and post-outcome fields manually for this "
                    "categorical target."
                ),
                metrics={"target": target, "target_dtype": str(df[target].dtype)},
            )

        correlations = self._target_correlations(df, target)
        leakage = {
            feature: value
            for feature, value in correlations.items()
            if abs(value) >= 0.95
        }
        deduction = min(maximum, len(leakage) * 5.0)
        deductions = []
        if leakage:
            deductions.append(
                f"{deduction:.2f} point(s): {len(leakage)} feature(s) have "
                "|correlation| >= 0.95 with the target."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="possible_target_leakage",
                    severity="high",
                    message=(
                        f"{len(leakage)} feature(s) are extremely correlated with "
                        "the target."
                    ),
                    recommendation=(
                        "Verify whether these fields are derived from, recorded after, "
                        "or otherwise expose the target."
                    ),
                    confidence=0.9,
                )
            )
        else:
            strengths.append("No extreme numeric target correlations were detected.")

        return self._component(
            key="leakage_safety",
            name="Leakage safety",
            score=maximum - deduction,
            maximum=maximum,
            summary=(
                "15 points minus 5 per feature with |Pearson correlation| >= 0.95, "
                "capped at 15."
            ),
            deductions=deductions,
            metrics={
                "target": target,
                "leakage_threshold": 0.95,
                "screened_numeric_features": len(correlations),
                "flagged_feature_count": len(leakage),
                "flagged_features": {
                    feature: round(value, 4)
                    for feature, value in list(leakage.items())[:20]
                },
            },
            recommendation=(
                "Remove confirmed post-outcome or target-derived fields before training."
                if leakage
                else None
            ),
        )

    def _multicollinearity_component(
        self,
        df: pd.DataFrame,
        target: str | None,
        issues: list[MLReadinessIssue],
        strengths: list[str],
    ) -> MLReadinessComponent:
        maximum = self.COMPONENT_WEIGHTS["multicollinearity"]
        numeric_features = [
            column
            for column in df.select_dtypes(include="number").columns
            if column != target
        ]
        if len(numeric_features) < 2:
            return self._unassessed_component(
                key="multicollinearity",
                name="Multicollinearity",
                maximum=maximum,
                summary="At least two numeric predictors are required for screening.",
                recommendation="Add or encode predictors before reassessing.",
                metrics={"numeric_predictors": len(numeric_features)},
            )

        matrix = df[numeric_features].corr(numeric_only=True)
        flagged = []
        for index, feature_a in enumerate(numeric_features):
            for feature_b in numeric_features[index + 1 :]:
                value = matrix.loc[feature_a, feature_b]
                if not pd.isna(value) and abs(value) >= 0.9:
                    flagged.append(
                        {
                            "feature_a": feature_a,
                            "feature_b": feature_b,
                            "correlation": round(float(value), 4),
                        }
                    )

        deduction = min(maximum, len(flagged) * 2.0)
        deductions = []
        if flagged:
            deductions.append(
                f"{deduction:.2f} point(s): {len(flagged)} predictor pair(s) "
                "have |correlation| >= 0.90."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="multicollinearity_risk",
                    severity="high",
                    message=(
                        f"{len(flagged)} very strong predictor relationship(s) detected."
                    ),
                    recommendation=(
                        "Review redundant predictors and confirm with VIF for linear "
                        "or coefficient-sensitive models."
                    ),
                    confidence=0.9,
                )
            )
        else:
            strengths.append(
                "No severe pairwise multicollinearity detected among numeric predictors."
            )

        return self._component(
            key="multicollinearity",
            name="Multicollinearity",
            score=maximum - deduction,
            maximum=maximum,
            summary=(
                "10 points minus 2 per predictor pair with |Pearson correlation| "
                ">= 0.90, capped at 10."
            ),
            deductions=deductions,
            metrics={
                "numeric_predictors": len(numeric_features),
                "correlation_threshold": 0.9,
                "flagged_pair_count": len(flagged),
                "flagged_pairs": flagged[:20],
            },
            recommendation=(
                "Remove, combine, regularize, or separately justify redundant features."
                if flagged
                else None
            ),
        )

    def _stability_component(
        self,
        df: pd.DataFrame,
        *,
        reference_df: pd.DataFrame | None,
        reference_name: str | None,
        target: str | None,
        issues: list[MLReadinessIssue],
        strengths: list[str],
    ) -> MLReadinessComponent:
        maximum = self.COMPONENT_WEIGHTS["feature_stability"]
        if reference_df is None:
            return self._unassessed_component(
                key="feature_stability",
                name="Feature stability",
                maximum=maximum,
                summary=(
                    "No reference dataset was supplied, so AutoDQ does not assume "
                    "that feature distributions are stable."
                ),
                recommendation=(
                    "Run READINESS REFERENCE <baseline_dataset> to compare feature "
                    "distributions using Population Stability Index (PSI)."
                ),
                metrics={"reference_dataset": None, "psi_thresholds": "0.10 / 0.25"},
            )
        if not isinstance(reference_df, pd.DataFrame):
            raise TypeError("The readiness reference must be a pandas DataFrame.")
        if len(df) < 50 or len(reference_df) < 50:
            return self._unassessed_component(
                key="feature_stability",
                name="Feature stability",
                maximum=maximum,
                summary="Both current and reference datasets need at least 50 rows.",
                recommendation="Use larger representative samples for PSI comparison.",
                metrics={
                    "current_rows": len(df),
                    "reference_rows": len(reference_df),
                    "reference_dataset": reference_name,
                },
            )

        current_features = [column for column in df.columns if column != target]
        reference_features = [
            column for column in reference_df.columns if column != target
        ]
        common = [column for column in reference_features if column in current_features]
        missing_current = [
            column for column in reference_features if column not in current_features
        ]
        new_current = [
            column for column in current_features if column not in reference_features
        ]
        feature_results = []
        penalties = []

        for column in common:
            psi = self._population_stability_index(
                reference_df[column],
                df[column],
            )
            if psi <= 0.1:
                status = "stable"
                penalty = 0.0
            elif psi <= 0.25:
                status = "moderate_shift"
                penalty = 0.5
            else:
                status = "unstable"
                penalty = 1.0
            penalties.append(penalty)
            feature_results.append(
                {"feature": column, "psi": round(psi, 4), "status": status}
            )

        for column in missing_current:
            penalties.append(1.0)
            feature_results.append(
                {"feature": column, "psi": None, "status": "missing_in_current"}
            )

        if not penalties:
            return self._unassessed_component(
                key="feature_stability",
                name="Feature stability",
                maximum=maximum,
                summary="No comparable feature columns were found in the reference.",
                recommendation="Provide a baseline with matching feature columns.",
                metrics={
                    "reference_dataset": reference_name,
                    "current_columns": len(current_features),
                    "reference_columns": len(reference_features),
                },
            )

        score = maximum * (1 - sum(penalties) / len(penalties))
        shifted = [
            item for item in feature_results if item["status"] != "stable"
        ]
        unstable = [
            item
            for item in feature_results
            if item["status"] in {"unstable", "missing_in_current"}
        ]
        psi_values = [
            item["psi"] for item in feature_results if item["psi"] is not None
        ]
        deductions = []
        if score < maximum:
            deductions.append(
                f"{maximum - score:.2f} point(s): {len(shifted)} of "
                f"{len(feature_results)} compared feature(s) show distribution "
                "shift or schema loss."
            )
            issues.append(
                MLReadinessIssue(
                    issue_type="feature_instability",
                    severity="high" if unstable else "medium",
                    message=(
                        f"{len(shifted)} feature(s) shifted relative to the "
                        f"{reference_name or 'reference'} dataset."
                    ),
                    recommendation=(
                        "Investigate data drift, schema changes, sampling changes, "
                        "and whether retraining is required."
                    ),
                    confidence=0.88,
                )
            )
        else:
            strengths.append("Compared feature distributions are stable by PSI.")

        top_shifted = sorted(
            shifted,
            key=lambda item: (
                item["psi"] is None,
                item["psi"] if item["psi"] is not None else float("inf"),
            ),
            reverse=True,
        )[:20]
        return self._component(
            key="feature_stability",
            name="Feature stability",
            score=score,
            maximum=maximum,
            summary=(
                "10 points scaled by feature-level PSI: stable <= 0.10, "
                "moderate shift <= 0.25, unstable > 0.25."
            ),
            deductions=deductions,
            metrics={
                "reference_dataset": reference_name,
                "current_rows": len(df),
                "reference_rows": len(reference_df),
                "compared_features": len(feature_results),
                "stable_features": len(feature_results) - len(shifted),
                "shifted_features": len(shifted),
                "unstable_features": len(unstable),
                "new_current_features": new_current[:20],
                "mean_psi": (
                    round(float(np.mean(psi_values)), 4) if psi_values else None
                ),
                "max_psi": round(max(psi_values), 4) if psi_values else None,
                "top_shifted_features": top_shifted,
            },
            recommendation=(
                "Investigate shifted features before reusing the same model or "
                "preprocessing assumptions."
                if shifted
                else None
            ),
        )

    def _component(
        self,
        *,
        key: str,
        name: str,
        score: float,
        maximum: float,
        summary: str,
        deductions: list[str],
        metrics: dict,
        recommendation: str | None,
    ) -> MLReadinessComponent:
        score = round(max(0.0, min(maximum, score)), 2)
        return MLReadinessComponent(
            key=key,
            name=name,
            score=score,
            max_score=maximum,
            status=self._component_status(score, maximum),
            summary=summary,
            deductions=deductions,
            metrics=metrics,
            recommendation=recommendation,
        )

    @staticmethod
    def _unassessed_component(
        *,
        key: str,
        name: str,
        maximum: float,
        summary: str,
        recommendation: str,
        metrics: dict,
    ) -> MLReadinessComponent:
        return MLReadinessComponent(
            key=key,
            name=name,
            score=0.0,
            max_score=maximum,
            status="not_assessed",
            summary=summary,
            recommendation=recommendation,
            metrics=metrics,
            assessed=False,
        )

    @staticmethod
    def _component_status(score: float, maximum: float) -> str:
        percentage = score / maximum * 100 if maximum else 0.0
        if percentage >= 90:
            return "excellent"
        if percentage >= 75:
            return "good"
        if percentage >= 50:
            return "warning"
        return "high_risk"

    @staticmethod
    def _interpretation_counts(interpretation_report) -> tuple[int, int]:
        if interpretation_report is None:
            return 0, 0

        insights = getattr(interpretation_report, "insights", None)
        if insights is None:
            interpretations = getattr(
                interpretation_report,
                "interpretations",
                {},
            )
            insights = [
                item
                for column_insights in interpretations.values()
                for item in column_insights
            ]

        high_skew_count = sum(
            1
            for insight in insights
            if getattr(insight, "insight_type", None) == "skewness"
            and getattr(insight, "severity", None) == "high"
        )
        high_tail_count = sum(
            1
            for insight in insights
            if getattr(insight, "insight_type", None) == "heavy_tail"
            and getattr(insight, "severity", None) == "high"
        )
        return high_skew_count, high_tail_count

    @staticmethod
    def _target_correlations(df: pd.DataFrame, target: str) -> dict[str, float]:
        numeric = df.select_dtypes(include="number")
        if target not in numeric.columns:
            return {}

        correlations = numeric.corr(numeric_only=True)[target]
        return {
            str(feature): float(value)
            for feature, value in correlations.items()
            if feature != target and not pd.isna(value)
        }

    @staticmethod
    def _population_stability_index(
        reference: pd.Series,
        current: pd.Series,
    ) -> float:
        epsilon = 1e-6
        if pd.api.types.is_numeric_dtype(reference) and pd.api.types.is_numeric_dtype(
            current
        ):
            reference_numeric = pd.to_numeric(reference, errors="coerce")
            current_numeric = pd.to_numeric(current, errors="coerce")
            valid_reference = reference_numeric.dropna()
            if valid_reference.nunique() >= 2:
                quantiles = np.unique(
                    valid_reference.quantile(np.linspace(0, 1, 11)).to_numpy()
                )
                internal = quantiles[1:-1]
                bins = np.concatenate(([-np.inf], internal, [np.inf]))
                reference_values = pd.cut(
                    reference_numeric,
                    bins=bins,
                    include_lowest=True,
                    duplicates="drop",
                ).astype("string")
                current_values = pd.cut(
                    current_numeric,
                    bins=bins,
                    include_lowest=True,
                    duplicates="drop",
                ).astype("string")
            else:
                reference_values = reference_numeric.astype("string")
                current_values = current_numeric.astype("string")
        else:
            reference_values = reference.astype("string")
            current_values = current.astype("string")

        reference_values = reference_values.fillna("__MISSING__")
        current_values = current_values.fillna("__MISSING__")
        reference_distribution = reference_values.value_counts(normalize=True)
        current_distribution = current_values.value_counts(normalize=True)
        categories = reference_distribution.index.union(current_distribution.index)
        expected = reference_distribution.reindex(categories, fill_value=0.0) + epsilon
        actual = current_distribution.reindex(categories, fill_value=0.0) + epsilon
        psi = ((actual - expected) * np.log(actual / expected)).sum()
        return float(max(0.0, psi))

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

    @staticmethod
    def _recommended_task(target_type: str) -> str:
        if target_type == "continuous_numeric":
            return "regression"

        if target_type in [
            "categorical_classification",
            "numeric_discrete_or_classification",
        ]:
            return "classification"

        if target_type == "unknown":
            return "unsupervised_or_set_target"

        return "review_target"

    @staticmethod
    def _recommended_models(target_type: str) -> list[str]:
        if target_type == "continuous_numeric":
            return [
                "Random Forest Regressor",
                "Gradient Boosting Regressor",
                "Linear Regression with preprocessing",
                "XGBoost/LightGBM Regressor",
            ]

        if target_type in [
            "categorical_classification",
            "numeric_discrete_or_classification",
        ]:
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
