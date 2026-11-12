"""Application lifecycle hooks — background workers and periodic tasks.

Extracted from ``main.py``: the admission queue worker and the artifact
cleanup task are owned by the app lifecycle, registered here so the
factory stays readable.
"""

import asyncio
import socket
from contextlib import suppress

from fastapi import FastAPI

from soar_lab.application.use_cases.alert_admission import AlertAdmissionUseCase
from soar_lab.config.logging import get_logger
from soar_lab.infrastructure.cleanup_service import CleanupService
from soar_lab.infrastructure.clients import create_async_redis_client
from soar_lab.infrastructure.messaging.admission_worker import (
    AdmissionWorker,
    WorkerStats,
)
from soar_lab.infrastructure.messaging.redis_admission_store import RedisAdmissionStore
from soar_lab.infrastructure.messaging.redis_streams_queue import RedisStreamsQueue
from soar_lab.infrastructure.messaging.shuffle_forward import make_shuffle_forward
from soar_lab.infrastructure.messaging.worker_lease import WorkerLease
from soar_lab.infrastructure.monitoring.kpi_alerts import KPIAlertManager
from soar_lab.infrastructure.monitoring.stale_execution_gc import StaleExecutionGC

logger = get_logger(__name__)


def register_worker_lifecycle(app_instance: FastAPI, cp) -> None:
    """Start/stop the admission worker (PERF-001) with the app lifecycle.

    Builds the async Redis client, stream queue, admission store, use case
    and worker on startup; skips everything when ``ALERT_INGEST_ENABLED``
    is off or Redis is unreachable — the endpoint then returns 503.
    """

    @app_instance.on_event("startup")
    async def _start_admission_worker() -> None:
        enabled = str(cp.get("ALERT_INGEST_ENABLED", "true")).lower() not in (
            "0",
            "false",
            "off",
            "no",
        )
        if not enabled:
            logger.info("Alert admission disabled (ALERT_INGEST_ENABLED=false)")
            return
        try:
            client = await create_async_redis_client(cp)
            if client is None:
                logger.warning("Admission queue unavailable — POST /api/v1/alerts returns 503")
                return

            queue = RedisStreamsQueue(client)
            store = RedisAdmissionStore(client)
            app_instance.state.admission_service = AlertAdmissionUseCase(
                queue=queue,
                store=store,
                # CONFIG-001: WEBHOOK_PAYLOAD_MAX_SIZE now actually drives
                # the admission cap — no more decorative config.
                max_payload_bytes=int(cp.get("WEBHOOK_PAYLOAD_MAX_SIZE", "262144")),
                max_queue_depth=int(cp.get("ALERT_INGEST_MAX_DEPTH", "50000")),
            )
            stats = WorkerStats()
            app_instance.state.admission_worker_stats = stats
            forward = make_shuffle_forward(cp)
            app_instance.state.admission_forward = forward
            # R3 HA: unique consumer per replica (hostname) so N API
            # workers in one consumer group can't double-claim; the
            # Redis lease elects a single leader for recover/redrive.
            # WORKER-007: the lease TTL must exceed the renewal cadence
            # (recover_interval_s=60s) — a shorter TTL lets the key
            # expire mid-cycle, so every "renewal" was really a fresh
            # acquisition: leadership gaps plus meaningless fence churn.
            consumer_name = f"worker-{socket.gethostname()}"
            lease = WorkerLease(client, holder=consumer_name, ttl_ms=180_000)
            worker = AdmissionWorker(
                queue,
                store,
                forward=forward,
                consumer=consumer_name,
                max_attempts=int(cp.get("ALERT_INGEST_MAX_ATTEMPTS", "5")),
                concurrency=int(cp.get("ALERT_INGEST_CONCURRENCY", "4")),
                stats=stats,
                lease=lease,
                reconciler=app_instance.state.admission_service.reconcile,
            )
            stop = asyncio.Event()
            app_instance.state.admission_worker_stop = stop
            app_instance.state.admission_worker_task = asyncio.create_task(worker.run(stop))
            logger.info("Admission worker started (stream=%s)", queue.stream)
        except Exception:
            logger.exception("Failed to start admission worker")

    @app_instance.on_event("shutdown")
    async def _stop_admission_worker() -> None:
        stop = getattr(app_instance.state, "admission_worker_stop", None)
        task = getattr(app_instance.state, "admission_worker_task", None)
        if stop is not None:
            stop.set()
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=5)
            except (TimeoutError, asyncio.CancelledError):
                task.cancel()
        # Close the pooled Shuffle-forward session (BL-HTTP-003) and the
        # pooled HTTP sessions used by health checks — without this
        # the connection pools linger past app shutdown.
        forward = getattr(app_instance.state, "admission_forward", None)
        aclose = getattr(forward, "aclose", None)
        if aclose is not None:
            try:
                await aclose()
            except Exception:
                logger.warning("Failed to close Shuffle forward session", exc_info=True)
        health_checker = getattr(app_instance.state, "health_checker", None)
        http_client = getattr(health_checker, "http_client", None)
        if http_client is not None and hasattr(http_client, "close"):
            try:
                await http_client.close()
            except Exception:
                logger.warning("Failed to close health-check http client", exc_info=True)


