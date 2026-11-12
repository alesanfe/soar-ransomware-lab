"""Branch coverage for resilience edges: mutually exclusive retry knobs,
linear/jitter strategies, timeout handler defaults, signal fallback, and
the circuit breaker's reset/record surfaces."""

import time

import pytest

from soar_lab.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitOpenError,
)
from soar_lab.resilience.retry import RetryPolicy, RetryStrategy
from soar_lab.resilience.timeout import TimeoutHandler, timeout_context


class TestRetryPolicyEdges:
    def test_both_max_retries_and_attempts_raises(self):
        with pytest.raises(ValueError, match=r"^Specify only one of max_retries or max_attempts$"):
            RetryPolicy(max_retries=2, max_attempts=4)

    def test_max_attempts_converts_to_retries(self):
        assert RetryPolicy(max_attempts=5).max_retries == 4

    def test_linear_backoff_delay_scales_with_attempt(self):
        p = RetryPolicy(strategy=RetryStrategy.LINEAR_BACKOFF, base_delay=2.0)
        assert p._calculate_delay(0) == 2.0
        assert p._calculate_delay(2) == 6.0

    def test_jittered_delay_positive_and_bounded(self, monkeypatch):
        p = RetryPolicy(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF_WITH_JITTER,
            base_delay=4.0,
            jitter_factor=0.5,
        )
        monkeypatch.setattr("soar_lab.resilience.retry.random.uniform", lambda a, b: -1.0)
        assert p._jittered_delay(1) == pytest.approx(4.0)  # 8 * (1 - 0.5)

    def test_retryable_false_attr_never_retried(self):
        class CircuitOpenError(Exception):
            retryable = False

        p = RetryPolicy()
        assert p._should_retry(CircuitOpenError()) is False
        assert p._should_retry(Exception()) is True

    def test_fixed_strategy_returns_base_delay(self):
        p = RetryPolicy(strategy=RetryStrategy.FIXED, base_delay=3.0)
        assert p._calculate_delay(0) == 3.0
        assert p._calculate_delay(5) == 3.0

    def test_non_retryable_excluded_even_if_in_retryable(self):
        p = RetryPolicy(retryable_errors=Exception, non_retryable_errors=ValueError)
        assert p._should_retry(ValueError("x")) is False
        assert p._should_retry(RuntimeError("x")) is True


class TestTimeoutHandlerEdges:
    def test_default_timeout_override(self):
        assert TimeoutHandler(timeout=9.0, default_timeout=2.0).timeout == 2.0
        assert TimeoutHandler(timeout=9.0).timeout == 9.0

    def test_context_noop_when_no_signal(self, monkeypatch):
        """_resolve_signum → None path: context becomes a no-op."""
        import soar_lab.resilience.timeout as to

        monkeypatch.setattr(to, "_resolve_signum", lambda: None)
        ran = False
        with timeout_context(0.01):  # must not raise — signal unavailable
            ran = True
        assert ran

    def test_context_cancels_timer_and_restores(self, monkeypatch):
        import soar_lab.resilience.timeout as to

        restored = []
        monkeypatch.setattr(to.signal, "signal", lambda s, h: restored.append((s, h)) or h)
        with timeout_context(5.0):
            pass
        # first call installs handler, second restores it
        assert len(restored) == 2


