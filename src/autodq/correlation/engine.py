import pandas as pd

from autodq.correlation.models import (
    CorrelationRelationship,
    CorrelationReport,
    TargetCorrelation,
)


class CorrelationEngine:
    """
    Analyzes numeric relationships and converts correlation values into
    practical intelligence.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        target: str | None = None,
        min_abs_correlation: float = 0.3,
    ) -> CorrelationReport:
        numeric_df = df.select_dtypes(include="number")

        if numeric_df.empty:
            return CorrelationReport(matrix={}, relationships=[])

        corr = numeric_df.corr(numeric_only=True).round(4)

        relationships = self._build_relationships(
            corr=corr,
            min_abs_correlation=min_abs_correlation,
        )

        target_relationships = []

        if target is not None and target in corr.columns:
            target_relationships = self._build_target_relationships(
                corr=corr,
                target=target,
                min_abs_correlation=0.05,
            )

        return CorrelationReport(
            relationships=relationships,
            target_relationships=target_relationships,
            matrix=corr.to_dict(),
        )

    def _build_relationships(
        self,
        corr: pd.DataFrame,
        min_abs_correlation: float,
    ) -> list[CorrelationRelationship]:
        relationships = []
        columns = list(corr.columns)

        for i, feature_a in enumerate(columns):
            for feature_b in columns[i + 1:]:
                value = corr.loc[feature_a, feature_b]

                if pd.isna(value):
                    continue

                if abs(value) < min_abs_correlation:
                    continue

                relationships.append(
                    CorrelationRelationship(
                        feature_a=feature_a,
                        feature_b=feature_b,
                        correlation=float(value),
                        strength=self._strength(value),
                        direction=self._direction(value),
                        severity=self._severity(value),
                        interpretation=self._relationship_interpretation(
                            feature_a,
                            feature_b,
                            value,
                        ),
                        recommendation=self._relationship_recommendation(
                            feature_a,
                            feature_b,
                            value,
                        ),
                        confidence=self._confidence(value),
                    )
                )

        relationships.sort(
            key=lambda relationship: abs(relationship.correlation),
            reverse=True,
        )

        return relationships

    def _build_target_relationships(
        self,
        corr: pd.DataFrame,
        target: str,
        min_abs_correlation: float,
    ) -> list[TargetCorrelation]:
        target_relationships = []

        for feature in corr.columns:
            if feature == target:
                continue

            value = corr.loc[feature, target]

            if pd.isna(value):
                continue

            if abs(value) < min_abs_correlation:
                continue

            target_relationships.append(
                TargetCorrelation(
                    feature=feature,
                    target=target,
                    correlation=float(value),
                    strength=self._strength(value),
                    direction=self._direction(value),
                    interpretation=self._target_interpretation(
                        feature,
                        target,
                        value,
                    ),
                    recommendation=self._target_recommendation(
                        feature,
                        target,
                        value,
                    ),
                    confidence=self._confidence(value),
                )
            )

        target_relationships.sort(
            key=lambda relationship: abs(relationship.correlation),
            reverse=True,
        )

        return target_relationships

    def _strength(self, value: float) -> str:
        abs_value = abs(value)

        if abs_value >= 0.9:
            return "very_strong"
        if abs_value >= 0.7:
            return "strong"
        if abs_value >= 0.5:
            return "moderate"
        if abs_value >= 0.3:
            return "weak"

        return "very_weak"

    def _direction(self, value: float) -> str:
        if value > 0:
            return "positive"

        if value < 0:
            return "negative"

        return "none"

    def _severity(self, value: float) -> str:
        abs_value = abs(value)

        if abs_value >= 0.9:
            return "high"
        if abs_value >= 0.7:
            return "medium"

        return "low"

    def _confidence(self, value: float) -> float:
        abs_value = abs(value)

        if abs_value >= 0.9:
            return 0.95
        if abs_value >= 0.7:
            return 0.9
        if abs_value >= 0.5:
            return 0.82
        if abs_value >= 0.3:
            return 0.7

        return 0.55

    def _relationship_interpretation(
        self,
        feature_a: str,
        feature_b: str,
        value: float,
    ) -> str:
        strength = self._strength(value).replace("_", " ")
        direction = self._direction(value)

        if direction == "positive":
            return (
                f"{feature_a} and {feature_b} have a {strength} positive "
                "relationship. As one increases, the other tends to increase."
            )

        if direction == "negative":
            return (
                f"{feature_a} and {feature_b} have a {strength} negative "
                "relationship. As one increases, the other tends to decrease."
            )

        return f"{feature_a} and {feature_b} show little linear relationship."

    def _relationship_recommendation(
        self,
        feature_a: str,
        feature_b: str,
        value: float,
    ) -> str:
        abs_value = abs(value)

        if abs_value >= 0.9:
            return (
                "Possible multicollinearity risk. Avoid using both variables "
                "together in sensitive linear models unless there is a clear "
                "business reason."
            )

        if abs_value >= 0.7:
            return (
                "Strong relationship detected. Review whether both variables "
                "provide unique information before modelling."
            )

        if abs_value >= 0.5:
            return (
                "Moderate relationship detected. This may be useful for feature "
                "selection or business interpretation."
            )

        return "Weak relationship detected. Use with caution for prediction."

    def _target_interpretation(
        self,
        feature: str,
        target: str,
        value: float,
    ) -> str:
        strength = self._strength(value).replace("_", " ")
        direction = self._direction(value)

        if direction == "positive":
            return (
                f"{feature} has a {strength} positive relationship with "
                f"{target}. Higher {feature} values tend to align with higher "
                f"{target} values."
            )

        if direction == "negative":
            return (
                f"{feature} has a {strength} negative relationship with "
                f"{target}. Higher {feature} values tend to align with lower "
                f"{target} values."
            )

        return f"{feature} has little linear relationship with {target}."

    def _target_recommendation(
        self,
        feature: str,
        target: str,
        value: float,
    ) -> str:
        abs_value = abs(value)

        if abs_value >= 0.7:
            return (
                f"{feature} may be an important predictor of {target}. "
                "Review for possible target leakage before modelling."
            )

        if abs_value >= 0.5:
            return (
                f"{feature} may provide useful predictive signal for {target}."
            )

        if abs_value >= 0.3:
            return (
                f"{feature} has weak predictive signal for {target}. It may still "
                "help nonlinear models."
            )

        return (
            f"{feature} has very weak linear signal for {target}. Consider "
            "nonlinear relationships or interactions."
        )