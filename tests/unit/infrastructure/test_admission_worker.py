"""PERF-001: admission worker — durable forward semantics.

The worker consumes queued admissions and forwards each alert to the
slow downstream (Shuffle webhook). Contract:

- success      -> store.mark_forwarded + queue.ack
- failure      -> retry counter, entry re-queued, original acked
- max attempts -> dead-letter + status "dead"
- restart      -> stale pending entries are claimed (XAUTOCLAIM) and processed
"""

from __future__ import annotations

from soar_lab.infrastructure.messaging.admission_worker import AdmissionWorker


class FakeQueue:
    def __init__(self):
        self.entries: list[tuple[str, dict]] = []
        self.acked: list[str] = []
        self.dlq: list[dict] = []
        self.claimed = False
        self._counter = 0

    async def enqueue(self, event: dict) -> str:
        self._counter += 1
        eid = f"e-{self._counter}"
        self.entries.append((eid, event))
        return eid

    async def read(self, group, consumer, count, block_ms):
        # The real XREAD blocks up to block_ms — emulate the yield so the
        # worker loop does not spin without ever suspending (test deadlock).
        if not self.entries:
            import asyncio

            await asyncio.sleep(min(block_ms, 5) / 1000)
        batch, self.entries = self.entries[:count], self.entries[count:]
        return batch

    async def ensure_group(self, group):
        return None

    async def claim_stale(self, group, consumer, min_idle_ms):
        self.claimed = True
        return [("stale-1", {"admission_id": "adm-stale", "alert": {"alert_id": "old"}})]

    async def ack(self, group, entry_id):
        self.acked.append(entry_id)

    async def dead_letter(self, entry, reason):
        self.dlq.append({"entry": entry, "reason": reason})


class FakeStore:
    def __init__(self):
        self.records: dict[str, dict] = {}
        self.by_key: dict[str, str] = {}

    async def update(self, admission_id, fields):
        self.records.setdefault(admission_id, {}).update(fields)

    async def get(self, admission_id):
        return self.records.get(admission_id)

    async def try_bind_key(self, key, aid):
        if key in self.by_key:
            return self.by_key[key]
        self.by_key[key] = aid
        return None

    async def unbind_key(self, key, aid):
        if self.by_key.get(key) == aid:
            del self.by_key[key]


def _admission(n: int, attempts: int = 0) -> dict:
    return {
        "admission_id": f"adm-{n}",
        "attempts": attempts,
        "alert": {"alert_id": f"alr-{n}", "hostname": f"victim_{n}"},
    }


def _fwd(result: dict):
    async def forward(alert):
        return dict(result)

    return forward


class TestForward:
    async def test_success_marks_forwarded_and_acks(self):
        queue, store = FakeQueue(), FakeStore()
        queue.entries = [("e-1", _admission(1))]
        worker = AdmissionWorker(queue, store, forward=_fwd({"ok": True, "exec_id": "wx-1"}))
        await worker.run_once()
        assert queue.acked == ["e-1"]
        assert store.records["adm-1"]["status"] == "forwarded"
        assert store.records["adm-1"]["downstream_execution_id"] == "wx-1"

    async def test_failure_increments_attempts_and_requeues(self):
        queue, store = FakeQueue(), FakeStore()
        queue.entries = [("e-1", _admission(1))]
        worker = AdmissionWorker(
            queue, store, forward=_fwd({"ok": False, "error": "boom"}), max_attempts=5
        )
        await worker.run_once()
        assert queue.acked == ["e-1"], "original entry must be acked once re-enqueued"
        assert len(queue.entries) == 1, "event must be re-enqueued for retry"
        assert store.records["adm-1"]["attempts"] == 1
        assert store.records["adm-1"]["status"] == "retry_scheduled"

    async def test_max_attempts_goes_to_dlq(self):
        queue, store = FakeQueue(), FakeStore()
        queue.entries = [("e-1", _admission(1, attempts=4))]
        worker = AdmissionWorker(
            queue,
            store,
            forward=_fwd({"ok": False, "error": "boom"}),
            max_attempts=5,
            retry_base_s=0.001,
            retry_cap_s=0.002,
        )
        await worker.run_once()
        assert queue.dlq, "exhausted entry must land in DLQ"
        assert store.records["adm-1"]["status"] == "dead"
        assert not queue.entries, "dead entry must not be re-queued"

    async def test_batch_processes_multiple_entries(self):
        queue, store = FakeQueue(), FakeStore()
        queue.entries = [(f"e-{n}", _admission(n)) for n in range(4)]
        worker = AdmissionWorker(queue, store, forward=_fwd({"ok": True}))
        processed = await worker.run_once()
        assert processed == 4
        assert len(queue.acked) == 4