class TestCircuitBreakerSurfaces:
    @pytest.fixture
    def cb(self):
        return CircuitBreaker(failure_threshold=2, recovery_timeout=60)

    def test_record_success_failure_counters(self, cb):
        cb.record_failure()
        assert cb.failures == 1
        cb.record_success()
        assert cb.failures == 0

    def test_is_open_reflects_state(self, cb):
        assert cb.is_open() is False
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open() is True

    def test_attempt_reset_noop_when_not_open(self, cb):
        cb.attempt_reset()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_attempt_reset_stays_open_before_timeout(self, cb):
        cb.record_failure()
        cb.record_failure()
        cb.last_failure_time = time.time()  # just failed — timeout not elapsed
        cb.attempt_reset()
        assert cb.state == CircuitBreakerState.OPEN

    def test_attempt_reset_half_opens_after_timeout(self, cb):
        cb.record_failure()
        cb.record_failure()
        cb.last_failure_time = time.time() - 120  # past recovery_timeout
        cb.attempt_reset()
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_exit_counts_matching_exception_as_failure(self, cb):
        try:
            with cb:
                raise ValueError("expected type")
        except ValueError:
            pass
        assert cb.failures == 1

    def test_exit_counts_unmatched_exception_as_success(self, cb):
        cb_fail = CircuitBreaker(failure_threshold=2, expected_exception=KeyError)
        try:
            with cb_fail:
                raise ValueError("other")
        except ValueError:
            pass
        assert cb_fail.failures == 0


