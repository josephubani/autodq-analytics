from pathlib import Path
import pandas as pd

from autodq.io.loaders import load_dataset
from autodq.profiling.profiler import generate_profile
from autodq.diagnosis.engine import run_diagnosis


class AutoDQ:
    """
    Main project class for AutoDQ Analytics.
    """

    def __init__(self, dataset_path: str, target: str | None = None):
        self.dataset_path = Path(dataset_path)
        self.target = target

        self.data: pd.DataFrame | None = None
        self.profile_report: dict | None = None
        self.diagnosis_report = None

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

    def diagnose(self) -> dict:
        if self.data is None:
            self.load()

        self.diagnosis_report = run_diagnosis(self.data)
        return self.diagnosis_report

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

    def show_diagnosis(self) -> None:
        if self.diagnosis_report is None:
            self.diagnose()

        report = self.diagnosis_report

        print("\n=== AutoDQ Data Quality Diagnosis ===")
        print(f"Quality Score: {report.quality_score}/100")
        print(f"Issues found: {report.issue_count}")

        if report.summary:
            print(f"Summary: {report.summary}")

        if not report.has_issues():
            return

        print("\nDetected Issues:")

        for issue in report.issues:
            print(f"\n- [{issue.severity.upper()}] {issue.issue_type}")
            print(f"  Message: {issue.message}")

            if issue.affected_columns:
                print(f"  Affected Columns: {', '.join(issue.affected_columns)}")

            if issue.recommendation:
                print(f"  Recommendation: {issue.recommendation}")

            if issue.confidence is not None:
                print(f"  Confidence: {round(issue.confidence * 100, 2)}%")