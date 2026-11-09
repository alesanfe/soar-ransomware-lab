"""Branch coverage for routes_services: IOC cache endpoint and the
enforce-mode containment guards/failure paths."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from soar_lab.interfaces.api.models import ContainmentRequest
from soar_lab.interfaces.api.routes_services import (
    _enforce_containment,
    register_service_routes,
)


class _Cfg:
    def get(self, key, default=None):
        return "false" if key == "API_REQUIRE_AUTH" else default


def _app(**state) -> FastAPI:
    app = FastAPI()
    app.state.config_provider = _Cfg()
    app.state.get_current_user = None
    for k, v in state.items():
        setattr(app.state, k, v)
    register_service_routes(app)
    return app


class TestIocCacheEndpoint:
    def test_no_redis_returns_failure(self):
        app = _app(redis_client=None)
        resp = TestClient(app).post("/api/v1/cache/ioc", json={"key": "k", "value": "v"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "not available" in body["message"]

    def test_set_success(self):
        class FakeRedis:
            def __init__(self):
                self.calls = []

            def set(self, k, v, ex=None):
                self.calls.append((k, v, ex))

        redis = FakeRedis()
        app = _app(redis_client=redis)
        resp = TestClient(app).post(
            "/api/v1/cache/ioc", json={"key": "ioc:1", "value": "x", "ttl_seconds": 60}
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert redis.calls == [("ioc:1", "x", 60)]

    def test_set_exception_returns_failure(self):
        class FailRedis:
            def set(self, *a, **k):
                raise ConnectionError("redis down")

        app = _app(redis_client=FailRedis())
        resp = TestClient(app).post("/api/v1/cache/ioc", json={"key": "k", "value": "v"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "redis down" in body["message"]


class TestEnforceContainment:
    def _request(self, **kw):
        base = {"alert_id": "a", "case_id": "c", "hostname": "h", "mode": "enforce"}
        base.update(kw)
        return ContainmentRequest(**base)

    def test_disabled_env_returns_403(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "0")
        with pytest.raises(HTTPException) as exc:
            _enforce_containment(self._request(target_container="victim_x"), _app())
        assert exc.value.status_code == 403

    def test_missing_target_returns_400(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")
        with pytest.raises(HTTPException) as exc:
            _enforce_containment(self._request(target_container=None), _app())
        assert exc.value.status_code == 400

    def test_no_docker_client_returns_503(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")
        app = _app()
        app.state.docker_client = None
        with pytest.raises(HTTPException) as exc:
            _enforce_containment(self._request(target_container="victim_x"), app)
        assert exc.value.status_code == 503

    def test_unknown_container_returns_404(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")

        class Containers:
            def get(self, name):
                raise LookupError("nope")

        class FakeDocker:
            containers = Containers()

        app = _app()
        app.state.docker_client = FakeDocker()
        with pytest.raises(HTTPException) as exc:
            _enforce_containment(self._request(target_container="victim_x"), app)
        assert exc.value.status_code == 404

    def test_non_allowlisted_container_returns_403(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")

        class FakeContainer:
            attrs = {"Config": {"Labels": {}}}

        class Containers:
            def get(self, name):
                return FakeContainer()

        class FakeDocker:
            containers = Containers()

        app = _app()
        app.state.docker_client = FakeDocker()
        with pytest.raises(HTTPException) as exc:
            _enforce_containment(self._request(target_container="not_victim"), app)
        assert exc.value.status_code == 403

    def test_infra_container_never_contained(self, monkeypatch):
        """soar_* containers can't be contained even with the victim label."""
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")

        class FakeContainer:
            attrs = {"Config": {"Labels": {"soar.victim": "true"}}}

        class Containers:
            def get(self, name):
                return FakeContainer()

        class FakeDocker:
            containers = Containers()

        app = _app()
        app.state.docker_client = FakeDocker()
        with pytest.raises(HTTPException) as exc:
            _enforce_containment(self._request(target_container="soar_es"), app)
        assert exc.value.status_code == 403


class TestEnforceFailures:
    """disconnect/pause exceptions are tolerated and logged, not fatal."""

    def _setup(self, monkeypatch, pause_fails=False, disconnect_fails=False):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")

        class FakeContainer:
            def __init__(self):
                self.paused = False

            def reload(self):
                pass

            def pause(self):
                if pause_fails:
                    raise RuntimeError("pause fail")
                self.paused = True

            attrs = {
                "Config": {"Labels": {"soar.victim": "true"}},
                "NetworkSettings": {"Networks": {"net-a": {}, "net-b": {}}},
                "State": {"Paused": False},
            }

        container = FakeContainer()

        class Net:
            def disconnect(self, c, force):
                if disconnect_fails:
                    raise RuntimeError("disconnect fail")

        class Networks:
            def get(self, name):
                return Net()

        class Containers:
            def get(self, name):
                return container

        class FakeDocker:
            containers = Containers()
            networks = Networks()

        app = _app()
        app.state.docker_client = FakeDocker()
        return app, container

    def test_disconnect_failure_tolerated(self, monkeypatch):
        app, container = self._setup(monkeypatch, disconnect_fails=True)
        resp = _enforce_containment(
            ContainmentRequest(
                alert_id="a",
                case_id="c",
                hostname="h",
                mode="enforce",
                target_container="victim_x",
            ),
            app,
        )
        # No disconnect actions recorded, but pause still ran
        assert "container_pause" in resp.actions
        assert not any(a.startswith("network_disconnect") for a in resp.actions)

    def test_pause_failure_tolerated(self, monkeypatch):
        app, container = self._setup(monkeypatch, pause_fails=True)
        resp = _enforce_containment(
            ContainmentRequest(
                alert_id="a",
                case_id="c",
                hostname="h",
                mode="enforce",
                target_container="victim_x",
            ),
            app,
        )
        assert "container_pause" not in resp.actions
        assert sorted(a for a in resp.actions if a.startswith("network_disconnect")) == [
            "network_disconnect:net-a",
            "network_disconnect:net-b",
        ]


