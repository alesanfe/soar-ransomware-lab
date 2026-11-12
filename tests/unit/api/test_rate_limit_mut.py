#!/usr/bin/env python3
"""Mutation-hardening tests for rate_limit middleware — sliding-window
boundaries, client-key derivation, fail-open and 429 contract."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from soar_lab.interfaces.api.middleware.rate_limit import (
    InMemorySlidingWindowStore,
    RateLimitMiddleware,
    RateLimitRule,
    RedisSlidingWindowStore,
)


def _req(path="/x", client="10.0.0.1", headers=None):
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers or [],
        "client": (client, 1234) if client else None,
        "query_string": b"",
        "server": ("test", 80),
        "scheme": "http",
    }
    return Request(scope)


class TestInMemoryStore:
    async def test_window_eviction_boundary(self):
        s = InMemorySlidingWindowStore()
        t = 1000.0
        await s.record("k", t, 60.0)
        # at exactly +60 the first hit falls out (>= boundary)
        n, oldest = await s.record("k", t + 60.0, 60.0)
        assert n == 1 and oldest == t + 60.0
        # at +59.9 both remain
        s2 = InMemorySlidingWindowStore()
        await s2.record("k", t, 60.0)
        n, _ = await s2.record("k", t + 59.9, 60.0)
        assert n == 2

    async def test_sweep_removes_stale(self):
        s = InMemorySlidingWindowStore()
        t = 1000.0
        s._last_sweep = t
        await s.record("old", t, 60.0)
        await s.record("new", t, 60.0)
        # jump past 2*window triggers sweep; pre-existing keys are stale,
        # but the current key's hit was already appended before the sweep
        # (regression fix: it used to be popped and lost on an orphan deque).
        s._hits["old"].clear()  # empty deque -> stale
        s._hits["other"] = __import__("collections").deque([t - 100])
        n, oldest = await s.record("new", t + 121.0, 60.0)
        # append-before-sweep: the current key keeps its fresh hit.
        assert set(s._hits) == {"new"}
        assert (n, oldest) == (1, t + 121.0)
        assert s._last_sweep == t + 121.0


class TestRedisStore:
    async def test_pipeline_exact(self):
        client = MagicMock()
        pipe = MagicMock()
        client.pipeline.return_value = pipe
        pipe.execute = AsyncMock(
            return_value=[0, 1, 3, [(b"m", 555.0)], True]
        )
        store = RedisSlidingWindowStore(client)
        n, oldest = await store.record("tok:abc", 500.0, 60.0)
        client.pipeline.assert_called_once_with(transaction=False)
        assert pipe.zremrangebyscore.call_args.args == ("ratelimit:tok:abc", "-inf", 440.0)
        member = next(iter(pipe.zadd.call_args.args[1]))
        assert member.startswith("500.0:") and len(member) == 18
        assert pipe.expire.call_args.args == ("ratelimit:tok:abc", 62)
        assert n == 3 and oldest == 555.0

    async def test_empty_oldest_none(self):
        client = MagicMock()
        pipe = MagicMock()
        client.pipeline.return_value = pipe
        pipe.execute = AsyncMock(return_value=[0, 1, 1, [], True])
        store = RedisSlidingWindowStore(client)
        n, oldest = await store.record("k", 1.0, 60.0)
        assert (n, oldest) == (1, None)

    def test_from_url(self):
        with patch(
            "soar_lab.interfaces.api.middleware.rate_limit.redis.asyncio.from_url"
        ) as fu:
            RedisSlidingWindowStore.from_url("redis://x/0")
            fu.assert_called_once_with("redis://x/0")


class TestBudgetAndTrust:
    def test_longest_prefix_wins(self):
        mw = RateLimitMiddleware(
            object(),
            per_minute=100,
            rules=[RateLimitRule("/auth", 10), RateLimitRule("/auth/login", 3)],
        )
        assert mw._budget_for("/auth/login") == 3
        assert mw._budget_for("/auth/x") == 10
        assert mw._budget_for("/other") == 100

    def test_invalid_cidr_warns(self, caplog):
        with caplog.at_level("WARNING"):
            mw = RateLimitMiddleware(object(), trusted_proxies=["bad-cidr", "10.0.0.0/8"])
        assert "Ignoring invalid trusted-proxy CIDR" in caplog.text
        assert len(mw._trusted_nets) == 1

    def test_is_trusted_proxy(self):
        mw = RateLimitMiddleware(object(), trusted_proxies=["10.0.0.0/8"])
        assert mw._is_trusted_proxy("10.1.2.3") is True
        assert mw._is_trusted_proxy("192.168.0.1") is False
        assert mw._is_trusted_proxy("not-an-ip") is False


class TestClientKey:
    def test_bearer_token_key(self):
        import hashlib

        mw = RateLimitMiddleware(object())
        req = _req(headers=[(b"authorization", b"Bearer secret-token")])
        expect = "tok:" + hashlib.sha256(b"secret-token").hexdigest()[:16]
        assert mw._client_key(req) == expect

    def test_service_token_key(self):
        import hashlib

        mw = RateLimitMiddleware(object())
        req = _req(headers=[(b"x-service-token", b"svc")])
        assert mw._client_key(req) == "tok:" + hashlib.sha256(b"svc").hexdigest()[:16]

    def test_no_client_unknown(self):
        mw = RateLimitMiddleware(object())
        assert mw._client_key(_req(client=None)) == "ip:unknown"

    def test_xff_only_from_trusted(self):
        mw = RateLimitMiddleware(object(), trusted_proxies=["10.0.0.0/8"])
        req = _req(headers=[(b"x-forwarded-for", b"1.2.3.4")])
        assert mw._client_key(req) == "ip:1.2.3.4"
        # untrusted peer -> XFF ignored
        req2 = _req(client="8.8.8.8", headers=[(b"x-forwarded-for", b"1.2.3.4")])
        assert mw._client_key(req2) == "ip:8.8.8.8"

    def test_xff_right_to_left_skip_trusted(self):
        mw = RateLimitMiddleware(
            object(), trusted_proxies=["10.0.0.0/8", "172.16.0.0/12"]
        )
        req = _req(headers=[(b"x-forwarded-for", b"1.2.3.4, 10.9.9.9, 172.16.1.1")])
        assert mw._client_key(req) == "ip:1.2.3.4"

    def test_xff_invalid_hop_skipped(self):
        mw = RateLimitMiddleware(object(), trusted_proxies=["10.0.0.0/8"])
        req = _req(headers=[(b"x-forwarded-for", b"1.2.3.4, not-an-ip")])
        assert mw._client_key(req) == "ip:1.2.3.4"

    def test_xff_all_trusted_falls_back_leftmost(self):
        mw = RateLimitMiddleware(object(), trusted_proxies=["0.0.0.0/0"])
        req = _req(headers=[(b"x-forwarded-for", b"9.9.9.9, 8.8.8.8")])
        assert mw._client_key(req) == "ip:9.9.9.9"

    def test_xff_empty_falls_to_peer(self):
        mw = RateLimitMiddleware(object(), trusted_proxies=["10.0.0.0/8"])
        req = _req(headers=[(b"x-forwarded-for", b" , , ")])
        assert mw._client_key(req) == "ip:10.0.0.1"


class TestAllow:
    async def test_over_budget_429_values(self):
        store = AsyncMock()
        store.record.return_value = (101, time.time() - 10)
        mw = RateLimitMiddleware(object(), per_minute=100, store=store)
        allowed, remaining, retry, reset = await mw._allow("k", 100)
        assert allowed is False and remaining == 0
        assert 1 <= retry <= 60 and reset > time.time()

    async def test_count_exact_budget_allowed(self):
        store = AsyncMock()
        store.record.return_value = (100, 1000.0)
        mw = RateLimitMiddleware(object(), store=store)
        allowed, remaining, *_ = await mw._allow("k", 100)
        assert allowed is True and remaining == 0

    async def test_store_error_fail_open(self, caplog):
        store = AsyncMock()
        store.record.side_effect = RuntimeError("redis dead")
        mw = RateLimitMiddleware(object(), per_minute=7, store=store)
        with caplog.at_level("WARNING"):
            allowed, remaining, retry, _ = await mw._allow("k", 7)
        assert allowed is True and remaining == 6 and retry == 0
        assert "Rate-limit store failed (RuntimeError)" in caplog.text
        # second failure inside 60s -> no new log line
        caplog.clear()
        with caplog.at_level("WARNING"):
            await mw._allow("k", 7)
        assert "Rate-limit store failed" not in caplog.text

    async def test_oldest_none_retry_60(self):
        store = AsyncMock()
        store.record.return_value = (200, None)
        mw = RateLimitMiddleware(object(), store=store)
        allowed, _, retry, _ = await mw._allow("k", 100)
        assert allowed is False and retry == 60


class TestDispatch:
    def _app(self, **kw):
        async def ok(request):
            return JSONResponse({"ok": True})

        app = Starlette(routes=[Route("/x", ok), Route("/health", ok)])
        app.add_middleware(RateLimitMiddleware, **kw)
        return TestClient(app)

    def test_429_contract(self):
        c = self._app(per_minute=1)
        c.get("/x")
        r = c.get("/x")
        assert r.status_code == 429
        body = r.json()
        assert body["code"] == "rate_limited"
        assert body["detail"] == "Rate limit exceeded"
        assert body["retry_after_seconds"] >= 1
        assert r.headers["Retry-After"] == str(body["retry_after_seconds"])
        assert r.headers["X-RateLimit-Limit"] == "1"
        assert r.headers["X-RateLimit-Remaining"] == "0"
        assert "X-RateLimit-Reset" in r.headers

    def test_allowed_response_headers(self):
        c = self._app(per_minute=10)
        r = c.get("/x")
        assert r.status_code == 200
        assert r.headers["X-RateLimit-Limit"] == "10"
        assert r.headers["X-RateLimit-Remaining"] == "9"

    def test_exempt_and_static(self):
        c = self._app(per_minute=1, exempt_paths=["/health"])
        c.get("/x")
        assert c.get("/health").status_code == 200  # exempt path no limit

    def test_disabled(self):
        c = self._app(per_minute=1, enabled=False)
        c.get("/x")
        assert c.get("/x").status_code == 200
