#!/usr/bin/env python3
"""Surgical mutation-killers: exact log args, env-var names, codec
error-handlers, redis call args and boundary values across the queue,
rate-limit and store modules."""

from __future__ import annotations

import json
import logging
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from soar_lab.infrastructure.messaging.redis_streams_queue import RedisStreamsQueue
from soar_lab.interfaces.api.middleware.rate_limit import (
    RateLimitMiddleware,
    RedisSlidingWindowStore,
)


def _q():
    c = AsyncMock()
    return RedisStreamsQueue(c), c


class TestQueueLogContracts:
    async def test_claim_stale_logs_exc(self, caplog):
        q, c = _q()
        c.xautoclaim.side_effect = RuntimeError("redis gone")
        with caplog.at_level(logging.WARNING):
            await q.claim_stale("g", "c", 1)
        assert caplog.records[-1].getMessage() == "XAUTOCLAIM failed: redis gone"

    async def test_redrive_logs_entry_and_stream(self, caplog):
        q, c = _q()
        c.xrange.return_value = [
            ("1-0", {b"payload": json.dumps({"a": 1}).encode()})
        ]
        c.xadd.return_value = "9-9"
        with caplog.at_level(logging.INFO):
            await q.dlq_redrive("1-0")
        assert caplog.records[-1].getMessage() == (
            "Redrove DLQ entry 1-0 back to soar:admissions"
        )

    async def test_auto_redrive_count_log(self, caplog):
        q, c = _q()
        c.xadd.return_value = "9-9"
        q.dlq_list = AsyncMock(
            return_value=[{"dlq_entry_id": "bad-id", "reason": "r", "payload": {"x": 1}}]
        )
        with caplog.at_level(logging.INFO):
            await q.dlq_auto_redrive()
        assert caplog.records[-1].getMessage() == "Auto-redrove 1 DLQ entry(s)"

    async def test_metrics_xinfo_debug_log(self, caplog):
        q, c = _q()
        c.xlen.return_value = 0
        c.xinfo_groups.side_effect = RuntimeError("nope")
        with caplog.at_level(logging.DEBUG):
            await q.metrics()
        assert caplog.records[-1].getMessage() == "xinfo_groups unavailable: nope"

    async def test_poison_decode_bytes_key(self, caplog):
        q, c = _q()
        c.xautoclaim.return_value = (
            "0-0",
            [("7-7", {b"payload": b"\xff\xfe"})],
            [],
        )
        with caplog.at_level(logging.WARNING):
            out = await q.claim_stale("g", "c", 1)
        assert out == []
        assert caplog.records[-1].getMessage() == (
            "Poison queue entry 7-7 moved to DLQ"
        )
        f = c.xadd.call_args.args[1]
        assert f["source_entry_id"] == "7-7"

    async def test_poison_str_payload_key(self):
        q, c = _q()
        # str key variant of the payload field
        c.xautoclaim.return_value = ("0-0", [("1-0", {"payload": "bad{"})], [])
        out = await q.claim_stale("g", "c", 1)
        assert out == []
        c.xadd.assert_awaited_once()

    async def test_undecodable_skip_log(self, caplog):
        q, c = _q()
        c.xreadgroup.return_value = [
            ("s", [("1-0", {b"payload": b"bad{"})]),
        ]
        with caplog.at_level(logging.WARNING):
            await q.read("g", "c", count=5, block_ms=10)
        msgs = [r.getMessage() for r in caplog.records]
        assert "Undecodable queue payload skipped" in msgs
        assert "Poison queue entry 1-0 moved to DLQ" in msgs

    async def test_depth_str_keys(self):
        q, c = _q()
        c.xinfo_groups.return_value = [{"pending": 3, "lag": 4}]
        assert await q.depth() == 7

    async def test_metrics_lag_keys(self):
        q, c = _q()
        c.xlen.return_value = 0
        c.xinfo_groups.return_value = [
            {"name": "soar-api", "pending": 5, "lag": 9},
        ]
        out = await q.metrics()
        assert out["pending"] == 5 and out["consumer_lag"] == 9


class TestRedisStoreCallArgs:
    async def test_zrange_args_exact(self):
        client = MagicMock()
        pipe = MagicMock()
        client.pipeline.return_value = pipe
        pipe.execute = AsyncMock(return_value=[0, 1, 2, [(b"m", 5.0)], True])
        store = RedisSlidingWindowStore(client)
        await store.record("k", 100.0, 60.0)
        assert pipe.zrange.call_args.args == ("ratelimit:k", 0, 0)
        assert pipe.zrange.call_args.kwargs == {"withscores": True}
        assert pipe.zadd.call_args.args[0] == "ratelimit:k"


