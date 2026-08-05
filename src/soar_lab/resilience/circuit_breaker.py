from enum import Enum
import time


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exception: type = Exception,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.state = CircuitBreakerState.CLOSED
        self.failures = 0
        self.last_failure_time = 0.0

    def call(self, func, *args, **kwargs):
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
        except self.expected_exception as exc:
            self._handle_failure()
            raise
        except Exception as exc:
            # Other exception types do not count as failures
            raise

        self._handle_success()
        return result

    def _handle_success(self) -> None:
        self.failures = 0
        self.state = CircuitBreakerState.CLOSED

    def _handle_failure(self) -> None:
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.last_failure_time = time.time()
            return

        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN

    def record_success(self) -> None:
        self._handle_success()

    def record_failure(self) -> None:
        self._handle_failure()

    def is_open(self) -> bool:
        return self.state == CircuitBreakerState.OPEN

    def attempt_reset(self) -> None:
        if self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN

    def __enter__(self):
        if self.state == CircuitBreakerState.OPEN:
            raise Exception("Circuit breaker is open")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, self.expected_exception):
            self._handle_failure()
        else:
            self._handle_success()
        return False
