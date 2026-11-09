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
DEFAULT_LEASE_TTL_MS = 30_000


class WorkerLease:
    """Redis-backed leader lease for worker singleton duties."""

    def __init__(
        self, client: object | None, holder: str, ttl_ms: int = DEFAULT_LEASE_TTL_MS
    ) -> None:
        self._client = client
        self.holder = holder
        self.ttl_ms = ttl_ms

    async def held(self) -> bool:
        """Acquire or renew the lease; ``True`` when this worker leads."""
        if self._client is None:
            return True
        try:
            current = await self._client.get(LEASE_KEY)
            current = current.decode() if isinstance(current, bytes) else current
            if current is None or current == self.holder:
                await self._client.set(LEASE_KEY, self.holder, px=self.ttl_ms)
                return True
            return False
        except Exception as e:
            logger.warning("Worker lease check failed: %s", e)
            return False

    async def release(self) -> None:
        """Relinquish the lease if we hold it (shutdown fast takeover)."""
        if self._client is None:
            return
        try:
            current = await self._client.get(LEASE_KEY)
            current = current.decode() if isinstance(current, bytes) else current
            if current == self.holder:
                await self._client.delete(LEASE_KEY)
        except Exception as e:
            logger.debug("Worker lease release failed: %s", e)
