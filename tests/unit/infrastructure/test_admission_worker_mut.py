#!/usr/bin/env python3
"""Mutation-hardening tests for AdmissionWorker — exact error codes,
dedup/fence semantics, retry budget boundaries and DLQ policy."""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock

import pytest

from soar_lab.application.use_cases.alert_admission import (
    STATUS_DEAD,
    STATUS_FORWARDED,
    STATUS_RETRY_SCHEDULED,
)
from soar_lab.infrastructure.messaging.admission_worker import (
    AdmissionWorker,
    WorkerStats,
)


def _worker(**kw):
    q = AsyncMock()
    s = AsyncMock()
    fwd = kw.pop("forward", AsyncMock(return_value={"ok": True}))
    return (
        AdmissionWorker(
            q,
            s,
            fwd,
            stale_ms=30_000,
            retry_cap_s=1.0,
            retry_base_s=0.001,
            **kw,
        ),
        q,
        s,
        fwd,
    )


class TestCtorGuard:
    def test_cap_vs_stale_guard(self):
        q, s = AsyncMock(), AsyncMock()
        with pytest.raises(ValueError, match="must stay < stale_ms"):
            AdmissionWorker(q, s, AsyncMock(), stale_ms=30_000, retry_cap_s=30.0)


class TestRetryDelay:
    def test_delay_bounds(self):
        w, *_ = _worker()
        for _ in range(50):
            assert 0 <= w._retry_delay(1) <= 0.001
            assert 0 <= w._retry_delay(3) <= 0.004
            assert 0 <= w._retry_delay(100) <= 1.0  # capped


class TestRunOnceAndRecover:
    async def test_run_once_empty(self):
        w, q, *_ = _worker()
        q.read.return_value = []
        assert await w.run_once() == 0
        q.read.assert_awaited_once_with("soar-api", "worker-1", 10, 500)

    async def test_run_once_exception_left_pending(self, caplog):
        w, q, *_ = _worker()
        q.read.return_value = [("1-0", {})]

        async def boom(entry_id, event):
            raise RuntimeError("x")

        w._process = boom
        with caplog.at_level(logging.ERROR):
            assert await w.run_once() == 1
        assert "failed unhandled" in caplog.text
        q.ack.assert_not_awaited()

    async def test_recover_empty(self):
        w, q, *_ = _worker()
        q.claim_stale.return_value = []
        assert await w.recover() == 0
        q.claim_stale.assert_awaited_once_with("soar-api", "worker-1", 30_000)

    async def test_recover_processes_and_logs(self, caplog):
        w, q, *_ = _worker()
        q.claim_stale.return_value = [("1-0", {"admission_id": "a1", "alert": {}})]
        w._process = AsyncMock()
        with caplog.at_level(logging.INFO):
            assert await w.recover() == 1
        assert "Recovering 1 stale" in caplog.text

    async def test_recover_exception_logged(self, caplog):
        w, q, *_ = _worker()
        q.claim_stale.return_value = [("1-0", {})]

        async def boom(entry_id, event):
            raise RuntimeError("x")

        w._process = boom
        with caplog.at_level(logging.ERROR):
            assert await w.recover() == 1
        assert "Recovered entry 1-0" in caplog.text


class TestLeaderFence:
    async def test_no_lease_leader(self):
        w, *_ = _worker()
        assert await w._leader() is True

    async def test_lease_held(self):
        lease = AsyncMock()
        lease.held.return_value = True
        lease.fence_token = None
        w, *_ = _worker(lease=lease)
        assert await w._leader() is True

    async def test_lease_not_held(self):
        lease = AsyncMock()
        lease.held.return_value = False
        w, *_ = _worker(lease=lease)
        assert await w._leader() is False

    async def test_lease_error(self):
        lease = AsyncMock()
        lease.held.side_effect = RuntimeError("x")
        w, *_ = _worker(lease=lease)
        assert await w._leader() is False

    async def test_fence_rotation_skips_cycle(self, caplog):
        lease = AsyncMock()
        lease.held.return_value = True
        w, *_ = _worker(lease=lease)
        w._fence_token = "t1"
        lease.fence_token = "t2"
        with caplog.at_level(logging.WARNING):
            assert await w._leader() is False
        assert "fence token rotated" in caplog.text
        assert w._fence_token == "t2"
        # stable token again -> leader
        assert await w._leader() is True


