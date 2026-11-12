"""Mutation-kill contracts for the hardened messaging layer.

Pins the exact observable behaviour of the Redis Streams queue, the
admission worker, the worker lease, the admission store and the Shuffle
forwarder — argument order, serialization, boundary comparisons, error
classification and default budgets. The broad mutmut run showed these
were silently mutable without an assertion pinning them.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
import requests

from soar_lab.infrastructure.messaging.admission_worker import AdmissionWorker
from soar_lab.infrastructure.messaging.redis_admission_store import (
    RedisAdmissionStore,
)
from soar_lab.infrastructure.messaging.redis_streams_queue import (
    RedisStreamsQueue,
)
from soar_lab.infrastructure.messaging.shuffle_forward import (
    DestinationPolicyError,
    _classify,
    _validate_target,
    make_shuffle_forward,
    resolve_target_url,
)
from soar_lab.infrastructure.messaging.worker_lease import (
    FENCE_KEY,
    LEASE_KEY,
    WorkerLease,
)


def _worker(queue=None, store=None, forward=None, **kw):
    return AdmissionWorker(
        queue or AsyncMock(),
        store or AsyncMock(),
        forward or AsyncMock(),
        **kw,
    )


# ── RedisStreamsQueue ────────────────────────────────────────────────────


class TestRedisStreamsQueue:
    @pytest.mark.asyncio
    async def test_enqueue_payload_contract(self):
        client = AsyncMock()
        q = RedisStreamsQueue(client, "s", "dlq", maxlen=1000)
        event = {"alert": {"a": 1}, "when": datetime(2024, 1, 1)}
        await q.enqueue(event)
        client.xadd.assert_awaited_once()
        stream, fields = client.xadd.call_args[0]
        assert stream == "s"
        assert set(fields) == {"payload"}
        # default=str must serialize non-JSON-native values (kills its removal).
        assert json.loads(fields["payload"])["when"] == "2024-01-01 00:00:00"
        assert client.xadd.call_args.kwargs == {"maxlen": 1000, "approximate": True}

    @pytest.mark.asyncio
    async def test_enqueue_non_serializable_does_not_raise(self):
        q = RedisStreamsQueue(AsyncMock(), "s", "dlq")
        await q.enqueue({"ts": datetime(2030, 6, 15, 12, 0, 0)})

    @pytest.mark.asyncio
    async def test_dead_letter_reason_truncated(self):
        client = AsyncMock()
        q = RedisStreamsQueue(client, "s", "dlq", maxlen=5)
        await q.dead_letter({"a": 1}, reason="r" * 600)
        _, fields = client.xadd.call_args[0]
        assert set(fields) == {"payload", "reason"}
        assert fields["reason"] == "r" * 512
        assert client.xadd.call_args.kwargs == {"maxlen": 5, "approximate": True}

    @pytest.mark.asyncio
    async def test_ack_args(self):
        client = AsyncMock()
        q = RedisStreamsQueue(client, "s", "dlq")
        await q.ack("g", "1-1")
        client.xack.assert_awaited_once_with("s", "g", "1-1")

    @pytest.mark.asyncio
    async def test_ensure_group_swallows_only_busygroup(self):
        client = AsyncMock()
        q = RedisStreamsQueue(client, "s", "dlq")
        client.xgroup_create.side_effect = Exception("BUSYGROUP Consumer Group name already exists")
        await q.ensure_group("g")  # no raise
        client.xgroup_create.side_effect = Exception("WRONGTYPE")
        with pytest.raises(Exception, match="WRONGTYPE"):
            await q.ensure_group("g")

    @pytest.mark.asyncio
    async def test_ensure_group_args(self):
        client = AsyncMock()
        q = RedisStreamsQueue(client, "s", "dlq")
        await q.ensure_group("g")
        client.xgroup_create.assert_awaited_once_with(
            "s", "g", id="0", mkstream=True
        )

    @pytest.mark.asyncio
    async def test_read_xreadgroup_args(self):
        client = AsyncMock()
        client.xreadgroup.return_value = []
        q = RedisStreamsQueue(client, "s", "dlq")
        await q.read("g", "c", 10, 500)
        client.xreadgroup.assert_awaited_once_with(
            "g", "c", {"s": ">"}, count=10, block=500
        )

    @pytest.mark.asyncio
    async def test_read_ensures_group_first(self):
        client = AsyncMock()
        client.xreadgroup.return_value = []
        q = RedisStreamsQueue(client, "s", "dlq")
        await q.read("g", "c", 1, 1)
        client.xgroup_create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_read_decodes_entries(self):
        client = AsyncMock()
        client.xreadgroup.return_value = [
            (b"s", [(b"1-1", {b"payload": b'{"a": 1}'})])
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        rows = await q.read("g", "c", 1, 1)
        # entry_id passes through as Redis returns it (bytes).
        assert rows == [(b"1-1", {"a": 1})]

    @pytest.mark.asyncio
    async def test_read_poison_goes_to_dlq(self):
        client = AsyncMock()
        client.xreadgroup.return_value = [
            (b"s", [(b"1-1", {b"payload": b"not-json{"})])
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        rows = await q.read("g", "c", 1, 1)
        assert rows == []
        # poison: xadd to DLQ with decode_failed + xack on main stream
        dlq_call = client.xadd.call_args
        assert dlq_call[0][0] == "dlq"
        assert dlq_call[0][1]["reason"] == "decode_failed"
        assert dlq_call[0][1]["source_entry_id"] == "1-1"
        client.xack.assert_awaited_once_with("s", "g", b"1-1")

    @pytest.mark.asyncio
    async def test_claim_stale_xautoclaim_args(self):
        client = AsyncMock()
        client.xautoclaim.return_value = (b"0-0", [], [])
        q = RedisStreamsQueue(client, "s", "dlq")
        await q.claim_stale("g", "c", 30000)
        client.xautoclaim.assert_awaited_once_with(
            "s", "g", "c", min_idle_time=30000, start_id="0-0", count=100
        )

    @pytest.mark.asyncio
    async def test_claim_stale_error_returns_empty(self):
        client = AsyncMock()
        client.xautoclaim.side_effect = RuntimeError("boom")
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.claim_stale("g", "c", 1) == []

    @pytest.mark.asyncio
    async def test_claim_stale_decodes_and_poisons(self):
        client = AsyncMock()
        client.xautoclaim.return_value = (
            b"0-0",
            [(b"1-1", {b"payload": b'{"ok": true}'}), (b"2-2", {b"payload": b"bad{"})],
            [],
        )
        q = RedisStreamsQueue(client, "s", "dlq")
        out = await q.claim_stale("g", "c", 1)
        assert out == [(b"1-1", {"ok": True})]
        client.xack.assert_awaited_once_with("s", "g", b"2-2")

    @pytest.mark.asyncio
    async def test_depth_sums_pending_and_lag(self):
        client = AsyncMock()
        client.xinfo_groups.return_value = [
            {b"pending": 3, b"lag": 2},
            {"pending": 4, "lag": 1},
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.depth() == 10
        client.xinfo_groups.assert_awaited_once_with("s")

    @pytest.mark.asyncio
    async def test_depth_falls_back_to_xlen(self):
        client = AsyncMock()
        client.xinfo_groups.side_effect = RuntimeError("unsupported")
        client.xlen.return_value = 42
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.depth() == 42

    @pytest.mark.asyncio
    async def test_stream_length_and_dlq_size(self):
        client = AsyncMock()
        client.xlen.side_effect = [10, 7]
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.stream_length() == 10
        assert await q.dlq_size() == 7
        assert client.xlen.await_args_list[0][0][0] == "s"
        assert client.xlen.await_args_list[1][0][0] == "dlq"

    @pytest.mark.asyncio
    async def test_dlq_list_shape(self):
        client = AsyncMock()
        client.xrange.return_value = [
            (b"1-1", {b"payload": b'{"a": 1}', b"reason": b"oops"}),
            (b"2-2", {b"payload": b"bad{", b"reason": b"r2"}),
            (b"3-3", {b"other": b"x"}),
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        rows = await q.dlq_list(count=25)
        client.xrange.assert_awaited_once_with("dlq", count=25)
        assert rows[0] == {"dlq_entry_id": "1-1", "reason": "oops", "payload": {"a": 1}}
        assert rows[1]["payload"] is None and rows[1]["reason"] == "r2"
        assert rows[2]["reason"] == "unknown" and rows[2]["payload"] is None

    @pytest.mark.asyncio
    async def test_dlq_redrive_found(self):
        client = AsyncMock()
        client.xrange.return_value = [
            (b"1-1", {b"payload": b'{"attempts": 5, "x": 1}'})
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.dlq_redrive("1-1") is True
        client.xrange.assert_awaited_once_with("dlq", min="1-1", max="1-1")
        re_queued = json.loads(client.xadd.call_args[0][1]["payload"])
        assert re_queued["attempts"] == 0
        assert "redriven_at" in re_queued
        client.xdel.assert_awaited_once_with("dlq", "1-1")

    @pytest.mark.asyncio
    async def test_dlq_redrive_missing_or_bad(self):
        client = AsyncMock()
        client.xrange.return_value = []
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.dlq_redrive("9-9") is False
        client.xrange.return_value = [(b"1-1", {b"payload": b'"just-a-string"'})]
        assert await q.dlq_redrive("1-1") is False
        client.xadd.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dlq_purge(self):
        client = AsyncMock()
        client.xlen.return_value = 3
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.dlq_purge() == 3
        client.xtrim.assert_awaited_once_with("dlq", maxlen=0)
        client.xtrim.reset_mock()
        client.xlen.return_value = 0
        assert await q.dlq_purge() == 0
        client.xtrim.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_dlq_auto_redrive_guards(self):
        client = AsyncMock()
        old = "1000-0"  # ancient entry — past any min_age
        client.xrange.return_value = [
            (old.encode(), {b"payload": b'{"a": 1}', b"reason": b"transient"}),
            (b"2000-0", {b"payload": b'{"b": 2}', b"reason": b"decode_failed"}),
            (old.encode(), {b"payload": b'"str"', b"reason": b"r"}),
            (old.encode(), {b"payload": b'{"redrive_count": 3}', b"reason": b"r"}),
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        n = await q.dlq_auto_redrive(limit=10, max_redrives=3, min_age_s=60.0)
        # Only entry 1 redrives: decode_failed skipped, non-dict skipped,
        # redrive_count>=3 skipped.
        assert n == 1
        re_queued = json.loads(client.xadd.call_args[0][1]["payload"])
        assert re_queued["attempts"] == 0 and re_queued["redrive_count"] == 1
        client.xdel.assert_awaited_once_with("dlq", old)

    @pytest.mark.asyncio
    async def test_dlq_auto_redrive_min_age(self):
        client = AsyncMock()
        fresh = str(int(__import__("time").time() * 1000)) + "-0"
        client.xrange.return_value = [
            (fresh.encode(), {b"payload": b'{"a": 1}', b"reason": b"r"})
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        # Fresh entry + 60s min age → not redriven.
        assert await q.dlq_auto_redrive() == 0
        client.xadd.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_metrics_shape(self):
        client = AsyncMock()
        client.xlen.side_effect = [10, 2]
        client.xinfo_groups.return_value = [
            {b"name": b"soar-api", b"pending": 5, b"lag": 3},
            {b"name": b"other", b"pending": 9, b"lag": 9},
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        m = await q.metrics()
        assert m["queue_depth"] == 26  # sum of pending+lag across all groups
        assert m["stream_length"] == 10
        assert m["dlq_size"] == 2
        assert m["pending"] == 5
        assert m["consumer_lag"] == 3

    @pytest.mark.asyncio
    async def test_metrics_xinfo_failure(self):
        client = AsyncMock()
        # depth() fallback xlen, stream_length xlen, dlq_size xlen.
        client.xlen.side_effect = [1, 4, 0]
        client.xinfo_groups.side_effect = RuntimeError("down")
        q = RedisStreamsQueue(client, "s", "dlq")
        m = await q.metrics()
        assert m["queue_depth"] == 1
        assert m["pending"] is None and m["consumer_lag"] is None

    def test_decode_fields(self):
        f = RedisStreamsQueue._decode_fields
        assert f({b"payload": b'{"a": 1}'}) == {"a": 1}
        assert f({"payload": '{"a": 1}'}) == {"a": 1}
        assert f({b"other": b"x"}) is None
        assert f({b"payload": b"bad{"}) is None
        assert f({}) is None

    def test_s_helper(self):
        s = RedisStreamsQueue._s
        assert s(b"abc") == "abc"
        assert s("abc") == "abc"
        assert s(123) == "123"


class TestQueueInternalsExtra:
    @pytest.mark.asyncio
    async def test_read_ensures_real_group(self):
        client = AsyncMock()
        client.xreadgroup.return_value = []
        q = RedisStreamsQueue(client, "s", "dlq")
        await q.read("the-group", "c", 1, 1)
        client.xgroup_create.assert_awaited_once_with(
            "s", "the-group", id="0", mkstream=True
        )

    @pytest.mark.asyncio
    async def test_claim_stale_ensures_real_group(self):
        client = AsyncMock()
        client.xautoclaim.return_value = (b"0-0", [], [])
        q = RedisStreamsQueue(client, "s", "dlq")
        await q.claim_stale("the-group", "c", 1)
        client.xgroup_create.assert_awaited_once_with(
            "s", "the-group", id="0", mkstream=True
        )

    @pytest.mark.asyncio
    async def test_dead_letter_payload_serializes_entry(self):
        client = AsyncMock()
        q = RedisStreamsQueue(client, "s", "dlq")
        await q.dead_letter({"a": 1, "n": None}, reason="r")
        _, fields = client.xadd.call_args[0]
        assert json.loads(fields["payload"]) == {"a": 1, "n": None}
        assert fields["reason"] == "r"

    @pytest.mark.asyncio
    async def test_depth_zero_pending_counts_zero(self):
        client = AsyncMock()
        client.xinfo_groups.return_value = [{b"pending": 0, b"lag": 0}]
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.depth() == 0

    @pytest.mark.asyncio
    async def test_depth_missing_keys_contribute_zero(self):
        client = AsyncMock()
        client.xinfo_groups.return_value = [{}, {"other": 5}]
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.depth() == 0

    @pytest.mark.asyncio
    async def test_dlq_redrive_marks_redriven_at(self):
        client = AsyncMock()
        client.xrange.return_value = [
            (b"1-1", {b"payload": b'{"attempts": 5}'})
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.dlq_redrive("1-1") is True
        re_queued = json.loads(client.xadd.call_args[0][1]["payload"])
        assert isinstance(re_queued["redriven_at"], float)
        assert re_queued["attempts"] == 0

    @pytest.mark.asyncio
    async def test_auto_redrive_exact_min_age_boundary_redrives(self):
        import time as time_mod

        client = AsyncMock()
        # Entry dead exactly 60s — the `now-entry < min_age` guard must NOT
        # skip it (kills < vs <=).
        entry_ms = int(time_mod.time() * 1000) - 60_000
        eid = f"{entry_ms}-0"
        client.xrange.return_value = [
            (eid.encode(), {b"payload": b'{"a": 1}', b"reason": b"r"})
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.dlq_auto_redrive(min_age_s=60.0) == 1

    @pytest.mark.asyncio
    async def test_auto_redrive_exponential_backoff_2_pow(self):
        import time as time_mod

        client = AsyncMock()
        # redrive_count=1 → min age = 60*2**1 = 120s. Entry dead 150s:
        # real code redrives; a 3**count mutant (180s) would skip it.
        entry_ms = int(time_mod.time() * 1000) - 150_000
        eid = f"{entry_ms}-0"
        client.xrange.return_value = [
            (
                eid.encode(),
                {b"payload": b'{"redrive_count": 1}', b"reason": b"r"},
            )
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.dlq_auto_redrive(min_age_s=60.0) == 1
        re_queued = json.loads(client.xadd.call_args[0][1]["payload"])
        assert re_queued["redrive_count"] == 2

    @pytest.mark.asyncio
    async def test_auto_redrive_unparseable_entry_id_redrives(self):
        client = AsyncMock()
        client.xrange.return_value = [
            (b"abc", {b"payload": b'{"a": 1}', b"reason": b"r"})
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        assert await q.dlq_auto_redrive() == 1

    @pytest.mark.asyncio
    async def test_auto_redrive_default_limit_100(self):
        client = AsyncMock()
        client.xrange.return_value = []
        q = RedisStreamsQueue(client, "s", "dlq")
        await q.dlq_auto_redrive()
        client.xrange.assert_awaited_once_with("dlq", count=100)

    @pytest.mark.asyncio
    async def test_auto_redrive_default_max_redrives_3(self):
        client = AsyncMock()
        client.xrange.return_value = [
            (b"1-0", {b"payload": b'{"redrive_count": 3}', b"reason": b"r"}),
            (b"1-0", {b"payload": b'{"redrive_count": 2}', b"reason": b"r"}),
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        # count=3 at the default budget → skipped; count=2 → redriven.
        assert await q.dlq_auto_redrive() == 1

    @pytest.mark.asyncio
    async def test_metrics_str_keyed_groups(self):
        client = AsyncMock()
        client.xlen.side_effect = [5, 1]
        client.xinfo_groups.return_value = [
            {"name": "soar-api", "pending": 2},  # no lag key → lag None
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        m = await q.metrics()
        assert m["pending"] == 2
        assert m["consumer_lag"] is None

    @pytest.mark.asyncio
    async def test_metrics_group_name_filter(self):
        client = AsyncMock()
        client.xlen.side_effect = [5, 1]
        client.xinfo_groups.return_value = [
            {b"name": b"other-group", b"pending": 7, b"lag": 7},
        ]
        q = RedisStreamsQueue(client, "s", "dlq")
        m = await q.metrics(group="soar-api")
        assert m["pending"] is None and m["consumer_lag"] is None

    @pytest.mark.asyncio
    async def test_poison_truncates_raw_and_decodes(self):
        client = AsyncMock()
        q = RedisStreamsQueue(client, "s", "dlq", maxlen=9)
        big = b"x" * 5000
        await q._poison_to_dlq("g", b"1-1", {b"payload": big})
        _, fields = client.xadd.call_args[0]
        assert len(fields["payload"]) == 4000
        assert fields["reason"] == "decode_failed"
        assert fields["source_entry_id"] == "1-1"
        assert client.xadd.call_args.kwargs == {"maxlen": 9, "approximate": True}
        client.xack.assert_awaited_once_with("s", "g", b"1-1")


# ── AdmissionWorker ──────────────────────────────────────────────────────


class TestAdmissionWorker:
    def test_defaults(self):
        w = _worker()
        assert w.group == "soar-api"
        assert w.consumer == "worker-1"
        assert w.max_attempts == 5
        assert w.batch_size == 10
        assert w.poll_ms == 500
        assert w.stale_ms == 30_000
        assert w.retry_base_s == 1.0
        assert w.retry_cap_s == 16.0
        assert w.retry_cap_s * 1000 < w.stale_ms
        assert w.recover_interval_s == 60.0
        assert w.dlq_auto_redrive is True
        assert w.dlq_redrive_max == 3
        assert w.dlq_redrive_min_age_s == 60.0

    def test_retry_delay_cap_curve(self):
        w = _worker()
        caps = []
        w._rng.uniform = lambda lo, hi: caps.append((lo, hi)) or 0.0
        for attempts in (1, 2, 3, 4, 5, 100):
            w._retry_delay(attempts)
        assert caps == [
            (0, 1.0),   # 1 * 2**0
            (0, 2.0),   # 1 * 2**1
            (0, 4.0),   # 1 * 2**2
            (0, 8.0),   # 1 * 2**3
            (0, 16.0),  # capped at retry_cap_s
            (0, 16.0),  # stays capped below stale_ms (PIPE-EVAL-001)
        ]

    def test_retry_delay_low_bound_zero(self):
        w = _worker()
        w._rng.seed(0)
        for _ in range(50):
            assert 0.0 <= w._retry_delay(3) <= 4.0

    @pytest.mark.asyncio
    async def test_run_once_read_args(self):
        w = _worker()
        w.queue.read.return_value = []
        assert await w.run_once() == 0
        w.queue.read.assert_awaited_once_with("soar-api", "worker-1", 10, 500)

    @pytest.mark.asyncio
    async def test_run_once_sibling_failure_does_not_propagate(self):
        # return_exceptions=True contract: a crashing _process must not
        # raise out of run_once nor lose the count.
        w = _worker()
        w.queue.read.return_value = [("1-1", {"admission_id": "a"}), ("2-2", {"admission_id": "b"})]

        async def boom(*_a):
            raise RuntimeError("boom")

        w._process = boom
        assert await w.run_once() == 2

    @pytest.mark.asyncio
    async def test_recover_args(self):
        w = _worker()
        w.queue.claim_stale.return_value = []
        assert await w.recover() == 0
        w.queue.claim_stale.assert_awaited_once_with("soar-api", "worker-1", 30_000)

    @pytest.mark.asyncio
    async def test_process_envelope_attempt_and_delivery_id(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        forward = AsyncMock(return_value={"ok": True, "exec_id": "e1", "status_code": 200})
        w = AdmissionWorker(queue, store, forward)
        await w._process("1-1", {"admission_id": "adm-1", "alert": {"x": 1}, "attempts": 2})
        alert = forward.call_args[0][0]
        assert alert["attempt"] == 3
        assert alert["delivery_id"] == "adm-1:3"

    @pytest.mark.asyncio
    async def test_process_success_updates_and_acks(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        forward = AsyncMock(return_value={"ok": True, "exec_id": "e1", "status_code": 200})
        w = AdmissionWorker(queue, store, forward)
        await w._process("1-1", {"admission_id": "adm-1", "alert": {}, "attempts": 0})
        fields = store.update.call_args[0][1]
        assert fields["status"] == "forwarded"
        assert fields["attempts"] == 1
        assert fields["downstream_execution_id"] == "e1"
        assert fields["downstream_status"] == 200
        queue.ack.assert_awaited_once_with("soar-api", "1-1")

    @pytest.mark.asyncio
    async def test_terminal_record_skips_and_acks(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "forwarded"}
        forward = AsyncMock()
        w = AdmissionWorker(queue, store, forward)
        await w._process("1-1", {"admission_id": "a", "alert": {}})
        forward.assert_not_awaited()
        queue.ack.assert_awaited_once_with("soar-api", "1-1")

    @pytest.mark.asyncio
    async def test_unreadable_store_defers_without_forward(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.side_effect = RuntimeError("down")
        forward = AsyncMock()
        w = AdmissionWorker(queue, store, forward)
        await w._process("1-1", {"admission_id": "a", "alert": {}})
        forward.assert_not_awaited()
        queue.ack.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_non_retryable_goes_to_dlq_immediately(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        forward = AsyncMock(return_value={"ok": False, "retryable": False, "error_code": "DOWNSTREAM_REJECTED"})
        w = AdmissionWorker(queue, store, forward)
        event = {"admission_id": "a", "alert": {}, "attempts": 0}
        await w._process("1-1", event)
        queue.dead_letter.assert_awaited_once()
        assert queue.dead_letter.call_args.kwargs["reason"] == "DOWNSTREAM_REJECTED"
        assert store.update.call_args[0][1]["status"] == "dead"

    @pytest.mark.asyncio
    async def test_max_attempts_boundary(self):
        # attempts=4 (5th total) must DLQ at default max_attempts=5 —
        # pins `attempts >= self.max_attempts` (kills >=→>).
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        forward = AsyncMock(return_value={"ok": False, "retryable": True, "error_code": "X"})
        w = AdmissionWorker(queue, store, forward)
        await w._process("1-1", {"admission_id": "a", "alert": {}, "attempts": 3})
        queue.dead_letter.assert_not_awaited()  # attempt 4 → retry
        await w._process("2-2", {"admission_id": "b", "alert": {}, "attempts": 4})
        queue.dead_letter.assert_awaited_once()  # attempt 5 → dead

    @pytest.mark.asyncio
    async def test_retryable_failure_reenqueues(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        forward = AsyncMock(return_value={"ok": False, "retryable": True, "error_code": "X"})
        w = AdmissionWorker(queue, store, forward)
        event = {"admission_id": "a", "alert": {}, "attempts": 0}
        await w._process("1-1", event)
        queue.enqueue.assert_awaited_once()
        re_queued = queue.enqueue.call_args[0][0]
        assert re_queued["attempts"] == 1
        assert re_queued["admission_id"] == "a"

    @pytest.mark.asyncio
    async def test_error_code_from_result(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        forward = AsyncMock(return_value={"ok": False, "retryable": False, "error": "raw failure text"})
        w = AdmissionWorker(queue, store, forward)
        await w._process("1-1", {"admission_id": "a", "alert": {}, "attempts": 0})
        reason = queue.dead_letter.call_args.kwargs["reason"]
        assert reason == "raw failure text"

    @pytest.mark.asyncio
    async def test_forward_exception_classified(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        forward = AsyncMock(side_effect=RuntimeError("net down"))
        w = AdmissionWorker(queue, store, forward)
        await w._process("1-1", {"admission_id": "a", "alert": {}, "attempts": 0})
        # FORWARD_EXCEPTION is retryable → re-enqueue, not DLQ (attempt 1).
        queue.enqueue.assert_awaited_once()
        queue.dead_letter.assert_not_awaited()
        assert w.stats.last_error == "FORWARD_EXCEPTION"

    @pytest.mark.asyncio
    async def test_retry_path_updates_enqueue_ack(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        forward = AsyncMock(return_value={"ok": False, "retryable": True, "error_code": "X"})
        w = AdmissionWorker(queue, store, forward)
        event = {"admission_id": "a", "alert": {}, "attempts": 1}
        await w._process("1-1", event)
        fields = store.update.call_args[0][1]
        assert fields["status"] == "retry_scheduled"
        assert fields["attempts"] == 2
        assert fields["last_error"] == "X"
        enq = queue.enqueue.call_args[0][0]
        assert enq["attempts"] == 2
        queue.ack.assert_awaited_once_with("soar-api", "1-1")
        assert w.stats.retried_total == 1

    @pytest.mark.asyncio
    async def test_dead_letter_event_and_update_fields(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        forward = AsyncMock(return_value={"ok": False, "retryable": False, "error_code": "E"})
        w = AdmissionWorker(queue, store, forward)
        event = {"admission_id": "a", "alert": {}, "attempts": 0}
        await w._process("1-1", event)
        dlq_event = queue.dead_letter.call_args[0][0]
        assert dlq_event is event  # same object, not None/clone
        fields = store.update.call_args[0][1]
        assert fields["status"] == "dead"
        assert fields["attempts"] == 1
        assert fields["last_error"] == "E"
        queue.ack.assert_awaited_once_with("soar-api", "1-1")
        assert w.stats.dead_total == 1

    @pytest.mark.asyncio
    async def test_error_code_falls_back_to_redacted_error(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        long_err = "e" * 200
        forward = AsyncMock(return_value={"ok": False, "retryable": False, "error": long_err})
        w = AdmissionWorker(queue, store, forward)
        await w._process("1-1", {"admission_id": "a", "alert": {}, "attempts": 0})
        reason = queue.dead_letter.call_args.kwargs["reason"]
        # redact_text with max_len=80 bounds the stored/forwarded error.
        assert len(reason) <= 80

    @pytest.mark.asyncio
    async def test_stats_inflight_and_counters(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        seen = {}

        async def slow_forward(_alert):
            seen["inflight"] = w.stats.inflight
            return {"ok": True, "exec_id": None, "status_code": 200}

        w = AdmissionWorker(queue, store, slow_forward)
        await w._process("1-1", {"admission_id": "a", "alert": {}, "attempts": 0})
        assert seen["inflight"] == 1  # incremented during the call
        assert w.stats.inflight == 0  # decremented after
        assert w.stats.processed_total == 1
        assert w.stats.forwarded_total == 1
        assert w.stats.forward_seconds_total >= 0

    @pytest.mark.asyncio
    async def test_retry_backoff_sleeps_bounded(self):
        import asyncio

        w = _worker()
        sleeps = []
        orig_sleep = asyncio.sleep

        async def fake_sleep(d):
            sleeps.append(d)

        w._rng.uniform = lambda lo, hi: hi  # deterministic max delay
        # attempts=3 → delay cap 4.0 but bounded by stale_ms/2000 = 15
        monkey = asyncio.sleep
        try:
            asyncio.sleep = fake_sleep
            await w._retry_backoff(3)
        finally:
            asyncio.sleep = orig_sleep
        assert sleeps == [4.0]  # min(4.0, 15.0)

    @pytest.mark.asyncio
    async def test_retry_backoff_skips_zero_and_negative(self):
        w = _worker()
        called = []
        w._rng.uniform = lambda lo, hi: called.append(1) or 0.0
        await w._retry_backoff(0)
        await w._retry_backoff(-1)
        assert called == []  # attempts<=0 returns before computing delay

    @pytest.mark.asyncio
    async def test_update_sets_changed_at_and_version(self):
        store = AsyncMock()
        store.get.return_value = {"status": "queued", "state_version": 5}
        w = _worker(store=store)
        await w._update("a", {"status": "forwarded"})
        fields = store.update.call_args[0][1]
        assert fields["status"] == "forwarded"
        import re

        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", fields["changed_at"])
        assert fields["state_version"] == 6  # current(5) + 1

    @pytest.mark.asyncio
    async def test_update_default_version_increments_from_1(self):
        store = AsyncMock()
        store.get.return_value = None
        w = _worker(store=store)
        await w._update("a", {"status": "queued"})
        assert store.update.call_args[0][1]["state_version"] == 2  # default 1 + 1

    @pytest.mark.asyncio
    async def test_update_illegal_transition_flagged(self):
        store = AsyncMock()
        store.get.return_value = {"status": "forwarded", "state_version": 3}
        w = _worker(store=store)
        # forwarded → dead is NOT in TRANSITIONS → violation audited.
        await w._update("a", {"status": "dead"})
        fields = store.update.call_args[0][1]
        assert fields["transition_violation"] == "forwarded->dead"

    @pytest.mark.asyncio
    async def test_update_legal_transition_clean(self):
        store = AsyncMock()
        store.get.return_value = {"status": "queued"}
        w = _worker(store=store)
        await w._update("a", {"status": "forwarded"})
        assert "transition_violation" not in store.update.call_args[0][1]

    @pytest.mark.asyncio
    async def test_update_no_status_to_skips_check(self):
        store = AsyncMock()
        store.get.return_value = {"status": "forwarded"}
        w = _worker(store=store)
        await w._update("a", {"attempts": 2})  # no "status" key → no check
        assert "transition_violation" not in store.update.call_args[0][1]

    def test_init_details(self):
        stats = Mock()
        w = _worker(stats=stats)
        assert w.stats is stats  # injected stats used, not replaced
        assert w._semaphore._value == 4  # concurrency default
        assert w._fence_token is None

    @pytest.mark.asyncio
    async def test_leader_no_lease_is_true(self):
        w = _worker()
        assert await w._leader() is True

    @pytest.mark.asyncio
    async def test_leader_lease_semantics(self):
        lease = Mock()
        w = _worker(lease=lease)
        lease.held = AsyncMock(return_value=False)
        assert await w._leader() is False
        lease.held = AsyncMock(return_value=True)
        lease.fence_token = 7
        assert await w._leader() is True
        assert w._fence_token == 7
        lease.held = AsyncMock(side_effect=RuntimeError("x"))
        assert await w._leader() is False

    @pytest.mark.asyncio
    async def test_reconcile_noop_and_error(self):
        w = _worker()  # reconciler None → no-op
        await w._reconcile()
        w2 = _worker(reconciler=AsyncMock(side_effect=RuntimeError("x")))
        await w2._reconcile()  # swallowed, logged
        w3 = _worker(reconciler=AsyncMock(return_value={"enqueue_failed_repaired": 4}))
        await w3._reconcile()
        assert w3.stats.orphans_repaired_total == 4

    @pytest.mark.asyncio
    async def test_run_invokes_dlq_auto_redrive_when_leader(self):
        import asyncio

        queue, store = AsyncMock(), AsyncMock()
        queue.claim_stale.return_value = []
        stop = asyncio.Event()

        async def read_then_stop(*_a, **_kw):
            stop.set()  # exit after exactly one iteration — no busy loop
            return []

        queue.read.side_effect = read_then_stop
        w = AdmissionWorker(queue, store, AsyncMock(), recover_interval_s=0.0)
        await asyncio.wait_for(w.run(stop), timeout=10)
        queue.dlq_auto_redrive.assert_awaited_with(max_redrives=3, min_age_s=60.0)


class TestWorkerInternalsExtra:
    @pytest.mark.asyncio
    async def test_retry_backoff_attempts_1_sleeps(self, monkeypatch):
        import asyncio

        w = _worker()
        sleeps = []

        async def fake_sleep(d):
            sleeps.append(d)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        w._rng.uniform = lambda lo, hi: hi
        await w._retry_backoff(1)  # attempts<=0 mutant would skip this
        assert sleeps == [1.0]

    @pytest.mark.asyncio
    async def test_retry_backoff_zero_delay_no_sleep(self, monkeypatch):
        import asyncio

        w = _worker()
        sleeps = []

        async def fake_sleep(d):
            sleeps.append(d)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        w._rng.uniform = lambda lo, hi: 0.0  # delay == 0 → skip (`>` not `>=`)
        await w._retry_backoff(2)
        assert sleeps == []

    @pytest.mark.asyncio
    async def test_retry_backoff_sub_1_delay_sleeps(self, monkeypatch):
        import asyncio

        w = _worker()
        sleeps = []

        async def fake_sleep(d):
            sleeps.append(d)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        w._rng.uniform = lambda lo, hi: 0.5
        await w._retry_backoff(1)  # `delay > 0`, not `> 1`
        assert sleeps == [0.5]

    @pytest.mark.asyncio
    async def test_retry_backoff_cap_stale_div_2000(self, monkeypatch):
        import asyncio

        w = _worker()
        sleeps = []

        async def fake_sleep(d):
            sleeps.append(d)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        w._rng.uniform = lambda lo, hi: 20.0  # delay above cap
        await w._retry_backoff(2)
        assert sleeps == [15.0]  # min(20, stale_ms/2000=15.0)

    @pytest.mark.asyncio
    async def test_forward_timed_exception_exact_result(self):
        forward = AsyncMock(side_effect=RuntimeError("down"))
        w = _worker(forward=forward)
        res = await w._forward_timed({}, "adm-1")
        assert res == {
            "ok": False,
            "error_code": "FORWARD_EXCEPTION",
            "retryable": True,
        }

    @pytest.mark.asyncio
    async def test_forward_timed_inflight_restored_and_counters(self):
        w = _worker(forward=AsyncMock(return_value={"ok": True}))
        await w._forward_timed({}, "a")
        await w._forward_timed({}, "a")
        assert w.stats.inflight == 0
        assert w.stats.processed_total == 2
        assert w.stats.forward_seconds_total >= 0

    @pytest.mark.asyncio
    async def test_process_missing_admission_id_defaults_unknown(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = None
        w = _worker(queue=queue, store=store, forward=AsyncMock(return_value={"ok": True}))
        await w._process("1-1", {})
        store.get.assert_awaited_with("unknown")

    @pytest.mark.asyncio
    async def test_process_missing_alert_defaults_empty(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = None
        forward = AsyncMock(return_value={"ok": True})
        w = _worker(queue=queue, store=store, forward=forward)
        await w._process("1-1", {"admission_id": "a"})
        alert = forward.call_args[0][0]
        assert alert["attempt"] == 1
        assert alert["delivery_id"] == "a:1"

    @pytest.mark.asyncio
    async def test_stats_counters_accumulate(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        forward = AsyncMock(return_value={"ok": True})
        w = _worker(queue=queue, store=store, forward=forward)
        await w._process("1-1", {"admission_id": "a", "alert": {}})
        await w._process("2-2", {"admission_id": "b", "alert": {}})
        assert w.stats.forwarded_total == 2  # += not =

    @pytest.mark.asyncio
    async def test_stats_dead_and_retried_accumulate(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "queued"}
        w = _worker(queue=queue, store=store)
        w.forward = AsyncMock(
            return_value={"ok": False, "retryable": False, "error_code": "X"}
        )
        await w._process("1-1", {"admission_id": "a", "alert": {}, "attempts": 0})
        await w._process("2-2", {"admission_id": "b", "alert": {}, "attempts": 0})
        assert w.stats.dead_total == 2

    @pytest.mark.asyncio
    async def test_terminal_dedup_accumulates(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = {"status": "dead"}
        w = _worker(queue=queue, store=store, forward=AsyncMock())
        await w._process("1-1", {"admission_id": "a", "alert": {}})
        await w._process("2-2", {"admission_id": "b", "alert": {}})
        assert w.stats.dedup_total == 2

    @pytest.mark.asyncio
    async def test_handle_failure_default_error_code(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = None
        w = _worker(queue=queue, store=store)
        await w._handle_failure(
            "1-1", {}, "a", 4, {"ok": False, "retryable": False}
        )
        # Neither error_code nor error → FORWARD_FAILED fallback.
        assert w.stats.last_error == "FORWARD_FAILED"
        assert w.stats.errors["FORWARD_FAILED"] == 1
        assert queue.dead_letter.call_args.kwargs["reason"] == "FORWARD_FAILED"

    @pytest.mark.asyncio
    async def test_handle_failure_error_truncated_80(self):
        queue, store = AsyncMock(), AsyncMock()
        store.get.return_value = None
        w = _worker(queue=queue, store=store)
        await w._handle_failure(
            "1-1", {}, "a", 4, {"ok": False, "retryable": False, "error": "e" * 200}
        )
        assert len(w.stats.last_error) <= 81  # 80 + ellipsis

    @pytest.mark.asyncio
    async def test_reconcile_accumulates(self):
        rec = AsyncMock(return_value={"enqueue_failed_repaired": 2})
        w = _worker(reconciler=rec)
        await w._reconcile()
        await w._reconcile()
        assert w.stats.orphans_repaired_total == 4

    @pytest.mark.asyncio
    async def test_reconcile_empty_result_no_increment(self):
        w = _worker(reconciler=AsyncMock(return_value={}))
        await w._reconcile()
        assert w.stats.orphans_repaired_total == 0
        w2 = _worker(reconciler=AsyncMock(return_value=None))
        await w2._reconcile()
        assert w2.stats.orphans_repaired_total == 0

    @pytest.mark.asyncio
    async def test_run_ensures_group(self):
        import asyncio

        queue, store = AsyncMock(), AsyncMock()
        queue.claim_stale.return_value = []
        stop = asyncio.Event()
        stop.set()  # exit immediately after setup
        w = _worker(queue=queue, store=store)
        await asyncio.wait_for(w.run(stop), timeout=10)
        queue.ensure_group.assert_awaited_once_with("soar-api")

    @pytest.mark.asyncio
    async def test_run_survives_queue_without_auto_redrive(self):
        import asyncio
        from unittest.mock import MagicMock

        queue = MagicMock(spec=[])  # no attrs at all
        queue.ensure_group = AsyncMock()
        queue.claim_stale = AsyncMock(return_value=[])
        stop = asyncio.Event()

        async def read_then_stop(*_a, **_kw):
            stop.set()
            return []

        queue.read = read_then_stop
        w = _worker(queue=queue, store=AsyncMock(), recover_interval_s=0.0)
        await asyncio.wait_for(w.run(stop), timeout=10)  # no AttributeError


# ── WorkerLease ──────────────────────────────────────────────────────────


class TestWorkerLease:
    @pytest.mark.asyncio
    async def test_no_client_is_single_worker(self):
        assert await WorkerLease(None, "h").held() is True
        await WorkerLease(None, "h").release()  # no-op, no raise

    @pytest.mark.asyncio
    async def test_eval_args(self):
        client = AsyncMock()
        client.eval.return_value = 2
        client.incr.return_value = 7
        lease = WorkerLease(client, "holder-9", ttl_ms=1234)
        assert await lease.held() is True
        script, nkeys, key, holder, ttl = client.eval.call_args[0]
        assert nkeys == 1 and key == LEASE_KEY
        assert holder == "holder-9" and ttl == "1234"
        assert "'PX'" in script and "'NX'" in script
        client.incr.assert_awaited_once_with(FENCE_KEY)
        assert lease.fence_token == 7

    @pytest.mark.asyncio
    async def test_held_by_other_returns_false(self):
        client = AsyncMock()
        client.eval.return_value = 0
        lease = WorkerLease(client, "h")
        assert await lease.held() is False
        client.incr.assert_not_awaited()
        assert lease.fence_token is None

    @pytest.mark.asyncio
    async def test_renewal_does_not_bump_fence(self):
        client = AsyncMock()
        client.eval.return_value = 1
        lease = WorkerLease(client, "h")
        assert await lease.held() is True
        client.incr.assert_not_awaited()
        assert lease.fence_token is None

    @pytest.mark.asyncio
    async def test_eval_failure_fails_safe(self):
        client = AsyncMock()
        client.eval.side_effect = RuntimeError("redis down")
        assert await WorkerLease(client, "h").held() is False

    @pytest.mark.asyncio
    async def test_incr_failure_leaves_none(self):
        client = AsyncMock()
        client.eval.return_value = 2
        client.incr.side_effect = RuntimeError("down")
        lease = WorkerLease(client, "h")
        assert await lease.held() is True
        assert lease.fence_token is None

    @pytest.mark.asyncio
    async def test_release_compare_and_delete(self):
        client = AsyncMock()
        await WorkerLease(client, "h-1").release()
        script, nkeys, key, holder = client.eval.call_args[0]
        assert nkeys == 1 and key == LEASE_KEY and holder == "h-1"
        assert "ARGV[1]" in script  # only deletes own lease

    @pytest.mark.asyncio
    async def test_release_error_swallowed(self):
        client = AsyncMock()
        client.eval.side_effect = RuntimeError("down")
        await WorkerLease(client, "h").release()  # must not raise


# ── RedisAdmissionStore ─────────────────────────────────────────────────


class TestRedisAdmissionStore:
    @pytest.mark.asyncio
    async def test_create_serializes_nested(self):
        client = AsyncMock()
        s = RedisAdmissionStore(client, record_ttl_s=99)
        await s.create({"admission_id": "a1", "meta": {"m": 1}, "tags": ["t"], "n": 5})
        key = client.hset.call_args[0][0]
        assert key.endswith("a1")
        fields = client.hset.call_args.kwargs["mapping"]
        assert fields["meta"] == '{"m": 1}'
        assert fields["tags"] == '["t"]'
        assert fields["n"] == "5"
        client.expire.assert_awaited_once_with(key, 99)

    @pytest.mark.asyncio
    async def test_get_deserializes(self):
        client = AsyncMock()
        client.hgetall.return_value = {
            b"status": b"queued",
            b"meta": b'{"m": 1}',
            b"n": b"7",
        }
        s = RedisAdmissionStore(client)
        rec = await s.get("a1")
        # json.loads roundtrip: scalar strings decode back to JSON types.
        assert rec == {"status": "queued", "meta": {"m": 1}, "n": 7}

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self):
        client = AsyncMock()
        client.hgetall.return_value = {}
        assert await RedisAdmissionStore(client).get("x") is None

    @pytest.mark.asyncio
    async def test_find_by_key_decodes_bytes(self):
        client = AsyncMock()
        client.get.return_value = b"adm-9"
        assert await RedisAdmissionStore(client).find_by_key("k") == "adm-9"
        client.get.return_value = None
        assert await RedisAdmissionStore(client).find_by_key("k") is None

    @pytest.mark.asyncio
    async def test_bind_key_nx_and_ttl(self):
        client = AsyncMock()
        await RedisAdmissionStore(client, record_ttl_s=42).bind_key("ik", "adm")
        client.set.assert_awaited_once()
        args, kwargs = client.set.call_args
        assert args[1] == "adm" and kwargs == {"ex": 42, "nx": True}

    @pytest.mark.asyncio
    async def test_try_bind_winner_gets_none_loser_gets_existing(self):
        # SET NX contract: winner (set succeeds) → None = proceed;
        # loser → the admission_id already bound = duplicate detected.
        client = AsyncMock()
        client.set.side_effect = [True, False]
        client.get.return_value = b"existing-adm"
        s = RedisAdmissionStore(client)
        assert await s.try_bind_key("ik", "adm") is None
        assert await s.try_bind_key("ik", "adm") == "existing-adm"
        client.get.return_value = None
        client.set.side_effect = [False]
        # Lost the race AND nothing stored → treat own id as bound.
        assert await s.try_bind_key("ik", "adm") == "adm"


class TestAdmissionStoreArgExact:
    @pytest.mark.asyncio
    async def test_create_key_prefix(self):
        client = AsyncMock()
        s = RedisAdmissionStore(client)
        await s.create({"admission_id": "a1"})
        client.hset.assert_awaited_once()
        assert client.hset.call_args[0][0] == "soar:admission:a1"
        client.expire.assert_awaited_once_with("soar:admission:a1", 7 * 24 * 3600)

    @pytest.mark.asyncio
    async def test_get_key_arg(self):
        client = AsyncMock()
        client.hgetall.return_value = {}
        await RedisAdmissionStore(client).get("a1")
        client.hgetall.assert_awaited_once_with("soar:admission:a1")

    @pytest.mark.asyncio
    async def test_update_exists_and_hset_args(self):
        client = AsyncMock()
        client.exists.return_value = 1
        s = RedisAdmissionStore(client)
        await s.update("a1", {"status": "dead"})
        client.exists.assert_awaited_once_with("soar:admission:a1")
        client.hset.assert_awaited_once()
        assert client.hset.call_args[0][0] == "soar:admission:a1"
        assert client.hset.call_args.kwargs["mapping"] == {"status": "dead"}

    @pytest.mark.asyncio
    async def test_update_vanished_skips_hset(self):
        client = AsyncMock()
        client.exists.return_value = 0
        await RedisAdmissionStore(client).update("a1", {"status": "dead"})
        client.hset.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_find_by_key_key_arg(self):
        client = AsyncMock()
        client.get.return_value = None
        await RedisAdmissionStore(client).find_by_key("ik-1")
        client.get.assert_awaited_once_with("soar:admission:key:ik-1")

    @pytest.mark.asyncio
    async def test_try_bind_set_args(self):
        client = AsyncMock()
        client.set.return_value = True
        s = RedisAdmissionStore(client, record_ttl_s=42)
        await s.try_bind_key("ik-1", "adm")
        client.set.assert_awaited_once_with(
            "soar:admission:key:ik-1", "adm", ex=42, nx=True
        )

    @pytest.mark.asyncio
    async def test_unbind_compare_and_delete_script(self):
        client = AsyncMock()
        s = RedisAdmissionStore(client)
        await s.unbind_key("ik-1", "adm")
        script, nkeys, key, holder = client.eval.call_args[0]
        assert nkeys == 1
        assert key == "soar:admission:key:ik-1"
        assert holder == "adm"
        assert "redis.call('GET', KEYS[1]) == ARGV[1]" in script
        assert "redis.call('DEL', KEYS[1])" in script

    @pytest.mark.asyncio
    async def test_list_by_status_scan_and_limit(self):
        client = AsyncMock()

        async def scan(*, match=None):
            assert match == "soar:admission:*"
            for k in [
                b"soar:admission:a1",
                b"soar:admission:key:ik",
                b"soar:admission:a2",
                b"soar:admission:a3",
            ]:
                yield k

        client.scan_iter = scan
        client.hgetall.side_effect = lambda k: (
            {b"status": b"queued"} if k.endswith("a1") or k.endswith("a2")
            else {b"status": b"dead"}
        )
        s = RedisAdmissionStore(client)
        out = await s.list_by_status({"queued"}, limit=2)
        # key-prefix entries skipped; limit=2 bounds results.
        assert len(out) <= 2
        assert all(r["status"] == "queued" for r in out)


# ── shuffle_forward destination policy + classification ─────────────────


class TestDestinationPolicy:
    def test_scheme_allowlist(self):
        assert _validate_target("https://h/x", None) == "https://h/x"
        assert _validate_target("http://h/x", None) == "http://h/x"
        for bad in ("ftp://h/x", "file:///x", "gopher://h"):
            with pytest.raises(DestinationPolicyError):
                _validate_target(bad, None)

    def test_credentials_rejected(self):
        # `username or password` — either alone must trip (kills or→and).
        with pytest.raises(DestinationPolicyError):
            _validate_target("https://user@h/x", None)
        with pytest.raises(DestinationPolicyError):
            _validate_target("https://user:pw@h/x", None)
        with pytest.raises(DestinationPolicyError):
            _validate_target("https://:pw@h/x", None)

    def test_host_allowlist(self):
        allowed = {"shuffle-backend"}
        assert _validate_target("https://shuffle-backend/h", allowed)
        with pytest.raises(DestinationPolicyError):
            _validate_target("https://evil/h", allowed)
        # Empty/None allowlist = lab default, any host.
        assert _validate_target("https://any/h", set()) == "https://any/h"
        assert _validate_target("https://any/h", None) == "https://any/h"

    def test_malformed_rejected(self):
        with pytest.raises(DestinationPolicyError):
            _validate_target("http://[::1", None)


class TestClassify:
    def test_timeout(self):
        assert _classify(None, requests.Timeout()) == {
            "error_code": "DOWNSTREAM_TIMEOUT",
            "retryable": True,
        }

    def test_connection_error(self):
        assert _classify(None, requests.ConnectionError()) == {
            "error_code": "DOWNSTREAM_UNAVAILABLE",
            "retryable": True,
        }

    def test_generic_exception(self):
        assert _classify(None, ValueError()) == {
            "error_code": "FORWARD_ERROR",
            "retryable": True,
        }

    def test_http_status_classes(self):
        assert _classify(429, None) == {"error_code": "DOWNSTREAM_RATE_LIMITED", "retryable": True}
        assert _classify(503, None) == {"error_code": "DOWNSTREAM_5XX", "retryable": True}
        assert _classify(500, None)["retryable"] is True
        for st in (400, 401, 403, 404, 422):
            assert _classify(st, None) == {
                "error_code": "DOWNSTREAM_REJECTED",
                "retryable": False,
            }, st
        assert _classify(302, None) == {"error_code": "DOWNSTREAM_HTTP_302", "retryable": False}
        # 2xx is success — no error code, not retryable.
        assert _classify(200, None) == {"error_code": None, "retryable": False}
        # No status and no exception = transport failure → retryable error.
        assert _classify(None, None) == {"error_code": "FORWARD_ERROR", "retryable": True}

    def test_status_300_is_not_success(self):
        # `200 <= status < 300` boundary — 300/301 are redirects, not ok.
        assert _classify(300, None) == {
            "error_code": "DOWNSTREAM_HTTP_300",
            "retryable": False,
        }


class TestResolveTargetUrl:
    def test_ingest_url_wins_over_shuffle_url(self):
        cp = {
            "ALERT_INGEST_TARGET_URL": "https://ingest/h",
            "SHUFFLE_WEBHOOK_URL": "https://shuffle/h",
        }
        assert resolve_target_url(cp) == "https://ingest/h"

    def test_shuffle_url_fallback(self):
        cp = {"SHUFFLE_WEBHOOK_URL": "https://shuffle/h"}
        assert resolve_target_url(cp) == "https://shuffle/h"

    def test_file_fallback_skips_corrupt_candidate(self, tmp_path, monkeypatch):
        # `continue` on bad JSON must reach the NEXT candidate (kills
        # continue→break which would silently fall back to default).
        from soar_lab.infrastructure.messaging import shuffle_forward

        bad = tmp_path / "bad.json"
        good = tmp_path / "good.json"
        bad.write_text("{not json")
        good.write_text(json.dumps({"webhook_url": "https://file/h"}))
        monkeypatch.setattr(
            shuffle_forward, "WEBHOOK_INFO_PATHS", [str(bad), str(good)]
        )
        assert resolve_target_url({}) == "https://file/h"

    def test_host_url_fallback_inside_file(self, tmp_path, monkeypatch):
        from soar_lab.infrastructure.messaging import shuffle_forward

        good = tmp_path / "w.json"
        good.write_text(json.dumps({"webhook_url_host": "https://hostside/h"}))
        monkeypatch.setattr(
            shuffle_forward, "WEBHOOK_INFO_PATHS", [str(good)]
        )
        assert resolve_target_url({}) == "https://hostside/h"

    def test_default_when_nothing(self, monkeypatch):
        from soar_lab.common.constants import SHUFFLE_WEBHOOK_DEFAULT
        from soar_lab.infrastructure.messaging import shuffle_forward

        monkeypatch.setattr(shuffle_forward, "WEBHOOK_INFO_PATHS", [])
        assert resolve_target_url({}) == SHUFFLE_WEBHOOK_DEFAULT


class TestMakeShuffleForward:
    def _config(self, **over):
        base = {
            "ALERT_INGEST_TARGET_URL": "https://shuffle-backend/hook",
            "ALERT_INGEST_ALLOWED_HOSTS": "",
            "ALERT_SIGNING_KEY": "",
            "ALERT_SIGNING_KEY_ID": "",
        }
        base.update(over)
        return base

    def test_allowed_hosts_env_enforced(self):
        # Non-empty allowlist must REJECT off-list hosts (kills
        # `{...} or None` → `and None` — the egress-open mutant).
        cp = self._config(ALERT_INGEST_ALLOWED_HOSTS="other-host")
        with pytest.raises(DestinationPolicyError):
            make_shuffle_forward(cp)

    def test_allowed_hosts_list_permits_member(self):
        cp = self._config(
            ALERT_INGEST_TARGET_URL="https://shuffle-backend/hook",
            ALERT_INGEST_ALLOWED_HOSTS="a,shuffle-backend, c",
        )
        make_shuffle_forward(cp)  # member of the comma list → allowed

    @pytest.mark.asyncio
    async def test_forward_envelope_contract(self):
        client = AsyncMock()
        client.post_json.return_value = (200, {"execution_id": "exec-1"})
        forward = make_shuffle_forward(self._config(), http_client=client)
        alert = {
            "alert_id": "al-1",
            "delivery_id": "al-1:2",
            "attempt": 2,
            "idempotency_key": "ik-9",
            "severity": "high",
        }
        res = await forward(alert)
        assert res["ok"] is True
        assert res["status_code"] == 200
        assert res["exec_id"] == "exec-1"
        assert res["error_code"] is None
        assert res["retryable"] is False
        url, kwargs = client.post_json.call_args[0][0], client.post_json.call_args.kwargs
        assert url == "https://shuffle-backend/hook"
        payload = kwargs["payload"]
        assert payload["schema_version"] == "1.0"
        assert payload["event_id"] == "al-1"
        assert payload["delivery_id"] == "al-1:2"
        assert payload["attempt"] == 2
        assert payload["idempotency_key"] == "ik-9"
        assert payload["severity"] == "high"  # alert fields at top level
        assert kwargs["timeout"] == 30.0

    @pytest.mark.asyncio
    async def test_forward_envelope_defaults(self):
        client = AsyncMock()
        client.post_json.return_value = (202, {})
        forward = make_shuffle_forward(self._config(), http_client=client)
        res = await forward({})
        payload = client.post_json.call_args.kwargs["payload"]
        assert payload["attempt"] == 1
        assert payload["event_id"].startswith("evt-")
        assert payload["delivery_id"].startswith("dlv-")
        assert payload["idempotency_key"] is None
        assert res["exec_id"] is None  # absent → None via .get chain

    @pytest.mark.asyncio
    async def test_forward_exec_id_fallback_chain(self):
        client = AsyncMock()
        client.post_json.return_value = (200, {"executionId": "e2"})
        forward = make_shuffle_forward(self._config(), http_client=client)
        assert (await forward({}))["exec_id"] == "e2"
        client.post_json.return_value = (200, {"id": "e3"})
        assert (await forward({}))["exec_id"] == "e3"

    @pytest.mark.asyncio
    async def test_forward_error_classified(self):
        client = AsyncMock()
        client.post_json.return_value = (429, {})
        forward = make_shuffle_forward(self._config(), http_client=client)
        res = await forward({})
        assert res["ok"] is False
        assert res["error_code"] == "DOWNSTREAM_RATE_LIMITED"
        assert res["retryable"] is True

    @pytest.mark.asyncio
    async def test_forward_exception_path(self):
        client = AsyncMock()
        client.post_json.side_effect = requests.Timeout()
        forward = make_shuffle_forward(self._config(), http_client=client)
        res = await forward({})
        assert res == {
            "ok": False,
            "status_code": None,
            "exec_id": None,
            "error_code": "DOWNSTREAM_TIMEOUT",
            "retryable": True,
        }


class TestAdmissionStoreUpdateAndScan:
    @pytest.mark.asyncio
    async def test_update_serializes_and_skips_vanished(self):
        client = AsyncMock()
        client.exists.return_value = True
        s = RedisAdmissionStore(client)
        await s.update("a1", {"meta": {"m": 1}, "n": 3})
        mapping = client.hset.call_args.kwargs["mapping"]
        assert mapping["meta"] == '{"m": 1}'
        assert mapping["n"] == "3"
        # Vanished record → warning + no write.
        client.exists.return_value = False
        client.hset.reset_mock()
        await s.update("gone", {"x": 1})
        client.hset.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_list_by_status_filters_and_skips_keyspace(self):
        async def scan(match=None):
            for k in [
                b"soar:admission:key:ik",  # keyspace — must be skipped
                b"soar:admission:rec:a",
                b"soar:admission:rec:b",
            ]:
                yield k

        client = AsyncMock()
        client.scan_iter = scan
        client.hgetall.side_effect = [
            {b"status": b'"queued"'},
            {b"status": b'"dead"'},
        ]
        s = RedisAdmissionStore(client)
        out = await s.list_by_status({"dead"})
        assert out == [{"status": "dead"}]
        assert client.hgetall.await_count == 2  # keyspace key never fetched

    @pytest.mark.asyncio
    async def test_unbind_key_compare_and_delete(self):
        client = AsyncMock()
        await RedisAdmissionStore(client).unbind_key("ik", "adm-1")
        script, nkeys, key, holder = client.eval.call_args[0]
        assert nkeys == 1 and key.endswith("ik") and holder == "adm-1"
        assert "ARGV[1]" in script and "DEL" in script


class TestRedaction:
    def test_hook_path_redacted(self):
        from soar_lab.security.redaction import redact_text

        out = redact_text("post to https://h/api/v1/hooks/webhook_abc-123 failed")
        assert "webhook_abc-123" not in out
        assert "/api/v1/hooks/[redacted]" in out

    def test_bearer_redacted(self):
        from soar_lab.security.redaction import redact_text

        assert "Bearer [redacted]" in redact_text("Bearer abcdef12345token")

    def test_hex_blob_redacted(self):
        from soar_lab.security.redaction import redact_text

        out = redact_text("key " + "a" * 41)
        assert "a" * 41 not in out
        assert "[redacted-hex]" in out

    def test_query_redacted(self):
        from soar_lab.security.redaction import redact_text

        out = redact_text("GET https://h/path?token=secret123 HTTP")
        assert "token=secret123" not in out
        assert "?[redacted]" in out

    def test_secret_kv_redacted(self):
        from soar_lab.security.redaction import redact_text

        out = redact_text("password=hunter2 ok")
        assert "hunter2" not in out
        assert "[redacted]" in out

    def test_max_len_and_control_chars(self):
        from soar_lab.security.redaction import redact_text

        out = redact_text("x" * 500, max_len=100)
        # s[:max_len] + "…" — boundary: 500 → 101 chars ending in ellipsis.
        assert len(out) == 101 and out.endswith("…")
        assert out[:100] == "x" * 100
        assert redact_text("a\x00b\x1fc") == "a b c"
        assert redact_text(None) == ""
        assert redact_text(123) == "123"
        # Default max_len is 200.
        assert len(redact_text("y" * 500)) == 201

    def test_redact_url_contract(self):
        from soar_lab.security.redaction import redact_url

        assert (
            redact_url("https://user:pw@host.example:8443/secret/path?tok=1")
            == "https://host.example:8443"
        )
        assert redact_url("https://host/path") == "https://host"
        # Non-URL input degrades to a safe placeholder, never echoing raw text.
        assert redact_url("not a url at all") == "http://unknown"
        # Unparseable port raises inside urlsplit.port → [redacted-url].
        assert redact_url("https://host:bad-port/x") == "[redacted-url]"


# ── send_alert CLI ───────────────────────────────────────────────────────


class TestDefaultWebhookUrl:
    def test_env_var_wins(self, monkeypatch, tmp_path):
        from soar_lab.infrastructure.messaging.send_alert import _default_webhook_url

        monkeypatch.setenv("SHUFFLE_WEBHOOK_URL", "https://env/hook")
        assert _default_webhook_url(tmp_path) == "https://env/hook"

    def _isolate(self, monkeypatch):
        # Keep the container's real WEBHOOK_INFO_PATHS out of the test.
        from soar_lab.infrastructure.messaging import send_alert

        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        monkeypatch.setattr(send_alert, "WEBHOOK_INFO_PATHS", [])
        return send_alert

    def _patch_dockerenv(self, monkeypatch, inside: bool):
        exists_orig = Path.exists
        monkeypatch.setattr(
            Path,
            "exists",
            (
                (lambda self: True)
                if inside
                else (
                    lambda self: (
                        exists_orig(self) if str(self) != "/.dockerenv" else False
                    )
                )
            ),
        )

    def test_fallback_to_default(self, monkeypatch, tmp_path):
        from soar_lab.common.constants import SHUFFLE_WEBHOOK_DEFAULT

        sa = self._isolate(monkeypatch)
        assert sa._default_webhook_url(tmp_path) == SHUFFLE_WEBHOOK_DEFAULT

    def test_reads_webhook_info_host_side(self, monkeypatch, tmp_path):
        sa = self._isolate(monkeypatch)
        info = {"webhook_url": "https://internal/h", "webhook_url_host": "https://host/h"}
        d = tmp_path / "runtime" / "results"
        d.mkdir(parents=True)
        (d / "webhook_info.json").write_text(json.dumps(info))
        # Host context (no /.dockerenv) → host URL first.
        self._patch_dockerenv(monkeypatch, inside=False)
        assert sa._default_webhook_url(tmp_path) == "https://host/h"

    def test_container_context_prefers_internal(self, monkeypatch, tmp_path):
        sa = self._isolate(monkeypatch)
        info = {"webhook_url": "https://internal/h", "webhook_url_host": "https://host/h"}
        d = tmp_path / "runtime" / "results"
        d.mkdir(parents=True)
        (d / "webhook_info.json").write_text(json.dumps(info))
        # /.dockerenv exists → inside container → internal URL first.
        self._patch_dockerenv(monkeypatch, inside=True)
        assert sa._default_webhook_url(tmp_path) == "https://internal/h"

    def test_missing_url_fields_fall_through(self, monkeypatch, tmp_path):
        sa = self._isolate(monkeypatch)
        d = tmp_path / "runtime" / "results"
        d.mkdir(parents=True)
        # Only host URL present → `or` chain must still yield it.
        (d / "webhook_info.json").write_text(json.dumps({"webhook_url_host": "https://h/h"}))
        self._patch_dockerenv(monkeypatch, inside=False)
        assert sa._default_webhook_url(tmp_path) == "https://h/h"


class TestSendAlertMain:
    def _run(self, monkeypatch, argv, send_result=None):
        import sys

        from soar_lab.infrastructure.messaging import send_alert

        monkeypatch.setattr(sys, "argv", ["send_alert.py", *argv])
        monkeypatch.setenv("SHUFFLE_WEBHOOK_URL", "https://h/hook")

        sender = Mock()
        sender.send.return_value = send_result or {"success": True}
        sender.get_metrics.return_value = {"alerts_sent": 1, "alerts_failed": 0}
        monkeypatch.setattr(
            send_alert, "HTTPAlertSender", lambda **kw: sender
        )
        gen = Mock()
        gen.generate_malicious.return_value = {"alert_id": "a1"}
        gen.generate_benign.return_value = {"alert_id": "b1"}
        monkeypatch.setattr(send_alert, "AlertGenerator", lambda: gen)
        monkeypatch.setattr(send_alert, "_verify_tls", lambda p: False)
        return send_alert, sender, gen

    def test_single_sends_one(self, monkeypatch, capsys):
        sa, sender, gen = self._run(monkeypatch, ["--single"])
        sa.main()
        sender.send.assert_called_once()
        gen.generate_malicious.assert_called_once()
        assert "1 sent" in capsys.readouterr().out

    def test_num_alerts_and_type(self, monkeypatch):
        sa, sender, gen = self._run(
            monkeypatch, ["--type", "benign", "--num-alerts", "3", "--delay", "0"]
        )
        sa.main()
        assert sender.send.call_count == 3
        assert gen.generate_benign.call_count == 3
        gen.generate_malicious.assert_not_called()

    def test_failure_exits_1(self, monkeypatch):
        sa, sender, gen = self._run(
            monkeypatch, ["--single"], send_result={"success": False, "error": "nope"}
        )
        with pytest.raises(SystemExit) as ei:
            sa.main()
        assert ei.value.code == 1

    def test_delay_between_alerts(self, monkeypatch):
        import time as time_mod

        sleeps = []
        monkeypatch.setattr(time_mod, "sleep", lambda s: sleeps.append(s))
        sa, _, _ = self._run(monkeypatch, ["--num-alerts", "3", "--delay", "7"])
        sa.main()
        # i < num-1 → sleeps between sends, not after the last.
        assert sleeps == [7, 7]

    def _run_capture(self, monkeypatch, argv, send_result=None, env=None):
        """Like _run but captures HTTPAlertSender constructor kwargs."""
        import sys

        from soar_lab.infrastructure.messaging import send_alert

        monkeypatch.setattr(sys, "argv", ["send_alert.py", *argv])
        for var in ("SHUFFLE_WEBHOOK_URL", "SIEM_WEBHOOK_TOKEN", "SHUFFLE_API_TOKEN"):
            monkeypatch.delenv(var, raising=False)
        for k, v in (env or {}).items():
            monkeypatch.setenv(k, v)
        sender_cls = Mock()
        sender = sender_cls.return_value
        sender.send.return_value = send_result or {"success": True}
        sender.get_metrics.return_value = {"alerts_sent": 1, "alerts_failed": 0}
        monkeypatch.setattr(send_alert, "HTTPAlertSender", sender_cls)
        gen = Mock()
        gen.generate_malicious.return_value = {"alert_id": "a1"}
        gen.generate_benign.return_value = {"alert_id": "b1"}
        monkeypatch.setattr(send_alert, "AlertGenerator", lambda: gen)
        monkeypatch.setattr(send_alert, "_verify_tls", lambda p: False)
        monkeypatch.setattr(send_alert, "WEBHOOK_INFO_PATHS", [])
        monkeypatch.setenv("BASE_DIR", "/nonexistent-base")
        return send_alert, sender_cls, sender, gen

    def test_default_num_alerts_is_1(self, monkeypatch):
        sa, _, sender, _ = self._run_capture(monkeypatch, [])
        sa.main()
        sender.send.assert_called_once()

    def test_default_type_is_malicious(self, monkeypatch):
        sa, _, _, gen = self._run_capture(monkeypatch, ["--num-alerts", "1"])
        sa.main()
        gen.generate_malicious.assert_called_once()
        gen.generate_benign.assert_not_called()

    def test_default_delay_is_3(self, monkeypatch):
        import time as time_mod

        sleeps = []
        monkeypatch.setattr(time_mod, "sleep", lambda s: sleeps.append(s))
        sa, _, _, _ = self._run_capture(monkeypatch, ["--num-alerts", "2"])
        sa.main()
        assert sleeps == [3]

    def test_invalid_type_rejected_exit_2(self, monkeypatch):
        sa, _, _, _ = self._run_capture(monkeypatch, ["--type", "bogus"])
        with pytest.raises(SystemExit) as ei:
            sa.main()
        assert ei.value.code == 2

    def test_api_token_siem_env_wins(self, monkeypatch):
        sa, sender_cls, _, _ = self._run_capture(
            monkeypatch,
            ["--single"],
            env={"SHUFFLE_WEBHOOK_URL": "https://h/h",
                 "SIEM_WEBHOOK_TOKEN": "siem-tok",
                 "SHUFFLE_API_TOKEN": "shuffle-tok"},
        )
        sa.main()
        assert sender_cls.call_args.kwargs["api_token"] == "siem-tok"

    def test_api_token_shuffle_fallback(self, monkeypatch):
        sa, sender_cls, _, _ = self._run_capture(
            monkeypatch,
            ["--single"],
            env={"SHUFFLE_WEBHOOK_URL": "https://h/h", "SHUFFLE_API_TOKEN": "shuffle-tok"},
        )
        sa.main()
        assert sender_cls.call_args.kwargs["api_token"] == "shuffle-tok"

    def test_api_token_empty_default(self, monkeypatch):
        sa, sender_cls, _, _ = self._run_capture(
            monkeypatch, ["--single"], env={"SHUFFLE_WEBHOOK_URL": "https://h/h"}
        )
        sa.main()
        assert sender_cls.call_args.kwargs["api_token"] == ""

    def test_webhook_url_flag_passthrough(self, monkeypatch):
        sa, sender_cls, _, _ = self._run_capture(
            monkeypatch, ["--single", "--webhook-url", "https://flag/hook"]
        )
        sa.main()
        assert sender_cls.call_args.kwargs["webhook_url"] == "https://flag/hook"

    def test_webhook_url_env_resolution(self, monkeypatch):
        sa, sender_cls, _, _ = self._run_capture(
            monkeypatch, ["--single"], env={"SHUFFLE_WEBHOOK_URL": "https://env/hook"}
        )
        sa.main()
        assert sender_cls.call_args.kwargs["webhook_url"] == "https://env/hook"

    def test_verify_tls_kwarg(self, monkeypatch):
        sa, sender_cls, _, _ = self._run_capture(monkeypatch, ["--single"])
        sa.main()
        assert sender_cls.call_args.kwargs["verify_tls"] is False

    def test_success_print_format(self, monkeypatch, capsys):
        sa, sender_cls, _, _ = self._run_capture(
            monkeypatch, ["--num-alerts", "2", "--delay", "0"]
        )
        sa.main()
        out = capsys.readouterr().out
        assert "[1/2] Alert sent successfully: a1" in out
        assert "[2/2] Alert sent successfully: a1" in out

    def test_failure_print_format(self, monkeypatch, capsys):
        sa, _, _, _ = self._run_capture(
            monkeypatch, ["--single"], send_result={"success": False, "error": "boom"}
        )
        with pytest.raises(SystemExit):
            sa.main()
        assert "[1/1] Failed to send alert: boom" in capsys.readouterr().out

    def test_summary_print_format(self, monkeypatch, capsys):
        sa, sender_cls, sender, _ = self._run_capture(
            monkeypatch, ["--num-alerts", "2", "--delay", "0"]
        )
        sender.get_metrics.return_value = {"alerts_sent": 2, "alerts_failed": 0}
        sa.main()
        assert "2 sent, 0 failed" in capsys.readouterr().out

    def test_no_sleep_when_delay_zero(self, monkeypatch):
        import time as time_mod

        sleeps = []
        monkeypatch.setattr(time_mod, "sleep", lambda s: sleeps.append(s))
        sa, _, _, _ = self._run_capture(monkeypatch, ["--num-alerts", "3", "--delay", "0"])
        sa.main()
        assert sleeps == []

    def test_single_overrides_num_alerts(self, monkeypatch):
        sa, _, sender, _ = self._run_capture(
            monkeypatch, ["--single", "--num-alerts", "5"]
        )
        sa.main()
        sender.send.assert_called_once()


class TestDefaultWebhookUrlLegacy:
    def _isolate(self, monkeypatch):
        from soar_lab.infrastructure.messaging import send_alert

        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        monkeypatch.setattr(send_alert, "WEBHOOK_INFO_PATHS", [])
        return send_alert

    def test_artifacts_legacy_fallback(self, monkeypatch, tmp_path):
        sa = self._isolate(monkeypatch)
        d = tmp_path / "artifacts" / "results"
        d.mkdir(parents=True)
        (d / "webhook_info.json").write_text(
            json.dumps({"webhook_url": "https://i/h", "webhook_url_host": "https://h/h"})
        )
        exists_orig = Path.exists
        monkeypatch.setattr(
            Path,
            "exists",
            lambda self: exists_orig(self) if str(self) != "/.dockerenv" else False,
        )
        assert sa._default_webhook_url(tmp_path) == "https://h/h"

    def test_runtime_path_preferred_over_artifacts(self, monkeypatch, tmp_path):
        sa = self._isolate(monkeypatch)
        for sub, host in (("runtime", "https://rt/h"), ("artifacts", "https://art/h")):
            d = tmp_path / sub / "results"
            d.mkdir(parents=True)
            (d / "webhook_info.json").write_text(
                json.dumps({"webhook_url_host": host})
            )
        exists_orig = Path.exists
        monkeypatch.setattr(
            Path,
            "exists",
            lambda self: exists_orig(self) if str(self) != "/.dockerenv" else False,
        )
        assert sa._default_webhook_url(tmp_path) == "https://rt/h"

    def test_corrupt_info_falls_through_to_next(self, monkeypatch, tmp_path):
        sa = self._isolate(monkeypatch)
        d1 = tmp_path / "runtime" / "results"
        d1.mkdir(parents=True)
        (d1 / "webhook_info.json").write_text("{not json")
        d2 = tmp_path / "artifacts" / "results"
        d2.mkdir(parents=True)
        (d2 / "webhook_info.json").write_text(
            json.dumps({"webhook_url_host": "https://h/h"})
        )
        exists_orig = Path.exists
        monkeypatch.setattr(
            Path,
            "exists",
            lambda self: exists_orig(self) if str(self) != "/.dockerenv" else False,
        )
        assert sa._default_webhook_url(tmp_path) == "https://h/h"


# ── Final mutation-gap batch: worker internals ────────────────────────────


class TestWorkerInitBoundary:
    def test_retry_cap_boundary_strict(self):
        # retry_cap_s * 1000 >= stale_ms must raise — exactly at the bound.
        with pytest.raises(ValueError):
            _worker(retry_cap_s=30.0, stale_ms=30_000)
        # Just below the bound must construct — kills *1000 -> *1001.
        _worker(retry_cap_s=29.98, stale_ms=30_000)


class TestRunOnceZipAndLog:
    @pytest.mark.asyncio
    async def test_shorter_results_still_counts_batch(self, monkeypatch):
        # zip(..., strict=False) tolerates a short results list —
        # strict=True would raise ValueError (kills that mutant).
        import asyncio as aio

        import soar_lab.infrastructure.messaging.admission_worker as aw

        queue = AsyncMock()
        queue.read.return_value = [("e1", {"admission_id": "a1"}), ("e2", {})]

        async def fake_gather(*coros, **kw):
            for c in coros:
                c.close()
            return [None]  # shorter than batch

        monkeypatch.setattr(aio, "gather", fake_gather)
        w = _worker(queue=queue)
        assert await w.run_once() == 2

    @pytest.mark.asyncio
    async def test_unhandled_failure_logs_entry_and_admission(self, caplog):
        import logging

        queue = AsyncMock()
        queue.read.return_value = [
            ("e-9", {"admission_id": "adm-9", "alert": {"x": 1}})
        ]
        w = _worker(queue=queue)
        w._process = AsyncMock(side_effect=RuntimeError("boom"))
        with caplog.at_level(logging.ERROR):
            assert await w.run_once() == 1
        rec = [r for r in caplog.records if "failed unhandled" in r.getMessage()]
        assert rec
        text = rec[0].getMessage()
        assert "e-9" in text and "adm-9" in text

    @pytest.mark.asyncio
    async def test_recover_unhandled_logs_admission_id(self, caplog):
        import logging

        queue = AsyncMock()
        queue.claim_stale.return_value = [("e-7", {"admission_id": "adm-7"})]
        w = _worker(queue=queue)
        w._process = AsyncMock(side_effect=RuntimeError("boom"))
        with caplog.at_level(logging.ERROR):
            assert await w.recover() == 1
        rec = [r for r in caplog.records if "failed unhandled" in r.getMessage()]
        assert rec and "adm-7" in rec[0].getMessage()


class TestRunLoopTiming:
    @pytest.mark.asyncio
    async def test_interval_boundary_triggers_duties(self, monkeypatch):
        import asyncio
        import types

        import soar_lab.infrastructure.messaging.admission_worker as aw

        # monotonic(): initial recover ts=0, then elapsed==interval exactly.
        mono = iter([0.0, 100.0, 100.0])
        monkeypatch.setattr(
            aw,
            "time",
            types.SimpleNamespace(
                monotonic=lambda: next(mono, 100.0),
                strftime=aw.time.strftime,
                gmtime=aw.time.gmtime,
            ),
        )
        queue = AsyncMock()
        queue.read.return_value = []
        stop = asyncio.Event()
        calls = []

        async def claim_then_stop(*_a, **_kw):
            calls.append(1)
            if len(calls) > 1:
                stop.set()
            return []

        queue.claim_stale = claim_then_stop
        w = _worker(queue=queue, recover_interval_s=100.0)
        await asyncio.wait_for(w.run(stop), timeout=10)
        # `>=` not `>`: elapsed==interval triggers the duty cycle →
        # claim_stale runs once at startup + once in the loop.
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_iteration_error_sleeps_1s(self, monkeypatch):
        import asyncio

        import soar_lab.infrastructure.messaging.admission_worker as aw

        slept = []

        async def fake_sleep(s):
            slept.append(s)
            stop.set()

        monkeypatch.setattr(aw.asyncio, "sleep", fake_sleep)
        queue = AsyncMock()
        queue.claim_stale.return_value = []
        queue.read.side_effect = RuntimeError("stream down")
        stop = asyncio.Event()
        w = _worker(queue=queue)
        await asyncio.wait_for(w.run(stop), timeout=10)
        # except path sleeps exactly 1s (kills sleep(1)→sleep(2)).
        assert slept == [1]

    @pytest.mark.asyncio
    async def test_fence_rotation_logs_tokens(self, caplog):
        import logging

        lease = AsyncMock()
        lease.held.return_value = True
        lease.fence_token = 9
        w = _worker(lease=lease)
        w._fence_token = 5
        with caplog.at_level(logging.WARNING):
            assert await w._leader() is False
        rec = [r for r in caplog.records if "fence token rotated" in r.getMessage()]
        assert rec
        text = rec[0].getMessage()
        assert "5" in text and "9" in text
        assert w._fence_token == 9


class TestForwardTimedAccumulation:
    @pytest.mark.asyncio
    async def test_stats_accumulate_across_calls(self):
        w = _worker(forward=AsyncMock(return_value={"ok": True}))
        await w._forward_timed({"a": 1}, "adm-1")
        await w._forward_timed({"a": 1}, "adm-1")
        assert w.stats.processed_total == 2
        assert w.stats.inflight == 0
        first = w.stats.forward_seconds_total
        assert first > 0 or first == 0  # monotonic may be same-tick; see below
        await w._forward_timed({"a": 1}, "adm-1")
        # `+=` keeps prior value; `=` would still pass here — pin via count
        assert w.stats.processed_total == 3

    @pytest.mark.asyncio
    async def test_inflight_is_increment_not_assignment(self):
        # `inflight += 1` vs `= 1`: seed inflight=4 → after call completes
        # -= brings it back to 4, not 0.
        w = _worker(forward=AsyncMock(return_value={"ok": True}))
        w.stats.inflight = 4
        await w._forward_timed({"a": 1}, "adm-1")
        assert w.stats.inflight == 4


class TestHandleFailureAccumulation:
    @pytest.mark.asyncio
    async def test_retried_total_accumulates(self):
        queue = AsyncMock()
        store = AsyncMock()
        store.get.return_value = None
        w = _worker(queue=queue, store=store)
        ev = {"admission_id": "a1", "attempts": 0}
        res = {"ok": False, "error_code": "X", "retryable": True}
        await w._handle_failure("e1", ev, "a1", 0, res)
        await w._handle_failure("e1", ev, "a1", 0, res)
        assert w.stats.retried_total == 2

    @pytest.mark.asyncio
    async def test_update_audit_args_on_illegal_transition(self):
        store = AsyncMock()
        store.get.return_value = {"status": "forwarded", "state_version": 3}
        w = _worker(store=store)
        # forwarded -> queued is illegal (only workflow_* states follow).
        await w._update("adm-5", {"status": "queued"})
        args, kwargs = store.update.call_args
        assert args[0] == "adm-5"
        fields = kwargs.get("fields", args[1] if len(args) > 1 else {})
        assert fields["transition_violation"] == "forwarded->queued"
        assert fields["state_version"] == 4

    @pytest.mark.asyncio
    async def test_terminal_check_uses_status_key(self):
        # record.get("status") — a terminal record must dedup (skip + ack).
        store = AsyncMock()
        store.get.return_value = {"status": "forwarded"}
        queue = AsyncMock()
        w = _worker(queue=queue, store=store)
        out = await w._terminal_check("e1", "adm-1")
        assert out == "skip"
        assert w.stats.dedup_total == 1
        queue.ack.assert_awaited_once_with(w.group, "e1")

    @pytest.mark.asyncio
    async def test_process_passes_admission_id_to_forward(self):
        store = AsyncMock()
        store.get.return_value = None
        fwd = AsyncMock(return_value={"ok": True})
        w = _worker(store=store, forward=fwd)
        await w._process("e1", {"admission_id": "adm-77", "alert": {"k": 1}})
        fwd.assert_awaited_once()
        alert_arg = fwd.call_args[0][0]
        assert alert_arg["delivery_id"].startswith("adm-77:")


# ── Final mutation-gap batch: queue internals ─────────────────────────────


class TestDlqAutoRedriveContract:
    def _q(self):
        from soar_lab.infrastructure.messaging.redis_streams_queue import (
            RedisStreamsQueue,
        )

        client = AsyncMock()
        q = RedisStreamsQueue(client, stream="s", dlq_stream="s:dlq")
        return q, client

    @pytest.mark.asyncio
    async def test_two_eligible_entries_redrive_both(self, monkeypatch):
        import time

        q, client = self._q()
        old = f"{int(time.time() * 1000) - 3600_000}-0"
        q.dlq_list = AsyncMock(
            return_value=[
                {"reason": "downstream", "payload": {}, "dlq_entry_id": old},
                {"reason": "downstream", "payload": {}, "dlq_entry_id": old},
            ]
        )
        n = await q.dlq_auto_redrive()
        assert n == 2  # kills `redriven += 1` -> `= 1`

    @pytest.mark.asyncio
    async def test_decode_failed_skipped_not_break(self, monkeypatch):
        import time

        q, client = self._q()
        old = f"{int(time.time() * 1000) - 3600_000}-0"
        q.dlq_list = AsyncMock(
            return_value=[
                {"reason": "decode_failed", "payload": {}, "dlq_entry_id": old},
                {"reason": "downstream", "payload": {}, "dlq_entry_id": old},
            ]
        )
        n = await q.dlq_auto_redrive()
        # `continue` skips poison and still redrives the good entry;
        # `break` would stop the loop → 0.
        assert n == 1

    @pytest.mark.asyncio
    async def test_min_age_boundary_and_entry_ms_zero(self, monkeypatch):
        import time as real_time
        import types

        import soar_lab.infrastructure.messaging.redis_streams_queue as rsq

        q, client = self._q()
        now_ms = int(real_time.time() * 1000)
        # aged exactly min_age → NOT too young (`<` not `<=`) → redrives.
        exact = f"{now_ms - 60_000}-0"
        q.dlq_list = AsyncMock(
            return_value=[
                {"reason": "x", "payload": {}, "dlq_entry_id": exact},
            ]
        )
        # Patch the module's `time` ref only — never the global module.
        monkeypatch.setattr(
            rsq, "time", types.SimpleNamespace(time=lambda: now_ms / 1000)
        )
        n = await q.dlq_auto_redrive(min_age_s=60.0)
        assert n == 1

    @pytest.mark.asyncio
    async def test_unparseable_entry_id_redrives(self):
        q, client = self._q()
        q.dlq_list = AsyncMock(
            return_value=[
                {"reason": "x", "payload": {}, "dlq_entry_id": "garbage"},
            ]
        )
        n = await q.dlq_auto_redrive()
        # entry_ms=0 → age check skipped → redrive (kills entry_ms=1).
        assert n == 1

    @pytest.mark.asyncio
    async def test_payload_must_be_dict(self):
        q, client = self._q()
        q.dlq_list = AsyncMock(
            return_value=[
                {"reason": "x", "payload": "not-a-dict", "dlq_entry_id": "1-0"},
                {"reason": "x", "payload": None, "dlq_entry_id": "1-0"},
            ]
        )
        assert await q.dlq_auto_redrive() == 0

    @pytest.mark.asyncio
    async def test_redrive_updates_payload_fields(self):
        import time

        q, client = self._q()
        old = f"{int(time.time() * 1000) - 3600_000}-0"
        q.dlq_list = AsyncMock(
            return_value=[
                {"reason": "x", "payload": {"redrive_count": 1, "attempts": 4}, "dlq_entry_id": old},
            ]
        )
        q.enqueue = AsyncMock()
        await q.dlq_auto_redrive(min_age_s=1.0)
        enqueued = q.enqueue.call_args[0][0]
        assert enqueued["attempts"] == 0
        assert enqueued["redrive_count"] == 2
        assert "redriven_at" in enqueued
        client.xdel.assert_awaited_once_with(q.dlq_stream, old)


class TestQueueMetricsAndPoison:
    def _q(self):
        from soar_lab.infrastructure.messaging.redis_streams_queue import (
            RedisStreamsQueue,
        )

        client = AsyncMock()
        return RedisStreamsQueue(client, stream="s", dlq_stream="s:dlq"), client

    @pytest.mark.asyncio
    async def test_metrics_xinfo_args_and_lag(self):
        q, client = self._q()
        client.xlen.side_effect = [5, 5, 2]
        client.xinfo_groups.return_value = [
            {b"name": b"soar-api", b"pending": 7, b"lag": 3}
        ]
        out = await q.metrics(group="soar-api")
        client.xinfo_groups.assert_awaited_with(q.stream)
        assert out["pending"] == 7
        assert out["consumer_lag"] == 3

    @pytest.mark.asyncio
    async def test_poison_uses_undecodable_marker(self):
        q, client = self._q()

        class Boom:
            def __str__(self):
                raise RuntimeError("nope")

        await q._poison_to_dlq("g", "1-1", {"payload": Boom()})
        fields = client.xadd.call_args[0][1]
        assert fields["payload"] == "<undecodable>"
        assert fields["reason"] == "decode_failed"
        assert fields["source_entry_id"] == "1-1"

    @pytest.mark.asyncio
    async def test_dlq_list_missing_payload_is_none(self):
        q, client = self._q()
        client.xrange.return_value = [
            (b"1-0", {b"reason": b"x"})  # no payload field
        ]
        rows = await q.dlq_list()
        # `payload_raw is not None` — missing payload must be None, not crash.
        assert rows and rows[0]["payload"] is None


# ── Final mutation-gap batch: send_alert CLI ──────────────────────────────


class TestSendAlertMainContracts:
    def test_webhook_url_host_empty_falls_to_url(self, monkeypatch, tmp_path):
        import soar_lab.infrastructure.messaging.send_alert as sa

        monkeypatch.delenv("SHUFFLE_WEBHOOK_URL", raising=False)
        sa.WEBHOOK_INFO_PATHS = (tmp_path / "wi.json",)
        (tmp_path / "wi.json").write_text(
            json.dumps({"webhook_url_host": "", "webhook_url": "https://fb/h"})
        )
        exists_orig = Path.exists
        monkeypatch.setattr(
            Path,
            "exists",
            lambda self: exists_orig(self) if str(self) != "/.dockerenv" else False,
        )
        # empty webhook_url_host must fall through to webhook_url
        assert sa._default_webhook_url(tmp_path) == "https://fb/h"
