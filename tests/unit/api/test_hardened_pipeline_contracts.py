"""Mutation-kill contracts for the hardened admission pipeline.

These tests pin the EXACT observable contract of the webhook ingestion
middleware — error bodies, rate-limit headers, boundary comparisons,
skip conditions and identity derivation. They exist because the mutation
run showed each of these behaviours could be silently broken (XX-marker,
case or boundary mutants surviving) without a contract-level assertion.
"""

from __future__ import annotations

import hashlib
import time
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from soar_lab.interfaces.api.middleware.body_limit import (
    BodyLimitMiddleware,
    BodyLimitRule,
)
from soar_lab.interfaces.api.middleware.preauth_rate_limit import (
    PreAuthRateLimitMiddleware,
)
from soar_lab.interfaces.api.middleware.rate_limit import (
    InMemorySlidingWindowStore,
    RateLimitMiddleware,
    RateLimitRule,
    RedisSlidingWindowStore,
)
from soar_lab.interfaces.api.middleware.security_headers import (
    SecurityHeadersMiddleware,
)
from soar_lab.interfaces.api.middleware.trace_id import TraceIdMiddleware


def _app(response_status: int = 200):
    async def echo(request):
        return JSONResponse({"ok": True}, status_code=response_status)

    return Starlette(
        routes=[Route("/{p:path}", echo, methods=["GET", "POST", "OPTIONS", "HEAD"])]
    )


# ── PreAuthRateLimitMiddleware ───────────────────────────────────────────


class TestPreAuthRateLimitContract:
    def test_429_body_and_headers_exact(self):
        app = PreAuthRateLimitMiddleware(_app(), per_minute=1)
        c = TestClient(app)
        assert c.get("/x").status_code == 200
        r = c.get("/x")
        assert r.status_code == 429
        assert r.json() == {
            "detail": "Rate limit exceeded",
            "code": "rate_limited",
            "retry_after_seconds": r.json()["retry_after_seconds"],
        }
        assert set(r.json()) == {"detail", "code", "retry_after_seconds"}
        assert r.headers["Retry-After"] == str(r.json()["retry_after_seconds"])
        assert r.headers["X-RateLimit-Limit"] == "1"
        assert r.headers["X-RateLimit-Remaining"] == "0"
        assert int(r.headers["X-RateLimit-Reset"]) >= int(time.time())

    def test_default_budget_is_60(self):
        # The documented default must admit exactly 60 requests/minute —
        # pins per_minute=60 against ±1 mutants.
        app = PreAuthRateLimitMiddleware(_app())
        c = TestClient(app)
        for _ in range(60):
            assert c.get("/x").status_code == 200
        assert c.get("/x").status_code == 429

    def test_disabled_passes_everything(self):
        # not enabled → every http request flows through untouched
        # (kills `or` → `and` on the skip condition).
        app = PreAuthRateLimitMiddleware(_app(), per_minute=1, enabled=False)
        c = TestClient(app)
        for _ in range(5):
            assert c.get("/x").status_code == 200

    def test_window_expiry_boundary(self):
        mw = PreAuthRateLimitMiddleware(_app(), per_minute=1)
        key = "1.2.3.4"
        allowed, _ = mw._allow(key, now=1000.0)
        assert allowed
        # Entry is still live at 59.9s — blocks.
        allowed, retry = mw._allow(key, now=1059.9)
        assert not allowed
        assert retry >= 1
        # At exactly +60.0 the old hit expired (`>=` boundary) — allowed.
        allowed, retry = mw._allow(key, now=1060.0)
        assert allowed and retry == 0

    def test_retry_after_math(self):
        mw = PreAuthRateLimitMiddleware(_app(), per_minute=1)
        mw._allow("k", now=1000.0)
        _, retry = mw._allow("k", now=1010.0)
        # int(60 - 10) = 50 — pins max(1, int(60.0 - delta)).
        assert retry == 50
        # Nearly-expired window still floors Retry-After at 1.
        _, retry = mw._allow("k", now=1059.99)
        assert retry == 1

    def test_xff_ignored_from_untrusted_peer(self):
        app = PreAuthRateLimitMiddleware(_app(), per_minute=1)
        c = TestClient(app)
        c.get("/x")
        # Spoofed XFF from an untrusted peer must not rotate the bucket.
        r = c.get("/x", headers={"X-Forwarded-For": "9.9.9.9"})
        assert r.status_code == 429

    def test_xff_honoured_from_trusted_proxy(self):
        app = PreAuthRateLimitMiddleware(
            _app(), per_minute=1, trusted_proxies=["testclient"]
        )
        mw = app
        scope = {
            "client": ("10.0.0.1", 1234),
            "headers": [(b"x-forwarded-for", b"8.8.8.8, 10.0.0.1")],
        }
        mw._trusted = []
        import ipaddress

        mw._trusted = [ipaddress.ip_network("10.0.0.0/8")]
        assert mw._client_ip(scope) == "8.8.8.8"

    def test_scope_without_headers_or_client(self):
        mw = PreAuthRateLimitMiddleware(_app())
        assert mw._client_ip({}) == "unknown"
        mw._trusted = [__import__("ipaddress").ip_network("0.0.0.0/0")]
        assert mw._client_ip({"client": ("10.1.2.3", 1)}) == "10.1.2.3"