class TestReconcile:
    async def test_none_noop(self):
        w, *_ = _worker()
        await w._reconcile()  # no error

    async def test_counts_repaired(self):
        w, *_ = _worker(reconciler=AsyncMock(return_value={"enqueue_failed_repaired": 3}))
        await w._reconcile()
        assert w.stats.orphans_repaired_total == 3

    async def test_none_result(self):
        w, *_ = _worker(reconciler=AsyncMock(return_value=None))
        await w._reconcile()
        assert w.stats.orphans_repaired_total == 0

    async def test_exception_logged(self, caplog):
        w, *_ = _worker(reconciler=AsyncMock(side_effect=RuntimeError("x")))
        with caplog.at_level(logging.ERROR):
            await w._reconcile()
        assert "reconciler failed" in caplog.text


class TestProcess:
    async def test_success_path_updates_and_acks(self):
        w, q, s, fwd = _worker(
            forward=AsyncMock(
                return_value={"ok": True, "exec_id": "e9", "status_code": 200}
            )
        )
        s.get.return_value = {"status": "queued", "state_version": 1}
        await w._process("1-0", {"admission_id": "a1", "alert": {"x": 1}, "attempts": 1})
        sent = fwd.call_args.args[0]
        assert sent["delivery_id"] == "a1:2"
        assert sent["attempt"] == 2
        upd = s.update.call_args.args[1]
        assert upd["status"] == STATUS_FORWARDED
        assert upd["attempts"] == 2
        assert upd["downstream_execution_id"] == "e9"
        q.ack.assert_awaited_once_with("soar-api", "1-0")
        assert w.stats.forwarded_total == 1

    async def test_defaults_unknown_and_attempts(self):
        w, q, s, fwd = _worker()
        s.get.return_value = None
        await w._process("1-0", {})
        sent = fwd.call_args.args[0]
        assert sent["delivery_id"] == "unknown:1"
        assert sent["attempt"] == 1


class TestTerminalCheck:
    async def test_store_error_defers(self, caplog):
        w, q, s, *_ = _worker()
        s.get.side_effect = RuntimeError("redis down")
        with caplog.at_level(logging.WARNING):
            assert await w._terminal_check("1-0", "a1") == "defer"
        assert "unreadable" in caplog.text
        q.ack.assert_not_awaited()

    async def test_terminal_skips_and_counts(self):
        w, q, s, *_ = _worker()
        s.get.return_value = {"status": STATUS_DEAD}
        assert await w._terminal_check("1-0", "a1") == "skip"
        assert w.stats.dedup_total == 1
        q.ack.assert_awaited_once_with("soar-api", "1-0")

    async def test_non_terminal_processes(self):
        w, q, s, *_ = _worker()
        s.get.return_value = {"status": "queued"}
        assert await w._terminal_check("1-0", "a1") == "process"
        s.get.return_value = None
        assert await w._terminal_check("1-0", "a1") == "process"


class TestUpdate:
    async def test_illegal_transition_marked(self, caplog):
        w, q, s, *_ = _worker()
        s.get.return_value = {"status": STATUS_DEAD, "state_version": 2}
        with caplog.at_level(logging.WARNING):
            await w._update("a1", {"status": STATUS_FORWARDED})
        assert "Illegal admission transition" in caplog.text
        upd = s.update.call_args.args[1]
        assert upd["transition_violation"] == f"{STATUS_DEAD}->{STATUS_FORWARDED}"
        assert upd["state_version"] == 3
        assert upd["changed_at"].endswith("Z")

    async def test_store_error_uses_none(self):
        w, q, s, *_ = _worker()
        s.get.side_effect = RuntimeError("x")
        await w._update("a1", {"status": STATUS_FORWARDED})
        upd = s.update.call_args.args[1]
        assert upd["state_version"] == 2


