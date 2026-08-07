from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


SEVERITY_LEVELS = {"never": 4, "error": 3, "warning": 2, "info": 1}


def _serializable(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass

    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_serializable(item) for item in value]
    if isinstance(value, list):
        return [_serializable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serializable(item) for key, item in value.items()}
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


@dataclass(slots=True)
class QualityAssertion:
    subject: str
    predicate: str
    column: str | None = None
    operator: str | None = None
    expected: Any = None
    expected_max: Any = None
    values: list[Any] | None = None
    severity: str = "error"
    name: str | None = None

    def __post_init__(self) -> None:
        self.subject = str(self.subject).lower().strip()
        self.predicate = str(self.predicate).lower().strip()
        self.severity = str(self.severity).lower().strip()
        if self.severity not in {"error", "warning", "info"}:
            raise ValueError("Assertion severity must be error, warning, or info.")
        if self.column is not None:
            self.column = str(self.column).strip()
        if self.name is not None:
            self.name = str(self.name).strip()
        if self.values is not None:
            self.values = list(self.values)

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        target = (
            self.column
            if self.subject == "column"
            else self.subject.upper()
            + (f" {self.column}" if self.column else "")
        )
        labels = {
            "not_null": "is not null",
            "unique": "is unique",
            "exists": "exists",
            "type": f"has type {self.expected}",
            "min": f"is at least {self.expected}",
            "max": f"is at most {self.expected}",
            "between": f"is between {self.expected} and {self.expected_max}",
            "allowed": "uses allowed values",
            "matches": f"matches {self.expected}",
            "compare": f"{self.operator} {self.expected}",
        }
        return f"{target} {labels.get(self.predicate, self.predicate)}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "predicate": self.predicate,
            "column": self.column,
            "operator": self.operator,
            "expected": _serializable(self.expected),
            "expected_max": _serializable(self.expected_max),
            "values": _serializable(self.values),
            "severity": self.severity,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "QualityAssertion":
        if not isinstance(payload, dict):
            raise ValueError("Quality assertion must be a dictionary.")
        try:
            return cls(
                subject=payload["subject"],
                predicate=payload["predicate"],
                column=payload.get("column"),
                operator=payload.get("operator"),
                expected=payload.get("expected"),
                expected_max=payload.get("expected_max"),
                values=payload.get("values"),
                severity=payload.get("severity", "error"),
                name=payload.get("name"),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Invalid quality assertion data.") from error


@dataclass(slots=True)
class QualityTestResult:
    assertion: QualityAssertion
    passed: bool
    observed: Any
    expected: Any
    message: str
    failed_count: int = 0
    total_count: int = 0

    @property
    def status(self) -> str:
        return "passed" if self.passed else "failed"

    @property
    def severity(self) -> str:
        return self.assertion.severity

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.assertion.display_name,
            "status": self.status,
            "passed": self.passed,
            "severity": self.severity,
            "subject": self.assertion.subject,
            "column": self.assertion.column,
            "predicate": self.assertion.predicate,
            "observed": _serializable(self.observed),
            "expected": _serializable(self.expected),
            "failed_count": self.failed_count,
            "total_count": self.total_count,
            "message": self.message,
            "assertion": self.assertion.to_dict(),
        }


@dataclass(slots=True)
class QualityTestSuite:
    name: str
    assertions: list[QualityAssertion] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValueError("Quality suite name cannot be empty.")

    @property
    def test_count(self) -> int:
        return len(self.assertions)

    def add(self, assertion: QualityAssertion) -> None:
        if assertion.name and any(
            item.name and item.name.casefold() == assertion.name.casefold()
            for item in self.assertions
        ):
            raise ValueError(
                f"Quality suite {self.name} already contains a test named "
                f"{assertion.name}."
            )
        self.assertions.append(assertion)
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": 1,
            "name": self.name,
            "test_count": self.test_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "assertions": [item.to_dict() for item in self.assertions],
        }

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
        *,
        name: str | None = None,
    ) -> "QualityTestSuite":
        if not isinstance(payload, dict) or payload.get("format_version") != 1:
            raise ValueError("Unsupported quality suite format.")
        assertions = payload.get("assertions")
        if not isinstance(assertions, list):
            raise ValueError("Quality suite assertions must be a list.")
        try:
            created_at = datetime.fromisoformat(
                str(payload.get("created_at", datetime.now().isoformat()))
            )
            updated_at = datetime.fromisoformat(
                str(payload.get("updated_at", datetime.now().isoformat()))
            )
        except ValueError as error:
            raise ValueError("Invalid quality suite timestamp.") from error
        return cls(
            name=name or payload.get("name", ""),
            assertions=[QualityAssertion.from_dict(item) for item in assertions],
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass(slots=True)
class QualityTestReport:
    dataset: str
    results: list[QualityTestResult]
    suite_name: str | None = None
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
            not item.passed
            and SEVERITY_LEVELS[item.severity] >= threshold
            for item in self.results
        )

    @property
    def success(self) -> bool:
        return self.blocking_failure_count == 0

    def to_frame(self) -> pd.DataFrame:
        columns = [
            "test",
            "status",
            "severity",
            "subject",
            "column",
            "predicate",
            "observed",
            "expected",
            "failed_count",
            "total_count",
            "message",
        ]
        return pd.DataFrame(
            [
                {
                    "test": item.assertion.display_name,
                    "status": item.status,
                    "severity": item.severity,
                    "subject": item.assertion.subject,
                    "column": item.assertion.column,
                    "predicate": item.assertion.predicate,
                    "observed": _serializable(item.observed),
                    "expected": _serializable(item.expected),
                    "failed_count": item.failed_count,
                    "total_count": item.total_count,
                    "message": item.message,
                }
                for item in self.results
            ],
            columns=columns,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "suite_name": self.suite_name,
            "success": self.success,
            "fail_on": self.fail_on,
            "test_count": self.test_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "blocking_failure_count": self.blocking_failure_count,
            "generated_at": self.generated_at.isoformat(),
            "results": [item.to_dict() for item in self.results],
        }
