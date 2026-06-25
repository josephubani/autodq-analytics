import pandas as pd


def analyze_duplicates(df: pd.DataFrame) -> dict:
    """
    Analyze duplicate rows in a DataFrame.
    """

    duplicate_mask = df.duplicated()
    duplicate_count = int(duplicate_mask.sum())
    duplicate_percentage = round((duplicate_count / len(df)) * 100, 2) if len(df) > 0 else 0

    return {
        "duplicate_rows": duplicate_count,
        "duplicate_percentage": duplicate_percentage,
        "has_duplicates": duplicate_count > 0,
        "severity": _get_duplicate_severity(duplicate_percentage),
    }


def _get_duplicate_severity(duplicate_percentage: float) -> str:
    """
    Classify duplicate row severity.
    """

    if duplicate_percentage == 0:
        return "none"

    if duplicate_percentage < 2:
        return "low"

    if duplicate_percentage < 10:
        return "medium"

    if duplicate_percentage < 25:
        return "high"

    return "critical"