"""PERF-001: asynchronous alert admission.

``POST /api/v1/alerts`` validates the payload, stamps an ``alert_id`` when
absent, persists a minimal admission record and enqueues the event on the
durable ``EventQueue`` port — returning 202 immediately. A background
worker then forwards each admission to the slow synchronous downstream
(Shuffle webhook) with retry/DLQ semantics. This decouples admission
latency from downstream workflow execution time and makes the admission
crash-safe.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from soar_lab.application.ports.output import AdmissionStore, EventQueue
from soar_lab.common.ids import new_id

logger = logging.getLogger(__name__)

STATUS_QUEUED = "queued"
STATUS_FORWARDED = "forwarded"
STATUS_DEAD = "dead"
STATUS_FAILED = "failed"


class AdmissionValidationError(ValueError):
    """Raised when an incoming alert payload cannot be admitted."""


class BackpressureError(RuntimeError):
    """Raised when the admission queue is saturated (PERF-003).

    The HTTP layer maps this to ``503 + Retry-After`` so callers can
    retry later instead of silently losing alerts to stream trimming.
    """


# IDEMP-002: fields that identify the *submission*, not the alert — they
# are excluded from the content fingerprint so two identical alerts sent
# twice deduplicate, while genuinely different alerts never collapse.
_VOLATILE_KEY_FIELDS = frozenset({"alert_id", "idempotency_key", "admission_id"})


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

    async def admit(
        self,
        alert: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Validate, persist and enqueue ``alert``; return 202-shaped result.

        Idempotent on ``idempotency_key`` (defaults to ``alert_id`` when the
        caller supplies one): a replayed submission returns the existing
        admission instead of enqueueing a duplicate.
        """
        self._validate_payload(alert)

        key = (
            idempotency_key
            or alert.get("idempotency_key")
            or alert.get("alert_id")
            or _content_fingerprint(alert)
        )

        alert = alert.copy()
        alert.setdefault("alert_id", new_id("alr"))
        if key:
            # Stamp the effective key into the body so the admission
            # worker can propagate it downstream (IDEMP-003).
            alert["idempotency_key"] = str(key)
        admission_id = new_id("adm")

        # IDEMP-001: claim the key ATOMICALLY first (SET NX). find-then-
        # bind raced: two concurrent admits with the same key both passed
        # find_by_key before either bound → duplicate enqueue.
        if key:
            existing = await self.store.try_bind_key(str(key), admission_id)
            if existing is not None:
                logger.debug("Idempotent replay for key %s -> %s", key, existing)
                rec = await self.store.get(existing)
                return self._result(existing, rec)

        record = {
            "admission_id": admission_id,
            "alert_id": alert["alert_id"],
            "status": STATUS_QUEUED,
            "attempts": 0,
            "queued_at": _utcnow(),
            "idempotency_key": str(key) if key else None,
        }
        await self._persist_and_enqueue(record, alert, key)
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
        try:
            # PERF-003 backpressure: reject before persisting when the
            # backlog is saturated — the caller gets a retryable 503
            # instead of a lost admission.
            depth = await self.queue.depth()
            if depth >= self.max_queue_depth:
                raise BackpressureError(
                    f"admission queue saturated ({depth} >= {self.max_queue_depth})"
                )

            await self.store.create(record)
            await self.queue.enqueue({"admission_id": admission_id, "attempts": 0, "alert": alert})
        except Exception:
            # Compensation: free the NX claim so the key does not point
            # at a phantom admission forever.
            if key:
                await self.store.unbind_key(str(key), admission_id)
            raise

    async def status(self, admission_id: str) -> dict[str, Any] | None:
        """Return the admission record or ``None`` when unknown."""
        return await self.store.get(admission_id)

    @staticmethod
    def _result(admission_id: str, record: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "admission_id": admission_id,
            "status": (record or {}).get("status", STATUS_QUEUED),
            "status_url": f"/api/v1/alerts/{admission_id}",
        }
