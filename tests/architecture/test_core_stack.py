#!/usr/bin/env python3
"""Static validators for the core SOAR stack (TheHive/Cortex/Shuffle/Orborus/
Tenzir/Redis/network-watcher) — CORE-EVAL findings pinned as gates.

Findings verified live 2026-11-10:

- CORE-001: tenzir-node and network-watcher published ports bound to
  0.0.0.0 while every other service binds 127.0.0.1 — dev-mode web APIs
  exposed LAN-wide.
- CORE-002: orborus healthcheck probes `nc -z shuffle-backend 5001` — it
  reports the BACKEND's health, so a hung/deadlocked orborus stays green.
- CORE-003: cortex.conf.template renders a developer-machine Windows path
  (/run/desktop/mnt/host/c/Users/...) as the dockerDirectory DEFAULT —
  analyzer DinD jobs break on any non-Windows host.
- CORE-004: cortex.conf disables CSRF protection (bypassCorsTrustedOrigins
  + wildcard bypassHeaders).
- CORE-005: auth/session secrets fail open — THEHIVE_SECRET and
  CORTEX_API_KEY default to empty strings instead of erroring at config
  time.
- CORE-006: zero Prometheus coverage for core services (no scrape target,
  no blackbox probe) — the SOAR heart is observable only via logs.

Positive gates also pinned: image pinning, healthchecks, resource limits,
no fail-open idioms, hardened-overlay coverage (nnp + pids) for every
core service, watcher socket through the restricted proxy.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra/docker/compose/docker-compose.core.yml"
HARDENED = ROOT / "infra/docker/compose/docker-compose.hardened.yml"
PROM = ROOT / "infra/docker/config/prometheus.yml"
CORTEX_TPL = ROOT / "infra/docker/config/templates/cortex.conf.template"

CORE_SERVICES = {
    "redis",
    "thehive",
    "cortex",
    "shuffle-frontend",
    "shuffle-backend",
    "orborus",
    "tenzir-node",
    "network-watcher",
}


class _Loader(yaml.SafeLoader):
    """Tolerate compose-spec tags (!reset / !override) like
    test_docker_socket_access.py."""


def _tag(loader, suffix, node):
    if suffix == "override":
        if isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        if isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
    if suffix == "reset":
        return None
    return None


_Loader.add_multi_constructor("!", _tag)


def _compose() -> dict:
    return yaml.load(COMPOSE.read_text(encoding="utf-8"), Loader=_Loader)


def _hardened() -> dict:
    return yaml.load(HARDENED.read_text(encoding="utf-8"), Loader=_Loader)


# --- CORE-001: host port bindings ------------------------------------------


def test_all_host_ports_loopback_bound():
    """Every published port must bind 127.0.0.1 — the stack convention that
    thehive/cortex/shuffle already follow. 0.0.0.0 binds expose dev-mode
    APIs (tenzir) and unauthenticated probes (watcher) to the whole LAN."""
    offenders = []
    for svc, spec in _compose()["services"].items():
        for p in spec.get("ports", []) or []:
            p = str(p)
            assert "127.0.0.1" in p or "localhost" in p, (
                f"{svc}: port '{p}' is not loopback-bound (CORE-001)"
            )


# --- CORE-002: healthcheck truthfulness ------------------------------------


def test_healthchecks_probe_the_service_itself():
    """A healthcheck that only probes a *dependency* reports the wrong
    health: if the service deadlocks while its dependency is up, Docker
    keeps it 'healthy'. Each check must exercise the container's own
    process/port."""
    for svc, spec in _compose()["services"].items():
        hc = spec.get("healthcheck", {}).get("test")
        if not hc:
            continue
        cmd = " ".join(str(x) for x in hc if isinstance(x, str))
        # Probing another service's hostname as the ONLY check is the bug.
        own_ok = (
            "localhost" in cmd
            or "127.0.0.1" in cmd
            or f"${{COMPOSE_PROJECT_NAME" in cmd
            or "nc -z" not in cmd  # process-level probes (pgrep, api ping)
        )
        for dep in CORE_SERVICES - {svc}:
            assert not (dep in cmd and not own_ok), (
                f"{svc}: healthcheck only probes '{dep}' — reports the "
                f"dependency's health, not its own (CORE-002)"
            )


# --- CORE-003: cortex template portability ---------------------------------


def test_cortex_template_has_no_machine_specific_default():
    """dockerDirectory must not default to a developer's host path."""
    text = CORTEX_TPL.read_text(encoding="utf-8")
    assert "/run/desktop/mnt/host/" not in text, (
        "cortex.conf.template bakes a Windows Docker-Desktop path into the "
        "dockerDirectory default — analyzer DinD jobs break on Linux "
        "(CORE-003). Use a required var or a derived default."
    )


# --- CORE-004: cortex CSRF --------------------------------------------------


def test_cortex_csrf_protection_not_bypassed():
    """bypassCorsTrustedOrigins + wildcard bypassHeaders disable CSRF
    validation entirely. Lab convenience must not weaken the auth surface."""
    text = CORTEX_TPL.read_text(encoding="utf-8")
    assert '"bypassCorsTrustedOrigins": true' not in text, (
        "cortex.conf.template enables bypassCorsTrustedOrigins (CORE-004)"
    )
    assert '"X-Requested-With": "*"' not in text and '"Raw-Request-URI": "*"' not in text, (
        "cortex.conf.template sets wildcard CSRF bypass headers (CORE-004)"
    )


