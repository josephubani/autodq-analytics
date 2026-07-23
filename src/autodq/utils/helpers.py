from __future__ import annotations

import pandas as pd


def is_text_or_categorical_dtype(dtype) -> bool:
    """Return whether a pandas dtype should be analyzed as categorical text."""
    return (
        pd.api.types.is_object_dtype(dtype)
        or pd.api.types.is_string_dtype(dtype)
        or isinstance(dtype, pd.CategoricalDtype)
    )


def categorical_columns(df: pd.DataFrame) -> list[str]:
    """Select text/category columns without deprecated pandas dtype helpers."""
    return [
        column
        for column in df.columns
        if is_text_or_categorical_dtype(df[column].dtype)
    ]
