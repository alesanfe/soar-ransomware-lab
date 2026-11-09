"""Unit tests for IsolationMixin + timeouts table (E2E-ISO-001/TIME-001/002)."""

from __future__ import annotations

import itertools
import time

import pytest

from tests.e2e.base.isolation_mixin import IsolationMixin
from tests.e2e.base.timeouts import TIMEOUTS, timeout_for


def _mixin() -> IsolationMixin:
    m = IsolationMixin()
    m.POLL_INTERVAL = 0.01
    m.env = {}
    m.init_run_namespace()
    return m


class TestUid:
    def test_uids_are_unique_across_calls(self):
        m = _mixin()
        ids = {m.uid("ALERT") for _ in range(50)}
        assert len(ids) == 50

    def test_uid_carries_prefix_and_run_id(self):
        m = _mixin()
        u = m.uid("TC34-VALID")
        assert u.startswith("TC34-VALID-")
        assert m.run_id in u

    def test_run_ids_differ_between_runs(self):
        a, b = _mixin(), _mixin()
        assert a.run_id != b.run_id
        # Same prefix, different runs → different ids even in the same second
        assert a.uid("X") != b.uid("X")


class TestTimeouts:
    def test_table_covers_documented_kinds(self):
        for kind in (
            "api_local",
            "healthcheck",
            "case_creation",
            "workflow",
            "cortex_analyzer",
            "misp_query",
            "misp_restart",
            "cleanup",
        ):
            assert TIMEOUTS[kind] > 0, kind

    def test_env_override_wins(self):
        m = _mixin()
        m.env = {"E2E_TIMEOUT_WORKFLOW": "42"}
        assert m.timeout("workflow") == 42

    def test_unknown_kind_raises_keyerror(self):
        with pytest.raises(KeyError, match="nope"):
            timeout_for("nope")


class TestWaitUntil:
    def test_returns_truthy_value_immediately(self):
        m = _mixin()
        assert m.wait_until(lambda: "ready", timeout=1) == "ready"

    def test_eventual_condition_succeeds(self):
        m = _mixin()
        states = itertools.chain([False, False, "ok"], itertools.repeat("ok"))
        assert m.wait_until(lambda: next(states), timeout=5) == "ok"

    def test_timeout_raises_with_last_state(self):
        m = _mixin()
        # A falsy-but-informative return (e.g. a progress counter) is what
        # "last state" diagnostics capture — truthy values return early.
        with pytest.raises(TimeoutError, match="Last state: 0"):
            m.wait_until(lambda: 0, timeout=0.05, description="progress")

    def test_timeout_kind_reads_central_table(self):
        m = _mixin()
        m.env = {"E2E_TIMEOUT_API_LOCAL": "0"}  # zero → immediate deadline
        with pytest.raises(TimeoutError):
            m.wait_until(lambda: False, timeout_kind="api_local")

    def test_finishes_early_when_condition_met(self):
        m = _mixin()
        t0 = time.monotonic()
        m.wait_until(lambda: True, timeout=30)
        assert time.monotonic() - t0 < 5
