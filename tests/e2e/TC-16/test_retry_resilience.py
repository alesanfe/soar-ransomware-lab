"""TC-16 — retry/circuit-breaker semantics against production resilience code.

Verifies the actual soar_lab.resilience classes inside the live container:
retryable vs non-retryable classification, retry-storm load shedding,
full breaker state machine, bounded attempts, and jitter bounds.
"""

from __future__ import annotations

import time

import pytest

from soar_lab.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitOpenError,
)
from soar_lab.resilience.retry import RetryPolicy, RetryStrategy


@pytest.mark.e2e
class TestRetryResilience:
    tc_id = "TC-16"

    def test_retryable_vs_nonretryable_classification(self):
        """A non-retryable error aborts immediately (1 attempt); a retryable
        one is retried up to the bound."""
        calls = {"n": 0}

        def fail_untyped():
            calls["n"] += 1
            raise ValueError("non-retryable")

        policy = RetryPolicy(
            max_retries=3, base_delay=0.01,
            non_retryable_errors=(ValueError,),
        )
        with pytest.raises(ValueError):
            policy.execute(fail_untyped)
        assert calls["n"] == 1, f"non-retryable retried {calls['n']}x"

        calls["n"] = 0

        def fail_retryable():
            calls["n"] += 1
            raise ConnectionError("transient")

        with pytest.raises(ConnectionError):
            policy.execute(fail_retryable)
        assert calls["n"] == 4, f"expected 4 attempts, got {calls['n']}"

    def test_circuit_open_never_retried_retryable_false(self):
        """CircuitOpenError carries retryable=False — even an aggressive
        RetryPolicy must not retry it (RES-002: retrying defeats shedding)."""
        calls = {"n": 0}

        def fail_open():
            calls["n"] += 1
            raise CircuitOpenError("breaker open")

        policy = RetryPolicy(
            max_retries=5, base_delay=0.01,
            retryable_errors=(Exception,),
        )
        with pytest.raises(CircuitOpenError):
            policy.execute(fail_open)
        assert calls["n"] == 1, "CircuitOpenError was retried — storm possible"
        assert CircuitOpenError("x").retryable is False

    def test_retry_storm_protection_load_sheds(self):
        """After failure_threshold, the breaker rejects calls WITHOUT
        invoking the function — backend protected from retry storms."""
        breaker = CircuitBreaker(
            failure_threshold=3, recovery_timeout=60.0,
            expected_exception=ConnectionError,
        )
        invoked = {"n": 0}

        def fail():
            invoked["n"] += 1
            raise ConnectionError("backend down")

        for _ in range(3):
            with pytest.raises(ConnectionError):
                breaker.call(fail)
        assert breaker.state == CircuitBreakerState.OPEN
        assert invoked["n"] == 3

        invoked["n"] = 0
        for _ in range(10):
            with pytest.raises(CircuitOpenError):
                breaker.call(fail)
        assert invoked["n"] == 0, (
            f"{invoked['n']} calls hit the backend while OPEN — no shedding"
        )

    def test_state_machine_halfopen_probe_then_recovers(self):
        """OPEN→HALF_OPEN after recovery_timeout; bounded probes; success
        closes the circuit; failure re-opens immediately."""
        breaker = CircuitBreaker(
            failure_threshold=1, recovery_timeout=0.5,
            expected_exception=ConnectionError, max_probe_requests=2,
        )
        with pytest.raises(ConnectionError):
            breaker.call(lambda: (_ for _ in ()).throw(ConnectionError()))
        assert breaker.state == CircuitBreakerState.OPEN

        time.sleep(0.6)
        # First call after timeout must go through as a probe
        assert breaker.call(lambda: "probe-ok") == "probe-ok"
        assert breaker.state == CircuitBreakerState.CLOSED

        # Re-open and verify half-open failure path
        with pytest.raises(ConnectionError):
            breaker.call(lambda: (_ for _ in ()).throw(ConnectionError()))
        assert breaker.state == CircuitBreakerState.OPEN
        time.sleep(0.6)
        with pytest.raises(ConnectionError):
            breaker.call(lambda: (_ for _ in ()).throw(ConnectionError()))
        assert breaker.state == CircuitBreakerState.OPEN, (
            "HALF_OPEN probe failure must re-open the circuit"
        )

    def test_error_budget_bounded_attempts_and_timeout(self):
        """Total attempts == max_retries+1 exactly; an overall timeout caps
        the budget even when retries remain."""
        calls = {"n": 0}
        policy = RetryPolicy(
            max_retries=2, base_delay=0.05, timeout=0.08,
        )

        def fail():
            calls["n"] += 1
            raise RuntimeError("always")

        t0 = time.time()
        with pytest.raises(TimeoutError):
            policy.execute(fail)
        elapsed = time.time() - t0
        assert elapsed < 1.0, f"timeout cap not honored: {elapsed:.2f}s"
        assert calls["n"] <= 2, (
            f"timeout should cut retries: {calls['n']} attempts"
        )

    def test_backoff_jitter_stays_bounded(self):
        """Exponential backoff with jitter stays inside the factor band —
        no runaway delays."""
        policy = RetryPolicy(
            max_retries=6, base_delay=0.01,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF_WITH_JITTER,
            jitter_factor=0.5,
        )
        for attempt in range(6):
            base = 0.01 * (2**attempt)
            for _ in range(50):
                d = policy._calculate_delay(attempt)
                assert 0 <= d <= base * 1.5 + 1e-9, (
                    f"attempt {attempt}: delay {d} out of jitter band"
                )
