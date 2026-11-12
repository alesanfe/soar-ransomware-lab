"""Tests for the Grafana Alertmanager webhook receiver (GRAF-ALERT-RX)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from soar_lab.interfaces.api import routes_grafana_alerts as mod
from soar_lab.interfaces.api.auth import require_api_auth


def _app() -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_api_auth] = lambda: {"sub": "grafana"}
    mod.register_grafana_alert_routes(app)
    return app


def _payload(status="firing", alerts=None, receiver="soar-api-webhook"):
    return {
        "status": status,
        "receiver": receiver,
        "alerts": alerts or [],
        "commonLabels": {},
        "commonAnnotations": {},
    }


class TestLogSafe:
    """INPUT-003: label values are attacker-influenceable — escape them."""

    def test_none_becomes_dash(self):
        assert mod._log_safe(None) == "-"

    def test_empty_becomes_dash(self):
        assert mod._log_safe("") == "-"

    def test_control_chars_replaced(self):
        forged = "evil\nforged-entry\twith\nnewlines\x7f"
        safe = mod._log_safe(forged)
        assert "\n" not in safe and "\t" not in safe and "\x7f" not in safe
        assert "evil forged-entry" in safe

    def test_truncated_at_max_len(self):
        assert len(mod._log_safe("x" * 500)) == 120
        assert len(mod._log_safe("x" * 500, max_len=10)) == 10


class TestReceiveGrafanaAlert:
    def setup_method(self):
        # Process-wide counters persist across tests — reset per test.
        mod._counts.update({"firing": 0, "resolved": 0, "other": 0})

    def test_firing_notification_counted(self):
        resp = TestClient(_app()).post(
            "/api/v1/alerts/grafana",
            json=_payload(
                "firing",
                alerts=[{"status": "firing", "labels": {"alertname": "HighCPU"}}],
            ),
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "received": 1}
        assert mod.grafana_alert_counters()["firing"] == 1

    def test_resolved_notification_counted(self):
        resp = TestClient(_app()).post(
            "/api/v1/alerts/grafana", json=_payload("resolved", alerts=[{"status": "resolved"}])
        )
        assert resp.status_code == 200
        assert mod.grafana_alert_counters()["resolved"] == 1

    def test_unknown_status_counted_as_other(self):
        resp = TestClient(_app()).post(
            "/api/v1/alerts/grafana", json=_payload("suppressed", alerts=[])
        )
        assert resp.status_code == 200
        assert mod.grafana_alert_counters()["other"] == 1

    def test_alert_status_falls_back_to_payload_status(self, caplog):
        """Alert without own status inherits the notification status."""
        resp = TestClient(_app()).post(
            "/api/v1/alerts/grafana",
            json=_payload("firing", alerts=[{"labels": {"alertname": "A"}}]),
        )
        assert resp.status_code == 200
        assert "grafana_alert=1 status=firing" in caplog.text

    def test_resolved_alert_logs_at_info(self, caplog):
        import logging

        with caplog.at_level(logging.INFO):
            TestClient(_app()).post(
                "/api/v1/alerts/grafana",
                json=_payload(
                    "resolved", alerts=[{"status": "resolved", "labels": {"alertname": "B"}}]
                ),
            )
        assert "grafana_alert=1 status=resolved" in caplog.text

    def test_empty_alerts_logged_and_acknowledged(self, caplog):
        import logging

        with caplog.at_level(logging.INFO):
            resp = TestClient(_app()).post("/api/v1/alerts/grafana", json=_payload("firing"))
        assert resp.status_code == 200
        assert resp.json()["received"] == 0
        assert "empty notification" in caplog.text

    def test_label_forge_escaped_in_log(self, caplog):
        """A newline in alertname must not forge extra log entries (CWE-117)."""
        TestClient(_app()).post(
            "/api/v1/alerts/grafana",
            json=_payload("firing", alerts=[{"status": "firing", "labels": {"alertname": "a\nb"}}]),
        )
        assert "a\nb" not in caplog.text
        assert "a b" in caplog.text

    def test_counters_snapshot_is_a_copy(self):
        snap = mod.grafana_alert_counters()
        snap["firing"] = 999
        assert mod.grafana_alert_counters()["firing"] == 0
