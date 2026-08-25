"""Circuit breaker pattern for protecting against repeated failing calls."""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import Enum
from typing import Any, Self

__all__ = ["CircuitBreakerState", "CircuitBreaker"]


class CircuitBreakerState(Enum):
    """States a circuit breaker can be in."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker that blocks calls after a configurable failure threshold."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
    ) -> None:
        """Initialize the CircuitBreaker with the given parameters.

        Args:
            failure_threshold: Number of failures before the circuit opens.
            recovery_timeout: Seconds to wait before transitioning from OPEN
                to HALF_OPEN.
            expected_exception: Exception type that counts as a failure.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.state = CircuitBreakerState.CLOSED
        self.failures = 0
        self.last_failure_time = 0.0

    def call(self, func: Callable, *args: object, **kwargs: object) -> Any:
        """Execute *func* through the circuit breaker.

        Args:
            func: Callable to invoke.
            *args: Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func*.

        Raises:
            Exception: If the circuit is open or *func* raises an exception.
        """
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
        except self.expected_exception:
            self._handle_failure()
            raise
        except Exception:
            # Other exception types do not count as failures
            raise

        self._handle_success()
        return result

    def _handle_success(self) -> None:
        """Reset the failure counter and close the circuit."""
        self.failures = 0
        self.state = CircuitBreakerState.CLOSED

    def _handle_failure(self) -> None:
        """Record a failure and open the circuit if the threshold is reached."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.last_failure_time = time.time()
            return

        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

    def record_success(self) -> None:
        """Record a successful call, resetting the failure counter."""
        self._handle_success()

    def record_failure(self) -> None:
        """Record a failed call, potentially opening the circuit."""
        self._handle_failure()

    def is_open(self) -> bool:
        """Return whether the circuit is currently in the OPEN state."""
        return self.state == CircuitBreakerState.OPEN

    def attempt_reset(self) -> None:
        """Transition from OPEN to HALF_OPEN if the recovery timeout has elapsed."""
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN

    def __enter__(self) -> Self:
        """Enter the context manager, raising if the circuit is open.

        Returns:
            The circuit breaker instance.

        Raises:
            Exception: If the circuit is currently OPEN.
        """
        if self.state == CircuitBreakerState.OPEN:
            raise Exception("Circuit breaker is open")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        _exc_tb: object,
    ) -> None:
        """Exit the context manager, recording success or failure.

        Args:
            exc_type: Exception type raised within the block, if any.
            exc_val: Exception instance raised, if any.
            _exc_tb: Traceback object, if any.
        """
        if exc_type is not None and issubclass(exc_type, self.expected_exception):
            self._handle_failure()
        else:
            self._handle_success()
