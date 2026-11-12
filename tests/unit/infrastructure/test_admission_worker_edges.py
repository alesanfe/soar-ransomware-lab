#!/usr/bin/env python3
"""AdmissionWorker edge coverage: recover failures, leader lease, reconcile."""

import asyncio

import pytest

from soar_lab.infrastructure.messaging.admission_worker import AdmissionWorker, WorkerStats


class FakeQueue:
    def __init__(self):
        self.entries = []
        self.stale = []
        self.acked = []
        self.redrive_calls = []

    async def read(self, group, consumer, count, block_ms):
        if not self.entries:
            await asyncio.sleep(0.001)
        batch, self.entries = self.entries[:count], self.entries[count:]
        return batch

    async def ensure_group(self, group):
        return None

    async def claim_stale(self, group, consumer, min_idle_ms):
        return self.stale

    async def ack(self, group, entry_id):
        self.acked.append(entry_id)

    async def dead_letter(self, entry, reason):
        pass

    async def dlq_auto_redrive(self, max_redrives, min_age_s):
        self.redrive_calls.append((max_redrives, min_age_s))


class FakeStore:
    def __init__(self):
        self.records = {}

    async def update(self, aid, fields):
        self.records.setdefault(aid, {}).update(fields)

    async def get(self, aid):
        return self.records.get(aid)


def _worker(queue, store, fwd=None, **kw):
    fwd = fwd or (lambda alert: {"ok": True, "exec_id": "e", "status_code": 200})

    async def _f(alert):
        return fwd(alert)

    defaults = dict(poll_ms=1, recover_interval_s=0.0, concurrency=2)
    defaults.update(kw)
    return AdmissionWorker(queue=queue, store=store, forward=_f, **defaults)


class TestRecoverEdges:
    async def test_empty_stale_returns_zero(self):
        assert await _worker(FakeQueue(), FakeStore()).recover() == 0

    async def test_stale_exception_logged_not_raised(self):
        q = FakeQueue()
        q.stale = [("s1", {"admission_id": "a1", "alert": {}})]
        store = FakeStore()

        async def boom(alert):
            raise RuntimeError("forward exploded")

        w = _worker(q, store, fwd=boom)
        # _process catches forward errors internally only via _handle_failure;
        # a raw raise inside gather lands in results — recover must not raise.
        assert await w.recover() == 1


class TestLeader:
    async def test_no_lease_is_leader(self):
        assert await _worker(FakeQueue(), FakeStore())._leader() is True

    async def test_lease_held_exception(self):
        class L:
            async def held(self):
                raise RuntimeError("redis gone")

        assert await _worker(FakeQueue(), FakeStore(), lease=L())._leader() is False

    async def test_lease_not_held(self):
        class L:
            async def held(self):
                return False

        assert await _worker(FakeQueue(), FakeStore(), lease=L())._leader() is False

    async def test_fence_token_recorded(self):
        class L:
            fence_token = 42

            async def held(self):
                return True

        w = _worker(FakeQueue(), FakeStore(), lease=L())
        assert await w._leader() is True
        assert w._fence_token == 42


class TestReconcile:
    async def test_none_reconciler_noop(self):
        await _worker(FakeQueue(), FakeStore())._reconcile()  # no raise

    async def test_reconciler_result_updates_stats(self):
        async def rec():
            return {"enqueue_failed_repaired": 3}

        w = _worker(FakeQueue(), FakeStore(), reconciler=rec)
        await w._reconcile()
        assert w.stats.orphans_repaired_total == 3

    async def test_reconciler_exception_logged(self):
        async def boom():
            raise RuntimeError("x")

        w = _worker(FakeQueue(), FakeStore(), reconciler=boom)
        await w._reconcile()  # must not raise
        assert w.stats.orphans_repaired_total == 0


class TestRunLoop:
    async def test_leader_runs_recover_reconcile_redrive_and_releases_lease(self):
        q = FakeQueue()
        released = []

        class Lease:
            fence_token = 1

            async def held(self):
                return True

            async def release(self):
                released.append(True)

        reconciled = []

        async def rec():
            reconciled.append(True)
            return {"enqueue_failed_repaired": 1}

        w = _worker(q, FakeStore(), lease=Lease(), reconciler=rec, dlq_auto_redrive=True)
        stop = asyncio.Event()

        async def run_and_stop():
            task = asyncio.create_task(w.run(stop))
            await asyncio.sleep(0.15)
            stop.set()
            await asyncio.wait_for(task, timeout=5)

        await run_and_stop()
        assert reconciled
        assert q.redrive_calls  # auto-redrive ran under the lease
        assert released  # lease released on shutdown
        assert w.stats.orphans_repaired_total >= 1

    async def test_non_leader_skips_singleton_duties(self):
        q = FakeQueue()

        class Lease:
            async def held(self):
                return False

            async def release(self):
                pass

        rec_calls = []

        async def rec():
            rec_calls.append(True)

        w = _worker(q, FakeStore(), lease=Lease(), reconciler=rec, dlq_auto_redrive=True)
        stop = asyncio.Event()
        task = asyncio.create_task(w.run(stop))
        await asyncio.sleep(0.15)
        stop.set()
        await asyncio.wait_for(task, timeout=5)
        assert not rec_calls and not q.redrive_calls


class TestTerminalCheck:
    async def test_defer_when_store_unreadable(self):
        class BadStore(FakeStore):
            async def get(self, aid):
                raise RuntimeError("redis down")

        w = _worker(FakeQueue(), BadStore())
        assert await w._terminal_check("e1", "a1") == "defer"

    async def test_skip_when_terminal(self):
        store = FakeStore()
        store.records["a1"] = {"status": "forwarded"}
        q = FakeQueue()
        w = _worker(q, store)
        assert await w._terminal_check("e1", "a1") == "skip"
        assert w.stats.dedup_total == 1
        assert q.acked == ["e1"]

    async def test_process_when_pending(self):
        store = FakeStore()
        store.records["a1"] = {"status": "pending"}
        w = _worker(FakeQueue(), store)
        assert await w._terminal_check("e1", "a1") == "process"


class TestRunOnceBatch:
    async def test_run_once_processes_nonempty_batch(self):
        q = FakeQueue()
        q.entries = [
            ("e1", {"admission_id": "a1", "alert": {"title": "t"}}),
            ("e2", {"admission_id": "a2", "alert": {"title": "t"}}),
        ]
        store = FakeStore()
        store.records = {"a1": {"status": "pending"}, "a2": {"status": "pending"}}
        w = _worker(q, store)
        assert await w.run_once() == 2
        assert set(q.acked) == {"e1", "e2"}

    async def test_run_once_empty_batch_returns_zero(self):
        assert await _worker(FakeQueue(), FakeStore()).run_once() == 0
