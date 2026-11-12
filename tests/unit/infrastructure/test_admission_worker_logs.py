#!/usr/bin/env python3
"""Log/arg contract tests for AdmissionWorker — kills string and
default-argument mutations that semantic tests leave alive."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock

import pytest

from soar_lab.application.use_cases.alert_admission import (
    STATUS_DEAD,
    STATUS_FORWARDED,
)
from soar_lab.infrastructure.messaging.admission_worker import AdmissionWorker


def _worker(**kw):
    q = AsyncMock()
    s = AsyncMock()
    fwd = kw.pop("forward", AsyncMock(return_value={"ok": True}))
    return (
        AdmissionWorker(
            q, s, fwd, stale_ms=30_000, retry_cap_s=1.0, retry_base_s=0.001, **kw
        ),
        q,
        s,
        fwd,
    )


def _msgs(caplog):
    return [r.getMessage() for r in caplog.records]


class TestCtorGuardExact:
    def test_boundary_1000x(self):
        # cap*1000 == stale_ms must still raise (>= semantics)
        q, s = AsyncMock(), AsyncMock()
        with pytest.raises(ValueError):
            AdmissionWorker(q, s, AsyncMock(), stale_ms=30_000, retry_cap_s=30.0)
        # just under the bound is allowed
        AdmissionWorker(q, s, AsyncMock(), stale_ms=30_000, retry_cap_s=29.97)

    def test_message_text(self):
        q, s = AsyncMock(), AsyncMock()
        with pytest.raises(
            ValueError, match=r"retry_cap_s \(30\.0s\) must stay < stale_ms \(30000ms\)"
        ):
            AdmissionWorker(q, s, AsyncMock(), stale_ms=30_000, retry_cap_s=30.0)


class TestExactLogContracts:
    async def test_run_once_exception_message(self, caplog):
        w, q, *_ = _worker()
        q.read.return_value = [("1-0", {"admission_id": "a1"})]

        async def boom(eid, ev):
            raise RuntimeError("x")

        w._process = boom
        with caplog.at_level(logging.ERROR):
            await w.run_once()
        assert _msgs(caplog) == [
            "Entry 1-0 (admission a1) failed unhandled — left pending for recover"
        ]

    async def test_run_once_exception_unknown_id(self, caplog):
        w, q, *_ = _worker()
        q.read.return_value = [("1-0", {})]
        w._process = AsyncMock(side_effect=RuntimeError("x"))
        with caplog.at_level(logging.ERROR):
            await w.run_once()
        assert "(admission ?)" in _msgs(caplog)[0]

    async def test_recover_exception_message(self, caplog):
        w, q, *_ = _worker()
        q.claim_stale.return_value = [("2-0", {"admission_id": "a2"})]
        w._process = AsyncMock(side_effect=RuntimeError("x"))
        with caplog.at_level(logging.ERROR):
            await w.recover()
        assert "Recovered entry 2-0 (admission a2) failed unhandled" in _msgs(caplog)

    async def test_defer_message(self, caplog):
        w, q, s, *_ = _worker()
        s.get.side_effect = RuntimeError("down")
        with caplog.at_level(logging.WARNING):
            await w._terminal_check("1-0", "adm-9")
        assert _msgs(caplog) == [
            "Admission adm-9 unreadable — deferring (no forward)"
        ]

    async def test_dedup_message(self, caplog):
        w, q, s, *_ = _worker()
        s.get.return_value = {"status": STATUS_DEAD}
        with caplog.at_level(logging.INFO):
            await w._terminal_check("1-0", "adm-9")
        assert _msgs(caplog) == [
            f"Admission adm-9 already {STATUS_DEAD} — skipping re-forward (dedup)"
        ]

    async def test_transition_message(self, caplog):
        w, q, s, *_ = _worker()
        s.get.return_value = {"status": STATUS_DEAD}
        with caplog.at_level(logging.WARNING):
            await w._update("a1", {"status": STATUS_FORWARDED})
        assert _msgs(caplog) == [
            f"Illegal admission transition {STATUS_DEAD} -> {STATUS_FORWARDED} for a1 (audit)"
        ]

    async def test_forward_failure_logs_redacted(self, caplog):
        w, q, s, fwd = _worker()
        fwd.side_effect = RuntimeError("Bearer abcdefghijklmnop down")
        with caplog.at_level(logging.WARNING):
            await w._forward_timed({}, "adm-5")
        assert _msgs(caplog) == [
            "Forward failed for adm-5: Bearer [redacted] down"
        ]

    async def test_dead_letter_message(self, caplog):
        w, q, s, *_ = _worker()
        s.get.return_value = None
        with caplog.at_level(logging.ERROR):
            await w._handle_failure(
                "1-0", {}, "a9", 0, {"error_code": "X", "retryable": False}
            )
        assert _msgs(caplog) == [
            "Admission a9 dead-lettered after 1 attempt(s): X"
        ]

    async def test_reconciler_failure_message(self, caplog):
        w, *_ = _worker(reconciler=AsyncMock(side_effect=RuntimeError("x")))
        with caplog.at_level(logging.ERROR):
            await w._reconcile()
        assert _msgs(caplog) == ["Admission reconciler failed"]

    async def test_fence_rotation_message(self, caplog):
        lease = AsyncMock()
        lease.held.return_value = True
        w, *_ = _worker(lease=lease)
        w._fence_token = "t1"
        lease.fence_token = "t2"
        with caplog.at_level(logging.WARNING):
            await w._leader()
        msg = _msgs(caplog)[0]
        assert msg.startswith("Worker lease fence token rotated (t1 -> t2)")
        assert "skipping this duty cycle" in msg

    async def test_recover_count_message(self, caplog):
        w, q, *_ = _worker()
        q.claim_stale.return_value = [("1", {}), ("2", {})]
        w._process = AsyncMock()
        with caplog.at_level(logging.INFO):
            await w.recover()
        assert _msgs(caplog) == ["Recovering 2 stale admission(s)"]


class TestNoneResultAndMissingKey:
    async def test_reconciler_none_no_error(self, caplog):
        w, *_ = _worker(reconciler=AsyncMock(return_value=None))
        with caplog.at_level(logging.ERROR):
            await w._reconcile()
        assert _msgs(caplog) == []
        assert w.stats.orphans_repaired_total == 0

    async def test_reconciler_missing_key_zero(self, caplog):
        w, *_ = _worker(reconciler=AsyncMock(return_value={"other": 5}))
        with caplog.at_level(logging.ERROR):
            await w._reconcile()
        assert _msgs(caplog) == []
        assert w.stats.orphans_repaired_total == 0


class TestProcessAlertFields:
    async def test_alert_fields_forwarded(self):
        w, q, s, fwd = _worker()
        s.get.return_value = {"status": "queued"}
        await w._process(
            "1-0", {"admission_id": "a1", "alert": {"sev": 3}, "attempts": 0}
        )
        sent = fwd.call_args.args[0]
        assert sent["sev"] == 3
        assert sent["delivery_id"] == "a1:1"

    async def test_forward_timed_admission_id(self, caplog):
        w, q, s, fwd = _worker()
        fwd.side_effect = RuntimeError("x")
        with caplog.at_level(logging.WARNING):
            await w._forward_timed({}, "adm-77")
        assert "for adm-77" in _msgs(caplog)[0]

    async def test_forward_seconds_accumulates(self):
        w, q, s, fwd = _worker()
        await w._forward_timed({}, "a")
        t1 = w.stats.forward_seconds_total
        await w._forward_timed({}, "a")
        assert w.stats.forward_seconds_total >= t1
        assert w.stats.inflight == 0

    async def test_retried_total_increments(self):
        w, q, s, *_ = _worker()
        s.get.return_value = None
        for _ in range(2):
            await w._handle_failure(
                "1-0", {}, "a", 0, {"error_code": "E", "retryable": True}
            )
        assert w.stats.retried_total == 2

    async def test_error_code_max_len_80(self):
        w, q, s, *_ = _worker()
        s.get.return_value = None
        long_err = "error " + "z" * 200  # non-hex so redaction doesn't collapse it
        await w._handle_failure(
            "1-0", {}, "a", 0, {"error": long_err, "retryable": True}
        )
        assert len(w.stats.last_error) == 81  # 80 chars + ellipsis