class TestRecovery:
    async def test_startup_claims_stale_pending_entries(self):
        queue, store = FakeQueue(), FakeStore()
        worker = AdmissionWorker(queue, store, forward=_fwd({"ok": True}))
        recovered = await worker.recover()
        assert queue.claimed is True
        assert recovered == 1
        assert store.records["adm-stale"]["status"] == "forwarded"


class TestConcurrencyBound:
    async def test_in_flight_bounded_by_concurrency(self):
        import asyncio

        queue, store = FakeQueue(), FakeStore()
        queue.entries = [(f"e-{n}", _admission(n)) for n in range(10)]
        in_flight = {"now": 0, "max": 0}

        async def slow_forward(alert):
            in_flight["now"] += 1
            in_flight["max"] = max(in_flight["max"], in_flight["now"])
            await asyncio.sleep(0.01)
            in_flight["now"] -= 1
            return {"ok": True}

        worker = AdmissionWorker(queue, store, forward=slow_forward, concurrency=3)
        await worker.run_once()
        assert in_flight["max"] <= 3
        assert len(queue.acked) == 10


class TestRunLoop:
    """run(): ensure_group + recover + iterate-until-stop + resilience."""

    async def test_run_ensures_group_recovers_and_stops(self):
        import asyncio

        q = FakeQueue()
        worker = AdmissionWorker(q, FakeStore(), _fwd({"ok": True}), recover_interval_s=9999)
        stop = asyncio.Event()
        stop.set()  # loop exits immediately after boot sequence
        await worker.run(stop)
        assert q.claimed is True

    async def test_run_processes_until_stop_set(self):
        import asyncio

        q = FakeQueue()
        q.entries.append(("e-1", _admission(1)))
        worker = AdmissionWorker(q, FakeStore(), _fwd({"ok": True}), poll_ms=1)
        stop = asyncio.Event()

        async def stopper():
            while "e-1" not in q.acked:
                await asyncio.sleep(0.005)
            stop.set()

        await asyncio.gather(worker.run(stop), stopper())
        assert "e-1" in q.acked

    async def test_run_survives_iteration_exception(self):
        import asyncio

        class FlakyQueue(FakeQueue):
            def __init__(self):
                super().__init__()
                self.calls = 0

            async def read(self, group, consumer, count, block_ms):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("redis blip")
                # emulate the blocking XREAD yield — an instant empty return
                # would spin the worker loop and starve the stopper task
                await asyncio.sleep(min(block_ms, 5) / 1000)
                return []

        q = FlakyQueue()
        worker = AdmissionWorker(q, FakeStore(), _fwd({"ok": True}), poll_ms=1)
        stop = asyncio.Event()

        async def stopper():
            while q.calls < 2:
                await asyncio.sleep(0.005)
            stop.set()

        await asyncio.gather(worker.run(stop), stopper())
        assert q.calls >= 2  # loop continued after the exception


