"""Pure presentation helpers used by the AutoDQ Streamlit interface."""

from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def humanize_identifier(value: Any) -> str:
    """Return a readable UI label without changing the source identifier."""
    text = str(value)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def dataset_metrics(frame: pd.DataFrame) -> dict[str, float | int]:
    """Calculate lightweight dataset metrics without mutating the frame."""
    rows, columns = frame.shape
    cells = rows * columns
    missing = int(frame.isna().sum().sum())
    duplicates = int(frame.duplicated().sum())
    missing_percent = (missing / cells * 100) if cells else 0.0
    duplicate_percent = (duplicates / rows * 100) if rows else 0.0
    completeness = 100.0 - missing_percent

    return {
        "rows": int(rows),
        "columns": int(columns),
        "missing": missing,
        "duplicates": duplicates,
        "missing_percent": round(missing_percent, 2),
        "duplicate_percent": round(duplicate_percent, 2),
        "completeness": round(completeness, 2),
        "memory_bytes": int(frame.memory_usage(deep=True).sum()),
    }


def column_catalog(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the compact column catalogue shown in the web application."""
    rows = len(frame)
    records = []

    for column in frame.columns:
        series = frame[column]
        missing = int(series.isna().sum())
        distinct = int(series.nunique(dropna=True))

        if pd.api.types.is_datetime64_any_dtype(series):
            kind = "Datetime"
        elif pd.api.types.is_bool_dtype(series):
            kind = "Boolean"
        elif pd.api.types.is_numeric_dtype(series):
            kind = "Numeric"
        else:
            kind = "Categorical" if distinct <= max(25, rows * 0.05) else "Text"

        records.append(
            {
                "Column": humanize_identifier(column),
                "Source name": str(column),
                "Type": str(series.dtype),
                "Role": kind,
                "Missing": missing,
                "Missing %": round((missing / rows * 100) if rows else 0.0, 2),
                "Distinct": distinct,
            }
        )

    return pd.DataFrame(records)


def issue_frame(report: Any) -> pd.DataFrame:
    """Convert a diagnosis report into a concise user-facing table."""
    records = []

    for issue in getattr(report, "issues", []) or []:
        records.append(
            {
                "Issue": humanize_identifier(issue.issue_type),
                "Severity": str(issue.severity).title(),
                "Columns": ", ".join(
                    humanize_identifier(item)
                    for item in issue.affected_columns
                ) or "—",
                "Finding": issue.message,
                "Recommended response": issue.recommendation or "—",
                "Confidence": (
                    round(float(issue.confidence) * 100, 1)
                    if issue.confidence is not None
                    else None
                ),
            }
        )

    return pd.DataFrame(records)


def recommendation_frame(recommendations: list[Any] | None) -> pd.DataFrame:
    """Convert cleaning recommendations into a stable display schema."""
    records = []

    for item in recommendations or []:
        records.append(
            {
                "Issue": humanize_identifier(item.issue_type),
                "Strategy": humanize_identifier(item.strategy),
                "Priority": str(item.priority).title(),
                "Columns": ", ".join(
                    humanize_identifier(column)
                    for column in item.affected_columns
                ) or "—",
                "Action": item.action,
                "Reason": item.reason,
                "Risk": item.risk or "—",
                "Confidence": (
                    round(float(item.confidence) * 100, 1)
                    if item.confidence is not None
                    else None
                ),
            }
        )

    return pd.DataFrame(records)


def action_frame(review: Any) -> pd.DataFrame:
    """Convert review actions into a compact approval table."""
    records = []

    for item in getattr(review, "actions", []) or []:
        records.append(
            {
                "ID": int(item.action_id),
                "Status": str(item.status).title(),
                "Issue": humanize_identifier(item.issue_type),
                "Strategy": humanize_identifier(item.strategy),
                "Columns": ", ".join(
                    humanize_identifier(column)
                    for column in item.affected_columns
                ) or "—",
                "Priority": str(item.priority).title(),
                "Proposed action": item.action,
            }
        )

    return pd.DataFrame(records)


def validation_frame(report: Any) -> pd.DataFrame:
    """Create the before/after quality comparison table."""
    if report is None:
        return pd.DataFrame()

    metrics = [
        report.missing_values,
        report.duplicate_rows,
        report.rows,
        report.columns,
    ]
    return pd.DataFrame(
        [
            {
                "Metric": humanize_identifier(metric.name),
                "Before": metric.before,
                "After": metric.after,
                "Change": metric.change,
            }
            for metric in metrics
        ]
    )


def to_serializable(value: Any) -> Any:
    """Convert common AutoDQ, NumPy, and pandas values to JSON-safe data."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (datetime, date, pd.Timestamp, Path)):
        return str(value)
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, pd.Series):
        return value.to_dict()
    if is_dataclass(value):
        return to_serializable(asdict(value))
    if hasattr(value, "to_dict"):
        return to_serializable(value.to_dict())
    if isinstance(value, dict):
        return {str(key): to_serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_serializable(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def frame_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def frame_to_excel_bytes(frame: pd.DataFrame) -> bytes:
    stream = BytesIO()
    frame.to_excel(stream, index=False, engine="openpyxl")
    return stream.getvalue()
