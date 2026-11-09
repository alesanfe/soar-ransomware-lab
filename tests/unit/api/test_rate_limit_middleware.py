"""Unit tests for the RateLimitMiddleware.

Verifies sliding-window enforcement, per-path budgets, token/IP keying,
exempt paths, 429 responses with informational headers, and the
enabled/disabled configuration switch.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from soar_lab.interfaces.api.middleware import RateLimitMiddleware, RateLimitRule

__all__ = [
    "TestRateLimitEnforcement",
    "TestRateLimitHeaders",
    "TestRateLimitRules",
    "TestRateLimitKeying",
    "TestRateLimitExempt",
    "TestRateLimitToggle",
]


def _make_app(**kwargs) -> FastAPI:
    """Create a minimal FastAPI app with the RateLimitMiddleware."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, **kwargs)

    @app.get("/api/v1/resource")
    async def resource():
        return {"ok": True}

    @app.post("/auth/login")
    async def login():
        return {"ok": True}

    @app.post("/api/v1/contain")
    async def contain():
        return {"ok": True}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


class TestRateLimitEnforcement:
    """Requests beyond the per-minute budget must be throttled with 429."""

    def test_requests_under_limit_pass(self):
        client = TestClient(_make_app(per_minute=5))
        for _ in range(5):
            assert client.get("/api/v1/resource").status_code == 200

    def test_request_over_limit_returns_429(self):
        client = TestClient(_make_app(per_minute=3))
        for _ in range(3):
            assert client.get("/api/v1/resource").status_code == 200
        resp = client.get("/api/v1/resource")
        assert resp.status_code == 429
        body = resp.json()
        assert body["detail"] == "Rate limit exceeded"
        assert body["code"] == "rate_limited"
        assert body["retry_after_seconds"] >= 1

    def test_spoofed_xff_does_not_bypass_limit(self):
        """XFF from an untrusted peer must not create a fresh bucket.

        The previous behaviour keyed the limiter on client-supplied
        ``X-Forwarded-For`` unconditionally — rotating the header bypassed
        throttling entirely. Buckets are keyed on the real peer unless it
        is a configured trusted proxy (covered by test_fase0_hardening).
        """
        app = _make_app(per_minute=2)
        c1 = TestClient(app)
        c1.get("/api/v1/resource", headers={"x-forwarded-for": "10.0.0.1"})
        c1.get("/api/v1/resource", headers={"x-forwarded-for": "10.0.0.1"})
        blocked = c1.get("/api/v1/resource", headers={"x-forwarded-for": "10.0.0.1"})
        assert blocked.status_code == 429
        # A forged different XFF from the SAME untrusted peer must not reset
        # the budget — it stays rate limited.
        other = c1.get("/api/v1/resource", headers={"x-forwarded-for": "10.0.0.2"})
        assert other.status_code == 429


class TestRateLimitHeaders:
    """Rate limit informational headers must be present on responses."""

    def test_headers_on_successful_request(self):
        client = TestClient(_make_app(per_minute=10))
        resp = client.get("/api/v1/resource")
        assert resp.headers["X-RateLimit-Limit"] == "10"
        assert resp.headers["X-RateLimit-Remaining"] == "9"
        assert "X-RateLimit-Reset" in resp.headers

    def test_retry_after_header_on_429(self):
        client = TestClient(_make_app(per_minute=1))
        client.get("/api/v1/resource")
        resp = client.get("/api/v1/resource")
        assert resp.status_code == 429
        retry_after = int(resp.headers["Retry-After"])
        assert 1 <= retry_after <= 60
        assert resp.headers["X-RateLimit-Remaining"] == "0"


class TestRateLimitRules:
    """Stricter per-path budgets override the global one."""

    def test_strict_rule_applies_to_prefix(self):
        client = TestClient(_make_app(per_minute=100, rules=[RateLimitRule("/auth", 2)]))
        assert client.post("/auth/login").status_code == 200
        assert client.post("/auth/login").status_code == 200
        assert client.post("/auth/login").status_code == 429

    def test_global_budget_still_applies_to_other_paths(self):
        client = TestClient(_make_app(per_minute=3, rules=[RateLimitRule("/auth", 50)]))
        for _ in range(3):
            assert client.get("/api/v1/resource").status_code == 200
        assert client.get("/api/v1/resource").status_code == 429

    def test_longest_prefix_wins(self):
        client = TestClient(
            _make_app(
                per_minute=100,
                rules=[
                    RateLimitRule("/api", 10),
                    RateLimitRule("/api/v1/contain", 1),
                ],
            )
        )
        assert client.post("/api/v1/contain").status_code == 200
        assert client.post("/api/v1/contain").status_code == 429


