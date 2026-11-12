"""Tests for BodyLimitMiddleware (DOS-001, pure-ASGI body cap)."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from soar_lab.interfaces.api.middleware.body_limit import (
    BodyLimitMiddleware,
    BodyLimitRule,
)


def _app(**mw_kwargs) -> FastAPI:
    inner = FastAPI()

    @inner.post("/echo")
    async def echo(request: Request):
        body = await request.body()
        return {"size": len(body)}

    @inner.post("/api/v1/alerts")
    async def alerts(request: Request):
        body = await request.body()
        return {"size": len(body)}

    inner.add_middleware(BodyLimitMiddleware, **mw_kwargs)
    return inner


class TestLimitFor:
    def test_default_when_no_rule_matches(self):
        mw = BodyLimitMiddleware(None, default_max_bytes=100)
        assert mw._limit_for("/anything") == 100

    def test_longest_prefix_wins(self):
        mw = BodyLimitMiddleware(
            None,
            default_max_bytes=10,
            rules=[BodyLimitRule("/api", 50), BodyLimitRule("/api/v1/alerts", 500)],
        )
        assert mw._limit_for("/api/v1/alerts") == 500
        assert mw._limit_for("/api/v1/other") == 50
        assert mw._limit_for("/web") == 10


class TestPassthrough:
    def test_get_passes_regardless(self):
        resp = TestClient(_app(default_max_bytes=1)).get("/echo")
        assert resp.status_code == 405 or resp.status_code == 200

    def test_options_passes(self):
        resp = TestClient(_app(default_max_bytes=1)).options("/echo")
        assert resp.status_code != 413


class TestContentLength:
    def test_under_limit_accepted(self):
        resp = TestClient(_app(default_max_bytes=100)).post("/echo", content=b"abc")
        assert resp.status_code == 200
        assert resp.json() == {"size": 3}

    def test_over_limit_rejected_413(self):
        resp = TestClient(_app(default_max_bytes=4)).post("/echo", content=b"12345")
        assert resp.status_code == 413
        assert resp.json()["code"] == "payload_too_large"

    def test_malformed_content_length_400(self):
        # Inject a non-numeric Content-Length directly at ASGI level.
        called = {}

        async def asgi_app(scope, receive, send):
            called["ran"] = True

        mw = BodyLimitMiddleware(asgi_app, default_max_bytes=100)
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/echo",
            "headers": [(b"content-length", b"abc")],
        }
        messages = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            messages.append(message)

        import asyncio

        asyncio.run(mw(scope, receive, send))
        assert "ran" not in called
        assert messages[0]["type"] == "http.response.start"
        assert messages[0]["status"] == 400

    def test_exact_limit_accepted(self):
        resp = TestClient(_app(default_max_bytes=5)).post("/echo", content=b"12345")
        assert resp.status_code == 200


class TestStreamingAccounting:
    def test_chunked_over_limit_truncated_and_warned(self, caplog):
        # Chunked transfer → no Content-Length → stream accounting applies.
        chunks = (b"x" * 600 for _ in range(4))  # 2400B > 1000B rule

        with caplog.at_level(logging.WARNING):
            resp = TestClient(
                _app(rules=[BodyLimitRule("/api/v1/alerts", 1000)])
            ).post("/api/v1/alerts", content=chunks)

        # Documented behavior: the app sees a truncated body and still
        # responds; the over-limit hit is logged for the next request.
        assert resp.status_code == 200
        assert "exceeded 1000 bytes mid-stream" in caplog.text

    def test_chunked_under_limit_ok(self):
        chunks = (b"x" * 10 for _ in range(3))
        resp = TestClient(_app(default_max_bytes=100)).post("/echo", content=chunks)
        assert resp.status_code == 200

    def test_read_timeout_flags_over_limit(self, caplog):
        # Simulated stall: monotonic jumps past _READ_TIMEOUT_S mid-read.
        import logging

        import soar_lab.interfaces.api.middleware.body_limit as bl

        received_by_app = []

        class StallApp:
            async def __call__(self, scope, receive, send):
                m = await receive()
                received_by_app.append(m)
                from starlette.responses import JSONResponse as JR

                await JR({"ok": True})(scope, receive, send)

        mw = BodyLimitMiddleware(StallApp(), default_max_bytes=10**6)
        scope = {"type": "http", "method": "POST", "path": "/echo", "headers": []}

        async def receive():
            return {"type": "http.request", "body": b"a", "more_body": True}

        async def send(message):
            pass

        # monotonic advancing 100s per call: whatever value ``started``
        # captures, the next read is >_READ_TIMEOUT_S later (asyncio also
        # calls monotonic, so a fixed iterator would be consumed early).
        t = [0.0]

        def advancing():
            t[0] += 100.0
            return t[0]

        orig = bl.time.monotonic
        bl.time.monotonic = advancing
        try:
            import asyncio

            with caplog.at_level(logging.WARNING):
                asyncio.run(mw(scope, receive, send))
        finally:
            bl.time.monotonic = orig

        # The timeout truncated the stream: the app saw an empty final body.
        assert received_by_app[0]["body"] == b""
        assert received_by_app[0]["more_body"] is False
        assert "mid-stream" in caplog.text
