from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


SEVERITY_LEVELS = {"never": 4, "error": 3, "warning": 2, "info": 1}
VALID_SEVERITIES = {"error", "warning", "info"}


def serializable(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serializable(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _severity(value: str, *, allow_ignore: bool = False) -> str:
    normalized = str(value).lower().strip()
    valid = VALID_SEVERITIES | ({"ignore"} if allow_ignore else set())
    if normalized not in valid:
        labels = ", ".join(sorted(valid))
        raise ValueError(f"Severity must be one of: {labels}.")
    return normalized


@dataclass(slots=True)
class SchemaColumn:
    name: str
    dtype: str | None = None
    required: bool = True
    nullable: bool = True
    unique: bool = False
    minimum: Any = None
    maximum: Any = None
    allowed_values: list[Any] | None = None
    pattern: str | None = None
    severity: str = "error"

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValueError("Schema column name cannot be empty.")
        if self.dtype is not None:
            self.dtype = str(self.dtype).lower().strip()
        self.severity = _severity(self.severity)
        if self.allowed_values is not None:
            self.allowed_values = list(self.allowed_values)

    @property
    def rule_count(self) -> int:
        return sum(
            [
                self.required,
                self.dtype is not None,
                not self.nullable,
                self.unique,
                self.minimum is not None,
                self.maximum is not None,
                self.allowed_values is not None,
                self.pattern is not None,
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "required": self.required,
            "nullable": self.nullable,
            "unique": self.unique,
            "minimum": serializable(self.minimum),
            "maximum": serializable(self.maximum),
            "allowed_values": serializable(self.allowed_values),
            "pattern": self.pattern,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SchemaColumn":
        if not isinstance(payload, dict):
            raise ValueError("Schema column must be a dictionary.")
        try:
            return cls(
                name=payload["name"],
                dtype=payload.get("dtype"),
                required=bool(payload.get("required", True)),
                nullable=bool(payload.get("nullable", True)),
                unique=bool(payload.get("unique", False)),
                minimum=payload.get("minimum"),
                maximum=payload.get("maximum"),
                allowed_values=payload.get("allowed_values"),
                pattern=payload.get("pattern"),
                severity=payload.get("severity", "error"),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Invalid schema column data.") from error


@dataclass(slots=True)
class SchemaContract:
    name: str
    dataset: str
    columns: dict[str, SchemaColumn]
    extra_columns: str = "warning"
    contract_version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    FORMAT_VERSION = 1

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        self.dataset = str(self.dataset).strip()
        self.contract_version = str(self.contract_version).strip()
        self.extra_columns = _severity(self.extra_columns, allow_ignore=True)
        if not self.name:
            raise ValueError("Schema contract name cannot be empty.")
        if not self.contract_version:
            raise ValueError("Schema contract version cannot be empty.")
        normalized = {}
        for name, column in self.columns.items():
            item = column if isinstance(column, SchemaColumn) else SchemaColumn.from_dict(column)
            if item.name != str(name):
                item.name = str(name)
            normalized[item.name] = item
        self.columns = normalized

    @property
    def column_count(self) -> int:
        return len(self.columns)

    @property
    def rule_count(self) -> int:
        return sum(item.rule_count for item in self.columns.values())

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "column": item.name,
                    "dtype": item.dtype,
                    "required": item.required,
                    "nullable": item.nullable,
                    "unique": item.unique,
                    "minimum": item.minimum,
                    "maximum": item.maximum,
                    "allowed_values": item.allowed_values,
                    "pattern": item.pattern,
                    "severity": item.severity,
                }
                for item in self.columns.values()
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": self.FORMAT_VERSION,
            "name": self.name,
            "contract_version": self.contract_version,
            "dataset": self.dataset,
            "extra_columns": self.extra_columns,
            "column_count": self.column_count,
            "rule_count": self.rule_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": serializable(self.metadata),
            "columns": [item.to_dict() for item in self.columns.values()],
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
        *,
        name: str | None = None,
    ) -> "SchemaContract":
        if not isinstance(payload, dict) or payload.get("format_version") != 1:
            raise ValueError("Unsupported schema contract format.")
        columns = payload.get("columns")
        if not isinstance(columns, list):
            raise ValueError("Schema contract columns must be a list.")
        try:
            items = [SchemaColumn.from_dict(item) for item in columns]
            return cls(
                name=name or payload["name"],
                contract_version=payload.get("contract_version", "1.0.0"),
                dataset=payload.get("dataset", "unknown"),
                extra_columns=payload.get("extra_columns", "warning"),
                columns={item.name: item for item in items},
                created_at=datetime.fromisoformat(payload["created_at"]),
                updated_at=datetime.fromisoformat(payload["updated_at"]),
                metadata=dict(payload.get("metadata", {})),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Invalid schema contract data.") from error


@dataclass(slots=True)
class SchemaValidationResult:
    rule: str
    passed: bool
    severity: str
    column: str | None
    observed: Any
    expected: Any
    failed_count: int
    total_count: int
    message: str

    def __post_init__(self) -> None:
        self.severity = _severity(self.severity)

    @property
    def status(self) -> str:
        return "passed" if self.passed else "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "status": self.status,
            "passed": self.passed,
            "severity": self.severity,
            "column": self.column,
            "observed": serializable(self.observed),
            "expected": serializable(self.expected),
            "failed_count": self.failed_count,
            "total_count": self.total_count,
            "message": self.message,
        }


@dataclass(slots=True)
class SchemaValidationReport:
    contract_name: str
    contract_version: str
    dataset: str
    results: list[SchemaValidationResult]
    fail_on: str = "error"
    generated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        self.fail_on = str(self.fail_on).lower().strip()
        if self.fail_on not in SEVERITY_LEVELS:
            raise ValueError("FAIL_ON must be error, warning, info, or never.")

    @property
    def test_count(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(item.passed for item in self.results)

    @property
    def failed_count(self) -> int:
        return self.test_count - self.passed_count

    @property
    def blocking_failure_count(self) -> int:
        threshold = SEVERITY_LEVELS[self.fail_on]
        return sum(
            not item.passed and SEVERITY_LEVELS[item.severity] >= threshold
            for item in self.results
        )

    @property
    def success(self) -> bool:
        return self.blocking_failure_count == 0

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([item.to_dict() for item in self.results])

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_name": self.contract_name,
            "contract_version": self.contract_version,
            "dataset": self.dataset,
            "success": self.success,
            "fail_on": self.fail_on,
            "test_count": self.test_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "blocking_failure_count": self.blocking_failure_count,
            "results": [item.to_dict() for item in self.results],
            "generated_at": self.generated_at.isoformat(),
        }

    def to_notebook_html(self) -> str:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(item.rule)}</td>"
            f"<td>{html.escape(item.column or 'Dataset')}</td>"
            f"<td><span class='autodq-schema-status autodq-schema-status--{item.status}'>{item.status.title()}</span></td>"
            f"<td>{html.escape(item.severity)}</td>"
            f"<td>{html.escape(str(serializable(item.observed)))}</td>"
            f"<td>{html.escape(str(serializable(item.expected)))}</td>"
            f"<td>{html.escape(item.message)}</td>"
            "</tr>"
            for item in self.results
        )
        return f"""<style>
.autodq-schema{{color:var(--vscode-foreground,#172033);font-family:var(--vscode-font-family,system-ui)}}
.autodq-schema-grid{{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));margin:12px 0}}
.autodq-schema-card{{border:1px solid var(--vscode-panel-border,#d9e2ef);border-radius:8px;padding:9px}}
.autodq-schema-card span{{color:var(--vscode-descriptionForeground,#64748b);display:block;font-size:11px;text-transform:uppercase}}
.autodq-schema-card strong{{font-size:18px}}
.autodq-schema table{{border-collapse:collapse;font-size:12px;width:100%}}
.autodq-schema th,.autodq-schema td{{border-bottom:1px solid var(--vscode-panel-border,#d9e2ef);padding:6px 8px;text-align:left;vertical-align:top}}
.autodq-schema-status{{border-radius:999px;padding:2px 7px;font-size:10px;font-weight:700}}
.autodq-schema-status--passed{{background:var(--vscode-testing-iconPassed,#166534);color:#fff}}
.autodq-schema-status--failed{{background:var(--vscode-testing-iconFailed,#991b1b);color:#fff}}
</style><section class="autodq-schema">
<h2>Schema Contract Validation</h2>
<p>{html.escape(self.contract_name)} {html.escape(self.contract_version)} against {html.escape(self.dataset)}</p>
<div class="autodq-schema-grid">
<div class="autodq-schema-card"><span>Status</span><strong>{'Passed' if self.success else 'Failed'}</strong></div>
<div class="autodq-schema-card"><span>Checks passed</span><strong>{self.passed_count}/{self.test_count}</strong></div>
<div class="autodq-schema-card"><span>Failures</span><strong>{self.failed_count}</strong></div>
<div class="autodq-schema-card"><span>Blocking</span><strong>{self.blocking_failure_count}</strong></div>
</div><table><thead><tr><th>Rule</th><th>Column</th><th>Status</th><th>Severity</th><th>Observed</th><th>Expected</th><th>Message</th></tr></thead><tbody>{rows}</tbody></table></section>"""


@dataclass(slots=True)
class DriftColumnBaseline:
    name: str
    dtype: str
    kind: str
    missing_percent: float
    distinct_count: int
    distinct_ratio: float
    minimum: Any = None
    maximum: Any = None
    bin_edges: list[float] = field(default_factory=list)
    distribution: dict[str, float] = field(default_factory=dict)
    categories: list[str] = field(default_factory=list)
    categories_complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "kind": self.kind,
            "missing_percent": self.missing_percent,
            "distinct_count": self.distinct_count,
            "distinct_ratio": self.distinct_ratio,
            "minimum": serializable(self.minimum),
            "maximum": serializable(self.maximum),
            "bin_edges": self.bin_edges,
            "distribution": self.distribution,
            "categories": self.categories,
            "categories_complete": self.categories_complete,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DriftColumnBaseline":
        if not isinstance(payload, dict):
            raise ValueError("Drift baseline column must be a dictionary.")
        try:
            return cls(
                name=str(payload["name"]),
                dtype=str(payload["dtype"]),
                kind=str(payload["kind"]),
                missing_percent=float(payload["missing_percent"]),
                distinct_count=int(payload["distinct_count"]),
                distinct_ratio=float(payload["distinct_ratio"]),
                minimum=payload.get("minimum"),
                maximum=payload.get("maximum"),
                bin_edges=[float(item) for item in payload.get("bin_edges", [])],
                distribution={
                    str(key): float(value)
                    for key, value in payload.get("distribution", {}).items()
                },
                categories=[str(item) for item in payload.get("categories", [])],
                categories_complete=bool(payload.get("categories_complete", False)),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Invalid drift baseline column data.") from error


@dataclass(slots=True)
class DriftBaseline:
    name: str
    dataset: str
    row_count: int
    column_count: int
    duplicate_percent: float
    columns: dict[str, DriftColumnBaseline]
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    FORMAT_VERSION = 1

    @property
    def profiled_column_count(self) -> int:
        return len(self.columns)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "column": item.name,
                    "dtype": item.dtype,
                    "kind": item.kind,
                    "missing_percent": item.missing_percent,
                    "distinct_count": item.distinct_count,
                    "distinct_ratio": item.distinct_ratio,
                    "minimum": item.minimum,
                    "maximum": item.maximum,
                    "distribution_buckets": len(item.distribution),
                }
                for item in self.columns.values()
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": self.FORMAT_VERSION,
            "name": self.name,
            "dataset": self.dataset,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "duplicate_percent": self.duplicate_percent,
            "profiled_column_count": self.profiled_column_count,
            "created_at": self.created_at.isoformat(),
            "metadata": serializable(self.metadata),
            "columns": [item.to_dict() for item in self.columns.values()],
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
        *,
        name: str | None = None,
    ) -> "DriftBaseline":
        if not isinstance(payload, dict) or payload.get("format_version") != 1:
            raise ValueError("Unsupported drift baseline format.")
        columns = payload.get("columns")
        if not isinstance(columns, list):
            raise ValueError("Drift baseline columns must be a list.")
        try:
            items = [DriftColumnBaseline.from_dict(item) for item in columns]
            return cls(
                name=name or str(payload["name"]),
                dataset=str(payload.get("dataset", "unknown")),
                row_count=int(payload["row_count"]),
                column_count=int(payload["column_count"]),
                duplicate_percent=float(payload.get("duplicate_percent", 0.0)),
                columns={item.name: item for item in items},
                created_at=datetime.fromisoformat(payload["created_at"]),
                metadata=dict(payload.get("metadata", {})),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Invalid drift baseline data.") from error


@dataclass(slots=True)
class DriftResult:
    metric: str
    status: str
    severity: str
    column: str | None
    reference: Any
    current: Any
    difference: Any
    message: str

    def __post_init__(self) -> None:
        self.status = str(self.status).lower().strip()
        if self.status not in {"stable", "moderate", "major"}:
            raise ValueError("Drift status must be stable, moderate, or major.")
        self.severity = _severity(self.severity)

    @property
    def passed(self) -> bool:
        return self.status == "stable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "column": self.column,
            "status": self.status,
            "severity": self.severity,
            "reference": serializable(self.reference),
            "current": serializable(self.current),
            "difference": serializable(self.difference),
            "message": self.message,
        }


