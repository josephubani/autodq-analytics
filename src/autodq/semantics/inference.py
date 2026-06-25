import pandas as pd


ID_KEYWORDS = ["id", "identifier", "number", "no", "code", "key"]


def infer_semantic_types(df: pd.DataFrame) -> dict:
    """
    Infer semantic column types beyond pandas physical dtypes.
    """

    semantic_types = {}

    for column in df.columns:
        series = df[column]
        column_lower = column.lower()

        if _is_identifier(column_lower, series, len(df)):
            semantic_types[column] = "identifier"

        elif _is_datetime(series):
            semantic_types[column] = "datetime"

        elif pd.api.types.is_numeric_dtype(series):
            if _is_discrete_numeric(series):
                semantic_types[column] = "discrete_numeric"
            else:
                semantic_types[column] = "continuous_numeric"

        elif pd.api.types.is_object_dtype(series):
            semantic_types[column] = "categorical"

        else:
            semantic_types[column] = "unknown"

    return semantic_types


def _is_identifier(column_lower: str, series: pd.Series, total_rows: int) -> bool:
    """
    Detect ID-like columns.
    """

    name_suggests_id = any(keyword in column_lower for keyword in ID_KEYWORDS)

    unique_ratio = series.nunique(dropna=True) / total_rows if total_rows > 0 else 0

    mostly_unique = unique_ratio >= 0.9

    return name_suggests_id and mostly_unique


def _is_datetime(series: pd.Series) -> bool:
    """
    Detect datetime-like columns.
    """

    if pd.api.types.is_datetime64_any_dtype(series):
        return True

    if not pd.api.types.is_object_dtype(series):
        return False

    parsed = pd.to_datetime(series.dropna(), errors="coerce")
    success_rate = parsed.notna().mean() if len(parsed) > 0 else 0

    return success_rate >= 0.8


def _is_discrete_numeric(series: pd.Series) -> bool:
    """
    Detect discrete numeric columns.
    """

    non_null = series.dropna()

    if non_null.empty:
        return False

    unique_count = non_null.nunique()

    if pd.api.types.is_integer_dtype(non_null) and unique_count <= 20:
        return True

    return False