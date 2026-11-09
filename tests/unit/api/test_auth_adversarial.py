"""API-01: endpoint-level adversarial auth tests.

Provider-level JWT checks (expired/wrong-secret) already live in
``test_jwt_token_provider.py``; these tests pin the *endpoint* behaviour:
a tampered or expired token must surface as 401, a replayed WS ticket
must be rejected, and a denied role must surface as 403 — not 200, not
500.
"""

from __future__ import annotations

import base64
import json
import time

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from soar_lab.common.exceptions import AuthError
from soar_lab.interfaces.api.auth import require_api_auth

_SECRET = "x" * 64  # >= 32 chars per _validate_secret_length
_ALG = "HS256"


def _b64(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _jwt(payload: dict, provider) -> str:
    return provider.create_token("analyst", _SECRET, 60, _ALG, extra_claims=payload)


def _provider():
    from soar_lab.infrastructure.jwt_token_provider import JWTTokenProvider

    return JWTTokenProvider()


def _app(auth_dep, extra_route=None) -> TestClient:
    app = FastAPI()
    app.state.config_provider = _CP({"API_REQUIRE_AUTH": "true"})
    app.state.get_current_user = auth_dep

    # Mirror the production mapping in interfaces/api/main.py: AuthError -> 401.
    @app.exception_handler(AuthError)
    async def _auth_handler(request: Request, exc: AuthError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.post("/protected", dependencies=[Depends(require_api_auth)])
    async def protected():
        return {"ok": True}

    if extra_route:
        extra_route(app)
    return TestClient(app)


class _CP:
    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def _dep_for(provider):
    """get_current_user backed by the real JWT provider + real secret."""

    def dep(credentials):
        return provider.verify_token(credentials.credentials, _SECRET, _ALG)

    return dep


class TestExpiredAndTamperedJWT:
    def test_expired_jwt_returns_401(self):
        provider = _provider()
        token = provider.create_token("analyst", _SECRET, -1, _ALG)
        client = _app(_dep_for(provider))
        resp = client.post("/protected", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_tampered_payload_returns_401(self):
        """Rewrite a claim but keep the old signature -> must be rejected."""
        provider = _provider()
        token = provider.create_token("analyst", _SECRET, 60, _ALG)
        head, payload, sig = token.split(".")
        forged_payload = _b64({"sub": "admin", "role": "admin", "exp": int(time.time()) + 9999})
        forged = f"{head}.{forged_payload}.{sig}"
        client = _app(_dep_for(provider))
        resp = client.post("/protected", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401

    def test_forged_signature_returns_401(self):
        """Payload signed with a DIFFERENT secret -> invalid signature."""
        provider = _provider()
        forged = provider.create_token("analyst", "y" * 64, 60, _ALG)
        client = _app(_dep_for(provider))
        resp = client.post("/protected", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401

    def test_alg_none_style_header_returns_401(self):
        """A token the provider cannot verify must never authenticate."""
        provider = _provider()
        forged = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64({'sub': 'admin'})}."
        client = _app(_dep_for(provider))
        resp = client.post("/protected", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401


class TestWsTicketReplay:
    def test_ticket_reuse_rejected(self):
        """Single-use ticket: second consume of the same ticket fails."""
        from soar_lab.infrastructure.ws_ticket_store import WsTicketStore

        store = WsTicketStore(ttl=60, max_pending_per_user=3)
        ticket = store.issue("user-1")
        assert store.consume(ticket).ok is True
        assert store.consume(ticket).ok is False  # replay -> invalid

    def test_unknown_ticket_rejected(self):
        from soar_lab.infrastructure.ws_ticket_store import WsTicketStore

        store = WsTicketStore(ttl=60, max_pending_per_user=3)
        assert store.consume("forged-ticket").ok is False


class TestCrossRoleIsolation:
    def test_denied_role_returns_403(self):
        """AUTH-003: analyst role denied on an admin-only action -> 403."""
        from soar_lab.interfaces.api.auth import _enforce_role

        class _Svc:
            def can_access_endpoint(self, user, path, method):
                return False

        request = type(
            "R",
            (),
            {
                "method": "POST",
                "url": type("U", (), {"path": "/api/v1/contain"})(),
                "headers": {},
                "client": type("C", (), {"host": "127.0.0.1"})(),
                "app": type("A", (), {"state": type("S", (), {"auth_service": _Svc()})()})(),
            },
        )()
        principal = {"sub": "analyst", "role": "analyst"}
        with pytest.raises(Exception) as excinfo:
            _enforce_role(request, principal)
        assert getattr(excinfo.value, "status_code", None) == 403