class TestDelayValues:
    """Mutation-hardening: assert exact delay arithmetic, not only bounds."""

    def test_exponential_values(self):
        p = RetryPolicy(base_delay=0.5, strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
        assert [p._calculate_delay(a) for a in range(4)] == [0.5, 1.0, 2.0, 4.0]

    def test_linear_values(self):
        p = RetryPolicy(base_delay=0.5, strategy=RetryStrategy.LINEAR_BACKOFF)
        assert [p._calculate_delay(a) for a in range(4)] == [0.5, 1.0, 1.5, 2.0]

    def test_fixed_values(self):
        p = RetryPolicy(base_delay=0.5, strategy=RetryStrategy.FIXED)
        assert [p._calculate_delay(a) for a in range(3)] == [0.5, 0.5, 0.5]

    def test_jittered_base_uses_pow_not_mul(self):
        # jitter_factor=0 -> jittered_delay == exponential base, exactly
        p = RetryPolicy(
            base_delay=0.5,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF_WITH_JITTER,
            jitter_factor=0.0,
        )
        assert [p._jittered_delay(a) for a in range(4)] == [0.5, 1.0, 2.0, 4.0]

    def test_jitter_bounded_by_factor(self):
        p = RetryPolicy(
            base_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF_WITH_JITTER,
            jitter_factor=0.25,
        )
        base = 1.0 * (2**2)
        for _ in range(50):
            d = p._jittered_delay(2)
            assert base * 0.75 <= d <= base * 1.25

    def test_jitter_never_negative(self):
        p = RetryPolicy(base_delay=0.5, jitter_factor=1.0)
        for _ in range(50):
            assert p._jittered_delay(1) >= 0.0

    def test_should_retry_retryable_flag_false(self):
        p = RetryPolicy()
        err = Exception("x")
        err.retryable = False
        assert p._should_retry(err) is False

    def test_should_retry_honors_non_retryable_types(self):
        p = RetryPolicy(retryable_errors=(Exception,), non_retryable_errors=(KeyError,))
        assert p._should_retry(KeyError()) is False
        assert p._should_retry(ValueError()) is True

    def test_should_retry_rejects_unlisted_types(self):
        p = RetryPolicy(retryable_errors=(ValueError,))
        assert p._should_retry(ValueError()) is True
        assert p._should_retry(KeyError()) is False

    def test_execute_raises_retry_timeout(self, monkeypatch):
        import soar_lab.resilience.retry as retry_mod

        p = RetryPolicy(max_retries=3, base_delay=0, timeout=0.0)
        t = [0.0]

        def fake_time():
            t[0] += 100.0
            return t[0]

        monkeypatch.setattr(retry_mod.time, "time", fake_time)
        with pytest.raises(Exception, match=r"^Retry\ timeout\ exceeded$"):
            p.execute(lambda: 1 / 0)

    def test_init_rejects_both_retries_and_attempts(self):
        with pytest.raises(ValueError, match=r"^Specify only one of max_retries or max_attempts$"):
            RetryPolicy(max_retries=2, max_attempts=3)

    def test_max_attempts_maps_to_retries(self):
        assert RetryPolicy(max_attempts=3).max_retries == 2


class TestBreakerMutationHardening:
    def test_defaults_exact(self):
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 30.0
        assert cb.max_probe_requests == 3
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failures == 0
        assert cb.last_failure_time == 0.0
        assert cb._half_open_probes == 0

    def test_open_error_default_message(self):
        e = CircuitOpenError()
        assert str(e) == "Circuit breaker is open"
        assert e.retryable is False

    def test_open_rejection_message_exact(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        with pytest.raises(CircuitOpenError, match=r"^Circuit\ breaker\ is\ open$"):
            cb.call(lambda: 1)

    def test_probe_limit_message_exact(self):
        cb = CircuitBreaker(failure_threshold=1, max_probe_requests=1)
        cb.record_failure()
        cb.state = CircuitBreakerState.HALF_OPEN
        cb._half_open_probes = 1
        with pytest.raises(
            CircuitOpenError, match=r"^Circuit breaker half-open: probe limit reached$"
        ):
            cb.call(lambda: 1)

    def test_recovery_boundary_exact_timeout(self, monkeypatch):
        import soar_lab.resilience.circuit_breaker as cb_mod

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        # elapsed exactly == recovery_timeout -> >= transitions to HALF_OPEN
        monkeypatch.setattr(cb_mod.time, "time", lambda: cb.last_failure_time + 30.0)
        cb._pre_call()
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_probe_count_increments_per_call(self):
        cb = CircuitBreaker(failure_threshold=1, max_probe_requests=2)
        cb.state = CircuitBreakerState.HALF_OPEN
        cb._pre_call()
        assert cb._half_open_probes == 1
        cb._pre_call()
        assert cb._half_open_probes == 2
        with pytest.raises(CircuitOpenError):
            cb._pre_call()

    def test_call_forwards_positional_args(self):
        cb = CircuitBreaker()
        assert cb.call(lambda a, b: a + b, 2, 3) == 5

    def test_handle_success_resets_everything(self):
        cb = CircuitBreaker()
        cb.state = CircuitBreakerState.HALF_OPEN
        cb._half_open_probes = 2
        cb.failures = 4
        cb._handle_success()
        assert cb.failures == 0
        assert cb._half_open_probes == 0
        assert cb.state == CircuitBreakerState.CLOSED

    def test_half_open_failure_reopens_and_zeroes_probes(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.state = CircuitBreakerState.HALF_OPEN
        cb._half_open_probes = 1
        cb._handle_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb._half_open_probes == 0
        assert cb.last_failure_time > 0

    def test_closed_failures_increment_and_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        assert cb.failures == 1 and cb.state == CircuitBreakerState.CLOSED
        cb.record_failure()
        cb.record_failure()
        assert cb.failures == 3 and cb.state == CircuitBreakerState.OPEN


class TestTimeoutMutationHardening:
    def test_default_timeout_values(self):
        h = TimeoutHandler()
        assert h.timeout == 5.0
        assert h.default_timeout == 5.0
        h2 = TimeoutHandler(timeout=2.0, default_timeout=3.0)
        assert h2.timeout == 3.0
        assert h2.default_timeout == 3.0

    def test_execute_forwards_positional_args(self):
        h = TimeoutHandler(timeout=5)
        # positional *args come right after func; timeout stays keyword-only
        assert h.execute_with_timeout(lambda a, b: a * b, 2, 3, timeout=2) == 6

    def test_run_uses_args_and_kwargs(self):
        h = TimeoutHandler(timeout=5)
        assert h.run(lambda a, b=0: a + b, 2, 3) == 5
        assert h.run(lambda a, b=0: a + b, 2, b=4) == 6

    def test_timeout_error_message_exact(self):
        import time as _t

        h = TimeoutHandler()
        with pytest.raises(TimeoutError, match=r"^Operation\ timed\ out$"):
            h.execute_with_timeout(lambda: _t.sleep(5), timeout=0.05)

    def test_cleanup_and_on_timeout_invoked(self):
        import time as _t

        calls = []
        h = TimeoutHandler()
        with pytest.raises(TimeoutError):
            h.execute_with_timeout(
                lambda: _t.sleep(5),
                timeout=0.05,
                cleanup=lambda: calls.append("cleanup"),
                on_timeout=lambda: calls.append("on_timeout"),
            )
        assert calls == ["cleanup", "on_timeout"]

    def test_cleanup_exception_swallowed(self):
        import time as _t

        h = TimeoutHandler()
        with pytest.raises(TimeoutError, match=r"^Operation\ timed\ out$"):
            h.execute_with_timeout(
                lambda: _t.sleep(5),
                timeout=0.05,
                cleanup=lambda: 1 / 0,
            )

    def test_explicit_timeout_used_over_default(self):
        import time as _t

        h = TimeoutHandler(timeout=30)
        # deadline mutants (or->and) would wait 30s; original times out fast
        with pytest.raises(TimeoutError):
            h.execute_with_timeout(lambda: _t.sleep(10), timeout=0.05)

    def test_func_exception_propagates(self):
        h = TimeoutHandler(timeout=5)
        with pytest.raises(KeyError):
            h.execute_with_timeout(lambda: {}["nope"], timeout=2)

    def test_run_uses_handler_timeout(self):
        import time as _t

        h = TimeoutHandler(timeout=0.05)
        with pytest.raises(TimeoutError):
            h.run(lambda: _t.sleep(10))

    def test_signal_handler_raises(self):
        from soar_lab.resilience.timeout import _timeout_signal_handler

        with pytest.raises(TimeoutError, match=r"^Operation\ timed\ out$"):
            _timeout_signal_handler(0, None)

    def test_resolve_signum_returns_int(self):
        from soar_lab.resilience.timeout import _resolve_signum

        assert isinstance(_resolve_signum(), int)

    def test_timeout_context_default_and_lifecycle(self):
        from soar_lab.resilience.timeout import _TimeoutContext, timeout_context

        ctx = timeout_context()
        assert ctx.timeout == 5.0
        assert isinstance(ctx, _TimeoutContext)
        ctx2 = timeout_context(2.5)
        assert ctx2.timeout == 2.5
        with ctx2:
            pass
        assert ctx2._timer is not None and ctx2._timer.finished.is_set()

    def test_resolve_signum_prefers_sigbreak(self, monkeypatch):
        import soar_lab.resilience.timeout as to

        monkeypatch.setattr(to.signal, "SIGBREAK", 777, raising=False)
        assert to._resolve_signum() == 777

    def test_resolve_signum_none_when_no_signal_available(self, monkeypatch):
        import soar_lab.resilience.timeout as to

        monkeypatch.delattr(to.signal, "SIGBREAK", raising=False)
        monkeypatch.delattr(to.signal, "SIGALRM", raising=False)
        assert to._resolve_signum() is None

    def test_worker_thread_created_as_daemon(self, monkeypatch):
        import soar_lab.resilience.timeout as to

        seen = {}

        class FakeThread:
            def __init__(self, target=None, daemon=None):
                seen["daemon"] = daemon
                self._target = target

            def start(self):
                self._target()

        monkeypatch.setattr(to.threading, "Thread", FakeThread)
        assert TimeoutHandler(timeout=5).execute_with_timeout(lambda: 42) == 42
        assert seen["daemon"] is True

    def test_deadline_falls_back_to_self_timeout_when_default_zeroed(self):
        # `or` -> `and` mutant: deadline = timeout or (default_timeout and self.timeout)
        # -> deadline 0 -> wait(0) must see the still-running worker thread
        import time as _t

        h = TimeoutHandler(timeout=5)
        h.default_timeout = 0  # falsy override — original falls back to self.timeout
        assert h.execute_with_timeout(lambda: (_t.sleep(0.05), "ok")[1]) == "ok"


class TestRetryMutationHardening:
    def test_defaults_exact(self):
        p = RetryPolicy()
        assert p.jitter_factor == 0.0
        assert p.base_delay == 1.0
        assert p.max_retries == 3
        assert p.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert p.timeout is None
        assert p.retryable_errors == (Exception,)
        assert p.non_retryable_errors == ()
        assert p.on_retry is None

    def test_max_retries_clamps_zero(self):
        assert RetryPolicy(max_attempts=1).max_retries == 0
        assert RetryPolicy(max_attempts=0).max_retries == 3  # falsy -> default 4-1

    def test_to_tuple_normalizes_iterable(self):
        p = RetryPolicy(retryable_errors=[ValueError, KeyError])
        assert p.retryable_errors == (ValueError, KeyError)
        p2 = RetryPolicy(retryable_errors=ValueError)
        assert p2.retryable_errors == (ValueError,)

    def test_value_error_message_exact(self):
        with pytest.raises(ValueError, match=r"^Specify only one of max_retries or max_attempts$"):
            RetryPolicy(max_retries=1, max_attempts=2)

    def test_execute_call_count_bounded(self):
        p = RetryPolicy(max_retries=1, base_delay=0)
        calls = []

        def fail():
            calls.append(1)
            raise ValueError("x")

        with pytest.raises(ValueError):
            p.execute(fail)
        assert len(calls) == 2  # max_retries + 1, not + 2

    def test_execute_forwards_positional_args(self):
        p = RetryPolicy(base_delay=0)
        assert p.execute(lambda a, b: a - b, 10, 3) == 7

    def test_on_retry_receives_attempt_and_error(self):
        seen = []
        p = RetryPolicy(max_retries=2, base_delay=0, on_retry=lambda n, e: seen.append((n, e)))
        with pytest.raises(ValueError, match=r"^boom$"):
            p.execute(lambda: (_ for _ in ()).throw(ValueError("boom")))
        assert [n for n, _ in seen] == [1, 2]
        assert all(isinstance(e, ValueError) for _, e in seen)

    def test_no_sleep_when_delay_zero(self, monkeypatch):
        import soar_lab.resilience.retry as retry_mod

        sleeps = []
        monkeypatch.setattr(retry_mod.time, "sleep", lambda d: sleeps.append(d))
        p = RetryPolicy(max_retries=1, base_delay=0, strategy=RetryStrategy.FIXED)
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) == 1:
                raise ValueError
            return "ok"

        assert p.execute(flaky) == "ok"
        assert sleeps == []  # delay>0 required; delay==0 must not sleep

    def test_sleep_called_for_small_positive_delay(self, monkeypatch):
        import soar_lab.resilience.retry as retry_mod

        sleeps = []
        monkeypatch.setattr(retry_mod.time, "sleep", lambda d: sleeps.append(d))
        p = RetryPolicy(max_retries=1, base_delay=0.5, strategy=RetryStrategy.FIXED)
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) == 1:
                raise ValueError
            return "ok"

        assert p.execute(flaky) == "ok"
        assert sleeps == [0.5]

    def test_exhausted_raises_last_error_not_generic(self):
        p = RetryPolicy(max_retries=1, base_delay=0)
        with pytest.raises(KeyError):
            p.execute(lambda: {}["gone"])

    def test_timeout_boundary_exact(self, monkeypatch):
        import soar_lab.resilience.retry as retry_mod

        times = iter([0.0, 5.0])  # start, then elapsed exactly == timeout
        monkeypatch.setattr(retry_mod.time, "time", lambda: next(times))
        monkeypatch.setattr(retry_mod.time, "sleep", lambda d: None)
        p = RetryPolicy(max_retries=3, base_delay=0, timeout=5.0)
        called = []
        with pytest.raises(Exception, match=r"^Retry\ timeout\ exceeded$"):
            p.execute(lambda: called.append(1))
        assert called == []  # >= fires at exactly the boundary

    def test_jitter_uniform_called_with_pm_one(self, monkeypatch):
        import soar_lab.resilience.retry as retry_mod

        captured = []
        monkeypatch.setattr(
            retry_mod.random, "uniform", lambda a, b: captured.append((a, b)) or 0.5
        )
        p = RetryPolicy(base_delay=1.0, jitter_factor=0.25)
        d = p._jittered_delay(2)
        assert captured == [(-1, 1)]
        base = 1.0 * (2**2)
        assert d == base + base * 0.25 * 0.5

    def test_jitter_clamps_to_zero_not_one(self, monkeypatch):
        import soar_lab.resilience.retry as retry_mod

        monkeypatch.setattr(retry_mod.random, "uniform", lambda a, b: -1)
        p = RetryPolicy(base_delay=1.0, jitter_factor=1.0)
        # delay*(1 + 1*(-1)) = 0 -> clamp floor is 0.0, not 1.0
        assert p._jittered_delay(2) == 0.0

    def test_delay_param_overrides_base_delay(self):
        # `or True` mutant always picks base_delay
        assert RetryPolicy(delay=7.5).base_delay == 7.5
        assert RetryPolicy(delay=7.5, base_delay=2.0).base_delay == 7.5

    def test_probe_counter_resets_to_zero_on_open_to_half_open(self):
        # `_half_open_probes = 1` mutant: first probe after transition must read 1
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30, max_probe_requests=3)
        cb.record_failure()
        cb.last_failure_time = time.time() - 60  # recovery elapsed
        cb._pre_call()  # OPEN -> HALF_OPEN, then probe += 1
        assert cb._half_open_probes == 1

    def test_attempt_reset_boundary_exact(self, monkeypatch):
        import soar_lab.resilience.circuit_breaker as cb_mod

        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)
        cb.record_failure()
        monkeypatch.setattr(cb_mod.time, "time", lambda: cb.last_failure_time + 30.0)
        cb.attempt_reset()
        assert cb.state == CircuitBreakerState.HALF_OPEN  # >=, not >

    def test_call_forwards_kwargs(self):
        cb = CircuitBreaker()
        assert cb.call(lambda **kw: kw["x"] * 2, x=4) == 8

    def test_retry_timeout_start_above_zero(self, monkeypatch):
        import soar_lab.resilience.retry as retry_mod

        # start=100, now=101: `-` gives 1 < 5 (retry), `+` gives 201 >= 5 (raise)
        times = iter([100.0, 101.0, 106.0])
        monkeypatch.setattr(retry_mod.time, "time", lambda: next(times))
        monkeypatch.setattr(retry_mod.time, "sleep", lambda d: None)
        p = RetryPolicy(max_retries=1, base_delay=0, timeout=5.0)
        called = []
        with pytest.raises(Exception, match="^Retry timeout exceeded$"):
            p.execute(lambda: called.append(1) or (_ for _ in ()).throw(ValueError))
        assert called == [1]  # `-` proceeds to attempt; `+` raises before call

    def test_timer_daemon_flag(self):
        from soar_lab.resilience.timeout import timeout_context

        ctx = timeout_context(30)
        with ctx:
            assert ctx._timer.daemon is True

    def test_execute_forwards_kwargs(self):
        p = RetryPolicy(max_retries=0)
        assert p.execute(lambda k: k * 2, k=4) == 8

    def test_half_open_probe_reset_to_zero(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0, max_probe_requests=1)
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        cb.attempt_reset()
        # probes reset to 0: first probe with max=1 must be admitted
        assert cb.call(lambda: "ok") == "ok"
