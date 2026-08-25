"""Unit tests for the TraceIdMiddleware.

Verifies that:
- A new trace ID is generated when no X-Request-ID header is sent.
- An incoming X-Request-ID is propagated (reused) in the response.
- The trace ID is accessible via get_trace_id() within a request scope.
- The trace_id is injected into StructuredLogger output during requests.
"""

import logging
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from soar_lab.interfaces.api.middleware import (
    TRACE_ID_HEADER,
    TraceIdMiddleware,
    get_trace_id,
)
from soar_lab.logging.structured import StructuredLogger

__all__ = [
    "TestTraceIdGeneration",
    "TestTraceIdPropagation",
    "TestTraceIdContext",
    "TestStructuredLoggerTraceId",
]


def _make_app() -> FastAPI:
    """Create a minimal FastAPI app with the TraceIdMiddleware."""
    app = FastAPI()
    app.add_middleware(TraceIdMiddleware)

    @app.get("/echo-trace")
    async def echo_trace():
        return {"trace_id": get_trace_id()}

    return app


@pytest.fixture()
def client():
    """TestClient for the minimal trace-ID app."""
    return TestClient(_make_app())


class TestTraceIdGeneration:
    """Tests for automatic trace ID generation."""

    def test_generates_trace_id_when_absent(self, client):
        """Response must include an X-Request-ID when none was sent."""
        resp = client.get("/echo-trace")
        assert resp.status_code == 200
        trace_id = resp.headers.get(TRACE_ID_HEADER)
        assert trace_id is not None
        assert len(trace_id) == 32  # uuid4 hex
        # The endpoint should see the same trace_id via context
        assert resp.json()["trace_id"] == trace_id

    def test_generated_trace_id_is_valid_uuid_hex(self, client):
        """Generated trace ID must be a valid UUID4 hex string."""
        resp = client.get("/echo-trace")
        trace_id = resp.headers[TRACE_ID_HEADER]
        # Should not raise
        uuid.UUID(hex=trace_id)


class TestTraceIdPropagation:
    """Tests for incoming trace ID propagation."""

    def test_propagates_incoming_trace_id(self, client):
        """An incoming X-Request-ID must be reused in the response."""
        custom_id = "my-custom-trace-id-123"
        resp = client.get("/echo-trace", headers={TRACE_ID_HEADER: custom_id})
        assert resp.headers[TRACE_ID_HEADER] == custom_id
        assert resp.json()["trace_id"] == custom_id

    def test_different_trace_ids_per_request(self, client):
        """Two requests without X-Request-ID must get different trace IDs."""
        r1 = client.get("/echo-trace")
        r2 = client.get("/echo-trace")
        assert r1.headers[TRACE_ID_HEADER] != r2.headers[TRACE_ID_HEADER]


class TestTraceIdContext:
    """Tests for context variable lifecycle."""

    def test_trace_id_none_outside_request(self):
        """get_trace_id() must return None outside a request scope."""
        assert get_trace_id() is None


class TestStructuredLoggerTraceId:
    """Tests that StructuredLogger automatically includes trace_id."""

    def test_structured_logger_includes_trace_id(self, client, caplog):
        """StructuredLogger must inject trace_id into log records during a request."""
        app = _make_app()

        captured = {}

        @app.get("/log-test")
        async def log_test():
            slog = StructuredLogger("test_trace", level=logging.INFO)
            slog.info("test message")
            captured["trace_id"] = get_trace_id()
            return {"ok": True}

        client2 = TestClient(app)
        with caplog.at_level(logging.INFO, logger="test_trace"):
            resp = client2.get("/log-test", headers={TRACE_ID_HEADER: "log-trace-abc"})
        assert resp.status_code == 200
        assert captured["trace_id"] == "log-trace-abc"
        # At least one log record should contain the trace_id
        trace_found = any(
            "log-trace-abc" in record.getMessage()
            for record in caplog.records
            if record.name == "test_trace"
        )
        assert trace_found, "trace_id not found in structured log output"
