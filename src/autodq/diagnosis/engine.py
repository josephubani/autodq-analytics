import pandas as pd

from autodq.diagnosis.missingness import analyze_missing_values
from autodq.diagnosis.duplicates import analyze_duplicates


def run_diagnosis(df: pd.DataFrame) -> dict:
    """
    Run all diagnosis checks on a DataFrame.
    """

    missing_report = analyze_missing_values(df)
    duplicate_report = analyze_duplicates(df)

    issues = []

    if missing_report["total_missing_values"] > 0:
        issues.append(
            {
                "issue_type": "missing_values",
                "severity": _highest_missing_severity(missing_report),
                "message": (
                    f"{missing_report['total_missing_values']} missing values found "
                    f"across {missing_report['columns_affected']} columns."
                ),
            }
        )

    if duplicate_report["has_duplicates"]:
        issues.append(
            {
                "issue_type": "duplicate_rows",
                "severity": duplicate_report["severity"],
                "message": (
                    f"{duplicate_report['duplicate_rows']} duplicate rows found "
                    f"({duplicate_report['duplicate_percentage']}% of dataset)."
                ),
            }
        )

    return {
        "missing_values": missing_report,
        "duplicates": duplicate_report,
        "issue_count": len(issues),
        "issues": issues,
    }


def _highest_missing_severity(missing_report: dict) -> str:
    """
    Return the highest severity among columns with missing values.
    """

    severity_rank = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    highest = "none"

    for column_info in missing_report["columns_with_missing"].values():
        if severity_rank[column_info["severity"]] > severity_rank[highest]:
            highest = column_info["severity"]

    return highest