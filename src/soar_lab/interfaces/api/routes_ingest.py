"""PERF-001: alert admission routes.

``POST /api/v1/alerts`` returns 202 with an ``admission_id`` and a
``status_url``; the alert is forwarded to Shuffle asynchronously by the
admission worker. ``GET /api/v1/alerts/{admission_id}`` exposes the
admission lifecycle (queued -> forwarded/dead).

QUEUE-002: the DLQ is operator-visible and recoverable — ``GET`` lists
poisoned entries, ``POST .../redrive`` re-enqueues one, ``DELETE`` purges.

VAL-001/002: the alert payload is validated by ``AlertIngestSchema``
(typed known fields + bounded lengths) instead of a raw ``dict``.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from soar_lab.application.use_cases.alert_admission import (
    AdmissionValidationError,
    BackpressureError,
)
from soar_lab.domain.models import AlertSeverity

from .auth import require_api_auth

logger = logging.getLogger(__name__)

_AUTH = Depends(require_api_auth)


class AlertIngestSchema(BaseModel):
    """VAL-001/002: validated alert envelope.

    Extra fields are allowed — the SOAR lab receives heterogeneous
    simulator/Shuffle payloads.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    alert_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=256)
    title: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=8192)
    source: str | None = Field(default=None, max_length=128)
    alert_type: str | None = Field(default=None, max_length=128)
    event_type: str | None = Field(default=None, max_length=128)
    severity: int | str | None = None
    hostname: str | None = Field(default=None, max_length=253)
    hash: str | None = Field(default=None, max_length=128)
    domain: str | None = Field(default=None, max_length=253)
    detection_time: str | None = Field(default=None, max_length=64)
    mitre_techniques: list[str] | None = Field(default=None, max_length=64)

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_bounds(cls, v: int | str | None) -> int | str | None:
        # mode="before": pydantic's lax int coercion turns True -> 1,
        # which would smuggle `severity: true` in as LOW.
        if isinstance(v, bool):
            raise ValueError("severity must not be a bool")
        if isinstance(v, int) and not (
            AlertSeverity.LOW.value <= v <= AlertSeverity.CRITICAL.value
        ):
            raise ValueError(
                f"severity int must be in {AlertSeverity.LOW.value}.."
                f"{AlertSeverity.CRITICAL.value}"
            )
        if isinstance(v, str) and len(v) > 32:
            raise ValueError("severity str must be <=32 chars")
        return v

    @field_validator("hash")
    @classmethod
    def _hash_shape(cls, v: str | None) -> str | None:
        if v is not None and len(v) not in (32, 40, 64):
            raise ValueError("hash must be MD5/SHA1/SHA256 length")
        return v

    def to_alert_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class RedriveRequest(BaseModel):
    """Request body for redriving a dead-lettered alert."""

    dlq_entry_id: Annotated[str, Field(min_length=1, max_length=64)]


class DlqPurgeResult(BaseModel):
    """Result of a dead-letter queue purge operation."""

    purged: int


