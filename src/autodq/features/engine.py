import pandas as pd
import numpy as np

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
        recommendations.extend(self._bounded_numeric_features(df))
        recommendations.extend(
            self._skew_transform_features(
                df=df,
                target=target,
            )
        )

        recommendations = self._sort_recommendations(recommendations)

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
                        FeatureRecommendation(
                            feature_name=f"{column}_is_weekend",
                            source_columns=[column],
                            feature_type="date_flag",
                            formula=f"{column}.dt.dayofweek >= 5",
                            reason="Weekend flags can reveal different buying or operational behaviour.",
                            priority="medium",
                            executable=True,
                            confidence=0.84,
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
                    formula=f"bin {age} into 18-24, 25-34, 35-44, 45-54, 55+",
                    reason="Age groups are often more interpretable than raw age and support segmentation.",
                    priority="high",
                    executable=True,
                    confidence=0.88,
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

    def _bounded_numeric_features(self, df: pd.DataFrame) -> list[FeatureRecommendation]:
        recommendations = []

        for column in df.select_dtypes(include="number").columns:
            lower_name = column.lower()
            series = pd.to_numeric(df[column], errors="coerce").dropna()

            if series.empty:
                continue

            if self._is_binary(series):
                continue

            if self._is_rate_or_percentage(column, series):
                recommendations.append(
                    FeatureRecommendation(
                        feature_name=f"{column}_level",
                        source_columns=[column],
                        feature_type="binning",
                        formula=f"bin {column} into low, medium, high",
                        reason=f"{column} appears to be a bounded rate/percentage. Binning may make it more interpretable than log transformation.",
                        priority="medium",
                        executable=False,
                        confidence=0.82,
                    )
                )

        return recommendations

    def _skew_transform_features(
        self,
        df: pd.DataFrame,
        target: str | None = None,
    ) -> list[FeatureRecommendation]:
        recommendations = []

        numeric_columns = list(df.select_dtypes(include="number").columns)

        for column in numeric_columns:
            if column == target:
                continue

            series = pd.to_numeric(df[column], errors="coerce").dropna()

            if series.empty:
                continue

            if self._is_binary(series):
                continue

            if self._is_rate_or_percentage(column, series):
                continue

            if self._looks_like_identifier(column, series):
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

    def _is_binary(self, series: pd.Series) -> bool:
        values = set(series.dropna().unique().tolist())
        return values.issubset({0, 1, 0.0, 1.0}) and len(values) <= 2

    def _is_rate_or_percentage(self, column: str, series: pd.Series) -> bool:
        name = column.lower()

        name_suggests_rate = any(
            keyword in name
            for keyword in ["rate", "ratio", "percent", "percentage", "margin"]
        )

        bounded_between_zero_and_one = series.min() >= 0 and series.max() <= 1

        return name_suggests_rate or bounded_between_zero_and_one

    def _looks_like_identifier(self, column: str, series: pd.Series) -> bool:
        name = column.lower()

        if "id" in name:
            return True

        unique_ratio = series.nunique(dropna=True) / max(len(series), 1)

        return unique_ratio > 0.9

    def _sort_recommendations(
        self,
        recommendations: list[FeatureRecommendation],
    ) -> list[FeatureRecommendation]:
        priority_order = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }

        return sorted(
            recommendations,
            key=lambda rec: (
                priority_order.get(rec.priority, 3),
                -rec.confidence,
                rec.feature_name,
            ),
        )
    def apply(
        self,
        df: pd.DataFrame,
        feature_report: FeatureEngineeringReport,
        selected_features: list[str] | None = None,
    ) -> pd.DataFrame:
        engineered_df = df.copy()

        selected = set(selected_features) if selected_features else None

        for recommendation in feature_report.recommendations:
            if not recommendation.executable:
                continue

            if selected is not None and recommendation.feature_name not in selected:
                continue

            engineered_df = self._apply_recommendation(
                engineered_df,
                recommendation,
            )

        return engineered_df

    def _apply_recommendation(
        self,
        df: pd.DataFrame,
        recommendation: FeatureRecommendation,
    ) -> pd.DataFrame:
        name = recommendation.feature_name
        source = recommendation.source_columns

        if name in df.columns:
            return df

        if recommendation.feature_type in ["date_part", "date_flag"]:
            column = source[0]

            if column not in df.columns:
                return df

            date_series = pd.to_datetime(df[column], errors="coerce")

            if name.endswith("_year"):
                df[name] = date_series.dt.year

            elif name.endswith("_month"):
                df[name] = date_series.dt.month

            elif name.endswith("_quarter"):
                df[name] = date_series.dt.quarter

            elif name.endswith("_weekday"):
                df[name] = date_series.dt.dayofweek

            elif name.endswith("_is_weekend"):
                df[name] = date_series.dt.dayofweek.isin([5, 6]).astype(int)

            return df

        if name == "revenue_per_unit":
            revenue, quantity = source
            df[name] = df[revenue] / df[quantity].replace(0, np.nan)
            return df

        if name == "profit_margin":
            profit, revenue = source
            df[name] = df[profit] / df[revenue].replace(0, np.nan)
            return df

        if name == "discount_intensity":
            discount_amount, gross_sales = source
            df[name] = df[discount_amount] / df[gross_sales].replace(0, np.nan)
            return df

        if name == "cost_to_revenue_ratio":
            cost, revenue = source
            df[name] = df[cost] / df[revenue].replace(0, np.nan)
            return df

        if name == "high_value_transaction":
            revenue = source[0]
            threshold = df[revenue].quantile(0.75)
            df[name] = (df[revenue] >= threshold).astype(int)
            return df

        if name == "is_returned_order":
            returned = source[0]
            df[name] = (df[returned] == 1).astype(int)
            return df

        if name == "customer_age_group":
            age = source[0]
            df[name] = pd.cut(
                df[age],
                bins=[17, 24, 34, 44, 54, np.inf],
                labels=["18-24", "25-34", "35-44", "45-54", "55+"],
            )
            return df

        if recommendation.feature_type == "transformation" and name.startswith("log_"):
            column = source[0]
            df[name] = np.log1p(pd.to_numeric(df[column], errors="coerce"))
            return df

        return df