"""Unit tests for the SecurityHeadersMiddleware.

Verifies that the hardened header set is applied to every response —
including error responses — that docs paths get the relaxed Swagger CSP,
and that HSTS honours its toggle.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from soar_lab.interfaces.api.middleware.security_headers import (
    SecurityHeadersMiddleware,
)


def _make_app(hsts_enabled: bool = True) -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, hsts_enabled=hsts_enabled)

    @app.get("/api/v1/x")
    async def api_ok():
        return {"ok": True}

    @app.get("/docs")
    async def docs():
        return {"doc": True}

    @app.get("/api/v1/fail")
    async def fail():
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="unavailable")

    return app


class TestBaselineHeaders:
    def test_headers_on_success(self):
        resp = TestClient(_make_app()).get("/api/v1/x")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "no-referrer"
        assert "Permissions-Policy" in resp.headers
        assert resp.headers["Strict-Transport-Security"].startswith("max-age=")

    def test_headers_on_error(self):
        resp = TestClient(_make_app()).get("/api/v1/fail")
        assert resp.status_code == 503
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"

    def test_hsts_toggle_off(self):
        resp = TestClient(_make_app(hsts_enabled=False)).get("/api/v1/x")
        assert "Strict-Transport-Security" not in resp.headers


class TestCSP:
    def test_api_csp_is_closed(self):
        resp = TestClient(_make_app()).get("/api/v1/x")
        assert "default-src 'none'" in resp.headers["Content-Security-Policy"]

    def test_docs_csp_allows_swagger_cdn(self):
        resp = TestClient(_make_app()).get("/docs")
        csp = resp.headers["Content-Security-Policy"]
        assert "cdn.jsdelivr.net" in csp
        assert "'unsafe-inline'" in csp


class TestCacheControl:
    def test_api_no_store(self):
        resp = TestClient(_make_app()).get("/api/v1/x")
        assert resp.headers["Cache-Control"] == "no-store"

    def test_non_api_not_marked(self):
        resp = TestClient(_make_app()).get("/docs")
        assert "Cache-Control" not in resp.headers
