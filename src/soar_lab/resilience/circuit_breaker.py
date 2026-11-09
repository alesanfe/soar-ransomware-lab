"""Circuit breaker pattern for protecting against repeated failing calls."""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import Enum
from typing import Any, Self

__all__ = ["CircuitBreakerState", "CircuitBreaker", "CircuitOpenError"]


class CircuitBreakerState(Enum):
    """States a circuit breaker can be in."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit is open.

    ``retryable=False`` tells retry policies NOT to retry: the breaker is
    intentionally shedding load — retrying would defeat it (RES-002).
    """

    retryable = False

    def __init__(self, message: str = "Circuit breaker is open") -> None:
        super().__init__(message)
        self.retryable = False


class CircuitBreaker:
    """Circuit breaker that blocks calls after a configurable failure threshold."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
        max_probe_requests: int = 3,
    ) -> None:
        """Initialize the CircuitBreaker with the given parameters.

        Args:
            failure_threshold: Number of failures before the circuit opens.
            recovery_timeout: Seconds to wait before transitioning from OPEN
                to HALF_OPEN.
            expected_exception: Exception type that counts as a failure.
            max_probe_requests: Max probe calls admitted while HALF_OPEN
                (RES-003); further calls are rejected until the state
                resolves.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.max_probe_requests = max_probe_requests
        self.state = CircuitBreakerState.CLOSED
        self.failures = 0
        self.last_failure_time = 0.0
        self._half_open_probes = 0

    def _pre_call(self) -> None:
        """State machine gate shared by ``call()`` and ``__enter__()``.

        OPEN → HALF_OPEN once recovery_timeout elapses. In HALF_OPEN only
        ``max_probe_requests`` probes are admitted; the rest are rejected
        (RES-003). Raises ``CircuitOpenError`` (never bare ``Exception``).
        """
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self._half_open_probes = 0
            else:
                raise CircuitOpenError("Circuit breaker is open")
        if self.state == CircuitBreakerState.HALF_OPEN:
            if self._half_open_probes >= self.max_probe_requests:
                raise CircuitOpenError("Circuit breaker half-open: probe limit reached")
            self._half_open_probes += 1

    def call(self, func: Callable, *args: object, **kwargs: object) -> Any:
        """Execute *func* through the circuit breaker.

        Args:
            func: Callable to invoke.
            *args: Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func*.

        Raises:
            CircuitOpenError: If the circuit rejects the call (RES-001).
            Exception: If *func* raises an exception.
        """
        self._pre_call()
        try:
            result = func(*args, **kwargs)
        except self.expected_exception:
            self._handle_failure()
            raise
        except Exception:  # pylint: disable=duplicate-except
            # Other exception types do not count as failures
            raise

        self._handle_success()
        return result

    def _handle_success(self) -> None:
        """Reset the failure counter and close the circuit."""
        self.failures = 0
        self._half_open_probes = 0
        self.state = CircuitBreakerState.CLOSED

    def _handle_failure(self) -> None:
        """Record a failure and open the circuit if the threshold is reached."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self._half_open_probes = 0
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
                self._half_open_probes = 0

    def __enter__(self) -> Self:
        """Enter the context manager — same gate semantics as ``call()``.

        RES-004: OPEN→HALF_OPEN transition, probe accounting,
        ``CircuitOpenError`` on rejection.

        Returns:
            The circuit breaker instance.

        Raises:
            CircuitOpenError: If the circuit rejects the call.
        """
        self._pre_call()
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
