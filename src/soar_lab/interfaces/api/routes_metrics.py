"""QUEUE-006 / OBS-lite: Prometheus text exposition at ``GET /metrics``.

Pull model — every scrape samples the live admission queue
(``queue.metrics()``) and the cumulative worker counters
(``WorkerStats``) instead of relying on a push gateway. The path is in
the DefaultDenyAuthMiddleware public whitelist on purpose: Prometheus
scrapers are unauthenticated by design (expose on the internal
interface when this leaves the lab).

Exposition format: Prometheus text-based 0.0.4 — emitted manually to
keep the module free of a hard ``prometheus_client`` dependency and to
stay fully async (no sync collector callbacks inside the event loop).
"""

from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)

_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

_START = time.monotonic()


def _metric(
    lines: list[str],
    name: str,
    value: float | None,
    help_text: str,
    mtype: str = "gauge",
    labels: dict[str, str] | None = None,
) -> None:
    """Append one HELP/TYPE/sample triple; ``None`` values are skipped."""
    if value is None:
        return
    lines.extend((f"# HELP {name} {help_text}", f"# TYPE {name} {mtype}"))
    if labels:
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        lines.append(f"{name}{{{label_str}}} {value}")
    else:
        lines.append(f"{name} {value}")


def register_metrics_route(app_instance: FastAPI) -> None:
    """Register the unauthenticated Prometheus scrape endpoint."""

    @app_instance.get("/metrics", include_in_schema=False)
    async def prometheus_metrics() -> PlainTextResponse:
        lines: list[str] = []

        _metric(
            lines,
            "soar_app_uptime_seconds",
            round(time.monotonic() - _START, 3),
            "Seconds since the metrics module was loaded.",
        )

        # --- queue gauges (sampled live) -------------------------------
        admission = getattr(app_instance.state, "admission_service", None)
        queue = getattr(admission, "queue", None)
        if queue is not None:
            try:
                m = await queue.metrics()
            except Exception as exc:
                logger.debug("queue.metrics() failed during scrape: %s", exc)
                m = {}
            _metric(
                lines,
                "soar_queue_depth",
                m.get("queue_depth"),
                "Entries currently in the admission stream.",
            )
            _metric(
                lines,
                "soar_queue_pending",
                m.get("pending"),
                "Entries pending (delivered, un-acked) for the consumer group.",
            )
            _metric(
                lines,
                "soar_queue_consumer_lag",
                m.get("consumer_lag"),
                "Consumer group lag reported by XINFO GROUPS.",
            )
            _metric(
                lines,
                "soar_queue_dlq_size",
                m.get("dlq_size"),
                "Entries in the dead-letter queue.",
            )
        _metric(
            lines,
            "soar_queue_available",
            1 if queue is not None else 0,
            "Whether the admission queue backend is wired (1) or not (0).",
        )

        # --- worker counters -------------------------------------------
        stats = getattr(app_instance.state, "admission_worker_stats", None)
        if stats is not None:
            _metric(
                lines,
                "soar_admission_processed_total",
                stats.processed_total,
                "Admissions processed by the worker.",
                mtype="counter",
            )
            _metric(
                lines,
                "soar_admission_forwarded_total",
                stats.forwarded_total,
                "Admissions forwarded downstream successfully.",
                mtype="counter",
            )
            _metric(
                lines,
                "soar_admission_retried_total",
                stats.retried_total,
                "Admissions re-enqueued after a forward failure.",
                mtype="counter",
            )
            _metric(
                lines,
                "soar_admission_dead_total",
                stats.dead_total,
                "Admissions dead-lettered after max attempts.",
                mtype="counter",
            )
            _metric(
                lines,
                "soar_admission_forward_seconds_total",
                round(stats.forward_seconds_total, 6),
                "Cumulative downstream forward latency.",
                mtype="counter",
            )
            _metric(
                lines,
                "soar_admission_inflight",
                stats.inflight,
                "Forwards currently in flight.",
            )
            for err, count in sorted(stats.errors.items()):
                _metric(
                    lines,
                    "soar_admission_forward_errors_total",
                    count,
                    "Forward failures by last-error fingerprint.",
                    mtype="counter",
                    labels={"error": err[:80].replace('"', "'").replace("\\", "/")},
                )

        # --- GRAF-ALERT-RX: notifications received from Grafana --------
        from .routes_grafana_alerts import grafana_alert_counters

        for alert_status, count in sorted(grafana_alert_counters().items()):
            _metric(
                lines,
                "soar_grafana_alert_notifications_total",
                count,
                "Alertmanager notifications received from Grafana by status.",
                mtype="counter",
                labels={"status": alert_status},
            )

        return PlainTextResponse("\n".join(lines) + "\n", media_type=_CONTENT_TYPE)
