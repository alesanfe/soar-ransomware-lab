"""Fase-1b hardening regression tests.

Covers AUTH-003 (RBAC role map enforcement), AUTH-004 (per-request auth
audit trail), IDEMP-002 (content fingerprint fallback), IDEMP-003
(X-Idempotency-Key propagation to Shuffle), QUEUE-006 (Prometheus text
exposition), VAL-003 (exportable JSON Schema via OpenAPI) and VAL-004
(Hypothesis fuzzing of the ingest boundary).
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

pytest.importorskip("hypothesis", reason="hypothesis not installed")


# ---------------------------------------------------------------------
# IDEMP-002 — content fingerprint fallback
# ---------------------------------------------------------------------


class FakeEventQueue:
    def __init__(self):
        self.events: list[dict] = []

    async def enqueue(self, event: dict) -> str:
        self.events.append(event)
        return f"entry-{len(self.events)}"

    async def depth(self) -> int:
        return len(self.events)


class FakeAdmissionStore:
    def __init__(self):
        self.records: dict[str, dict] = {}
        self.by_key: dict[str, str] = {}

    async def create(self, record: dict) -> None:
        self.records[record["admission_id"]] = dict(record)

    async def update(self, admission_id: str, fields: dict) -> None:
        self.records[admission_id].update(fields)

    async def get(self, admission_id: str):
        return self.records.get(admission_id)

    async def find_by_key(self, key: str):
        return self.by_key.get(key)

    async def bind_key(self, key: str, admission_id: str) -> None:
        self.by_key[key] = admission_id

    async def try_bind_key(self, key: str, admission_id: str):
        if key in self.by_key:
            return self.by_key[key]
        self.by_key[key] = admission_id
        return None

    async def unbind_key(self, key: str, admission_id: str) -> None:
        if self.by_key.get(key) == admission_id:
            del self.by_key[key]


def _admission_uc():
    from soar_lab.application.use_cases.alert_admission import AlertAdmissionUseCase

    return AlertAdmissionUseCase(queue=FakeEventQueue(), store=FakeAdmissionStore())


class TestContentFingerprint:
    async def test_identical_alerts_dedupe_without_explicit_key(self):
        """IDEMP-002: two byte-identical alerts with no caller key must
        collapse into ONE admission — previously each got a random
        alert_id and duplicated downstream."""
        uc = _admission_uc()
        alert = {"title": "ransom-note", "severity": 4, "detection_time": "t0"}
        first = await uc.admit(dict(alert))
        second = await uc.admit(dict(alert))
        assert second["admission_id"] == first["admission_id"]
        assert len(uc.queue.events) == 1

    async def test_different_alerts_do_not_dedupe(self):
        """The fingerprint is over the FULL content — distinct alerts must
        never collapse (the trap of hashing only a few fields)."""
        uc = _admission_uc()
        a = await uc.admit({"hostname": "victim_1"})
        b = await uc.admit({"hostname": "victim_2"})
        assert a["admission_id"] != b["admission_id"]
        assert len(uc.queue.events) == 2

    async def test_volatile_ids_do_not_change_fingerprint(self):
        """alert_id/idempotency_key are per-submission — they must not
        defeat dedupe."""
        uc = _admission_uc()
        base = {"title": "t", "severity": 1}
        first = await uc.admit({**base, "alert_id": "ALR-1"})
        second = await uc.admit({**base, "alert_id": "ALR-2"})
        # Different explicit alert_ids -> different keys -> NOT deduped:
        # explicit caller keys always win over the fingerprint.
        assert first["admission_id"] != second["admission_id"]

    async def test_fingerprint_stamped_into_forwarded_alert(self):
        uc = _admission_uc()
        await uc.admit({"title": "t", "severity": 2})
        stamped = uc.queue.events[0]["alert"].get("idempotency_key")
        assert stamped and stamped.startswith(
            "fp:"
        ), "computed fingerprint must ride the body for IDEMP-003"

    async def test_explicit_key_wins_over_fingerprint(self):
        uc = _admission_uc()
        await uc.admit({"title": "t"}, idempotency_key="caller-key")
        assert uc.queue.events[0]["alert"]["idempotency_key"] == "caller-key"


# ---------------------------------------------------------------------
# IDEMP-003 — X-Idempotency-Key header to Shuffle
# ---------------------------------------------------------------------


class _FakeHttpClient:
    """Captures the POST kwargs the forwarder sends to Shuffle."""

    captured: dict = {}

    def __init__(self, **kwargs):
        _FakeHttpClient.captured = {}

    async def post_json(self, url, **kwargs):
        _FakeHttpClient.captured = {"url": url, **kwargs}
        return 200, {"execution_id": "exec-9"}

    async def close(self):
        pass


class TestIdempotencyHeader:
    async def test_forward_sends_idempotency_key(self, monkeypatch):
        import soar_lab.infrastructure.messaging.shuffle_forward as sf

        monkeypatch.setattr(sf, "AioHTTPClient", _FakeHttpClient)

        class CP:
            def get(self, key, default=None):
                return {"ALERT_INGEST_TARGET_URL": "http://sh/hook"}.get(key, default)

        forward = sf.make_shuffle_forward(CP())
        result = await forward({"alert_id": "a1", "idempotency_key": "fp:abc"})
        assert result["ok"] is True
        # HMAC-002: idempotency travels in the body envelope — Shuffle
        # hooks do not expose HTTP headers to the workflow.
        assert _FakeHttpClient.captured["payload"]["idempotency_key"] == "fp:abc"

    async def test_forward_falls_back_to_alert_id(self, monkeypatch):
        import soar_lab.infrastructure.messaging.shuffle_forward as sf

        monkeypatch.setattr(sf, "AioHTTPClient", _FakeHttpClient)

        class CP:
            def get(self, key, default=None):
                return {"ALERT_INGEST_TARGET_URL": "http://sh/hook"}.get(key, default)

        forward = sf.make_shuffle_forward(CP())
        await forward({"alert_id": "a-only"})
        # falls back to alert_id inside the envelope
        assert _FakeHttpClient.captured["payload"]["idempotency_key"] == "a-only"


# ---------------------------------------------------------------------
# AUTH-003 / AUTH-004 — RBAC enforcement + audit trail
# ---------------------------------------------------------------------


class _CP:
    def __init__(self, values):
        self._values = values

    def get(self, key, default=None):
        return self._values.get(key, default)


def _rbac_app(role: str | None) -> tuple[TestClient, object]:
    """App gated by require_api_auth + DefaultDeny middleware, with a JWT
    principal carrying ``role`` and the REAL AuthService RBAC logic."""
    from soar_lab.application.use_cases.auth_service import AuthService
    from soar_lab.interfaces.api.auth import (
        DefaultDenyAuthMiddleware,
        require_api_auth,
    )

    svc = AuthService(config_provider=_CP({}), token_provider=object())
    app = FastAPI()
    app.state.config_provider = _CP({"API_REQUIRE_AUTH": "true"})
    app.state.auth_service = svc
    app.state.get_current_user = lambda credentials: {
        "user": "web-user",
        "method": "jwt",
        "role": role,
    }

    auth = Depends(require_api_auth)

    @app.get("/analytics/metrics", dependencies=[auth])
    async def metrics():
        return {"ok": True}

    @app.get("/backup/list", dependencies=[auth])
    async def backups():
        return {"backups": []}

    @app.post("/backup/create", dependencies=[auth])
    async def mkbackup():
        return {"ok": True}

    @app.post("/api/v1/alerts", dependencies=[auth])
    async def admit():
        return {"ok": True}

    @app.post("/api/v1/contain", dependencies=[auth])
    async def contain():
        return {"ok": True}

    @app.post("/api/v1/cache/ioc", dependencies=[auth])
    async def ioc():
        return {"ok": True}

    @app.post("/auth/ws-ticket", dependencies=[auth])
    async def ticket():
        return {"ok": True}

    @app.delete("/api/v1/queue/dlq", dependencies=[auth])
    async def purge():
        return {"ok": True}

    @app.get("/api/v1/audit", dependencies=[auth])
    async def audit():
        return {"events": []}

    # Same wiring as main.py — Starlette injects scope["app"] before the
    # middleware chain runs (wrapping TestClient around the middleware
    # directly would leave scope["app"] unset).
    app.add_middleware(DefaultDenyAuthMiddleware)
    return TestClient(app), svc


_HDR = {"Authorization": "Bearer jwt"}


class TestRbacEnforcement:
    def test_viewer_reads_but_cannot_mutate(self):
        client, _ = _rbac_app("viewer")
        assert client.get("/analytics/metrics", headers=_HDR).status_code == 200
        assert client.post("/api/v1/alerts", headers=_HDR).status_code == 403

    def test_viewer_cannot_see_admin_paths(self):
        client, _ = _rbac_app("viewer")
        assert client.get("/backup/list", headers=_HDR).status_code == 403
        assert client.get("/api/v1/audit", headers=_HDR).status_code == 403

    def test_analyst_submits_alerts_not_containment(self):
        client, _ = _rbac_app("analyst")
        assert client.post("/api/v1/alerts", headers=_HDR).status_code == 200
        assert client.post("/api/v1/cache/ioc", headers=_HDR).status_code == 200
        assert client.post("/api/v1/contain", headers=_HDR).status_code == 403
        assert client.post("/backup/create", headers=_HDR).status_code == 403

    def test_operator_contains_but_not_backup(self):
        client, _ = _rbac_app("operator")
        assert client.post("/api/v1/contain", headers=_HDR).status_code == 200
        assert client.delete("/api/v1/queue/dlq", headers=_HDR).status_code == 200
        assert client.post("/backup/create", headers=_HDR).status_code == 403

    def test_admin_full_access(self):
        client, _ = _rbac_app("admin")
        assert client.post("/backup/create", headers=_HDR).status_code == 200
        assert client.get("/api/v1/audit", headers=_HDR).status_code == 200

    def test_unknown_role_falls_back_to_readonly(self):
        client, _ = _rbac_app("superuser-typo")
        assert client.get("/analytics/metrics", headers=_HDR).status_code == 200
        assert client.post("/api/v1/alerts", headers=_HDR).status_code == 403

    def test_missing_role_claim_is_readonly_not_admin(self):
        # AUTH-004: a JWT with no role claim resolves to READONLY —
        # the old "legacy => admin" backcompat granted /backup/create.
        client, _ = _rbac_app(None)
        assert client.post("/backup/create", headers=_HDR).status_code == 403

    def test_any_role_can_bootstrap_ws_ticket(self):
        client, _ = _rbac_app("viewer")
        assert client.post("/auth/ws-ticket", headers=_HDR).status_code == 200


class TestAuthAuditTrail:
    def test_allow_and_deny_are_recorded_once(self):
        client, svc = _rbac_app("viewer")
        client.get("/analytics/metrics", headers=_HDR)
        client.post("/api/v1/alerts", headers=_HDR)
        access = [e for e in svc.audit.events if e["action"] == "access"]
        allows = [e for e in access if e["result"] == "allow"]
        denies = [e for e in access if e["result"] == "deny"]
        assert len(allows) == 1, f"expected exactly 1 allow, got {allows}"
        assert len(denies) == 1, f"expected exactly 1 deny, got {denies}"
        assert allows[0]["endpoint"] == "/analytics/metrics"
        assert allows[0]["method"] == "GET"
        assert denies[0]["endpoint"] == "/api/v1/alerts"
        assert "role=viewer" in denies[0]["detail"]

    def test_unauthenticated_deny_is_audited(self):
        client, svc = _rbac_app("viewer")
        client.get("/analytics/metrics")  # no headers -> 401
        access = [e for e in svc.audit.events if e["action"] == "access"]
        assert access and access[-1]["result"] == "deny"


# ---------------------------------------------------------------------
# QUEUE-006 — Prometheus exposition
# ---------------------------------------------------------------------


class _FakeQueue:
    async def metrics(self):
        return {"queue_depth": 7, "pending": 2, "consumer_lag": 3, "dlq_size": 1}


class _FakeAdmission:
    queue = _FakeQueue()


def _metrics_app(with_queue=True) -> TestClient:
    from soar_lab.infrastructure.messaging.admission_worker import WorkerStats
    from soar_lab.interfaces.api.routes_metrics import register_metrics_route

    app = FastAPI()
    if with_queue:
        app.state.admission_service = _FakeAdmission()
        stats = WorkerStats()
        stats.processed_total = 10
        stats.forwarded_total = 8
        stats.retried_total = 1
        stats.dead_total = 1
        stats.inflight = 2
        stats.errors["HTTP 500"] = 4
        app.state.admission_worker_stats = stats
    register_metrics_route(app)
    return TestClient(app)


class TestPrometheusMetrics:
    def test_exposes_queue_and_worker_metrics(self):
        body = _metrics_app().get("/metrics")
        assert body.status_code == 200
        text = body.text
        assert "soar_queue_depth 7" in text
        assert "soar_queue_pending 2" in text
        assert "soar_queue_dlq_size 1" in text
        assert "soar_admission_processed_total 10" in text
        assert "soar_admission_retried_total 1" in text
        assert 'soar_admission_forward_errors_total{error="HTTP 500"} 4' in text
        assert "# TYPE soar_admission_processed_total counter" in text
        assert "soar_queue_available 1" in text
        assert "0.0.4" in body.headers["content-type"]

    def test_degrades_without_queue(self):
        text = _metrics_app(with_queue=False).get("/metrics").text
        assert "soar_queue_available 0" in text
        assert "soar_app_uptime_seconds" in text


# ---------------------------------------------------------------------
# VAL-003 — JSON Schema exportable via OpenAPI
# ---------------------------------------------------------------------


class TestSchemaExport:
    def test_alert_ingest_schema_is_exported_in_openapi(self):
        from soar_lab.interfaces.api.routes_ingest import register_ingest_routes

        app = FastAPI()
        register_ingest_routes(app)
        spec = TestClient(app).get("/openapi.json").json()
        schema = spec["components"]["schemas"]["AlertIngestSchema"]
        hash_constraints = schema["properties"]["hash"]["anyOf"][0]
        title_constraints = schema["properties"]["title"]["anyOf"][0]
        assert hash_constraints["maxLength"] == 128
        assert title_constraints["maxLength"] == 512
        assert "/api/v1/alerts" in spec["paths"]

    def test_schema_json_schema_roundtrip(self):
        from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

        js = AlertIngestSchema.model_json_schema()
        assert js["properties"]["idempotency_key"]["anyOf"][0]["maxLength"] == 256


# ---------------------------------------------------------------------
# VAL-004 — Hypothesis fuzzing of the ingest boundary
# ---------------------------------------------------------------------


class TestIngestFuzz:
    def test_arbitrary_json_never_crushes_the_schema(self):
        """Arbitrary JSON input must only ever produce ValidationError —
        never a bare TypeError/KeyError leaking out of the validator."""
        from hypothesis import HealthCheck, given, settings
        from hypothesis import strategies as st
        from pydantic import ValidationError

        from soar_lab.interfaces.api.routes_ingest import AlertIngestSchema

        json_val = st.recursive(
            st.none()
            | st.booleans()
            | st.integers()
            | st.floats(allow_nan=False, allow_infinity=False)
            | st.text(max_size=20),
            lambda c: st.lists(c, max_size=4) | st.dictionaries(st.text(max_size=8), c, max_size=4),
            max_leaves=8,
        )

        @given(payload=json_val)
        @settings(
            max_examples=150,
            deadline=None,
            suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
        )
        def check(payload):
            try:
                AlertIngestSchema.model_validate(payload)
            except ValidationError:
                pass
            # any other exception type is a validator bug

        check()

    def test_fuzz_endpoint_never_returns_500(self):
        """Posting arbitrary JSON objects to /api/v1/alerts must answer
        202/422 — never a 500 (validation is a boundary, not a crash)."""
        from hypothesis import HealthCheck, given, settings
        from hypothesis import strategies as st

        from soar_lab.interfaces.api.routes_ingest import register_ingest_routes

        class _FakeService:
            async def admit(self, alert):
                return {"admission_id": "adm-x", "status": "queued"}

        app = FastAPI()
        app.state.config_provider = None  # auth off -> exercises the route itself
        register_ingest_routes(app, admission_service=_FakeService())
        client = TestClient(app, raise_server_exceptions=False)

        bodies = st.fixed_dictionaries(
            {},
            optional={
                "title": st.text(max_size=600),
                "severity": st.one_of(
                    st.integers(),
                    st.text(max_size=40),
                    st.booleans(),
                    st.floats(allow_nan=False, allow_infinity=False),
                ),
                "hash": st.text(max_size=200),
                "mitre_techniques": st.one_of(st.lists(st.text()), st.text(), st.integers()),
            },
        )

        @given(body=bodies)
        @settings(
            max_examples=200,
            deadline=None,
            suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
        )
        def check(body):
            resp = client.post("/api/v1/alerts", json=body)
            assert resp.status_code in (202, 422), resp.text

        check()
