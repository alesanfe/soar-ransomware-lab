#!/usr/bin/env python3
"""Unit tests for RedisStreamsQueue — Redis client fully mocked.

Covers enqueue/read/ack/DLQ lifecycle (QUEUE-001/002/004), consumer
metrics, and the poison-message path (undecodable entries must not sit
pending forever). No Redis server needed.
"""

import json
import time
from unittest.mock import AsyncMock

import pytest

from soar_lab.infrastructure.messaging.redis_streams_queue import (
    RedisStreamsQueue,
)


@pytest.fixture
def client():
    c = AsyncMock()
    c.xreadgroup.return_value = []
    c.xautoclaim.return_value = ("0-0", [], [])
    c.xrange.return_value = []
    return c


@pytest.fixture
def queue(client):
    return RedisStreamsQueue(client)


class TestEnqueue:
    async def test_enqueue_xadds_with_bounded_maxlen(self, queue, client):
        client.xadd.return_value = "1-1"
        eid = await queue.enqueue({"a": 1})
        assert eid == "1-1"
        args, kwargs = client.xadd.await_args
        assert args[0] == "soar:admissions"
        assert json.loads(kwargs["maxlen"] and args[1]["payload"]) == {"a": 1}
        assert kwargs["maxlen"] == 100_000
        assert kwargs["approximate"] is True


class TestRead:
    async def test_read_decodes_entries(self, queue, client):
        client.xreadgroup.return_value = [("soar:admissions", [("2-1", {b"payload": b'{"x":1}'})])]
        rows = await queue.read("g", "c", count=5, block_ms=100)
        assert rows == [("2-1", {"x": 1})]

    async def test_read_creates_group_first(self, queue, client):
        client.xgroup_create.side_effect = Exception("BUSYGROUP exists")
        await queue.read("g", "c", count=1, block_ms=0)
        client.xgroup_create.assert_awaited_once()

    async def test_group_create_non_busy_error_propagates(self, queue, client):
        client.xgroup_create.side_effect = Exception("NOREPLICAS")
        with pytest.raises(Exception, match="NOREPLICAS"):
            await queue.ensure_group("g")

    async def test_poison_entry_dlq_and_ack(self, queue, client):
        client.xreadgroup.return_value = [
            ("soar:admissions", [("3-1", {b"payload": b"not-json{"})])
        ]
        rows = await queue.read("g", "c", count=1, block_ms=0)
        assert rows == []
        # Poison moved to DLQ stream with decode_failed reason, then acked.
        dlq_call = client.xadd.await_args
        assert dlq_call.args[0] == "soar:admissions:dlq"
        assert dlq_call.args[1]["reason"] == "decode_failed"
        client.xack.assert_awaited_once_with("soar:admissions", "g", "3-1")


class TestClaimStale:
    async def test_claim_stale_returns_decoded(self, queue, client):
        client.xautoclaim.return_value = (
            "0-0",
            [("4-1", {b"payload": b'{"y":2}'})],
            [],
        )
        rows = await queue.claim_stale("g", "c", min_idle_ms=1000)
        assert rows == [("4-1", {"y": 2})]

    async def test_claim_stale_autoclaim_failure_returns_empty(self, queue, client):
        client.xautoclaim.side_effect = Exception("xpending error")
        assert await queue.claim_stale("g", "c", min_idle_ms=1) == []

    async def test_claim_stale_poison_goes_to_dlq(self, queue, client):
        client.xautoclaim.return_value = (
            "0-0",
            [("4-2", {b"payload": b"broken["})],
            [],
        )
        rows = await queue.claim_stale("g", "c", min_idle_ms=1)
        assert rows == []
        assert client.xadd.await_args.args[0] == "soar:admissions:dlq"


class TestAckAndDeadLetter:
    async def test_ack(self, queue, client):
        await queue.ack("g", "5-1")
        client.xack.assert_awaited_once_with("soar:admissions", "g", "5-1")

    async def test_dead_letter_writes_dlq_with_reason(self, queue, client):
        await queue.dead_letter({"a": 1}, "x" * 600)
        args, _ = client.xadd.await_args
        assert args[0] == "soar:admissions:dlq"
        assert len(args[1]["reason"]) == 512


