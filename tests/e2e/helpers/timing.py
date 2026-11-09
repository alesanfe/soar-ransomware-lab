"""Shared timing helpers for E2E tests."""

import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

__all__ = [
    "measure_time",
    "time_execution",
    "measure_multiple_executions",
    "calculate_percentiles",
]


@contextmanager
def measure_time():
    """Context manager to measure execution time.

    Usage::

        with measure_time() as t:
            do_work()
        print(t["elapsed"])
    """
    result: dict[str, float] = {}
    start = time.monotonic()
    yield result
    result["elapsed"] = time.monotonic() - start


def time_execution(func: Callable[..., Any], *args, **kwargs) -> tuple[Any, float]:
    """Execute a function and return its result along with execution time.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Tuple of (result, elapsed_time_seconds)
    """
    start = time.monotonic()
    result = func(*args, **kwargs)
    elapsed = time.monotonic() - start
    return result, elapsed


def measure_multiple_executions(
    func: Callable[..., Any], count: int, *args, **kwargs
) -> list[float]:
    """Execute a function multiple times and return execution times.

    Args:
        func: Function to execute
        count: Number of times to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        List of execution times in seconds
    """
    times = []
    for _ in range(count):
        start = time.monotonic()
        func(*args, **kwargs)
        elapsed = time.monotonic() - start
        times.append(elapsed)
    return times


def calculate_percentiles(times: list[float]) -> dict:
    """Calculate percentiles from a list of times.

    Delegates to the canonical statistical core (M-001): single definition,
    single algorithm — linear interpolation. Kept signature for e2e callers.

    Args:
        times: List of execution times in seconds

    Returns:
        Dictionary with p50, p90, p95, p99, mean, min, max
    """
    if not times:
        return {}

    from soar_lab.domain.statistics import percentile as _pct

    n = len(times)
    return {
        "p50": _pct(times, 50),
        "p90": _pct(times, 90),
        "p95": _pct(times, 95),
        "p99": _pct(times, 99),
        "mean": sum(times) / n,
        "min": min(times),
        "max": max(times),
    }
