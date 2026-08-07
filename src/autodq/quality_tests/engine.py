from __future__ import annotations

import operator
import re
from typing import Any

import pandas as pd
from pandas.api import types as ptypes

from autodq.quality_tests.models import (
    QualityAssertion,
    QualityTestReport,
    QualityTestResult,
    QualityTestSuite,
)


class QualityTestEngine:
    """Evaluate non-mutating data-quality assertions against a dataframe."""

    METRICS = {
        "row_count",
        "column_count",
        "missing_count",
        "missing_percent",
        "duplicate_rows",
        "duplicate_percent",
        "distinct_count",
        "quality_score",
    }
    COLUMN_PREDICATES = {
        "exists",
        "not_null",
        "unique",
        "type",
        "min",
        "max",
        "between",
        "allowed",
        "matches",
    }
    COMPARISONS = {
        "=": operator.eq,
        "==": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
    }

    def evaluate(
        self,
        data: pd.DataFrame,
        assertion: QualityAssertion,
        *,
        context: dict[str, Any] | None = None,
    ) -> QualityTestResult:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Quality assertions require a pandas DataFrame.")
        self.validate_assertion(assertion)
        if assertion.subject == "column":
            return self._evaluate_column(data, assertion)
        return self._evaluate_metric(data, assertion, context=context or {})

    def run(
        self,
        data: pd.DataFrame,
        assertions: list[QualityAssertion],
        *,
        dataset: str,
        suite_name: str | None = None,
        fail_on: str = "error",
        context: dict[str, Any] | None = None,
    ) -> QualityTestReport:
        return QualityTestReport(
            dataset=dataset,
            suite_name=suite_name,
            fail_on=fail_on,
            results=[
                self.evaluate(data, assertion, context=context)
                for assertion in assertions
            ],
        )

    def validate_assertion(self, assertion: QualityAssertion) -> None:
        if assertion.subject == "column":
            if assertion.predicate not in self.COLUMN_PREDICATES:
                raise ValueError(
                    f"Unsupported column assertion: {assertion.predicate}."
                )
            if not assertion.column:
                raise ValueError("Column assertion requires a column name.")
        elif assertion.subject in self.METRICS:
            if assertion.predicate not in {"compare", "between"}:
                raise ValueError("Metric assertion requires a comparison.")
            if assertion.subject in {
                "missing_count",
                "missing_percent",
                "distinct_count",
            } and assertion.column is not None and not assertion.column:
                raise ValueError("Metric column name cannot be empty.")
        else:
            raise ValueError(f"Unsupported assertion subject: {assertion.subject}.")

        if assertion.predicate == "compare":
            if assertion.operator not in self.COMPARISONS:
                raise ValueError(
                    f"Unsupported assertion operator: {assertion.operator}."
                )
            if not isinstance(assertion.expected, (int, float)):
                raise ValueError("Metric comparison value must be numeric.")
        elif assertion.predicate == "between":
            if not isinstance(assertion.expected, (int, float)) or not isinstance(
                assertion.expected_max, (int, float)
            ):
                raise ValueError("BETWEEN bounds must be numeric.")
            if assertion.expected > assertion.expected_max:
                raise ValueError("BETWEEN lower bound cannot exceed upper bound.")
        elif assertion.predicate in {"min", "max"} and not isinstance(
            assertion.expected, (int, float)
        ):
            raise ValueError("MIN and MAX assertion values must be numeric.")
        elif assertion.predicate == "type":
            supported = {
                "numeric",
                "number",
                "integer",
                "int",
                "float",
                "string",
                "text",
                "datetime",
                "date",
                "boolean",
                "bool",
                "category",
                "categorical",
            }
            if str(assertion.expected).lower() not in supported:
                raise ValueError(
                    "TYPE must be numeric, integer, float, string, datetime, "
                    "boolean, or category."
                )
        elif assertion.predicate == "allowed" and not assertion.values:
            raise ValueError("ALLOWED requires at least one value.")
        elif assertion.predicate == "matches":
            if not isinstance(assertion.expected, str) or not assertion.expected:
                raise ValueError("MATCHES requires a non-empty regular expression.")
            try:
                re.compile(assertion.expected)
            except re.error as error:
                raise ValueError(f"Invalid MATCHES regular expression: {error}") from error

    def _evaluate_column(
        self,
        data: pd.DataFrame,
        assertion: QualityAssertion,
    ) -> QualityTestResult:
        column = assertion.column
        exists = column in data.columns
        if assertion.predicate == "exists":
            return self._result(
                assertion,
                passed=exists,
                observed=exists,
                expected=True,
                failed_count=0 if exists else 1,
                total_count=1,
                message=(
                    f"Column {column} exists."
                    if exists
                    else f"Column {column} does not exist."
                ),
            )
        if not exists:
            return self._result(
                assertion,
                passed=False,
                observed="missing_column",
                expected=self._expected(assertion),
                failed_count=len(data),
                total_count=len(data),
                message=f"Column {column} does not exist.",
            )

        series = data[column]
        non_null = series.dropna()
        predicate = assertion.predicate

        if predicate == "not_null":
            failed = int(series.isna().sum())
            observed = failed
            expected = 0
            message = f"{failed:,} missing value(s) found in {column}."
        elif predicate == "unique":
            failed = int(non_null.duplicated(keep=False).sum())
            observed = failed
            expected = 0
            message = f"{failed:,} row(s) use duplicated non-null {column} values."
        elif predicate == "type":
            observed = str(series.dtype)
            expected = str(assertion.expected).lower()
            passed = self._matches_type(series, expected)
            failed = 0 if passed else len(series)
            return self._result(
                assertion,
                passed=passed,
                observed=observed,
                expected=expected,
                failed_count=failed,
                total_count=len(series),
                message=(
                    f"{column} has dtype {observed}; expected {expected}."
                ),
            )
        elif predicate in {"min", "max", "between"}:
            numeric = pd.to_numeric(non_null, errors="coerce")
            invalid = int(numeric.isna().sum())
            if predicate == "min":
                mask = numeric < assertion.expected
                observed = numeric.min() if not numeric.dropna().empty else None
                expected = f">= {assertion.expected}"
            elif predicate == "max":
                mask = numeric > assertion.expected
                observed = numeric.max() if not numeric.dropna().empty else None
                expected = f"<= {assertion.expected}"
            else:
                mask = numeric.notna() & ~numeric.between(
                    assertion.expected,
                    assertion.expected_max,
                    inclusive="both",
                )
                observed = {
                    "min": numeric.min() if not numeric.dropna().empty else None,
                    "max": numeric.max() if not numeric.dropna().empty else None,
                }
                expected = [assertion.expected, assertion.expected_max]
            failed = int(mask.fillna(False).sum()) + invalid
            message = f"{failed:,} non-null {column} value(s) violate {expected}."
        elif predicate == "allowed":
            invalid_mask = ~non_null.isin(assertion.values)
            failed = int(invalid_mask.sum())
            observed = sorted(
                {str(value) for value in non_null[invalid_mask].unique()}
            )[:20]
            expected = assertion.values
            message = f"{failed:,} non-null {column} value(s) are not allowed."
        else:
            pattern = re.compile(str(assertion.expected))
            matches = non_null.astype(str).map(lambda value: bool(pattern.fullmatch(value)))
            failed = int((~matches).sum())
            observed = sorted(
                {str(value) for value in non_null[~matches].unique()}
            )[:20]
            expected = assertion.expected
            message = f"{failed:,} non-null {column} value(s) do not match the pattern."

        return self._result(
            assertion,
            passed=failed == 0,
            observed=observed,
            expected=expected,
            failed_count=failed,
            total_count=len(series),
            message=message,
        )

    def _evaluate_metric(
        self,
        data: pd.DataFrame,
        assertion: QualityAssertion,
        *,
        context: dict[str, Any],
    ) -> QualityTestResult:
        subject = assertion.subject
        column = assertion.column
        if column is not None and column not in data.columns:
            return self._result(
                assertion,
                passed=False,
                observed="missing_column",
                expected=self._expected(assertion),
                failed_count=1,
                total_count=1,
                message=f"Column {column} does not exist.",
            )

        if subject == "row_count":
            observed = len(data)
        elif subject == "column_count":
            observed = len(data.columns)
        elif subject == "missing_count":
            observed = int(
                data[column].isna().sum()
                if column is not None
                else data.isna().sum().sum()
            )
        elif subject == "missing_percent":
            if column is not None:
                denominator = len(data)
                missing = int(data[column].isna().sum())
            else:
                denominator = data.size
                missing = int(data.isna().sum().sum())
            observed = round(100 * missing / denominator, 4) if denominator else 0.0
        elif subject == "duplicate_rows":
            observed = int(data.duplicated().sum())
        elif subject == "duplicate_percent":
            duplicates = int(data.duplicated().sum())
            observed = round(100 * duplicates / len(data), 4) if len(data) else 0.0
        elif subject == "distinct_count":
            observed = int(data[column].nunique(dropna=True))
        else:
            observed = context.get("quality_score")
            if observed is None:
                return self._result(
                    assertion,
                    passed=False,
                    observed=None,
                    expected=self._expected(assertion),
                    failed_count=1,
                    total_count=1,
                    message="Quality score is unavailable.",
                )

        if assertion.predicate == "between":
            passed = assertion.expected <= observed <= assertion.expected_max
            expected = [assertion.expected, assertion.expected_max]
        else:
            passed = self.COMPARISONS[assertion.operator](
                observed,
                assertion.expected,
            )
            expected = f"{assertion.operator} {assertion.expected}"
        target = subject.upper() + (f" {column}" if column else "")
        return self._result(
            assertion,
            passed=bool(passed),
            observed=observed,
            expected=expected,
            failed_count=0 if passed else 1,
            total_count=1,
            message=f"{target} observed {observed}; expected {expected}.",
        )

    @staticmethod
    def _matches_type(series: pd.Series, expected: str) -> bool:
        if expected in {"numeric", "number"}:
            return ptypes.is_numeric_dtype(series.dtype) and not ptypes.is_bool_dtype(
                series.dtype
            )
        if expected in {"integer", "int"}:
            return ptypes.is_integer_dtype(series.dtype)
        if expected == "float":
            return ptypes.is_float_dtype(series.dtype)
        if expected in {"string", "text"}:
            return ptypes.is_string_dtype(series.dtype) or series.dtype == object
        if expected in {"datetime", "date"}:
            return ptypes.is_datetime64_any_dtype(series.dtype)
        if expected in {"boolean", "bool"}:
            return ptypes.is_bool_dtype(series.dtype)
        return isinstance(series.dtype, pd.CategoricalDtype)

    @staticmethod
    def _expected(assertion: QualityAssertion) -> Any:
        if assertion.predicate == "between":
            return [assertion.expected, assertion.expected_max]
        if assertion.predicate == "allowed":
            return assertion.values
        if assertion.predicate in {"exists", "not_null", "unique"}:
            return True
        if assertion.predicate == "compare":
            return f"{assertion.operator} {assertion.expected}"
        return assertion.expected

    @staticmethod
    def _result(
        assertion: QualityAssertion,
        *,
        passed: bool,
        observed: Any,
        expected: Any,
        failed_count: int,
        total_count: int,
        message: str,
    ) -> QualityTestResult:
        return QualityTestResult(
            assertion=assertion,
            passed=bool(passed),
            observed=observed,
            expected=expected,
            failed_count=int(failed_count),
            total_count=int(total_count),
            message=message,
        )
