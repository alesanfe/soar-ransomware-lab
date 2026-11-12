"""PERF-001: alert admission routes.

``POST /api/v1/alerts`` returns 202 with an ``admission_id`` and a
``status_url``; the alert is forwarded to Shuffle asynchronously by the
admission worker. ``GET /api/v1/alerts/{admission_id}`` exposes the
admission lifecycle (queued -> forwarded/dead; then the workflow
verdict via callback -> workflow_accepted / workflow_rejected).

QUEUE-002: the DLQ is operator-visible and recoverable — ``GET`` lists
poisoned entries, ``POST .../redrive`` re-enqueues one, ``DELETE`` purges.

VAL-001/002 + CONTRACT-001/003: the alert payload is validated by
``AlertIngestSchema`` against the shared contract (``contracts/``):
severity is normalized to the canonical 0..4 scale, ``schema_version``
is pinned, IP/hostname formats are checked, extras are bounded and
free-text fields go through ``PayloadSanitizer`` (INPUT-001).
"""

from __future__ import annotations

import ipaddress
import logging
import re
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from soar_lab.application.use_cases.alert_admission import (
    AdmissionValidationError,
    BackpressureError,
    IdempotencyConflictError,
    QueueUnavailableError,
)
from soar_lab.domain.severity import (
    DEFAULT_SEVERITY,
    SEVERITY_NAMES,
    SeverityContractError,
    normalize_severity,
)
from soar_lab.security.sanitization import PayloadSanitizer

from .auth import require_api_auth

logger = logging.getLogger(__name__)

_AUTH = Depends(require_api_auth)
_sanitizer = PayloadSanitizer()

_CONTRACT_VERSIONS = {"1.0"}  # contracts/versions.json — bump together
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)[A-Za-z0-9]([A-Za-z0-9_.-]*[A-Za-z0-9])?$"
)
_MAX_EXTRA_KEYS = 64
_MAX_EXTRA_STR = 4096
_SANITIZED_FIELDS = ("description", "title", "source", "alert_type", "event_type")


def _check_ip(value: str) -> str:
    ipaddress.ip_address(value)  # raises ValueError on garbage
    return value


