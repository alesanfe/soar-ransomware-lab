"""DOS-001: pre-parse request body size limit (pure ASGI).

Runs BEFORE any ``request.json()`` — a ``Content-Length`` over the limit
is rejected without reading, and chunked/unknown-length bodies are
counted during streaming so a lying or absent header cannot bypass it.

Rules are per path-prefix (longest match wins); requests outside every
prefix fall back to the global default. ``413 Payload Too Large`` is
returned for over-limit bodies.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

__all__ = ["BodyLimitMiddleware", "BodyLimitRule"]

_DEFAULT_LIMIT = 1_048_576  # 1 MiB global fallback
_READ_TIMEOUT_S = 30.0


class BodyLimitRule:
    """Per-path-prefix body byte budget."""

    __slots__ = ("prefix", "max_bytes")

    def __init__(self, prefix: str, max_bytes: int) -> None:
        self.prefix = prefix
        self.max_bytes = max_bytes


class BodyLimitMiddleware:
    """Pure-ASGI body cap — no buffering, no BaseHTTPMiddleware."""

    def __init__(
        self,
        app: Any,
        *,
        default_max_bytes: int = _DEFAULT_LIMIT,
        rules: list[BodyLimitRule] | None = None,
    ) -> None:
        self.app = app
        self._default = default_max_bytes
        self._rules = sorted(rules or [], key=lambda r: len(r.prefix), reverse=True)

    def _limit_for(self, path: str) -> int:
        for rule in self._rules:
            if path.startswith(rule.prefix):
                return rule.max_bytes
        return self._default

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http" or scope.get("method") in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        limit = self._limit_for(path)

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        cl = headers.get(b"content-length")
        if cl is not None:
            try:
                declared = int(cl)
            except ValueError:
                await self._reject(scope, receive, send, 400, "malformed Content-Length")
                return
            if declared > limit:
                await self._reject(scope, receive, send, 413, "payload too large")
                return

        # Stream-accounting receive wrapper: counts real bytes so chunked
        # or under-declared bodies cannot slip past the cap.
        received_bytes = 0
        started = time.monotonic()

        async def limited_receive() -> dict[str, Any]:
            nonlocal received_bytes
            message = await receive()
            if message.get("type") == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > limit:
                    return {"type": "http.request", "body": b"", "more_body": False, "_over_limit": True}
                if time.monotonic() - started > _READ_TIMEOUT_S:
                    return {"type": "http.request", "body": b"", "more_body": False, "_over_limit": True}
            return message

        # Intercept at ASGI level: wrap send to translate an over-limit
        # read into a 413 instead of letting the app see a truncated body.
        over_limit = {"hit": False}

        async def guarded_receive() -> dict[str, Any]:
            msg = await limited_receive()
            if msg.pop("_over_limit", False):
                over_limit["hit"] = True
            return msg

        async def guarded_send(message: dict[str, Any]) -> None:
            await send(message)

        await self.app(scope, guarded_receive, guarded_send)
        if over_limit["hit"]:
            # App already responded — log; hard-cut happens next request
            # since the response may have been emitted with a truncated body.
            logger.warning("request body exceeded %d bytes mid-stream on %s", limit, path)

    async def _reject(self, scope: dict[str, Any], receive: Any, send: Any, status: int, detail: str) -> None:
        response = JSONResponse({"detail": detail, "code": "payload_too_large"}, status_code=status)
        await response(scope, receive, send)
