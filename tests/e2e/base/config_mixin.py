"""Configuration mixin for E2E tests.

Handles environment loading, path resolution (container vs host), and
webhook info discovery.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# ── Path resolution (container vs host) ──────────────────────────────────────

INSIDE_CONTAINER = (
    Path("/.dockerenv").exists()
    or os.environ.get("container", "").lower() in ("oci", "docker")
    # /app is POSIX-only evidence — on Windows it resolves to <drive>:\app,
    # which exists on some hosts and produced false positives here.
    or (os.name != "nt" and Path("/app").exists())
)

REPO_ROOT = (
    Path("/app") if INSIDE_CONTAINER else Path(__file__).resolve().parent.parent.parent.parent
)
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
RUNTIME_DIR = Path("/app/runtime") if INSIDE_CONTAINER else REPO_ROOT / "runtime"
REPORTS_DIR = Path("/app/reports") if INSIDE_CONTAINER else REPO_ROOT / "reports"
VALIDATION_RESULTS_DIR = (
    Path("/app/reports/validation/results")
    if INSIDE_CONTAINER
    else REPO_ROOT / "reports" / "validation" / "results"
)
E2E_RESULTS_DIR = VALIDATION_RESULTS_DIR / "e2e"
E2E_REPORT_DIR = Path("/app/reports/e2e") if INSIDE_CONTAINER else REPO_ROOT / "reports" / "e2e"
LOGS_DIR = Path("/app/runtime/logs") if INSIDE_CONTAINER else REPO_ROOT / "runtime" / "logs"
ENV_FULL = Path("/app/.env.full") if INSIDE_CONTAINER else REPO_ROOT / ".env.full"
# Container runs mount .env.container, not .env.full — fall back to it so
# credential keys (GRAFANA_*, etc.) resolve inside docker.
_ENV_CANDIDATES = (
    [Path("/app/.env.full"), Path("/app/.env.container")]
    if INSIDE_CONTAINER
    else [REPO_ROOT / ".env.full", REPO_ROOT / ".env.container"]
)

# Add src to path for importing integration clients
_SRC_PATH = str(REPO_ROOT / "src")
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

# Webhook info paths
_WEBHOOK_INFO_PATHS = [
    Path("/app/reports/validation/results/webhook_info.json"),
    REPO_ROOT / "reports" / "validation" / "results" / "webhook_info.json",
]

from soar_lab.security.tls_config import ca_verify


class LabDatastoreAuth:
    """``requests`` auth that picks OpenSearch vs Elasticsearch credentials
    by hostname/port — one object covers both datastores on ``self.s`` and on
    bare ``requests.*`` calls (pass it via ``auth=self.s.auth``).

    Explicit ``Authorization`` headers always win (Bearer tokens for TheHive
    etc. are untouched)."""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        env = env or {}
        self._os = (
            env.get("SHUFFLE_OPENSEARCH_USERNAME")
            or env.get("OPENSEARCH_USERNAME", "admin"),
            env.get("SHUFFLE_OPENSEARCH_PASSWORD")
            or env.get("OPENSEARCH_PASSWORD", ""),
        )
        self._es = (
            env.get("ELASTIC_USERNAME", "elastic"),
            env.get("ELASTIC_PASSWORD", ""),
        )

    def __call__(self, r):
        from urllib.parse import urlparse

        if r.headers.get("Authorization"):
            return r
        u = urlparse(r.url or "")
        host, port = u.hostname or "", u.port
        if host == "opensearch" or (host in ("localhost", "127.0.0.1") and port == 19201):
            creds = self._os
        elif host == "elasticsearch" or (host in ("localhost", "127.0.0.1") and port == 19200):
            creds = self._es
        else:
            return r
        if creds[1]:
            import base64

            r.headers["Authorization"] = "Basic " + base64.b64encode(
                f"{creds[0]}:{creds[1]}".encode()
            ).decode()
        return r


class ConfigMixin:
    """Mixin for environment configuration and path resolution."""

    # Workflow name — can be overridden by subclasses
    workflow_name: str = "SOAR-Ransomware-Response"

    def load_env(self) -> dict[str, str]:
        """Load environment variables from OS env and .env.full.

        OS environment variables take precedence over .env.full values.
        """
        env_keys = [
            "SHUFFLE_URL",
            "ES_URL",
            "THEHIVE_URL",
            "CORTEX_URL",
            "MISP_URL",
            "THEHIVE_API_KEY",
            "CORTEX_API_KEY",
            "CORTEX_ADMIN_USER",
            "CORTEX_ADMIN_PASSWORD",
            "MISP_API_KEY",
            "SHUFFLE_DEFAULT_APIKEY",
            "SHUFFLE_DEFAULT_PASSWORD",
            "ELASTIC_USERNAME",
            "ELASTIC_PASSWORD",
            "OPENSEARCH_URL",
            "LOKI_URL",
            "PROMTAIL_URL",
            "GRAFANA_URL",
            "GRAFANA_ADMIN_USER",
            "GRAFANA_ADMIN_PASSWORD",
            "GRAFANA_API_KEY",
            "API_URL",
            "REDIS_PASSWORD",
            "INTERNAL_SERVICE_TOKEN",
            # Cleanup configuration
            "E2E_CLEANUP_ON_SUCCESS",
            "E2E_CLEANUP_ON_FAILURE",
            "E2E_KEEP_ARTIFACTS_ON_FAILURE",
            "E2E_FAIL_ON_CLEANUP_ERROR",
            "E2E_PRESERVE_REPORT_DATA",
            "E2E_CLEANUP_AFTER_REPORT",
            # Services whose pre-test health check is skipped (fault-injection
            # suites like TC-18/TC-36 take services down on purpose).
            "E2E_SKIP_SERVICES",
            # Observability configuration
            "E2E_VERIFY_OBSERVABILITY",
            "E2E_VERIFY_LOKI",
            "E2E_VERIFY_PROMTAIL",
            "E2E_VERIFY_GRAFANA",
            "E2E_VERIFY_METRICS",
            # Fixtures configuration
            "E2E_SEED_MISP",
            "E2E_SEED_SEARCH",
            # Service-specific cleanup modes
            "E2E_THEHIVE_CLEANUP_MODE",
            "E2E_CORTEX_CLEANUP_MODE",
            "E2E_MISP_CLEANUP_MODE",
        ]

        result: dict[str, str] = {}
        for k in env_keys:
            v = os.environ.get(k)
            if v is not None:
                result[k] = v

        # Load from env files for any missing keys (first file wins).
        for env_file in _ENV_CANDIDATES:
            if not env_file.exists():
                continue
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip()
                    if k not in result:
                        result[k] = v
        return result

    def resolve_paths(self) -> None:
        """Resolve all paths based on execution environment."""
        self.inside_container = INSIDE_CONTAINER
        self.repo_root = REPO_ROOT
        self.fixtures_dir = FIXTURES_DIR
        self.runtime_dir = RUNTIME_DIR
        self.reports_dir = REPORTS_DIR
        self.validation_results_dir = VALIDATION_RESULTS_DIR
        self.e2e_results_dir = E2E_RESULTS_DIR
        self.e2e_report_dir = E2E_REPORT_DIR
        self.logs_dir = LOGS_DIR
        self.env_full_path = ENV_FULL

        # Ensure directories exist
        self.e2e_results_dir.mkdir(parents=True, exist_ok=True)
        self.e2e_report_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def load_webhook_info(self) -> dict[str, Any]:
        """Load webhook_info.json, trying container and host paths."""
        for p in _WEBHOOK_INFO_PATHS:
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    pass
        return {}

    def get_service_url(self, service: str) -> str:
        """Get the URL for a service based on execution environment.

        Args:
            service: One of 'shuffle', 'thehive', 'cortex', 'misp', 'es',
                     'opensearch', 'loki', 'promtail', 'grafana', 'api',
                     'redis', 'network_watcher', 'tenzir'.

        Returns:
            Service URL string.
        """
        env = getattr(self, "env", {})
        defaults_container = {
            "shuffle": "https://shuffle-backend:5443",
            "shuffle_frontend": "http://shuffle-frontend:80",
            "thehive": "https://thehive:9443",
            "cortex": "https://cortex:9443",
            "misp": "http://misp:80",
            "es": "https://elasticsearch:9200",
            "opensearch": "https://opensearch:9200",
            "opensearch_dashboards": "http://opensearch-dashboards:5601",
            "loki": "https://loki:3100",
            "promtail": "http://promtail:9080",
            "grafana": "https://grafana:3000",
            "api": "http://api:8000",
            "network_watcher": "http://network-watcher:8080",
            "tenzir": "http://tenzir-node:5160",
            "nginx": "http://nginx:80",
            "nginx_https": "https://nginx:443",
            "docs_site": "http://docs-site:8080",
            "web_management": "http://web-management:8080",
            "redis": "http://redis:6379",
        }
        defaults_host = {
            "shuffle": "http://localhost:5001",
            "shuffle_frontend": "http://localhost:8081",
            "thehive": "https://localhost:18100",
            "cortex": "https://localhost:18101",
            "misp": "http://localhost:8083",
            "es": "https://localhost:19200",
            "opensearch": "https://localhost:19201",
            "opensearch_dashboards": "http://localhost:19202",
            "loki": "https://localhost:3100",
            "promtail": "http://localhost:9080",
            "grafana": "https://localhost:8084",
            "api": "http://localhost:8000",
            "network_watcher": "http://localhost:15130",
            "tenzir": "http://localhost:15160",
            "nginx": "http://localhost:80",
            "nginx_https": "https://localhost:443",
            "docs_site": "http://localhost:8086",
            "web_management": "http://localhost:8085",
        }
        env_keys = {
            "shuffle": "SHUFFLE_URL",
            "shuffle_frontend": "SHUFFLE_FRONTEND_URL",
            "thehive": "THEHIVE_URL",
            "cortex": "CORTEX_URL",
            "misp": "MISP_URL",
            "es": "ES_URL",
            "opensearch": "OPENSEARCH_URL",
            "opensearch_dashboards": "OPENSEARCH_DASHBOARDS_URL",
            "loki": "LOKI_URL",
            "promtail": "PROMTAIL_URL",
            "grafana": "GRAFANA_URL",
            "api": "API_URL",
            "network_watcher": "NETWORK_WATCHER_URL",
            "tenzir": "TENZIR_URL",
            "nginx": "NGINX_URL",
            "nginx_https": "NGINX_HTTPS_URL",
            "docs_site": "DOCS_URL",
            "web_management": "WEB_MANAGEMENT_URL",
        }
        defaults = defaults_container if self.inside_container else defaults_host
        env_key = env_keys.get(service)
        if env_key and env.get(env_key):
            return env[env_key]
        return defaults.get(service, "")

    def get_redis_host(self) -> str:
        """Get Redis host based on execution environment."""
        return "redis" if self.inside_container else "localhost"

    def get_redis_port(self) -> int:
        """Get Redis port."""
        return int(self.env.get("REDIS_PORT", "6379"))

    def get_redis_password(self) -> str:
        """Get Redis password."""
        return self.env.get("REDIS_PASSWORD", "")