class TestBackoff:
    async def test_zero_attempts_no_sleep(self):
        w, *_ = _worker()
        with pytest.MonkeyPatch.context() as mp:
            slept = []

            async def s(d):
                slept.append(d)

            mp.setattr(asyncio, "sleep", s)
            await w._retry_backoff(0)
            assert slept == []

    async def test_positive_sleeps_capped(self):
        w, *_ = _worker()
        with pytest.MonkeyPatch.context() as mp:
            slept = []

            async def s(d):
                slept.append(d)

            mp.setattr(asyncio, "sleep", s)
            await w._retry_backoff(1)
            assert len(slept) == 1
            assert slept[0] <= 30_000 / 2000


class TestForwardTimed:
    async def test_exception_contract(self):
        w, q, s, fwd = _worker()
        fwd.side_effect = RuntimeError("conn refused")
        out = await w._forward_timed({}, "a1")
        assert out == {
            "ok": False,
            "error_code": "FORWARD_EXCEPTION",
            "retryable": True,
        }
        assert w.stats.inflight == 0
        assert w.stats.processed_total == 1
        assert w.stats.forward_seconds_total >= 0


class TestHandleFailure:
    async def test_error_code_priority(self):
        w, q, s, *_ = _worker()
        s.get.return_value = None
        await w._handle_failure(
            "1-0", {}, "a1", 0, {"error_code": "HTTP_502", "retryable": True}
        )
        assert w.stats.last_error == "HTTP_502"
        assert w.stats.errors == {"HTTP_502": 1}

    async def test_error_fallback_and_default(self):
        w, q, s, *_ = _worker()
        s.get.return_value = None
        await w._handle_failure(
            "1-0", {}, "a1", 0, {"error": "boom", "retryable": True}
        )
        assert w.stats.last_error == "boom"
        await w._handle_failure("1-0", {}, "a1", 0, {"retryable": True})
        assert w.stats.last_error == "FORWARD_FAILED"

    async def test_non_retryable_dead_letters(self):
        w, q, s, *_ = _worker()
        s.get.return_value = None
        ev = {"admission_id": "a1"}
        await w._handle_failure(
            "1-0", ev, "a1", 0, {"error_code": "HTTP_400", "retryable": False}
        )
        assert w.stats.dead_total == 1
        q.dead_letter.assert_awaited_once_with(ev, reason="HTTP_400")
        upd = s.update.call_args.args[1]
        assert upd["status"] == STATUS_DEAD and upd["attempts"] == 1
        q.ack.assert_awaited_once()

    async def test_max_attempts_dead_letters(self):
        w, q, s, *_ = _worker(max_attempts=5)
        s.get.return_value = None
        await w._handle_failure(
            "1-0", {}, "a1", 4, {"error_code": "T", "retryable": True}
        )
        q.dead_letter.assert_awaited_once()

    async def test_retry_reenqueues(self):
        w, q, s, *_ = _worker()
        s.get.return_value = None
        ev = {"admission_id": "a1"}
        await w._handle_failure(
            "1-0", ev, "a1", 0, {"error_code": "HTTP_502", "retryable": True}
        )
        assert w.stats.retried_total == 1
        assert ev["attempts"] == 1
        upd = s.update.call_args.args[1]
        assert upd["status"] == STATUS_RETRY_SCHEDULED
        q.enqueue.assert_awaited_once_with(ev)
        q.ack.assert_awaited_once()


class TestRun:
    async def test_stop_set_releases_lease(self):
        lease = AsyncMock()
        w, q, *_ = _worker(lease=lease)
        q.claim_stale.return_value = []
        stop = asyncio.Event()
        stop.set()
        await w.run(stop)
        q.ensure_group.assert_awaited_once_with("soar-api")
        lease.release.assert_awaited_once()
