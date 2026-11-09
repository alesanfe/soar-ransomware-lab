"""Request-scoped trace ID context shared by all architecture layers.

The contextvar lives in ``common`` (the lowest layer) so that both
``interfaces`` (which sets the ID per request) and ``infrastructure`` /
``logging`` (which read it for propagation and structured logs) can depend
on it without creating an ``infrastructure <-> interfaces`` import cycle.
"""

import contextvars

from soar_lab.common.ids import uuid7_hex

__all__ = ["trace_id_ctx", "get_trace_id", "new_trace_id"]

# Context variable accessible from any coroutine in the request scope.
trace_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)


def get_trace_id() -> str | None:
    """Return the current trace ID, or ``None`` if outside a request scope."""
    return trace_id_ctx.get()


def new_trace_id() -> str:
    """Generate a new trace ID (UUIDv7 hex, 32 chars, time-ordered)."""
    return uuid7_hex()
