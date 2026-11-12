#!/usr/bin/env python3
"""Mutation-hardening tests for RedisStreamsQueue — exact call args,
reason strings, DLQ lifecycle and retry-budget boundaries."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from soar_lab.infrastructure.messaging.redis_streams_queue import RedisStreamsQueue


def _q():
    c = AsyncMock()
    return RedisStreamsQueue(c), c


class TestEnqueueAndRead:
    async def test_enqueue_exact_args_and_default_str(self):
        q, c = _q()
        c.xadd.return_value = "1-0"
        # non-JSON-serializable value -> default=str renders it
        out = await q.enqueue({"n": object()})
        assert out == "1-0"
        (stream, fields), kw = c.xadd.call_args
        assert stream == "soar:admissions"
        assert kw["maxlen"] == 100_000 and kw["approximate"] is True
        payload = json.loads(fields["payload"])
        assert payload["n"].startswith("<object object")

    async def test_read_exact_args(self):
        q, c = _q()
        c.xreadgroup.return_value = []
        await q.read("g1", "c1", count=7, block_ms=123)
        assert c.xreadgroup.call_args.args == ("g1", "c1", {"soar:admissions": ">"})
        assert c.xreadgroup.call_args.kwargs == {"count": 7, "block": 123}
        c.xgroup_create.assert_awaited_once()

    async def test_claim_stale_exact_args(self):
        q, c = _q()
        c.xautoclaim.return_value = ("0-0", [], [])
        out = await q.claim_stale("g", "c", 5000)
        assert out == []
        args, kw = c.xautoclaim.call_args
        assert args == ("soar:admissions", "g", "c")
        assert kw == {"min_idle_time": 5000, "start_id": "0-0", "count": 100}

    async def test_claim_stale_exception_logs_and_empty(self, caplog):
        q, c = _q()
        c.xautoclaim.side_effect = RuntimeError("redis gone")
        with caplog.at_level("WARNING"):
            assert await q.claim_stale("g", "c", 1) == []
        assert "XAUTOCLAIM failed" in caplog.text

    async def test_claim_stale_decodes_and_poisons(self):
        q, c = _q()
        c.xautoclaim.return_value = (
            "0-0",
            [("1-0", {b"payload": b'{"a":1}'}), ("2-0", {b"payload": b"bad{"})],
            [],
        )
        out = await q.claim_stale("g", "c", 1)
        assert out == [("1-0", {"a": 1})]
        # poison entry went to DLQ and was acked
        assert c.xadd.await_count == 1
        c.xack.assert_awaited_once_with("soar:admissions", "g", "2-0")

    async def test_ack_exact_args(self):
        q, c = _q()
        await q.ack("g", "1-0")
        c.xack.assert_awaited_once_with("soar:admissions", "g", "1-0")


class TestDeadLetter:
    async def test_reason_truncated_512(self):
        q, c = _q()
        await q.dead_letter({"a": 1}, "r" * 600)
        (_, fields), kw = c.xadd.call_args
        assert fields["reason"] == "r" * 512
        assert kw["approximate"] is True

    async def test_ensure_group_busygroup_ok_other_raises(self):
        q, c = _q()
        c.xgroup_create.side_effect = Exception("BUSYGROUP exists")
        await q.ensure_group("g")
        c.xgroup_create.side_effect = Exception("OOM")
        with pytest.raises(Exception, match="OOM"):
            await q.ensure_group("g")
        args, kw = c.xgroup_create.call_args
        assert kw == {"id": "0", "mkstream": True}


class TestDepth:
    async def test_pending_plus_lag_bytes_keys(self):
        q, c = _q()
        c.xinfo_groups.return_value = [
            {b"pending": 3, b"lag": 4},
            {b"pending": 0, b"lag": 0},
        ]
        assert await q.depth() == 7

    async def test_str_key_fallback(self):
        q, c = _q()
        c.xinfo_groups.return_value = [{"pending": 2, "lag": 5}]
        assert await q.depth() == 7

    async def test_missing_keys_default_zero(self):
        q, c = _q()
        c.xinfo_groups.return_value = [{"pending": 2}]
        assert await q.depth() == 2

    async def test_xinfo_error_falls_to_xlen(self):
        q, c = _q()
        c.xinfo_groups.side_effect = RuntimeError("nope")
        c.xlen.return_value = 9
        assert await q.depth() == 9
        c.xlen.assert_awaited_once_with("soar:admissions")

    async def test_stream_length_and_dlq_size_streams(self):
        q, c = _q()
        c.xlen.side_effect = [10, 3]
        assert await q.stream_length() == 10
        assert await q.dlq_size() == 3
        assert c.xlen.await_args_list[0].args == ("soar:admissions",)
        assert c.xlen.await_args_list[1].args == ("soar:admissions:dlq",)


class TestDlqList:
    async def test_count_default_50(self):
        q, c = _q()
        c.xrange.return_value = []
        await q.dlq_list()
        assert c.xrange.call_args.args == ("soar:admissions:dlq",)
        assert c.xrange.call_args.kwargs == {"count": 50}

    async def test_decodes_and_unknown_reason(self):
        q, c = _q()
        c.xrange.return_value = [
            ("1-0", {b"payload": b'{"a":1}', b"reason": b"fwd"}),
            ("2-0", {}),
            ("3-0", {b"payload": b"notjson", b"reason": b"decode_failed"}),
        ]
        out = await q.dlq_list()
        assert out[0] == {
            "dlq_entry_id": "1-0",
            "reason": "fwd",
            "payload": {"a": 1},
        }
        assert out[1]["reason"] == "unknown" and out[1]["payload"] is None
        assert out[2]["payload"] is None and out[2]["reason"] == "decode_failed"


class TestDlqRedrive:
    async def test_missing_returns_false(self):
        q, c = _q()
        c.xrange.return_value = []
        assert await q.dlq_redrive("9-9") is False
        assert c.xrange.call_args.kwargs == {"min": "9-9", "max": "9-9"}

    async def test_bad_payload_false(self):
        q, c = _q()
        c.xrange.return_value = [("1-0", {b"payload": b"[1,2]"})]
        assert await q.dlq_redrive("1-0") is False

    async def test_success_resets_attempts_and_cleans(self):
        q, c = _q()
        c.xrange.return_value = [
            ("1-0", {b"payload": json.dumps({"attempts": 4, "x": 1}).encode()})
        ]
        c.xadd.return_value = "2-0"
        assert await q.dlq_redrive("1-0") is True
        sent = json.loads(c.xadd.call_args.args[1]["payload"])
        assert sent["attempts"] == 0
        assert isinstance(sent["redriven_at"], float)
        c.xdel.assert_awaited_once_with("soar:admissions:dlq", "1-0")


class TestDlqPurgeAndAuto:
    async def test_purge_trims_and_counts(self):
        q, c = _q()
        c.xlen.return_value = 4
        assert await q.dlq_purge() == 4
        c.xtrim.assert_awaited_once_with("soar:admissions:dlq", maxlen=0)

    async def test_purge_empty_no_trim(self):
        q, c = _q()
        c.xlen.return_value = 0
        assert await q.dlq_purge() == 0
        c.xtrim.assert_not_awaited()

    _SENT = object()

    def _dlq_row(self, eid="0-0", reason="fwd", payload=_SENT):
        if payload is self._SENT:
            payload = {}
        return {"dlq_entry_id": eid, "reason": reason, "payload": payload}

    async def test_auto_redrive_skips_decode_failed_and_nondict(self):
        q, c = _q()
        q.dlq_list = AsyncMock(
            return_value=[
                self._dlq_row(reason="decode_failed"),
                self._dlq_row(payload=None),
            ]
        )
        assert await q.dlq_auto_redrive() == 0
        c.xadd.assert_not_awaited()

    async def test_auto_redrive_budget_and_redrive(self):
        q, c = _q()
        q.dlq_list = AsyncMock(
            return_value=[
                self._dlq_row("1-0", payload={"redrive_count": 3}),  # over budget
                self._dlq_row("2-0", payload={"x": 1}),
            ]
        )
        c.xadd.return_value = "9-9"
        n = await q.dlq_auto_redrive()
        assert n == 1
        sent = json.loads(c.xadd.call_args.args[1]["payload"])
        assert sent["redrive_count"] == 1 and sent["attempts"] == 0
        c.xdel.assert_awaited_once_with("soar:admissions:dlq", "2-0")

    async def test_auto_redrive_min_age_blocks(self):
        import time as _t

        q, c = _q()
        young_ms = int(_t.time() * 1000) - 1000  # 1s old
        q.dlq_list = AsyncMock(
            return_value=[self._dlq_row(f"{young_ms}-0", payload={"x": 1})]
        )
        assert await q.dlq_auto_redrive(min_age_s=60.0) == 0
        c.xadd.assert_not_awaited()

    async def test_auto_redrive_backoff_exponential(self):
        import time as _t

        q, c = _q()
        # redrive_count=1 -> needs 120s age; entry is 90s old -> skipped
        entry_ms = int(_t.time() * 1000) - 90_000
        q.dlq_list = AsyncMock(
            return_value=[
                self._dlq_row(f"{entry_ms}-0", payload={"redrive_count": 1})
            ]
        )
        assert await q.dlq_auto_redrive(min_age_s=60.0) == 0

    async def test_auto_redrive_bad_entry_id_still_redrives(self):
        q, c = _q()
        c.xadd.return_value = "9-9"
        q.dlq_list = AsyncMock(
            return_value=[self._dlq_row("garbage", payload={"x": 1})]
        )
        assert await q.dlq_auto_redrive() == 1


class TestMetrics:
    async def test_metrics_shape_and_group_values(self):
        q, c = _q()
        c.xlen.side_effect = [8, 2]
        c.xinfo_groups.return_value = [
            {b"name": b"other", b"pending": 99, b"lag": 99},
            {b"name": b"soar-api", b"pending": 5, b"lag": 7},
        ]
        out = await q.metrics()
        assert out["pending"] == 5
        assert out["consumer_lag"] == 7
        assert out["stream_length"] == 8
        assert out["dlq_size"] == 2
        # queue_depth sums pending+lag over ALL groups: 99+99+5+7
        assert out["queue_depth"] == 210

    async def test_metrics_missing_lag_none(self):
        q, c = _q()
        c.xlen.side_effect = [0, 0]
        c.xinfo_groups.return_value = [{"name": "soar-api", "pending": 2}]
        out = await q.metrics()
        assert out["pending"] == 2
        assert out["consumer_lag"] is None

    async def test_metrics_xinfo_error_safe(self):
        q, c = _q()
        c.xlen.return_value = 0
        c.xinfo_groups.side_effect = RuntimeError("down")
        out = await q.metrics()
        assert out["pending"] is None
        assert out["consumer_lag"] is None


class TestPoisonAndDecode:
    async def test_poison_fields_exact(self, caplog):
        q, c = _q()
        fields = {b"payload": b"\xff\xfe{bad"}
        with caplog.at_level("WARNING"):
            await q._poison_to_dlq("g", "1-0", fields)
        (_, f), kw = c.xadd.call_args
        assert f["reason"] == "decode_failed"
        assert f["source_entry_id"] == "1-0"
        assert len(f["payload"]) <= 4000
        c.xack.assert_awaited_once_with("soar:admissions", "g", "1-0")
        assert "Poison queue entry" in caplog.text

    async def test_decode_rows_none(self):
        q, _ = _q()
        assert await q._decode(None, "g") == []

    def test_decode_fields_variants(self, caplog):
        f = RedisStreamsQueue._decode_fields
        assert f({}) is None
        assert f({b"payload": b'{"x":2}'}) == {"x": 2}
        with caplog.at_level("WARNING"):
            assert f({b"payload": b"oops"}) is None
        assert "Undecodable queue payload skipped" in caplog.text

    def test_s_helper(self):
        assert RedisStreamsQueue._s(b"a") == "a"
        assert RedisStreamsQueue._s(3) == "3"
