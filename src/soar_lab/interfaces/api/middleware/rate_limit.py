"""In-memory sliding-window rate limiting middleware.

Enforces per-client request budgets so brute-force and accidental flood
traffic is throttled before it reaches sensitive endpoints. The limiter is
keyed on the Bearer token when present (per-credential) and on the client
IP otherwise (per-host).

Configuration is injected by the composition root from environment-backed
settings:

- ``RATE_LIMIT_ENABLED``        master switch (default ``true``)
- ``RATE_LIMIT_PER_MINUTE``     global budget per client (default 100)
- ``RATE_LIMIT_AUTH_PER_MINUTE`` budget for ``/auth/*`` (default 10)
- ``RATE_LIMIT_CONTAIN_PER_MINUTE`` budget for ``/api/v1/contain`` (default 30)
- ``RATE_LIMIT_BACKEND``        ``memory`` (default) or ``redis`` (BL-RATE-005)
- ``RATE_LIMIT_REDIS_URL``      backend URL, falls back to ``REDIS_URL``

With ``RATE_LIMIT_BACKEND=redis`` the sliding window is shared across
instances (a ZSET per client key), so N replicas enforce N× budget
instead of each applying its own. A backend failure fails *open* (the
request is allowed and a warning logged once per minute) — a rate
limiter must never take the API down with it.

Responses return HTTP 429 with ``Retry-After`` plus the conventional
``X-RateLimit-Limit`` / ``-Remaining`` / ``-Reset`` headers.
"""

import hashlib
import ipaddress
import logging
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Sequence
from contextlib import suppress

import redis.asyncio
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

__all__ = [
    "RateLimitMiddleware",
    "RateLimitRule",
    "InMemorySlidingWindowStore",
    "RedisSlidingWindowStore",
]


class RateLimitRule:
    """Per-path-prefix request budget.

    Args:
        prefix: Request path prefix the rule applies to (e.g. ``/auth``).
        per_minute: Maximum requests allowed inside a 60-second window.
    """

    __slots__ = ("per_minute", "prefix")

    def __init__(self, prefix: str, per_minute: int) -> None:
        self.prefix = prefix
        self.per_minute = per_minute


