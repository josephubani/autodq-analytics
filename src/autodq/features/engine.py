import pandas as pd

from autodq.features.models import (
    FeatureEngineeringReport,
    FeatureRecommendation,
)


class FeatureEngineeringEngine:
    """
    Recommends useful feature engineering ideas based on dataset columns.
    """

    def recommend(
        self,
        df: pd.DataFrame,
        target: str | None = None,
        statistics_report=None,
        interpretation_report=None,
    ) -> FeatureEngineeringReport:
        recommendations: list[FeatureRecommendation] = []

        columns_lower = {column.lower(): column for column in df.columns}

        recommendations.extend(self._date_features(df))
        recommendations.extend(self._sales_features(columns_lower))
        recommendations.extend(self._customer_features(columns_lower))
        recommendations.extend(
            self._skew_transform_features(
                df=df,
                target=target,
                interpretation_report=interpretation_report,
            )
        )

        return FeatureEngineeringReport(
            recommendations=recommendations,
        )

    def _date_features(self, df: pd.DataFrame) -> list[FeatureRecommendation]:
        recommendations = []

        for column in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[column]):
                recommendations.extend(
                    [
                        FeatureRecommendation(
                            feature_name=f"{column}_year",
                            source_columns=[column],
                            feature_type="date_part",
                            formula=f"{column}.dt.year",
                            reason="Year can reveal long-term sales, customer, or operational trends.",
                            priority="medium",
                            executable=True,
                            confidence=0.9,
                        ),
                        FeatureRecommendation(
                            feature_name=f"{column}_month",
                            source_columns=[column],
                            feature_type="date_part",
                            formula=f"{column}.dt.month",
                            reason="Month can capture seasonality patterns.",
                            priority="high",
                            executable=True,
                            confidence=0.92,
                        ),
                        FeatureRecommendation(
                            feature_name=f"{column}_quarter",
                            source_columns=[column],
                            feature_type="date_part",
                            formula=f"{column}.dt.quarter",
                            reason="Quarter is useful for business reporting and seasonal analysis.",
                            priority="medium",
                            executable=True,
                            confidence=0.88,
                        ),
                        FeatureRecommendation(
                            feature_name=f"{column}_weekday",
                            source_columns=[column],
                            feature_type="date_part",
                            formula=f"{column}.dt.dayofweek",
                            reason="Weekday can reveal weekly demand or transaction patterns.",
                            priority="medium",
                            executable=True,
                            confidence=0.86,
                        ),
                    ]
                )

        return recommendations

    def _sales_features(
        self,
        columns_lower: dict[str, str],
    ) -> list[FeatureRecommendation]:
        recommendations = []

        revenue = columns_lower.get("revenue")
        quantity = columns_lower.get("quantity")
        profit = columns_lower.get("profit")
        cost = columns_lower.get("cost")
        gross_sales = columns_lower.get("gross_sales")
        discount_amount = columns_lower.get("discount_amount")

        if revenue and quantity:
            recommendations.append(
                FeatureRecommendation(
                    feature_name="revenue_per_unit",
                    source_columns=[revenue, quantity],
                    feature_type="ratio",
                    formula=f"{revenue} / {quantity}",
                    reason="Revenue per unit helps compare transaction value independent of quantity.",
                    priority="high",
                    executable=True,
                    confidence=0.92,
                )
            )

        if profit and revenue:
            recommendations.append(
                FeatureRecommendation(
                    feature_name="profit_margin",
                    source_columns=[profit, revenue],
                    feature_type="ratio",
                    formula=f"{profit} / {revenue}",
                    reason="Profit margin explains profitability better than profit alone.",
                    priority="high",
                    executable=True,
                    confidence=0.94,
                )
            )

        if discount_amount and gross_sales:
            recommendations.append(
                FeatureRecommendation(
                    feature_name="discount_intensity",
                    source_columns=[discount_amount, gross_sales],
                    feature_type="ratio",
                    formula=f"{discount_amount} / {gross_sales}",
                    reason="Discount intensity measures how much of gross sales was reduced by discounts.",
                    priority="medium",
                    executable=True,
                    confidence=0.88,
                )
            )

        if revenue:
            recommendations.append(
                FeatureRecommendation(
                    feature_name="high_value_transaction",
                    source_columns=[revenue],
                    feature_type="flag",
                    formula=f"{revenue} >= {revenue}.quantile(0.75)",
                    reason="High-value transaction flags can help segmentation and modelling.",
                    priority="medium",
                    executable=True,
                    confidence=0.84,
                )
            )

        if cost and revenue:
            recommendations.append(
                FeatureRecommendation(
                    feature_name="cost_to_revenue_ratio",
                    source_columns=[cost, revenue],
                    feature_type="ratio",
                    formula=f"{cost} / {revenue}",
                    reason="Cost-to-revenue ratio helps identify inefficient transactions.",
                    priority="medium",
                    executable=True,
                    confidence=0.86,
                )
            )

        return recommendations

    def _customer_features(
        self,
        columns_lower: dict[str, str],
    ) -> list[FeatureRecommendation]:
        recommendations = []

        age = (
            columns_lower.get("age")
            or columns_lower.get("customer_age")
        )

        returned = columns_lower.get("returned")

        if age:
            recommendations.append(
                FeatureRecommendation(
                    feature_name="customer_age_group",
                    source_columns=[age],
                    feature_type="binning",
                    formula=f"bin {age} into age groups",
                    reason="Age groups are often more interpretable than raw age.",
                    priority="medium",
                    executable=False,
                    confidence=0.82,
                )
            )

        if returned:
            recommendations.append(
                FeatureRecommendation(
                    feature_name="is_returned_order",
                    source_columns=[returned],
                    feature_type="flag",
                    formula=f"{returned} == 1",
                    reason="Returned order flag can support return-risk and profitability analysis.",
                    priority="medium",
                    executable=True,
                    confidence=0.88,
                )
            )

        return recommendations

    def _skew_transform_features(
        self,
        df: pd.DataFrame,
        target: str | None = None,
        interpretation_report=None,
    ) -> list[FeatureRecommendation]:
        recommendations = []

        numeric_columns = list(df.select_dtypes(include="number").columns)

        for column in numeric_columns:
            if column == target:
                continue

            series = pd.to_numeric(df[column], errors="coerce").dropna()

            if series.empty:
                continue

            skewness = series.skew()

            if skewness > 1.5 and series.min() >= 0:
                recommendations.append(
                    FeatureRecommendation(
                        feature_name=f"log_{column}",
                        source_columns=[column],
                        feature_type="transformation",
                        formula=f"log1p({column})",
                        reason=f"{column} is highly right-skewed. Log transform may reduce skewness.",
                        priority="medium",
                        executable=True,
                        confidence=0.83,
                    )
                )

        return recommendations