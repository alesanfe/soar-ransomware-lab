#!/usr/bin/env python3
"""Unit tests for interfaces/api/main.py create_app function.

Tests the FastAPI app factory with mocked dependencies, covering route
registration, error handling, and dependency injection.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from soar_lab.interfaces.api.main import create_app

__all__ = [
    "TestCreateAppInitialization",
    "TestHealthEndpoint",
    "TestAuthEndpoints",
    "TestMetricsEndpoint",
    "TestKpisEndpoint",
    "TestBackupEndpoints",
    "TestTestsEndpoint",
    "TestServicesStatusEndpoint",
    "TestSoarEndpoints",
    "TestApiInitModule",
]


def _make_mock_config():
    """Create a mock config provider with standard test values."""
    cp = Mock()
    cp.get.side_effect = lambda key, default=None: {
        "API_TITLE": "SOAR Test API",
        "API_DESCRIPTION": "Test API",
        "API_VERSION": "1.0.0",
        "CORS_ORIGINS": ["*"],
        "DOCS_DIR": "/nonexistent",
    }.get(key, default)
    cp.get_service_urls.return_value = {}
    return cp


def _make_mock_auth_service():
    """Create a mock auth service."""
    auth = Mock()
    auth.verify_credentials.return_value = True
    auth.create_jwt_token.return_value = "test-jwt-token"
    auth.verify_jwt_token.return_value = {"user": "admin", "role": "admin"}
    return auth


def _create_test_app(**overrides):
    """Create a FastAPI app with all mocked dependencies."""
    cp = _make_mock_config()
    auth = _make_mock_auth_service()

    defaults = {
        "config_provider": cp,
        "auth_service": auth,
        "system_metrics": Mock(),
        "health_service": Mock(),
        "analytics_service": Mock(),
        "backup_service": Mock(),
        "test_service": Mock(),
        "storage": Mock(),
        "path_service": Mock(),
        "log_reader": Mock(),
    }
    defaults.update(overrides)
    return create_app(**defaults)


@pytest.fixture()
def app():
    """Create a test FastAPI app with mocked dependencies."""
    return _create_test_app()


@pytest.fixture()
def client(app):
    """TestClient for the test app."""
    return TestClient(app)


class TestCreateAppInitialization:
    """Tests for create_app initialization."""

    def test_create_app_requires_config_provider(self):
        """Test that create_app raises ValueError when config_provider is None."""
        with pytest.raises(ValueError, match="config_provider is required"):
            create_app(config_provider=None, auth_service=_make_mock_auth_service())

    def test_create_app_requires_auth_service(self):
        """Test that create_app raises ValueError when auth_service is None."""
        with pytest.raises(ValueError, match="auth_service is required"):
            create_app(config_provider=_make_mock_config(), auth_service=None)

    def test_create_app_returns_fastapi(self, app):
        """Test that create_app returns a FastAPI instance."""
        assert isinstance(app, FastAPI)

    def test_create_app_stores_state(self, app):
        """Test that create_app stores dependencies in app.state."""
        assert app.state.config_provider is not None
        assert app.state.auth_service is not None
        assert app.state.system_metrics is not None

    def test_create_app_sets_get_current_user(self, app):
        """Test that create_app sets get_current_user in state."""
        assert hasattr(app.state, "get_current_user")
        assert callable(app.state.get_current_user)


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_returns_200(self, client):
        """Test /health returns 200 with status healthy."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data