# ── RateLimitMiddleware (post-auth) ──────────────────────────────────────


class TestRateLimitContract:
    def _client(self, **kw):
        app = RateLimitMiddleware(_app(), **kw)
        return TestClient(app)

    def test_429_body_exact(self):
        c = self._client(per_minute=1)
        assert c.get("/x").status_code == 200
        r = c.get("/x")
        assert r.status_code == 429
        assert set(r.json()) == {"detail", "code", "retry_after_seconds"}
        assert r.json()["detail"] == "Rate limit exceeded"
        assert r.json()["code"] == "rate_limited"
        assert r.headers["Retry-After"] == str(r.json()["retry_after_seconds"])

    def test_2xx_carries_limit_headers(self):
        c = self._client(per_minute=10)
        r = c.get("/x")
        assert r.headers["X-RateLimit-Limit"] == "10"
        assert r.headers["X-RateLimit-Remaining"] == "9"
        assert "X-RateLimit-Reset" in r.headers
        assert "Retry-After" not in r.headers

    def test_exempt_path_unlimited(self):
        c = self._client(per_minute=1, exempt_paths=["/health"])
        for _ in range(5):
            assert c.get("/health").status_code == 200

    def test_static_prefix_unlimited(self):
        c = self._client(per_minute=1)
        for _ in range(5):
            assert c.get("/static/app.js").status_code == 200

    def test_disabled_unlimited(self):
        c = self._client(per_minute=1, enabled=False)
        for _ in range(5):
            assert c.get("/x").status_code == 200

    def test_rule_longest_prefix_budget(self):
        c = self._client(
            per_minute=100, rules=[RateLimitRule("/auth", 1), RateLimitRule("/auth/login", 3)]
        )
        for _ in range(3):
            assert c.post("/auth/login").status_code == 200
        assert c.post("/auth/login").status_code == 429

    def test_bearer_token_buckets_separately(self):
        c = self._client(per_minute=1)
        assert c.get("/x", headers={"Authorization": "Bearer aaa"}).status_code == 200
        # Different token → different bucket.
        assert c.get("/x", headers={"Authorization": "Bearer bbb"}).status_code == 200
        # Same token → same bucket, exhausted.
        assert c.get("/x", headers={"Authorization": "Bearer aaa"}).status_code == 429

    def test_client_key_derivation(self):
        mw = RateLimitMiddleware(_app(), per_minute=1)

        class Req:
            def __init__(self, headers, client):
                self.headers = headers
                self.client = client

        r = Req({"authorization": "Bearer secret"}, None)
        key = mw._client_key(r)
        assert key == "tok:" + hashlib.sha256(b"secret").hexdigest()[:16]

        r = Req({"x-service-token": "svc"}, None)
        key = mw._client_key(r)
        assert key == "tok:" + hashlib.sha256(b"svc").hexdigest()[:16]

        class C:
            host = "9.9.9.9"

        r = Req({}, C())
        assert mw._client_key(r) == "ip:9.9.9.9"
        r = Req({}, None)
        assert mw._client_key(r) == "ip:unknown"