def register_cleanup_task(app_instance: FastAPI, cp) -> None:
    """Periodic artifact retention (``CleanupService``) with the app lifecycle.

    ``cleanup_old_artifacts()`` existed but had no invoker — backups,
    results and logs grew unbounded. Runs once at startup, then every
    ``CLEANUP_INTERVAL_HOURS`` (default 24 h); disabled with
    ``CLEANUP_ENABLED=false``.
    """

    @app_instance.on_event("startup")
    async def _start_cleanup_task() -> None:
        if str(cp.get("CLEANUP_ENABLED", "true")).lower() in ("0", "false", "off", "no"):
            return
        try:

            path_service = getattr(app_instance.state, "path_service", None)
            if path_service is None:
                return
            service = CleanupService(path_service=path_service, config_provider=cp)
            interval_h = max(0.25, float(cp.get("CLEANUP_INTERVAL_HOURS", "24")))
            stop = asyncio.Event()
            app_instance.state.cleanup_task_stop = stop

            async def _loop() -> None:
                while not stop.is_set():
                    try:
                        counts = await asyncio.to_thread(service.cleanup_old_artifacts)
                        if any(counts.values()):
                            logger.info("Artifact cleanup removed: %s", counts)
                    except Exception:
                        logger.exception("Artifact cleanup pass failed")
                    with suppress(TimeoutError):
                        await asyncio.wait_for(stop.wait(), timeout=interval_h * 3600)

            app_instance.state.cleanup_task = asyncio.create_task(_loop())
            logger.info("Artifact cleanup task started (interval=%sh)", interval_h)
        except Exception:
            logger.exception("Failed to start artifact cleanup task")

    @app_instance.on_event("shutdown")
    async def _stop_cleanup_task() -> None:
        stop = getattr(app_instance.state, "cleanup_task_stop", None)
        task = getattr(app_instance.state, "cleanup_task", None)
        if stop is not None:
            stop.set()
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=5)
            except (TimeoutError, asyncio.CancelledError):
                task.cancel()
            except Exception:
                logger.warning("Failed to close pooled HTTP sessions", exc_info=True)


def register_kpi_alert_task(app_instance: FastAPI, cp) -> None:
    """O3: periodic KPI-threshold check routed to a real webhook.

    ``KPIAlertManager`` computed threshold violations but had no
    invoker — alerts only existed in code. With ``KPI_ALERT_WEBHOOK_URL``
    set, the app evaluates all thresholds every
    ``KPI_ALERT_INTERVAL_S`` (default 300 s) and POSTs violations to
    the configured channel (Slack/Teams/generic webhook).
    """

    @app_instance.on_event("startup")
    async def _start_kpi_alert_task() -> None:
        webhook_url = cp.get("KPI_ALERT_WEBHOOK_URL")
        if not webhook_url:
            logger.info("KPI alerting disabled (KPI_ALERT_WEBHOOK_URL unset)")
            return
        es = getattr(app_instance.state, "elasticsearch_client", None)
        if es is None:
            logger.warning("KPI alerting skipped — no Elasticsearch client")
            return
        manager = KPIAlertManager(es, webhook_url=str(webhook_url))
        interval_s = max(30.0, float(cp.get("KPI_ALERT_INTERVAL_S", "300")))
        stop = asyncio.Event()
        app_instance.state.kpi_alert_stop = stop

        async def _loop() -> None:
            while not stop.is_set():
                try:
                    await asyncio.to_thread(manager.check_all_thresholds)
                except Exception:
                    logger.exception("KPI alert check failed")
                with suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=interval_s)

        app_instance.state.kpi_alert_task = asyncio.create_task(_loop())
        logger.info("KPI alerting started (interval=%ss)", interval_s)

    @app_instance.on_event("shutdown")
    async def _stop_kpi_alert_task() -> None:
        stop = getattr(app_instance.state, "kpi_alert_stop", None)
        task = getattr(app_instance.state, "kpi_alert_task", None)
        if stop is not None:
            stop.set()
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=5)
            except (TimeoutError, asyncio.CancelledError):
                task.cancel()


