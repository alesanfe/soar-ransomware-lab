"""Trace ID middleware for request correlation across the SOAR pipeline.

Generates or propagates an ``X-Request-ID`` header for every HTTP request.
The trace ID is stored in a contextvar so that structured log entries
anywhere in the request lifecycle automatically include ``trace_id``,
enabling end-to-end correlation from webhook → API → Shuffle → TheHive →
Cortex → Elasticsearch.
"""

import contextvars
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from soar_lab.common.constants import HEADER_TRACE_ID

__all__ = ["trace_id_ctx", "TraceIdMiddleware", "get_trace_id", "TRACE_ID_HEADER"]

TRACE_ID_HEADER = HEADER_TRACE_ID

# Context variable accessible from any coroutine in the request scope.
trace_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)


def get_trace_id() -> str | None:
    """Return the current trace ID, or ``None`` if outside a request scope."""
    return trace_id_ctx.get()


def _generate_trace_id() -> str:
    """Generate a new trace ID (UUID4 without dashes, 32 chars)."""
    return uuid.uuid4().hex


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Middleware that injects a trace ID into every request/response cycle.

    If the incoming request carries an ``X-Request-ID`` header, that value
    is reused (propagation).  Otherwise a new UUID4-based ID is generated.
    The ID is stored in ``trace_id_ctx`` so that log records emitted during
    the request automatically include it.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get(TRACE_ID_HEADER) or _generate_trace_id()
        token = trace_id_ctx.set(trace_id)
        try:
            response = await call_next(request)
            response.headers[TRACE_ID_HEADER] = trace_id
            return response
        finally:
            trace_id_ctx.reset(token)