class TestDepthAndDlqLifecycle:
    async def test_depth(self, queue, client):
        # depth() is real backlog = pending + lag across groups (XINFO),
        # not raw XLEN (which counts processed entries retained by maxlen).
        client.xinfo_groups.return_value = [{b"name": b"soar-api", b"pending": 5, b"lag": 2}]
        assert await queue.depth() == 7

    async def test_depth_falls_back_to_xlen_without_groups(self, queue, client):
        client.xinfo_groups.side_effect = Exception("old server")
        client.xlen.return_value = 7
        assert await queue.depth() == 7

    async def test_dlq_size(self, queue, client):
        client.xlen.return_value = 3
        assert await queue.dlq_size() == 3

    async def test_dlq_list_decodes_payload_and_reason(self, queue, client):
        client.xrange.return_value = [
            ("9-1", {b"payload": b'{"a":1}', b"reason": b"forward failed"})
        ]
        out = await queue.dlq_list()
        assert out == [
            {
                "dlq_entry_id": "9-1",
                "reason": "forward failed",
                "payload": {"a": 1},
            }
        ]

    async def test_dlq_list_undecodable_payload_becomes_none(self, queue, client):
        client.xrange.return_value = [("9-2", {b"payload": b"broken{", b"reason": b"r"})]
        out = await queue.dlq_list()
        assert out[0]["payload"] is None

    async def test_dlq_redrive_unknown_entry(self, queue, client):
        client.xrange.return_value = []
        assert await queue.dlq_redrive("9-x") is False

    async def test_dlq_redrive_reenqueues_and_deletes(self, queue, client):
        client.xrange.return_value = [("9-3", {b"payload": b'{"alert_id":"a"}', b"reason": b"r"})]
        assert await queue.dlq_redrive("9-3") is True
        # Re-enqueued on the main stream with attempts reset.
        enqueue_call = client.xadd.await_args
        assert enqueue_call.args[0] == "soar:admissions"
        payload = json.loads(enqueue_call.args[1]["payload"])
        assert payload["attempts"] == 0
        assert "redriven_at" in payload
        client.xdel.assert_awaited_once_with("soar:admissions:dlq", "9-3")

    async def test_dlq_redrive_undecodable_payload_returns_false(self, queue, client):
        client.xrange.return_value = [("9-4", {b"payload": b"broken{"})]
        assert await queue.dlq_redrive("9-4") is False

    async def test_dlq_purge_trims_and_returns_count(self, queue, client):
        client.xlen.return_value = 4
        assert await queue.dlq_purge() == 4
        client.xtrim.assert_awaited_once_with("soar:admissions:dlq", maxlen=0)

    async def test_dlq_purge_empty_skips_trim(self, queue, client):
        client.xlen.return_value = 0
        assert await queue.dlq_purge() == 0
        client.xtrim.assert_not_awaited()


class TestMetrics:
    async def test_metrics_with_group_info(self, queue, client):
        # depth() derives backlog from XINFO (pending+lag); stream_length
        # and dlq_size use XLEN.
        client.xlen.side_effect = [12, 2]  # stream_length, dlq_size
        client.xinfo_groups.return_value = [{b"name": b"soar-api", b"pending": 5, b"lag": 3}]
        m = await queue.metrics("soar-api")
        assert m == {
            "queue_depth": 8,
            "stream_length": 12,
            "dlq_size": 2,
            "consumer_lag": 3,
            "pending": 5,
        }

    async def test_metrics_xinfo_failure_returns_nones(self, queue, client):
        client.xlen.side_effect = [1, 0, 0]  # depth fallback, stream_length, dlq
        client.xinfo_groups.side_effect = Exception("unsupported")
        m = await queue.metrics("soar-api")
        assert m["queue_depth"] == 1
        assert m["consumer_lag"] is None
        assert m["pending"] is None

    async def test_metrics_other_group_ignored(self, queue, client):
        client.xlen.side_effect = [1, 0]
        client.xinfo_groups.return_value = [{b"name": b"other", b"pending": 9}]
        m = await queue.metrics("soar-api")
        assert m["pending"] is None


class TestDlqAutoRedrive:
    """R2: bounded auto-redrive — transient entries come back, poison
    and budget-exhausted entries stay dead."""

    async def test_transient_entry_is_reenqueued(self, queue, client):
        old_id = f"{int((time.time() - 120) * 1000)}-0"  # 2 min old
        client.xrange.return_value = [
            (old_id, {b"payload": b'{"alert_id":"a"}', b"reason": b"forward failed"}),
        ]
        assert await queue.dlq_auto_redrive() == 1
        payload = json.loads(client.xadd.await_args.args[1]["payload"])
        assert payload["redrive_count"] == 1
        assert payload["attempts"] == 0

    async def test_decode_failed_never_redriven(self, queue, client):
        old_id = f"{int((time.time() - 3600) * 1000)}-0"
        client.xrange.return_value = [
            (old_id, {b"payload": b'{"alert_id":"a"}', b"reason": b"decode_failed"}),
        ]
        assert await queue.dlq_auto_redrive() == 0
        client.xadd.assert_not_awaited()

    async def test_young_entry_waits_for_backoff(self, queue, client):
        fresh_id = f"{int(time.time() * 1000)}-0"  # just dead-lettered
        client.xrange.return_value = [
            (fresh_id, {b"payload": b'{"alert_id":"a"}', b"reason": b"forward failed"}),
        ]
        assert await queue.dlq_auto_redrive() == 0

    async def test_redrive_budget_exhausted(self, queue, client):
        old_id = f"{int((time.time() - 3600) * 1000)}-0"
        client.xrange.return_value = [
            (
                old_id,
                {
                    b"payload": b'{"alert_id":"a","redrive_count":3}',
                    b"reason": b"forward failed",
                },
            ),
        ]
        assert await queue.dlq_auto_redrive(max_redrives=3) == 0
        client.xadd.assert_not_awaited()
