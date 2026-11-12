"""Tests for the TAXII-lite read-only surface (INT-01)."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from soar_lab.application.use_cases.taxii_server import ALERTS_COLLECTION_ID
from soar_lab.interfaces.api import routes_taxii as mod
from soar_lab.interfaces.api.auth import require_api_auth


def _app(repository=None) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[require_api_auth] = lambda: {"sub": "taxii"}
    if repository is not None:
        app.state.alert_repository = repository
    mod.register_taxii_routes(app)
    return app


def _repo(alerts=None):
    repo = Mock()
    repo.get_alerts = Mock(return_value=alerts or [])
    return repo


class TestServerResolution:
    def test_missing_repository_raises_503(self):
        app = FastAPI()  # no alert_repository in state
        with pytest.raises(HTTPException) as exc:
            mod._server(app)
        assert exc.value.status_code == 503

    def test_repository_without_get_alerts_raises_503(self):
        app = FastAPI()
        app.state.alert_repository = object()
        with pytest.raises(HTTPException) as exc:
            mod._server(app)
        assert exc.value.status_code == 503

    def test_valid_repository_builds_server(self):
        app = FastAPI()
        app.state.alert_repository = _repo()
        assert mod._server(app) is not None


class TestTaxiiEndpoints:
    def test_discovery(self):
        resp = TestClient(_app(_repo())).get("/api/v1/taxii2/")
        assert resp.status_code == 200
        assert "title" in resp.json() or "default" in resp.json()

    def test_api_root(self):
        resp = TestClient(_app(_repo())).get("/api/v1/taxii2/api/")
        assert resp.status_code == 200

    def test_collections_lists_static_collection(self):
        resp = TestClient(_app(_repo())).get("/api/v1/taxii2/api/collections/")
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()["collections"]]
        assert ALERTS_COLLECTION_ID in ids

    def test_collection_metadata(self):
        resp = TestClient(_app(_repo())).get(
            f"/api/v1/taxii2/api/collections/{ALERTS_COLLECTION_ID}/"
        )
        assert resp.status_code == 200

    def test_unknown_collection_404(self):
        resp = TestClient(_app(_repo())).get("/api/v1/taxii2/api/collections/does-not-exist/")
        assert resp.status_code == 404

    def test_objects_envelope_taxii_media_type(self):
        resp = TestClient(_app(_repo())).get(
            f"/api/v1/taxii2/api/collections/{ALERTS_COLLECTION_ID}/objects/"
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/taxii+json")

    def test_objects_unknown_collection_404(self):
        resp = TestClient(_app(_repo())).get(
            "/api/v1/taxii2/api/collections/does-not-exist/objects/"
        )
        assert resp.status_code == 404

    def test_objects_error_maps_to_500(self):
        repo = _repo()
        repo.get_alerts.side_effect = RuntimeError("repo exploded")
        resp = TestClient(_app(repo)).get(
            f"/api/v1/taxii2/api/collections/{ALERTS_COLLECTION_ID}/objects/"
        )
        assert resp.status_code == 500

    def test_missing_repository_503(self):
        resp = TestClient(_app()).get("/api/v1/taxii2/api/collections/")
        assert resp.status_code == 503