def register_stale_exec_gc(app_instance: FastAPI, cp) -> None:
    """RES-01: periodic GC of zombie Shuffle ``EXECUTING`` executions.

    Runs ``StaleExecutionGC.collect_once()`` every
    ``SHUFFLE_STALE_GC_INTERVAL_S`` (default 300 s). Disabled with
    ``SHUFFLE_STALE_GC_ENABLED=false``; skipped when
    ``SHUFFLE_OPENSEARCH_URL`` is unset. Threshold:
    ``SHUFFLE_STALE_MINUTES`` (default 30 — nothing legitimate exceeds
    the workflow timeout).
    """

    @app_instance.on_event("startup")
    async def _start_stale_gc() -> None:
        if str(cp.get("SHUFFLE_STALE_GC_ENABLED", "true")).lower() in (
            "0",
            "false",
            "off",
            "no",
        ):
            return
        os_url = cp.get("SHUFFLE_OPENSEARCH_URL")
        if not os_url:
            logger.info("Stale-exec GC skipped (SHUFFLE_OPENSEARCH_URL unset)")
            return
        try:
            gc = StaleExecutionGC(
                os_url=str(os_url),
                backend_url=str(cp.get("shuffle_url", "https://shuffle-backend:5443")),
                api_key=str(cp.get("shuffle_api_key", "") or ""),
                stale_minutes=float(cp.get("SHUFFLE_STALE_MINUTES", "30")),
            )
            interval_s = max(60.0, float(cp.get("SHUFFLE_STALE_GC_INTERVAL_S", "300")))
            stop = asyncio.Event()
            app_instance.state.stale_gc_stop = stop
            app_instance.state.stale_gc = gc

            async def _loop() -> None:
                while not stop.is_set():
                    try:
                        await asyncio.to_thread(gc.collect_once)
                    except Exception:
                        logger.exception("Stale-exec GC pass failed")
                    # DT-02: fill node_timings/execution_id on soar-metrics docs
                    # the workflow writes before Shuffle exposes results.
                    if str(cp.get("TIMINGS_BACKFILL_ENABLED", "true")).lower() not in (
                        "0",
                        "false",
                        "off",
                        "no",
                    ):
                        try:
                            proc = await asyncio.create_subprocess_exec(
                                "python3",
                                "/app/scripts/maintenance/backfill_node_timings.py",
                                "--size",
                                "100",
                                stdout=asyncio.subprocess.DEVNULL,
                                stderr=asyncio.subprocess.DEVNULL,
                            )
                            await asyncio.wait_for(proc.wait(), timeout=120)
                        except Exception:
                            logger.exception("node_timings backfill pass failed")
                    with suppress(TimeoutError):
                        await asyncio.wait_for(stop.wait(), timeout=interval_s)

            app_instance.state.stale_gc_task = asyncio.create_task(_loop())
            logger.info("Stale-exec GC started (interval=%ss)", interval_s)
        except Exception:
            logger.exception("Failed to start stale-exec GC")

    @app_instance.on_event("shutdown")
    async def _stop_stale_gc() -> None:
        stop = getattr(app_instance.state, "stale_gc_stop", None)
        task = getattr(app_instance.state, "stale_gc_task", None)
        if stop is not None:
            stop.set()
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=5)
            except (TimeoutError, asyncio.CancelledError):
                task.cancel()
