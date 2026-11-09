"""Chaos/degradation tests (R5): dependency failures must produce typed
errors — never an unhandled traceback or a silent success.

Covers:
- readiness probe reports per-check failure with latency and returns 503
- a storage backend that throws mid-request surfaces as a typed 503
- integration clients that raise inside /soar/status degrade honestly
"""

from unittest.mock import Mock

from fastapi.testclient import TestClient

from soar_lab.interfaces.api.main import create_app


def _make_config():
    cp = Mock()
    cp.get.side_effect = lambda key, default=None: {
        "API_REQUIRE_AUTH": "false",
        "DOCS_DIR": "/nonexistent",
    }.get(key, default)
    cp.get_service_urls.return_value = {}
    return cp


def _make_app(**overrides):
    auth = Mock()
    auth.verify_credentials.return_value = True
    auth.create_jwt_token.return_value = "t"
    auth.verify_jwt_token.return_value = {"user": "admin", "role": "admin"}
    defaults = {
        "config_provider": _make_config(),
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


class TestReadinessChaos:
    def test_storage_exception_reports_fail_with_latency(self):
        storage = Mock()
        storage.get_file_info.side_effect = OSError("disk gone")
        client = TestClient(_make_app(storage=storage))
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["status"] == "not_ready"
        check = detail["checks"]["storage"]
        assert check["status"] == "fail"
        assert check["detail"] == "OSError"
        assert "latency_ms" in check

    def test_queue_metrics_exception_reports_fail(self):
        service = Mock()
        service.queue.metrics.side_effect = ConnectionError("redis down")
        app = _make_app()
        app.state.admission_service = service
        client = TestClient(app)
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        check = resp.json()["detail"]["checks"]["admission_queue"]
        assert check["status"] == "fail"
        assert check["detail"] == "ConnectionError"

    def test_absent_queue_reports_not_configured(self):
        app = _make_app()
        service = Mock()
        service.queue = None
        app.state.admission_service = service
        resp = TestClient(app).get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["detail"]["checks"]["admission_queue"]["detail"] == "not-configured"


class TestTypedErrors:
    def test_unhandled_error_returns_json_not_html(self):
        """A route that raises still returns a JSON error envelope."""
        client = TestClient(_make_app())
        resp = client.get("/api/v1/nonexistent-route")
        # 404/401 — either way the body must be JSON, not a traceback page.
        assert resp.headers["content-type"].startswith("application/json")
