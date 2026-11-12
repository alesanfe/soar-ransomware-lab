"""CONTRACT-001: canonical alert severity model shared API <-> workflow.

One normalization table, one source of truth. The API validates and
normalizes at the edge; ``normalize_inputs.py`` (embedded in the Shuffle
workflow) mirrors the SAME table so an admitted alert can never be
rejected downstream solely on a severity discrepancy.

Canonical range: 0..4 (informational, low, medium, high, critical).
Downstream TheHive severity (1..3) is a separate mapping applied at the
case-building step — never at admission.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "SeverityContractError",
    "SEVERITY_MIN",
    "SEVERITY_MAX",
    "SEVERITY_NAMES",
    "DEFAULT_SEVERITY",
    "normalize_severity",
    "severity_to_thehive",
]

SEVERITY_MIN = 0  # informational
SEVERITY_MAX = 4  # critical

# Textual aliases -> canonical int. Keys are already lower()+stripped.
SEVERITY_NAMES: dict[str, int] = {
    "informational": 0,
    "info": 0,
    "low": 1,
    "medium": 2,
    "med": 2,
    "warning": 2,
    "warn": 2,
    "high": 3,
    "critical": 4,
    "crit": 4,
}

# Documented default when the field is absent/null (CONTRACT-001: the
# API never drops an alert only for a missing severity).
DEFAULT_SEVERITY = 2  # medium


class SeverityContractError(ValueError):
    """Raised when a severity value violates the shared contract."""


def normalize_severity(value: Any) -> int:
    """Normalize ``value`` to the canonical 0..4 int.

    Accepts ints in range, numeric strings ("3", "2.0") and the textual
    names in ``SEVERITY_NAMES`` (case/space tolerant). Rejects bools,
    None-without-default is handled by callers, and unknown text.

    Raises:
        SeverityContractError: on any non-conforming value.
    """
    if value is None:
        raise SeverityContractError("severity is required")
    if isinstance(value, bool):
        # bool is an int subtype in Python — `severity: true` must not
        # smuggle in as LOW.
        raise SeverityContractError("severity must not be a bool")
    if isinstance(value, int):
        if SEVERITY_MIN <= value <= SEVERITY_MAX:
            return value
        raise SeverityContractError(
            f"severity int must be in {SEVERITY_MIN}..{SEVERITY_MAX}"
        )
    if isinstance(value, float):
        if value.is_integer() and SEVERITY_MIN <= value <= SEVERITY_MAX:
            return int(value)
        raise SeverityContractError(
            f"severity float must be integral and in {SEVERITY_MIN}..{SEVERITY_MAX}"
        )
    if isinstance(value, str):
        text = value.strip().lower()
        if not text:
            raise SeverityContractError("severity must not be empty")
        if text in SEVERITY_NAMES:
            return SEVERITY_NAMES[text]
        # numeric strings like "3" or "2.0"
        import re

        if re.fullmatch(r"\d+(?:\.0+)?", text):
            return normalize_severity(float(text))
        raise SeverityContractError(f"unknown severity name: {value!r}")
    raise SeverityContractError(f"severity type not allowed: {type(value).__name__}")


def severity_to_thehive(severity: int) -> int:
    """Map canonical 0..4 severity onto TheHive's 1..3 scale."""
    return min(3, max(1, severity))
