"""Unit tests for DockerMixin._check_with_warmup_retries.

The e2e health gate retries transient network conditions (warmup,
memory pressure) but must NOT retry definitive answers (401, 404,
"not configured") — and must never mask a real failure behind
retries that all fail.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "e2e"))

from base.docker_mixin import DockerMixin


@pytest.fixture()
def mixin(monkeypatch):
    m = DockerMixin()
    m._log = lambda *a, **k: None
    monkeypatch.setattr(time, "sleep", lambda s: None)
    return m


def _seq(*results):
    it = iter(results)

    def check():
        return next(it, results[-1])

    return check


class TestWarmupRetries:
    def test_transient_then_ok_returns_ok(self, mixin):
        check = _seq((False, "Connection refused"), (True, "OK"))
        assert mixin._check_with_warmup_retries("X", check) == (True, "OK")

    def test_all_transient_retries_exhausted_returns_last(self, mixin):
        check = _seq(
            (False, "Read timed out"),
            (False, "Read timed out"),
            (False, "Read timed out"),
        )
        ok, msg = mixin._check_with_warmup_retries("X", check)
        assert ok is False and "timed out" in msg

    def test_definitive_failure_not_retried(self, mixin):
        calls = []

        def check():
            calls.append(1)
            return False, "API key invalid (401)"

        ok, msg = mixin._check_with_warmup_retries("X", check)
        assert ok is False
        assert calls == [1], "definitive failure must not be retried"

    def test_transient_then_definitive_stops_early(self, mixin):
        check = _seq(
            (False, "Connection refused"),
            (False, "API key invalid (401)"),
        )
        ok, msg = mixin._check_with_warmup_retries("X", check)
        assert ok is False and "401" in msg

    def test_exception_in_check_is_retried(self, mixin):
        calls = []

        def check():
            calls.append(1)
            if len(calls) == 1:
                raise ConnectionError("refused")
            return True, "OK"

        ok, _ = mixin._check_with_warmup_retries("X", check)
        assert ok is True and len(calls) == 2


class TestTransientMarkers:
    @pytest.mark.parametrize(
        "msg",
        [
            "Read timed out. (read timeout=10)",
            "Connection refused",
            "Connection reset by peer",
            "Max retries exceeded with url",
            "Temporary failure in name resolution",
        ],
    )
    def test_transient_markers_match(self, mixin, msg):
        assert mixin._is_transient_health_error(msg) is True

    @pytest.mark.parametrize(
        "msg",
        [
            "API key invalid (401)",
            "MISP_API_KEY not configured",
            "404 Not Found",
            "Authentication required",
        ],
    )
    def test_definitive_not_marked_transient(self, mixin, msg):
        assert mixin._is_transient_health_error(msg) is False
