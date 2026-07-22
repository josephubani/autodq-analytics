from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def serializable_value(value: Any) -> Any:
    """Convert pandas and NumPy values into report-safe values."""
    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, (datetime, date, pd.Timestamp, Path)):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): serializable_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [serializable_value(item) for item in value]

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    return value


@dataclass(slots=True)
class AuditEntry:
    audit_id: int
    event_type: str
    actor: str = "user"
    action_id: int | None = None
    row_index: Any | None = None
    column: str | None = None
    old_value: Any | None = None
    new_value: Any | None = None
    reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "action_id": self.action_id,
            "row_index": serializable_value(self.row_index),
            "column": self.column,
            "old_value": serializable_value(self.old_value),
            "new_value": serializable_value(self.new_value),
            "reason": self.reason,
            "details": serializable_value(self.details),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass(slots=True)
class DomainRule:
    rule_id: str
    column: str
    min_value: Any | None = None
    max_value: Any | None = None
    allowed_values: list[Any] | None = None
    pattern: str | None = None
    nullable: bool = True
    unique: bool = False
    description: str | None = None
    source: str = "custom"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "column": self.column,
            "min_value": serializable_value(self.min_value),
            "max_value": serializable_value(self.max_value),
            "allowed_values": serializable_value(self.allowed_values),
            "pattern": self.pattern,
            "nullable": self.nullable,
            "unique": self.unique,
            "description": self.description,
            "source": self.source,
        }


@dataclass(slots=True)
class DomainViolation:
    rule_id: str
    row_index: Any
    column: str
    value: Any
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "row_index": serializable_value(self.row_index),
            "column": self.column,
            "value": serializable_value(self.value),
            "code": self.code,
            "message": self.message,
        }


@dataclass(slots=True)
class DomainValidationReport:
    rules: list[DomainRule] = field(default_factory=list)
    violations: list[DomainViolation] = field(default_factory=list)
    checked_rows: int = 0
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def rule_count(self) -> int:
        return len(self.rules)

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def invalid_row_count(self) -> int:
        return len(
            {
                serializable_value(item.row_index)
                for item in self.violations
            }
        )

    @property
    def is_valid(self) -> bool:
        return self.violation_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_count": self.rule_count,
            "violation_count": self.violation_count,
            "invalid_row_count": self.invalid_row_count,
            "checked_rows": self.checked_rows,
            "is_valid": self.is_valid,
            "generated_at": self.generated_at.isoformat(),
            "rules": [rule.to_dict() for rule in self.rules],
            "violations": [item.to_dict() for item in self.violations],
        }

    def to_html(self) -> str:
        from autodq.review.notebook_renderer import ReviewNotebookRenderer

        return ReviewNotebookRenderer().render_domain_report(self)

    def _repr_html_(self) -> str:
        return self.to_html()


@dataclass(slots=True)
class OutlierRecord:
    row_index: Any
    column: str
    value: float
    lower_bound: float
    upper_bound: float
    direction: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_index": serializable_value(self.row_index),
            "column": self.column,
            "value": self.value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "direction": self.direction,
        }


@dataclass(slots=True)
class OutlierReviewReport:
    records: list[OutlierRecord] = field(default_factory=list)
    method: str = "IQR"
    multiplier: float = 1.5
    checked_columns: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def outlier_count(self) -> int:
        return len(self.records)

    @property
    def columns(self) -> list[str]:
        return sorted({item.column for item in self.records})

    @property
    def column_count(self) -> int:
        return len(self.columns)

    def for_column(self, column: str) -> list[OutlierRecord]:
        return [item for item in self.records if item.column == column]

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "multiplier": self.multiplier,
            "checked_columns": self.checked_columns,
            "outlier_count": self.outlier_count,
            "column_count": self.column_count,
            "columns": self.columns,
            "generated_at": self.generated_at.isoformat(),
            "records": [item.to_dict() for item in self.records],
        }

    def to_html(self) -> str:
        from autodq.review.notebook_renderer import ReviewNotebookRenderer

        return ReviewNotebookRenderer().render_outlier_report(self)

    def _repr_html_(self) -> str:
        return self.to_html()


@dataclass(slots=True)
class CleaningActionPreview:
    action_id: int
    issue_type: str
    strategy: str
    status: str
    affected_row_count: int
    details: dict[str, Any] = field(default_factory=dict)
    before_sample: list[dict[str, Any]] = field(default_factory=list)
    after_sample: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "issue_type": self.issue_type,
            "strategy": self.strategy,
            "status": self.status,
            "affected_row_count": self.affected_row_count,
            "details": serializable_value(self.details),
            "before_sample": serializable_value(self.before_sample),
            "after_sample": serializable_value(self.after_sample),
        }

    def to_html(self) -> str:
        from autodq.review.notebook_renderer import ReviewNotebookRenderer

        return ReviewNotebookRenderer().render_action_previews([self])

    def _repr_html_(self) -> str:
        return self.to_html()


