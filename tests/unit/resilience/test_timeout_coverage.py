#!/usr/bin/env python3
"""Coverage for the thread-based timeout executor and signal context."""

import signal
import threading
import time

import pytest

from soar_lab.resilience.timeout import (
    TimeoutHandler,
    _resolve_signum,
    _TimeoutContext,
    _timeout_signal_handler,
    timeout_context,
)


class TestExecuteWithTimeout:
    def test_returns_result(self):
        h = TimeoutHandler(timeout=5.0)
        assert h.execute_with_timeout(lambda a, b: a + b, 2, 3) == 5

    def test_timeout_invokes_callbacks(self):
        h = TimeoutHandler(timeout=5.0)
        called = []
        with pytest.raises(TimeoutError):
            h.execute_with_timeout(
                time.sleep,
                30,
                timeout=0.05,
                cleanup=lambda: called.append("c"),
                on_timeout=lambda: called.append("t"),
            )
        assert called == ["c", "t"]

    def test_func_exception_propagates(self):
        h = TimeoutHandler(timeout=5.0)

        def boom():
            raise ValueError("inner")

        with pytest.raises(ValueError, match="inner"):
            h.execute_with_timeout(boom, timeout=1.0)

    def test_run_uses_default_timeout(self):
        h = TimeoutHandler(timeout=5.0)
        assert h.run(lambda: "ok") == "ok"


class TestSignalHelpers:
    def test_handler_raises_timeout(self):
        with pytest.raises(TimeoutError, match="timed out"):
            _timeout_signal_handler(signal.SIGALRM, None)

    def test_resolve_signum(self):
        assert _resolve_signum() in (getattr(signal, "SIGBREAK", None), signal.SIGALRM)

    def test_context_without_signum_noop(self):
        ctx = _TimeoutContext(1.0)
        ctx._signum = None
        assert ctx.__enter__() is ctx
        ctx.__exit__(None, None, None)  # no timer/handler — must not raise

    def test_context_arms_and_disarms(self):
        ctx = _TimeoutContext(30.0)
        if ctx._signum is None:
            pytest.skip("no signal support on this platform")
        with ctx:
            assert ctx._timer is not None and ctx._timer.is_alive()
            assert signal.getsignal(ctx._signum) is _timeout_signal_handler
        assert ctx._timer.finished.is_set()  # cancelled on exit
        assert signal.getsignal(ctx._signum) is not _timeout_signal_handler

    def test_context_exit_without_timer(self):
        ctx = _TimeoutContext(1.0)
        ctx._timer = None
        ctx.__exit__(None, None, None)

    def test_timeout_context_factory(self):
        assert isinstance(timeout_context(2.5), _TimeoutContext)
        assert timeout_context(2.5).timeout == 2.5
