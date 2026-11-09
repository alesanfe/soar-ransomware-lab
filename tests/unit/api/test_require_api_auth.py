"""Unit tests for the require_api_auth dependency (SOAR-011).

The dependency gates mutating endpoints behind either a Bearer JWT or a
shared ``X-Service-Token`` when ``API_REQUIRE_AUTH=true``. Auth is enabled
by default (secure-by-default); an explicit ``API_REQUIRE_AUTH=false``
opts out for throwaway lab runs.
"""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from soar_lab.interfaces.api.auth import require_api_auth

__all__ = ["TestRequireApiAuth"]


class _CP:
    """Minimal config provider stub."""

    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def _make_app(require_auth: bool, service_token: str = "", user_dep=None) -> TestClient:
    app = FastAPI()
    app.state.config_provider = _CP(
        {
            "API_REQUIRE_AUTH": "true" if require_auth else "false",
            "INTERNAL_SERVICE_TOKEN": service_token,
            "SHUFFLE_WEBHOOK_TOKEN": "",
        }
    )
    app.state.get_current_user = user_dep

    @app.post("/protected", dependencies=[Depends(require_api_auth)])
    async def protected():
        return {"ok": True}

    return TestClient(app)


class TestRequireApiAuth:
    """Enforcement behaviour of require_api_auth."""

    def test_disabled_allows_unauthenticated(self):
        client = _make_app(require_auth=False)
        assert client.post("/protected").status_code == 200

    def test_default_enforces_auth(self):
        """Missing API_REQUIRE_AUTH must default to enforced (secure-by-default)."""
        app = FastAPI()
        app.state.config_provider = _CP({"INTERNAL_SERVICE_TOKEN": "tok"})
        app.state.get_current_user = None

        @app.post("/protected", dependencies=[Depends(require_api_auth)])
        async def protected():
            return {"ok": True}

        client = TestClient(app)
        resp = client.post("/protected")
        assert resp.status_code == 401

    def test_enabled_rejects_missing_credentials(self):
        client = _make_app(require_auth=True, service_token="tok-123")
        resp = client.post("/protected")
        assert resp.status_code == 401
        assert resp.headers.get("WWW-Authenticate") == "Bearer"

    def test_enabled_rejects_wrong_service_token(self):
        client = _make_app(require_auth=True, service_token="tok-123")
        resp = client.post("/protected", headers={"X-Service-Token": "wrong"})
        assert resp.status_code == 401

    def test_enabled_accepts_service_token(self):
        client = _make_app(require_auth=True, service_token="tok-123")
        resp = client.post("/protected", headers={"X-Service-Token": "tok-123"})
        assert resp.status_code == 200

    def test_enabled_accepts_valid_jwt(self):
        def fake_get_current_user(credentials):
            assert credentials.credentials == "jwt-abc"
            return {"user": "analyst"}

        client = _make_app(
            require_auth=True, service_token="tok-123", user_dep=fake_get_current_user
        )
        resp = client.post("/protected", headers={"Authorization": "Bearer jwt-abc"})
        assert resp.status_code == 200

    def test_enabled_rejects_empty_bearer(self):
        client = _make_app(require_auth=True, service_token="tok-123")
        resp = client.post("/protected", headers={"Authorization": "Basic abc"})
        assert resp.status_code == 401
