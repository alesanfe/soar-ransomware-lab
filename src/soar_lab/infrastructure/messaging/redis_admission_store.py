"""PERF-001: Redis implementation of the ``AdmissionStore`` port.

- Record   -> ``soar:admission:<id>`` hash + TTL (records are audit data,
  kept 7 days by default so ``status_url`` stays meaningful).
- Idempotency -> ``soar:admission:key:<key>`` -> admission_id (SET NX).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_RECORD_PREFIX = "soar:admission:"
_KEY_PREFIX = "soar:admission:key:"


class RedisAdmissionStore:
    """``AdmissionStore`` port backed by Redis hashes."""

    def __init__(self, client: aioredis.Redis, record_ttl_s: int = 7 * 24 * 3600) -> None:
        self.client = client
        self.record_ttl_s = record_ttl_s

    async def create(self, record: dict[str, Any]) -> None:
        key = _RECORD_PREFIX + record["admission_id"]
        fields = {
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in record.items()
        }
        await self.client.hset(key, mapping=fields)
        await self.client.expire(key, self.record_ttl_s)

    async def update(self, admission_id: str, fields: dict[str, Any]) -> None:
        key = _RECORD_PREFIX + admission_id
        if not await self.client.exists(key):
            logger.warning("Admission %s vanished before update %s", admission_id, fields)
            return
        await self.client.hset(
            key,
            mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in fields.items()
            },
        )

    async def get(self, admission_id: str) -> dict[str, Any] | None:
        raw = await self.client.hgetall(_RECORD_PREFIX + admission_id)
        if not raw:
            return None
        out: dict[str, Any] = {}
        for k, v in raw.items():
            k = k.decode() if isinstance(k, bytes) else k
            v = v.decode() if isinstance(v, bytes) else v
            try:
                out[k] = json.loads(v)
            except (TypeError, ValueError):
                out[k] = v
        return out

    async def find_by_key(self, idempotency_key: str) -> str | None:
        val = await self.client.get(_KEY_PREFIX + idempotency_key)
        if val is None:
            return None
        return val.decode() if isinstance(val, bytes) else val

    async def bind_key(self, idempotency_key: str, admission_id: str) -> None:
        await self.client.set(
            _KEY_PREFIX + idempotency_key, admission_id, ex=self.record_ttl_s, nx=True
        )

    async def try_bind_key(self, idempotency_key: str, admission_id: str) -> str | None:
        """SET NX winner/loser split — the atomic idempotency claim."""
        won = await self.client.set(
            _KEY_PREFIX + idempotency_key,
            admission_id,
            ex=self.record_ttl_s,
            nx=True,
        )
        if won:
            return None
        existing = await self.find_by_key(idempotency_key)
        return existing or admission_id

    async def list_by_status(
        self, statuses: set[str], limit: int = 500
    ) -> list[dict[str, Any]]:
        """ADMISSION-002: bounded scan for records in ``statuses``.

        Used by the reconciler to find ``enqueue_failed`` orphans. SCAN +
        HGETALL per candidate — runs under the leader lease every
        ``recover_interval_s``, never on the hot path.
        """
        out: list[dict[str, Any]] = []
        async for key in self.client.scan_iter(match=f"{_RECORD_PREFIX}*"):
            if len(out) >= limit:
                break
            k = key.decode() if isinstance(key, bytes) else key
            if k.startswith(_KEY_PREFIX):  # keyspace shares prefix pattern
                continue
            raw = await self.client.hgetall(k)
            dec: dict[str, Any] = {}
            for fk, fv in raw.items():
                fk = fk.decode() if isinstance(fk, bytes) else fk
                fv = fv.decode() if isinstance(fv, bytes) else fv
                try:
                    dec[fk] = json.loads(fv)
                except (TypeError, ValueError):
                    dec[fk] = fv
            if dec.get("status") in statuses:
                out.append(dec)
        return out

    async def unbind_key(self, idempotency_key: str, admission_id: str) -> None:
        # Compare-and-delete so we never free a key claimed by someone else.
        script = (
            "if redis.call('GET', KEYS[1]) == ARGV[1] "
            "then return redis.call('DEL', KEYS[1]) else return 0 end"
        )
        await self.client.eval(script, 1, _KEY_PREFIX + idempotency_key, admission_id)
