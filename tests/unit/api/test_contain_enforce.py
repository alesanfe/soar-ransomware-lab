#!/usr/bin/env python3
"""Unit tests for real containment (mode='enforce') — VAL-010.

Covers: enforce flag gating, victim allowlisting, real network
disconnect + pause via the docker client, before/after evidence, and
error paths (missing target, unknown container, unavailable client).
"""

from __future__ import annotations

from unittest.mock import Mock

from fastapi.testclient import TestClient

from soar_lab.interfaces.api.main import create_app


class FakeContainer:
    def __init__(self, name, labels=None, networks=None):
        self.name = name
        self.attrs = {
            "Config": {"Labels": labels or {}},
            "NetworkSettings": {"Networks": {n: {} for n in (networks or [])}},
            "State": {"Paused": False, "Running": True},
        }
        self.paused = False

    def reload(self):
        self.attrs["State"]["Paused"] = self.paused

    def pause(self):
        self.paused = True


class FakeNetwork:
    def __init__(self, name):
        self.name = name
        self.disconnected = []

    def disconnect(self, container, force=False):
        self.disconnected.append((container.name, force))
        container.attrs["NetworkSettings"]["Networks"].pop(self.name, None)


class FakeDocker:
    def __init__(self, containers=None, networks=None):
        self._containers = containers or {}
        self._networks = networks or {}
        self.containers = Mock()
        self.containers.get = self._get_container
        self.networks = Mock()
        self.networks.get = self._get_network

    def _get_container(self, name):
        if name not in self._containers:
            raise KeyError(name)
        return self._containers[name]

    def _get_network(self, name):
        if name not in self._networks:
            self._networks[name] = FakeNetwork(name)
        return self._networks[name]


def _app(docker_client=None):
    cp = Mock()
    cp.get = lambda k, d=None: {
        "API_TITLE": "t",
        "API_DESCRIPTION": "d",
        "API_VERSION": "1.0.0",
        "API_DOCS_ENABLED": "false",
        "API_REQUIRE_AUTH": "off",
    }.get(k, d)
    cp.get_service_urls = dict
    auth = Mock()
    auth.verify_jwt_token.return_value = {"user": "admin", "role": "admin"}
    return create_app(
        config_provider=cp,
        auth_service=auth,
        docker_client=docker_client,
        system_metrics=Mock(),
        health_service=Mock(),
        analytics_service=Mock(),
        backup_service=Mock(),
        test_service=Mock(),
        storage=Mock(),
        path_service=Mock(),
        log_reader=Mock(),
    )


def _payload(**kw):
    base = {
        "alert_id": "a1",
        "case_id": "c1",
        "hostname": "victim-host",
        "mode": "enforce",
        "target_container": "victim_box",
    }
    base.update(kw)
    return base


class TestEnforceFlag:
    def test_enforce_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("SOAR_CONTAIN_ENFORCE", raising=False)
        client = TestClient(_app(docker_client=FakeDocker()))
        resp = client.post("/api/v1/contain", json=_payload())
        assert resp.status_code == 403
        assert "disabled" in resp.json()["detail"]

    def test_simulated_mode_still_works(self, monkeypatch):
        monkeypatch.delenv("SOAR_CONTAIN_ENFORCE", raising=False)
        client = TestClient(_app())
        resp = client.post("/api/v1/contain", json=_payload(mode="simulated"))
        assert resp.status_code == 200
        assert resp.json()["status"] == "simulated"


