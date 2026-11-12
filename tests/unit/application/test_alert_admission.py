"""PERF-001: async alert admission — use case contract.

POST /api/v1/alerts must validate, stamp an alert_id, record a minimal
admission and enqueue the event — returning 202 immediately instead of
blocking on the synchronous Shuffle workflow path (~500 s timeouts under
~10 concurrent submissions). These tests pin the use-case behaviour
against fake queue/store ports (no Redis, no HTTP).
"""

from __future__ import annotations

import pytest

from soar_lab.application.use_cases.alert_admission import (
    AdmissionValidationError,
    AlertAdmissionUseCase,
)


class FakeEventQueue:
    def __init__(self):
        self.events: list[dict] = []
        self.acked: list[str] = []
        self.dlq: list[tuple[dict, str]] = []

    async def enqueue(self, event: dict) -> str:
        self.events.append(event)
        return f"entry-{len(self.events)}"

    async def read(self, group, consumer, count, block_ms):
        return []

    async def ack(self, group, entry_id) -> None:
        self.acked.append(entry_id)

    async def dead_letter(self, entry: dict, reason: str) -> None:
        self.dlq.append((entry, reason))

    async def ensure_group(self, group: str) -> None:
        pass

    async def depth(self) -> int:
        return len(self.events)


class FakeAdmissionStore:
    def __init__(self):
        self.records: dict[str, dict] = {}
        self.by_key: dict[str, str] = {}

    async def create(self, record: dict) -> None:
        self.records[record["admission_id"]] = dict(record)

    async def update(self, admission_id: str, fields: dict) -> None:
        self.records[admission_id].update(fields)

    async def get(self, admission_id: str):
        return self.records.get(admission_id)

    async def find_by_key(self, idempotency_key: str):
        return self.by_key.get(idempotency_key)

    async def bind_key(self, idempotency_key: str, admission_id: str) -> None:
        self.by_key[idempotency_key] = admission_id

    async def try_bind_key(self, idempotency_key: str, admission_id: str):
        if idempotency_key in self.by_key:
            return self.by_key[idempotency_key]
        self.by_key[idempotency_key] = admission_id
        return None

    async def unbind_key(self, idempotency_key: str, admission_id: str) -> None:
        if self.by_key.get(idempotency_key) == admission_id:
            del self.by_key[idempotency_key]


def _uc(max_bytes: int = 262_144) -> AlertAdmissionUseCase:
    return AlertAdmissionUseCase(
        queue=FakeEventQueue(), store=FakeAdmissionStore(), max_payload_bytes=max_bytes
    )


class TestAdmit:
    async def test_returns_admission_with_status_url(self):
        uc = _uc()
        result = await uc.admit({"hostname": "victim_1", "severity": 3})
        assert result["status"] == "queued"
        assert result["admission_id"].startswith("adm-")
        assert result["status_url"] == f"/api/v1/alerts/{result['admission_id']}"

    async def test_stamps_alert_id_into_payload(self):
        uc = _uc()
        await uc.admit({"hostname": "victim_1"})
        assert uc.queue.events[0]["alert"]["alert_id"], "enqueued alert must carry an alert_id"

    async def test_preserves_caller_alert_id(self):
        uc = _uc()
        await uc.admit({"alert_id": "ALR-FIXED-1", "hostname": "victim_1"})
        assert uc.queue.events[0]["alert"]["alert_id"] == "ALR-FIXED-1"

    async def test_records_minimal_admission(self):
        uc = _uc()
        result = await uc.admit({"alert_id": "a1", "severity": 2})
        rec = await uc.store.get(result["admission_id"])
        assert rec is not None
        assert rec["status"] == "queued"
        assert rec["alert_id"] == "a1"
        assert "queued_at" in rec

    async def test_rejects_non_object_payload(self):
        uc = _uc()
        with pytest.raises(AdmissionValidationError):
            await uc.admit(["not", "an", "object"])

    async def test_rejects_oversized_payload(self):
        uc = _uc(max_bytes=64)
        with pytest.raises(AdmissionValidationError):
            await uc.admit({"blob": "x" * 1000})

    async def test_idempotent_replay_returns_same_admission(self):
        uc = _uc()
        first = await uc.admit({"alert_id": "x"}, idempotency_key="k-1")
        second = await uc.admit({"alert_id": "x"}, idempotency_key="k-1")
        assert second["admission_id"] == first["admission_id"]
        assert len(uc.queue.events) == 1, "replay must not enqueue twice"


class TestStatus:
    async def test_status_returns_record(self):
        uc = _uc()
        result = await uc.admit({"alert_id": "a9"})
        rec = await uc.status(result["admission_id"])
        assert rec["status"] == "queued"

    async def test_status_unknown_returns_none(self):
        uc = _uc()
        assert await uc.status("adm-nope") is None


class TestBackpressure:
    """PERF-003: saturated queue -> explicit rejection (maps to 503)."""

    @pytest.mark.asyncio
    async def test_saturated_queue_rejects(self):
        from soar_lab.application.use_cases.alert_admission import BackpressureError

        queue = FakeEventQueue()
        queue.events = [{}] * 5  # depth 5 >= cap 5
        uc = AlertAdmissionUseCase(queue=queue, store=FakeAdmissionStore(), max_queue_depth=5)
        with pytest.raises(BackpressureError, match="saturated"):
            await uc.admit({"title": "x"})
        # nothing persisted nor enqueued
        assert uc.store.records == {}
        assert len(queue.events) == 5

    @pytest.mark.asyncio
    async def test_below_capacity_admits(self):
        queue = FakeEventQueue()
        queue.events = [{}] * 4  # depth 4 < cap 5
        uc = AlertAdmissionUseCase(queue=queue, store=FakeAdmissionStore(), max_queue_depth=5)
        r = await uc.admit({"title": "x"})
        assert r["status"] == "queued"
        assert len(queue.events) == 5

    @pytest.mark.asyncio
    async def test_replay_bypasses_backpressure(self):
        """An idempotent replay returns the existing admission even when
        the queue is saturated — it does not add load."""
        queue = FakeEventQueue()
        store = FakeAdmissionStore()
        uc = AlertAdmissionUseCase(queue=queue, store=store, max_queue_depth=1)
        first = await uc.admit({"title": "x"}, idempotency_key="k")
        queue.events = [{}] * 10  # now saturated
        second = await uc.admit({"title": "x"}, idempotency_key="k")
        assert second["admission_id"] == first["admission_id"]