# --- CORE-SEC-003: tenzir web auth ------------------------------------------


def test_tenzir_web_default_mode_requires_auth():
    """`--mode=dev` disables TLS *and* token auth on the Tenzir REST API —
    any workload on the docker net could manage pipelines unauthenticated.
    The compose default must be a token-enforcing mode ("upstream");
    dev stays reachable only as an explicit env override."""
    spec = _compose()["services"]["tenzir-node"]
    cmd = " ".join(str(x) for x in spec.get("command", []) or [])
    m = re.search(r"TENZIR_WEB_MODE:-(\w+)", cmd)
    assert m, f"tenzir-node command lacks a TENZIR_WEB_MODE default: {cmd!r}"
    assert m.group(1) != "dev", (
        "tenzir-node defaults to --mode=dev (no auth) — use 'upstream' "
        "and mint a token via scripts/setup/init_tenzir_token.sh (CORE-SEC-003)"
    )


# --- CORE-005: fail-closed secrets ------------------------------------------


def test_session_and_api_secrets_fail_closed():
    """Auth/session secrets must use ${VAR} (required) — never an empty
    :-default that silently disables signing/connector auth."""
    text = COMPOSE.read_text(encoding="utf-8")
    for var in ("THEHIVE_SECRET", "CORTEX_API_KEY"):
        assert f"${{{var}:-}}" not in text, (
            f"{var} defaults to empty — session/connector auth silently "
            f"weakened when unset (CORE-005). Use ${{{var}}}"
        )


# --- CORE-006: observability coverage ---------------------------------------


def test_core_services_have_prometheus_coverage():
    """Every externally-probeable core service must appear in prometheus.yml
    (scrape_configs or blackbox targets). Verified live: zero coverage —
    the SOAR heart was observable via logs only."""
    text = PROM.read_text(encoding="utf-8")
    missing = []
    # Service -> hostname the probe should reference
    for svc, host in (
        ("thehive", "thehive:9443"),
        ("cortex", "cortex:9443"),
        ("shuffle-backend", "shuffle-backend:5443"),
        ("redis", "redis:6379"),
        ("network-watcher", "network-watcher:8080"),
        ("tenzir-node", "tenzir-node:5160"),
    ):
        if host not in text:
            missing.append(f"{svc} ({host})")
    assert not missing, (
        "core services without any Prometheus scrape/blackbox probe "
        "(CORE-006):\n" + "\n".join(missing)
    )


# --- positive gates ---------------------------------------------------------


def test_all_images_pinned_no_latest():
    for svc, spec in _compose()["services"].items():
        img = spec.get("image") or ""
        if not img or "$" in img:
            # env-indirect images carry their tag in the default
            m = re.search(r":-([^}]+)", img)
            img = m.group(1) if m else img
        assert ":latest" not in img, f"{svc}: :latest tag"
        assert ":" in img, f"{svc}: unpinned image '{img}'"


# Images with no shell/tools cannot exec a healthcheck command at all;
# their liveness signal is the Prometheus `up` scrape instead. Each entry
# here must be justified next to the service definition in compose.
DISTROLESS_NO_EXEC = {"redis-exporter"}


def test_all_long_running_services_have_healthchecks():
    missing = [
        s
        for s, spec in _compose()["services"].items()
        if "healthcheck" not in spec and s not in DISTROLESS_NO_EXEC
    ]
    assert not missing, f"core services without healthcheck: {missing}"


def test_all_services_have_resource_limits():
    missing = [
        s
        for s, spec in _compose()["services"].items()
        if "limits" not in spec.get("deploy", {}).get("resources", {})
    ]
    assert not missing, f"core services without resource limits: {missing}"


def test_no_fail_open_shell_idioms():
    text = COMPOSE.read_text(encoding="utf-8")
    assert "|| true" not in text


def test_hardened_overlay_covers_every_core_service():
    """Secure-by-default: `make up` always composes hardened.yml — every
    core service must receive no-new-privileges from base or overlay."""
    hard = _hardened()["services"]
    base = _compose()["services"]
    missing = []
    for svc in CORE_SERVICES:
        opts = (hard.get(svc) or {}).get("security_opt") or (
            base.get(svc) or {}
        ).get("security_opt") or []
        if not any("no-new-privileges" in str(o) for o in opts):
            missing.append(svc)
    assert not missing, f"core services without no-new-privileges: {missing}"


def test_hardened_overlay_gives_every_service_pids_limit():
    hard = _hardened()["services"]
    missing = [
        svc
        for svc in CORE_SERVICES
        if "pids"
        not in (
            (hard.get(svc) or {}).get("deploy", {}).get("resources", {}).get("limits", {})
            or {}
        )
    ]
    assert not missing, f"core services without pids limit in hardened: {missing}"


def test_watcher_uses_restricted_proxy_not_raw_socket():
    """Hardened override must remove the raw docker.sock from
    network-watcher (DOCKER_HOST -> docker-socket-proxy)."""
    w = (_hardened()["services"]).get("network-watcher", {})
    env = " ".join(str(e) for e in w.get("environment") or [])
    assert "docker-socket-proxy" in env, "watcher must go via the proxy"
    # volumes !reset [] — raw socket mount cleared
    assert w.get("volumes") in (None, []), (
        "hardened watcher must reset volumes (no raw docker.sock)"
    )
