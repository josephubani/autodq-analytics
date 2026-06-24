from pathlib import Path
import pandas as pd


def load_dataset(path: str | Path) -> pd.DataFrame:
    """
    Load a dataset from CSV or Excel.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)

    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path)

    raise ValueError(
        f"Unsupported file type: {suffix}. Currently supported: .csv, .xlsx, .xls"
    )