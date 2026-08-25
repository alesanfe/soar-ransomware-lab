"""Shared constants and dependency factories for API route modules."""

from typing import Any

from fastapi import FastAPI, HTTPException

from soar_lab.common.constants import (
    DEFAULT_ANALYTICS_SEARCH_SIZE,
    DEFAULT_API_VERSION,
    DEFAULT_KPI_SEARCH_SIZE,
    MOCK_METRICS_CPU,
    MOCK_METRICS_DISK,
    MOCK_METRICS_MEMORY,
)

__all__ = [
    "DEFAULT_KPI_SEARCH_SIZE",
    "DEFAULT_ANALYTICS_SEARCH_SIZE",
    "MOCK_METRICS_CPU",
    "MOCK_METRICS_MEMORY",
    "MOCK_METRICS_DISK",
    "DEFAULT_API_VERSION",
    "make_state_getter",
    "make_simple_getter",
]


def make_state_getter(app_instance: FastAPI, attr: str, label: str) -> Any:
    """Create a FastAPI dependency that returns a state value with a 503.

    guard.
    """

    def _get() -> Any:
        """Return the requested state value or raise 503 if unavailable."""
        val = getattr(app_instance.state, attr)
        if val is None:
            raise HTTPException(status_code=503, detail=f"{label} not available") from None
        return val

    return _get


def make_simple_getter(app_instance: FastAPI, attr: str) -> Any:
    """Create a FastAPI dependency that returns a state value without None.

    check.
    """

    def _get() -> Any:
        """Return the requested state value without a None check."""
        return getattr(app_instance.state, attr)

    return _get
