from pathlib import Path

import pandas as pd


def load_dataset(path: str | Path, sheet_name: str | int | None = 0) -> pd.DataFrame:
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


def export_dataset(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    suffix = path.suffix.lower()

    if suffix == ".csv":
        df.to_csv(path, index=False)
        return

    if suffix == ".xlsx":
        df.to_excel(path, index=False, engine="openpyxl")
        return

    raise ValueError(
        f"Unsupported export format: {suffix}. "
        "Supported export formats are .csv and .xlsx."
    )