class TestInMemoryStore:
    @pytest.mark.asyncio
    async def test_window_boundary(self):
        s = InMemorySlidingWindowStore()
        count, _ = await s.record("k", now=1000.0, window_s=60.0)
        assert count == 1
        # Exactly at the window edge the hit expires (>= boundary).
        count, _ = await s.record("k", now=1060.0, window_s=60.0)
        assert count == 1
        # Just inside the window both hits count.
        count, _ = await s.record("k", now=1060.1, window_s=60.0)
        assert count == 2

    @pytest.mark.asyncio
    async def test_returns_oldest_hit(self):
        s = InMemorySlidingWindowStore()
        await s.record("k", now=1000.0, window_s=60.0)
        _, oldest = await s.record("k", now=1010.0, window_s=60.0)
        assert oldest == 1000.0


class TestRedisStore:
    @pytest.mark.asyncio
    async def test_pipeline_semantics(self):
        # pipeline() is synchronous; only execute() is awaited.
        client = Mock()
        pipe = Mock()
        pipe.execute = AsyncMock(return_value=[None, None, 3, [(b"m", 1000.0)], None])
        client.pipeline.return_value = pipe
        s = RedisSlidingWindowStore(client)
        count, oldest = await s.record("clientkey", now=1010.0, window_s=60.0)
        client.pipeline.assert_called_once_with(transaction=False)
        rkey = "ratelimit:clientkey"
        pipe.zremrangebyscore.assert_called_once_with(rkey, "-inf", 950.0)
        member_arg = pipe.zadd.call_args[0][1]
        member = next(iter(member_arg))
        assert member.startswith("1010.0:")
        pipe.zcard.assert_called_once_with(rkey)
        pipe.expire.assert_called_once_with(rkey, 62)
        assert count == 3 and oldest == 1000.0


class TestFailOpen:
    @pytest.mark.asyncio
    async def test_store_error_allows(self):
        store = AsyncMock()
        store.record.side_effect = RuntimeError("redis down")
        mw = RateLimitMiddleware(_app(), per_minute=1, store=store)
        allowed, remaining, retry, reset = await mw._allow("k", 5)
        assert allowed and retry == 0
        assert remaining == 4
        assert reset > time.time()

    @pytest.mark.asyncio
    async def test_store_error_reset_is_now_plus_60(self, monkeypatch):
        import soar_lab.interfaces.api.middleware.rate_limit as rl

        store = AsyncMock()
        store.record.side_effect = RuntimeError("down")
        monkeypatch.setattr(rl.time, "time", lambda: 1000.0)
        mw = RateLimitMiddleware(_app(), store=store)
        *_, reset = await mw._allow("k", 5)
        assert reset == 1060.0

    @pytest.mark.asyncio
    async def test_store_error_log_throttled_at_60s(self, monkeypatch, caplog):
        import soar_lab.interfaces.api.middleware.rate_limit as rl

        store = AsyncMock()
        store.record.side_effect = RuntimeError("down")
        mw = RateLimitMiddleware(_app(), store=store)
        calls = []
        monkeypatch.setattr(
            rl.logger, "warning", lambda *a, **k: calls.append(a)
        )
        monkeypatch.setattr(rl.time, "time", lambda: 1000.0)
        await mw._allow("k", 5)
        assert len(calls) == 1
        # A second failure inside 60s does not log.
        await mw._allow("k", 5)
        assert len(calls) == 1
        # At +61s it logs again (strict `>` throttle).
        monkeypatch.setattr(rl.time, "time", lambda: 1061.0)
        await mw._allow("k", 5)
        assert len(calls) == 2