class TestContainmentEndpointErrors:
    def test_unexpected_error_returns_500(self, monkeypatch):
        import soar_lab.interfaces.api.routes_services as rs

        monkeypatch.setattr(rs, "_enforce_containment", Mock(side_effect=RuntimeError("kaboom")))
        app = _app()
        resp = TestClient(app).post(
            "/api/v1/contain",
            json={
                "alert_id": "a",
                "case_id": "c",
                "hostname": "h",
                "mode": "enforce",
                "target_container": "victim_x",
            },
        )
        assert resp.status_code == 500
        assert "kaboom" in resp.json()["detail"]


class TestApprovalFlow:
    """Authorization-scope regression tests for the F4 approval flow.

    BUG-APP-01 (scope escalation): ``_approval_granted`` only checks
    ``record["status"] == STATUS_APPROVED`` — it never compares the
    resubmitted payload with the one that was approved. An approval
    granted for ``victim_one`` is a bearer token that authorizes
    containment of ANY other target.

    BUG-APP-02 (replay): an approved record is never consumed — the same
    ``approval_id`` authorizes unlimited executions of the approved
    payload (and, via BUG-APP-01, of anything else). ``get()`` only
    expires PENDING records, so an APPROVED id lives forever.

    Both currently fail: the resubmit path executes payloads it should
    re-park.
    """

    class _ApprovalCfg:
        def get(self, key, default=None):
            if key == "API_REQUIRE_AUTH":
                return "false"
            if key == "SOAR_CONTAIN_REQUIRE_APPROVAL":
                return "1"
            return default

    def _app(self):
        app = FastAPI()
        app.state.config_provider = self._ApprovalCfg()
        app.state.get_current_user = None
        register_service_routes(app)
        return app

    _REQ_A = {
        "alert_id": "alert-1",
        "case_id": "case-1",
        "hostname": "victim_one",
        "mode": "simulated",
    }
    _REQ_B = {
        "alert_id": "alert-2",
        "case_id": "case-2",
        "hostname": "victim_two",
        "mode": "simulated",
    }

    def _park(self, client, req):
        resp = client.post("/api/v1/contain", json=req)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending_approval"
        return body["approval_id"]

    def test_approved_id_does_not_authorize_different_payload(self):
        """An approval for request A must not execute request B."""
        client = TestClient(self._app())
        aid = self._park(client, self._REQ_A)
        client.post(f"/api/v1/contain/{aid}/approve")

        resp = client.post("/api/v1/contain", json={**self._REQ_B, "approval_id": aid})
        body = resp.json()
        assert (
            body["status"] == "pending_approval"
        ), f"unapproved payload executed with borrowed approval_id: {body}"
        assert body["approval_id"] != aid

    def test_approved_id_is_single_use(self):
        """A consumed approval cannot replay the same payload.

        The resubmit path executes when the record is APPROVED but not
        yet spent (approve decided at store level, e.g. the analyst UI
        decided without triggering execution). First resubmit runs and
        burns the ticket; the second must re-park, not re-execute.
        """
        app = self._app()
        client = TestClient(app)
        aid = self._park(client, self._REQ_A)
        app.state.containment_approvals.decide(aid, approve=True, decided_by="analyst")

        first = client.post("/api/v1/contain", json={**self._REQ_A, "approval_id": aid})
        assert first.json()["status"] != "pending_approval"

        replay = client.post("/api/v1/contain", json={**self._REQ_A, "approval_id": aid})
        assert replay.json()["status"] == "pending_approval", f"approval replayed: {replay.json()}"

    def test_approve_endpoint_consumes_the_approval(self):
        """Approving executes the stored request; a resubmit afterwards
        must NOT execute it a second time — the approval is spent by
        the analyst-driven execution already."""
        client = TestClient(self._app())
        aid = self._park(client, self._REQ_A)
        approve = client.post(f"/api/v1/contain/{aid}/approve")
        assert approve.status_code == 200

        resubmit = client.post("/api/v1/contain", json={**self._REQ_A, "approval_id": aid})
        assert (
            resubmit.json()["status"] == "pending_approval"
        ), f"double execution via resubmit after approve: {resubmit.json()}"
