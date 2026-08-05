"""
Shared timing helpers for E2E tests.
"""

import time
from contextlib import contextmanager
from typing import Callable, Any, List


@contextmanager
def measure_time():
    """Context manager to measure execution time."""
    start = time.time()
    yield
    elapsed = time.time() - start
    return elapsed


def time_execution(func: Callable[..., Any], *args, **kwargs) -> tuple[Any, float]:
    """
    Execute a function and return its result along with execution time.

    Args:
        func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function

    Returns:
        Tuple of (result, elapsed_time_seconds)
    """
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed


def measure_multiple_executions(func: Callable[..., Any], count: int, *args, **kwargs) -> List[float]:
    """
    Execute a function multiple times and return execution times.

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
        start = time.time()
        func(*args, **kwargs)
        elapsed = time.time() - start
        times.append(elapsed)
    return times


def calculate_percentiles(times: List[float]) -> dict:
    """
    Calculate percentiles from a list of times.

    Args:
        times: List of execution times in seconds

    Returns:
        Dictionary with p50, p90, p95, p99, mean, min, max
    """
    if not times:
        return {}

    sorted_times = sorted(times)
    n = len(sorted_times)

    def percentile(p: float) -> float:
        index = int(p * n)
        return sorted_times[min(index, n - 1)]

    return {
        "p50": percentile(0.5),
        "p90": percentile(0.9),
        "p95": percentile(0.95),
        "p99": percentile(0.99),
        "mean": sum(times) / n,
        "min": min(times),
        "max": max(times)
    }
