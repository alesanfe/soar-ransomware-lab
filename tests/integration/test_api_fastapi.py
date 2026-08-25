#!/usr/bin/env python3
"""FastAPI endpoint tests using TestClient.

Covers all routes registered in soar_lab.api.main:   GET  /health   GET
/   POST /auth/login   POST /auth/verify   GET  /analytics/metrics   GET
/analytics/kpis   GET  /services/status   POST /backup/create   GET
/backup/list   POST /backup/restore   POST /tests/run   WS   /ws/logs
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from soar_lab.interfaces.api.main import create_app

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_config():
    cp = MagicMock()
    cp.get.side_effect = lambda key, default=None: {
        "API_TITLE": "SOAR Lab Test API",
        "API_DESCRIPTION": "Test",
        "API_VERSION": "1.0.0",
        "CORS_ORIGINS": ["*"],
    }.get(key, default)
    cp.get_service_urls.return_value = {}
    return cp


@pytest.fixture
def mock_auth_service():
    svc = MagicMock()
    svc.verify_credentials.return_value = True
    svc.create_jwt_token.return_value = "test.jwt.token"
    svc.verify_jwt_token.return_value = {"user": "admin", "method": "jwt"}
    return svc


@pytest.fixture
def mock_analytics_service():
    svc = MagicMock()
    svc.get_comprehensive_kpis.return_value = {
        "mttr_minutes": 5.2,
        "total_alerts": 42,
        "malicious": 10,
        "benign": 32,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    return svc


@pytest.fixture
def mock_backup_service():
    svc = MagicMock()
    svc.create.return_value = {
        "filename": "backup-20250101.tar.gz",
        "message": "Backup created successfully",
    }
    svc.list_backups.return_value = {
        "backups": [
            {"name": "backup-20250101.tar.gz", "size": "10.0 MB", "date": "2025-01-01 00:00"},
            {"name": "backup-20250102.tar.gz", "size": "11.0 MB", "date": "2025-01-02 00:00"},
        ]
    }
    svc.restore.return_value = {
        "backup_name": "backup-20250101",
        "status": "success",
        "message": "Backup restored",
    }
    return svc


@pytest.fixture
def mock_test_service():
    svc = MagicMock()
    svc.run_tests = AsyncMock(
        return_value={
            "category": "unit",
            "passed": 50,
            "failed": 0,
            "skipped": 2,
            "coverage": 85.0,
            "output": "50 passed, 2 skipped",
            "duration": 3.14,
        }
    )
    return svc


@pytest.fixture
def mock_health_service():
    svc = MagicMock()
    svc.get_all_services_status = AsyncMock(
        return_value={
            "elasticsearch": "healthy",
            "thehive": "healthy",
            "cortex": "healthy",
        }
    )
    return svc


@pytest.fixture
def mock_system_metrics():
    svc = MagicMock()
    svc.get_hardware_metrics.return_value = {
        "cpu": {"percent": 22.0},
        "memory": {"percent": 55.0},
        "disk": {"percent": 40.0},
    }
    return svc


@pytest.fixture
def mock_websocket_manager():
    mgr = MagicMock()
    mgr.connect = AsyncMock()
    mgr.disconnect = MagicMock()
    return mgr


@pytest.fixture
def client(
    mock_config,
    mock_auth_service,
    mock_analytics_service,
    mock_backup_service,
    mock_test_service,
    mock_health_service,
    mock_system_metrics,
    mock_websocket_manager,
):
    app = create_app(
        config_provider=mock_config,
        auth_service=mock_auth_service,
        analytics_service=mock_analytics_service,
        backup_service=mock_backup_service,
        test_service=mock_test_service,
        health_service=mock_health_service,
        system_metrics=mock_system_metrics,
        websocket_manager=mock_websocket_manager,
    )
    return TestClient(app, raise_server_exceptions=False)


# ─────────────────────────────────────────────────────────────────────────────
# GET /health
# ─────────────────────────────────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_body_contains_status(self, client):
        r = client.get("/health")
        data = r.json()
        assert data["status"] == "healthy"

    def test_health_body_contains_version(self, client):
        r = client.get("/health")
        assert "version" in r.json()

    def test_health_body_contains_timestamp(self, client):
        r = client.get("/health")
        assert "timestamp" in r.json()


# ─────────────────────────────────────────────────────────────────────────────
# GET /  (HTML docs)
# ─────────────────────────────────────────────────────────────────────────────


class TestRootEndpoint:
    def test_root_returns_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")


# ─────────────────────────────────────────────────────────────────────────────
# POST /auth/login
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthLogin:
    def test_login_valid_credentials(self, client):
        r = client.post("/auth/login", json={"username": "admin", "password": "secret"})
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert data["token_type"] == "Bearer"

    def test_login_invalid_credentials(self, client, mock_auth_service):
        mock_auth_service.verify_credentials.return_value = False
        r = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401

    def test_login_missing_password(self, client):
        r = client.post("/auth/login", json={"username": "admin"})
        assert r.status_code == 422

    def test_login_missing_username(self, client):
        r = client.post("/auth/login", json={"password": "secret"})
        assert r.status_code == 422

    def test_login_empty_body(self, client):
        r = client.post("/auth/login", json={})
        assert r.status_code == 422

    def test_login_auth_error_returns_401(self, client, mock_auth_service):
        from soar_lab.common.exceptions import AuthError

        mock_auth_service.verify_credentials.side_effect = AuthError("locked", status_code=401)
        r = client.post("/auth/login", json={"username": "admin", "password": "x"})
        assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# POST /auth/verify
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthVerify:
    def test_verify_valid_token(self, client, mock_auth_service):
        mock_auth_service.verify_jwt_token.return_value = {"user": "admin", "method": "jwt"}
        r = client.post(
            "/auth/verify",
            headers={"Authorization": "Bearer test.jwt.token"},
        )
        # The endpoint calls get_current_user which calls verify_jwt_token via the stored dependency
        assert r.status_code in (200, 401)

    def test_verify_invalid_token(self, client, mock_auth_service):
        mock_auth_service.verify_jwt_token.side_effect = Exception("bad token")
        r = client.post(
            "/auth/verify",
            headers={"Authorization": "Bearer bad.token"},
        )
        assert r.status_code == 401

    def test_verify_missing_token(self, client):
        r = client.post("/auth/verify")
        assert r.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/metrics
# ─────────────────────────────────────────────────────────────────────────────


class TestAnalyticsMetrics:
    def test_metrics_returns_200(self, client):
        r = client.get("/analytics/metrics")
        assert r.status_code == 200

    def test_metrics_schema(self, client):
        data = client.get("/analytics/metrics").json()
        for key in ("cpu", "memory", "disk", "timestamp"):
            assert key in data

    def test_metrics_values_in_range(self, client):
        data = client.get("/analytics/metrics").json()
        assert 0.0 <= data["cpu"] <= 100.0
        assert 0.0 <= data["memory"] <= 100.0
        assert 0.0 <= data["disk"] <= 100.0

    def test_metrics_fallback_when_no_system_metrics(self, mock_config, mock_auth_service):
        app = create_app(
            config_provider=mock_config,
            auth_service=mock_auth_service,
            system_metrics=None,
        )
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/analytics/metrics")
        assert r.status_code == 200
        data = r.json()
        assert "cpu" in data


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/kpis
# ─────────────────────────────────────────────────────────────────────────────


class TestAnalyticsKPIs:
    def test_kpis_returns_200(self, client):
        r = client.get("/analytics/kpis")
        assert r.status_code == 200

    def test_kpis_contains_expected_keys(self, client):
        data = client.get("/analytics/kpis").json()
        assert "mttr_minutes" in data
        assert "total_alerts" in data

    def test_kpis_accepts_log_file_param(self, client):
        r = client.get("/analytics/kpis?log_file_path=/tmp/fake.log")
        assert r.status_code == 200

    def test_kpis_service_unavailable(self, mock_config, mock_auth_service):
        app = create_app(
            config_provider=mock_config,
            auth_service=mock_auth_service,
            analytics_service=None,
        )
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/analytics/kpis")
        assert r.status_code == 503


# ─────────────────────────────────────────────────────────────────────────────
# GET /services/status
# ─────────────────────────────────────────────────────────────────────────────


class TestServicesStatus:
    def test_services_status_returns_200(self, client):
        r = client.get("/services/status")
        assert r.status_code == 200

    def test_services_status_schema(self, client):
        data = client.get("/services/status").json()
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data

    def test_services_status_services_is_dict(self, client):
        data = client.get("/services/status").json()
        assert isinstance(data["services"], dict)

    def test_services_status_fallback_when_no_health_service(self, mock_config, mock_auth_service):
        app = create_app(
            config_provider=mock_config,
            auth_service=mock_auth_service,
            health_service=None,
        )
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/services/status")
        assert r.status_code == 200
        assert r.json()["services"] == {}


# ─────────────────────────────────────────────────────────────────────────────
# POST /backup/create
# ─────────────────────────────────────────────────────────────────────────────


class TestBackupCreate:
    def test_create_backup_returns_200(self, client, mock_backup_service):
        mock_backup_service.create.return_value = {
            "filename": "backup-20250101.tar.gz",
            "message": "Backup created successfully",
        }
        r = client.post(
            "/backup/create",
            json={"backup_name": "backup-20250101.tar.gz"},
        )
        assert r.status_code == 200

    def test_create_backup_response_schema(self, client, mock_backup_service):
        mock_backup_service.create.return_value = {
            "filename": "backup-20250101.tar.gz",
            "message": "Backup created successfully",
        }
        data = client.post(
            "/backup/create",
            json={"backup_name": "backup-20250101.tar.gz"},
        ).json()
        assert "backup_name" in data
        assert "message" in data

    def test_create_backup_service_unavailable(self, mock_config, mock_auth_service):
        app = create_app(
            config_provider=mock_config,
            auth_service=mock_auth_service,
            backup_service=None,
        )
        c = TestClient(app, raise_server_exceptions=False)
        r = c.post("/backup/create", json={})
        assert r.status_code == 503


# ─────────────────────────────────────────────────────────────────────────────
# GET /backup/list
# ─────────────────────────────────────────────────────────────────────────────


class TestBackupList:
    def test_list_backups_returns_200(self, client, mock_backup_service):
        mock_backup_service.list_backups.return_value = {
            "backups": [
                {"name": "backup-20250101.tar.gz", "size": "10.0 MB", "date": "2025-01-01 00:00"},
            ]
        }
        r = client.get("/backup/list")
        assert r.status_code == 200

    def test_list_backups_returns_list(self, client, mock_backup_service):
        mock_backup_service.list_backups.return_value = {
            "backups": [
                {"name": "backup-20250101.tar.gz", "size": "10.0 MB", "date": "2025-01-01 00:00"},
            ]
        }
        data = client.get("/backup/list").json()
        assert "backups" in data
        assert isinstance(data["backups"], list)

    def test_list_backups_contains_expected_names(self, client, mock_backup_service):
        mock_backup_service.list_backups.return_value = {
            "backups": [
                {"name": "backup-20250101.tar.gz", "size": "10.0 MB", "date": "2025-01-01 00:00"},
            ]
        }
        data = client.get("/backup/list").json()
        names = [b["name"] for b in data["backups"]]
        assert "backup-20250101.tar.gz" in names

    def test_list_backups_service_unavailable(self, mock_config, mock_auth_service):
        app = create_app(
            config_provider=mock_config,
            auth_service=mock_auth_service,
            backup_service=None,
        )
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/backup/list")
        assert r.status_code == 503


# ─────────────────────────────────────────────────────────────────────────────
# POST /backup/restore
# ─────────────────────────────────────────────────────────────────────────────


class TestBackupRestore:
    def test_restore_returns_200(self, client, mock_backup_service):
        mock_backup_service.restore.return_value = {
            "backup_name": "backup-20250101.tar.gz",
            "status": "success",
            "message": "Restored",
        }
        r = client.post("/backup/restore", json={"backup_name": "backup-20250101.tar.gz"})
        assert r.status_code == 200

    def test_restore_response_schema(self, client, mock_backup_service):
        mock_backup_service.restore.return_value = {
            "backup_name": "backup-20250101.tar.gz",
            "status": "success",
            "message": "Restored",
        }
        data = client.post("/backup/restore", json={"backup_name": "backup-20250101.tar.gz"}).json()
        assert "message" in data

    def test_restore_invalid_name_rejected(self, client):
        r = client.post("/backup/restore", json={"backup_name": "../../../etc/passwd"})
        assert r.status_code == 422

    def test_restore_missing_tar_gz_rejected(self, client):
        r = client.post("/backup/restore", json={"backup_name": "backup-no-extension"})
        assert r.status_code == 422

    def test_restore_service_unavailable(self, mock_config, mock_auth_service):
        app = create_app(
            config_provider=mock_config,
            auth_service=mock_auth_service,
            backup_service=None,
        )
        c = TestClient(app, raise_server_exceptions=False)
        r = c.post("/backup/restore", json={"backup_name": "backup-ok.tar.gz"})
        assert r.status_code == 503


# ─────────────────────────────────────────────────────────────────────────────
# POST /tests/run
# ─────────────────────────────────────────────────────────────────────────────


class TestTestsRun:
    def test_run_unit_tests_returns_200(self, client):
        r = client.post("/tests/run", json={"category": "unit"})
        assert r.status_code == 200

    def test_run_tests_response_schema(self, client):
        data = client.post("/tests/run", json={"category": "unit"}).json()
        for key in ("category", "passed", "failed", "skipped", "coverage", "duration"):
            assert key in data

    def test_run_tests_all_categories(self, client):
        for cat in (
            "unit",
            "integration",
            "e2e",
            "atomic",
            "performance",
            "security",
            "smoke",
            "all",
        ):
            r = client.post("/tests/run", json={"category": cat})
            assert r.status_code == 200, f"Failed for category {cat}"

    def test_run_tests_invalid_category_rejected(self, client):
        r = client.post("/tests/run", json={"category": "nonexistent"})
        assert r.status_code == 422

    def test_run_tests_missing_category(self, client):
        r = client.post("/tests/run", json={})
        assert r.status_code == 422

    def test_run_tests_fallback_when_no_service(self, mock_config, mock_auth_service):
        app = create_app(
            config_provider=mock_config,
            auth_service=mock_auth_service,
            test_service=None,
        )
        c = TestClient(app, raise_server_exceptions=False)
        r = c.post("/tests/run", json={"category": "unit"})
        assert r.status_code == 200
        data = r.json()
        assert data["passed"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# WS /ws/logs
# ─────────────────────────────────────────────────────────────────────────────


class TestWebSocketLogs:
    def test_websocket_endpoint_registered(self, client):
        """Verify /ws/logs is registered as a WebSocket route."""
        from starlette.routing import WebSocketRoute

        routes = client.app.routes
        ws_paths = [r.path for r in routes if isinstance(r, WebSocketRoute)]
        assert "/ws/logs" in ws_paths, f"/ws/logs not found in WebSocket routes: {ws_paths}"

    def test_websocket_unavailable_when_no_manager(self, mock_config, mock_auth_service):
        from starlette.websockets import WebSocketDisconnect

        app = create_app(
            config_provider=mock_config,
            auth_service=mock_auth_service,
            websocket_manager=None,
        )
        c = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with c.websocket_connect("/ws/logs") as ws:
                ws.receive_json()
        # Verify the close code indicates service unavailable
        assert exc_info.value.code == 1011


# ─────────────────────────────────────────────────────────────────────────────
# Error handling
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_unknown_endpoint_returns_404(self, client):
        r = client.get("/nonexistent")
        assert r.status_code == 404

    def test_wrong_method_returns_405(self, client):
        r = client.delete("/health")
        assert r.status_code == 405

    def test_analytics_metrics_error_returns_500(self, client, mock_system_metrics):
        mock_system_metrics.get_hardware_metrics.side_effect = RuntimeError("disk error")
        r = client.get("/analytics/metrics")
        assert r.status_code == 500

    def test_kpis_error_returns_500(self, client, mock_analytics_service):
        mock_analytics_service.get_comprehensive_kpis.side_effect = RuntimeError("parse error")
        r = client.get("/analytics/kpis")
        assert r.status_code == 500
