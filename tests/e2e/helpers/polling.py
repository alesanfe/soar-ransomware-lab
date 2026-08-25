"""Shared polling helpers for E2E tests."""

import time
from collections.abc import Callable
from typing import Any

__all__ = [
    "poll_until",
    "poll_for_value",
    "poll_for_not_none",
]


def poll_until(
    condition: Callable[[], bool],
    timeout: int = 60,
    interval: float = 1.0,
    error_message: str = "Condition not met within timeout",
) -> bool:
    """Poll until a condition is met or timeout is reached.

    Args:
        condition: Function that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between polls in seconds
        error_message: Error message to raise on timeout

    Returns:
        True if condition was met, False otherwise
    """
    start = time.time()
    while time.time() - start < timeout:
        if condition():
            return True
        time.sleep(interval)
    raise TimeoutError(error_message)


def poll_for_value(
    getter: Callable[[], Any],
    expected_value: Any,
    timeout: int = 60,
    interval: float = 1.0,
    error_message: str = "Expected value not found within timeout",
) -> bool:
    """Poll until a getter returns the expected value.

    Args:
        getter: Function that returns a value
        expected_value: Value to wait for
        timeout: Maximum time to wait in seconds
        interval: Time between polls in seconds
        error_message: Error message to raise on timeout

    Returns:
        True if expected value was found, False otherwise
    """
    start = time.time()
    while time.time() - start < timeout:
        if getter() == expected_value:
            return True
        time.sleep(interval)
    raise TimeoutError(error_message)


def poll_for_not_none(
    getter: Callable[[], Any | None],
    timeout: int = 60,
    interval: float = 1.0,
    error_message: str = "Value remained None within timeout",
) -> Any:
    """Poll until a getter returns a non-None value.

    Args:
        getter: Function that returns a value or None
        timeout: Maximum time to wait in seconds
        interval: Time between polls in seconds
        error_message: Error message to raise on timeout

    Returns:
        The non-None value
    """
    start = time.time()
    while time.time() - start < timeout:
        value = getter()
        if value is not None:
            return value
        time.sleep(interval)
    raise TimeoutError(error_message)
