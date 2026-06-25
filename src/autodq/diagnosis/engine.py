import pandas as pd
from autodq.semantics.inference import infer_semantic_types
from autodq.diagnosis.outliers import analyze_outliers_iqr
from autodq.diagnosis.missingness import analyze_missing_values
from autodq.diagnosis.duplicates import analyze_duplicates
from autodq.models.issues import DataIssue
from autodq.models.reports import DiagnosisReport


def run_diagnosis(df: pd.DataFrame) -> DiagnosisReport:
    """
    Run all diagnosis checks on a DataFrame and return a structured DiagnosisReport.
    """

    missing_report = analyze_missing_values(df)
    duplicate_report = analyze_duplicates(df)

    issues: list[DataIssue] = []

    if missing_report["total_missing_values"] > 0:
        affected_columns = list(missing_report["columns_with_missing"].keys())

        issues.append(
            DataIssue(
                issue_type="missing_values",
                severity=_highest_missing_severity(missing_report),
                message=(
                    f"{missing_report['total_missing_values']} missing values found "
                    f"across {missing_report['columns_affected']} columns."
                ),
                affected_columns=affected_columns,
                recommendation="Review affected columns and apply appropriate imputation or removal strategy.",
                confidence=0.95,
            )
        )

    if duplicate_report["has_duplicates"]:
        issues.append(
            DataIssue(
                issue_type="duplicate_rows",
                severity=duplicate_report["severity"],
                message=(
                    f"{duplicate_report['duplicate_rows']} duplicate rows found "
                    f"({duplicate_report['duplicate_percentage']}% of dataset)."
                ),
                affected_columns=[],
                recommendation="Remove duplicate rows unless duplicates represent valid repeated events.",
                confidence=0.9,
            )
        )
    semantic_types = infer_semantic_types(df)
    outlier_report = analyze_outliers_iqr(df, semantic_types=semantic_types)
    if outlier_report["total_outlier_cells"] > 0:
        affected_columns = list(outlier_report["columns_with_outliers"].keys())

        issues.append(
            DataIssue(
                issue_type="outliers",
                severity=_highest_outlier_severity(outlier_report),
                message=(
                    f"{outlier_report['total_outlier_cells']} outlier values found "
                    f"across {outlier_report['columns_affected']} numeric columns."
                ),
                affected_columns=affected_columns,
                recommendation="Review outlier values and consider IQR clipping, winsorization, transformation, or domain-based validation.",
                confidence=0.85,
            )
        )

    quality_score = _calculate_basic_quality_score(
        missing_report=missing_report,
        duplicate_report=duplicate_report,
    )

    summary = _build_summary(issues, quality_score)

    return DiagnosisReport(
        issues=issues,
        quality_score=quality_score,
        summary=summary,
        raw_details={
            "missing_values": missing_report,
            "duplicates": duplicate_report,
            "outliers": outlier_report,
            "semantic_types": semantic_types,
        },
    )


def _highest_missing_severity(missing_report: dict) -> str:
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


def _calculate_basic_quality_score(
    missing_report: dict,
    duplicate_report: dict,
) -> float:
    """
    Calculate an early-stage data quality score from 0 to 100.

    This is a simple v0.2 scoring model.
    Later, we will improve it with weighted issue categories.
    """

    score = 100.0

    total_rows = missing_report["total_rows"]
    total_missing = missing_report["total_missing_values"]
    columns_affected = missing_report["columns_affected"]

    if total_rows > 0:
        missing_penalty = min(30, (total_missing / total_rows) * 10)
        score -= missing_penalty

    score -= min(20, columns_affected * 2)

    if duplicate_report["has_duplicates"]:
        score -= min(25, duplicate_report["duplicate_percentage"] * 2)

    return round(max(score, 0), 2)


def _build_summary(issues: list[DataIssue], quality_score: float) -> str:
    if not issues:
        return "No major data quality issues detected."

    return (
        f"{len(issues)} data quality issue(s) detected. "
        f"Current dataset quality score is {quality_score}/100."
    )
def _highest_outlier_severity(outlier_report: dict) -> str:
    severity_rank = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    highest = "none"

    for column_info in outlier_report["columns_with_outliers"].values():
        if severity_rank[column_info["severity"]] > severity_rank[highest]:
            highest = column_info["severity"]

    return highest