class TestEnforceExecution:
    def test_enforce_disconnects_and_pauses(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")
        victim = FakeContainer(
            "victim_box",
            labels={"soar.victim": "true"},
            networks=["soar_net", "ti_net"],
        )
        docker = FakeDocker(containers={"victim_box": victim})
        client = TestClient(_app(docker_client=docker))

        resp = client.post("/api/v1/contain", json=_payload())
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "enforced"
        assert "network_disconnect:soar_net" in body["actions"]
        assert "network_disconnect:ti_net" in body["actions"]
        assert "container_pause" in body["actions"]
        ev = body["evidence"]
        assert ev["before"]["networks"] == ["soar_net", "ti_net"]
        assert ev["after"]["networks"] == []
        assert ev["after"]["paused"] is True
        assert victim.paused

    def test_prefix_allowlist_without_label(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")
        victim = FakeContainer("victim_nolabel", networks=["soar_net"])
        docker = FakeDocker(containers={"victim_nolabel": victim})
        client = TestClient(_app(docker_client=docker))
        resp = client.post("/api/v1/contain", json=_payload(target_container="victim_nolabel"))
        assert resp.status_code == 200
        assert resp.json()["status"] == "enforced"

    def test_infrastructure_container_rejected(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")
        docker = FakeDocker(containers={"soar_redis": FakeContainer("soar_redis")})
        client = TestClient(_app(docker_client=docker))
        resp = client.post("/api/v1/contain", json=_payload(target_container="soar_redis"))
        assert resp.status_code == 403
        assert "not an allowlisted victim" in resp.json()["detail"]

    def test_random_container_rejected(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")
        docker = FakeDocker(containers={"random_box": FakeContainer("random_box")})
        client = TestClient(_app(docker_client=docker))
        resp = client.post("/api/v1/contain", json=_payload(target_container="random_box"))
        assert resp.status_code == 403


class TestEnforceErrors:
    def test_missing_target_container(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")
        client = TestClient(_app(docker_client=FakeDocker()))
        resp = client.post("/api/v1/contain", json=_payload(target_container=None))
        assert resp.status_code == 400

    def test_unknown_container(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")
        client = TestClient(_app(docker_client=FakeDocker()))
        resp = client.post("/api/v1/contain", json=_payload())
        assert resp.status_code == 404

    def test_no_docker_client(self, monkeypatch):
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")
        client = TestClient(_app(docker_client=None))
        resp = client.post("/api/v1/contain", json=_payload())
        assert resp.status_code == 503

    def test_empty_prefix_env_does_not_bypass_allowlist(self, monkeypatch):
        """Bug: SOAR_CONTAIN_ALLOW_PREFIX='' made name.startswith('') True
        for every container — the victim allowlist was fully bypassed."""
        monkeypatch.setenv("SOAR_CONTAIN_ENFORCE", "1")
        monkeypatch.setenv("SOAR_CONTAIN_ALLOW_PREFIX", "")
        evil = FakeContainer("random_container", labels={})
        docker = FakeDocker(containers={"random_container": evil})
        client = TestClient(_app(docker_client=docker))

        resp = client.post("/api/v1/contain", json=_payload(target_container="random_container"))
        assert resp.status_code == 403


def test_service_token_nonascii_returns_false_not_crash():
    """Bug: hmac.compare_digest on str raises TypeError for non-ASCII
    input — a non-ASCII X-Service-Token (raw socket / latin-1 header)
    crashed _service_token_scope instead of returning None."""
    from soar_lab.interfaces.api.auth import _service_token_scope

    request = Mock()
    request.headers = {"X-Service-Token": "ñoño€"}
    cp = Mock()
    cp.get = lambda k, d=None: {"INTERNAL_SERVICE_TOKEN": "s3cret"}.get(k, d)
    assert _service_token_scope(request, cp) == (None, False)


def test_service_token_prev_slot_grants_scope_with_grace_flag():
    """S2: during rotation the *_PREV secret authenticates but reports
    rotation_grace=True so the audit trail flags stale-credential use."""
    from soar_lab.interfaces.api.auth import _service_token_scope

    request = Mock()
    request.headers = {"X-Service-Token": "old-secret"}
    cp = Mock()
    cp.get = lambda k, d=None: {
        "INTERNAL_SERVICE_TOKEN": "new-secret",
        "INTERNAL_SERVICE_TOKEN_PREV": "old-secret",
    }.get(k, d)
    assert _service_token_scope(request, cp) == ("internal", True)


def test_service_token_prev_not_accepted_when_slot_empty():
    """S2: once the *_PREV slot is cleared rotation is complete — the old
    secret no longer authenticates."""
    from soar_lab.interfaces.api.auth import _service_token_scope

    request = Mock()
    request.headers = {"X-Service-Token": "old-secret"}
    cp = Mock()
    cp.get = lambda k, d=None: {"INTERNAL_SERVICE_TOKEN": "new-secret"}.get(k, d)
    assert _service_token_scope(request, cp) == (None, False)
