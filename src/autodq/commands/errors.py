from __future__ import annotations


class ADQLError(Exception):
    """Base class for all ADQL errors."""


class ADQLSyntaxError(ADQLError, ValueError):
    """Raised when an ADQL statement cannot be parsed."""


class ADQLValidationError(ADQLError, ValueError):
    """Raised when parsed ADQL violates language safety rules."""


class ADQLAssertionError(ADQLError, AssertionError):
    """Raised when an ASSERT result reaches its configured failure level."""

    def __init__(self, message, *, report=None, data=None):
        super().__init__(message)
        self.report = report
        self.data = data


class ADQLContractError(ADQLAssertionError):
    """Raised when schema contract validation reaches its failure level."""


class ADQLDriftError(ADQLAssertionError):
    """Raised when drift detection reaches its configured failure level."""


class ADQLExecutionError(ADQLError, RuntimeError):
    """Raised when a valid ADQL statement fails during execution."""

    def __init__(self, message, *, statement=None, result=None, cause=None):
        super().__init__(message)
        self.statement = statement
        self.result = result
        self.cause = cause
