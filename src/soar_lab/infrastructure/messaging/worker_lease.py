"""HA worker lease (R3): one holder among N admission workers.

Multiple API replicas each run an ``AdmissionWorker``; per-entry
consumption is already safe via the Redis Streams consumer group, but
the *singleton duties* — ``recover()`` (stale-entry reclaim across
consumers) and ``dlq_auto_redrive`` — must run on exactly one worker,
or N replicas all redrive the same DLQ entries.

The lease is a Redis key ``SET holder NX PX ttl`` refreshed by the
holder each cycle. A holder that dies stops renewing; after ``ttl``
another worker acquires — no fencing needed because the duties are
idempotent (redrive budgets and reclaim are safe to run twice).

Degrades honestly: without Redis there is no distributed coordination,
so the lease reports ``holder=True`` (single-worker semantics) — a
standalone deployment must not lose recovery because a lock service
is absent.
"""

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)

LEASE_KEY = "soar:worker:lease"
FENCE_KEY = "soar:worker:lease:fence"
DEFAULT_LEASE_TTL_MS = 30_000

# WORKER-006: acquire/renew in one round-trip — a GET+SET pair leaves a
# TOCTOU window where two workers both read ``None`` and both lead for a
# cycle. Returns 1 = renewed own lease, 2 = fresh acquisition, 0 = held
# by another worker.
_HELD_SCRIPT = (
    "local current = redis.call('GET', KEYS[1]) "
    "if current == ARGV[1] then "
    "  redis.call('SET', KEYS[1], ARGV[1], 'PX', ARGV[2]) return 1 "
    "end "
    "if redis.call('SET', KEYS[1], ARGV[1], 'PX', ARGV[2], 'NX') then return 2 end "
    "return 0"
)

# Compare-and-delete: a worker whose lease expired between the check and
# the DEL must not evict the NEW holder's key.
_RELEASE_SCRIPT = (
    "if redis.call('GET', KEYS[1]) == ARGV[1] "
    "then return redis.call('DEL', KEYS[1]) else return 0 end"
)


class WorkerLease:
    """Redis-backed leader lease for worker singleton duties."""

    def __init__(
        self, client: object | None, holder: str, ttl_ms: int = DEFAULT_LEASE_TTL_MS
    ) -> None:
        self._client = client
        self.holder = holder
        self.ttl_ms = ttl_ms
        self.fence_token: int | None = None

    async def held(self) -> bool:
        """Acquire or renew the lease; ``True`` when this worker leads.

        WORKER-005: on (re)acquisition the fencing counter is INCR'ed —
        a paused leader that wakes after losing the lease sees a stale
        token and must not run singleton duties.
        """
        if self._client is None:
            return True
        try:
            res = await self._client.eval(
                _HELD_SCRIPT, 1, LEASE_KEY, self.holder, str(self.ttl_ms)
            )
        except Exception as e:
            logger.warning("Worker lease check failed: %s", e)
            return False
        if res == 0:
            return False
        if res == 2:
            try:
                self.fence_token = await self._client.incr(FENCE_KEY)
            except Exception:
                self.fence_token = None
        return True

    async def release(self) -> None:
        """Relinquish the lease if we hold it (shutdown fast takeover)."""
        if self._client is None:
            return
        try:
            await self._client.eval(_RELEASE_SCRIPT, 1, LEASE_KEY, self.holder)
        except Exception as e:
            logger.debug("Worker lease release failed: %s", e)
