from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class BLUEVisualInsight:
    """
    Interpretation of one BLUE diagnostic visualization.
    """

    chart_type: str
    title: str
    status: str
    interpretation: str
    recommendation: str
    severity: str
    confidence: float
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "chart_type": self.chart_type,
            "title": self.title,
            "status": self.status,
            "interpretation": self.interpretation,
            "recommendation": self.recommendation,
            "severity": self.severity,
            "confidence": self.confidence,
            "metrics": self.metrics,
        }


class BLUEVisualInterpreter:
    """
    Produces human-readable interpretations for BLUE diagnostic charts.

    Supported interpretations:
    - residuals versus fitted values
    - Q-Q residual normality
    - Cook's distance
    - VIF multicollinearity
    """

    def interpret(
        self,
        blue_report,
        blue_visualization_report=None,
    ) -> list[BLUEVisualInsight]:
        if blue_report is None:
            raise ValueError(
                "No BLUE report available. Run project.blue() first."
            )

        insights = [
            self._interpret_residuals_vs_fitted(
                blue_report
            ),
            self._interpret_qq_plot(
                blue_report
            ),
            self._interpret_cooks_distance(
                blue_report
            ),
            self._interpret_vif(
                blue_report
            ),
        ]

        return insights

    def _interpret_residuals_vs_fitted(
        self,
        blue_report,
    ) -> BLUEVisualInsight:
        linearity = self._find_assumption(
            blue_report,
            "linearity",
        )

        homoscedasticity = self._find_assumption(
            blue_report,
            "homoscedasticity",
        )

        statuses = {
            getattr(linearity, "status", "warning"),
            getattr(homoscedasticity, "status", "warning"),
        }

        if statuses == {"passed"}:
            status = "passed"
            severity = "low"

            interpretation = (
                "The residual-versus-fitted diagnostics support an "
                "approximately linear relationship with reasonably "
                "constant residual variance."
            )

            recommendation = (
                "The current linear specification appears acceptable. "
                "Continue reviewing influential observations and "
                "multicollinearity before final use."
            )

        elif "failed" in statuses:
            status = "failed"
            severity = "high"

            interpretation = (
                "The residual-versus-fitted diagnostics indicate that "
                "the linear model may contain nonlinear structure, "
                "non-constant variance, or both."
            )

            recommendation = (
                "Consider transforming the target, adding polynomial or "
                "interaction terms, using weighted least squares, robust "
                "standard errors, or selecting a nonlinear model."
            )

        else:
            status = "warning"
            severity = "medium"

            interpretation = (
                "The residual pattern is not fully ideal. Some curvature "
                "or changing residual spread may remain."
            )

            recommendation = (
                "Inspect the residual plot carefully and test appropriate "
                "transformations or interaction features."
            )

        return BLUEVisualInsight(
            chart_type="blue_residuals_vs_fitted",
            title="Residuals vs Fitted Values",
            status=status,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.9,
            metrics={
                "linearity_status": getattr(
                    linearity,
                    "status",
                    None,
                ),
                "homoscedasticity_status": getattr(
                    homoscedasticity,
                    "status",
                    None,
                ),
            },
        )

    def _interpret_qq_plot(
        self,
        blue_report,
    ) -> BLUEVisualInsight:
        normality = self._find_assumption(
            blue_report,
            "residual_normality",
        )

        status = getattr(
            normality,
            "status",
            "warning",
        )

        p_value = getattr(
            normality,
            "p_value",
            None,
        )

        if status == "passed":
            interpretation = (
                "Residual normality was not rejected. Q-Q plot points "
                "should generally remain close to the reference line."
            )

            recommendation = (
                "Standard linear-model inference may be reasonable, "
                "subject to the remaining BLUE assumptions."
            )

            severity = "low"

        elif status == "failed":
            interpretation = (
                "The residual distribution differs substantially from "
                "normality. The Q-Q plot is expected to show deviations, "
                "particularly in the tails."
            )

            recommendation = (
                "Review extreme observations, transform skewed variables "
                "or the target, and consider robust standard errors or "
                "robust regression."
            )

            severity = "medium"

        else:
            interpretation = (
                "Residual normality is uncertain and should be reviewed "
                "alongside the Q-Q plot."
            )

            recommendation = (
                "Inspect tail deviations and compare results using robust "
                "inference."
            )

            severity = "medium"

        return BLUEVisualInsight(
            chart_type="blue_qq_plot",
            title="Residual Q-Q Plot",
            status=status,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.92,
            metrics={
                "normality_p_value": p_value,
            },
        )

    def _interpret_cooks_distance(
        self,
        blue_report,
    ) -> BLUEVisualInsight:
        influence_result = self._find_assumption(
            blue_report,
            "influential_observations",
        )

        status = getattr(
            influence_result,
            "status",
            "warning",
        )

        details = getattr(
            influence_result,
            "details",
            {},
        ) or {}

        influential_rows = details.get(
            "influential_rows",
            0,
        )

        influential_percentage = details.get(
            "influential_percentage",
            0,
        )

        threshold = details.get(
            "cooks_distance_threshold",
            None,
        )

        if status == "passed":
            interpretation = (
                "Few observations exceed the Cook's-distance threshold. "
                "The model does not appear to be dominated by a small "
                "number of records."
            )

            recommendation = (
                "No major influential-observation correction is required."
            )

            severity = "low"

        elif status == "failed":
            interpretation = (
                f"{influential_rows} observation(s), representing "
                f"{influential_percentage}% of the analyzed rows, may "
                "have substantial influence on the fitted coefficients."
            )

            recommendation = (
                "Inspect influential records for data errors, unusual "
                "segments, or valid extreme cases. Compare model results "
                "with and without these observations and consider robust "
                "regression."
            )

            severity = "high"

        else:
            interpretation = (
                f"{influential_rows} potentially influential observation(s) "
                "were detected."
            )

            recommendation = (
                "Review the highest Cook's-distance observations before "
                "interpreting coefficient estimates."
            )

            severity = "medium"

        return BLUEVisualInsight(
            chart_type="blue_cooks_distance",
            title="Cook's Distance",
            status=status,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.9,
            metrics={
                "influential_rows": influential_rows,
                "influential_percentage": influential_percentage,
                "threshold": threshold,
            },
        )

    def _interpret_vif(
        self,
        blue_report,
    ) -> BLUEVisualInsight:
        vif_results = list(
            getattr(
                blue_report,
                "vif_results",
                [],
            )
        )

        if not vif_results:
            return BLUEVisualInsight(
                chart_type="blue_vif_chart",
                title="Variance Inflation Factors",
                status="warning",
                interpretation=(
                    "No VIF values were available for interpretation."
                ),
                recommendation=(
                    "Use at least two numeric predictors to assess "
                    "multicollinearity."
                ),
                severity="low",
                confidence=0.7,
            )

        severe_features = [
            result.feature
            for result in vif_results
            if float(result.vif) >= 10
        ]

        moderate_features = [
            result.feature
            for result in vif_results
            if 5 <= float(result.vif) < 10
        ]

        maximum_vif = max(
            float(result.vif)
            for result in vif_results
        )

        if severe_features:
            status = "failed"
            severity = "high"

            interpretation = (
                "Severe multicollinearity was detected. The largest VIF "
                f"is {round(maximum_vif, 4)}, and the affected features "
                f"include {', '.join(severe_features[:8])}."
            )

            recommendation = (
                "Remove redundant or target-derived predictors, combine "
                "correlated variables, or use Ridge/Lasso regularization."
            )

        elif moderate_features:
            status = "warning"
            severity = "medium"

            interpretation = (
                "Moderate multicollinearity was detected for "
                f"{', '.join(moderate_features[:8])}."
            )

            recommendation = (
                "Review coefficient stability and consider regularized "
                "regression."
            )

        else:
            status = "passed"
            severity = "low"

            interpretation = (
                "All available VIF values are below the moderate-risk "
                "threshold of 5."
            )

            recommendation = (
                "Predictor multicollinearity appears acceptable."
            )

        return BLUEVisualInsight(
            chart_type="blue_vif_chart",
            title="Variance Inflation Factors",
            status=status,
            interpretation=interpretation,
            recommendation=recommendation,
            severity=severity,
            confidence=0.95,
            metrics={
                "maximum_vif": round(
                    maximum_vif,
                    4,
                ),
                "severe_features": severe_features,
                "moderate_features": moderate_features,
            },
        )

    def _find_assumption(
        self,
        blue_report,
        assumption_name: str,
    ):
        for result in blue_report.assumptions:
            if result.assumption == assumption_name:
                return result

        return None