class TestRateLimitKeying:
    """Bearer tokens and IPs produce independent budgets."""

    def test_different_tokens_have_independent_budgets(self):
        client = TestClient(_make_app(per_minute=1))
        r1 = client.get("/api/v1/resource", headers={"authorization": "Bearer token-a"})
        r2 = client.get("/api/v1/resource", headers={"authorization": "Bearer token-b"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        r3 = client.get("/api/v1/resource", headers={"authorization": "Bearer token-a"})
        assert r3.status_code == 429


class TestRateLimitExempt:
    """Exempt paths (health checks, docs, static) are never throttled."""

    def test_exempt_path_never_limited(self):
        client = TestClient(_make_app(per_minute=1, exempt_paths=("/health",)))
        for _ in range(5):
            assert client.get("/health").status_code == 200

    def test_static_prefix_always_exempt(self):
        app = _make_app(per_minute=1)

        @app.get("/static-docs/file.css")
        async def static_file():
            return {"ok": True}

        client = TestClient(app)
        for _ in range(3):
            assert client.get("/static-docs/file.css").status_code == 200


class TestRateLimitToggle:
    """The enabled flag must fully bypass the limiter."""

    def test_disabled_middleware_never_limits(self):
        client = TestClient(_make_app(per_minute=1, enabled=False))
        for _ in range(5):
            assert client.get("/api/v1/resource").status_code == 200


class TestClientKeySeparation:
    """_client_key must isolate per-credential buckets."""

    def test_jwt_clients_do_not_share_bucket(self):
        """Bug: keying on auth[7:33] put every JWT in the SAME bucket —
        all standard JWTs share the ~26-char header prefix."""
        mw = RateLimitMiddleware(None)

        class _Req:
            def __init__(self, tok):
                self.headers = {"authorization": f"Bearer {tok}"}
                self.client = None

        t1 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.sig1"
        t2 = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.bbb.sig2"
        assert mw._client_key(_Req(t1)) != mw._client_key(_Req(t2))


class TestInMemoryStoreSweep:
    """Stale keys are swept once _last_sweep lapses two windows."""

    async def test_sweep_removes_stale_keys(self):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            InMemorySlidingWindowStore,
        )

        store = InMemorySlidingWindowStore()
        store._last_sweep = 0.0  # align with the fake clock
        await store.record("old-client", now=0.0, window_s=60.0)
        assert "old-client" in store._hits

        # Two windows later + one hit: the stale key must be swept
        await store.record("new-client", now=121.0, window_s=60.0)
        await store.record("new-client", now=122.0, window_s=60.0)
        assert "old-client" not in store._hits

    async def test_sweep_preserves_active_keys(self):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            InMemorySlidingWindowStore,
        )

        store = InMemorySlidingWindowStore()
        store._last_sweep = 0.0  # align with the fake clock
        await store.record("a", now=0.0, window_s=60.0)
        await store.record("b", now=100.0, window_s=60.0)  # b active
        await store.record("c", now=130.0, window_s=60.0)  # triggers sweep
        assert "b" in store._hits
        assert "a" not in store._hits


class TestRedisStore:
    def test_from_url_constructs_client(self, monkeypatch):
        from soar_lab.interfaces.api.middleware.rate_limit import (
            RedisSlidingWindowStore,
        )

        calls = {}
        import redis.asyncio as aioredis

        monkeypatch.setattr(aioredis, "from_url", lambda u: calls.setdefault("u", u) or "cli")
        RedisSlidingWindowStore.from_url("redis://x:6379/0")
        assert calls["u"] == "redis://x:6379/0"

    async def test_record_pipelines_window_ops(self):
        from unittest.mock import AsyncMock

        from soar_lab.interfaces.api.middleware.rate_limit import (
            RedisSlidingWindowStore,
        )

        pipe = AsyncMock()
        pipe.execute.return_value = (None, None, 4, [(b"m", 5.0)], None)
        client = AsyncMock()
        client.pipeline = lambda **_kw: pipe

        store = RedisSlidingWindowStore(client)
        count, oldest = await store.record("k", now=10.0, window_s=60.0)
        assert count == 4
        assert oldest == 5.0
        pipe.zremrangebyscore.assert_called_once_with("ratelimit:k", "-inf", -50.0)
        pipe.expire.assert_called_once_with("ratelimit:k", 62)


class TestTrustedProxies:
    def _req(self, client_ip, xff=""):
        class _C:
            host = client_ip

        class _R:
            headers = {"x-forwarded-for": xff} if xff else {}
            client = _C()

        return _R()

    def test_invalid_cidr_warned_and_ignored(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            mw = RateLimitMiddleware(None, trusted_proxies=["10.0.0.0/8", "garbage"])
        assert len(mw._trusted_nets) == 1
        assert "garbage" in caplog.text

    def test_non_ip_hop_skipped_in_chain(self):
        mw = RateLimitMiddleware(None, trusted_proxies=["192.168.0.0/16"])
        # proxy peer trusted; rightmost hop garbage → skipped → real client
        key = mw._client_key(self._req("192.168.1.5", "1.2.3.4, not-an-ip"))
        assert key == "ip:1.2.3.4"

    def test_fully_trusted_chain_falls_back_to_leftmost(self):
        mw = RateLimitMiddleware(None, trusted_proxies=["192.168.0.0/16"])
        key = mw._client_key(self._req("192.168.1.5", "192.168.2.2, 192.168.3.3"))
        assert key == "ip:192.168.2.2"

    def test_malformed_first_hop_falls_back_to_peer(self):
        mw = RateLimitMiddleware(None, trusted_proxies=["192.168.0.0/16"])
        key = mw._client_key(self._req("192.168.1.5", "junk-value"))
        assert key == "ip:192.168.1.5"

    def test_untrusted_peer_ignores_xff(self):
        mw = RateLimitMiddleware(None, trusted_proxies=["192.168.0.0/16"])
        key = mw._client_key(self._req("8.8.8.8", "1.2.3.4"))
        assert key == "ip:8.8.8.8"