class TestTransitionAndConflicts:
    def test_check_transition_edges(self):
        from soar_lab.application.use_cases.alert_admission import check_transition

        assert check_transition(None, "queued") is True
        assert check_transition(None, "forwarded") is False
        # Unknown/missing state behaves like fresh: only "queued" allowed.
        assert check_transition("bogus", "queued") is True
        assert check_transition("bogus", "dead") is False
        assert check_transition("dead", "queued") is True  # operator redrive
        assert check_transition("workflow_accepted", "queued") is False

    async def test_idempotency_conflict_raises_409(self):
        from soar_lab.application.use_cases.alert_admission import IdempotencyConflictError

        uc = _uc()
        await uc.admit({"alert_id": "a", "hostname": "h1"}, idempotency_key="k1")
        with pytest.raises(IdempotencyConflictError):
            await uc.admit({"alert_id": "b", "hostname": "DIFFERENT"}, idempotency_key="k1")

    async def test_orphan_binding_repaired_and_retried(self):
        uc = _uc()
        # Pre-bind a key to a phantom admission_id (no record).
        uc.store.by_key["k-orphan"] = "adm-ghost"
        r = await uc.admit({"alert_id": "x", "title": "t"}, idempotency_key="k-orphan")
        assert r["status"] == "queued"
        assert uc.orphan_bindings_cleaned == 1
        assert uc.store.by_key["k-orphan"] == r["admission_id"]

    async def test_binding_exhaustion_raises_queue_unavailable(self):
        from soar_lab.application.use_cases.alert_admission import QueueUnavailableError

        store = FakeAdmissionStore()

        # Key is always claimed by a phantom whose record never exists —
        # both repair attempts exhaust the loop -> for/else fires.
        async def always_ghost(key, aid):
            return "ghost"

        async def never_record(aid):
            return None

        store.try_bind_key = always_ghost
        store.get = never_record
        uc = AlertAdmissionUseCase(queue=FakeEventQueue(), store=store)
        with pytest.raises(QueueUnavailableError, match="idempotency binding"):
            await uc.admit({"title": "t"}, idempotency_key="k")

    async def test_non_serializable_payload_rejected(self):
        uc = _uc()
        circular: dict = {}
        circular["self"] = circular  # default=str can't save a cycle
        with pytest.raises(AdmissionValidationError, match="serializable"):
            await uc.admit(circular)

    async def test_no_key_skips_binding(self):
        # No idempotency_key/alert_id/fingerprint -> line 184 break.
        uc = _uc()
        r = await uc.admit({})
        assert r["status"] == "queued"
        assert uc.store.by_key == {}


class TestWorkflowVerdict:
    async def test_unknown_returns_none(self):
        assert await _uc().record_workflow_verdict("adm-x", "accepted") is None

    async def test_ignored_when_not_forwarded(self):
        uc = _uc()
        r = await uc.admit({"alert_id": "a"})
        rec = await uc.record_workflow_verdict(r["admission_id"], "accepted")
        assert rec["status"] == "queued"  # ignored, no transition

    async def test_forwarded_transitions(self):
        uc = _uc()
        r = await uc.admit({"alert_id": "a"})
        aid = r["admission_id"]
        await uc.store.update(aid, {"status": "forwarded"})
        rec = await uc.record_workflow_verdict(aid, "rejected", reason="bad sig")
        assert rec["status"] == "workflow_rejected"
        assert rec["state_version"] == 2


class TestReconcile:
    async def test_repairs_enqueue_failed_records(self):
        uc = _uc()
        stuck = [
            {"admission_id": "a1", "alert": {"title": "t"}, "attempts": 1, "state_version": 1},
            {"admission_id": "a2", "alert": "not-a-dict"},  # skipped
            {"admission_id": None},  # skipped
        ]
        await uc.store.create(stuck[0])  # so update() works

        async def list_stuck(statuses, limit):
            return stuck

        uc.store.list_by_status = list_stuck
        out = await uc.reconcile()
        assert out == {"enqueue_failed_repaired": 1}
        assert uc.orphans_repaired == 1
        assert uc.store.records["a1"]["status"] == "queued"
        assert uc.queue.events[0]["admission_id"] == "a1"

    async def test_list_by_status_missing_or_failing(self):
        uc = _uc()
        assert await uc.reconcile() == {"enqueue_failed_repaired": 0}

        async def boom(statuses, limit):
            raise RuntimeError("redis down")

        uc.store.list_by_status = boom
        assert await uc.reconcile() == {"enqueue_failed_repaired": 0}

    async def test_reenqueue_failure_leaves_record(self):
        uc = _uc()
        await uc.store.create({"admission_id": "a1", "alert": {"t": 1}})

        async def stuck(statuses, limit):
            return [{"admission_id": "a1", "alert": {"t": 1}}]

        uc.store.list_by_status = stuck
        uc.queue.enqueue = lambda e: (_ for _ in ()).throw(RuntimeError("full"))
        assert await uc.reconcile() == {"enqueue_failed_repaired": 0}
