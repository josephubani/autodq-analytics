from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson

from autodq.blue.models import (
    BLUEAssumptionResult,
    BLUEReport,
    VIFResult,
)


class BLUEEngine:
    """
    Evaluates assumptions associated with linear regression and BLUE.

    Current diagnostics:
    - linearity
    - residual normality
    - homoscedasticity
    - independence of errors
    - multicollinearity
    - influential observations
    """

    def analyze(
        self,
        df: pd.DataFrame,
        target: str,
        max_features: int = 20,
        significance_level: float = 0.05,
    ) -> BLUEReport:
        if target is None:
            raise ValueError(
                "A target column must be set before BLUE analysis."
            )

        if target not in df.columns:
            raise ValueError(
                f"Target column not found: {target}"
            )

        working_df = df.copy()

        numeric_df = working_df.select_dtypes(
            include="number"
        ).copy()

        if target not in numeric_df.columns:
            raise ValueError(
                "BLUE analysis currently requires a numeric target."
            )

        feature_columns = [
            column
            for column in numeric_df.columns
            if column != target
        ]

        feature_columns = self._filter_identifier_columns(
            feature_columns
        )

        if not feature_columns:
            raise ValueError(
                "No suitable numeric predictor columns were found."
            )

        feature_columns = feature_columns[:max_features]

        model_df = numeric_df[
            feature_columns + [target]
        ].replace(
            [np.inf, -np.inf],
            np.nan,
        ).dropna()

        if len(model_df) < 30:
            raise ValueError(
                "BLUE analysis requires at least 30 complete rows."
            )

        X = model_df[feature_columns].astype(float)
        y = model_df[target].astype(float)

        X_constant = sm.add_constant(
            X,
            has_constant="add",
        )

        fitted_model = sm.OLS(
            y,
            X_constant,
        ).fit()

        residuals = fitted_model.resid
        fitted_values = fitted_model.fittedvalues

        assumption_results = [
            self._test_linearity(
                residuals=residuals,
                fitted_values=fitted_values,
            ),
            self._test_normality(
                residuals=residuals,
                significance_level=significance_level,
            ),
            self._test_homoscedasticity(
                residuals=residuals,
                design_matrix=X_constant,
                significance_level=significance_level,
            ),
            self._test_independence(
                residuals=residuals,
            ),
            self._test_influential_observations(
                fitted_model=fitted_model,
            ),
        ]

        vif_results = self._calculate_vif(X)

        multicollinearity_result = (
            self._build_multicollinearity_result(
                vif_results
            )
        )

        assumption_results.append(
            multicollinearity_result
        )

        suitability_score = self._calculate_score(
            assumption_results
        )

        overall_status = self._overall_status(
            suitability_score=suitability_score,
            assumptions=assumption_results,
        )

        recommendations = self._build_recommendations(
            assumption_results=assumption_results,
            vif_results=vif_results,
        )

        warnings = []

        if fitted_model.rsquared >= 0.98:
            warnings.append(
                "The fitted linear model has an unusually high R². "
                "Review predictors for target leakage."
            )

        return BLUEReport(
            target=target,
            rows_analyzed=len(model_df),
            features_analyzed=len(feature_columns),
            overall_status=overall_status,
            suitability_score=suitability_score,
            assumptions=assumption_results,
            vif_results=vif_results,
            recommendations=recommendations,
            warnings=warnings,
        )

    def _test_linearity(
        self,
        residuals: pd.Series,
        fitted_values: pd.Series,
    ) -> BLUEAssumptionResult:
        correlation = stats.pearsonr(
            fitted_values,
            residuals,
        )

        absolute_correlation = abs(
            float(correlation.statistic)
        )

        if absolute_correlation < 0.1:
            status = "passed"
            severity = "low"
            interpretation = (
                "Residuals show little linear association with fitted "
                "values, supporting the linearity assumption."
            )
            recommendation = (
                "No major linearity correction is currently required."
            )

        elif absolute_correlation < 0.3:
            status = "warning"
            severity = "medium"
            interpretation = (
                "Residuals show some association with fitted values. "
                "Possible nonlinear structure may remain."
            )
            recommendation = (
                "Review residual plots and consider polynomial terms, "
                "interactions, or transformations."
            )

        else:
            status = "failed"
            severity = "high"
            interpretation = (
                "Residuals are strongly associated with fitted values, "
                "suggesting the relationship may not be adequately linear."
            )
            recommendation = (
                "Consider nonlinear models, transformations, splines, "
                "or interaction features."
            )

        return BLUEAssumptionResult(
            assumption="linearity",
            status=status,
            statistic=round(
                float(correlation.statistic),
                6,
            ),
            p_value=round(
                float(correlation.pvalue),
                6,
            ),
            threshold=0.1,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.85,
        )

    def _test_normality(
        self,
        residuals: pd.Series,
        significance_level: float,
    ) -> BLUEAssumptionResult:
        sample = residuals

        if len(sample) > 5000:
            sample = sample.sample(
                5000,
                random_state=42,
            )

        statistic, p_value = stats.jarque_bera(
            sample
        )

        if p_value >= significance_level:
            status = "passed"
            severity = "low"
            interpretation = (
                "Residual normality was not rejected."
            )
            recommendation = (
                "Residual distribution appears acceptable for standard "
                "linear inference."
            )
        else:
            status = "failed"
            severity = "medium"
            interpretation = (
                "Residuals significantly deviate from normality."
            )
            recommendation = (
                "Review outliers, transform skewed variables, or use "
                "robust standard errors."
            )

        return BLUEAssumptionResult(
            assumption="residual_normality",
            status=status,
            statistic=round(float(statistic), 6),
            p_value=round(float(p_value), 6),
            threshold=significance_level,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.9,
        )

    def _test_homoscedasticity(
        self,
        residuals: pd.Series,
        design_matrix: pd.DataFrame,
        significance_level: float,
    ) -> BLUEAssumptionResult:
        lm_statistic, lm_p_value, _, _ = (
            het_breuschpagan(
                residuals,
                design_matrix,
            )
        )

        if lm_p_value >= significance_level:
            status = "passed"
            severity = "low"
            interpretation = (
                "The Breusch-Pagan test did not detect significant "
                "heteroscedasticity."
            )
            recommendation = (
                "Standard linear regression variance assumptions appear "
                "reasonable."
            )
        else:
            status = "failed"
            severity = "high"
            interpretation = (
                "The Breusch-Pagan test detected non-constant residual "
                "variance."
            )
            recommendation = (
                "Use heteroscedasticity-robust standard errors, transform "
                "the target, or consider weighted least squares."
            )

        return BLUEAssumptionResult(
            assumption="homoscedasticity",
            status=status,
            statistic=round(
                float(lm_statistic),
                6,
            ),
            p_value=round(
                float(lm_p_value),
                6,
            ),
            threshold=significance_level,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.95,
        )

    def _test_independence(
        self,
        residuals: pd.Series,
    ) -> BLUEAssumptionResult:
        statistic = float(
            durbin_watson(residuals)
        )

        if 1.5 <= statistic <= 2.5:
            status = "passed"
            severity = "low"
            interpretation = (
                "The Durbin-Watson statistic suggests limited residual "
                "autocorrelation."
            )
            recommendation = (
                "No major autocorrelation correction is currently required."
            )

        elif 1.0 <= statistic <= 3.0:
            status = "warning"
            severity = "medium"
            interpretation = (
                "Some residual autocorrelation may be present."
            )
            recommendation = (
                "Review observation order, time effects, lagged variables, "
                "or clustered errors."
            )

        else:
            status = "failed"
            severity = "high"
            interpretation = (
                "The Durbin-Watson statistic indicates substantial "
                "residual autocorrelation."
            )
            recommendation = (
                "Consider time-series regression, generalized least "
                "squares, or lag features."
            )

        return BLUEAssumptionResult(
            assumption="independence",
            status=status,
            statistic=round(statistic, 6),
            threshold=2.0,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.9,
        )

    def _test_influential_observations(
        self,
        fitted_model,
    ) -> BLUEAssumptionResult:
        influence = fitted_model.get_influence()

        cooks_distance = influence.cooks_distance[0]

        threshold = 4 / len(cooks_distance)

        influential_count = int(
            (cooks_distance > threshold).sum()
        )

        influential_percentage = (
            influential_count
            / len(cooks_distance)
            * 100
        )

        if influential_percentage <= 1:
            status = "passed"
            severity = "low"
            interpretation = (
                "Very few observations exceed the Cook's distance "
                "threshold."
            )
            recommendation = (
                "No major influential-observation issue was detected."
            )

        elif influential_percentage <= 5:
            status = "warning"
            severity = "medium"
            interpretation = (
                "Several potentially influential observations were found."
            )
            recommendation = (
                "Review high Cook's distance records and compare models "
                "with and without them."
            )

        else:
            status = "failed"
            severity = "high"
            interpretation = (
                "A notable portion of observations may strongly influence "
                "the regression estimates."
            )
            recommendation = (
                "Investigate influential rows, possible data errors, "
                "segmentation, or robust regression."
            )

        return BLUEAssumptionResult(
            assumption="influential_observations",
            status=status,
            statistic=round(
                influential_percentage,
                4,
            ),
            threshold=1.0,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.88,
            details={
                "influential_rows": influential_count,
                "influential_percentage": round(
                    influential_percentage,
                    4,
                ),
                "cooks_distance_threshold": round(
                    threshold,
                    6,
                ),
            },
        )

    def _calculate_vif(
        self,
        X: pd.DataFrame,
    ) -> list[VIFResult]:
        if X.shape[1] < 2:
            return []

        vif_frame = sm.add_constant(
            X,
            has_constant="add",
        )

        results = []

        for index, column in enumerate(
            vif_frame.columns
        ):
            if column == "const":
                continue

            try:
                vif = float(
                    variance_inflation_factor(
                        vif_frame.values,
                        index,
                    )
                )
            except Exception:
                vif = float("inf")

            if vif < 5:
                severity = "low"
                interpretation = (
                    "No major multicollinearity concern."
                )
                recommendation = (
                    "The feature can generally remain in the model."
                )

            elif vif < 10:
                severity = "medium"
                interpretation = (
                    "Moderate multicollinearity detected."
                )
                recommendation = (
                    "Review correlated predictors and coefficient stability."
                )

            else:
                severity = "high"
                interpretation = (
                    "Severe multicollinearity detected."
                )
                recommendation = (
                    "Remove, combine, transform, or regularize correlated "
                    "predictors."
                )

            results.append(
                VIFResult(
                    feature=column,
                    vif=round(vif, 4),
                    severity=severity,
                    interpretation=interpretation,
                    recommendation=recommendation,
                )
            )

        return sorted(
            results,
            key=lambda item: item.vif,
            reverse=True,
        )

    def _build_multicollinearity_result(
        self,
        vif_results: list[VIFResult],
    ) -> BLUEAssumptionResult:
        if not vif_results:
            return BLUEAssumptionResult(
                assumption="multicollinearity",
                status="warning",
                interpretation=(
                    "VIF could not be calculated because fewer than two "
                    "predictors were available."
                ),
                recommendation=(
                    "Use at least two predictors for multicollinearity "
                    "assessment."
                ),
                severity="low",
                confidence=0.7,
            )

        maximum_vif = max(
            result.vif
            for result in vif_results
        )

        severe_count = sum(
            result.vif >= 10
            for result in vif_results
        )

        moderate_count = sum(
            5 <= result.vif < 10
            for result in vif_results
        )

        if severe_count > 0:
            status = "failed"
            severity = "high"
            interpretation = (
                f"{severe_count} predictor(s) have VIF values of at least "
                "10, indicating severe multicollinearity."
            )
            recommendation = (
                "Review highly correlated predictors, derived variables, "
                "and target-leakage-like features."
            )

        elif moderate_count > 0:
            status = "warning"
            severity = "medium"
            interpretation = (
                f"{moderate_count} predictor(s) have moderate VIF values."
            )
            recommendation = (
                "Review coefficient stability and consider regularization."
            )

        else:
            status = "passed"
            severity = "low"
            interpretation = (
                "No major multicollinearity was detected."
            )
            recommendation = (
                "Predictor collinearity appears acceptable."
            )

        return BLUEAssumptionResult(
            assumption="multicollinearity",
            status=status,
            statistic=round(
                maximum_vif,
                4,
            ),
            threshold=5.0,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.95,
            details={
                "maximum_vif": round(
                    maximum_vif,
                    4,
                ),
                "moderate_vif_features": moderate_count,
                "severe_vif_features": severe_count,
            },
        )

    def _calculate_score(
        self,
        assumptions: list[BLUEAssumptionResult],
    ) -> float:
        scores = {
            "passed": 100,
            "warning": 65,
            "failed": 25,
        }

        if not assumptions:
            return 0.0

        total = sum(
            scores.get(result.status, 0)
            for result in assumptions
        )

        return round(
            total / len(assumptions),
            2,
        )

    def _overall_status(
        self,
        suitability_score: float,
        assumptions: list[BLUEAssumptionResult],
    ) -> str:
        severe_failures = sum(
            result.status == "failed"
            and result.severity == "high"
            for result in assumptions
        )

        if suitability_score >= 85 and severe_failures == 0:
            return "suitable"

        if suitability_score >= 60:
            return "suitable_with_caution"

        return "not_suitable"

    def _build_recommendations(
        self,
        assumption_results: list[BLUEAssumptionResult],
        vif_results: list[VIFResult],
    ) -> list[str]:
        recommendations = []

        for result in assumption_results:
            if result.status != "passed":
                recommendations.append(
                    result.recommendation
                )

        high_vif_features = [
            result.feature
            for result in vif_results
            if result.vif >= 10
        ]

        if high_vif_features:
            recommendations.append(
                "High-VIF predictors requiring review: "
                + ", ".join(high_vif_features[:10])
            )

        if not recommendations:
            recommendations.append(
                "The tested linear regression assumptions appear "
                "acceptable."
            )

        return list(dict.fromkeys(recommendations))

    def _filter_identifier_columns(
        self,
        columns: list[str],
    ) -> list[str]:
        identifier_tokens = (
            "id",
            "uuid",
            "guid",
            "transaction",
            "invoice",
            "receipt",
        )

        return [
            column
            for column in columns
            if not any(
                token in column.lower()
                for token in identifier_tokens
            )
        ]