from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api import types as ptypes

from autodq.schema_drift.models import (
    DriftBaseline,
    DriftColumnBaseline,
    DriftReport,
    DriftResult,
    SchemaColumn,
    SchemaContract,
    SchemaValidationReport,
    SchemaValidationResult,
)


SUPPORTED_DTYPES = {
    "numeric",
    "integer",
    "float",
    "string",
    "datetime",
    "boolean",
    "category",
}


def canonical_dtype(series: pd.Series) -> str:
    dtype = series.dtype
    if ptypes.is_bool_dtype(dtype):
        return "boolean"
    if ptypes.is_integer_dtype(dtype):
        return "integer"
    if ptypes.is_float_dtype(dtype):
        return "float"
    if ptypes.is_numeric_dtype(dtype):
        return "numeric"
    if ptypes.is_datetime64_any_dtype(dtype):
        return "datetime"
    if isinstance(dtype, pd.CategoricalDtype):
        return "category"
    return "string"


def validate_name(value: str, *, artifact: str) -> str:
    name = str(value).strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,127}", name):
        raise ValueError(
            f"{artifact} name must begin with a letter or underscore and "
            "contain only letters, digits, underscores, or hyphens."
        )
    return name


class SchemaContractEngine:
    """Infer, edit, validate, and persist dataset schema contracts."""

    MAX_COLUMNS = 1_000
    MAX_FILE_SIZE = 2_000_000

    def infer(
        self,
        data: pd.DataFrame,
        *,
        name: str,
        dataset: str,
        contract_version: str = "1.0.0",
        extra_columns: str = "warning",
        infer_ranges: bool = False,
        infer_categories: bool = True,
    ) -> SchemaContract:
        self._require_frame(data)
        name = validate_name(name, artifact="Schema contract")
        if len(data.columns) > self.MAX_COLUMNS:
            raise ValueError(
                f"Schema contracts support at most {self.MAX_COLUMNS:,} columns."
            )
        columns: dict[str, SchemaColumn] = {}
        for column in data.columns:
            series = data[column]
            non_null = series.dropna()
            dtype = canonical_dtype(series)
            normalized_name = re.sub(r"[^a-z0-9]+", "_", str(column).lower())
            identifier = (
                normalized_name in {"id", "key", "uuid", "identifier"}
                or normalized_name.endswith(("_id", "_key", "_uuid"))
            )
            unique = bool(
                identifier
                and len(non_null) == len(series)
                and non_null.nunique(dropna=True) == len(non_null)
            )
            minimum = None
            maximum = None
            if infer_ranges and dtype in {"integer", "float", "numeric", "datetime"}:
                if not non_null.empty:
                    minimum = non_null.min()
                    maximum = non_null.max()
            allowed_values = None
            distinct = int(non_null.nunique(dropna=True))
            if (
                infer_categories
                and dtype in {"string", "category", "boolean"}
                and distinct > 0
                and distinct <= 50
                and distinct / max(len(non_null), 1) <= 0.2
            ):
                allowed_values = [
                    value.item() if hasattr(value, "item") else value
                    for value in non_null.drop_duplicates().tolist()
                ]
            columns[str(column)] = SchemaColumn(
                name=str(column),
                dtype=dtype,
                required=True,
                nullable=bool(series.isna().any()),
                unique=unique,
                minimum=minimum,
                maximum=maximum,
                allowed_values=allowed_values,
                severity="error",
            )
        now = datetime.now()
        return SchemaContract(
            name=name,
            dataset=dataset,
            columns=columns,
            contract_version=contract_version,
            extra_columns=extra_columns,
            created_at=now,
            updated_at=now,
            metadata={
                "rows_observed": len(data),
                "infer_ranges": bool(infer_ranges),
                "infer_categories": bool(infer_categories),
            },
        )

    def add_column_rule(
        self,
        contract: SchemaContract,
        *,
        column: str,
        dtype: str | None = None,
        required: bool | None = None,
        nullable: bool | None = None,
        unique: bool | None = None,
        minimum: Any = None,
        maximum: Any = None,
        allowed_values: list[Any] | None = None,
        pattern: str | None = None,
        severity: str | None = None,
    ) -> SchemaContract:
        column = str(column).strip()
        if not column:
            raise ValueError("Schema contract column cannot be empty.")
        existing = contract.columns.get(column, SchemaColumn(name=column))
        if dtype is not None:
            dtype = self.normalize_dtype(dtype)
            existing.dtype = dtype
        if required is not None:
            existing.required = bool(required)
        if nullable is not None:
            existing.nullable = bool(nullable)
        if unique is not None:
            existing.unique = bool(unique)
        if minimum is not None:
            existing.minimum = minimum
        if maximum is not None:
            existing.maximum = maximum
        if existing.minimum is not None and existing.maximum is not None:
            try:
                if existing.minimum > existing.maximum:
                    raise ValueError("Schema minimum cannot exceed maximum.")
            except TypeError as error:
                raise ValueError("Schema minimum and maximum must be comparable.") from error
        if allowed_values is not None:
            if not allowed_values or len(allowed_values) > 1_000:
                raise ValueError("ALLOWED requires between 1 and 1,000 values.")
            existing.allowed_values = list(allowed_values)
        if pattern is not None:
            try:
                re.compile(str(pattern))
            except re.error as error:
                raise ValueError(f"Invalid schema regular expression: {error}") from error
            existing.pattern = str(pattern)
        if severity is not None:
            normalized = str(severity).lower().strip()
            if normalized not in {"error", "warning", "info"}:
                raise ValueError("Schema severity must be error, warning, or info.")
            existing.severity = normalized
        contract.columns[column] = existing
        contract.updated_at = datetime.now()
        if len(contract.columns) > self.MAX_COLUMNS:
            raise ValueError(
                f"Schema contracts support at most {self.MAX_COLUMNS:,} columns."
            )
        return contract

    def validate(
        self,
        data: pd.DataFrame,
        contract: SchemaContract,
        *,
        dataset: str,
        fail_on: str = "error",
    ) -> SchemaValidationReport:
        self._require_frame(data)
        results: list[SchemaValidationResult] = []
        for name, rule in contract.columns.items():
            exists = name in data.columns
            if rule.required:
                results.append(
                    self._result(
                        rule="required",
                        passed=exists,
                        severity=rule.severity,
                        column=name,
                        observed=exists,
                        expected=True,
                        failed_count=0 if exists else 1,
                        total_count=1,
                        message=(
                            f"Required column {name} exists."
                            if exists
                            else f"Required column {name} is missing."
                        ),
                    )
                )
            if not exists:
                continue
            series = data[name]
            if rule.dtype is not None:
                observed = canonical_dtype(series)
                passed = self._matches_dtype(series, rule.dtype)
                results.append(
                    self._result(
                        rule="dtype",
                        passed=passed,
                        severity=rule.severity,
                        column=name,
                        observed=observed,
                        expected=rule.dtype,
                        failed_count=0 if passed else len(series),
                        total_count=len(series),
                        message=f"{name} has type {observed}; expected {rule.dtype}.",
                    )
                )
            if not rule.nullable:
                failed = int(series.isna().sum())
                results.append(
                    self._result(
                        rule="not_null",
                        passed=failed == 0,
                        severity=rule.severity,
                        column=name,
                        observed=failed,
                        expected=0,
                        failed_count=failed,
                        total_count=len(series),
                        message=f"{failed:,} missing value(s) found in {name}.",
                    )
                )
            non_null = series.dropna()
            if rule.unique:
                failed = int(non_null.duplicated(keep=False).sum())
                results.append(
                    self._result(
                        rule="unique",
                        passed=failed == 0,
                        severity=rule.severity,
                        column=name,
                        observed=failed,
                        expected=0,
                        failed_count=failed,
                        total_count=len(series),
                        message=f"{failed:,} row(s) use duplicate non-null {name} values.",
                    )
                )
            if rule.minimum is not None:
                values, expected = self._comparable_values(series, rule.minimum)
                invalid = values.notna() & (values < expected)
                failed = int(invalid.sum())
                observed = values.min() if not values.dropna().empty else None
                results.append(
                    self._result(
                        rule="minimum",
                        passed=failed == 0,
                        severity=rule.severity,
                        column=name,
                        observed=observed,
                        expected=rule.minimum,
                        failed_count=failed,
                        total_count=len(series),
                        message=f"{failed:,} {name} value(s) are below the minimum.",
                    )
                )
            if rule.maximum is not None:
                values, expected = self._comparable_values(series, rule.maximum)
                invalid = values.notna() & (values > expected)
                failed = int(invalid.sum())
                observed = values.max() if not values.dropna().empty else None
                results.append(
                    self._result(
                        rule="maximum",
                        passed=failed == 0,
                        severity=rule.severity,
                        column=name,
                        observed=observed,
                        expected=rule.maximum,
                        failed_count=failed,
                        total_count=len(series),
                        message=f"{failed:,} {name} value(s) exceed the maximum.",
                    )
                )
            if rule.allowed_values is not None:
                invalid = ~non_null.isin(rule.allowed_values)
                failed = int(invalid.sum())
                observed = sorted({str(value) for value in non_null[invalid].unique()})[:20]
                results.append(
                    self._result(
                        rule="allowed_values",
                        passed=failed == 0,
                        severity=rule.severity,
                        column=name,
                        observed=observed,
                        expected=rule.allowed_values,
                        failed_count=failed,
                        total_count=len(series),
                        message=f"{failed:,} non-null {name} value(s) are not allowed.",
                    )
                )
            if rule.pattern is not None:
                pattern = re.compile(rule.pattern)
                matched = non_null.astype(str).map(lambda value: bool(pattern.fullmatch(value)))
                failed = int((~matched).sum())
                observed = sorted({str(value) for value in non_null[~matched].unique()})[:20]
                results.append(
                    self._result(
                        rule="pattern",
                        passed=failed == 0,
                        severity=rule.severity,
                        column=name,
                        observed=observed,
                        expected=rule.pattern,
                        failed_count=failed,
                        total_count=len(series),
                        message=f"{failed:,} non-null {name} value(s) do not match the pattern.",
                    )
                )
        extras = [str(column) for column in data.columns if str(column) not in contract.columns]
        if contract.extra_columns != "ignore":
            for column in extras:
                results.append(
                    self._result(
                        rule="extra_column",
                        passed=False,
                        severity=contract.extra_columns,
                        column=column,
                        observed="present",
                        expected="not declared",
                        failed_count=1,
                        total_count=1,
                        message=f"Column {column} is not declared in {contract.name}.",
                    )
                )
        return SchemaValidationReport(
            contract_name=contract.name,
            contract_version=contract.contract_version,
            dataset=dataset,
            results=results,
            fail_on=fail_on,
        )

    @staticmethod
    def normalize_dtype(value: str) -> str:
        aliases = {
            "number": "numeric",
            "decimal": "float",
            "int": "integer",
            "text": "string",
            "date": "datetime",
            "timestamp": "datetime",
            "bool": "boolean",
            "categorical": "category",
        }
        normalized = aliases.get(str(value).lower().strip(), str(value).lower().strip())
        if normalized not in SUPPORTED_DTYPES:
            raise ValueError(
                "Schema TYPE must be numeric, integer, float, string, datetime, "
                "boolean, or category."
            )
        return normalized

    def export(self, contract: SchemaContract, path: str | Path, *, overwrite: bool = False) -> Path:
        return self._write_json(contract.to_dict(), path, overwrite=overwrite, label="schema contract")

    def load(self, path: str | Path, *, name: str | None = None) -> SchemaContract:
        payload = self._read_json(path, label="schema contract")
        contract = SchemaContract.from_dict(payload, name=name)
        if contract.column_count > self.MAX_COLUMNS:
            raise ValueError(
                f"Schema contracts support at most {self.MAX_COLUMNS:,} columns."
            )
        return contract

    @staticmethod
    def _matches_dtype(series: pd.Series, expected: str) -> bool:
        observed = canonical_dtype(series)
        if expected == "numeric":
            return observed in {"numeric", "integer", "float"}
        if expected == "string":
            return observed in {"string", "category"}
        return observed == expected

    @staticmethod
    def _comparable_values(series: pd.Series, expected: Any) -> tuple[pd.Series, Any]:
        if ptypes.is_datetime64_any_dtype(series.dtype):
            return pd.to_datetime(series, errors="coerce"), pd.to_datetime(expected)
        return pd.to_numeric(series, errors="coerce"), float(expected)

    @staticmethod
    def _result(**kwargs) -> SchemaValidationResult:
        return SchemaValidationResult(**kwargs)

    @staticmethod
    def _require_frame(data: pd.DataFrame) -> None:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Schema contracts require a pandas DataFrame.")

    @classmethod
    def _read_json(cls, path: str | Path, *, label: str) -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        if source.suffix.lower() != ".json":
            raise ValueError(f"{label.title()} path must end with .json.")
        if not source.is_file():
            raise FileNotFoundError(f"{label.title()} was not found: {source}")
        if source.stat().st_size > cls.MAX_FILE_SIZE:
            raise ValueError(f"{label.title()} JSON cannot exceed 2 MB.")
        try:
            return json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid {label} JSON: {error}") from error

    @staticmethod
    def _write_json(
        payload: dict[str, Any],
        path: str | Path,
        *,
        overwrite: bool,
        label: str,
    ) -> Path:
        output = Path(path).expanduser().resolve()
        if output.suffix.lower() != ".json":
            raise ValueError(f"{label.title()} path must end with .json.")
        if output.exists() and not overwrite:
            raise FileExistsError(
                f"{label.title()} already exists: {output}. Use overwrite=True."
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output


class DriftEngine:
    """Create compact statistical baselines and compare future datasets."""

    MAX_COLUMNS = 1_000
    MAX_FILE_SIZE = 5_000_000
    TOP_CATEGORIES = 50

    def create_baseline(
        self,
        data: pd.DataFrame,
        *,
        name: str,
        dataset: str,
    ) -> DriftBaseline:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Drift baselines require a pandas DataFrame.")
        name = validate_name(name, artifact="Drift baseline")
        if len(data.columns) > self.MAX_COLUMNS:
            raise ValueError(
                f"Drift baselines support at most {self.MAX_COLUMNS:,} columns."
            )
        columns = {
            str(column): self._profile_column(str(column), data[column], len(data))
            for column in data.columns
        }
        duplicate_percent = round(
            float(data.duplicated().sum() / max(len(data), 1) * 100), 4
        )
        return DriftBaseline(
            name=name,
            dataset=dataset,
            row_count=len(data),
            column_count=len(data.columns),
            duplicate_percent=duplicate_percent,
            columns=columns,
            metadata={
                "psi_thresholds": {"moderate": 0.1, "major": 0.25},
                "missing_delta_points": {"moderate": 2.0, "major": 5.0},
            },
        )

    def detect(
        self,
        data: pd.DataFrame,
        baseline: DriftBaseline,
        *,
        dataset: str,
        fail_on: str = "error",
        contract_report: SchemaValidationReport | None = None,
        psi_warning: float = 0.1,
        psi_error: float = 0.25,
        missing_warning: float = 2.0,
        missing_error: float = 5.0,
    ) -> DriftReport:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Drift detection requires a pandas DataFrame.")
        self._validate_thresholds(
            psi_warning, psi_error, missing_warning, missing_error
        )
        results: list[DriftResult] = []
        baseline_names = set(baseline.columns)
        current_names = {str(column) for column in data.columns}
        for column in sorted(baseline_names - current_names):
            results.append(
                self._result(
                    "missing_column", "major", column, "present", "missing", None,
                    f"Baseline column {column} is missing from the current dataset."
                )
            )
        for column in sorted(current_names - baseline_names):
            results.append(
                self._result(
                    "added_column", "moderate", column, "not present", "present", None,
                    f"Current column {column} was not present in the baseline."
                )
            )
        for column in sorted(baseline_names & current_names):
            reference = baseline.columns[column]
            series = data[column]
            observed_dtype = canonical_dtype(series)
            expected_dtype = self._canonical_baseline_dtype(reference.dtype)
            compatible = self._compatible_dtype(expected_dtype, observed_dtype)
            results.append(
                self._result(
                    "dtype",
                    "stable" if compatible else "major",
                    column,
                    expected_dtype,
                    observed_dtype,
                    None,
                    (
                        f"{column} retains compatible type {observed_dtype}."
                        if compatible
                        else f"{column} changed from {expected_dtype} to {observed_dtype}."
                    ),
                )
            )
            current_missing = round(float(series.isna().mean() * 100), 4)
            missing_delta = round(current_missing - reference.missing_percent, 4)
            status = self._absolute_status(
                abs(missing_delta), missing_warning, missing_error
            )
            results.append(
                self._result(
                    "missing_percent",
                    status,
                    column,
                    reference.missing_percent,
                    current_missing,
                    missing_delta,
                    f"{column} missingness changed by {missing_delta:+.2f} percentage points.",
                )
            )
            distinct = int(series.nunique(dropna=True))
            distinct_ratio = round(distinct / max(series.notna().sum(), 1) * 100, 4)
            distinct_delta = round(distinct_ratio - reference.distinct_ratio, 4)
            status = self._absolute_status(abs(distinct_delta), 5.0, 20.0)
            results.append(
                self._result(
                    "distinct_ratio",
                    status,
                    column,
                    reference.distinct_ratio,
                    distinct_ratio,
                    distinct_delta,
                    f"{column} distinct-value ratio changed by {distinct_delta:+.2f} percentage points.",
                )
            )
            current_distribution = self._current_distribution(reference, series)
            psi = round(self._psi(reference.distribution, current_distribution), 4)
            status = self._absolute_status(psi, psi_warning, psi_error)
            results.append(
                self._result(
                    "population_stability_index",
                    status,
                    column,
                    {
                        "stable_at_or_below": psi_warning,
                        "major_above": psi_error,
                    },
                    psi,
                    psi,
                    (
                        f"{column} PSI is {psi:.4f}; stable is at or below "
                        f"{psi_warning:.4f} and major is above {psi_error:.4f}."
                    ),
                )
            )
            if (
                reference.kind in {"numeric", "datetime"}
                and reference.minimum is not None
                and reference.maximum is not None
            ):
                outside = self._outside_range_percent(series, reference)
                status = self._absolute_status(outside, 0.0, 1.0)
                results.append(
                    self._result(
                        "outside_baseline_range_percent",
                        status,
                        column,
                        [reference.minimum, reference.maximum],
                        outside,
                        outside,
                        f"{outside:.2f}% of non-null {column} values fall outside the baseline range.",
                    )
                )
            if reference.categories_complete:
                non_null = series.dropna().astype(str)
                unseen = ~non_null.isin(reference.categories)
                unseen_percent = round(float(unseen.mean() * 100) if len(non_null) else 0.0, 4)
                status = self._absolute_status(unseen_percent, 0.0, 5.0)
                results.append(
                    self._result(
                        "unseen_category_percent",
                        status,
                        column,
                        0.0,
                        unseen_percent,
                        unseen_percent,
                        f"{unseen_percent:.2f}% of non-null {column} values are new categories.",
                    )
                )
        current_duplicate = round(
            float(data.duplicated().sum() / max(len(data), 1) * 100), 4
        )
        duplicate_delta = round(current_duplicate - baseline.duplicate_percent, 4)
        results.append(
            self._result(
                "duplicate_percent",
                self._absolute_status(abs(duplicate_delta), 1.0, 5.0),
                None,
                baseline.duplicate_percent,
                current_duplicate,
                duplicate_delta,
                f"Exact-duplicate rate changed by {duplicate_delta:+.2f} percentage points.",
            )
        )
        row_delta = round((len(data) - baseline.row_count) / max(baseline.row_count, 1) * 100, 4)
        results.append(
            self._result(
                "row_count",
                self._absolute_status(abs(row_delta), 25.0, 50.0),
                None,
                baseline.row_count,
                len(data),
                row_delta,
                f"Row count changed by {row_delta:+.2f}% relative to the baseline batch.",
            )
        )
        if contract_report is not None:
            for item in contract_report.results:
                if item.passed:
                    continue
                status = "major" if item.severity == "error" else "moderate"
                results.append(
                    DriftResult(
                        metric=f"contract_{item.rule}",
                        status=status,
                        severity=item.severity,
                        column=item.column,
                        reference=item.expected,
                        current=item.observed,
                        difference=item.failed_count,
                        message=item.message,
                    )
                )
        return DriftReport(
            baseline_name=baseline.name,
            baseline_dataset=baseline.dataset,
            dataset=dataset,
            contract_name=(contract_report.contract_name if contract_report else None),
            results=results,
            fail_on=fail_on,
        )

    def export(self, baseline: DriftBaseline, path: str | Path, *, overwrite: bool = False) -> Path:
        return SchemaContractEngine._write_json(
            baseline.to_dict(), path, overwrite=overwrite, label="drift baseline"
        )

    def load(self, path: str | Path, *, name: str | None = None) -> DriftBaseline:
        payload = self._read_json(path)
        baseline = DriftBaseline.from_dict(payload, name=name)
        if baseline.profiled_column_count > self.MAX_COLUMNS:
            raise ValueError(
                f"Drift baselines support at most {self.MAX_COLUMNS:,} columns."
            )
        return baseline

    def _profile_column(
        self,
        name: str,
        series: pd.Series,
        row_count: int,
    ) -> DriftColumnBaseline:
        dtype = str(series.dtype)
        canonical = canonical_dtype(series)
        kind = "datetime" if canonical == "datetime" else (
            "numeric" if canonical in {"integer", "float", "numeric"} else "categorical"
        )
        non_null = series.dropna()
        missing = round(float(series.isna().mean() * 100), 4)
        distinct = int(non_null.nunique(dropna=True))
        distinct_ratio = round(distinct / max(len(non_null), 1) * 100, 4)
        minimum = None
        maximum = None
        bin_edges: list[float] = []
        categories: list[str] = []
        categories_complete = False
        if kind in {"numeric", "datetime"}:
            numeric = self._numeric_values(series, kind)
            valid = numeric.dropna()
            if not valid.empty:
                minimum = non_null.min()
                maximum = non_null.max()
                if valid.nunique() >= 2:
                    quantiles = np.unique(valid.quantile(np.linspace(0, 1, 11)).to_numpy())
                    bin_edges = [float(item) for item in quantiles[1:-1]]
            distribution = self._numeric_distribution(numeric, bin_edges)
        else:
            values = non_null.astype(str)
            counts = values.value_counts()
            categories_complete = distinct <= self.TOP_CATEGORIES
            categories = [str(item) for item in counts.head(self.TOP_CATEGORIES).index]
            distribution = self._categorical_distribution(series, categories)
            if not non_null.empty:
                try:
                    minimum = non_null.min()
                    maximum = non_null.max()
                except TypeError:
                    minimum = None
                    maximum = None
        return DriftColumnBaseline(
            name=name,
            dtype=dtype,
            kind=kind,
            missing_percent=missing,
            distinct_count=distinct,
            distinct_ratio=distinct_ratio,
            minimum=minimum,
            maximum=maximum,
            bin_edges=bin_edges,
            distribution=distribution,
            categories=categories,
            categories_complete=categories_complete,
        )

    def _current_distribution(
        self,
        reference: DriftColumnBaseline,
        series: pd.Series,
    ) -> dict[str, float]:
        if reference.kind in {"numeric", "datetime"}:
            return self._numeric_distribution(
                self._numeric_values(series, reference.kind),
                reference.bin_edges,
            )
        return self._categorical_distribution(series, reference.categories)

    @staticmethod
    def _numeric_values(series: pd.Series, kind: str) -> pd.Series:
        if kind == "datetime":
            converted = pd.to_datetime(series, errors="coerce")
            result = pd.Series(np.nan, index=series.index, dtype=float)
            mask = converted.notna()
            result.loc[mask] = converted.loc[mask].astype("int64") / 1_000_000_000
            return result
        return pd.to_numeric(series, errors="coerce")

    @staticmethod
    def _numeric_distribution(
        values: pd.Series,
        internal_edges: list[float],
    ) -> dict[str, float]:
        labels = None
        if internal_edges:
            bins = np.asarray([-np.inf, *internal_edges, np.inf], dtype=float)
            bucketed = pd.cut(values, bins=bins, include_lowest=True, duplicates="drop")
            labels = bucketed.astype("string")
        else:
            labels = pd.Series("__VALUE__", index=values.index, dtype="string")
            labels.loc[values.isna()] = pd.NA
        labels = labels.fillna("__MISSING__")
        return {
            str(key): round(float(value), 10)
            for key, value in labels.value_counts(normalize=True).items()
        }

    @staticmethod
    def _categorical_distribution(
        series: pd.Series,
        categories: list[str],
    ) -> dict[str, float]:
        values = series.astype("string")
        missing = values.isna()
        values = values.where(values.isin(categories), "__OTHER__")
        values = values.where(~missing, "__MISSING__")
        return {
            str(key): round(float(value), 10)
            for key, value in values.value_counts(normalize=True).items()
        }

    @staticmethod
    def _psi(reference: dict[str, float], current: dict[str, float]) -> float:
        epsilon = 1e-6
        keys = set(reference) | set(current)
        value = sum(
            ((current.get(key, 0.0) + epsilon) - (reference.get(key, 0.0) + epsilon))
            * np.log(
                (current.get(key, 0.0) + epsilon)
                / (reference.get(key, 0.0) + epsilon)
            )
            for key in keys
        )
        return float(max(0.0, value))

    def _outside_range_percent(
        self,
        series: pd.Series,
        reference: DriftColumnBaseline,
    ) -> float:
        if reference.kind == "datetime":
            values = pd.to_datetime(series, errors="coerce")
            minimum = pd.to_datetime(reference.minimum)
            maximum = pd.to_datetime(reference.maximum)
        else:
            values = pd.to_numeric(series, errors="coerce")
            minimum = float(reference.minimum)
            maximum = float(reference.maximum)
        valid = values.dropna()
        if valid.empty:
            return 0.0
        return round(float(((valid < minimum) | (valid > maximum)).mean() * 100), 4)

    @staticmethod
    def _absolute_status(value: float, warning: float, error: float) -> str:
        if value <= warning:
            return "stable"
        if value <= error:
            return "moderate"
        return "major"

    @staticmethod
    def _result(
        metric: str,
        status: str,
        column: str | None,
        reference: Any,
        current: Any,
        difference: Any,
        message: str,
    ) -> DriftResult:
        severity = "info" if status == "stable" else (
            "warning" if status == "moderate" else "error"
        )
        return DriftResult(
            metric=metric,
            status=status,
            severity=severity,
            column=column,
            reference=reference,
            current=current,
            difference=difference,
            message=message,
        )

    @staticmethod
    def _canonical_baseline_dtype(dtype: str) -> str:
        lowered = str(dtype).lower()
        if "datetime" in lowered:
            return "datetime"
        if "category" in lowered:
            return "category"
        if "bool" in lowered:
            return "boolean"
        if "int" in lowered:
            return "integer"
        if "float" in lowered:
            return "float"
        if any(item in lowered for item in ("number", "decimal")):
            return "numeric"
        return "string"

    @staticmethod
    def _compatible_dtype(expected: str, observed: str) -> bool:
        if expected in {"numeric", "integer", "float"} and observed in {
            "numeric", "integer", "float"
        }:
            return True
        if expected in {"string", "category"} and observed in {"string", "category"}:
            return True
        return expected == observed

    @staticmethod
    def _validate_thresholds(
        psi_warning: float,
        psi_error: float,
        missing_warning: float,
        missing_error: float,
    ) -> None:
        if not 0 <= psi_warning <= psi_error:
            raise ValueError("PSI thresholds must satisfy 0 <= warning <= error.")
        if not 0 <= missing_warning <= missing_error <= 100:
            raise ValueError(
                "Missingness thresholds must satisfy 0 <= warning <= error <= 100."
            )

    @classmethod
    def _read_json(cls, path: str | Path) -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        if source.suffix.lower() != ".json":
            raise ValueError("Drift baseline path must end with .json.")
        if not source.is_file():
            raise FileNotFoundError(f"Drift baseline was not found: {source}")
        if source.stat().st_size > cls.MAX_FILE_SIZE:
            raise ValueError("Drift baseline JSON cannot exceed 5 MB.")
        try:
            return json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid drift baseline JSON: {error}") from error
