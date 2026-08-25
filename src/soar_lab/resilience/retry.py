"""Retry policy with configurable backoff strategies and jitter."""

import random
import time
from collections.abc import Callable, Iterable
from enum import Enum
from typing import Any

__all__ = ["RetryStrategy", "RetryPolicy"]


class RetryStrategy(Enum):
    """Backoff strategies for calculating delay between retry attempts."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF_WITH_JITTER = "exponential_backoff_with_jitter"


_EXPONENTIAL_STRATEGIES = frozenset({RetryStrategy.EXPONENTIAL, RetryStrategy.EXPONENTIAL_BACKOFF})


class RetryPolicy:
    """Configurable retry policy with backoff, jitter, and error filtering."""

    def __init__(
        self,
        max_attempts: int | None = None,
        max_retries: int | None = None,
        delay: float | None = None,
        base_delay: float = 1.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_errors: type[Exception] | Iterable[type[Exception]] | None = None,
        non_retryable_errors: type[Exception] | Iterable[type[Exception]] | None = None,
        jitter_factor: float = 0.0,
        timeout: float | None = None,
        on_retry: Callable[[int, Exception], None] | None = None,
    ) -> None:
        """Initialize the RetryPolicy with the given parameters.

        Args:
            max_attempts: Maximum number of attempts (mutually exclusive with
                *max_retries*).
            max_retries: Maximum number of retries (mutually exclusive with
                *max_attempts*).
            delay: Fixed delay between attempts; overrides *base_delay* when set.
            base_delay: Base delay used by backoff calculations.
            strategy: Backoff strategy for computing delay.
            retryable_errors: Exception type(s) that should trigger a retry.
            non_retryable_errors: Exception type(s) that should never be retried.
            jitter_factor: Jitter factor (0–1) for randomized delay variation.
            timeout: Optional overall timeout in seconds.
            on_retry: Optional callback invoked before each retry with the
                attempt number and the exception.

        Raises:
            ValueError: If both *max_retries* and *max_attempts* are provided.
        """
        if max_retries is not None and max_attempts is not None:
            raise ValueError("Specify only one of max_retries or max_attempts")
        self.max_retries = max_retries if max_retries is not None else (max_attempts or 3)
        self.base_delay = base_delay if delay is None else delay
        self.strategy = strategy
        self.jitter_factor = jitter_factor
        self.timeout = timeout
        self.on_retry = on_retry
        self.retryable_errors = (
            self._to_tuple(retryable_errors) if retryable_errors else (Exception,)
        )
        self.non_retryable_errors = (
            self._to_tuple(non_retryable_errors) if non_retryable_errors else ()
        )

    @staticmethod
    def _to_tuple(
        errors: type[Exception] | Iterable[type[Exception]],
    ) -> tuple[type[Exception], ...]:
        """Normalize an error spec into a tuple of exception classes.

        Args:
            errors: A single exception class or an iterable of exception classes.

        Returns:
            A tuple of exception classes.
        """
        if isinstance(errors, type) and issubclass(errors, Exception):
            return (errors,)
        return tuple(errors)

    def _should_retry(self, error: Exception) -> bool:
        """Determine whether *error* should trigger a retry.

        Args:
            error: The exception that was raised.

        Returns:
            True if the error is retryable and not in the non-retryable set.
        """
        return not isinstance(error, self.non_retryable_errors) and isinstance(
            error, self.retryable_errors
        )

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate the delay before the next retry attempt.

        Args:
            attempt: Zero-based attempt index.

        Returns:
            Delay in seconds before the next retry.
        """
        if self.strategy in _EXPONENTIAL_STRATEGIES:
            return self.base_delay * (2**attempt)
        if self.strategy == RetryStrategy.LINEAR_BACKOFF:
            return self.base_delay * (attempt + 1)
        if self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF_WITH_JITTER:
            return self._jittered_delay(attempt)
        return self.base_delay

    def _jittered_delay(self, attempt: int) -> float:
        """Compute an exponential backoff delay with optional jitter.

        Args:
            attempt: Zero-based attempt index.

        Returns:
            Jittered delay in seconds, clamped to a minimum of 0.
        """
        delay = self.base_delay * (2**attempt)
        if self.jitter_factor > 0:
            delay = max(0.0, delay + delay * self.jitter_factor * random.uniform(-1, 1))
        return delay

    def execute(self, func: Callable, *args: object, **kwargs: object) -> Any:
        """Execute *func* with retry according to the configured policy.

        Args:
            func: Callable to execute.
            *args: Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func* on success.

        Raises:
            Exception: The last error if all retries are exhausted or the
                timeout is exceeded.
        """
        start_time = time.time() if self.timeout is not None else None
        last_error = None
        for attempt in range(self.max_retries + 1):
            if start_time is not None and time.time() - start_time >= self.timeout:
                raise Exception("Retry timeout exceeded")
            try:
                return func(*args, **kwargs)
            except Exception as error:
                last_error = error
                if attempt == self.max_retries or not self._should_retry(error):
                    raise
                if self.on_retry is not None:
                    self.on_retry(attempt + 1, error)
                delay = self._calculate_delay(attempt)
                if delay > 0:
                    time.sleep(delay)
        raise last_error if last_error is not None else Exception("Retry exhausted")