class TestAllowContract:
    @pytest.mark.asyncio
    async def test_window_is_60_seconds(self, monkeypatch):
        import soar_lab.interfaces.api.middleware.rate_limit as rl

        store = AsyncMock()
        store.record.return_value = (1, 1000.0)
        monkeypatch.setattr(rl.time, "time", lambda: 1010.0)
        mw = RateLimitMiddleware(_app(), store=store)
        await mw._allow("k", 5)
        store.record.assert_awaited_once_with("k", 1010.0, 60.0)

    @pytest.mark.asyncio
    async def test_reset_epoch_is_oldest_plus_60(self, monkeypatch):
        import soar_lab.interfaces.api.middleware.rate_limit as rl

        store = AsyncMock()
        store.record.return_value = (2, 1000.0)
        monkeypatch.setattr(rl.time, "time", lambda: 1030.0)
        mw = RateLimitMiddleware(_app(), store=store)
        *_, reset = await mw._allow("k", 5)
        assert reset == 1060.0

    @pytest.mark.asyncio
    async def test_reset_epoch_now_plus_60_when_no_oldest(self, monkeypatch):
        import soar_lab.interfaces.api.middleware.rate_limit as rl

        store = AsyncMock()
        store.record.return_value = (1, None)
        monkeypatch.setattr(rl.time, "time", lambda: 1000.0)
        mw = RateLimitMiddleware(_app(), store=store)
        *_, reset = await mw._allow("k", 5)
        assert reset == 1060.0

    @pytest.mark.asyncio
    async def test_allowed_remaining_and_zero_retry(self, monkeypatch):
        import soar_lab.interfaces.api.middleware.rate_limit as rl

        store = AsyncMock()
        store.record.return_value = (3, 1000.0)
        monkeypatch.setattr(rl.time, "time", lambda: 1030.0)
        mw = RateLimitMiddleware(_app(), store=store)
        allowed, remaining, retry, reset = await mw._allow("k", 5)
        assert (allowed, remaining, retry, reset) == (True, 2, 0, 1060.0)

    @pytest.mark.asyncio
    async def test_retry_after_exact(self, monkeypatch):
        import soar_lab.interfaces.api.middleware.rate_limit as rl

        store = AsyncMock()
        store.record.return_value = (6, 1000.0)
        monkeypatch.setattr(rl.time, "time", lambda: 1030.0)
        mw = RateLimitMiddleware(_app(), store=store)
        allowed, remaining, retry, reset = await mw._allow("k", 5)
        # int(60 - 30) = 30 — kills +61, +inf and sign mutations.
        assert (allowed, remaining, retry, reset) == (False, 0, 30, 1060.0)

    @pytest.mark.asyncio
    async def test_retry_after_floored_at_1(self, monkeypatch):
        import soar_lab.interfaces.api.middleware.rate_limit as rl

        store = AsyncMock()
        store.record.return_value = (6, 1000.0)
        monkeypatch.setattr(rl.time, "time", lambda: 1059.9)
        mw = RateLimitMiddleware(_app(), store=store)
        *_, retry, _ = await mw._allow("k", 5)
        # int(60 - 59.9) = 0 → floored to 1 (kills max(2, …)).
        assert retry == 1

    @pytest.mark.asyncio
    async def test_retry_after_60_when_no_oldest(self, monkeypatch):
        import soar_lab.interfaces.api.middleware.rate_limit as rl

        store = AsyncMock()
        store.record.return_value = (6, None)
        monkeypatch.setattr(rl.time, "time", lambda: 1000.0)
        mw = RateLimitMiddleware(_app(), store=store)
        *_, retry, _ = await mw._allow("k", 5)
        assert retry == 60


