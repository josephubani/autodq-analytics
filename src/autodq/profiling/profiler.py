import pandas as pd


def generate_profile(df: pd.DataFrame, dataset_path: str | None = None) -> dict:
    """
    Generate a basic profile report for a pandas DataFrame.
    """

    profile = {
        "dataset_path": dataset_path,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "data_types": df.dtypes.astype(str).to_dict(),
        "missing_values": df.isna().sum().astype(int).to_dict(),
        "missing_percentages": (df.isna().mean() * 100).round(2).to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_columns": list(df.select_dtypes(include=["number"]).columns),
        "categorical_columns": list(df.select_dtypes(include=["object", "category"]).columns),
        "datetime_columns": list(df.select_dtypes(include=["datetime"]).columns),
    }

    return profile