class TestRateLimitEnvAndCidr:
    def test_env_var_trusted_proxies(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_TRUSTED_PROXIES", "10.0.0.0/8 , 192.168.0.0/16")
        mw = RateLimitMiddleware(object())
        assert len(mw._trusted_nets) == 2

    def test_env_unset_no_crash(self, monkeypatch):
        monkeypatch.delenv("RATE_LIMIT_TRUSTED_PROXIES", raising=False)
        mw = RateLimitMiddleware(object())
        assert mw._trusted_nets == []

    def test_host_bits_cidr_strict_false(self, caplog):
        # "10.0.0.1/8" is only valid with strict=False parsing
        with caplog.at_level(logging.WARNING):
            mw = RateLimitMiddleware(object(), trusted_proxies=["10.0.0.1/8"])
        assert len(mw._trusted_nets) == 1
        assert caplog.records == [] or "Ignoring" not in caplog.records[-1].getMessage()

    def test_bad_cidr_logs_net(self, caplog):
        with caplog.at_level(logging.WARNING):
            RateLimitMiddleware(object(), trusted_proxies=["bogus-x"])
        assert caplog.records[-1].getMessage() == (
            "Ignoring invalid trusted-proxy CIDR: bogus-x"
        )

    def test_default_per_minute(self):
        assert RateLimitMiddleware(object())._per_minute == 100

    def test_log_throttle_60s(self, caplog):
        store = AsyncMock()
        store.record.side_effect = RuntimeError("x")
        mw = RateLimitMiddleware(object(), store=store)
        import asyncio

        async def run():
            await mw._allow("k", 5)
            # force second failure past 60s boundary -> logs again
            mw._last_store_error_log -= 61.0
            await mw._allow("k", 5)

        with caplog.at_level(logging.WARNING):
            asyncio.run(run())
        msgs = [r.getMessage() for r in caplog.records]
        assert msgs == [
            "Rate-limit store failed (RuntimeError) — allowing request",
            "Rate-limit store failed (RuntimeError) — allowing request",
        ]


class TestRateLimitStoreSweep:
    async def test_sweep_exact_boundary(self):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            InMemorySlidingWindowStore,
        )

        s = InMemorySlidingWindowStore()
        t = 1000.0
        s._last_sweep = t
        s._hits["stale"] = __import__("collections").deque([t - 61])
        # now - last_sweep == 2*window exactly -> NOT > -> no sweep
        await s.record("k", t + 120.0, 60.0)
        assert "stale" in s._hits
        # just past -> sweeps
        await s.record("k", t + 120.1, 60.0)
        assert "stale" not in s._hits


class TestDispatchHeaderValues:
    def _app(self, **kw):
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        async def ok(request):
            return JSONResponse({"ok": True})

        app = Starlette(routes=[Route("/x", ok)])
        app.add_middleware(RateLimitMiddleware, **kw)
        return TestClient(app)

    def test_reset_header_is_digits(self):
        c = self._app(per_minute=5)
        r = c.get("/x")
        assert r.headers["X-RateLimit-Reset"].isdigit()
        assert r.headers["X-RateLimit-Remaining"] == "4"


class TestPreAuthExact:
    def test_bad_cidr_message(self, caplog):
        from soar_lab.interfaces.api.middleware.preauth_rate_limit import (
            PreAuthRateLimitMiddleware,
        )

        with caplog.at_level(logging.WARNING):
            PreAuthRateLimitMiddleware(None, trusted_proxies=["bad9"])
        assert caplog.records[-1].getMessage() == (
            "Ignoring invalid pre-auth trusted-proxy CIDR: bad9"
        )

    async def test_429_headers_exact(self):
        import time as _t

        from soar_lab.interfaces.api.middleware.preauth_rate_limit import (
            PreAuthRateLimitMiddleware,
        )

        mw = PreAuthRateLimitMiddleware(None, per_minute=3)
        mw._hits["10.0.0.1"] = __import__("collections").deque(
            [_t.time()] * 5
        )
        sent = []

        async def receive():
            return {"type": "http.disconnect"}

        async def send(m):
            sent.append(m)

        async def app(scope, receive, send):
            raise AssertionError("should not reach app")

        mw.app = app
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/x",
            "headers": [],
            "client": ("10.0.0.1", 1),
        }
        await mw(scope, receive, send)
        assert sent[0]["status"] == 429
        h = dict(sent[0]["headers"])
        assert h[b"retry-after"].isdigit()
        assert h[b"x-ratelimit-limit"] == b"3"
        assert h[b"x-ratelimit-remaining"] == b"0"
        assert h[b"x-ratelimit-reset"].isdigit()
