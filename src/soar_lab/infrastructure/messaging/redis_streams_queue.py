"""PERF-001: Redis Streams implementation of the ``EventQueue`` port.

- ``enqueue``      -> ``XADD`` (QUEUE-004: bounded by ``MAXLEN ~``)
- ``read``         -> ``XREADGROUP`` (pending until acked)
- ``claim_stale``  -> ``XAUTOCLAIM`` (post-restart recovery)
- ``ack``          -> ``XACK``
- ``dead_letter``  -> ``XADD`` on the DLQ stream
- ``ensure_group`` -> ``XGROUP CREATE ... MKSTREAM``

QUEUE-001 poison handling: an entry whose payload cannot be decoded can
never succeed — it is moved to the DLQ with ``reason=decode_failed`` and
acked so it does not sit pending forever.

QUEUE-002 real DLQ lifecycle: ``dlq_size``/``dlq_list``/``dlq_redrive``/
``dlq_purge`` give operators redrive + purge instead of a write-only
graveyard.

Uses ``redis.asyncio`` so the worker cooperates with the FastAPI event loop.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

DEFAULT_MAXLEN = 100_000


class RedisStreamsQueue:
    """``EventQueue`` port backed by a Redis Stream + consumer group."""

    def __init__(
        self,
        client: aioredis.Redis,
        stream: str = "soar:admissions",
        dlq_stream: str = "soar:admissions:dlq",
        maxlen: int = DEFAULT_MAXLEN,
    ) -> None:
        self.client = client
        self.stream = stream
        self.dlq_stream = dlq_stream
        self.maxlen = maxlen

    async def enqueue(self, event: dict[str, Any]) -> str:
        # QUEUE-004: approximate MAXLEN keeps the stream bounded (~O(1)
        # trim) — an unbounded stream grows until Redis runs out of memory.
        entry_id: str = await self.client.xadd(
            self.stream,
            {"payload": json.dumps(event, default=str)},
            maxlen=self.maxlen,
            approximate=True,
        )
        return entry_id

    async def read(
        self, group: str, consumer: str, count: int, block_ms: int
    ) -> list[tuple[str, dict[str, Any]]]:
        await self.ensure_group(group)
        rows = await self.client.xreadgroup(
            group, consumer, {self.stream: ">"}, count=count, block=block_ms
        )
        return await self._decode(rows, group)

    async def claim_stale(
        self, group: str, consumer: str, min_idle_ms: int
    ) -> list[tuple[str, dict[str, Any]]]:
        await self.ensure_group(group)
        try:
            _next, claimed, _deleted = await self.client.xautoclaim(
                self.stream,
                group,
                consumer,
                min_idle_time=min_idle_ms,
                start_id="0-0",
                count=100,
            )
        except Exception as exc:
            logger.warning("XAUTOCLAIM failed: %s", exc)
            return []
        out: list[tuple[str, dict[str, Any]]] = []
        for entry_id, fields in claimed:
            event = self._decode_fields(fields)
            if event is None:
                await self._poison_to_dlq(group, entry_id, fields)
            else:
                out.append((entry_id, event))
        return out

    async def ack(self, group: str, entry_id: str) -> None:
        await self.client.xack(self.stream, group, entry_id)

    async def dead_letter(self, entry: dict[str, Any], reason: str) -> None:
        await self.client.xadd(
            self.dlq_stream,
            {"payload": json.dumps(entry, default=str), "reason": reason[:512]},
            maxlen=self.maxlen,
            approximate=True,
        )

    async def ensure_group(self, group: str) -> None:
        try:
            await self.client.xgroup_create(self.stream, group, id="0", mkstream=True)
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def depth(self) -> int:
        """Real backlog: entries still needing work across all groups.

        ``XLEN`` counts every entry ever appended — including processed
        ones retained up to ``maxlen`` — so it overstates the backlog.
        ``XINFO GROUPS`` exposes ``lag`` (never delivered) + ``pending``
        (delivered, unacked); their sum is the actual queue depth.
        """
        try:
            groups = await self.client.xinfo_groups(self.stream)
            total = 0
            for g in groups:
                pending = g.get(b"pending") if isinstance(g, dict) else None
                pending = pending if pending is not None else g.get("pending", 0)
                lag = g.get(b"lag") if isinstance(g, dict) else None
                lag = lag if lag is not None else g.get("lag")
                total += int(pending or 0) + int(lag or 0)
            return total
        except Exception:
            # Old server / no groups yet / unexpected shape — fall back to
            # stream length rather than failing the metrics path.
            return int(await self.client.xlen(self.stream))

    async def stream_length(self) -> int:
        """Raw XLEN — includes already-processed entries retained by maxlen."""
        return int(await self.client.xlen(self.stream))

    # ------------------------------------------------------------------
    # QUEUE-002: real DLQ lifecycle (size / inspect / redrive / purge)
    # ------------------------------------------------------------------

    async def dlq_size(self) -> int:
        return int(await self.client.xlen(self.dlq_stream))

    async def dlq_list(self, count: int = 50) -> list[dict[str, Any]]:
        rows = await self.client.xrange(self.dlq_stream, count=count)
        out: list[dict[str, Any]] = []
        for entry_id, fields in rows or []:
            fields = {self._s(k): v for k, v in fields.items()}
            payload_raw = fields.get("payload")
            try:
                payload = json.loads(payload_raw) if payload_raw is not None else None
            except (TypeError, ValueError):
                payload = None
            out.append(
                {
                    "dlq_entry_id": self._s(entry_id),
                    "reason": self._s(fields.get("reason")) or "unknown",
                    "payload": payload,
                }
            )
        return out

    async def dlq_redrive(self, dlq_entry_id: str, group: str = "soar-api") -> bool:
        """Re-enqueue one DLQ entry on the main stream; remove it from the DLQ.

        Returns ``False`` when the entry is unknown or its payload cannot
        be recovered.
        """
        rows = await self.client.xrange(self.dlq_stream, min=dlq_entry_id, max=dlq_entry_id)
        if not rows:
            return False
        _eid, fields = rows[0]
        fields = {self._s(k): v for k, v in fields.items()}
        raw = fields.get("payload")
        try:
            payload = json.loads(raw) if raw is not None else None
        except (TypeError, ValueError):
            payload = None
        if not isinstance(payload, dict):
            return False
        payload["attempts"] = 0  # reset retry budget on redrive
        payload["redriven_at"] = time.time()
        await self.enqueue(payload)
        await self.client.xdel(self.dlq_stream, dlq_entry_id)
        logger.info("Redrove DLQ entry %s back to %s", dlq_entry_id, self.stream)
        return True

    async def dlq_purge(self) -> int:
        """Drop every DLQ entry; returns how many were deleted."""
        n = await self.dlq_size()
        if n:
            await self.client.xtrim(self.dlq_stream, maxlen=0)
        return n

    async def dlq_auto_redrive(
        self,
        limit: int = 100,
        max_redrives: int = 3,
        min_age_s: float = 60.0,
    ) -> int:
        """R2: bounded automatic redrive of transient DLQ entries.

        A dead-lettered admission is usually a *transient* downstream
        outage (Shuffle/TheHive/ES down) — retrying it later recovers
        the alert without operator action. Two guards stop churn:

        - ``reason == "decode_failed"`` entries are permanent poison:
          re-enqueueing them only loops them through the DLQ forever.
        - ``redrive_count`` is a per-entry budget (default 3) and the
          minimum dead-age grows exponentially per redrive
          (``min_age_s * 2**redrive_count``), so an entry that keeps
          failing backs off instead of hammering a sick downstream.

        Returns the number of entries re-enqueued this pass.
        """
        now_ms = time.time() * 1000
        redriven = 0
        for row in await self.dlq_list(count=limit):
            if row["reason"] == "decode_failed":
                continue
            payload = row.get("payload")
            if not isinstance(payload, dict):
                continue
            count = int(payload.get("redrive_count") or 0)
            if count >= max_redrives:
                continue
            try:
                entry_ms = int(str(row["dlq_entry_id"]).split("-", 1)[0])
            except (ValueError, IndexError):
                entry_ms = 0
            min_age_ms = min_age_s * (2**count) * 1000
            if entry_ms and (now_ms - entry_ms) < min_age_ms:
                continue
            payload["attempts"] = 0
            payload["redrive_count"] = count + 1
            payload["redriven_at"] = time.time()
            await self.enqueue(payload)
            await self.client.xdel(self.dlq_stream, row["dlq_entry_id"])
            redriven += 1
        if redriven:
            logger.info("Auto-redrove %d DLQ entry(s)", redriven)
        return redriven

    # QUEUE-006-lite: real queue metrics for observability.
    async def metrics(self, group: str = "soar-api") -> dict[str, Any]:
        out: dict[str, Any] = {
            "queue_depth": await self.depth(),
            "stream_length": await self.stream_length(),
            "dlq_size": await self.dlq_size(),
            "consumer_lag": None,
            "pending": None,
        }
        try:
            groups = await self.client.xinfo_groups(self.stream)
            for g in groups:
                name = self._s(g.get(b"name") or g.get("name"))
                if name == group:
                    out["pending"] = int(g.get(b"pending") or g.get("pending") or 0)
                    lag = g.get(b"lag") if isinstance(g, dict) else None
                    lag = lag if lag is not None else g.get("lag")
                    out["consumer_lag"] = int(lag) if lag is not None else None
        except Exception as exc:
            logger.debug("xinfo_groups unavailable: %s", exc)
        return out

    # ------------------------------------------------------------------

    async def _poison_to_dlq(self, group: str, entry_id: str, fields: dict[Any, Any]) -> None:
        """QUEUE-001: undecodable entries are a poison message — DLQ + ack.

        Before this, ``_decode_fields`` returned ``None`` and the entry
        stayed pending forever, growing the PEL and being re-claimed on
        every recovery pass.
        """
        raw = fields.get(b"payload") or fields.get("payload")
        try:
            raw_str = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        except Exception:
            raw_str = "<undecodable>"
        await self.client.xadd(
            self.dlq_stream,
            {
                "payload": raw_str[:4000],
                "reason": "decode_failed",
                "source_entry_id": self._s(entry_id),
            },
            maxlen=self.maxlen,
            approximate=True,
        )
        await self.client.xack(self.stream, group, entry_id)
        logger.warning("Poison queue entry %s moved to DLQ", entry_id)

    async def _decode(self, rows: Any, group: str) -> list[tuple[str, dict[str, Any]]]:
        out: list[tuple[str, dict[str, Any]]] = []
        for _stream, entries in rows or []:
            for entry_id, fields in entries:
                event = self._decode_fields(fields)
                if event is None:
                    await self._poison_to_dlq(group, entry_id, fields)
                else:
                    out.append((entry_id, event))
        return out

    @staticmethod
    def _s(v: Any) -> str:
        return v.decode() if isinstance(v, bytes) else str(v)

    @staticmethod
    def _decode_fields(fields: dict[Any, Any]) -> dict[str, Any] | None:
        raw = fields.get(b"payload") or fields.get("payload")
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("Undecodable queue payload skipped")
            return None
