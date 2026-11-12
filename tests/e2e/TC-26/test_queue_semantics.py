"""TC-26 — Redis Streams queue semantics against the production queue impl.

Uses RedisStreamsQueue on a dedicated stream (soar:e2e:tc26*) so the live
soar:admissions pipeline is untouched. Verifies DLQ lifecycle, poison
guards, redrive budget, pending-age measurement, maxlen bounding, and
the deliberate noeviction policy.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest
import redis.asyncio as aioredis

from soar_lab.infrastructure.messaging.redis_streams_queue import RedisStreamsQueue

STREAM = "soar:e2e:tc26"
DLQ = "soar:e2e:tc26:dlq"
GROUP = "e2e-tc26"
CONSUMER = "tc26-worker"


def _client() -> aioredis.Redis:
    pw = next(
        ln.split("=", 1)[1].strip()
        for f in (Path("/app/.env.container"), Path("/app/.env.full"))
        if f.exists()
        for ln in f.read_text().splitlines()
        if ln.startswith("REDIS_PASSWORD=")
    )
    from tests.e2e.helpers.redis_tls import redis_kwargs

    return aioredis.Redis(
        **redis_kwargs(host="redis", port=6379, password=pw, socket_timeout=10)
    )


def _run(coro):
    return asyncio.run(coro)


@pytest.mark.e2e
class TestQueueSemantics:
    tc_id = "TC-26"

    @pytest.fixture(autouse=True)
    def clean_streams(self):
        c = _client()

        async def _wipe():
            await c.delete(STREAM, DLQ)
            await c.aclose()

        _run(_wipe())
        yield
        _run(_wipe())

    def _queue(self, maxlen: int = 100_000) -> RedisStreamsQueue:
        return RedisStreamsQueue(_client(), stream=STREAM, dlq_stream=DLQ, maxlen=maxlen)

    def test_dlq_redrive_full_lifecycle(self):
        """dead_letter → dlq_size/list → dlq_redrive → payload re-enqueued,
        DLQ entry removed, attempts reset."""

        async def scenario():
            q = self._queue()
            await q.enqueue({"alert_id": "tc26-redrive", "attempts": 3})
            await q.dead_letter({"alert_id": "tc26-redrive", "attempts": 3}, reason="downstream_timeout")
            assert await q.dlq_size() == 1
            rows = await q.dlq_list()
            assert rows[0]["reason"] == "downstream_timeout"
            assert rows[0]["payload"]["alert_id"] == "tc26-redrive"
            dlq_id = rows[0]["dlq_entry_id"]
            stream_len_before = await q.stream_length()
            assert await q.dlq_redrive(dlq_id) is True
            assert await q.dlq_size() == 0, "redrive must delete the DLQ entry"
            assert await q.stream_length() == stream_len_before + 1
            # redriven payload carries a fresh retry budget + audit stamp
            latest = await q.client.xrevrange(STREAM, count=1)
            import json

            payload = json.loads(latest[0][1][b"payload"])
            assert payload["attempts"] == 0
            assert "redriven_at" in payload
            await q.client.aclose()

        _run(scenario())

    def test_auto_redrive_skips_poison_and_respects_budget(self):
        """decode_failed poison is never redriven; entries at the redrive
        cap stay; transient entries are re-enqueued."""

        async def scenario():
            q = self._queue()
            await q.dead_letter({"alert_id": "poison"}, reason="decode_failed")
            await q.dead_letter({"alert_id": "capped", "redrive_count": 3}, reason="timeout")
            await q.dead_letter({"alert_id": "transient"}, reason="downstream_timeout")
            time.sleep(0.1)
            n = await q.dlq_auto_redrive(max_redrives=3, min_age_s=0)
            assert n == 1, f"expected 1 redrive, got {n}"
            left = await q.dlq_list()
            ids = {r["payload"].get("alert_id") for r in left}
            assert ids == {"poison", "capped"}, f"wrong entries left in DLQ: {ids}"
            await q.client.aclose()

        _run(scenario())

    def test_pending_message_age_measurable(self):
        """A read-but-unacked entry is pending with measurable idle time;
        claim_stale picks it up once it crosses min_idle_ms."""

        async def scenario():
            q = self._queue()
            await q.enqueue({"alert_id": "tc26-pending"})
            rows = await q.read(GROUP, CONSUMER, count=1, block_ms=500)
            assert len(rows) == 1
            time.sleep(0.3)
            pend = await q.client.xpending(STREAM, GROUP)
            assert pend["pending"] == 1
            claimed = await q.claim_stale(GROUP, "tc26-reaper", min_idle_ms=200)
            assert any(e[1]["alert_id"] == "tc26-pending" for e in claimed), (
                "stale entry not claimed"
            )
            await q.client.aclose()

        _run(scenario())

    def test_noeviction_policy_is_deliberate(self):
        """maxmemory-policy=noeviction is the deliberate queue-safe choice:
        Redis errors on OOM rather than silently dropping queue data."""

        async def scenario():
            cfg = await _client().config_get("maxmemory-policy")
            assert cfg["maxmemory-policy"] == "noeviction"
            mm = await _client().info("memory")
            assert mm["maxmemory"] >= 500 * 1024 * 1024, "maxmemory not bounded"
            await _client().aclose()

        _run(scenario())

    def test_stream_bounded_by_maxlen(self):
        """XADD with approximate MAXLEN keeps the stream length bounded —
        an unbounded stream would grow until Redis OOMs. Note: `MAXLEN ~`
        trims at radix-node granularity (~100 entries/node), so the bound
        only engages once a node boundary is crossed — production's
        DEFAULT_MAXLEN=100_000 is far above that."""

        async def scenario():
            q = self._queue(maxlen=200)
            for i in range(400):
                await q.enqueue({"alert_id": f"flood-{i}"})
            length = await q.stream_length()
            await q.client.aclose()
            # node-granular slack: 200 bound + ≤1 node (~100) tolerance
            assert length <= 300, f"stream not bounded: XLEN={length}"
            assert length >= 150, f"over-trimmed: XLEN={length}"

        _run(scenario())

    def test_redis_stats_exported(self):
        """keyspace hit/miss + commandstats are exposed — the cache/queue
        performance surface is observable, not a black box."""

        async def scenario():
            c = _client()
            await c.set("tc26:probe", "1")
            await c.get("tc26:probe")
            info = await c.info("stats")
            await c.delete("tc26:probe")
            await c.aclose()
            assert "keyspace_hits" in info and "keyspace_misses" in info
            assert info["keyspace_hits"] + info["keyspace_misses"] > 0

        _run(scenario())
