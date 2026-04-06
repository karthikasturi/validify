"""
core/exceptions.py — Exception hierarchy for Validify.

This file is provided in full. You do not need to modify it.
Study it before Day 1 — it shows how to design a clean exception hierarchy.
"""


class ValidifyError(Exception):
    """Base exception for all Validify errors.

    Catching this single type is sufficient to handle any error that originates
    from within this library.
    """


class ConfigError(ValidifyError):
    """Raised when a rule configuration is invalid or a required key is missing."""


class DataLoadError(ValidifyError):
    """Raised when a dataset file cannot be opened or parsed."""

    def __init__(self, path: str, reason: str) -> None:
        super().__init__(f"Cannot load dataset '{path}': {reason}")
        self.path = path
        self.reason = reason


class ValidationError(ValidifyError):
    """Raised when the validation engine encounters an unrecoverable error.

    Note: this is NOT raised for individual rule failures. Rule failures are
    captured as ValidationResult(passed=False) objects and collected in a Report.
    This exception is only raised when the engine itself cannot continue —
    for example, if a rule raises an unexpected exception mid-run.
    """
