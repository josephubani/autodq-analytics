from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class BLUEPrescription:
    action: str
    category: str
    priority: str
    reason: str
    recommendation: str
    confidence: float
    related_assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "category": self.category,
            "priority": self.priority,
            "reason": self.reason,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "related_assumptions": self.related_assumptions,
        }


class BLUEPrescriptionEngine:
    """
    Converts BLUE diagnostic results into practical model and
    preprocessing recommendations.
    """

    def prescribe(self, blue_report) -> list[BLUEPrescription]:
        if blue_report is None:
            raise ValueError(
                "No BLUE report available. Run project.blue() first."
            )

        prescriptions: list[BLUEPrescription] = []

        assumptions = {
            result.assumption: result
            for result in blue_report.assumptions
        }

        linearity = assumptions.get("linearity")
        normality = assumptions.get("residual_normality")
        homoscedasticity = assumptions.get("homoscedasticity")
        independence = assumptions.get("independence")
        influence = assumptions.get("influential_observations")
        multicollinearity = assumptions.get("multicollinearity")

        if homoscedasticity and homoscedasticity.status == "failed":
            prescriptions.append(
                BLUEPrescription(
                    action="Use robust standard errors",
                    category="inference",
                    priority="high",
                    reason=(
                        "The Breusch-Pagan test detected "
                        "non-constant residual variance."
                    ),
                    recommendation=(
                        "Use HC3 heteroscedasticity-robust standard errors "
                        "for coefficient inference. Weighted least squares "
                        "may also be appropriate when a variance structure "
                        "can be estimated."
                    ),
                    confidence=0.95,
                    related_assumptions=["homoscedasticity"],
                )
            )

        if normality and normality.status == "failed":
            prescriptions.append(
                BLUEPrescription(
                    action="Transform the target or use robust regression",
                    category="transformation",
                    priority="high",
                    reason=(
                        "Residuals significantly deviate from normality."
                    ),
                    recommendation=(
                        "Consider log1p, Box-Cox, or Yeo-Johnson "
                        "transformation of the target. Also review "
                        "extreme values and robust regression alternatives."
                    ),
                    confidence=0.9,
                    related_assumptions=["residual_normality"],
                )
            )

        if linearity and linearity.status in {"warning", "failed"}:
            priority = (
                "high"
                if linearity.status == "failed"
                else "medium"
            )

            prescriptions.append(
                BLUEPrescription(
                    action="Add nonlinear structure or use a nonlinear model",
                    category="model_selection",
                    priority=priority,
                    reason=(
                        "Residuals indicate that the current linear "
                        "specification may not fully capture the relationship."
                    ),
                    recommendation=(
                        "Test polynomial terms, interactions, splines, "
                        "Random Forest, or Gradient Boosting."
                    ),
                    confidence=0.88,
                    related_assumptions=["linearity"],
                )
            )

        if multicollinearity and multicollinearity.status in {
            "warning",
            "failed",
        }:
            priority = (
                "high"
                if multicollinearity.status == "failed"
                else "medium"
            )

            high_vif_features = [
                item.feature
                for item in blue_report.vif_results
                if float(item.vif) >= 10
            ]

            feature_text = (
                ", ".join(high_vif_features[:10])
                if high_vif_features
                else "the highest-VIF predictors"
            )

            prescriptions.append(
                BLUEPrescription(
                    action="Reduce multicollinearity",
                    category="feature_selection",
                    priority=priority,
                    reason=(
                        "Predictors with elevated VIF values may make "
                        "coefficients unstable."
                    ),
                    recommendation=(
                        f"Review {feature_text}. Remove redundant features, "
                        "combine related predictors, or use Ridge/Lasso "
                        "regularization."
                    ),
                    confidence=0.95,
                    related_assumptions=["multicollinearity"],
                )
            )

        if influence and influence.status in {"warning", "failed"}:
            details = influence.details or {}

            influential_rows = details.get(
                "influential_rows",
                0,
            )

            influential_percentage = details.get(
                "influential_percentage",
                0,
            )

            prescriptions.append(
                BLUEPrescription(
                    action="Review influential observations",
                    category="data_review",
                    priority=(
                        "high"
                        if influence.status == "failed"
                        else "medium"
                    ),
                    reason=(
                        f"{influential_rows} row(s), representing "
                        f"{influential_percentage}% of analyzed data, "
                        "may strongly influence the fitted coefficients."
                    ),
                    recommendation=(
                        "Inspect these rows for data errors, unusual groups, "
                        "or valid extreme cases. Compare model results with "
                        "and without them and consider robust regression."
                    ),
                    confidence=0.9,
                    related_assumptions=["influential_observations"],
                )
            )

        if independence and independence.status in {
            "warning",
            "failed",
        }:
            prescriptions.append(
                BLUEPrescription(
                    action="Address residual dependence",
                    category="model_structure",
                    priority=(
                        "high"
                        if independence.status == "failed"
                        else "medium"
                    ),
                    reason=(
                        "The Durbin-Watson result suggests residual "
                        "autocorrelation."
                    ),
                    recommendation=(
                        "Review time ordering, grouped observations, lagged "
                        "predictors, clustered errors, or generalized least "
                        "squares."
                    ),
                    confidence=0.9,
                    related_assumptions=["independence"],
                )
            )

        if (
            linearity
            and linearity.status == "passed"
            and homoscedasticity
            and homoscedasticity.status == "passed"
            and multicollinearity
            and multicollinearity.status == "passed"
        ):
            prescriptions.append(
                BLUEPrescription(
                    action="Retain linear regression",
                    category="model_selection",
                    priority="low",
                    reason=(
                        "The principal Gauss-Markov assumptions appear "
                        "acceptable."
                    ),
                    recommendation=(
                        "Linear regression remains a reasonable candidate, "
                        "subject to predictive validation."
                    ),
                    confidence=0.9,
                    related_assumptions=[
                        "linearity",
                        "homoscedasticity",
                        "multicollinearity",
                    ],
                )
            )

        prescriptions.sort(
            key=lambda item: {
                "high": 0,
                "medium": 1,
                "low": 2,
            }.get(item.priority, 3)
        )

        return prescriptions