class InMemorySlidingWindowStore:
    """Per-process sliding-window store (single instance deployments)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_sweep = time.time()

    async def record(self, key: str, now: float, window_s: float) -> tuple[int, float | None]:
        """Record a hit; return ``(hits_in_window, oldest_hit_epoch)``."""
        with self._lock:
            window = self._hits[key]
            while window and now - window[0] >= window_s:
                window.popleft()
            if now - self._last_sweep > 2 * window_s:
                stale = [k for k, w in self._hits.items() if not w or now - w[-1] >= window_s]
                for k in stale:
                    self._hits.pop(k, None)
                self._last_sweep = now
            window.append(now)
            return len(window), window[0]


class RedisSlidingWindowStore:
    """BL-RATE-005: shared sliding window backed by a Redis ZSET.

    One key per client (``ratelimit:<client-key>``) holding member
    ``<epoch>:<uuid>`` scored by hit time — concurrent replicas share
    the exact same window instead of each enforcing its own budget.
    """

    KEY_PREFIX = "ratelimit:"

    def __init__(self, client) -> None:
        self._client = client

    @classmethod
    def from_url(cls, url: str) -> "RedisSlidingWindowStore":

        return cls(redis.asyncio.from_url(url))

    async def record(self, key: str, now: float, window_s: float) -> tuple[int, float | None]:
        rkey = f"{self.KEY_PREFIX}{key}"
        member = f"{now}:{uuid.uuid4().hex[:12]}"
        pipe = self._client.pipeline(transaction=False)
        pipe.zremrangebyscore(rkey, "-inf", now - window_s)
        pipe.zadd(rkey, {member: now})
        pipe.zcard(rkey)
        pipe.zrange(rkey, 0, 0, withscores=True)
        pipe.expire(rkey, int(window_s) + 2)
        _, _, count, oldest, _ = await pipe.execute()
        oldest_ts = float(oldest[0][1]) if oldest else None
        return int(count), oldest_ts


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter keyed by Bearer token or client IP."""

    def __init__(
        self,
        app,
        per_minute: int = 100,
        rules: Sequence[RateLimitRule] | None = None,
        exempt_paths: Sequence[str] | None = None,
        enabled: bool = True,
        trusted_proxies: Sequence[str] | None = None,
        store=None,
    ) -> None:
        super().__init__(app)
        self._per_minute = per_minute
        self._rules = sorted(rules or [], key=lambda r: len(r.prefix), reverse=True)
        self._exempt = tuple(exempt_paths or ())
        self._enabled = enabled
        self._store = store if store is not None else InMemorySlidingWindowStore()
        self._last_store_error_log = 0.0
        # ``X-Forwarded-For`` is only honoured when the direct TCP peer is a
        # configured trusted proxy — otherwise a client can spoof the header
        # and rotate identities to bypass the limiter entirely.
        raw_nets = (
            list(trusted_proxies)
            if trusted_proxies is not None
            else [
                n.strip()
                for n in os.environ.get("RATE_LIMIT_TRUSTED_PROXIES", "").split(",")
                if n.strip()
            ]
        )
        self._trusted_nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for net in raw_nets:
            try:
                self._trusted_nets.append(ipaddress.ip_network(net, strict=False))
            except ValueError:
                logger.warning("Ignoring invalid trusted-proxy CIDR: %s", net)

    def _budget_for(self, path: str) -> int:
        """Return the per-minute budget for *path* (most specific rule wins)."""
        for rule in self._rules:
            if path.startswith(rule.prefix):
                return rule.per_minute
        return self._per_minute

    def _is_trusted_proxy(self, host: str) -> bool:
        try:
            addr = ipaddress.ip_address(host)
        except ValueError:
            return False
        return any(addr in net for net in self._trusted_nets)

    def _client_key(self, request: Request) -> str:
        """Identify the caller: Bearer/service token when present, else client IP."""
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            digest = hashlib.sha256(auth[7:].encode()).hexdigest()[:16]
            return f"tok:{digest}"
        # X-Service-Token callers (internal services) also get a per-token
        # bucket — otherwise every workflow shares a single IP bucket.
        service_token = request.headers.get("x-service-token", "")
        if service_token:
            digest = hashlib.sha256(service_token.encode()).hexdigest()[:16]
            return f"tok:{digest}"
        client = request.client.host if request.client else "unknown"
        if self._is_trusted_proxy(client):
            forwarded = request.headers.get("x-forwarded-for", "")
            # Walk right-to-left: the first address that is not itself a
            # trusted proxy is the real client. A fully-trusted chain falls
            # back to the leftmost entry; empty/malformed → direct peer.
            hops = [h.strip() for h in forwarded.split(",") if h.strip()][:20]
            for hop in reversed(hops):
                if not self._is_trusted_proxy(hop):
                    try:
                        ipaddress.ip_address(hop)
                    except ValueError:
                        continue
                    return f"ip:{hop}"
            if hops:
                with suppress(ValueError):
                    ipaddress.ip_address(hops[0])
                    return f"ip:{hops[0]}"
        return f"ip:{client}"

    async def _allow(self, key: str, budget: int) -> tuple[bool, int, int, float]:
        """Record a hit and return ``(allowed, remaining, retry_after, reset_epoch)``."""
        now = time.time()
        try:
            count, oldest = await self._store.record(key, now, 60.0)
        except Exception as exc:
            # Fail-open: a rate limiter is availability protection, not an
            # auth gate — if the shared backend dies the API keeps serving
            # and we log at most once a minute to avoid a log flood.
            if now - self._last_store_error_log > 60.0:
                logger.warning(
                    "Rate-limit store failed (%s) — allowing request", type(exc).__name__
                )
                self._last_store_error_log = now
            return True, budget - 1, 0, now + 60.0
        reset_epoch = (oldest + 60.0) if oldest is not None else now + 60.0
        if count > budget:
            retry_after = max(1, int(60.0 - (now - oldest))) if oldest else 60
            return False, 0, retry_after, reset_epoch
        return True, budget - count, 0, reset_epoch

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._enabled or request.scope["type"] != "http":
            return await call_next(request)
        path = request.url.path
        if path in self._exempt or path.startswith("/static"):
            return await call_next(request)

        budget = self._budget_for(path)
        key = self._client_key(request)
        allowed, remaining, retry_after, reset_epoch = await self._allow(key, budget)

        headers = {
            "X-RateLimit-Limit": str(budget),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(int(reset_epoch)),
        }
        if not allowed:
            headers["Retry-After"] = str(retry_after)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "code": "rate_limited",
                    "retry_after_seconds": retry_after,
                },
                headers=headers,
            )
        response = await call_next(request)
        response.headers.update(headers)
        return response