def register_ingest_routes(
    app_instance: FastAPI,
    admission_service: Any = None,
) -> None:
    """Register alert admission endpoints on the app.

    ``admission_service`` is the application use case
    (``AlertAdmissionUseCase``); when ``None`` the endpoints return 503 —
    admission is considered a core capability, not an optional extra.
    """

    def _service() -> Any:
        svc = admission_service or getattr(app_instance.state, "admission_service", None)
        if svc is None:
            raise HTTPException(status_code=503, detail="Alert admission is not available")
        return svc

    def _queue() -> Any:
        queue = getattr(_service(), "queue", None)
        if queue is None:
            raise HTTPException(status_code=503, detail="Queue backend is not available")
        return queue

    @app_instance.post(
        "/api/v1/alerts",
        status_code=202,
        dependencies=[_AUTH],
        tags=["ingest"],
        summary="Admit an alert for asynchronous processing",
    )
    async def admit_alert(alert: AlertIngestSchema) -> dict[str, Any]:
        try:
            return await _service().admit(alert.to_alert_dict())
        except AdmissionValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except BackpressureError as exc:
            # PERF-003: saturated queue -> explicit retryable 503.
            raise HTTPException(
                status_code=503,
                detail=str(exc),
                headers={"Retry-After": "5"},
            ) from exc

    @app_instance.get(
        "/api/v1/alerts/{admission_id}",
        dependencies=[_AUTH],
        tags=["ingest"],
        summary="Admission status for an alert",
    )
    async def admission_status(admission_id: str) -> dict[str, Any]:
        record = await _service().status(admission_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Unknown admission_id")
        return record

    # ------------------------------------------------------------------
    # QUEUE-002 / QUEUE-006: DLQ lifecycle + queue metrics (all authed)
    # ------------------------------------------------------------------

    @app_instance.get(
        "/api/v1/queue/dlq",
        dependencies=[_AUTH],
        tags=["ingest"],
        summary="List dead-lettered admission entries",
    )
    async def dlq_list(count: Annotated[int, Query(ge=1, le=1000)] = 50) -> dict[str, Any]:
        queue = _queue()
        return {
            "size": await queue.dlq_size(),
            "entries": await queue.dlq_list(min(count, 200)),
        }

    @app_instance.post(
        "/api/v1/queue/dlq/redrive",
        dependencies=[_AUTH],
        tags=["ingest"],
        summary="Redrive a dead-lettered entry back to the admission stream",
    )
    async def dlq_redrive(body: RedriveRequest) -> dict[str, Any]:
        ok = await _queue().dlq_redrive(body.dlq_entry_id)
        if not ok:
            raise HTTPException(status_code=404, detail="DLQ entry not found or unrecoverable")
        return {"redriven": True, "dlq_entry_id": body.dlq_entry_id}

    @app_instance.delete(
        "/api/v1/queue/dlq",
        dependencies=[_AUTH],
        tags=["ingest"],
        summary="Purge the admission dead-letter queue",
    )
    async def dlq_purge() -> DlqPurgeResult:
        return DlqPurgeResult(purged=await _queue().dlq_purge())

    @app_instance.get(
        "/api/v1/queue/metrics",
        dependencies=[_AUTH],
        tags=["ingest"],
        summary="Admission queue metrics (depth, lag, dlq size)",
    )
    async def queue_metrics() -> dict[str, Any]:
        return await _queue().metrics()

    @app_instance.get(
        "/api/v1/audit",
        dependencies=[_AUTH],
        tags=["ingest"],
        summary="AUTH-004: bounded auth/RBAC audit trail (admin only)",
    )
    async def audit_trail(limit: Annotated[int, Query(ge=0, le=1000)] = 200) -> dict[str, Any]:
        svc = getattr(app_instance.state, "auth_service", None)
        events = list(getattr(svc, "audit", None).events) if svc and svc.audit else []
        tail = min(limit, 1000)
        return {"size": len(events), "events": events[len(events) - tail :]}

    @app_instance.get(
        "/api/v1/config",
        dependencies=[_AUTH],
        tags=["ingest"],
        summary="BL-CFG: effective runtime configuration, secrets redacted (admin only)",
    )
    async def config_dump() -> dict[str, Any]:
        """Expose the effective config with secrets redacted by default.

        RBAC keeps this admin-only (``/api/v1/config`` is in
        ``_ADMIN_PREFIXES``); ``Settings.get_all()`` already redacts, so an
        accidental future reclassification cannot leak credentials through
        this endpoint — defence in depth, not trust in one layer.
        """
        svc = getattr(app_instance.state, "config_provider", None)
        if svc is None:
            return {"values": {}, "redacted": True}
        get_all = getattr(svc, "get_all", None)
        if get_all is None:
            return {"values": {}, "redacted": True}
        return {"values": get_all(), "redacted": True}
