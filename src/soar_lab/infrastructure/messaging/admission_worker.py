"""PERF-001: admission worker — durable forward to the slow downstream.

Consumes admitted alerts from the ``EventQueue`` port and forwards each
``alert`` via the injected ``forward`` callable (an async function that
POSTs to the Shuffle webhook and returns ``{"ok": bool, ...}``).

Semantics:

- success          -> ``store.update(status=forwarded, ...)`` + ``queue.ack``
- failure          -> ``attempts += 1``, event re-enqueued, original acked
- ``max_attempts`` -> ``queue.dead_letter`` + ``store.update(status=dead)``
- restart          -> ``recover()`` claims stale pending entries and processes
  them, so a crash mid-forward does not lose admissions. Runs every
  ``recover_interval_s`` seconds during ``run`` (QUEUE-005).

Retries honour an exponential backoff with AWS-style *full jitter*
(QUEUE-003): ``sleep = uniform(0, min(cap, base * 2**attempts))`` —
1s/2s/4s/8s/16s nominal, so a downstream brown-out is not hammered by
a synchronous retry storm.

Concurrency is bounded by a semaphore so a burst cannot exhaust
connections to the downstream.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from itertools import starmap
from typing import Any

from soar_lab.application.ports.output import AdmissionStore, EventQueue
from soar_lab.application.use_cases.alert_admission import (
    STATUS_DEAD,
    STATUS_FORWARDED,
    STATUS_QUEUED,
)

logger = logging.getLogger(__name__)

ForwardFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class WorkerStats:
    """QUEUE-006: cumulative worker counters exported via ``/metrics``.

    Read by the Prometheus exposition endpoint; updated by the worker on
    every processed entry. All values are monotonic except ``inflight``.
    """

    processed_total: int = 0
    forwarded_total: int = 0
    retried_total: int = 0
    dead_total: int = 0
    dedup_total: int = 0
    forward_seconds_total: float = 0.0
    inflight: int = 0
    last_error: str = ""
    errors: dict[str, int] = field(default_factory=dict)


class AdmissionWorker:
    """Forward queued admissions downstream with retry + DLQ semantics."""

    def __init__(
        self,
        queue: EventQueue,
        store: AdmissionStore,
        forward: ForwardFn,
        *,
        group: str = "soar-api",
        consumer: str = "worker-1",
        max_attempts: int = 5,
        batch_size: int = 10,
        poll_ms: int = 500,
        stale_ms: int = 30_000,
        concurrency: int = 4,
        retry_base_s: float = 1.0,
        retry_cap_s: float = 32.0,
        recover_interval_s: float = 60.0,
        dlq_auto_redrive: bool = True,
        dlq_redrive_max: int = 3,
        dlq_redrive_min_age_s: float = 60.0,
        stats: WorkerStats | None = None,
        lease: Any | None = None,
    ) -> None:
        self.queue = queue
        self.store = store
        self.forward = forward
        self.stats = stats if stats is not None else WorkerStats()
        self.group = group
        self.consumer = consumer
        self.max_attempts = max_attempts
        self.batch_size = batch_size
        self.poll_ms = poll_ms
        self.stale_ms = stale_ms
        self.retry_base_s = retry_base_s
        self.retry_cap_s = retry_cap_s
        self.recover_interval_s = recover_interval_s
        self.dlq_auto_redrive = dlq_auto_redrive
        self.dlq_redrive_max = dlq_redrive_max
        self.dlq_redrive_min_age_s = dlq_redrive_min_age_s
        self.lease = lease
        self._semaphore = asyncio.Semaphore(concurrency)
        self._rng = random.Random()

    def _retry_delay(self, attempts: int) -> float:
        """QUEUE-003: full-jitter exponential backoff (AWS pattern).

        Nominal schedule 1s→2s→4s→8s→16s→32s; the actual sleep is a
        uniform draw in ``[0, cap]`` so a fleet of consumers does not
        retry in lockstep.
        """
        cap = min(self.retry_cap_s, self.retry_base_s * (2 ** max(attempts - 1, 0)))
        return self._rng.uniform(0, cap)

    async def run_once(self) -> int:
        """Process one batch of new entries; return how many were handled."""
        batch = await self.queue.read(self.group, self.consumer, self.batch_size, self.poll_ms)
        if not batch:
            return 0
        await asyncio.gather(*starmap(self._process, batch))
        return len(batch)

    async def recover(self) -> int:
        """Claim stale pending entries (post-restart recovery) and process them."""
        stale = await self.queue.claim_stale(self.group, self.consumer, self.stale_ms)
        if not stale:
            return 0
        logger.info("Recovering %d stale admission(s)", len(stale))
        await asyncio.gather(*starmap(self._process, stale))
        return len(stale)

    async def run(self, stop: asyncio.Event) -> None:
        """Main loop: read batches until ``stop`` is set.

        QUEUE-005: ``recover()`` is periodic, not boot-only — a consumer
        that stalls mid-run (or a second worker that dies) no longer
        leaves entries pending until the next restart.
        """
        await self.queue.ensure_group(self.group)
        await self.recover()
        last_recover = time.monotonic()
        while not stop.is_set():
            try:
                await self.run_once()
                if time.monotonic() - last_recover >= self.recover_interval_s:
                    # R3: recover + auto-redrive are singleton duties —
                    # only the lease holder runs them so N replicas don't
                    # all reclaim/redrive the same entries.
                    leader = await self.lease.held() if self.lease is not None else True
                    if leader:
                        await self.recover()
                        # R2: piggyback DLQ auto-redrive on the recovery
                        # pass — transient dead-letters come back without
                        # operator action, bounded by the redrive budget.
                        if self.dlq_auto_redrive:
                            auto = getattr(self.queue, "dlq_auto_redrive", None)
                            if auto is not None:
                                await auto(
                                    max_redrives=self.dlq_redrive_max,
                                    min_age_s=self.dlq_redrive_min_age_s,
                                )
                    last_recover = time.monotonic()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Admission worker iteration failed")
                await asyncio.sleep(1)
        if self.lease is not None:
            await self.lease.release()

    async def _process(self, entry_id: str, event: dict[str, Any]) -> None:
        async with self._semaphore:
            admission_id = event.get("admission_id", "unknown")
            alert = event.get("alert") or {}
            attempts = int(event.get("attempts") or 0)
            if await self._skip_if_terminal(entry_id, admission_id):
                return
            await self._retry_backoff(attempts)
            result = await self._forward_timed(alert, admission_id)

            if result.get("ok"):
                self.stats.forwarded_total += 1
                await self.store.update(
                    admission_id,
                    {
                        "status": STATUS_FORWARDED,
                        "attempts": attempts + 1,
                        "downstream_execution_id": result.get("exec_id"),
                        "downstream_status": result.get("status_code"),
                    },
                )
                await self.queue.ack(self.group, entry_id)
                return

            await self._handle_failure(entry_id, event, admission_id, attempts, result)

    async def _skip_if_terminal(self, entry_id: str, admission_id: str) -> bool:
        # IDEMP-004: a reclaimed entry whose forward already committed
        # (store.update succeeded but the ack was lost) must NOT be
        # re-POSTed — that would spawn a duplicate downstream execution.
        try:
            record = await self.store.get(admission_id)
        except Exception:
            record = None
        if record and record.get("status") in (STATUS_FORWARDED, STATUS_DEAD):
            stats = self.stats
            stats.dedup_total += 1
            logger.info(
                "Admission %s already %s — skipping re-forward (dedup)",
                admission_id,
                record.get("status"),
            )
            await self.queue.ack(self.group, entry_id)
            return True
        return False

    async def _retry_backoff(self, attempts: int) -> None:
        if attempts <= 0:
            return
        delay = self._retry_delay(attempts)
        if delay > 0:
            # Backoff BEFORE forward: the entry stays pending with
            # this consumer; XAUTOCLAIM only reclaims entries idle
            # longer than stale_ms (30s > max delay 32s is a
            # deliberate bound — keep retry_cap_s < stale_ms).
            await asyncio.sleep(min(delay, self.stale_ms / 2000))

    async def _forward_timed(self, alert: dict[str, Any], admission_id: str) -> dict[str, Any]:
        stats = self.stats
        stats.inflight += 1
        t0 = time.monotonic()
        try:
            return await self.forward(alert)
        except Exception as exc:
            logger.warning("Forward failed for %s: %s", admission_id, exc)
            return {"ok": False, "error": str(exc)}
        finally:
            stats.inflight -= 1
            stats.forward_seconds_total += time.monotonic() - t0
            stats.processed_total += 1

    async def _handle_failure(
        self,
        entry_id: str,
        event: dict[str, Any],
        admission_id: str,
        attempts: int,
        result: dict[str, Any],
    ) -> None:
        stats = self.stats
        attempts += 1
        stats.last_error = str(result.get("error", ""))[:200]
        stats.errors[stats.last_error or "unknown"] = (
            stats.errors.get(stats.last_error or "unknown", 0) + 1
        )
        if attempts >= self.max_attempts:
            stats.dead_total += 1
            # DLQ alert: a dead admission is an operator-visible event
            # — surface it in logs, not only via the /metrics counter
            # and the DLQ endpoints nobody polls.
            logger.error(
                "Admission %s dead-lettered after %d attempt(s): %s",
                admission_id,
                attempts,
                result.get("error", "forward failed"),
            )
            await self.queue.dead_letter(event, reason=result.get("error", "forward failed"))
            await self.store.update(
                admission_id,
                {
                    "status": STATUS_DEAD,
                    "attempts": attempts,
                    "last_error": result.get("error"),
                },
            )
            await self.queue.ack(self.group, entry_id)
            return

        stats.retried_total += 1
        event["attempts"] = attempts
        await self.store.update(
            admission_id,
            {"status": STATUS_QUEUED, "attempts": attempts, "last_error": result.get("error")},
        )
        await self.queue.enqueue(event)
        await self.queue.ack(self.group, entry_id)
