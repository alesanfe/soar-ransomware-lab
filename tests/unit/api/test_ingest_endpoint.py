"""PERF-001: POST /api/v1/alerts endpoint contract.

- 202 Accepted with {admission_id, status, status_url}
- 422 on non-object JSON body
- 404 on unknown admission_id
- auth-gated like other mutating routes when API_REQUIRE_AUTH=true
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from soar_lab.application.use_cases.alert_admission import AlertAdmissionUseCase
from soar_lab.interfaces.api.routes_ingest import register_ingest_routes


class FakeQueue:
    async def enqueue(self, event):
        return "e-1"

    async def depth(self):
        return 0

    async def read(self, *a):
        return []

    async def ack(self, *a):
        pass

    async def dead_letter(self, *a):
        pass

    async def ensure_group(self, *a):
        pass


class FakeStore:
    def __init__(self):
        self.records = {}
        self.by_key = {}

    async def create(self, record):
        self.records[record["admission_id"]] = dict(record)

    async def update(self, aid, fields):
        self.records[aid].update(fields)

    async def get(self, aid):
        return self.records.get(aid)

    async def find_by_key(self, key):
        return self.by_key.get(key)

    async def bind_key(self, key, aid):
        self.by_key[key] = aid

    async def try_bind_key(self, key, aid):
        if key in self.by_key:
            return self.by_key[key]
        self.by_key[key] = aid
        return None

    async def unbind_key(self, key, aid):
        if self.by_key.get(key) == aid:
            del self.by_key[key]


def _client(require_auth: bool = False) -> TestClient:
    app = FastAPI()
    app.state.config_provider = _Cfg(require_auth)
    app.state.get_current_user = None
    store = FakeStore()
    uc = AlertAdmissionUseCase(queue=FakeQueue(), store=store)
    register_ingest_routes(app, admission_service=uc)
    return TestClient(app)


class _Cfg:
    def __init__(self, require_auth):
        self.require_auth = require_auth

    def get(self, key, default=None):
        if key == "API_REQUIRE_AUTH":
            return "true" if self.require_auth else "false"
        if key == "INTERNAL_SERVICE_TOKEN":
            return "svc-token-123"
        return default


class TestAdmitEndpoint:
    def test_post_alert_returns_202(self):
        client = _client()
        resp = client.post("/api/v1/alerts", json={"alert_id": "alr-1", "severity": 3})
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "queued"
        assert body["admission_id"].startswith("adm-")
        assert body["status_url"].endswith(body["admission_id"])

    def test_post_non_object_returns_422(self):
        client = _client()
        resp = client.post("/api/v1/alerts", json=[1, 2, 3])
        assert resp.status_code == 422

    def test_status_unknown_returns_404(self):
        client = _client()
        assert client.get("/api/v1/alerts/adm-nope").status_code == 404

    def test_status_roundtrip(self):
        client = _client()
        body = client.post("/api/v1/alerts", json={"alert_id": "alr-rt"}).json()
        resp = client.get(body["status_url"])
        assert resp.status_code == 200
        assert resp.json()["alert_id"] == "alr-rt"

    def test_saturated_queue_returns_503_retry_after(self):
        """PERF-003: backpressure surfaces as 503 + Retry-After."""

        class SaturatedQueue(FakeQueue):
            async def depth(self):
                return 10

        app = FastAPI()
        app.state.config_provider = _Cfg(False)
        app.state.get_current_user = None
        uc = AlertAdmissionUseCase(queue=SaturatedQueue(), store=FakeStore(), max_queue_depth=5)
        register_ingest_routes(app, admission_service=uc)
        resp = TestClient(app).post("/api/v1/alerts", json={"alert_id": "alr-1"})
        assert resp.status_code == 503
        assert resp.headers["Retry-After"] == "5"
        assert "saturated" in resp.json()["detail"]


class TestAuthGate:
    def test_no_token_returns_401(self):
        client = _client(require_auth=True)
        resp = client.post("/api/v1/alerts", json={"alert_id": "alr-1"})
        assert resp.status_code == 401

    def test_service_token_returns_202(self):
        client = _client(require_auth=True)
        resp = client.post(
            "/api/v1/alerts",
            json={"alert_id": "alr-1"},
            headers={"X-Service-Token": "svc-token-123"},
        )
        assert resp.status_code == 202


class RichQueue(FakeQueue):
    """FakeQueue + the DLQ/metrics surface used by queue endpoints."""

    def __init__(self):
        self.purged = 7
        self.redrive_ok = True

    async def dlq_size(self):
        return 2

    async def dlq_list(self, count=50):
        return [{"dlq_entry_id": "9-1", "reason": "r", "payload": {"a": 1}}]

    async def dlq_redrive(self, entry_id):
        return self.redrive_ok

    async def dlq_purge(self):
        return self.purged

    async def metrics(self, group=None):
        return {"queue_depth": 3, "dlq_size": 2, "consumer_lag": 1, "pending": 0}


def _client_with_queue(queue=None, require_auth=False) -> TestClient:
    app = FastAPI()
    app.state.config_provider = _Cfg(require_auth)
    app.state.get_current_user = None
    uc = AlertAdmissionUseCase(queue=queue or RichQueue(), store=FakeStore())
    register_ingest_routes(app, admission_service=uc)
    return TestClient(app)


class TestServiceGuards:
    def test_no_service_returns_503(self):
        app = FastAPI()
        app.state.config_provider = _Cfg(False)
        app.state.get_current_user = None
        register_ingest_routes(app, admission_service=None)
        resp = TestClient(app).post("/api/v1/alerts", json={"alert_id": "x"})
        assert resp.status_code == 503

    def test_service_without_queue_returns_503(self):
        class NoQueue:
            async def admit(self, alert):
                return {"ok": True}

        app = FastAPI()
        app.state.config_provider = _Cfg(False)
        app.state.get_current_user = None
        register_ingest_routes(app, admission_service=NoQueue())
        assert TestClient(app).get("/api/v1/queue/metrics").status_code == 503


class TestQueueEndpoints:
    def test_admit_validation_error_returns_422(self):
        from soar_lab.application.use_cases.alert_admission import AdmissionValidationError

        class RejectingSvc:
            async def admit(self, alert):
                raise AdmissionValidationError("bad payload")

        app = FastAPI()
        app.state.config_provider = _Cfg(False)
        app.state.get_current_user = None
        register_ingest_routes(app, admission_service=RejectingSvc())
        resp = TestClient(app).post("/api/v1/alerts", json={"alert_id": "x"})
        assert resp.status_code == 422
        assert "bad payload" in resp.json()["detail"]

    def test_dlq_list(self):
        resp = _client_with_queue().get("/api/v1/queue/dlq")
        assert resp.status_code == 200
        body = resp.json()
        assert body["size"] == 2
        assert body["entries"][0]["dlq_entry_id"] == "9-1"

    def test_dlq_redrive_success(self):
        resp = _client_with_queue().post("/api/v1/queue/dlq/redrive", json={"dlq_entry_id": "9-1"})
        assert resp.status_code == 200
        assert resp.json()["redriven"] is True

    def test_dlq_redrive_missing_returns_404(self):
        app = FastAPI()
        app.state.config_provider = _Cfg(False)
        app.state.get_current_user = None
        q = RichQueue()
        q.redrive_ok = False
        uc = AlertAdmissionUseCase(queue=q, store=FakeStore())
        register_ingest_routes(app, admission_service=uc)
        resp = TestClient(app).post("/api/v1/queue/dlq/redrive", json={"dlq_entry_id": "9-x"})
        assert resp.status_code == 404

    def test_dlq_purge(self):
        resp = _client_with_queue().delete("/api/v1/queue/dlq")
        assert resp.status_code == 200
        assert resp.json()["purged"] == 7

    def test_queue_metrics(self):
        resp = _client_with_queue().get("/api/v1/queue/metrics")
        assert resp.status_code == 200
        assert resp.json()["queue_depth"] == 3


class TestAuditAndConfig:
    def test_audit_trail_empty_without_auth_service(self):
        resp = _client_with_queue().get("/api/v1/audit")
        assert resp.status_code == 200
        assert resp.json() == {"size": 0, "events": []}

    def test_audit_trail_returns_events(self):
        app = FastAPI()
        app.state.config_provider = _Cfg(False)
        app.state.get_current_user = None
        register_ingest_routes(
            app, admission_service=AlertAdmissionUseCase(queue=RichQueue(), store=FakeStore())
        )
        from soar_lab.application.use_cases.auth_service import AuthService

        svc = AuthService()
        svc.audit.record("access", principal="p", endpoint="/x")
        app.state.auth_service = svc
        resp = TestClient(app).get("/api/v1/audit")
        assert resp.status_code == 200
        assert resp.json()["size"] == 1

    def test_config_dump_no_provider(self):
        app = FastAPI()
        app.state.get_current_user = None
        app.state.config_provider = None  # forces the svc-is-None branch
        register_ingest_routes(
            app, admission_service=AlertAdmissionUseCase(queue=RichQueue(), store=FakeStore())
        )
        resp = TestClient(app).get("/api/v1/config")
        assert resp.json() == {"values": {}, "redacted": True}

    def test_config_dump_provider_without_get_all(self):
        app = FastAPI()
        app.state.get_current_user = None

        class BareCfg:
            def get(self, k, d=None):
                return "false" if k == "API_REQUIRE_AUTH" else d

        app.state.config_provider = BareCfg()
        register_ingest_routes(
            app, admission_service=AlertAdmissionUseCase(queue=RichQueue(), store=FakeStore())
        )
        resp = TestClient(app).get("/api/v1/config")
        assert resp.json() == {"values": {}, "redacted": True}

    def test_config_dump_with_values(self):
        app = FastAPI()
        app.state.get_current_user = None

        class FullCfg(_Cfg):
            def get_all(self):
                return {"API_REQUIRE_AUTH": "false", "SETTING_X": "y"}

        app.state.config_provider = FullCfg(False)
        register_ingest_routes(
            app, admission_service=AlertAdmissionUseCase(queue=RichQueue(), store=FakeStore())
        )
        resp = TestClient(app).get("/api/v1/config")
        assert resp.status_code == 200
        assert resp.json()["redacted"] is True
        assert resp.json()["values"]["SETTING_X"] == "y"
