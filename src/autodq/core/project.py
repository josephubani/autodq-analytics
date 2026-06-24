from pathlib import Path
import pandas as pd

from autodq.io.loaders import load_dataset
from autodq.profiling.profiler import generate_profile


class AutoDQ:
    """
    Main project class for AutoDQ Analytics.
    """

    def __init__(self, dataset_path: str, target: str | None = None):
        self.dataset_path = Path(dataset_path)
        self.target = target
        self.data: pd.DataFrame | None = None
        self.profile_report: dict | None = None

    def load(self) -> pd.DataFrame:
        self.data = load_dataset(self.dataset_path)
        return self.data

    def profile(self) -> dict:
        if self.data is None:
            self.load()

        self.profile_report = generate_profile(
            self.data,
            dataset_path=str(self.dataset_path)
        )

        return self.profile_report

    def show_profile(self) -> None:
        if self.profile_report is None:
            self.profile()

        report = self.profile_report

        print("\n=== AutoDQ Dataset Profile ===")
        print(f"Dataset: {report['dataset_path']}")
        print(f"Rows: {report['rows']}")
        print(f"Columns: {report['columns']}")
        print(f"Duplicate rows: {report['duplicate_rows']}")

        print("\nColumn Groups:")
        print(f"Numeric: {report['numeric_columns']}")
        print(f"Categorical: {report['categorical_columns']}")
        print(f"Datetime: {report['datetime_columns']}")

        print("\nColumns:")
        for col in report["column_names"]:
            dtype = report["data_types"][col]
            missing = report["missing_values"][col]
            missing_pct = report["missing_percentages"][col]
            print(f"- {col} | type: {dtype} | missing: {missing} ({missing_pct}%)")