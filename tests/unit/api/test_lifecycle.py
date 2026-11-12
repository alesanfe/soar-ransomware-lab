"""Tests for app lifecycle hooks: admission worker, cleanup, KPI, stale-GC."""

import asyncio
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import soar_lab.interfaces.api.lifecycle as lc


def _cp(values=None):
    values = values or {}
    cp = Mock()
    cp.get = lambda key, default=None: values.get(key, default)
    return cp


def _run_app(app):
    """Enter TestClient context: runs startup hooks, exits → shutdown."""
    with TestClient(app):
        pass


class TestWorkerLifecycle:
    def _register(self, cp_values):
        app = FastAPI()
        lc.register_worker_lifecycle(app, _cp(cp_values))
        return app

    def test_disabled_skips_everything(self, caplog):
        with caplog.at_level(logging.INFO):
            _run_app(self._register({"ALERT_INGEST_ENABLED": "false"}))
        assert "disabled" in caplog.text
        app = self._register({"ALERT_INGEST_ENABLED": "false"})
        assert not hasattr(app.state, "admission_worker_task")

    def test_redis_unavailable_warns_and_returns(self, caplog):
        with patch.object(lc, "create_async_redis_client", new=AsyncMock(return_value=None)):
            with caplog.at_level(logging.WARNING):
                _run_app(self._register({}))
        assert "queue unavailable" in caplog.text

    def test_full_startup_and_graceful_shutdown(self):
        fake_client = Mock()
        forward = Mock()
        forward.aclose = AsyncMock()
        closer = Mock()
        closer.close = AsyncMock()
        app = self._register({})
        app.state.health_checker = Mock(http_client=closer)

        async def run_forever(stop):
            await stop.wait()

        worker = Mock()
        worker.run = run_forever

        with (
            patch.object(lc, "create_async_redis_client", new=AsyncMock(return_value=fake_client)),
            patch.object(lc, "RedisStreamsQueue", Mock()),
            patch.object(lc, "RedisAdmissionStore", Mock()),
            patch.object(lc, "AlertAdmissionUseCase", Mock()),
            patch.object(lc, "WorkerLease", Mock()),
            patch.object(lc, "make_shuffle_forward", Mock(return_value=forward)),
            patch.object(lc, "AdmissionWorker", Mock(return_value=worker)),
        ):
            _run_app(app)

        assert app.state.admission_worker_stop.is_set()
        forward.aclose.assert_awaited_once()
        closer.close.assert_awaited_once()

    def test_startup_exception_is_logged_not_raised(self, caplog):
        with patch.object(
            lc, "create_async_redis_client", new=AsyncMock(side_effect=RuntimeError("boom"))
        ):
            with caplog.at_level(logging.ERROR):
                _run_app(self._register({}))  # must not raise
        assert "Failed to start admission worker" in caplog.text

    def test_shutdown_tolerates_missing_state_and_timeouts(self):
        # No worker started → shutdown handler must be a no-op.
        _run_app(self._register({"ALERT_INGEST_ENABLED": "false"}))

        # Worker that never finishes → wait_for timeout → cancel path.
        app = self._register({})
        closer = Mock()
        closer.close = AsyncMock(side_effect=RuntimeError("close fail"))
        app.state.health_checker = Mock(http_client=closer)

        async def run_forever(_stop):
            await asyncio.sleep(3600)

        worker = Mock()
        worker.run = run_forever
        forward = Mock()
        forward.aclose = AsyncMock(side_effect=RuntimeError("aclose fail"))

        with (
            patch.object(lc, "create_async_redis_client", new=AsyncMock(return_value=Mock())),
            patch.object(lc, "RedisStreamsQueue", Mock()),
            patch.object(lc, "RedisAdmissionStore", Mock()),
            patch.object(lc, "AlertAdmissionUseCase", Mock()),
            patch.object(lc, "WorkerLease", Mock()),
            patch.object(lc, "make_shuffle_forward", Mock(return_value=forward)),
            patch.object(lc, "AdmissionWorker", Mock(return_value=worker)),
        ):
            _run_app(app)  # must not raise despite close/aclose failures


