#!/usr/bin/env python3
"""Single-use WebSocket tickets (WEB-AUTH-001/003/004).

Replaces passing the primary JWT on the WS query string. The client fetches
a short-lived, single-use ticket via ``POST /auth/ws-ticket`` (Bearer JWT or
service token) and connects with ``/ws/logs?ticket=<ticket>``.

Properties:
- cryptographically random (``secrets.token_urlsafe``)
- single-use — the first ``consume()`` wins; reuse fails
- short TTL (default 30 s)
- bound to the user/service identity that requested it
- bound to a scope (``logs:read`` today)
- never logged — only a sha256[:12] fingerprint may appear in logs

Close codes (WEB-AUTH-002), documented for the frontend:
    1000 normal close · 1008 policy violation · 4401 unauthenticated
    (missing/invalid/reused ticket) · 4403 authenticated but not authorized
    (missing scope) · 4408 ticket expired · 4429 connection limit ·
    4500 internal error.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)

WS_CLOSE = {
    "normal": 1000,
    "policy": 1008,
    "unauthenticated": 4401,
    "forbidden": 4403,
    "expired": 4408,
    "limit": 4429,
    "internal": 4500,
}

LOGS_READ_SCOPE = "logs:read"


@dataclass
class _Ticket:
    user: str
    scope: str
    expires_at: float
    consumed: bool = False


@dataclass
class ConsumeResult:
    """Outcome of a one-shot websocket ticket consumption attempt."""

    ok: bool
    user: str | None = None
    reason: str = "invalid"  # invalid | expired | consumed


class TicketIssueError(Exception):
    """Raised when a user has too many pending tickets (rate limit)."""


@dataclass
class WsTicketStore:
    """In-memory store of short-lived websocket auth tickets."""

    ttl: float = 30.0
    max_pending_per_user: int = 5
    _tickets: dict[str, _Ticket] = field(default_factory=dict)

    def issue(self, user: str, scope: str = LOGS_READ_SCOPE) -> str:
        self._prune()
        pending = sum(
            1
            for t in self._tickets.values()
            if t.user == user and not t.consumed and t.expires_at > time.monotonic()
        )
        if pending >= self.max_pending_per_user:
            raise TicketIssueError(user)
        token = secrets.token_urlsafe(32)
        self._tickets[token] = _Ticket(
            user=user, scope=scope, expires_at=time.monotonic() + self.ttl
        )
        return token

    def consume(self, token: str | None) -> ConsumeResult:
        """Single-use consume: returns ok only for a live, unconsumed ticket.

        The ticket is removed atomically via ``pop`` — a racing consumer
        observes ``None`` and is reported ``invalid`` (consumed/invalid are
        indistinguishable by design: no oracle on whether the token ever
        existed). ``reason="consumed"`` is reported only when the same
        object was raced within the process.
        """
        if not token:
            return ConsumeResult(ok=False, reason="invalid")
        t = self._tickets.pop(token, None)
        if t is None:
            return ConsumeResult(ok=False, reason="invalid")
        if t.consumed:
            return ConsumeResult(ok=False, reason="consumed")
        if t.expires_at <= time.monotonic():
            return ConsumeResult(ok=False, reason="expired")
        t.consumed = True
        return ConsumeResult(ok=True, user=t.user)

    def _prune(self) -> None:
        now = time.monotonic()
        for k in [k for k, t in self._tickets.items() if t.consumed or t.expires_at <= now]:
            del self._tickets[k]

    def __len__(self) -> int:
        self._prune()
        return len(self._tickets)


class RedisWsTicketStore:
    """Redis-backed ticket store — same contract as ``WsTicketStore``.

    Selected via ``WS_TICKET_BACKEND=redis`` so that a ticket issued by one
    uvicorn worker can be consumed on another (multi-worker deployments).
    Single-use semantics are atomic via ``GETDEL``; TTL is enforced by Redis
    itself, so an absent key means invalid-or-expired (the public contract
    already treats them as indistinguishable).

    Pending-per-user accounting uses ``INCR``/``DECR`` on a per-user counter
    that also carries a TTL, so leaked counters self-heal.
    """

    KEY_PREFIX = "ws:ticket:"
    PENDING_PREFIX = "ws:ticket:pending:"

    def __init__(
        self,
        redis_client,
        ttl: float = 30.0,
        max_pending_per_user: int = 5,
    ) -> None:
        self._r = redis_client
        self.ttl = ttl
        self.max_pending_per_user = max_pending_per_user

    @classmethod
    def from_url(cls, url: str, **kwargs) -> RedisWsTicketStore:
        # redis is an optional dependency — import lazily so the
        # in-memory backend works without it installed.
        import redis as _redis  # pylint: disable=import-outside-toplevel

        return cls(_redis.Redis.from_url(url, socket_timeout=5), **kwargs)

    def _decr_pending(self, pending_key: str) -> None:
        """Decrement the pending counter, clamped at zero.

        The counter may have lapsed (TTL) before consume — a raw DECR on a
        missing key recreates it at -1 with no TTL, permanently gifting
        the user an extra pending slot. Bookkeeping must never break the
        consume path, so failures are logged and swallowed.
        """
        try:
            if self._r.decr(pending_key) < 0:
                self._r.set(pending_key, 0)
        except Exception:
            logger.debug("pending counter decr failed", exc_info=True)

    def issue(self, user: str, scope: str = LOGS_READ_SCOPE) -> str:
        pending_key = f"{self.PENDING_PREFIX}{user}"
        pending = self._r.incr(pending_key)
        if pending == 1:
            self._r.expire(pending_key, int(self.ttl) + 60)
        if pending > self.max_pending_per_user:
            self._decr_pending(pending_key)
            raise TicketIssueError(user)
        token = secrets.token_urlsafe(32)
        try:
            self._r.set(
                f"{self.KEY_PREFIX}{token}",
                f"{user}\n{scope}",
                ex=int(self.ttl),
                nx=True,
            )
        except Exception:
            # Roll back the pending slot — a redis blip must not inflate
            # the user's pending count and lock them out (BUG-WST-04).
            self._decr_pending(pending_key)
            raise
        return token

    def consume(self, token: str | None) -> ConsumeResult:
        if not token:
            return ConsumeResult(ok=False, reason="invalid")
        try:
            raw = self._r.getdel(f"{self.KEY_PREFIX}{token}")
        except Exception:
            # Auth store unreachable -> deny (fail closed), never fail open.
            return ConsumeResult(ok=False, reason="invalid")
        if raw is None:
            return ConsumeResult(ok=False, reason="invalid")
        text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)
        try:
            user, _scope = text.split("\n", 1)
        except ValueError:
            return ConsumeResult(ok=False, reason="invalid")
        self._decr_pending(f"{self.PENDING_PREFIX}{user}")
        return ConsumeResult(ok=True, user=user)

    def __len__(self) -> int:
        return sum(1 for _ in self._r.scan_iter(f"{self.KEY_PREFIX}*"))


def _as_list(value: object) -> list:
    """Normalize a JWT claim to a list.

    ``scope`` is a space-delimited string (RFC 6749) and some IdPs emit
    ``roles`` as a plain string — a bare ``in`` check on a string would
    substring-match (``"admin" in "administrator"`` grants on a role the
    user does not hold). Split strings, coerce iterables, wrap scalars.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return value.split()
    try:
        return list(value)
    except TypeError:
        return [value]


def has_logs_read_scope(user_info: dict) -> bool:
    """``logs:read`` is required to emit a ticket (WEB-AUTH-003).

    The lab JWT v1 does not issue a ``scopes`` claim; when the claim is
    absent an authenticated user is treated as authorized (documented
    accepted limitation — scope enforcement activates as soon as tokens
    carry ``scopes``/``roles``). When the claim IS present it is enforced
    with exact membership (no substring matching).
    """
    scopes = user_info.get("scopes")
    if scopes is None:
        roles = _as_list(user_info.get("roles"))
        return "admin" in roles or "operator" in roles or not roles
    return LOGS_READ_SCOPE in _as_list(scopes)
