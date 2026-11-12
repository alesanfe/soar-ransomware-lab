"""PERF-001: admission worker - durable forward to the slow downstream.

Consumes admitted alerts from the ``EventQueue`` port and forwards each
``alert`` via the injected ``forward`` callable (an async function that
POSTs to the Shuffle webhook and returns ``{"ok": bool, ...}``).

Semantics:

- success          -> ``store.update(status=forwarded, ...)`` + ``queue.ack``
- retryable failure -> ``attempts += 1``, event re-enqueued, original acked
- non-retryable    -> ``queue.dead_letter`` immediately (WORKER-004 policy)
- ``max_attempts`` -> ``queue.dead_letter`` + ``store.update(status=dead)``
- restart          -> ``recover()`` claims stale pending entries and processes
  them, so a crash mid-forward does not lose admissions. Runs every
  ``recover_interval_s`` seconds during ``run`` (QUEUE-005).

WORKER-001: batch results are gathered with ``return_exceptions=True`` —
one entry's failure never cancels nor detaches its siblings.

WORKER-003: dedup on reclaimed entries is fail-safe — when the store is
unreadable the entry is left pending (retry later) instead of re-POSTing
a possibly-committed forward.

Retries honour an exponential backoff with AWS-style *full jitter*
(QUEUE-003): ``sleep = uniform(0, min(cap, base * 2**attempts))``.

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
    STATUS_RETRY_SCHEDULED,
    STATUS_WORKFLOW_ACCEPTED,
    STATUS_WORKFLOW_REJECTED,
    check_transition,
)
from soar_lab.security.redaction import redact_text

logger = logging.getLogger(__name__)

ForwardFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

_TERMINAL = frozenset(
    {STATUS_FORWARDED, STATUS_DEAD, STATUS_WORKFLOW_ACCEPTED, STATUS_WORKFLOW_REJECTED}
)


@dataclass
class WorkerStats:
    """QUEUE-006: cumulative worker counters exported via ``/metrics``."""

    processed_total: int = 0
    forwarded_total: int = 0
    retried_total: int = 0
    dead_total: int = 0
    dedup_total: int = 0
    orphans_repaired_total: int = 0
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
        # PIPE-EVAL-001: cap must stay < stale_ms — during the backoff the
        # entry is PENDING with this consumer; a delay past stale_ms lets
        # XAUTOCLAIM re-deliver it and the same forward runs twice. The
        # previous default (32s) violated its own documented bound.
        retry_cap_s: float = 16.0,
        recover_interval_s: float = 60.0,
        dlq_auto_redrive: bool = True,
        dlq_redrive_max: int = 3,
        dlq_redrive_min_age_s: float = 60.0,
        reconciler: Any | None = None,
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
        self.reconciler = reconciler
        self.lease = lease
        self._semaphore = asyncio.Semaphore(concurrency)
        self._rng = random.Random()
        self._fence_token = None
        if retry_cap_s * 1000 >= stale_ms:
            raise ValueError(
                f"retry_cap_s ({retry_cap_s}s) must stay < stale_ms "
                f"({stale_ms}ms) — a backoff delay outliving the reclaim "
                "threshold re-delivers the same entry mid-sleep (duplicate "
                "forward). Keep the cap below the stale bound."
            )

    def _retry_delay(self, attempts: int) -> float:
        """QUEUE-003: full-jitter exponential backoff (AWS pattern)."""
        cap = min(self.retry_cap_s, self.retry_base_s * (2 ** max(attempts - 1, 0)))
        return self._rng.uniform(0, cap)

    async def run_once(self) -> int:
        """Process one batch of new entries; return how many were handled."""
        batch = await self.queue.read(self.group, self.consumer, self.batch_size, self.poll_ms)
        if not batch:
            return 0
        # WORKER-001: return_exceptions — a sibling failure is recorded,
        # never propagated to cancel/detach the rest of the batch.
        results = await asyncio.gather(
            *starmap(self._process, batch), return_exceptions=True
        )
        for (entry_id, event), res in zip(batch, results, strict=False):
            if isinstance(res, Exception):
                logger.exception(
                    "Entry %s (admission %s) failed unhandled — left pending for recover",
                    entry_id,
                    (event or {}).get("admission_id", "?"),
                )
        return len(batch)

    async def recover(self) -> int:
        """Claim stale pending entries (post-restart recovery) and process them."""
        stale = await self.queue.claim_stale(self.group, self.consumer, self.stale_ms)
        if not stale:
            return 0
        logger.info("Recovering %d stale admission(s)", len(stale))
        results = await asyncio.gather(
            *starmap(self._process, stale), return_exceptions=True
        )
        for (entry_id, event), res in zip(stale, results, strict=False):
            if isinstance(res, Exception):
                logger.exception(
                    "Recovered entry %s (admission %s) failed unhandled",
                    entry_id,
                    (event or {}).get("admission_id", "?"),
                )
        return len(stale)

    async def run(self, stop: asyncio.Event) -> None:
        """Main loop: read batches until ``stop`` is set."""
        await self.queue.ensure_group(self.group)
        await self.recover()
        last_recover = time.monotonic()
        while not stop.is_set():
            try:
                await self.run_once()
                if time.monotonic() - last_recover >= self.recover_interval_s:
                    # R3: recover + reconcile + auto-redrive are singleton
                    # duties — only the lease holder runs them so N
                    # replicas don't all reclaim/redrive the same entries.
                    leader = await self._leader()
                    if leader:
                        await self.recover()
                        await self._reconcile()
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

    async def _leader(self) -> bool:
        """WORKER-005: lease check with fencing when the backend supports it."""
        if self.lease is None:
            return True
        try:
            held = await self.lease.held()
        except Exception:
            return False
        if not held:
            return False
        # PIPE-EVAL-002: token ROTATION means this worker lost the lease
        # and re-acquired it (another worker held it in between) — skip
        # this cycle's singleton duties rather than act on stale leadership.
        token = getattr(self.lease, "fence_token", None)
        if token is not None:
            if self._fence_token is not None and token != self._fence_token:
                logger.warning(
                    "Worker lease fence token rotated (%s -> %s) — leadership "
                    "was lost and re-acquired; skipping this duty cycle",
                    self._fence_token,
                    token,
                )
                self._fence_token = token
                return False
            self._fence_token = token
        return True

    async def _reconcile(self) -> None:
        if self.reconciler is None:
            return
        try:
            result = await self.reconciler()
            repaired = result.get("enqueue_failed_repaired", 0) if result else 0
            if repaired:
                self.stats.orphans_repaired_total += repaired
        except Exception:
            logger.exception("Admission reconciler failed")

    async def _process(self, entry_id: str, event: dict[str, Any]) -> None:
        async with self._semaphore:
            admission_id = event.get("admission_id", "unknown")
            alert = event.get("alert") or {}
            attempts = int(event.get("attempts") or 0)
            decision = await self._terminal_check(entry_id, admission_id)
            if decision != "process":
                return
            await self._retry_backoff(attempts)
            # IDEMP-001 (e2e): per-attempt delivery identity so the
            # workflow can correlate a retried transport with its effect.
            alert = dict(alert)
            alert.setdefault("delivery_id", f"{admission_id}:{attempts + 1}")
            alert["attempt"] = attempts + 1
            result = await self._forward_timed(alert, admission_id)

            if result.get("ok"):
                self.stats.forwarded_total += 1
                await self._update(
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

    async def _terminal_check(self, entry_id: str, admission_id: str) -> str:
        """Dedup guard: skip terminal, defer on unreadable store (WORKER-003)."""
        try:
            record = await self.store.get(admission_id)
        except Exception:
            # Fail-safe, not fail-open: an unreadable store means we
            # can't tell whether forward already committed. Leave the
            # entry pending — recover() retries after stale_ms instead
            # of risking a duplicate downstream execution.
            logger.warning(
                "Admission %s unreadable — deferring (no forward)", admission_id
            )
            return "defer"
        if record and record.get("status") in _TERMINAL:
            self.stats.dedup_total += 1
            logger.info(
                "Admission %s already %s — skipping re-forward (dedup)",
                admission_id,
                record.get("status"),
            )
            await self.queue.ack(self.group, entry_id)
            return "skip"
        return "process"

    async def _update(self, admission_id: str, fields: dict[str, Any]) -> None:
        """State-machine-checked update (ADMISSION-004)."""
        try:
            current = await self.store.get(admission_id)
        except Exception:
            current = None
        frm = (current or {}).get("status")
        to = fields.get("status")
        if to and frm and not check_transition(frm, to):
            logger.warning(
                "Illegal admission transition %s -> %s for %s (audit)",
                frm,
                to,
                admission_id,
            )
            fields = dict(fields)
            fields["transition_violation"] = f"{frm}->{to}"
        fields = dict(fields)
        fields["changed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        fields["state_version"] = int((current or {}).get("state_version", 1)) + 1
        await self.store.update(admission_id, fields)

    async def _retry_backoff(self, attempts: int) -> None:
        if attempts <= 0:
            return
        delay = self._retry_delay(attempts)
        if delay > 0:
            await asyncio.sleep(min(delay, self.stale_ms / 2000))

    async def _forward_timed(self, alert: dict[str, Any], admission_id: str) -> dict[str, Any]:
        stats = self.stats
        stats.inflight += 1
        t0 = time.monotonic()
        try:
            return await self.forward(alert)
        except Exception as exc:
            logger.warning("Forward failed for %s: %s", admission_id, redact_text(exc))
            return {"ok": False, "error_code": "FORWARD_EXCEPTION", "retryable": True}
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
        # WORKER-004: error class decides the retry policy — structured
        # code (no URLs/secrets) is what lands in state, logs and metrics.
        error_code = str(
            result.get("error_code")
            or redact_text(result.get("error") or "FORWARD_FAILED", max_len=80)
        )
        retryable = bool(result.get("retryable", True))
        stats.last_error = error_code
        stats.errors[error_code] = stats.errors.get(error_code, 0) + 1

        if not retryable or attempts >= self.max_attempts:
            stats.dead_total += 1
            logger.error(
                "Admission %s dead-lettered after %d attempt(s): %s",
                admission_id,
                attempts,
                error_code,
            )
            await self.queue.dead_letter(event, reason=error_code)
            await self._update(
                admission_id,
                {
                    "status": STATUS_DEAD,
                    "attempts": attempts,
                    "last_error": error_code,
                },
            )
            await self.queue.ack(self.group, entry_id)
            return

        stats.retried_total += 1
        event["attempts"] = attempts
        await self._update(
            admission_id,
            {
                "status": STATUS_RETRY_SCHEDULED,
                "attempts": attempts,
                "last_error": error_code,
            },
        )
        await self.queue.enqueue(event)
        await self.queue.ack(self.group, entry_id)
