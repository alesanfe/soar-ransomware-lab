"""DOS-002: pre-authentication rate limiting (pure ASGI).

Runs BEFORE ``DefaultDenyAuthMiddleware`` in the request path so token
guessing, JWT brute-force and anonymous floods consume budget instead
of getting unlimited free 401s. Keyed on client IP only (there is no
credential yet); honoured ``X-Forwarded-For`` solely when the direct
peer is a configured trusted proxy — same rule as the post-auth limiter.
"""

from __future__ import annotations

import ipaddress
import logging
import time
from collections import defaultdict, deque
from typing import Any

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

__all__ = ["PreAuthRateLimitMiddleware"]


class PreAuthRateLimitMiddleware:
    """Per-IP sliding-window limiter evaluated before authentication."""

    def __init__(
        self,
        app: Any,
        *,
        per_minute: int = 60,
        trusted_proxies: list[str] | None = None,
        enabled: bool = True,
    ) -> None:
        self.app = app
        self._per_minute = per_minute
        self._enabled = enabled
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._last_sweep = time.time()
        self._trusted: list[Any] = []
        for net in trusted_proxies or []:
            try:
                self._trusted.append(ipaddress.ip_network(net, strict=False))
            except ValueError:
                logger.warning("Ignoring invalid pre-auth trusted-proxy CIDR: %s", net)

    def _client_ip(self, scope: dict[str, Any]) -> str:
        client = scope.get("client")
        host = client[0] if client else "unknown"
        try:
            addr = ipaddress.ip_address(host)
        except ValueError:
            return host
        if not any(addr in net for net in self._trusted):
            return host
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        xff = headers.get(b"x-forwarded-for", b"").decode(errors="replace")
        for hop in reversed([h.strip() for h in xff.split(",") if h.strip()][:20]):
            try:
                ip = ipaddress.ip_address(hop)
            except ValueError:
                continue
            if not any(ip in net for net in self._trusted):
                return hop
        return host

    def _allow(self, key: str, now: float) -> tuple[bool, int]:
        window = self._hits[key]
        while window and now - window[0] >= 60.0:
            window.popleft()
        if now - self._last_sweep > 120.0:
            stale = [k for k, w in self._hits.items() if not w or now - w[-1] >= 60.0]
            for k in stale:
                self._hits.pop(k, None)
            self._last_sweep = now
        if len(window) >= self._per_minute:
            retry = max(1, int(60.0 - (now - window[0])))
            return False, retry
        window.append(now)
        return True, 0

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if not self._enabled or scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        key = self._client_ip(scope)
        now = time.time()
        allowed, retry = self._allow(key, now)
        if not allowed:
            response = JSONResponse(
                {"detail": "Rate limit exceeded", "code": "rate_limited",
                 "retry_after_seconds": retry},
                status_code=429,
                headers={
                    "Retry-After": str(retry),
                    "X-RateLimit-Limit": str(self._per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now) + retry),
                },
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
