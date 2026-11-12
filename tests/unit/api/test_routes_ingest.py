#!/usr/bin/env python3
"""Endpoint tests for routes_ingest — admission service fully mocked."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from soar_lab.application.use_cases.alert_admission import (
    AdmissionValidationError,
    BackpressureError,
    IdempotencyConflictError,
    QueueUnavailableError,
)


def _app(svc=None, **state):
    from soar_lab.interfaces.api.auth import require_api_auth
    from soar_lab.interfaces.api.routes_ingest import register_ingest_routes

    app = FastAPI()
    register_ingest_routes(app, admission_service=svc)
    for k, v in state.items():
        setattr(app.state, k, v)
    app.dependency_overrides[require_api_auth] = lambda: {"user": "t"}
    return TestClient(app)


def _svc():
    svc = Mock()
    svc.admit = AsyncMock(return_value={"admission_id": "a1", "status_url": "/x"})
    svc.status = AsyncMock(return_value=None)
    svc.record_workflow_verdict = AsyncMock(return_value=None)
    svc.queue = Mock()
    return svc


class TestSchemaValidators:
    def test_bad_version_ip_hash_hostname_extras(self):
        from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

        with pytest.raises(Exception, match="schema_version"):
            AlertIngestSchema(schema_version="9.9")
        with pytest.raises(Exception):
            AlertIngestSchema(src_ip="999.999.1.1")
        with pytest.raises(Exception, match="hash"):
            AlertIngestSchema(hash="abc")
        with pytest.raises(Exception, match="hostname"):
            AlertIngestSchema(hostname="-bad-")
        with pytest.raises(Exception, match="extra"):
            AlertIngestSchema(**{f"k{i}": "x" for i in range(70)})
        with pytest.raises(Exception, match="extra"):
            AlertIngestSchema(big="y" * 5000)

    def test_to_alert_dict_normalizes_and_sanitizes(self):
        from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

        d = AlertIngestSchema(title="t").to_alert_dict()
        assert d["severity"] == 2  # DEFAULT_SEVERITY
        d = AlertIngestSchema(severity="high").to_alert_dict()
        assert d["severity"] == 3


class TestAdmitEndpoint:
    def test_service_unavailable_503(self):
        assert _app(svc=None).post("/api/v1/alerts", json={}).status_code == 503

    def test_accepted_202(self):
        r = _app(svc=_svc()).post("/api/v1/alerts", json={"title": "t"})
        assert r.status_code == 202

    @pytest.mark.parametrize(
        "exc,code",
        [
            (AdmissionValidationError("bad"), 422),
            (IdempotencyConflictError("dup"), 409),
            (BackpressureError("full"), 503),
            (QueueUnavailableError("down"), 503),
        ],
    )
    def test_error_mapping(self, exc, code):
        svc = _svc()
        svc.admit.side_effect = exc
        r = _app(svc=svc).post("/api/v1/alerts", json={})
        assert r.status_code == code
        if code == 503:
            assert r.headers.get("Retry-After") == "5"


class TestCallbackAndStatus:
    def test_callback_404_and_ok(self):
        svc = _svc()
        svc.record_workflow_verdict.side_effect = [None, {"status": "workflow_accepted"}]
        c = _app(svc=svc, config_provider=Mock(get=Mock(return_value=None)))
        body = {"admission_id": "a1", "outcome": "accepted"}
        assert c.post("/api/v1/alerts/callback", json=body).status_code == 404
        r = c.post("/api/v1/alerts/callback", json=body)
        assert r.json()["status"] == "workflow_accepted"

    def test_status_404_and_record(self):
        svc = _svc()
        svc.status.side_effect = [{"x": 1}, None]
        c = _app(svc=svc)
        assert c.get("/api/v1/alerts/a1").json() == {"x": 1}
        assert c.get("/api/v1/alerts/nope").status_code == 404


class TestQueueEndpoints:
    def test_dlq_and_metrics(self):
        svc = _svc()
        svc.queue.dlq_size = AsyncMock(return_value=2)
        svc.queue.dlq_list = AsyncMock(return_value=[{"id": "d1"}])
        svc.queue.dlq_redrive = AsyncMock(side_effect=[True, False])
        svc.queue.dlq_purge = AsyncMock(return_value=3)
        svc.queue.metrics = AsyncMock(return_value={"depth": 5})
        c = _app(svc=svc)

        r = c.get("/api/v1/queue/dlq")
        assert r.json() == {"size": 2, "entries": [{"id": "d1"}]}
        assert c.post("/api/v1/queue/dlq/redrive", json={"dlq_entry_id": "d1"}).json() == {
            "redriven": True,
            "dlq_entry_id": "d1",
        }
        assert c.post("/api/v1/queue/dlq/redrive", json={"dlq_entry_id": "x"}).status_code == 404
        assert c.delete("/api/v1/queue/dlq").json() == {"purged": 3}
        assert c.get("/api/v1/queue/metrics").json() == {"depth": 5}

    def test_queue_missing_503(self):
        svc = _svc()
        svc.queue = None
        assert _app(svc=svc).get("/api/v1/queue/dlq").status_code == 503


class TestAuditAndConfig:
    def test_audit_trail_variants(self):
        c = _app(svc=_svc())
        # no auth_service -> empty
        assert c.get("/api/v1/audit").json() == {"size": 0, "events": []}
        c.app.state.auth_service = Mock(audit=Mock(events=[{"e": i} for i in range(3)]))
        r = c.get("/api/v1/audit?limit=2").json()
        assert r["size"] == 3 and len(r["events"]) == 2

    def test_config_dump_variants(self):
        c = _app(svc=_svc())
        assert c.get("/api/v1/config").json() == {"values": {}, "redacted": True}
        c.app.state.config_provider = object()  # no get_all
        assert c.get("/api/v1/config").json() == {"values": {}, "redacted": True}
        c.app.state.config_provider = Mock(get_all=Mock(return_value={"A": "1"}))
        assert c.get("/api/v1/config").json()["values"] == {"A": "1"}


class TestSchemaValidPaths:
    def test_valid_ip_version_severity_none_hostname(self):
        from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

        s = AlertIngestSchema(
            schema_version="1.0",
            src_ip="10.0.0.1",
            severity=None,
            hostname="web-01",
            domain="example.com",
        )
        assert s.src_ip == "10.0.0.1"

    def test_valid_hash_lengths_accepted(self):
        from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

        assert AlertIngestSchema(hash="a" * 32).hash == "a" * 32
        assert AlertIngestSchema(hash="b" * 64).hash == "b" * 64
        assert AlertIngestSchema(src_ip=None).src_ip is None

    def test_invalid_severity_raises_value_error(self):
        from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

        with pytest.raises(Exception):
            AlertIngestSchema(severity="bogus-tier")

    def test_short_extra_fields_pass_model_validator(self):
        from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

        s = AlertIngestSchema(title="t", custom_field="ok", num=1)
        assert s.title == "t"


class TestNonceBackendFallback:
    def test_redis_nonce_store_ctor_error_falls_back(self, monkeypatch):
        import soar_lab.interfaces.api.routes_ingest as ri
        from soar_lab.security.webhook_signing import sign_request

        class BoomStore:
            def __init__(self, *a, **kw):
                raise RuntimeError("ctor fail")

        monkeypatch.setattr(
            "soar_lab.security.webhook_signing.RedisNonceStore", BoomStore
        )
        secret = "s" * 40
        cp = Mock()
        cp.get = Mock(
            side_effect=lambda k: {
                "CALLBACK_HMAC_KEY": secret,
                "CALLBACK_HMAC_KEY_ID": "wf-callback-1",
            }.get(k)
        )
        app = FastAPI()
        svc = _svc()
        svc.record_workflow_verdict = AsyncMock(return_value={"status": "ok"})
        ri.register_ingest_routes(app, admission_service=svc)
        app.state.config_provider = cp
        app.state.redis_client = object()  # truthy -> attempts RedisNonceStore
        from soar_lab.interfaces.api.auth import require_api_auth

        app.dependency_overrides[require_api_auth] = lambda: {"user": "t"}
        body = b'{"admission_id":"a1","outcome":"accepted"}'
        headers = sign_request(
            secret,
            method="POST",
            path="/api/v1/alerts/callback",
            body=body,
            key_id="wf-callback-1",
        )
        headers["content-type"] = "application/json"
        # falls back to the in-memory nonce store -> signature still verifies
        r = TestClient(app).post(
            "/api/v1/alerts/callback", content=body, headers=headers
        )
        assert r.status_code == 200


class TestCallbackSignatureGate:
    def _app_with_hmac(self, cp, redis_client=None):
        from soar_lab.interfaces.api.auth import require_api_auth
        from soar_lab.interfaces.api.routes_ingest import register_ingest_routes

        app = FastAPI()
        svc = _svc()
        svc.record_workflow_verdict = AsyncMock(
            return_value={"status": "forwarded"}
        )
        register_ingest_routes(app, admission_service=svc)
        app.state.config_provider = cp
        if redis_client is not None:
            app.state.redis_client = redis_client
        app.dependency_overrides[require_api_auth] = lambda: {"user": "t"}
        return TestClient(app)

    def test_no_hmac_key_passes_through(self):
        cp = Mock()
        cp.get = Mock(return_value=None)
        r = self._app_with_hmac(cp).post(
            "/api/v1/alerts/callback", json={"admission_id": "a1", "outcome": "accepted"}
        )
        assert r.status_code == 200

    def test_bad_signature_401(self):
        cp = Mock()
        cp.get = Mock(
            side_effect=lambda k: "s" * 40 if k == "CALLBACK_HMAC_KEY" else None
        )
        r = self._app_with_hmac(cp).post(
            "/api/v1/alerts/callback",
            json={"admission_id": "a1", "outcome": "accepted"},
            headers={
                "X-SOAR-Signature-Version": "v1",
                "X-SOAR-Key-Id": "wf-callback-1",
                "X-SOAR-Timestamp": "1",
                "X-SOAR-Nonce": "n",
                "X-SOAR-Content-SHA256": "0" * 64,
                "X-SOAR-Signature": "v1=" + "0" * 64,
            },
        )
        assert r.status_code == 401

    def test_valid_signature_200_with_redis_nonce(self):
        from soar_lab.security.webhook_signing import sign_request

        secret = "s" * 40
        cp = Mock()
        cp.get = Mock(
            side_effect=lambda k: {
                "CALLBACK_HMAC_KEY": secret,
                "CALLBACK_HMAC_KEY_ID": "wf-callback-1",
            }.get(k)
        )
        body = b'{"admission_id":"a1","outcome":"accepted"}'
        headers = sign_request(
            secret,
            method="POST",
            path="/api/v1/alerts/callback",
            body=body,
            key_id="wf-callback-1",
        )

        class FakeRedis:
            async def set(self, *a, **kw):
                return True

        headers["content-type"] = "application/json"
        r = self._app_with_hmac(cp, redis_client=FakeRedis()).post(
            "/api/v1/alerts/callback", content=body, headers=headers
        )
        assert r.status_code == 200

    def test_nonce_backend_falls_back_on_redis_error(self):
        from soar_lab.security.webhook_signing import sign_request

        secret = "s" * 40
        cp = Mock()
        cp.get = Mock(
            side_effect=lambda k: {
                "CALLBACK_HMAC_KEY": secret,
                "CALLBACK_HMAC_KEY_ID": "wf-callback-1",
            }.get(k)
        )
        body = b'{"admission_id":"a1","outcome":"accepted"}'
        headers = sign_request(
            secret,
            method="POST",
            path="/api/v1/alerts/callback",
            body=body,
            key_id="wf-callback-1",
        )

        class ExplodingRedis:
            async def set(self, *a, **kw):
                raise RuntimeError("down")

        # RedisNonceStore raising inside claim -> 401, not a crash
        r = self._app_with_hmac(cp, redis_client=ExplodingRedis()).post(
            "/api/v1/alerts/callback", content=body, headers=headers
        )
        assert r.status_code == 401

    def test_unknown_key_id_resolver_returns_none_401(self):
        from soar_lab.security.webhook_signing import sign_request

        secret = "s" * 40
        cp = Mock()
        cp.get = Mock(
            side_effect=lambda k: {
                "CALLBACK_HMAC_KEY": secret,
                "CALLBACK_HMAC_KEY_ID": "wf-callback-1",
            }.get(k)
        )
        body = b'{"admission_id":"a1","outcome":"accepted"}'
        headers = sign_request(
            secret,
            method="POST",
            path="/api/v1/alerts/callback",
            body=body,
            key_id="unknown-kid",
        )
        headers["content-type"] = "application/json"
        r = self._app_with_hmac(cp).post(
            "/api/v1/alerts/callback", content=body, headers=headers
        )
        assert r.status_code == 401

    def test_prev_key_rotation_grace_verifies(self):
        from soar_lab.security.webhook_signing import sign_request

        prev = "p" * 40
        cp = Mock()
        cp.get = Mock(
            side_effect=lambda k: {
                "CALLBACK_HMAC_KEY": "s" * 40,
                "CALLBACK_HMAC_KEY_ID": "wf-callback-2",
                "CALLBACK_HMAC_KEY_PREV": prev,
            }.get(k)
        )
        body = b'{"admission_id":"a1","outcome":"accepted"}'
        headers = sign_request(
            prev,
            method="POST",
            path="/api/v1/alerts/callback",
            body=body,
            key_id="wf-callback-1",
        )
        headers["content-type"] = "application/json"
        r = self._app_with_hmac(cp).post(
            "/api/v1/alerts/callback", content=body, headers=headers
        )
        assert r.status_code == 200