class TestCleanupTask:
    def test_disabled(self):
        app = FastAPI()
        lc.register_cleanup_task(app, _cp({"CLEANUP_ENABLED": "false"}))
        _run_app(app)
        assert not hasattr(app.state, "cleanup_task")

    def test_no_path_service_skips(self):
        app = FastAPI()
        lc.register_cleanup_task(app, _cp({}))
        _run_app(app)
        assert not hasattr(app.state, "cleanup_task")

    def test_enabled_starts_and_stops(self):
        app = FastAPI()
        app.state.path_service = Mock()
        lc.register_cleanup_task(app, _cp({"CLEANUP_INTERVAL_HOURS": "1"}))
        with patch.object(lc, "CleanupService") as svc_cls:
            svc_cls.return_value.cleanup_old_artifacts = Mock(return_value={"backups": 0})
            _run_app(app)
        assert app.state.cleanup_task_stop.is_set()

    def test_cleanup_failure_logged(self, caplog):
        app = FastAPI()
        app.state.path_service = Mock()
        lc.register_cleanup_task(app, _cp({}))
        with patch.object(lc, "CleanupService", side_effect=RuntimeError("init fail")):
            with caplog.at_level(logging.ERROR):
                _run_app(app)
        assert "Failed to start artifact cleanup task" in caplog.text


class TestKpiAlertTask:
    def test_no_webhook_disables(self):
        app = FastAPI()
        lc.register_kpi_alert_task(app, _cp({}))
        _run_app(app)
        assert not hasattr(app.state, "kpi_alert_task")

    def test_no_es_client_warns(self, caplog):
        app = FastAPI()
        lc.register_kpi_alert_task(app, _cp({"KPI_ALERT_WEBHOOK_URL": "http://hook"}))
        with caplog.at_level(logging.WARNING):
            _run_app(app)
        assert "no Elasticsearch client" in caplog.text

    def test_full_start_and_stop(self):
        app = FastAPI()
        app.state.elasticsearch_client = Mock()
        lc.register_kpi_alert_task(
            app, _cp({"KPI_ALERT_WEBHOOK_URL": "http://hook", "KPI_ALERT_INTERVAL_S": "30"})
        )
        with patch.object(lc, "KPIAlertManager") as mgr:
            mgr.return_value.check_all_thresholds = Mock()
            _run_app(app)
        assert app.state.kpi_alert_stop.is_set()


class TestStaleExecGc:
    def test_disabled(self):
        app = FastAPI()
        lc.register_stale_exec_gc(app, _cp({"SHUFFLE_STALE_GC_ENABLED": "false"}))
        _run_app(app)
        assert not hasattr(app.state, "stale_gc_task")

    def test_no_opensearch_url_skips(self):
        app = FastAPI()
        lc.register_stale_exec_gc(app, _cp({}))
        _run_app(app)
        assert not hasattr(app.state, "stale_gc_task")

    def test_full_start_and_stop_no_backfill(self):
        app = FastAPI()
        lc.register_stale_exec_gc(
            app,
            _cp(
                {
                    "SHUFFLE_OPENSEARCH_URL": "https://os:9200",
                    "TIMINGS_BACKFILL_ENABLED": "false",
                }
            ),
        )
        with patch.object(lc, "StaleExecutionGC") as gc_cls:
            gc_cls.return_value.collect_once = Mock()
            _run_app(app)
        assert app.state.stale_gc_stop.is_set()

    def test_gc_exception_logged(self, caplog):
        app = FastAPI()
        lc.register_stale_exec_gc(app, _cp({"SHUFFLE_OPENSEARCH_URL": "https://os:9200"}))
        with patch.object(lc, "StaleExecutionGC", side_effect=RuntimeError("init fail")):
            with caplog.at_level(logging.ERROR):
                _run_app(app)
        assert "Failed to start stale-exec GC" in caplog.text
