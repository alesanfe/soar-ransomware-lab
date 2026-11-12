#!/usr/bin/env python3
"""Endpoint-level tests for TAXII-lite and Grafana alert receiver routes."""

from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _app(register_fn, auth_dep, **state):
    app = FastAPI()
    register_fn(app)
    for k, v in state.items():
        setattr(app.state, k, v)
    app.dependency_overrides[auth_dep] = lambda: {"user": "t"}
    return TestClient(app)


class TestTaxiiRoutes:
    def _client(self, repo=None):
        from soar_lab.interfaces.api.auth import require_api_auth
        from soar_lab.interfaces.api.routes_taxii import register_taxii_routes

        return _app(register_taxii_routes, require_api_auth, alert_repository=repo)

    def test_no_repository_503(self):
        c = self._client(repo=None)
        assert c.get("/api/v1/taxii2/").status_code == 503

    def test_discovery_and_api_root_and_collections(self):
        c = self._client(repo=Mock(get_alerts=Mock(return_value=[])))
        assert c.get("/api/v1/taxii2/").status_code == 200
        assert c.get("/api/v1/taxii2/api/").status_code == 200
        assert c.get("/api/v1/taxii2/api/collections/").status_code == 200

    def test_collection_404_and_objects_envelope(self):
        c = self._client(repo=Mock(get_alerts=Mock(return_value=[])))
        cols = c.get("/api/v1/taxii2/api/collections/").json()["collections"]
        cid = cols[0]["id"]
        assert c.get(f"/api/v1/taxii2/api/collections/{cid}/").status_code == 200
        assert c.get("/api/v1/taxii2/api/collections/nope/").status_code == 404

        r = c.get(f"/api/v1/taxii2/api/collections/{cid}/objects/")
        assert r.status_code == 200
        assert "taxii" in r.headers["content-type"]
        assert c.get("/api/v1/taxii2/api/collections/nope/objects/").status_code == 404

    def test_objects_internal_error_500(self):
        repo = Mock()
        repo.get_alerts.side_effect = RuntimeError("boom")
        c = self._client(repo=repo)
        cols = c.get("/api/v1/taxii2/api/collections/").json()["collections"]
        cid = cols[0]["id"]
        assert c.get(f"/api/v1/taxii2/api/collections/{cid}/objects/").status_code == 500


class TestGrafanaAlertRoutes:
    def _client(self):
        from soar_lab.interfaces.api.auth import require_api_auth
        from soar_lab.interfaces.api.routes_grafana_alerts import (
            register_grafana_alert_routes,
        )

        return _app(register_grafana_alert_routes, require_api_auth)

    def test_firing_notification_counts_and_logs(self):
        from soar_lab.interfaces.api.routes_grafana_alerts import grafana_alert_counters

        c = self._client()
        before = grafana_alert_counters()["firing"]
        r = c.post(
            "/api/v1/alerts/grafana",
            json={
                "status": "firing",
                "receiver": "soar-web",
                "alerts": [
                    {
                        "status": "firing",
                        "labels": {"alertname": "x\ninjected", "severity": "crit"},
                        "annotations": {"summary": "s"},
                        "fingerprint": "fp",
                        "startsAt": "t1",
                        "endsAt": "t2",
                    },
                    {"labels": {"rulename": "r"}},
                ],
            },
        )
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "received": 2}
        assert grafana_alert_counters()["firing"] == before + 1

    def test_unknown_status_and_empty_alerts(self):
        from soar_lab.interfaces.api.routes_grafana_alerts import grafana_alert_counters

        c = self._client()
        r = c.post("/api/v1/alerts/grafana", json={"status": "weird"})
        assert r.status_code == 200
        assert grafana_alert_counters()["other"] >= 1

    def test_log_safe_escapes_and_none(self):
        from soar_lab.interfaces.api.routes_grafana_alerts import _log_safe

        assert _log_safe(None) == "-"
        assert "\n" not in _log_safe("a\nb")
        assert _log_safe("") == "-"
        assert len(_log_safe("x" * 500)) == 120