class TestForwardException:
    async def test_forward_raising_counts_as_failure(self):
        async def boom(alert):
            raise ConnectionError("dial refused")

        q = FakeQueue()
        q.entries.append(("e-1", _admission(1)))
        store = FakeStore()
        worker = AdmissionWorker(q, store, boom, max_attempts=5)
        assert await worker.run_once() == 1
        rec = store.records["adm-1"]
        assert rec["status"] == "retry_scheduled"
        assert rec["attempts"] == 1
        # B6/ERROR-001: last_error stores the structured code, never
        # raw exception text (capability URLs can't leak into state).
        assert rec["last_error"] == "FORWARD_EXCEPTION"
        assert worker.stats.retried_total == 1

    async def test_retry_delay_zero_skips_sleep(self, monkeypatch):
        import asyncio

        sleeps = []
        real_sleep = asyncio.sleep

        async def spy(d):
            sleeps.append(d)
            await real_sleep(0)

        monkeypatch.setattr(asyncio, "sleep", spy)
        q = FakeQueue()
        q.entries.append(("e-1", _admission(1, attempts=1)))
        worker = AdmissionWorker(q, FakeStore(), _fwd({"ok": True}))
        worker._rng.uniform = lambda a, b: 0.0  # force delay==0
        assert await worker.run_once() == 1
        assert all(d == 0 or d >= 0.005 for d in sleeps)  # no backoff sleep
        assert q.acked == ["e-1"]

    async def test_error_stats_bucketized(self):
        q = FakeQueue()
        q.entries.append(("e-1", _admission(1)))
        q.entries.append(("e-2", _admission(2)))
        worker = AdmissionWorker(
            q, FakeStore(), _fwd({"ok": False, "error": "HTTP 503"}), max_attempts=3
        )
        await worker.run_once()
        assert worker.stats.errors["HTTP 503"] == 2


class TestDedupReclaimedEntry:
    """IDEMP-004: a reclaimed entry whose forward already committed must
    not be re-POSTed (ack was lost, not the forward)."""

    async def test_already_forwarded_entry_is_acked_without_forward(self):
        q = FakeQueue()
        q.entries.append(("e-1", _admission(1)))
        store = FakeStore()
        store.records["adm-1"] = {
            "status": "forwarded",
            "downstream_execution_id": "wx-prev",
        }
        calls = []

        async def spy_forward(alert):
            calls.append(alert)
            return {"ok": True, "exec_id": "wx-DUP"}

        worker = AdmissionWorker(q, store, spy_forward)
        assert await worker.run_once() == 1
        assert calls == [], "forward must NOT be called for a committed admission"
        assert q.acked == ["e-1"]
        assert store.records["adm-1"]["downstream_execution_id"] == "wx-prev"
        assert worker.stats.dedup_total == 1

    async def test_already_dead_entry_is_acked_without_forward(self):
        """DLQ'd admissions are terminal — a reclaimed copy must not
        resurrect a downstream execution either."""
        q = FakeQueue()
        q.entries.append(("e-1", _admission(1)))
        store = FakeStore()
        store.records["adm-1"] = {"status": "dead"}
        calls = []

        async def spy_forward(alert):
            calls.append(alert)
            return {"ok": True}

        worker = AdmissionWorker(q, store, spy_forward)
        assert await worker.run_once() == 1
        assert calls == []
        assert q.acked == ["e-1"]
        assert worker.stats.dedup_total == 1

    async def test_store_get_failure_defers_entry(self):
        """WORKER-003: an unreadable store must NOT trigger a forward —
        the entry stays pending for recover() instead of risking a
        duplicate downstream execution (fail-safe, not fail-open)."""

        class FlakyStore(FakeStore):
            async def get(self, admission_id):
                raise RuntimeError("store down")

        q = FakeQueue()
        q.entries.append(("e-1", _admission(1)))
        worker = AdmissionWorker(q, FlakyStore(), _fwd({"ok": True, "exec_id": "wx-9"}))
        assert await worker.run_once() == 1
        assert q.acked == [], "deferred entry must stay pending"
        assert worker.stats.forwarded_total == 0

    async def test_queued_record_still_forwards(self):
        """A reclaimed entry whose record is still queued (forward never
        committed) must forward normally."""
        q = FakeQueue()
        q.entries.append(("e-1", _admission(1)))
        store = FakeStore()
        store.records["adm-1"] = {"status": "queued", "attempts": 0}
        worker = AdmissionWorker(q, store, _fwd({"ok": True, "exec_id": "wx-7"}))
        assert await worker.run_once() == 1
        assert store.records["adm-1"]["downstream_execution_id"] == "wx-7"
        assert worker.stats.dedup_total == 0
