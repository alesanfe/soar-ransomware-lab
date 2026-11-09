#!/usr/bin/env python3
"""Regression test for tests/e2e/base setup ordering.

BUG-035: subclasses override ``_log`` using ``self.t0``, but ``t0`` was
only assigned *after* ``super().setup_method()`` — every ``_log`` call
inside the base setup (health checks, observability asserts) raised
``AttributeError`` which ``assert_grafana_healthy`` swallowed and
recorded as a failed ``grafana_healthy`` assertion (silent false
negative: pytest passed while the result JSON showed 10/11).
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tests" / "e2e"))

from base import E2EBaseTest


class _TCWithElapsedLog(E2EBaseTest):
    """Mimics TC-XX subclasses whose `_log` reads `self.t0`."""

    tc_id = "TC-TEST"
    logged: list[str] = []

    def _log(self, msg: str) -> None:
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self.logged.append(f"[{elapsed:.1f}s] {msg}")


def _method(name="test_x"):
    def f():
        pass

    f.__name__ = name
    return f


class TestSetupMethodT0:
    def test_setup_initializes_t0_before_any_log(self, monkeypatch):
        obj = _TCWithElapsedLog.__new__(_TCWithElapsedLog)
        obj.logged = []

        # Stub every heavyweight step; keep the real ordering.
        monkeypatch.setattr(
            obj, "load_env", lambda: {"THEHIVE_API_KEY": "x", "E2E_VERIFY_OBSERVABILITY": "true"}
        )
        for name in (
            "resolve_paths",
            "load_webhook_info",
            "create_run_context",
            "create_shuffle_client",
            "create_thehive_client",
            "create_cortex_client",
            "create_misp_client",
            "create_search_clients",
            "verify_core_services",
            "verify_workflow_ready",
            "verify_observability_stack",
            "assert_loki_ready",
            "assert_promtail_collecting",
            "setup_test_data",
        ):
            monkeypatch.setattr(obj, name, lambda *a, **k: None)
        monkeypatch.setattr(
            obj,
            "load_webhook_info",
            lambda: {"webhook_url": "http://x", "workflow_id": "w"},
        )
        # grafana assert exercises a `_log` call via record/log paths
        monkeypatch.setattr(obj, "assert_grafana_healthy", lambda: obj._log("grafana check"))
        obj.thehive = type("T", (), {"search_cases": lambda self: []})()
        obj.es = type("E", (), {"count": lambda self: 0})()

        obj.setup_method(_method())

        assert obj.logged == ["[0.0s] grafana check"] or obj.logged
        assert hasattr(obj, "t0")
