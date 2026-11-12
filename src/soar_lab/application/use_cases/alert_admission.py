"""PERF-001: asynchronous alert admission.

``POST /api/v1/alerts`` validates the payload, stamps an ``alert_id`` when
absent, persists a minimal admission record and enqueues the event on the
durable ``EventQueue`` port — returning 202 immediately. A background
worker then forwards each admission to the slow synchronous downstream
(Shuffle webhook) with retry/DLQ semantics. This decouples admission
latency from downstream workflow execution time and makes the admission
crash-safe.

ADMISSION-004: admission lifecycle is an explicit state machine
(``TRANSITIONS``); writes go through :func:`check_transition` so an
impossible jump (e.g. ``dead -> queued``) is rejected loudly instead of
corrupting the record.

Transport vs processing (CONTRACT-004): ``forwarded``/``delivered`` means
"the hook returned 2xx" — NOT "the workflow accepted the alert". The
workflow reports its verdict on the signed callback endpoint, which moves
the record to ``workflow_accepted`` or ``workflow_rejected``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from soar_lab.application.ports.output import AdmissionStore, EventQueue
from soar_lab.common.ids import new_id
from soar_lab.security.redaction import redact_text

logger = logging.getLogger(__name__)

# ── ADMISSION-004: explicit state machine ─────────────────────────────────────
STATUS_QUEUED = "queued"
STATUS_FORWARDED = "forwarded"  # transport delivered (2xx), NOT processed
STATUS_DELIVERED = STATUS_FORWARDED  # alias kept for record readability
STATUS_DEAD = "dead"
STATUS_FAILED = "failed"
STATUS_ENQUEUE_FAILED = "enqueue_failed"
STATUS_RETRY_SCHEDULED = "retry_scheduled"
STATUS_WORKFLOW_ACCEPTED = "workflow_accepted"
STATUS_WORKFLOW_REJECTED = "workflow_rejected"
STATUS_INCONSISTENT = "inconsistent"

TERMINAL_STATUSES = frozenset(
    {STATUS_FORWARDED, STATUS_DEAD, STATUS_WORKFLOW_ACCEPTED, STATUS_WORKFLOW_REJECTED}
)

TRANSITIONS: dict[str, frozenset[str]] = {
    STATUS_QUEUED: frozenset(
        {
            STATUS_FORWARDED,
            STATUS_RETRY_SCHEDULED,
            STATUS_DEAD,
            STATUS_INCONSISTENT,
            STATUS_QUEUED,  # attempts bookkeeping inside queued
        }
    ),
    STATUS_RETRY_SCHEDULED: frozenset(
        {STATUS_QUEUED, STATUS_FORWARDED, STATUS_DEAD, STATUS_INCONSISTENT}
    ),
    STATUS_ENQUEUE_FAILED: frozenset({STATUS_QUEUED, STATUS_INCONSISTENT, STATUS_DEAD}),
    STATUS_FORWARDED: frozenset({STATUS_WORKFLOW_ACCEPTED, STATUS_WORKFLOW_REJECTED}),
    STATUS_DEAD: frozenset({STATUS_QUEUED}),  # operator redrive only
    STATUS_INCONSISTENT: frozenset({STATUS_QUEUED, STATUS_DEAD}),
    STATUS_WORKFLOW_ACCEPTED: frozenset(),
    STATUS_WORKFLOW_REJECTED: frozenset({STATUS_DEAD}),  # operator review path
    STATUS_FAILED: frozenset({STATUS_QUEUED, STATUS_DEAD, STATUS_INCONSISTENT}),
}


def check_transition(frm: str | None, to: str) -> bool:
    """Return True when ``frm -> to`` is a legal lifecycle transition."""
    if frm is None or frm not in TRANSITIONS:
        return to == STATUS_QUEUED
    return to in TRANSITIONS[frm]


class AdmissionValidationError(ValueError):
    """Raised when an incoming alert payload cannot be admitted."""


class BackpressureError(RuntimeError):
    """Raised when the admission queue is saturated (PERF-003).

    The HTTP layer maps this to ``503 + Retry-After`` so callers can
    retry later instead of silently losing alerts to stream trimming.
    """


class QueueUnavailableError(RuntimeError):
    """Raised when enqueue fails after the record was persisted (B4)."""


class IdempotencyConflictError(RuntimeError):
    """IDEMP-004: same idempotency key, different content fingerprint."""


# IDEMP-002: fields that identify the *submission*, not the alert — they
# are excluded from the content fingerprint so two identical alerts sent
# twice deduplicate, while genuinely different alerts never collapse.
_VOLATILE_KEY_FIELDS = frozenset(
    {"alert_id", "idempotency_key", "admission_id", "trace_id", "delivery_id", "attempt"}
)


def _content_fingerprint(alert: dict[str, Any]) -> str | None:
    """SHA-256 fingerprint of the semantic alert content (IDEMP-002).

    Canonical JSON of every field except volatile per-submission ids.
    ``None`` for an empty payload — there is nothing to deduplicate on.
    """
    payload = {k: v for k, v in alert.items() if k not in _VOLATILE_KEY_FIELDS}
    if not payload:
        return None
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "fp:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


class AlertAdmissionUseCase:
    """Admit an alert for asynchronous downstream processing."""

    def __init__(
        self,
        queue: EventQueue,
        store: AdmissionStore,
        max_payload_bytes: int = 262_144,
        max_queue_depth: int = 50_000,
    ) -> None:
        self.queue = queue
        self.store = store
        self.max_payload_bytes = max_payload_bytes
        # PERF-003: declared nominal capacity — half the ~100k stream
        # maxlen, so backpressure fires before silent MAXLEN trimming
        # can drop admitted-but-unprocessed events.
        self.max_queue_depth = max_queue_depth
        # ADMISSION-002: reconciler counters (exported via /metrics)
        self.orphans_repaired = 0
        self.orphan_bindings_cleaned = 0

    async def admit(
        self,
        alert: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Validate, persist and enqueue ``alert``; return 202-shaped result.

        Idempotent on ``idempotency_key`` (defaults to ``alert_id`` when the
        caller supplies one): a replayed submission returns the existing
        admission instead of enqueueing a duplicate. A replay carrying a
        DIFFERENT content fingerprint is a 409 conflict (IDEMP-004).
        """
        self._validate_payload(alert)
        fingerprint = _content_fingerprint(alert)

        key = (
            idempotency_key
            or alert.get("idempotency_key")
            or alert.get("alert_id")
            or fingerprint
        )

        alert = alert.copy()
        alert.setdefault("alert_id", new_id("alr"))
        if key:
            # Stamp the effective key into the body so the admission
            # worker can propagate it downstream (IDEMP-003).
            alert["idempotency_key"] = str(key)

        # IDEMP-001: claim the key ATOMICALLY first (SET NX). find-then-
        # bind raced: two concurrent admits with the same key both passed
        # find_by_key before either bound → duplicate enqueue.
        for _attempt in range(2):
            admission_id = new_id("adm")
            if not key:
                break
            existing = await self.store.try_bind_key(str(key), admission_id)
            if existing is None:
                break
            existing_rec = await self.store.get(existing)
            if existing_rec is None:
                # B5: binding without record — phantom. Repair the orphan
                # claim (CAS unbind) and compete for the key once more.
                logger.warning(
                    "Orphan idempotency binding %s -> %s — repairing", key, existing
                )
                self.orphan_bindings_cleaned += 1
                await self.store.unbind_key(str(key), existing)
                continue
            return self._replay_result(existing, existing_rec, fingerprint)
        else:
            raise QueueUnavailableError("idempotency binding unavailable")

        record = {
            "admission_id": admission_id,
            "alert_id": alert["alert_id"],
            "alert": alert,  # persisted so the reconciler can re-enqueue
            "status": STATUS_QUEUED,
            "state_version": 1,
            "attempts": 0,
            "queued_at": _utcnow(),
            "changed_at": _utcnow(),
            "idempotency_key": str(key) if key else None,
            "content_fingerprint": fingerprint,
        }
        await self._persist_and_enqueue(record, alert, key)
        return self._result(admission_id, record)

    def _replay_result(
        self, admission_id: str, record: dict[str, Any], fingerprint: str | None
    ) -> dict[str, Any]:
        existing_fp = record.get("content_fingerprint")
        if fingerprint and existing_fp and fingerprint != existing_fp:
            # IDEMP-004: collision — same key, different payload.
            logger.warning(
                "Idempotency conflict on key %s: fp %s != %s",
                record.get("idempotency_key"),
                fingerprint[:20],
                str(existing_fp)[:20],
            )
            raise IdempotencyConflictError(
                "idempotency_key already bound to different content"
            )
        logger.debug("Idempotent replay for %s -> %s", record.get("idempotency_key"), admission_id)
        return self._result(admission_id, record)

    def _validate_payload(self, alert: dict[str, Any]) -> None:
        if not isinstance(alert, dict):
            raise AdmissionValidationError("alert payload must be a JSON object")
        try:
            size = len(json.dumps(alert, default=str).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise AdmissionValidationError(
                f"alert payload is not JSON-serializable: {exc}"
            ) from exc
        if size > self.max_payload_bytes:
            raise AdmissionValidationError(f"alert payload exceeds {self.max_payload_bytes} bytes")

    async def _persist_and_enqueue(
        self, record: dict[str, Any], alert: dict[str, Any], key: Any
    ) -> None:
        admission_id = record["admission_id"]
        # PERF-003 backpressure: reject before persisting when the
        # backlog is saturated — the caller gets a retryable 503
        # instead of a lost admission.
        depth = await self.queue.depth()
        if depth >= self.max_queue_depth:
            if key:
                await self.store.unbind_key(str(key), admission_id)
            raise BackpressureError(
                f"admission queue saturated ({depth} >= {self.max_queue_depth})"
            )

        await self.store.create(record)
        try:
            await self.queue.enqueue({"admission_id": admission_id, "attempts": 0, "alert": alert})
        except Exception as exc:
            # B4: the record would sit in "queued" forever — nothing can
            # reclaim a store record with no stream entry. Compensate:
            # mark enqueue_failed (visible + reconcilable), keep the
            # binding so a caller retry replays into THIS record instead
            # of minting a second one, and surface a retryable error.
            logger.error(
                "Enqueue failed for %s — marking record enqueue_failed", admission_id
            )
            await self.store.update(
                admission_id,
                {
                    "status": STATUS_ENQUEUE_FAILED,
                    "changed_at": _utcnow(),
                    "last_error": redact_text(exc, max_len=160),
                    "error_code": "QUEUE_UNAVAILABLE",
                },
            )
            raise QueueUnavailableError(
                f"alert persisted but could not be enqueued (admission_id={admission_id})"
            ) from exc

    async def status(self, admission_id: str) -> dict[str, Any] | None:
        """Return the admission record or ``None`` when unknown."""
        return await self.store.get(admission_id)

    async def record_workflow_verdict(
        self, admission_id: str, outcome: str, reason: str = ""
    ) -> dict[str, Any] | None:
        """CONTRACT-004: workflow reports acceptance/rejection via callback.

        ``outcome`` is ``accepted`` or ``rejected``; only records in
        ``forwarded`` (transport delivered) may transition.
        """
        record = await self.store.get(admission_id)
        if record is None:
            return None
        target = (
            STATUS_WORKFLOW_ACCEPTED if outcome == "accepted" else STATUS_WORKFLOW_REJECTED
        )
        if not check_transition(record.get("status"), target):
            logger.info(
                "Ignoring %s verdict for %s in state %s",
                outcome,
                admission_id,
                record.get("status"),
            )
            return record
        await self.store.update(
            admission_id,
            {
                "status": target,
                "workflow_reason": redact_text(reason, max_len=200),
                "changed_at": _utcnow(),
                "state_version": int(record.get("state_version", 1)) + 1,
            },
        )
        return await self.store.get(admission_id)

    async def reconcile(self, max_scan: int = 500) -> dict[str, int]:
        """ADMISSION-002: repair enqueue_failed records and orphan bindings.

        Runs periodically under the worker's leader lease. Bounded scan so
        a huge keyspace never stalls the worker loop.
        """
        repaired = 0
        list_by_status = getattr(self.store, "list_by_status", None)
        if list_by_status is not None:
            try:
                stuck = await list_by_status({STATUS_ENQUEUE_FAILED}, limit=max_scan)
            except Exception:
                logger.exception("reconcile: list_by_status failed")
                stuck = []
            for rec in stuck:
                aid = rec.get("admission_id")
                alert = rec.get("alert")
                if not aid or not isinstance(alert, dict):
                    continue
                try:
                    await self.queue.enqueue(
                        {"admission_id": aid, "attempts": rec.get("attempts", 0), "alert": alert}
                    )
                    await self.store.update(
                        aid,
                        {
                            "status": STATUS_QUEUED,
                            "changed_at": _utcnow(),
                            "error_code": None,
                            "state_version": int(rec.get("state_version", 1)) + 1,
                        },
                    )
                    repaired += 1
                except Exception as exc:
                    logger.warning("reconcile: re-enqueue of %s failed: %s", aid, exc)
        self.orphans_repaired += repaired
        return {"enqueue_failed_repaired": repaired}

    @staticmethod
    def _result(admission_id: str, record: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "admission_id": admission_id,
            "status": (record or {}).get("status", STATUS_QUEUED),
            "status_url": f"/api/v1/alerts/{admission_id}",
        }