@dataclass(slots=True)
class CleaningPreviewReport:
    previews: list[CleaningActionPreview] = field(default_factory=list)

    @property
    def action_count(self) -> int:
        return len(self.previews)

    def get(self, action_id: int) -> CleaningActionPreview:
        for preview in self.previews:
            if preview.action_id == action_id:
                return preview

        raise KeyError(f"Cleaning preview was not found: {action_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_count": self.action_count,
            "previews": [item.to_dict() for item in self.previews],
        }

    def to_html(self) -> str:
        from autodq.review.notebook_renderer import ReviewNotebookRenderer

        return ReviewNotebookRenderer().render_action_previews(self.previews)

    def _repr_html_(self) -> str:
        return self.to_html()


@dataclass(slots=True)
class CleaningReview:
    original_data: pd.DataFrame = field(repr=False)
    working_data: pd.DataFrame = field(repr=False)
    decision_plan: Any = field(repr=False)
    preview_report: Any | None = field(default=None, repr=False)
    domain_rules: list[DomainRule] = field(default_factory=list)
    domain_report: DomainValidationReport | None = None
    outlier_report: OutlierReviewReport | None = None
    audit_trail: list[AuditEntry] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    auto_display: bool = field(default=True, repr=False)
    _engine: Any = field(default=None, repr=False)

    @property
    def actions(self) -> list[Any]:
        return list(self.decision_plan.actions)

    @property
    def action_count(self) -> int:
        return len(self.actions)

    @property
    def pending_count(self) -> int:
        return sum(1 for item in self.actions if item.status == "pending")

    @property
    def approved_count(self) -> int:
        return sum(1 for item in self.actions if item.status == "approved")

    @property
    def rejected_count(self) -> int:
        return sum(1 for item in self.actions if item.status == "rejected")

    @property
    def audit_count(self) -> int:
        return len(self.audit_trail)

    @property
    def changed(self) -> bool:
        return not self.working_data.equals(self.original_data)

    def approve(self, action_ids) -> "CleaningReview":
        self._require_engine().approve(self, action_ids)
        return self

    def reject(
        self,
        action_ids,
        reason: str | None = None,
    ) -> "CleaningReview":
        self._require_engine().reject(self, action_ids, reason=reason)
        return self

    def approve_all(self) -> "CleaningReview":
        self._require_engine().approve_all(self)
        return self

    def edit_row(
        self,
        row_index,
        changes: dict[str, Any],
        reason: str | None = None,
    ) -> pd.Series:
        return self._require_engine().edit_row(
            self,
            row_index=row_index,
            changes=changes,
            reason=reason,
        )

    def preview(
        self,
        action_ids=None,
        max_rows: int = 5,
    ):
        return self._require_engine().preview_actions(
            self,
            action_ids=action_ids,
            max_rows=max_rows,
        )

    def add_domain_rule(self, column: str, **constraints) -> DomainRule:
        return self._require_engine().add_domain_rule(
            self,
            column=column,
            **constraints,
        )

    def validate_domain(self) -> DomainValidationReport:
        return self._require_engine().validate_domain(self)

    def review_outliers(
        self,
        columns: list[str] | str | None = None,
        iqr_multiplier: float = 1.5,
    ) -> OutlierReviewReport:
        return self._require_engine().detect_outliers(
            self,
            columns=columns,
            iqr_multiplier=iqr_multiplier,
        )

    def treat_outliers(
        self,
        column: str,
        strategy: str = "clip",
        **options,
    ) -> int:
        return self._require_engine().treat_outliers(
            self,
            column=column,
            strategy=strategy,
            **options,
        )

    def audit_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [entry.to_dict() for entry in self.audit_trail]
        )

    def export_audit(self, output: str | Path) -> Path:
        return self._require_engine().export_audit(self, output)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows_original": len(self.original_data),
            "rows_working": len(self.working_data),
            "action_count": self.action_count,
            "pending_count": self.pending_count,
            "approved_count": self.approved_count,
            "rejected_count": self.rejected_count,
            "changed": self.changed,
            "audit_count": self.audit_count,
            "generated_at": self.generated_at.isoformat(),
            "actions": [item.to_dict() for item in self.actions],
            "domain_rules": [rule.to_dict() for rule in self.domain_rules],
            "domain_report": (
                self.domain_report.to_dict()
                if self.domain_report is not None
                else None
            ),
            "outlier_report": (
                self.outlier_report.to_dict()
                if self.outlier_report is not None
                else None
            ),
            "audit_trail": [entry.to_dict() for entry in self.audit_trail],
        }

    def to_html(self) -> str:
        from autodq.review.notebook_renderer import ReviewNotebookRenderer

        return ReviewNotebookRenderer().render_review(self)

    def _repr_html_(self) -> str | None:
        if not self.auto_display:
            return None

        return self.to_html()

    def _require_engine(self):
        if self._engine is None:
            raise RuntimeError("Cleaning review engine is unavailable.")

        return self._engine
