from __future__ import annotations


class ADQLError(Exception):
    """Base class for all ADQL errors."""


class ADQLSyntaxError(ADQLError, ValueError):
    """Raised when an ADQL statement cannot be parsed."""


class ADQLValidationError(ADQLError, ValueError):
    """Raised when parsed ADQL violates language safety rules."""


class ADQLExecutionError(ADQLError, RuntimeError):
    """Raised when a valid ADQL statement fails during execution."""

    def __init__(self, message, *, statement=None, result=None, cause=None):
        super().__init__(message)
        self.statement = statement
        self.result = result
        self.cause = cause
