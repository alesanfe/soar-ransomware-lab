#!/usr/bin/env python3
"""Static validators for the frontend/serving surface (WEB-EVAL-*).

Pins the bugs found live during the frontend evaluation into permanent
gates:

- WEB-EVAL-001..004: web-management's nginx served ``/api/*`` as static
  files — ``POST /api/auth/login`` returned 405 on the direct port AND on
  the SSO path (oauth2-proxy upstreams the static server). The config must
  proxy ``/api/`` (REST) and ``/api/ws/`` (WebSocket Upgrade headers) to
  the API, and must answer ``/health`` itself for the healthcheck.
- WEB-EVAL-005: the healthcheck was ``pgrep nginx`` — passed with a broken
  config. It must hit the application-level ``/health`` endpoint.
- WEB-EVAL-006/008: web-management ran as root with NET_BIND_SERVICE on
  :80. It now listens on :8080 so it can run fully as the nginx uid with
  ZERO capabilities and a read-only rootfs — same posture as docs-site.
- WEB-EVAL-009: the edge nginx published :80/:443 on 0.0.0.0 — the only
  non-loopback bind in the project, exposing TheHive/Cortex/Shuffle/UI
  auth surfaces to the LAN.
- WEB-EVAL-010: every published port in docker-compose.api.yml must be
  loopback-bound (127.0.0.1:...).
- XSS surface: ``escapeHtml`` must escape quotes too — it is used inside
  double-quoted attributes (data-exec=, title=) as well as element text.
"""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
API_COMPOSE = ROOT / "infra/docker/compose/docker-compose.api.yml"
HARDENED = ROOT / "infra/docker/compose/docker-compose.hardened.yml"
SSO_COMPOSE = ROOT / "infra/docker/compose/docker-compose.sso.yml"
WEB_NGINX = ROOT / "apps/web-management/nginx.conf"
EDGE_NGINX = ROOT / "infra/docker/config/nginx/nginx.conf"
JS_DIR = ROOT / "apps/web-management/js"


class _ComposeLoader(yaml.SafeLoader):
    """Compose-spec tags used by the hardened overlay (`!override`/`!reset`)."""


_ComposeLoader.add_constructor(
    "!override",
    lambda loader, node: loader.construct_sequence(node)
    if isinstance(node, yaml.SequenceNode)
    else loader.construct_mapping(node),
)
_ComposeLoader.add_constructor("!reset", lambda loader, node: None)


def _load(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_ComposeLoader)


@pytest.fixture(scope="module")
def api_compose() -> dict:
    return _load(API_COMPOSE)


@pytest.fixture(scope="module")
def hardened() -> dict:
    return _load(HARDENED)


@pytest.fixture(scope="module")
def web_nginx() -> str:
    return WEB_NGINX.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# WEB-EVAL-001..004 — /api must be proxied, not served as static files
# ---------------------------------------------------------------------------


def test_web_nginx_proxies_api_routes(web_nginx):
    """`location /api/` must proxy_pass to the API upstream."""
    api_block = re.search(r"location\s+/api/\s*\{(?P<body>[^}]*)\}", web_nginx)
    assert api_block, "no `location /api/` block — /api falls through to statics (405)"
    assert "proxy_pass" in api_block.group("body")


def test_web_nginx_proxies_websocket(web_nginx):
    """`/api/ws/` must carry Upgrade/Connection headers or WS tickets 400."""
    ws_block = re.search(r"location\s+/api/ws/\s*\{(?P<body>[^}]*)\}", web_nginx)
    assert ws_block, "no `location /api/ws/` block — WebSocket upgrade fails"
    body = ws_block.group("body")
    assert "proxy_pass" in body
    assert "Upgrade" in body
    assert "Connection" in body


def test_web_nginx_has_health_endpoint(web_nginx):
    assert re.search(r"location\s+/health\s*\{", web_nginx)


def test_web_nginx_listens_unprivileged(web_nginx):
    """:8080 lets the whole process run as uid 101 with zero capabilities."""
    assert re.search(r"listen\s+8080\b", web_nginx)
    assert not re.search(r"listen\s+80\b(?!80)", web_nginx)


# ---------------------------------------------------------------------------
# WEB-EVAL-005 — application-level healthcheck, not pgrep
# ---------------------------------------------------------------------------


def test_web_management_healthcheck_hits_health_endpoint(api_compose):
    svc = api_compose["services"]["web-management"]
    test = svc.get("healthcheck", {}).get("test", [])
    joined = " ".join(str(t) for t in test)
    assert "/health" in joined, "healthcheck must hit the /health endpoint"
    assert "pgrep" not in joined, "pgrep passes with a broken config"
    assert "8080" in joined, "healthcheck must target the :8080 listener"


# ---------------------------------------------------------------------------
# WEB-EVAL-006/008 — capless, non-root, read-only postures
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("svc", ["web-management", "docs-site"])
def test_frontend_services_run_capless_nonroot(hardened, svc):
    cfg = hardened["services"][svc]
    assert cfg.get("user") == "101:101", f"{svc} must run as the nginx uid"
    assert "ALL" in cfg.get("cap_drop", []), f"{svc} must drop ALL capabilities"
    assert not cfg.get("cap_add"), f"{svc} must not re-add capabilities"
    assert cfg.get("read_only") is True, f"{svc} must have a read-only rootfs"
    opts = cfg.get("security_opt", [])
    assert "no-new-privileges:true" in opts
    assert cfg.get("tmpfs"), f"{svc} needs tmpfs scratch dirs under read_only"


