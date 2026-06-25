import pandas as pd


def analyze_outliers_iqr(df: pd.DataFrame, semantic_types: dict | None = None) -> dict:
    """
    Detect numeric outliers using the IQR method.
    """

    numeric_df = df.select_dtypes(include=["number"])

    outlier_columns = {}
    total_outlier_cells = 0

    for column in numeric_df.columns:
        series = numeric_df[column].dropna()

        if series.empty:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)

        outlier_mask = (series < lower_bound) | (series > upper_bound)
        outlier_count = int(outlier_mask.sum())

        if outlier_count > 0:
            outlier_percentage = round((outlier_count / len(df)) * 100, 2)

            outlier_columns[column] = {
                "outlier_count": outlier_count,
                "outlier_percentage": outlier_percentage,
                "lower_bound": round(float(lower_bound), 4),
                "upper_bound": round(float(upper_bound), 4),
                "severity": _get_outlier_severity(outlier_percentage),
            }

            total_outlier_cells += outlier_count

    return {
        "method": "IQR",
        "columns_with_outliers": outlier_columns,
        "total_outlier_cells": total_outlier_cells,
        "columns_affected": len(outlier_columns),
    }


def _get_outlier_severity(outlier_percentage: float) -> str:
    if outlier_percentage == 0:
        return "none"

    if outlier_percentage < 5:
        return "low"

    if outlier_percentage < 15:
        return "medium"

    if outlier_percentage < 30:
        return "high"

    return "critical"