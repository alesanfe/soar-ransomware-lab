"""Trace ID middleware for request correlation across the SOAR pipeline.

Generates or propagates an ``X-Request-ID`` header for every HTTP request.
The trace ID is stored in a contextvar so that structured log entries
anywhere in the request lifecycle automatically include ``trace_id``,
enabling end-to-end correlation from webhook → API → Shuffle → TheHive →
Cortex → Elasticsearch.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from soar_lab.common.constants import HEADER_TRACE_ID
from soar_lab.common.trace_context import get_trace_id, new_trace_id, trace_id_ctx

__all__ = ["trace_id_ctx", "TraceIdMiddleware", "get_trace_id", "TRACE_ID_HEADER"]

TRACE_ID_HEADER = HEADER_TRACE_ID


def _generate_trace_id() -> str:
    """Generate a new trace ID (UUID4 without dashes, 32 chars)."""
    return new_trace_id()


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Middleware that injects a trace ID into every request/response cycle.

    If the incoming request carries an ``X-Request-ID`` header, that value
    is reused (propagation).  Otherwise a new UUID4-based ID is generated.
    The ID is stored in ``trace_id_ctx`` so that log records emitted during
    the request automatically include it.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        inbound = request.headers.get(TRACE_ID_HEADER, "")
        # Trust inbound IDs only if sane — unbounded/garbage values pollute
        # log correlation and downstream headers.
        if inbound and len(inbound) <= 64 and inbound.replace("-", "").replace("_", "").isalnum():
            trace_id = inbound
        else:
            trace_id = _generate_trace_id()
        token = trace_id_ctx.set(trace_id)
        try:
            response = await call_next(request)
            response.headers[TRACE_ID_HEADER] = trace_id
            return response
        finally:
            trace_id_ctx.reset(token)
