"""GRAF-ALERT-RX: Grafana Alertmanager webhook receiver.

Grafana sends firing/resolved alert notifications here (contact point
``soar-api-webhook``). The endpoint authenticates with the shared
``X-Service-Token`` gate — it is deliberately NOT admitted to the alert
pipeline: observability alerts re-entering the SOAR admission queue could
create a feedback loop (SOAR alert -> pipeline load -> more SOAR alerts).

Instead each notification is:

1. Counted (exported at ``GET /metrics`` as
   ``soar_grafana_alert_notifications_total{status=...}``).
2. Emitted as a structured log line tagged ``grafana_alert=1`` — Promtail
   ships it to Loki, so delivered notifications are queryable from the
   Grafana logs dashboard itself (closed-loop, verifiable delivery).

Payload format: Alertmanager-compatible webhook body
(``status``, ``receiver``, ``alerts[]``, ``commonLabels``,
``commonAnnotations``). Unknown/extra fields are ignored.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from soar_lab.config.logging import get_logger

from .auth import require_api_auth

logger = get_logger(__name__)

_AUTH = Depends(require_api_auth)

# Process-wide counters; scraped by /metrics.
_counts: dict[str, int] = {"firing": 0, "resolved": 0, "other": 0}


def grafana_alert_counters() -> dict[str, int]:
    """Return a snapshot of received-notification counters."""
    return dict(_counts)


class GrafanaAlert(BaseModel, extra="allow"):
    """Single alert inside an Alertmanager webhook payload."""

    status: str = "unknown"
    labels: dict[str, Any] = Field(default_factory=dict)
    annotations: dict[str, Any] = Field(default_factory=dict)
    startsAt: str | None = None
    endsAt: str | None = None
    fingerprint: str | None = None


class AlertmanagerWebhook(BaseModel, extra="allow"):
    """Alertmanager/Grafana notification payload (v4 schema, tolerant)."""

    status: str = "unknown"
    receiver: str | None = None
    alerts: list[GrafanaAlert] = Field(default_factory=list)
    commonLabels: dict[str, Any] = Field(default_factory=dict)
    commonAnnotations: dict[str, Any] = Field(default_factory=dict)


_CONTROL_CHARS = tuple(chr(c) for c in range(0x20)) + ("\x7f",)


def _log_safe(value: Any, max_len: int = 120) -> str:
    """Escape log-forging characters in untrusted label values."""
    if value is None:
        return "-"
    text = str(value)
    for c in _CONTROL_CHARS:
        text = text.replace(c, " ")
    return text[:max_len] or "-"


def register_grafana_alert_routes(app_instance: FastAPI) -> None:
    """Register the Grafana notification receiver endpoint."""

    @app_instance.post(
        "/api/v1/alerts/grafana",
        status_code=200,
        dependencies=[_AUTH],
        tags=["observability"],
        summary="Receive Grafana alert notifications (Alertmanager webhook)",
    )
    async def receive_grafana_alert(payload: AlertmanagerWebhook) -> dict[str, Any]:
        status = payload.status if payload.status in ("firing", "resolved") else "other"
        _counts[status] = _counts.get(status, 0) + 1

        for alert in payload.alerts:
            alert_status = alert.status if alert.status in ("firing", "resolved") else status
            log = logger.warning if alert_status == "firing" else logger.info
            # INPUT-003: label values are attacker-influenceable — escape
            # control chars before they reach the log line (CWE-117: a
            # newline in alertname must not forge extra Loki entries).
            log(
                "grafana_alert=1 status=%s name=%s severity=%s summary=%s "
                "fingerprint=%s starts_at=%s ends_at=%s receiver=%s",
                alert_status,
                _log_safe(alert.labels.get("alertname", alert.labels.get("rulename", "unknown"))),
                _log_safe(alert.labels.get("severity", "none")),
                _log_safe(alert.annotations.get("summary", ""), 200),
                _log_safe(alert.fingerprint),
                _log_safe(alert.startsAt),
                _log_safe(alert.endsAt),
                _log_safe(payload.receiver),
            )

        if not payload.alerts:
            logger.info(
                "grafana_alert=1 status=%s empty notification receiver=%s", status, payload.receiver
            )

        return {"status": "ok", "received": len(payload.alerts)}