def test_web_management_published_port_is_unprivileged(api_compose):
    ports = api_compose["services"]["web-management"]["ports"]
    for mapping in ports:
        target = str(mapping).split(":")[-1]
        assert int(target) == 8080, "web-management must publish the :8080 listener"


# ---------------------------------------------------------------------------
# WEB-EVAL-009/010 — every published port loopback-bound
# ---------------------------------------------------------------------------


def test_all_api_compose_ports_loopback_bound(api_compose):
    offenders = []
    for name, svc in api_compose["services"].items():
        for mapping in svc.get("ports") or []:
            # ${VAR:-d} interpolation contains ':' — match the literal
            # leftmost host-IP segment instead of naive splitting.
            if not str(mapping).startswith("127.0.0.1:"):
                offenders.append(f"{name}: {mapping}")
    assert not offenders, f"non-loopback publishes: {offenders}"


def test_edge_upstreams_target_web_management_8080():
    conf = EDGE_NGINX.read_text(encoding="utf-8")
    for var in ("$upstream_web", "$upstream_web_index"):
        matches = re.findall(re.escape(var) + r"\s+web-management:(\d+)", conf)
        assert matches, f"{var} not defined"
        assert all(p == "8080" for p in matches), f"{var} -> :{matches}"


def test_sso_upstream_targets_web_management_8080():
    sso = _load(SSO_COMPOSE)
    upstreams = str(sso["services"]["oauth2-proxy-web"]["environment"])
    assert "web-management:8080" in upstreams


# ---------------------------------------------------------------------------
# XSS surface — escapeHtml must be attribute-safe
# ---------------------------------------------------------------------------


def test_escapehtml_escapes_quotes():
    util = (JS_DIR / "util.js").read_text(encoding="utf-8")
    body = util.split("export function escapeHtml", 1)[1]
    for escaped in ("&amp;", "&lt;", "&gt;", "&quot;", "&#39;"):
        assert escaped in body, f"escapeHtml misses {escaped} — attribute-unsafe"


# ---------------------------------------------------------------------------
# EDGE-EVAL-001/002 — deprecated header + weak TLS protocols
# ---------------------------------------------------------------------------

SHUFFLE_TMPL = ROOT / "infra/docker/config/shuffle-frontend/nginx.conf.tmpl"
DOCS_NGINX = ROOT / "apps/docs-site/nginx.conf"
NGINX_CONFS = [EDGE_NGINX, WEB_NGINX, DOCS_NGINX, SHUFFLE_TMPL]


def _uncommented_lines(conf: str) -> list[str]:
    return [ln for ln in conf.splitlines() if ln.strip() and not ln.strip().startswith("#")]


@pytest.mark.parametrize("path", NGINX_CONFS, ids=lambda p: p.name + "@" + p.parent.name)
def test_no_x_xss_protection_header(path):
    """X-XSS-Protection is deprecated and can weaken modern browsers (CSP supersedes it)."""
    offenders = [ln for ln in _uncommented_lines(path.read_text(encoding="utf-8")) if "X-XSS-Protection" in ln]
    assert not offenders, f"{path.name} still sets X-XSS-Protection: {offenders}"


@pytest.mark.parametrize("path", NGINX_CONFS, ids=lambda p: p.name + "@" + p.parent.name)
def test_no_tls_below_1_2(path):
    """TLSv1/1.1 are deprecated (RFC 8996) — ssl_protocols must be >= 1.2."""
    for ln in _uncommented_lines(path.read_text(encoding="utf-8")):
        m = re.search(r"ssl_protocols\s+([^;]+);", ln)
        if m:
            for proto in m.group(1).split():
                assert proto in ("TLSv1.2", "TLSv1.3"), f"{path.name}: {proto} in ssl_protocols"


def test_edge_http_redirects_to_https():
    """The :80 server must only expose /nginx-health and 301 everything else."""
    conf = EDGE_NGINX.read_text(encoding="utf-8")
    http_block = re.search(r"server\s*\{[^}]*listen\s+80\b.*?\n    \}", conf, re.DOTALL)
    assert http_block, "edge :80 server block not found"
    block = http_block.group(0)
    assert re.search(r"return\s+301\s+https://", block), "edge :80 does not redirect to HTTPS"
    assert "nginx-health" in block


def test_edge_hsts_enabled():
    conf = EDGE_NGINX.read_text(encoding="utf-8")
    assert re.search(r'Strict-Transport-Security "max-age=\d+', conf)


def test_edge_verifies_upstream_tls():
    """Proxied HTTPS backends must have their certs verified against the lab CA."""
    conf = EDGE_NGINX.read_text(encoding="utf-8")
    assert "proxy_ssl_verify on" in conf
    assert "proxy_ssl_trusted_certificate" in conf
    assert "proxy_ssl_server_name on" in conf


def test_docs_site_healthcheck_hits_app_content(api_compose):
    """docs-site probe must exercise the real baseUrl, not a bare socket."""
    svc = api_compose["services"]["docs-site"]
    joined = " ".join(str(t) for t in svc.get("healthcheck", {}).get("test", []))
    assert "soar-ransomware-lab" in joined
    assert "8080" in joined