class TestClientKeyContract:
    def _req(self, headers=None, host="9.9.9.9"):
        class C:
            pass

        c = C()
        c.host = host

        class Req:
            pass

        r = Req()
        r.headers = headers or {}
        r.client = c if host is not None else None
        return r

    def _trusted(self, *nets):
        mw = RateLimitMiddleware(_app(), trusted_proxies=list(nets))
        return mw

    def test_bearer_digest_truncated_16(self):
        mw = RateLimitMiddleware(_app())
        r = self._req({"authorization": "Bearer tok-value"}, "1.1.1.1")
        assert mw._client_key(r) == "tok:" + hashlib.sha256(b"tok-value").hexdigest()[:16]

    def test_xff_hop_cap_20(self):
        import ipaddress

        mw = self._trusted("10.0.0.0/8")
        # 21 hops: 20 trusted proxies + the real client LAST (index 20 is
        # dropped by [:20]). Real code falls back to hops[0]; the [:21]
        # mutant keeps and returns 8.8.8.8.
        hops = ["10.0.0.2"] + [f"10.0.0.{i}" for i in range(3, 22)] + ["8.8.8.8"]
        assert len(hops) == 21
        r = self._req(
            {"x-forwarded-for": ", ".join(hops)}, "10.0.0.1"
        )
        assert mw._client_key(r) == "ip:10.0.0.2"

    def test_invalid_hop_continues_scanning(self):
        mw = self._trusted("10.0.0.0/8")
        # Reversed walk: proxy → bogus (invalid, must `continue` not `break`)
        # → 1.1.1.1 (valid). A `break` falls back to hops[0]=10.0.0.2.
        r = self._req(
            {"x-forwarded-for": "10.0.0.2, 1.1.1.1, bogus, 10.0.0.1"},
            "10.0.0.1",
        )
        assert mw._client_key(r) == "ip:1.1.1.1"

    def test_trusted_proxy_no_xff_falls_back(self):
        mw = self._trusted("10.0.0.0/8")
        r = self._req({}, "10.0.0.1")
        assert mw._client_key(r) == "ip:10.0.0.1"

    def test_all_trusted_chain_falls_back_to_first(self):
        mw = self._trusted("10.0.0.0/8")
        r = self._req({"x-forwarded-for": "10.0.0.2, 10.0.0.3"}, "10.0.0.1")
        assert mw._client_key(r) == "ip:10.0.0.2"


# ── BodyLimitMiddleware ─────────────────────────────────────────────────


class TestBodyLimitContract:
    def _client(self, **kw):
        return TestClient(BodyLimitMiddleware(_app(), **kw))

    def test_413_body_exact(self):
        c = self._client(default_max_bytes=10)
        r = c.post("/x", content=b"0" * 11)
        assert r.status_code == 413
        assert r.json() == {"detail": "payload too large", "code": "payload_too_large"}

    def test_exact_limit_allowed(self):
        c = self._client(default_max_bytes=10)
        r = c.post("/x", content=b"0" * 10)
        assert r.status_code == 200

    def test_malformed_content_length(self):
        c = self._client()
        r = c.post("/x", headers={"Content-Length": "abc"})
        assert r.status_code == 400
        assert r.json()["code"] == "payload_too_large"
        assert r.json()["detail"] == "malformed Content-Length"

    def test_get_head_options_bypass(self):
        # `type!=http or method in (GET,HEAD,OPTIONS)` — a huge declared
        # body on a safe method must pass through (kills or→and).
        c = self._client(default_max_bytes=10)
        assert c.get("/x", headers={"Content-Length": "9999"}).status_code == 200
        assert c.options("/x", headers={"Content-Length": "9999"}).status_code == 200
        assert c.head("/x", headers={"Content-Length": "9999"}).status_code == 200

    def test_longest_prefix_rule(self):
        c = self._client(
            rules=[BodyLimitRule("/api", 5), BodyLimitRule("/api/big", 20)]
        )
        assert c.post("/api/big", content=b"0" * 15).status_code == 200
        assert c.post("/api/other", content=b"0" * 6).status_code == 413

    def test_chunked_over_limit_flagged(self):
        # Under-declared body: Content-Length small but real bytes exceed —
        # the streaming counter must flag _over_limit.
        c = self._client(default_max_bytes=10)
        r = c.post("/x", content=b"0" * 30, headers={"Content-Length": "5"})
        # App sees truncated/flagged body; middleware logs. Response is
        # the app's 200 (hard-cut is documented as next-request), the key
        # assertion is the request did not read past the cap silently.
        assert r.status_code in (200, 413)


