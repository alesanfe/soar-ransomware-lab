#!/usr/bin/env python3
"""Mutation-hardening tests for preauth_rate_limit, body_limit,
security_headers and trace_id middleware — exact contracts."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from soar_lab.interfaces.api.middleware.body_limit import (
    BodyLimitMiddleware,
    BodyLimitRule,
)
from soar_lab.interfaces.api.middleware.preauth_rate_limit import (
    PreAuthRateLimitMiddleware,
)
from soar_lab.interfaces.api.middleware.security_headers import (
    _API_CSP,
    _DOC_CSP,
    SecurityHeadersMiddleware,
)
from soar_lab.interfaces.api.middleware.trace_id import (
    TRACE_ID_HEADER,
    TraceIdMiddleware,
)


def _scope(path="/x", method="POST", client="10.0.0.1", headers=None, type_="http"):
    return {
        "type": type_,
        "method": method,
        "path": path,
        "headers": headers or [],
        "client": (client, 1234) if client else None,
    }


async def _call_asgi(mw, scope, messages=None):
    """Invoke a pure-ASGI middleware, capture sent messages."""
    msgs = list(messages or [{"type": "http.request", "body": b"", "more_body": False}])
    sent = []

    async def receive():
        return msgs.pop(0) if msgs else {"type": "http.disconnect"}

    async def send(m):
        sent.append(m)

    async def app(scope, receive, send):
        await PlainTextResponse("ok")(scope, receive, send)

    mw.app = app
    await mw(scope, receive, send)
    return sent


class TestPreAuthClientIp:
    def test_unknown_and_invalid(self):
        mw = PreAuthRateLimitMiddleware(None)
        assert mw._client_ip(_scope(client=None)) == "unknown"
        assert mw._client_ip(_scope(client="not-an-ip")) == "not-an-ip"

    def test_untrusted_ignores_xff(self):
        mw = PreAuthRateLimitMiddleware(None, trusted_proxies=["192.168.0.0/16"])
        s = _scope(headers=[(b"x-forwarded-for", b"1.2.3.4")])
        assert mw._client_ip(s) == "10.0.0.1"

    def test_trusted_uses_rightmost_untrusted(self):
        mw = PreAuthRateLimitMiddleware(None, trusted_proxies=["10.0.0.0/8"])
        s = _scope(headers=[(b"x-forwarded-for", b"1.1.1.1, 2.2.2.2, 10.9.9.9")])
        assert mw._client_ip(s) == "2.2.2.2"

    def test_trusted_invalid_hop_skipped(self):
        mw = PreAuthRateLimitMiddleware(None, trusted_proxies=["10.0.0.0/8"])
        s = _scope(headers=[(b"x-forwarded-for", b"1.1.1.1, junk")])
        assert mw._client_ip(s) == "1.1.1.1"

    def test_all_trusted_falls_back_peer(self):
        mw = PreAuthRateLimitMiddleware(None, trusted_proxies=["0.0.0.0/0"])
        s = _scope(headers=[(b"x-forwarded-for", b"1.1.1.1")])
        assert mw._client_ip(s) == "10.0.0.1"

    def test_invalid_cidr_warns(self, caplog):
        with caplog.at_level("WARNING"):
            mw = PreAuthRateLimitMiddleware(None, trusted_proxies=["bad", "10.0.0.0/8"])
        assert "Ignoring invalid pre-auth trusted-proxy CIDR" in caplog.text
        assert len(mw._trusted) == 1


class TestPreAuthAllow:
    def test_window_boundary_and_retry(self):
        mw = PreAuthRateLimitMiddleware(None, per_minute=2)
        t = 1000.0
        assert mw._allow("k", t) == (True, 0)
        assert mw._allow("k", t) == (True, 0)
        ok, retry = mw._allow("k", t + 10)
        assert ok is False and retry == 50  # 60-(10)
        # at exactly 60s the first hit falls out
        assert mw._allow("k", t + 60.0) == (True, 0)

    def test_sweep(self):
        mw = PreAuthRateLimitMiddleware(None, per_minute=2)
        t = 1000.0
        mw._last_sweep = t
        mw._allow("a", t)
        mw._hits["dead"] = __import__("collections").deque([t - 61])
        mw._allow("a", t + 121)
        assert "dead" not in mw._hits

    async def test_call_429_contract(self):
        mw = PreAuthRateLimitMiddleware(None, per_minute=1)
        mw._hits["10.0.0.1"] = __import__("collections").deque([time.time()])
        sent = await _call_asgi(mw, _scope())
        assert sent[0]["status"] == 429
        hdrs = dict(sent[0]["headers"])
        assert hdrs[b"retry-after"] >= b"1"
        assert hdrs[b"x-ratelimit-limit"] == b"1"
        assert hdrs[b"x-ratelimit-remaining"] == b"0"
        body = sent[1]["body"]
        assert b"Rate limit exceeded" in body and b"rate_limited" in body

    async def test_non_http_and_disabled_pass(self):
        mw = PreAuthRateLimitMiddleware(None, per_minute=1, enabled=False)
        mw._hits["10.0.0.1"] = __import__("collections").deque([time.time()] * 5)
        sent = await _call_asgi(mw, _scope())
        assert sent[0]["status"] == 200
        mw2 = PreAuthRateLimitMiddleware(None, per_minute=1)
        sent2 = await _call_asgi(mw2, _scope(type_="websocket"))
        assert sent2[0]["status"] == 200


class TestBodyLimit:
    def test_longest_prefix(self):
        mw = BodyLimitMiddleware(
            None,
            rules=[BodyLimitRule("/api", 100), BodyLimitRule("/api/ingest", 10)],
        )
        assert mw._limit_for("/api/ingest/x") == 10
        assert mw._limit_for("/api/other") == 100
        assert mw._limit_for("/web") == 1_048_576

    async def test_methods_bypass(self):
        for m in ("GET", "HEAD", "OPTIONS"):
            mw = BodyLimitMiddleware(None, default_max_bytes=1)
            sent = await _call_asgi(mw, _scope(method=m))
            assert sent[0]["status"] == 200, m

    async def test_non_http_bypass(self):
        mw = BodyLimitMiddleware(None, default_max_bytes=1)
        sent = await _call_asgi(mw, _scope(type_="websocket"))
        assert sent[0]["status"] == 200

    async def test_malformed_content_length_400(self):
        mw = BodyLimitMiddleware(None, default_max_bytes=100)
        sent = await _call_asgi(
            mw, _scope(headers=[(b"content-length", b"abc")])
        )
        assert sent[0]["status"] == 400
        assert b"malformed Content-Length" in sent[1]["body"]
        assert b"payload_too_large" in sent[1]["body"]

    async def test_declared_over_limit_413(self):
        mw = BodyLimitMiddleware(None, default_max_bytes=100)
        sent = await _call_asgi(
            mw, _scope(headers=[(b"content-length", b"101")])
        )
        assert sent[0]["status"] == 413
        assert b"payload too large" in sent[1]["body"]

    async def test_declared_exact_limit_ok(self):
        mw = BodyLimitMiddleware(None, default_max_bytes=100)
        sent = await _call_asgi(
            mw, _scope(headers=[(b"content-length", b"100")])
        )
        assert sent[0]["status"] == 200

    async def test_streamed_over_limit_warns(self, caplog):
        mw = BodyLimitMiddleware(None, default_max_bytes=4)
        msgs = [
            {"type": "http.request", "body": b"12345", "more_body": False},
        ]
        sent = []

        async def receive():
            return msgs.pop(0) if msgs else {"type": "http.disconnect"}

        async def send(m):
            sent.append(m)

        async def app(scope, receive, send):
            msg = await receive()  # drain the body -> triggers the cap
            assert msg.get("body", b"") == b""  # truncated to empty
            await PlainTextResponse("ok")(scope, receive, send)

        mw.app = app
        with caplog.at_level("WARNING"):
            await mw(_scope(), receive, send)
        assert "exceeded 4 bytes mid-stream" in caplog.text


class TestSecurityHeadersExact:
    def _app(self, hsts=True):
        async def ok(request):
            return PlainTextResponse("x")

        app = Starlette(routes=[Route("/x", ok), Route("/docs", ok), Route("/api/y", ok)])
        app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=hsts)
        return TestClient(app)

    def test_full_header_set(self):
        r = self._app().get("/x")
        h = r.headers
        assert h["X-Content-Type-Options"] == "nosniff"
        assert h["X-Frame-Options"] == "DENY"
        assert h["Referrer-Policy"] == "no-referrer"
        assert h["Permissions-Policy"].startswith("accelerometer=()")
        assert h["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
        assert h["Content-Security-Policy"] == _API_CSP
        assert "server" not in h

    def test_hsts_off(self):
        r = self._app(hsts=False).get("/x")
        assert "strict-transport-security" not in r.headers

    def test_docs_csp_and_cache_control(self):
        r = self._app().get("/docs")
        assert r.headers["Content-Security-Policy"] == _DOC_CSP
        assert "cache-control" not in r.headers
        r2 = self._app().get("/api/y")
        assert r2.headers["Cache-Control"] == "no-store"
        assert r2.headers["Content-Security-Policy"] == _API_CSP


class TestTraceId:
    def _app(self):
        async def ok(request):
            return PlainTextResponse("x")

        app = Starlette(routes=[Route("/x", ok)])
        app.add_middleware(TraceIdMiddleware)
        return TestClient(app)

    def test_valid_inbound_propagated(self):
        c = self._app()
        r = c.get("/x", headers={TRACE_ID_HEADER: "abc-123_DEF"})
        assert r.headers[TRACE_ID_HEADER] == "abc-123_DEF"

    @pytest.mark.parametrize("bad", ["x" * 65, "has space", "semi;colon", ""])
    def test_invalid_inbound_regenerated(self, bad):
        c = self._app()
        r = c.get("/x", headers={TRACE_ID_HEADER: bad})
        tid = r.headers[TRACE_ID_HEADER]
        assert len(tid) == 32 and tid != bad

    def test_boundary_64_accepted(self):
        c = self._app()
        r = c.get("/x", headers={TRACE_ID_HEADER: "a" * 64})
        assert r.headers[TRACE_ID_HEADER] == "a" * 64