class AlertIngestSchema(BaseModel):
    """CONTRACT-001/003 + INPUT-004: validated alert envelope.

    ``extra="allow"`` is kept for heterogeneous simulator payloads but
    is now *bounded*: unknown keys are counted and size-capped instead
    of forwarded blindly. Known fields validate against the shared
    contract in ``contracts/alert.schema.json``.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    schema_version: str = Field(default="1.0", max_length=16)
    alert_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=256)
    title: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=8192)
    source: str | None = Field(default=None, max_length=128)
    alert_type: str | None = Field(default=None, max_length=128)
    event_type: str | None = Field(default=None, max_length=128)
    severity: int | str | None = Field(default=None)
    hostname: str | None = Field(default=None, max_length=253)
    src_ip: str | None = Field(default=None, max_length=45)
    hash: str | None = Field(default=None, max_length=128)
    domain: str | None = Field(default=None, max_length=253)
    detection_time: str | None = Field(default=None, max_length=64)
    mitre_techniques: list[str] | None = Field(default=None, max_length=64)

    @field_validator("schema_version")
    @classmethod
    def _known_version(cls, v: str) -> str:
        if v not in _CONTRACT_VERSIONS:
            raise ValueError(f"unknown schema_version {v!r} (supported: {_CONTRACT_VERSIONS})")
        return v

    @field_validator("severity", mode="before")
    @classmethod
    def _severity_bounds(cls, v: int | str | None) -> int | str | None:
        # CONTRACT-001: same table as normalize_inputs.py — nothing the
        # API admits can be dropped downstream on severity alone.
        if v is None:
            return v  # normalized to DEFAULT_SEVERITY in to_alert_dict
        try:
            return normalize_severity(v)
        except SeverityContractError as exc:
            raise ValueError(str(exc)) from exc

    @field_validator("hash")
    @classmethod
    def _hash_shape(cls, v: str | None) -> str | None:
        if v is not None and len(v) not in (32, 40, 64):
            raise ValueError("hash must be MD5/SHA1/SHA256 length")
        return v

    @field_validator("src_ip")
    @classmethod
    def _src_ip_valid(cls, v: str | None) -> str | None:
        if v is not None:
            _check_ip(v)
        return v

    @field_validator("hostname", "domain")
    @classmethod
    def _hostname_shape(cls, v: str | None) -> str | None:
        if v is not None and not _HOSTNAME_RE.match(v):
            raise ValueError("invalid hostname/domain shape")
        return v

    @model_validator(mode="after")
    def _bound_extras(self) -> "AlertIngestSchema":
        extras = self.model_extra or {}
        if len(extras) > _MAX_EXTRA_KEYS:
            raise ValueError(f"too many extra fields ({len(extras)} > {_MAX_EXTRA_KEYS})")
        for k, v in extras.items():
            if isinstance(v, str) and len(v) > _MAX_EXTRA_STR:
                raise ValueError(f"extra field {k!r} exceeds {_MAX_EXTRA_STR} chars")
        return self

    def to_alert_dict(self) -> dict[str, Any]:
        data = self.model_dump(exclude_none=True)
        # Contract normalization happens at the edge, once:
        data["severity"] = (
            normalize_severity(data["severity"])
            if "severity" in data
            else DEFAULT_SEVERITY
        )
        # INPUT-001: free-text fields are sanitized BEFORE the payload is
        # queued/forwarded — this is the real ingest path, not a test seam.
        for field in _SANITIZED_FIELDS:
            if isinstance(data.get(field), str):
                data[field] = _sanitizer.sanitize(data[field])
        return data


class RedriveRequest(BaseModel):
    """Request body for redriving a dead-lettered alert."""

    dlq_entry_id: Annotated[str, Field(min_length=1, max_length=64)]


class DlqPurgeResult(BaseModel):
    """Result of a dead-letter queue purge operation."""

    purged: int


class WorkflowCallback(BaseModel):
    """CONTRACT-004: signed workflow verdict on a delivered admission."""

    model_config = ConfigDict(extra="forbid")
    admission_id: Annotated[str, Field(min_length=1, max_length=64)]
    outcome: Annotated[str, Field(pattern="^(accepted|rejected)$")]
    reason: str | None = Field(default=None, max_length=512)
    event_id: str | None = Field(default=None, max_length=128)


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
        except IdempotencyConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (BackpressureError, QueueUnavailableError) as exc:
            # PERF-003/B4: saturated or unavailable queue -> explicit
            # retryable 503; the record (when persisted) is reconcilable.
            raise HTTPException(
                status_code=503,
                detail=str(exc),
                headers={"Retry-After": "5"},
            ) from exc

    from soar_lab.security.webhook_signing import (
        InMemoryNonceStore,
        RedisNonceStore,
        SignatureError,
        verify_request,
    )

    _nonce_store = InMemoryNonceStore()

    def _nonce_backend() -> Any:
        rc = getattr(app_instance.state, "redis_client", None)
        if rc is not None:
            try:
                return RedisNonceStore(rc)
            except Exception:
                pass
        return _nonce_store

    async def _require_callback_signature(request: Request) -> None:
        """HMAC-003: signed-callback gate — enforced when CALLBACK_HMAC_KEY
        is provisioned; token-only otherwise (documented lab mode)."""
        cp = request.app.state.config_provider
        secret = str(cp.get("CALLBACK_HMAC_KEY") or "") if cp else ""
        if not secret:
            return  # unsigned lab mode — scope token still required (_AUTH)
        prev = str(cp.get("CALLBACK_HMAC_KEY_PREV") or "") if cp else ""

        def resolver(key_id: str):
            cur_id = str(cp.get("CALLBACK_HMAC_KEY_ID") or "wf-callback-1")
            if key_id == cur_id:
                return secret
            if prev and key_id != cur_id:
                return (prev, True)
            return None

        body = await request.body()
        try:
            await verify_request(
                resolver,
                method=request.method,
                path=request.url.path,
                headers=request.headers,
                body=body,
                nonce_store=_nonce_backend(),
            )
        except SignatureError as exc:
            _sig_metrics["rejections"] += 1
            raise HTTPException(status_code=401, detail="invalid signature") from exc
        _sig_metrics["accepted"] += 1

    _sig_metrics = {"accepted": 0, "rejections": 0}

    @app_instance.post(
        "/api/v1/alerts/callback",
        status_code=200,
        dependencies=[_AUTH, Depends(_require_callback_signature)],
        tags=["ingest"],
        summary="CONTRACT-004: workflow verdict callback (callback scope + HMAC)",
    )
    async def workflow_callback(body: WorkflowCallback) -> dict[str, Any]:
        svc = _service()
        record = await svc.record_workflow_verdict(
            body.admission_id, body.outcome, body.reason or ""
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Unknown admission_id")
        return {"admission_id": body.admission_id, "status": record.get("status")}

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
        """Expose the effective config with secrets redacted by default."""
        svc = getattr(app_instance.state, "config_provider", None)
        if svc is None:
            return {"values": {}, "redacted": True}
        get_all = getattr(svc, "get_all", None)
        if get_all is None:
            return {"values": {}, "redacted": True}
        return {"values": get_all(), "redacted": True}


# Kept importable for the contract tests: the severity table the workflow
# must mirror (contracts/severity.schema.json + domain.severity).
__all__ = [
    "AlertIngestSchema",
    "WorkflowCallback",
    "register_ingest_routes",
    "SEVERITY_NAMES",
]
