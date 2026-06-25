import pandas as pd


def analyze_missing_values(df: pd.DataFrame) -> dict:
    """
    Analyze missing values in a DataFrame.
    """

    total_rows = len(df)
    missing_counts = df.isna().sum()
    missing_percentages = (df.isna().mean() * 100).round(2)

    columns_with_missing = {}

    for column in df.columns:
        missing_count = int(missing_counts[column])
        missing_percentage = float(missing_percentages[column])

        if missing_count > 0:
            columns_with_missing[column] = {
                "missing_count": missing_count,
                "missing_percentage": missing_percentage,
                "severity": _get_missing_severity(missing_percentage),
            }

    return {
        "total_rows": total_rows,
        "columns_with_missing": columns_with_missing,
        "total_missing_values": int(missing_counts.sum()),
        "columns_affected": len(columns_with_missing),
    }


def _get_missing_severity(missing_percentage: float) -> str:
    """
    Classify missing value severity.
    """

    if missing_percentage == 0:
        return "none"

    if missing_percentage < 5:
        return "low"

    if missing_percentage < 20:
        return "medium"

    if missing_percentage < 50:
        return "high"

    return "critical"