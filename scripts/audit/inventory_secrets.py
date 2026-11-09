"""SEC-001: Inventory env vars as a secret-risk matrix WITHOUT printing values.

Classifies each variable as REAL/SYNTHETIC/PLACEHOLDER/CONFIG and maps it to
the services that consume it. Output: markdown table (no secret values).
"""

import re
import sys
from pathlib import Path

SECRET_NAME = re.compile(
    r"(SECRET|PASSWORD|PASSWD|API_?KEY|APIKEY|_KEY$|TOKEN|SALT|CREDENTIALS?)", re.IGNORECASE
)
PLACEHOLDER = re.compile(
    r"^(changeme|change[-_]?me|password|admin|test|example|sample|dummy|xxx+|"
    r"your[-_].*|todo|fixme|none|null|false|true|\d+|http[s]?://.*|[\w.-]+:\d+|.*\$\{.*)$",
    re.IGNORECASE,
)
GENERATED = re.compile(r"^[0-9a-f]{32,}$|^[A-Za-z0-9+/=_-]{32,}$")

SERVICE_MAP = {
    "API_": "api",
    "JWT_": "api (auth)",
    "INTERNAL_SERVICE": "api-workers",
    "CORTEX_": "cortex",
    "THEHIVE_": "thehive",
    "SHUFFLE_": "shuffle",
    "ORBORUS_": "shuffle (orborus)",
    "MISP_": "misp (+misp-db, misp-redis)",
    "ELASTIC": "elasticsearch",
    "OPENSEARCH": "opensearch (+dashboards)",
    "GRAFANA_": "grafana",
    "POSTGRES_": "postgres",
    "REDIS_": "redis",
    "SIEM_WEBHOOK": "api (webhook ingress)",
    "EDR_SIM": "edr simulator",
    "FIREWALL_SIM": "firewall simulator",
    "WEB_UI": "web-management",
    "LOKI_": "loki",
    "TENZIR_": "tenzir",
    "NGINX_": "nginx",
    "PROMTAIL_": "promtail",
    "NETWORK_WATCHER": "network-watcher",
    "DOCKER_": "docker-socket-proxy",
    "COMPOSE_": "docker-compose",
    "ELASTICSEARCH_": "elasticsearch",
    "RATE_LIMIT": "api (rate limiting)",
    "CORS_": "api (cors)",
    "WEBHOOK_PAYLOAD": "api (webhook)",
    "ANALYZER_": "api->cortex",
    "MAX_CONCURRENT": "api->cortex",
    "DECISION_": "api (decision engine)",
    "OUTER_": "compose networking",
    "DOCS_": "docs-site",
    "HTTPS?_": "ingress",
    "HTTP_": "ingress",
    "LOG_": "logging config",
}


def service_for(var: str) -> str:
    for prefix, svc in SERVICE_MAP.items():
        if re.match(prefix, var):
            return svc
    return "(unmapped)"


def classify(var: str, value: str) -> tuple[str, str]:
    if not SECRET_NAME.search(var):
        return "CONFIG", "not a credential by name"
    if PLACEHOLDER.match(value.strip()):
        return "PLACEHOLDER", "default/example value — rotate anyway"
    if GENERATED.match(value.strip()):
        return "REAL-GENERATED", "high-entropy value, looks generated"
    return "REAL-CUSTOM", "non-placeholder credential"


def main() -> int:
    env_path = Path(sys.argv[1] if len(sys.argv) > 1 else ".env.full")
    rows = []
    counts: dict[str, int] = {}
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        var, _, value = line.partition("=")
        var = var.strip()
        cls, note = classify(var, value)
        counts[cls] = counts.get(cls, 0) + 1
        rows.append((var, service_for(var), cls, note, len(value.strip())))

    print("| Variable | Servicio | Clasificacion | Nota | Len |")
    print("|---|---|---|---|---|")
    for var, svc, cls, note, ln in rows:
        print(f"| `{var}` | {svc} | {cls} | {note} | {ln} |")
    print("\n## Resumen\n")
    for k, v in sorted(counts.items()):
        print(f"- {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
