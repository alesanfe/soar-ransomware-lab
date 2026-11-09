"""Static regression tests for infra hardening fixes.

Covers SHF-001/SHF-008 (Shuffle upstream re-resolution), WEB-SEC-001
(per-location security headers + strict CSP), DOCS-001 (static
multistage docs-site) and TH-002/OSD-002 (loopback port bindings).
These run without Docker — they inspect the source artefacts.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


def test_shuffle_nginx_uses_dns_resolver():
    tmpl = _read("infra/docker/config/shuffle-frontend/nginx.conf.tmpl")
    assert "resolver" in tmpl, "nginx must resolve the backend via DNS per request"
    assert (
        "$shuffle_backend" in tmpl
    ), "upstream must be proxied through a variable so it re-resolves"
    assert "proxy_pass $shuffle_backend" in tmpl


def test_shuffle_frontend_healthcheck_proxies_upstream():
    compose = _read("infra/docker/compose/docker-compose.core.yml")
    assert "shuffle_backend" in compose or "shuffle-backend" in compose
    # healthcheck must hit the proxied backend path, not bare nginx
    assert "/api/v1/_health" in compose or "upstream" in compose.lower()


def test_web_management_csp_is_strict():
    conf = _read("apps/web-management/nginx.conf")
    assert "script-src 'self'" in conf
    assert (
        "'unsafe-inline'" not in conf.split("script-src")[1].split(";")[0]
    ), "script-src must not allow inline scripts"


def test_web_management_headers_survive_locations():
    conf = _read("apps/web-management/nginx.conf")
    # location-level add_header suppresses server-level inheritance —
    # every location that adds Cache-Control must re-add the headers
    idx = conf.find("location = /index.html")
    assert idx != -1
    block = conf[idx : idx + 1500]
    assert block.count("add_header X-Frame-Options") == 1
    assert "Content-Security-Policy" in block


def test_docs_site_is_static_multistage():
    dockerfile = _read("apps/docs-site/Dockerfile")
    assert "FROM nginx" in dockerfile
    assert "npm run build" in dockerfile
    assert "npm start" not in dockerfile and "docusaurus start" not in dockerfile


def test_ui_and_data_ports_are_loopback():
    files = {
        "infra/docker/compose/docker-compose.core.yml": [
            "THEHIVE_HTTP_PORT",
            "CORTEX_HTTP_PORT",
            "SHUFFLE_UI_PORT",
            "SHUFFLE_API_PORT",
        ],
        "infra/docker/compose/docker-compose.api.yml": ["WEB_UI_PORT"],
        "infra/docker/compose/docker-compose.misp.yml": ["MISP_PORT"],
        "infra/docker/compose/docker-compose.opensearch.yml": [
            "OPENSEARCH_PORT",
            "OPENSEARCH_DASHBOARDS_PORT",
        ],
        "infra/docker/compose/docker-compose.yml": ["ELASTICSEARCH_PORT"],
        "infra/docker/compose/logging/docker-compose.logging.yml": ["GRAFANA_PORT"],
    }
    for f, vars_ in files.items():
        text = _read(f)
        for var in vars_:
            assert f"127.0.0.1:${{{var}" in text, f"{var} in {f} must bind to 127.0.0.1"


def test_ingress_and_lab_ports_stay_public():
    # nginx edge + lab ingest feeds legitimately stay on 0.0.0.0
    api = _read("infra/docker/compose/docker-compose.api.yml")
    assert '"${HTTP_PORT:-80}:80"' in api
    assert '"${HTTPS_PORT:-443}:443"' in api
    core = _read("infra/docker/compose/docker-compose.core.yml")
    assert "127.0.0.1:${TENZIR" not in core


def test_grafana_alert_rules_reference_provisioned_uids():
    rules = _read("infra/docker/compose/logging/alert-rules.yml")
    assert "datasourceUid: loki" in rules
    ds = _read("infra/docker/config/templates/grafana-datasources.yml.template")
    assert "uid: loki" in ds
