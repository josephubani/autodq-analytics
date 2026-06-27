from pathlib import Path

import pandas as pd


def load_dataset(path: str | Path, sheet_name: str | int | None = 0) -> pd.DataFrame:
    """
    Load a tabular dataset from CSV or Excel.

    Supported formats:
    - .csv
    - .xlsx
    - .xls

    Parameters
    ----------
    path:
        Dataset file path.

    sheet_name:
        Excel sheet name or index. Defaults to first sheet.
        Ignored for CSV files.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)

    if suffix == ".xlsx":
        return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")

    if suffix == ".xls":
        return pd.read_excel(path, sheet_name=sheet_name, engine="xlrd")

    raise ValueError(
        f"Unsupported file format: {suffix}. "
        "Supported formats are .csv, .xlsx, and .xls."
    )