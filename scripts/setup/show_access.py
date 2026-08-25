#!/usr/bin/env python3
"""Show SOAR Lab access points and credentials after `make up`.

Reads `.env.full` and `reports/validation/results/webhook_info.json` and
prints a formatted summary that can be used to access every exposed
service.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
WEBHOOK_PATH = REPO_ROOT / "reports" / "validation" / "results" / "webhook_info.json"
ENV_PATH = REPO_ROOT / ".env.full"


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def main() -> int:
    if not ENV_PATH.exists():
        logger.error("ERROR: %s not found", ENV_PATH)
        return 1

    env = load_env(ENV_PATH)
    webhook = {}
    if WEBHOOK_PATH.exists():
        try:
            webhook = json.loads(WEBHOOK_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("[show_access] WARN: could not read %s: %s", WEBHOOK_PATH, exc)

    def get(key: str, default: str = "") -> str:
        return env.get(key, webhook.get(key, default))

    ports = {
        "api": get("API_PORT", "8000"),
        "web_management": get("WEB_UI_PORT", "8085"),
        "docs": get("DOCS_PORT", "8086"),
        "thehive": get("THEHIVE_HTTP_PORT", "8100"),
        "cortex": get("CORTEX_HTTP_PORT", "8101"),
        "shuffle_ui": get("SHUFFLE_UI_PORT", "8081"),
        "shuffle_api": get("SHUFFLE_API_PORT", "5001"),
        "misp": get("MISP_PORT", "8083"),
        "elasticsearch": get("ELASTICSEARCH_PORT", "8200"),
        "opensearch": get("OPENSEARCH_PORT", "8201"),
        "opensearch_dashboards": get("OPENSEARCH_DASHBOARDS_PORT", "8202"),
        "grafana": get("GRAFANA_PORT", "8084"),
        "network_watcher": get("NETWORK_WATCHER_PORT", "15130"),
        "tenzir_web": "15160",
        "tenzir_syslog": "15140",
    }

    rows = [
        (
            "SOAR API",
            f"http://localhost:{ports['api']}",
            f"user={get('WEB_UI_USER', 'admin')}  pass={get('WEB_UI_PASSWORD', '')}",
        ),
        (
            "Web Management",
            f"http://localhost:{ports['web_management']}",
            f"user={get('WEB_UI_USER', 'admin')}  pass={get('WEB_UI_PASSWORD', '')}",
        ),
        ("Documentation", f"http://localhost:{ports['docs']}", ""),
        (
            "TheHive",
            f"http://localhost:{ports['thehive']}",
            f"admin user={get('THEHIVE_ADMIN_USER', 'admin')}"
            f"  pass={get('THEHIVE_ADMIN_PASSWORD', '')}  |"
            f"  API key={get('THEHIVE_API_KEY', '')}",
        ),
        (
            "Cortex",
            f"http://localhost:{ports['cortex']}",
            f"admin user={get('CORTEX_ADMIN_USER', 'soaradmin')}"
            f"  pass={get('CORTEX_ADMIN_PASSWORD', '')}  |"
            f"  API key={get('CORTEX_API_KEY', '')}",
        ),
        (
            "Shuffle UI",
            f"http://localhost:{ports['shuffle_ui']}",
            f"user={get('SHUFFLE_DEFAULT_USERNAME', 'admin')}"
            f"  pass={get('SHUFFLE_DEFAULT_PASSWORD', '')}",
        ),
        (
            "Shuffle API",
            f"http://localhost:{ports['shuffle_api']}",
            f"API key={get('SHUFFLE_DEFAULT_APIKEY', webhook.get('api_key', ''))}  |"
            f"  org_id={get('SHUFFLE_ORG_ID', webhook.get('org_id', ''))}",
        ),
        (
            "MISP",
            f"http://localhost:{ports['misp']}",
            f"email={get('MISP_ADMIN_EMAIL', 'admin@soar.local')}"
            f"  pass={get('MISP_ADMIN_PASSWORD', '')}  |"
            f"  API key={get('MISP_API_KEY', '')}",
        ),
        (
            "Elasticsearch",
            f"http://localhost:{ports['elasticsearch']}",
            f"user={get('ELASTIC_USERNAME', 'elastic')}  pass={get('ELASTIC_PASSWORD', '')}",
        ),
        (
            "OpenSearch (Shuffle)",
            f"http://localhost:{ports['opensearch']}",
            f"user={get('OPENSEARCH_USERNAME', 'admin')}  pass={get('OPENSEARCH_PASSWORD', '')}",
        ),
        ("OpenSearch Dashboards", f"http://localhost:{ports['opensearch_dashboards']}", ""),
        (
            "Grafana",
            f"http://localhost:{ports['grafana']}",
            f"user={get('GRAFANA_ADMIN_USER', 'admin')}  pass={get('GRAFANA_ADMIN_PASSWORD', '')}",
        ),
        ("Nginx", "https://localhost", ""),
        ("Network Watcher", f"http://localhost:{ports['network_watcher']}", ""),
        ("Tenzir Web", f"http://localhost:{ports['tenzir_web']}", ""),
    ]

    lines = [
        "",
        "=" * 68,
        "  SOAR Ransomware Lab - Access Points & Credentials",
        "=" * 68,
    ]
    for name, url, extra in rows:
        lines.append("")
        lines.append(f"{name}")
        lines.append(f"  URL: {url}")
        if extra:
            lines.append(f"  {extra}")

    if webhook:
        lines.extend(
            [
                "",
                "--- Shuffle Webhook ---",
                f"  workflow_id : {webhook.get('workflow_id', '')}",
                f"  trigger_id  : {webhook.get('trigger_id', '')}",
                f"  org_id      : {webhook.get('org_id', '')}",
                f"  webhook_url (internal) : {webhook.get('webhook_url', '')}",
                f"  webhook_url (host)     : {webhook.get('webhook_url_host', '')}",
            ]
        )

    lines.extend(["", "=" * 68])
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
