import pandas as pd
from autodq.semantics.inference import infer_semantic_types
from autodq.utils.helpers import categorical_columns

def generate_profile(df: pd.DataFrame, dataset_path: str | None = None) -> dict:
    """
    Generate a basic profile report for a pandas DataFrame.
    """
    semantic_types = infer_semantic_types(df)

    profile = {
        "dataset_path": dataset_path,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "data_types": df.dtypes.astype(str).to_dict(),
        "semantic_types": semantic_types,
        "missing_values": df.isna().sum().astype(int).to_dict(),
        "missing_percentages": (df.isna().mean() * 100).round(2).to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_columns": list(df.select_dtypes(include=["number"]).columns),
        "categorical_columns": categorical_columns(df),
        "datetime_columns": list(df.select_dtypes(include=["datetime"]).columns),
    }

    return profile
