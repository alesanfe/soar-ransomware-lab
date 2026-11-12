"""Tests for PreAuthRateLimitMiddleware (DOS-002, pre-auth IP budget)."""

import time
from collections import deque
from unittest.mock import patch

from soar_lab.interfaces.api.middleware.preauth_rate_limit import (
    PreAuthRateLimitMiddleware,
)


def _mw(**kw):
    async def ok_app(scope, receive, send):
        from starlette.responses import JSONResponse

        await JSONResponse({"ok": True})(scope, receive, send)

    return PreAuthRateLimitMiddleware(ok_app, **kw)


def _scope(client="10.0.0.1", headers=None):
    return {
        "type": "http",
        "method": "GET",
        "path": "/",
        "client": (client, 1234),
        "headers": headers or [],
    }


async def _call(mw, scope):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b""}

    async def send(message):
        sent.append(message)

    await mw(scope, receive, send)
    start = next(m for m in sent if m["type"] == "http.response.start")
    return start["status"], dict(start.get("headers", []))


class TestClientIp:
    def test_no_client_unknown(self):
        assert _mw()._client_ip({"type": "http"}) == "unknown"

    def test_unparseable_host_returned_verbatim(self):
        assert _mw()._client_ip(_scope(client="not-an-ip")) == "not-an-ip"

    def test_untrusted_client_ignores_xff(self):
        mw = _mw(trusted_proxies=["192.168.0.0/16"])
        scope = _scope(client="10.0.0.1", headers=[(b"x-forwarded-for", b"1.2.3.4")])
        assert mw._client_ip(scope) == "10.0.0.1"

    def test_trusted_proxy_honours_xff(self):
        mw = _mw(trusted_proxies=["10.0.0.0/8"])
        scope = _scope(client="10.0.0.9", headers=[(b"x-forwarded-for", b"1.2.3.4, 10.0.0.9")])
        assert mw._client_ip(scope) == "1.2.3.4"

    def test_xff_all_trusted_falls_back_to_peer(self):
        mw = _mw(trusted_proxies=["10.0.0.0/8"])
        scope = _scope(client="10.0.0.9", headers=[(b"x-forwarded-for", b"10.0.0.1")])
        assert mw._client_ip(scope) == "10.0.0.9"

    def test_xff_skips_invalid_hops(self):
        mw = _mw(trusted_proxies=["10.0.0.0/8"])
        scope = _scope(
            client="10.0.0.9", headers=[(b"x-forwarded-for", b"1.2.3.4, garbage, 10.0.0.5")]
        )
        assert mw._client_ip(scope) == "1.2.3.4"

    def test_invalid_proxy_cidr_ignored(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            _mw(trusted_proxies=["not-a-cidr"])
        assert "Ignoring invalid pre-auth trusted-proxy CIDR" in caplog.text


class TestAllow:
    def test_window_expiry_frees_slots(self):
        mw = _mw(per_minute=1)
        mw._hits["ip"].append(0.0)  # stale entry
        allowed, _ = mw._allow("ip", now=61.0)
        assert allowed is True

    def test_over_budget_returns_retry_seconds(self):
        mw = _mw(per_minute=2)
        mw._allow("ip", now=100.0)
        mw._allow("ip", now=100.5)
        allowed, retry = mw._allow("ip", now=101.0)
        assert allowed is False
        assert retry >= 1

    def test_sweep_removes_stale_keys(self):
        mw = _mw(per_minute=60)
        mw._hits["stale"] = deque([0.0])
        mw._hits["empty"] = deque()
        mw._last_sweep = 0.0
        allowed, _ = mw._allow("fresh", now=200.0)
        assert allowed is True
        assert "stale" not in mw._hits and "empty" not in mw._hits


class TestCall:
    def test_disabled_passthrough(self):
        import asyncio

        status, _ = asyncio.run(_call(_mw(enabled=False), _scope()))
        assert status == 200

    def test_non_http_passthrough(self):
        import asyncio

        reached = []

        async def app(scope, receive, send):
            reached.append(scope["type"])

        mw = PreAuthRateLimitMiddleware(app, per_minute=1)
        asyncio.run(mw({"type": "websocket"}, lambda: None, lambda m: None))
        assert reached == ["websocket"]

    def test_under_budget_ok(self):
        import asyncio

        status, _ = asyncio.run(_call(_mw(per_minute=5), _scope()))
        assert status == 200

    def test_over_budget_429_with_headers(self):
        import asyncio

        mw = _mw(per_minute=1)
        asyncio.run(_call(mw, _scope()))
        status, headers = asyncio.run(_call(mw, _scope()))
        assert status == 429
        assert headers[b"retry-after"]
        assert headers[b"x-ratelimit-remaining"] == b"0"

    def test_separate_ips_have_separate_budgets(self):
        import asyncio

        mw = _mw(per_minute=1)
        asyncio.run(_call(mw, _scope(client="10.0.0.1")))
        status, _ = asyncio.run(_call(mw, _scope(client="10.0.0.2")))
        assert status == 200
