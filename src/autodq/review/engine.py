from __future__ import annotations

import copy
import json
import re
from numbers import Integral, Real
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from autodq.cleaning.engine import CleaningEngine
from autodq.decision.engine import DecisionPlan
from autodq.preview.engine import PreviewEngine
from autodq.review.models import (
    AuditEntry,
    CleaningActionPreview,
    CleaningPreviewReport,
    CleaningReview,
    DomainRule,
    DomainValidationReport,
    DomainViolation,
    OutlierRecord,
    OutlierReviewReport,
    serializable_value,
)


class CleaningReviewEngine:
    """Coordinate decisions, manual changes, rules, and audit history."""

    OUTLIER_STRATEGIES = {
        "clip",
        "winsorize",
        "median",
        "set_null",
        "remove",
        "keep",
    }

    def __init__(self):
        self.cleaning_engine = CleaningEngine()
        self.preview_engine = PreviewEngine()

    def create_review(
        self,
        *,
        df: pd.DataFrame,
        decision_plan,
        preview_report=None,
        knowledge_rules: dict | None = None,
        auto_display: bool = True,
    ) -> CleaningReview:
        review = CleaningReview(
            original_data=df.copy(deep=True),
            working_data=df.copy(deep=True),
            decision_plan=decision_plan,
            preview_report=preview_report,
            auto_display=auto_display,
            _engine=self,
        )
        self._record(
            review,
            event_type="review_started",
            actor="system",
            details={
                "rows": len(df),
                "columns": len(df.columns),
                "actions": len(decision_plan.actions),
            },
        )
        self._seed_knowledge_rules(review, knowledge_rules or {})

        if review.domain_rules:
            self.validate_domain(review)

        self.detect_outliers(review)
        return review

    def approve(self, review: CleaningReview, action_ids) -> None:
        actions = self._actions(review, action_ids)

        for action in actions:
            previous_status = action.status
            action.status = "approved"
            self._record(
                review,
                event_type="action_approved",
                action_id=action.action_id,
                old_value=previous_status,
                new_value="approved",
            )

    def reject(
        self,
        review: CleaningReview,
        action_ids,
        reason: str | None = None,
    ) -> None:
        actions = self._actions(review, action_ids)

        for action in actions:
            previous_status = action.status
            action.status = "rejected"
            self._record(
                review,
                event_type="action_rejected",
                action_id=action.action_id,
                old_value=previous_status,
                new_value="rejected",
                reason=reason,
            )

    def approve_all(self, review: CleaningReview) -> None:
        if not review.actions:
            return

        self.approve(
            review,
            [action.action_id for action in review.actions],
        )

    def edit_row(
        self,
        review: CleaningReview,
        *,
        row_index,
        changes: dict[str, Any],
        reason: str | None = None,
    ) -> pd.Series:
        self._require_unique_index(review.working_data)

        if row_index not in review.working_data.index:
            raise KeyError(f"Row index was not found: {row_index}")

        if not isinstance(changes, dict) or not changes:
            raise ValueError("changes must be a non-empty dictionary.")

        missing_columns = [
            column
            for column in changes
            if column not in review.working_data.columns
        ]

        if missing_columns:
            raise ValueError(
                "Manual edit contains unknown columns: "
                f"{missing_columns}"
            )

        old_values = {
            column: review.working_data.at[row_index, column]
            for column in changes
        }
        candidate = review.working_data.copy(deep=True)

        for column, new_value in changes.items():
            self._assign_cell(
                candidate,
                row_index=row_index,
                column=column,
                value=new_value,
            )

        review.working_data = candidate

        for column, new_value in changes.items():
            old_value = old_values[column]

            if self._values_equal(old_value, new_value):
                continue

            self._record(
                review,
                event_type="manual_cell_edit",
                row_index=row_index,
                column=column,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
            )

        review.domain_report = None
        review.outlier_report = None
        return review.working_data.loc[row_index].copy()

    def preview_actions(
        self,
        review: CleaningReview,
        *,
        action_ids=None,
        max_rows: int = 5,
    ):
        if not isinstance(max_rows, Integral) or max_rows < 1:
            raise ValueError("max_rows must be a positive integer.")

        actions = (
            review.actions
            if action_ids is None
            else self._actions(review, action_ids)
        )
        previews = [
            self._preview_action(review, action, int(max_rows))
            for action in actions
        ]

        if len(previews) == 1:
            return previews[0]

        return CleaningPreviewReport(previews=previews)

    def add_domain_rule(
        self,
        review: CleaningReview,
        *,
        column: str,
        min_value: Any | None = None,
        max_value: Any | None = None,
        allowed_values: Iterable[Any] | None = None,
        pattern: str | None = None,
        nullable: bool = True,
        unique: bool = False,
        description: str | None = None,
        source: str = "custom",
        actor: str = "user",
    ) -> DomainRule:
        if column not in review.working_data.columns:
            raise ValueError(f"Domain rule column was not found: {column}")

        if allowed_values is not None:
            if isinstance(allowed_values, (str, bytes)):
                raise ValueError(
                    "allowed_values must be a collection, not a string."
                )

            allowed_values = list(allowed_values)

            if not allowed_values:
                raise ValueError("allowed_values cannot be empty.")

        if pattern is not None:
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError(
                    f"Invalid domain regular expression: {error}"
                ) from error

        if (
            min_value is not None
            and max_value is not None
            and min_value > max_value
        ):
            raise ValueError("min_value cannot be greater than max_value.")

        if not any(
            (
                min_value is not None,
                max_value is not None,
                allowed_values is not None,
                pattern is not None,
                nullable is False,
                unique is True,
            )
        ):
            raise ValueError(
                "A domain rule must define at least one constraint."
            )

        rule = DomainRule(
            rule_id=f"domain_{len(review.domain_rules) + 1}",
            column=column,
            min_value=min_value,
            max_value=max_value,
            allowed_values=allowed_values,
            pattern=pattern,
            nullable=bool(nullable),
            unique=bool(unique),
            description=description,
            source=source,
        )
        review.domain_rules.append(rule)
        review.domain_report = None
        self._record(
            review,
            event_type="domain_rule_added",
            actor=actor,
            column=column,
            new_value=rule.to_dict(),
            reason=description,
        )
        return rule

    def validate_domain(
        self,
        review: CleaningReview,
    ) -> DomainValidationReport:
        violations = []

        for rule in review.domain_rules:
            series = review.working_data[rule.column]
            duplicate_mask = (
                series.notna() & series.duplicated(keep=False)
                if rule.unique
                else pd.Series(False, index=series.index)
            )

            for row_index, value in series.items():
                if pd.isna(value):
                    if not rule.nullable:
                        violations.append(
                            self._domain_violation(
                                rule,
                                row_index,
                                value,
                                "null",
                                "Value cannot be null.",
                            )
                        )
                    continue

                if rule.allowed_values is not None and not any(
                    self._values_equal(value, allowed)
                    for allowed in rule.allowed_values
                ):
                    violations.append(
                        self._domain_violation(
                            rule,
                            row_index,
                            value,
                            "allowed_values",
                            "Value is outside the allowed domain.",
                        )
                    )

                if rule.pattern is not None and re.fullmatch(
                    rule.pattern,
                    str(value),
                ) is None:
                    violations.append(
                        self._domain_violation(
                            rule,
                            row_index,
                            value,
                            "pattern",
                            "Value does not match the required pattern.",
                        )
                    )

                violations.extend(
                    self._range_violations(rule, row_index, value)
                )

                if bool(duplicate_mask.loc[row_index]):
                    violations.append(
                        self._domain_violation(
                            rule,
                            row_index,
                            value,
                            "unique",
                            "Value must be unique.",
                        )
                    )

        report = DomainValidationReport(
            rules=list(review.domain_rules),
            violations=violations,
            checked_rows=len(review.working_data),
        )
        review.domain_report = report
        self._record(
            review,
            event_type="domain_validation",
            actor="system",
            details={
                "rules": report.rule_count,
                "violations": report.violation_count,
                "invalid_rows": report.invalid_row_count,
            },
        )
        return report

    def detect_outliers(
        self,
        review: CleaningReview,
        *,
        columns: list[str] | str | None = None,
        iqr_multiplier: float = 1.5,
    ) -> OutlierReviewReport:
        if not isinstance(iqr_multiplier, Real) or iqr_multiplier <= 0:
            raise ValueError("iqr_multiplier must be greater than zero.")

        selected_columns = self._numeric_columns(
            review.working_data,
            columns,
        )
        records = []

        for column in selected_columns:
            records.extend(
                self._outlier_records(
                    review.working_data,
                    column,
                    float(iqr_multiplier),
                )
            )

        report = OutlierReviewReport(
            records=records,
            multiplier=float(iqr_multiplier),
            checked_columns=selected_columns,
        )
        review.outlier_report = report
        self._record(
            review,
            event_type="outlier_review",
            actor="system",
            details={
                "columns_checked": len(selected_columns),
                "columns_affected": report.column_count,
                "outliers": report.outlier_count,
                "iqr_multiplier": float(iqr_multiplier),
            },
        )
        return report

    def treat_outliers(
        self,
        review: CleaningReview,
        *,
        column: str,
        strategy: str = "clip",
        lower_bound: float | None = None,
        upper_bound: float | None = None,
        reason: str | None = None,
        iqr_multiplier: float = 1.5,
    ) -> int:
        strategy = str(strategy).lower().strip()

        if strategy not in self.OUTLIER_STRATEGIES:
            raise ValueError(
                "Unsupported outlier strategy. Choose from: "
                + ", ".join(sorted(self.OUTLIER_STRATEGIES))
            )

        self._require_unique_index(review.working_data)
        self._numeric_columns(review.working_data, [column])
        records = self._outlier_records(
            review.working_data,
            column,
            float(iqr_multiplier),
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )

        if strategy == "keep":
            self._record(
                review,
                event_type="outliers_kept",
                column=column,
                reason=reason,
                details={"outlier_count": len(records)},
            )
            return 0

        if strategy == "remove":
            row_indices = list(dict.fromkeys(item.row_index for item in records))

            for row_index in row_indices:
                self._record(
                    review,
                    event_type="manual_row_removal",
                    row_index=row_index,
                    old_value=(
                        review.working_data.loc[row_index].to_dict()
                    ),
                    new_value=None,
                    reason=reason,
                    details={
                        "column": column,
                        "strategy": strategy,
                    },
                )

            review.working_data = review.working_data.drop(
                index=row_indices
            )
            review.domain_report = None
            review.outlier_report = None
            return len(row_indices)

        inlier_values = self._inlier_values(
            review.working_data[column],
            records,
        )
        replacement = (
            float(inlier_values.median())
            if strategy == "median" and not inlier_values.empty
            else None
        )

        if pd.api.types.is_integer_dtype(
            review.working_data[column]
        ) or pd.api.types.is_bool_dtype(review.working_data[column]):
            review.working_data[column] = review.working_data[
                column
            ].astype(float)

        changed = 0

        for item in records:
            old_value = review.working_data.at[item.row_index, column]

            if strategy in {"clip", "winsorize"}:
                new_value = min(
                    max(float(old_value), item.lower_bound),
                    item.upper_bound,
                )
            elif strategy == "median":
                new_value = replacement
            else:
                new_value = np.nan

            review.working_data.at[item.row_index, column] = new_value
            changed += 1
            self._record(
                review,
                event_type="outlier_treatment",
                row_index=item.row_index,
                column=column,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
                details={
                    "strategy": strategy,
                    "lower_bound": item.lower_bound,
                    "upper_bound": item.upper_bound,
                },
            )

        review.domain_report = None
        review.outlier_report = None
        return changed

    def finalize_cleaning(
        self,
        review: CleaningReview,
        cleaned_data: pd.DataFrame,
        cleaning_report,
    ) -> None:
        for result in cleaning_report.actions:
            self._record(
                review,
                event_type="cleaning_action_executed",
                actor="system",
                action_id=result.action_id,
                details={
                    "status": result.status,
                    "message": result.message,
                    "rows_before": result.rows_before,
                    "rows_after": result.rows_after,
                },
            )

        review.working_data = cleaned_data.copy(deep=True)

        if review.domain_rules:
            self.validate_domain(review)

        self.detect_outliers(review)

    def export_audit(
        self,
        review: CleaningReview,
        output: str | Path,
    ) -> Path:
        output_path = Path(output).expanduser().resolve()
        suffix = output_path.suffix.lower()

        if suffix not in {".json", ".csv"}:
            raise ValueError("Audit output must be a .json or .csv file.")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if suffix == ".json":
            with output_path.open("w", encoding="utf-8") as stream:
                json.dump(
                    [item.to_dict() for item in review.audit_trail],
                    stream,
                    indent=2,
                    ensure_ascii=False,
                )
                stream.write("\n")
        else:
            review.audit_frame().to_csv(output_path, index=False)

        return output_path

    def _preview_action(
        self,
        review: CleaningReview,
        action,
        max_rows: int,
    ) -> CleaningActionPreview:
        before = review.working_data.copy(deep=True)
        simulated_action = copy.deepcopy(action)
        simulated_action.status = "approved"
        plan = DecisionPlan(actions=[simulated_action])
        after, _ = self.cleaning_engine.clean(before, plan)
        metadata = self.preview_engine.preview(before, plan)
        details = metadata.actions[0].details if metadata.actions else {}
        affected_indices = self._affected_indices(
            before,
            after,
            action,
            details,
        )
        return CleaningActionPreview(
            action_id=action.action_id,
            issue_type=action.issue_type,
            strategy=action.strategy,
            status=action.status,
            affected_row_count=len(affected_indices),
            details=details,
            before_sample=self._frame_records(
                before,
                affected_indices,
                max_rows,
            ),
            after_sample=self._frame_records(
                after,
                [index for index in affected_indices if index in after.index],
                max_rows,
            ),
        )

    def _affected_indices(
        self,
        before: pd.DataFrame,
        after: pd.DataFrame,
        action,
        details: dict,
    ) -> list[Any]:
        if action.issue_type == "duplicate_rows":
            return before.index[before.duplicated()].tolist()

        if action.issue_type == "missing_values":
            columns = [
                column
                for column in action.affected_columns
                if column in before.columns
            ]
            return (
                before.index[before[columns].isna().any(axis=1)].tolist()
                if columns
                else []
            )

        if action.issue_type == "outliers":
            indices = []

            for column, info in details.items():
                if column not in before.columns:
                    continue

                mask = (
                    (before[column] < info["lower_bound"])
                    | (before[column] > info["upper_bound"])
                )
                indices.extend(before.index[mask].tolist())

            return list(dict.fromkeys(indices))

        removed = before.index.difference(after.index).tolist()
        return removed

    def _seed_knowledge_rules(
        self,
        review: CleaningReview,
        knowledge_rules: dict,
    ) -> None:
        for column, knowledge_rule in knowledge_rules.items():
            if knowledge_rule is None or column not in review.working_data:
                continue

            min_value = knowledge_rule.expected_min

            if min_value is None and knowledge_rule.allow_negative is False:
                min_value = 0

            if min_value is None and knowledge_rule.expected_max is None:
                continue

            description = (
                " ".join(knowledge_rule.notes)
                if knowledge_rule.notes
                else f"AutoDQ knowledge rule: {knowledge_rule.name}"
            )
            self.add_domain_rule(
                review,
                column=column,
                min_value=min_value,
                max_value=knowledge_rule.expected_max,
                description=description,
                source="knowledge",
                actor="system",
            )

    def _range_violations(
        self,
        rule: DomainRule,
        row_index,
        value,
    ) -> list[DomainViolation]:
        violations = []

        try:
            if rule.min_value is not None and value < rule.min_value:
                violations.append(
                    self._domain_violation(
                        rule,
                        row_index,
                        value,
                        "min_value",
                        f"Value is below the minimum {rule.min_value}.",
                    )
                )

            if rule.max_value is not None and value > rule.max_value:
                violations.append(
                    self._domain_violation(
                        rule,
                        row_index,
                        value,
                        "max_value",
                        f"Value is above the maximum {rule.max_value}.",
                    )
                )
        except TypeError:
            violations.append(
                self._domain_violation(
                    rule,
                    row_index,
                    value,
                    "type",
                    "Value cannot be compared with the domain bounds.",
                )
            )

        return violations

    @staticmethod
    def _domain_violation(
        rule: DomainRule,
        row_index,
        value,
        code: str,
        message: str,
    ) -> DomainViolation:
        return DomainViolation(
            rule_id=rule.rule_id,
            row_index=row_index,
            column=rule.column,
            value=value,
            code=code,
            message=message,
        )

    def _outlier_records(
        self,
        df: pd.DataFrame,
        column: str,
        multiplier: float,
        *,
        lower_bound: float | None = None,
        upper_bound: float | None = None,
    ) -> list[OutlierRecord]:
        series = df[column].dropna()

        if series.empty:
            return []

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1

        if lower_bound is None:
            lower_bound = q1 - multiplier * iqr

        if upper_bound is None:
            upper_bound = q3 + multiplier * iqr

        lower_bound = float(lower_bound)
        upper_bound = float(upper_bound)

        if lower_bound > upper_bound:
            raise ValueError(
                "lower_bound cannot be greater than upper_bound."
            )

        mask = (series < lower_bound) | (series > upper_bound)
        return [
            OutlierRecord(
                row_index=row_index,
                column=column,
                value=float(value),
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                direction="low" if value < lower_bound else "high",
            )
            for row_index, value in series[mask].items()
        ]

    @staticmethod
    def _inlier_values(
        series: pd.Series,
        records: list[OutlierRecord],
    ) -> pd.Series:
        if not records:
            return series.dropna()

        lower_bound = records[0].lower_bound
        upper_bound = records[0].upper_bound
        return series[
            series.between(lower_bound, upper_bound, inclusive="both")
        ].dropna()

    @staticmethod
    def _numeric_columns(
        df: pd.DataFrame,
        columns: list[str] | str | None,
    ) -> list[str]:
        if columns is None:
            return list(df.select_dtypes(include="number").columns)

        if isinstance(columns, str):
            columns = [columns]
        else:
            columns = list(columns)

        missing = [column for column in columns if column not in df.columns]

        if missing:
            raise ValueError(f"Outlier columns were not found: {missing}")

        non_numeric = [
            column
            for column in columns
            if not pd.api.types.is_numeric_dtype(df[column])
        ]

        if non_numeric:
            raise ValueError(
                "Outlier review requires numeric columns: "
                f"{non_numeric}"
            )

        return columns

    @staticmethod
    def _frame_records(
        df: pd.DataFrame,
        indices: list[Any],
        max_rows: int,
    ) -> list[dict[str, Any]]:
        records = []

        for row_index in indices[:max_rows]:
            if row_index not in df.index:
                continue

            row = df.loc[row_index]

            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]

            record = {"_row_index": serializable_value(row_index)}
            record.update(
                {
                    str(column): serializable_value(value)
                    for column, value in row.items()
                }
            )
            records.append(record)

        return records

    def _actions(self, review: CleaningReview, action_ids) -> list[Any]:
        ids = self._normalize_action_ids(action_ids)
        by_id = {action.action_id: action for action in review.actions}
        missing = [action_id for action_id in ids if action_id not in by_id]

        if missing:
            raise KeyError(f"Cleaning action IDs were not found: {missing}")

        return [by_id[action_id] for action_id in ids]

    @staticmethod
    def _normalize_action_ids(action_ids) -> list[int]:
        if isinstance(action_ids, Integral) and not isinstance(
            action_ids,
            bool,
        ):
            values = [int(action_ids)]
        elif isinstance(action_ids, Iterable) and not isinstance(
            action_ids,
            (str, bytes),
        ):
            values = list(action_ids)
        else:
            raise TypeError(
                "action_ids must be an integer or an iterable of integers."
            )

        if not values or any(
            not isinstance(value, Integral) or isinstance(value, bool)
            for value in values
        ):
            raise ValueError(
                "action_ids must contain at least one integer ID."
            )

        return list(dict.fromkeys(int(value) for value in values))

    @staticmethod
    def _require_unique_index(df: pd.DataFrame) -> None:
        if not df.index.is_unique:
            raise ValueError(
                "Interactive row changes require a unique DataFrame index. "
                "Reset the index before starting the review."
            )

    @staticmethod
    def _values_equal(left, right) -> bool:
        try:
            if pd.isna(left) and pd.isna(right):
                return True
        except (TypeError, ValueError):
            pass

        try:
            return bool(left == right)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _assign_cell(
        df: pd.DataFrame,
        *,
        row_index,
        column: str,
        value,
    ) -> None:
        try:
            df.at[row_index, column] = value
            return
        except (TypeError, ValueError) as original_error:
            dtype = df[column].dtype
            is_null = False

            try:
                is_null = bool(pd.isna(value))
            except (TypeError, ValueError):
                pass

            if (
                pd.api.types.is_numeric_dtype(dtype)
                and (isinstance(value, Real) or is_null)
            ):
                df[column] = df[column].astype(float)
                df.at[row_index, column] = value
                return

            if isinstance(dtype, pd.CategoricalDtype):
                if value not in df[column].cat.categories:
                    df[column] = df[column].cat.add_categories([value])

                df.at[row_index, column] = value
                return

            raise ValueError(
                f"Value {value!r} is incompatible with column "
                f"'{column}' ({dtype})."
            ) from original_error

    def _record(
        self,
        review: CleaningReview,
        *,
        event_type: str,
        actor: str = "user",
        action_id: int | None = None,
        row_index=None,
        column: str | None = None,
        old_value=None,
        new_value=None,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            audit_id=len(review.audit_trail) + 1,
            event_type=event_type,
            actor=actor,
            action_id=action_id,
            row_index=row_index,
            column=column,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            details=details or {},
        )
        review.audit_trail.append(entry)
        return entry
