import random
import time
from enum import Enum
from typing import Callable, Iterable, Optional, Tuple, Type, Union


class RetryStrategy(Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF_WITH_JITTER = "exponential_backoff_with_jitter"


class RetryPolicy:
    def __init__(
        self,
        max_attempts: Optional[int] = None,
        max_retries: Optional[int] = None,
        delay: Optional[float] = None,
        base_delay: float = 1.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        retryable_errors: Optional[Union[Type[Exception], Iterable[Type[Exception]]]] = None,
        non_retryable_errors: Optional[Union[Type[Exception], Iterable[Type[Exception]]]] = None,
        jitter_factor: float = 0.0,
        timeout: Optional[float] = None,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
    ) -> None:
        if max_retries is not None and max_attempts is not None:
            raise ValueError("Specify only one of max_retries or max_attempts")

        self.max_retries = max_retries if max_retries is not None else (max_attempts if max_attempts is not None else 3)
        self.base_delay = base_delay if delay is None else delay
        self.strategy = strategy
        self.jitter_factor = jitter_factor
        self.timeout = timeout
        self.on_retry = on_retry

        self.retryable_errors = self._to_tuple(retryable_errors) if retryable_errors else (Exception,)
        self.non_retryable_errors = self._to_tuple(non_retryable_errors) if non_retryable_errors else ()

    @staticmethod
    def _to_tuple(errors):
        if isinstance(errors, type) and issubclass(errors, Exception):
            return (errors,)
        return tuple(errors)

    def _should_retry(self, error: Exception) -> bool:
        if isinstance(error, self.non_retryable_errors):
            return False
        if isinstance(error, self.retryable_errors):
            return True
        return False

    def _calculate_delay(self, attempt: int) -> float:
        if self.strategy in (RetryStrategy.EXPONENTIAL, RetryStrategy.EXPONENTIAL_BACKOFF):
            delay = self.base_delay * (2 ** attempt)
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.base_delay * (attempt + 1)
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF_WITH_JITTER:
            delay = self.base_delay * (2 ** attempt)
            if self.jitter_factor > 0:
                jitter = delay * self.jitter_factor * random.uniform(-1, 1)
                delay = max(0.0, delay + jitter)
        else:
            delay = self.base_delay
        return delay

    def execute(self, func: Callable, *args, **kwargs):
        start_time = time.time() if self.timeout is not None else None

        last_error = None
        for attempt in range(self.max_retries + 1):
            if start_time is not None and time.time() - start_time >= self.timeout:
                raise Exception("Retry timeout exceeded")

            try:
                return func(*args, **kwargs)
            except Exception as error:
                last_error = error
                if attempt == self.max_retries:
                    raise
                if not self._should_retry(error):
                    raise

                if self.on_retry is not None:
                    self.on_retry(attempt + 1, error)

                delay = self._calculate_delay(attempt)
                if delay > 0:
                    time.sleep(delay)

        raise last_error if last_error is not None else Exception("Retry exhausted")