@dataclass(slots=True)
class DriftReport:
    baseline_name: str
    baseline_dataset: str
    dataset: str
    results: list[DriftResult]
    fail_on: str = "error"
    contract_name: str | None = None
    generated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        self.fail_on = str(self.fail_on).lower().strip()
        if self.fail_on not in SEVERITY_LEVELS:
            raise ValueError("FAIL_ON must be error, warning, info, or never.")

    @property
    def check_count(self) -> int:
        return len(self.results)

    @property
    def stable_count(self) -> int:
        return sum(item.status == "stable" for item in self.results)

    @property
    def moderate_count(self) -> int:
        return sum(item.status == "moderate" for item in self.results)

    @property
    def major_count(self) -> int:
        return sum(item.status == "major" for item in self.results)

    @property
    def blocking_failure_count(self) -> int:
        threshold = SEVERITY_LEVELS[self.fail_on]
        return sum(
            not item.passed and SEVERITY_LEVELS[item.severity] >= threshold
            for item in self.results
        )

    @property
    def success(self) -> bool:
        return self.blocking_failure_count == 0

    @property
    def stability_score(self) -> float:
        if not self.results:
            return 100.0
        earned = self.stable_count + 0.5 * self.moderate_count
        return round(earned / self.check_count * 100, 2)

    @property
    def drifted_columns(self) -> list[str]:
        return sorted(
            {
                item.column
                for item in self.results
                if item.column is not None and not item.passed
            }
        )

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([item.to_dict() for item in self.results])

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_name": self.baseline_name,
            "baseline_dataset": self.baseline_dataset,
            "dataset": self.dataset,
            "contract_name": self.contract_name,
            "success": self.success,
            "fail_on": self.fail_on,
            "stability_score": self.stability_score,
            "score_formula": "(stable checks + 0.5 × moderate checks) / all checks × 100",
            "check_count": self.check_count,
            "stable_count": self.stable_count,
            "moderate_count": self.moderate_count,
            "major_count": self.major_count,
            "blocking_failure_count": self.blocking_failure_count,
            "drifted_columns": self.drifted_columns,
            "results": [item.to_dict() for item in self.results],
            "generated_at": self.generated_at.isoformat(),
        }

    def to_notebook_html(self) -> str:
        rows = "".join(
            "<tr>"
            f"<td>{html.escape(item.column or 'Dataset')}</td>"
            f"<td>{html.escape(item.metric.replace('_', ' ').title())}</td>"
            f"<td><span class='autodq-drift-status autodq-drift-status--{item.status}'>{item.status.title()}</span></td>"
            f"<td>{html.escape(item.severity)}</td>"
            f"<td>{html.escape(str(serializable(item.reference)))}</td>"
            f"<td>{html.escape(str(serializable(item.current)))}</td>"
            f"<td>{html.escape(item.message)}</td>"
            "</tr>"
            for item in self.results
        )
        return f"""<style>
.autodq-drift{{color:var(--vscode-foreground,#172033);font-family:var(--vscode-font-family,system-ui)}}
.autodq-drift-grid{{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));margin:12px 0}}
.autodq-drift-card{{border:1px solid var(--vscode-panel-border,#d9e2ef);border-radius:8px;padding:9px}}
.autodq-drift-card span{{color:var(--vscode-descriptionForeground,#64748b);display:block;font-size:11px;text-transform:uppercase}}
.autodq-drift-card strong{{font-size:18px}}
.autodq-drift table{{border-collapse:collapse;font-size:12px;width:100%}}
.autodq-drift th,.autodq-drift td{{border-bottom:1px solid var(--vscode-panel-border,#d9e2ef);padding:6px 8px;text-align:left;vertical-align:top}}
.autodq-drift-status{{border-radius:999px;padding:2px 7px;font-size:10px;font-weight:700;color:#fff}}
.autodq-drift-status--stable{{background:var(--vscode-testing-iconPassed,#166534)}}
.autodq-drift-status--moderate{{background:var(--vscode-editorWarning-foreground,#92400e)}}
.autodq-drift-status--major{{background:var(--vscode-testing-iconFailed,#991b1b)}}
</style><section class="autodq-drift">
<h2>Data Drift Detection</h2>
<p>{html.escape(self.dataset)} compared with {html.escape(self.baseline_name)} ({html.escape(self.baseline_dataset)})</p>
<div class="autodq-drift-grid">
<div class="autodq-drift-card"><span>Stability score</span><strong>{self.stability_score:.2f}</strong></div>
<div class="autodq-drift-card"><span>Stable checks</span><strong>{self.stable_count}</strong></div>
<div class="autodq-drift-card"><span>Moderate</span><strong>{self.moderate_count}</strong></div>
<div class="autodq-drift-card"><span>Major</span><strong>{self.major_count}</strong></div>
<div class="autodq-drift-card"><span>Blocking</span><strong>{self.blocking_failure_count}</strong></div>
</div>
<p><strong>Score:</strong> (stable checks + 0.5 × moderate checks) ÷ all checks × 100.</p>
<table><thead><tr><th>Column</th><th>Metric</th><th>Status</th><th>Severity</th><th>Baseline</th><th>Current</th><th>Explanation</th></tr></thead><tbody>{rows}</tbody></table></section>"""