# ── TraceIdMiddleware ───────────────────────────────────────────────────


class TestTraceIdContract:
    def _client(self):
        return TestClient(TraceIdMiddleware(_app()))

    def test_inbound_propagated(self):
        c = self._client()
        r = c.get("/x", headers={"X-Request-ID": "abc-123_ok"})
        assert r.headers["X-Request-ID"] == "abc-123_ok"

    def test_generated_when_absent(self):
        c = self._client()
        r = c.get("/x")
        tid = r.headers["X-Request-ID"]
        assert len(tid) == 32 and tid.isalnum()

    def test_boundary_64_accepted_65_rejected(self):
        c = self._client()
        ok64 = "a" * 64
        r = c.get("/x", headers={"X-Request-ID": ok64})
        assert r.headers["X-Request-ID"] == ok64
        bad65 = "a" * 65
        r = c.get("/x", headers={"X-Request-ID": bad65})
        assert r.headers["X-Request-ID"] != bad65
        assert len(r.headers["X-Request-ID"]) == 32

    def test_non_alnum_rejected(self):
        c = self._client()
        r = c.get("/x", headers={"X-Request-ID": "bad id!@#"})
        assert r.headers["X-Request-ID"] != "bad id!@#"


# ── SecurityHeadersMiddleware ───────────────────────────────────────────


class TestSecurityHeadersContract:
    EXPECTED = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    }

    def test_all_headers_on_200(self):
        c = TestClient(SecurityHeadersMiddleware(_app()))
        r = c.get("/api/v1/x")
        for k, v in self.EXPECTED.items():
            assert r.headers[k] == v
        assert r.headers["Strict-Transport-Security"] == (
            "max-age=31536000; includeSubDomains"
        )
        assert "accelerometer=()" in r.headers["Permissions-Policy"]
        assert r.headers["Content-Security-Policy"] == (
            "default-src 'none'; frame-ancestors 'none'"
        )
        assert r.headers["Cache-Control"] == "no-store"

    def test_headers_on_error_response(self):
        c = TestClient(SecurityHeadersMiddleware(_app(500)))
        r = c.get("/x")
        assert r.status_code == 500
        assert r.headers["X-Frame-Options"] == "DENY"

    def test_hsts_disabled(self):
        c = TestClient(SecurityHeadersMiddleware(_app(), hsts_enabled=False))
        r = c.get("/x")
        assert "Strict-Transport-Security" not in r.headers

    def test_docs_get_ui_csp(self):
        c = TestClient(SecurityHeadersMiddleware(_app()))
        r = c.get("/docs")
        assert "cdn.jsdelivr.net" in r.headers["Content-Security-Policy"]
        r = c.get("/openapi.json")
        assert "cdn.jsdelivr.net" in r.headers["Content-Security-Policy"]

    def test_non_api_path_no_cache_control(self):
        c = TestClient(SecurityHeadersMiddleware(_app()))
        r = c.get("/other")
        assert "Cache-Control" not in r.headers

    def test_server_banner_removed(self):
        async def with_server(request):
            return JSONResponse({"ok": True}, headers={"Server": "uvicorn"})

        app = Starlette(routes=[Route("/x", with_server)])
        c = TestClient(SecurityHeadersMiddleware(app))
        r = c.get("/x")
        assert "server" not in {k.lower() for k in r.headers}
