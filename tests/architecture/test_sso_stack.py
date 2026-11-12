"""Architecture gates for the SSO overlay (docker-compose.sso.yml).

Static checks over the compose/hardened/realm sources so a regression in
the Keycloak + oauth2-proxy stack fails CI instead of surfacing in a live
drill. Mirrors tests/architecture/test_misp_stack.py conventions.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / "infra/docker/compose/docker-compose.sso.yml"
HARDENED = REPO / "infra/docker/compose/docker-compose.hardened.yml"
PROM = REPO / "infra/docker/config/prometheus.yml"
ALERTS = REPO / "infra/docker/compose/logging/alert-rules.yml"
REALM = REPO / "infra/docker/config/keycloak/soar-realm.json"
ENTRYPOINT = REPO / "infra/docker/config/keycloak/entrypoint.sh"

SSO_SERVICES = {"keycloak", "oauth2-proxy-web", "oauth2-proxy-shuffle"}


class _Loader(yaml.SafeLoader):
    """Tolerate compose-spec tags (!reset / !override)."""


def _tag(loader, suffix, node):
    if suffix == "override":
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        if isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
    return None


_Loader.add_multi_constructor("!", _tag)


def _load(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_Loader)


def _service(path: Path, name: str) -> dict:
    return _load(path)["services"][name]


def _realm() -> dict:
    return json.loads(REALM.read_text(encoding="utf-8"))


def test_all_sso_services_declared() -> None:
    services = _load(COMPOSE)["services"]
    assert SSO_SERVICES == set(services)


def test_realm_secrets_are_placeholders() -> None:
    """SSO-EVAL-002: client secret + user passwords must be placeholders
    rendered at container start, never real values in the repo."""
    realm = _realm()
    for client in realm["clients"]:
        if client["clientId"] == "soar-proxy":
            assert client["secret"] == "__OIDC_CLIENT_SECRET__"
    placeholders = {
        cred["value"]
        for u in realm["users"]
        for cred in u.get("credentials", [])
    }
    assert all(v.startswith("__") for v in placeholders)
    raw = REALM.read_text(encoding="utf-8")
    for weak in ("soar-lab-oidc-secret", "soar-admin", "soar-analyst"):
        assert weak not in raw


def test_realm_bruteforce_and_policy() -> None:
    """SSO-EVAL-001: the IdP must not ship with brute-force disabled."""
    realm = _realm()
    assert realm["bruteForceProtected"] is True
    assert realm.get("passwordPolicy")
    assert realm.get("ssoSessionIdleTimeout", 0) > 0
    assert realm["sslRequired"] == "external"


def test_compose_secrets_fail_closed() -> None:
    """No :-defaults on secret env vars — the stack must not boot with
    baked-in credentials."""
    text = COMPOSE.read_text(encoding="utf-8")
    for var in ("OIDC_CLIENT_SECRET", "OAUTH2_PROXY_COOKIE_SECRET",
                "KEYCLOAK_ADMIN_PASSWORD"):
        assert f"{var}:-" not in text, f"{var} has a default"


def test_entrypoint_renders_and_fails_closed() -> None:
    text = ENTRYPOINT.read_text(encoding="utf-8")
    for var in ("OIDC_CLIENT_SECRET", "KC_ADMIN_USER_PASS", "KC_ANALYST_USER_PASS"):
        assert var in text
    assert "exit 1" in text  # missing env → container refuses to start


def test_sso_compose_self_hardened() -> None:
    """OBS-EVAL-006: optional-overlay services carry their own hardening —
    the default-set hardened overlay must not reference image-less
    services (it breaks `docker compose config` on the default set)."""
    for name in SSO_SERVICES:
        svc = _service(COMPOSE, name)
        assert svc["cap_drop"] == ["ALL"], name
        assert "no-new-privileges:true" in svc["security_opt"], name
        pids = svc["deploy"]["resources"]["limits"]["pids"]
        assert isinstance(pids, int) and pids > 0, name


def test_proxies_readonly_rootfs() -> None:
    """oauth2-proxy is distroless/stateless — RO rootfs must be on."""
    for name in ("oauth2-proxy-web", "oauth2-proxy-shuffle"):
        assert _service(COMPOSE, name)["read_only"] is True, name


def test_all_host_ports_loopback_bound() -> None:
    for name in SSO_SERVICES:
        for mapping in _service(COMPOSE, name).get("ports", []):
            host = str(mapping).split(":")[0]
            assert host == "127.0.0.1", f"{name}: {mapping}"


def test_keycloak_healthcheck_is_app_level() -> None:
    hc = " ".join(_service(COMPOSE, "keycloak")["healthcheck"]["test"])
    assert "/health/ready" in hc
    assert "200" in hc  # asserts a real 200, not just an open port


def test_keycloak_depends_chain_and_proxies_wait_for_it() -> None:
    for name in ("oauth2-proxy-web", "oauth2-proxy-shuffle"):
        dep = _service(COMPOSE, name)["depends_on"]
        assert dep["keycloak"]["condition"] == "service_healthy"


def test_sso_has_prometheus_coverage() -> None:
    text = PROM.read_text(encoding="utf-8")
    assert "keycloak:9000/health/ready" in text
    assert "oauth2-proxy-web:8443/ping" in text
    assert "oauth2-proxy-shuffle:8443/ping" in text


def test_everything_is_tls_only() -> None:
    # SSO-EVAL-004: no plain-HTTP listener survives the migration.
    ep = ENTRYPOINT.read_text(encoding="utf-8")
    cy = COMPOSE.read_text(encoding="utf-8")
    assert "--http-enabled=false" in ep
    assert "kc.sh start \\" in ep  # start-dev forces the HTTP listener on
    assert "OAUTH2_PROXY_HTTPS_ADDRESS" in cy
    assert "OAUTH2_PROXY_TLS_CERT_FILE" in cy
    assert 'OAUTH2_PROXY_COOKIE_SECURE: "true"' in cy
    assert "http://keycloak:8080" not in cy
    assert "http://localhost:8087" not in cy


def test_oidc_backchannel_verifies_lab_ca() -> None:
    cy = COMPOSE.read_text(encoding="utf-8")
    assert "OAUTH2_PROXY_PROVIDER_CA_FILES" in cy
    assert "certs/ca.crt" in cy
    assert "certs/keycloak.crt" in cy
    assert "certs/oauth2-proxy.crt" in cy


def test_refresh_token_rotation_enabled() -> None:
    # OAuth2 BCP / NIST 800-63C — refresh tokens rotate on every use.
    raw = REALM.read_text(encoding="utf-8")
    assert '"revokeRefreshToken": true' in raw
    assert '"refreshTokenMaxReuse": 0' in raw


def test_mfa_required_action_on_all_users() -> None:
    # NIST 800-63B AAL2 — every realm user must enroll TOTP at first login.
    for u in _realm()["users"]:
        assert "CONFIGURE_TOTP" in u.get("requiredActions", []), u["username"]


def test_no_implicit_or_password_grants() -> None:
    # OAuth2 BCP — only authorization_code survives on the client.
    raw = REALM.read_text(encoding="utf-8")
    assert '"implicitFlowEnabled": false' in raw
    assert '"directAccessGrantsEnabled": false' in raw


def test_keycloak_healthcheck_is_https_app_level() -> None:
    hc = " ".join(_service(COMPOSE, "keycloak")["healthcheck"]["test"])
    assert "/health/ready" in hc
    assert "HttpsURLConnection" in hc  # real TLS probe, not a TCP peek


def test_sso_in_core_availability_alert() -> None:
    alerts = ALERTS.read_text(encoding="utf-8")
    assert "keycloak" in alerts and "oauth2" in alerts