class TestAuthEndpoints:
    """Test auth endpoints."""

    def test_login_success(self, client, app):
        """Test /auth/login with valid credentials."""
        app.state.auth_service.verify_credentials.return_value = True
        app.state.auth_service.create_jwt_token.return_value = "jwt-token-123"

        resp = client.post("/auth/login", json={"username": "admin", "password": "secret"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["token"] == "jwt-token-123"
        assert data["message"] == "Login successful"

    def test_login_invalid_credentials(self, client, app):
        """Test /auth/login with invalid credentials returns 401."""
        app.state.auth_service.verify_credentials.return_value = False

        resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_auth_error(self, client, app):
        """Test /auth/login returns 401 on AuthError."""
        from soar_lab.common.exceptions import AuthError

        app.state.auth_service.verify_credentials.side_effect = AuthError(
            "Invalid", status_code=401
        )

        resp = client.post("/auth/login", json={"username": "admin", "password": "secret"})
        assert resp.status_code == 401

    def test_verify_auth_success(self, client, app):
        """Test /auth/verify with valid token."""
        app.state.auth_service.verify_jwt_token.return_value = {"user": "admin"}

        resp = client.post(
            "/auth/verify",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True

    def test_verify_auth_invalid_token(self, client, app):
        """Test /auth/verify with invalid token returns 401."""
        app.state.auth_service.verify_jwt_token.side_effect = Exception("invalid")

        resp = client.post(
            "/auth/verify",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert resp.status_code == 401


class TestMetricsEndpoint:
    """Test the /analytics/metrics endpoint."""

    def test_metrics_with_system_metrics(self, client, app):
        """Test /analytics/metrics returns real metrics."""
        app.state.system_metrics.get_hardware_metrics.return_value = {
            "cpu": {"percent": 45.0},
            "memory": {"percent": 60.0},
            "disk": {"percent": 75.0},
        }

        resp = client.get("/analytics/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cpu"] == 45.0
        assert data["memory"] == 60.0
        assert data["disk"] == 75.0

    def test_metrics_without_system_metrics(self, client, app):
        """Test /analytics/metrics returns mock values when system_metrics is None."""
        app.state.system_metrics = None

        resp = client.get("/analytics/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cpu"] == 50.0
        assert data["memory"] == 60.0
        assert data["disk"] == 70.0

    def test_metrics_exception_returns_500(self, client, app):
        """Test /analytics/metrics returns 500 on error."""
        app.state.system_metrics.get_hardware_metrics.side_effect = RuntimeError("fail")

        resp = client.get("/analytics/metrics")
        assert resp.status_code == 500


class TestKpisEndpoint:
    """Test the /analytics/kpis endpoint."""

    def test_kpis_success(self, client, app):
        """Test /analytics/kpis returns KPI data."""
        app.state.analytics_service.get_comprehensive_kpis.return_value = {"mttr": 100}

        resp = client.get("/analytics/kpis")
        assert resp.status_code == 200
        assert resp.json()["mttr"] == 100

    def test_kpis_exception_returns_500(self, client, app):
        """Test /analytics/kpis returns 500 on error."""
        app.state.analytics_service.get_comprehensive_kpis.side_effect = RuntimeError("fail")

        resp = client.get("/analytics/kpis")
        assert resp.status_code == 500


class TestBackupEndpoints:
    """Test backup endpoints."""

    def test_create_backup_success(self, client, app):
        """Test /backup/create returns success."""
        app.state.backup_service.create.return_value = {
            "filename": "backup-001.tar.gz",
            "status": "success",
            "message": "Created",
        }

        resp = client.post("/backup/create", json={"backup_name": "backup-001.tar.gz"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["backup_name"] == "backup-001.tar.gz"
        assert data["status"] == "success"

    def test_create_backup_exception_returns_500(self, client, app):
        """Test /backup/create returns 500 on error."""
        app.state.backup_service.create.side_effect = RuntimeError("fail")

        resp = client.post("/backup/create", json={"backup_name": "backup.tar.gz"})
        assert resp.status_code == 500

    def test_list_backups_success(self, client, app):
        """Test /backup/list returns backup list."""
        app.state.backup_service.list_backups.return_value = {"backups": []}

        resp = client.get("/backup/list")
        assert resp.status_code == 200
        assert resp.json()["backups"] == []

    def test_list_backups_exception_returns_500(self, client, app):
        """Test /backup/list returns 500 on error."""
        app.state.backup_service.list_backups.side_effect = RuntimeError("fail")

        resp = client.get("/backup/list")
        assert resp.status_code == 500

    def test_restore_backup_success(self, client, app):
        """Test /backup/restore returns success."""
        app.state.backup_service.restore.return_value = {
            "backup_name": "backup-001.tar.gz",
            "status": "success",
            "message": "Restored",
        }

        resp = client.post("/backup/restore", json={"backup_name": "backup-001.tar.gz"})
        assert resp.status_code == 200
        assert resp.json()["backup_name"] == "backup-001.tar.gz"

    def test_restore_backup_exception_returns_500(self, client, app):
        """Test /backup/restore returns 500 on error."""
        app.state.backup_service.restore.side_effect = RuntimeError("fail")

        resp = client.post("/backup/restore", json={"backup_name": "backup.tar.gz"})
        assert resp.status_code == 500


class TestTestsEndpoint:
    """Test the /tests/run endpoint."""

    def test_run_tests_success(self, client, app):
        """Test /tests/run with test service available."""
        app.state.test_service.run_tests = AsyncMock(
            return_value={
                "category": "unit",
                "passed": 10,
                "failed": 0,
                "skipped": 1,
                "coverage": 85.5,
                "output": "All passed",
                "duration": 1.5,
            }
        )

        resp = client.post("/tests/run", json={"category": "unit"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] == 10
        assert data["failed"] == 0
        assert data["coverage"] == 85.5

    def test_run_tests_no_service(self, client, app):
        """Test /tests/run returns mock data when test service is None."""
        app.state.test_service = None

        resp = client.post("/tests/run", json={"category": "unit"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] == 0
        assert "not available" in data["output"]

    def test_run_tests_exception_returns_500(self, client, app):
        """Test /tests/run returns 500 on error."""
        app.state.test_service.run_tests = AsyncMock(side_effect=RuntimeError("fail"))

        resp = client.post("/tests/run", json={"category": "unit"})
        assert resp.status_code == 500


class TestServicesStatusEndpoint:
    """Test the /services/status endpoint."""

    def test_services_status_with_health(self, client, app):
        """Test /services/status with health service and config provider."""
        app.state.health_service.get_all_services_status = AsyncMock(
            return_value={
                "thehive": {"reachable": True},
            }
        )

        resp = client.get("/services/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "services" in data

    def test_services_status_without_health(self, client, app):
        """Test /services/status returns empty services without health service."""
        app.state.health_service = None

        resp = client.get("/services/status")
        assert resp.status_code == 200
        assert resp.json()["services"] == {}

    def test_services_status_exception_returns_500(self, client, app):
        """Test /services/status returns 500 on error."""
        app.state.health_service.get_all_services_status = AsyncMock(
            side_effect=RuntimeError("fail")
        )

        resp = client.get("/services/status")
        assert resp.status_code == 500


class TestSoarEndpoints:
    """Test SOAR integration endpoints in main.py."""

    def test_thehive_cases_503_when_no_client(self):
        """Test 503 when TheHive client is not available."""
        app = _create_test_app(thehive_client=None)
        client = TestClient(app)
        resp = client.get("/soar/thehive/cases")
        assert resp.status_code == 503

    def test_thehive_cases_success(self):
        """Test TheHive cases endpoint with mock client."""
        mock_thehive = Mock()
        mock_thehive.search_cases.return_value = [{"id": "case1"}]
        app = _create_test_app(thehive_client=mock_thehive)
        client = TestClient(app)
        resp = client.get("/soar/thehive/cases")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_root_endpoint(self, client, app):
        """Test root endpoint returns HTML fallback when storage has no docs."""
        app.state.storage.read_file.return_value = None

        resp = client.get("/")
        assert resp.status_code == 200

    def test_root_endpoint_with_storage(self, client, app):
        """Test root endpoint uses storage when available."""
        app.state.storage.read_file.side_effect = lambda path: (
            "<html>Docs</html>" if path == "api-docs.html" else None
        )

        resp = client.get("/")
        assert resp.status_code == 200
        assert "Docs" in resp.text


class TestApiInitModule:
    """Test the api __init__.py module behavior."""

    def test_app_is_none_when_skip_eager_init(self):
        """Test that app is None when SOAR_SKIP_EAGER_INIT is set."""
        # The conftest sets SOAR_SKIP_EAGER_INIT=1, so app should be None
        import soar_lab.interfaces.api as api_module

        assert api_module.app is None

    def test_create_app_exported(self):
        """Test that create_app is exported from the module."""
        import soar_lab.interfaces.api as api_module

        assert hasattr(api_module, "create_app")
        assert callable(api_module.create_app)

    def test_all_exported(self):
        """Test that __all__ contains expected exports."""
        import soar_lab.interfaces.api as api_module

        assert "app" in api_module.__all__
        assert "create_app" in api_module.__all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
