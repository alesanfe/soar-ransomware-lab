#!/usr/bin/env python3
"""Cross-platform health check for SOAR services.

Reads environment from `.env.full` and hits each service's endpoint.
Exits with non-zero code if any check fails.
"""

from __future__ import annotations

import base64
import logging
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env.full"

logger = logging.getLogger(__name__)

# Service definitions: (name, URL or docker-filter, requires_basic_auth, expected_code)
# For Docker-only checks set url to None and filter to the docker --filter name value.
SERVICES = []


def load_env():
    """Best-effort load of .env.full into os.environ."""
    if ENV_FILE.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(ENV_FILE, override=True)
        except Exception:
            for line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def basic_auth_header(username: str, password: str) -> str:
    creds = f"{username}:{password}".encode()
    return "Basic " + base64.b64encode(creds).decode("ascii")


def http_check(
    name: str, url: str, auth: tuple[str, str] | None = None, expected: int | None = None
) -> bool:
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, method="GET")
        if auth:
            req.add_header("Authorization", basic_auth_header(auth[0], auth[1]))
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:  # nosec B310
            if expected is not None and resp.status != expected:
                logger.error(f"[FAIL] {name}: HTTP {resp.status}")
                return False
            logger.info(f"[OK] {name}")
            return True
    except urllib.error.HTTPError as e:
        logger.error(f"[FAIL] {name}: HTTP {e.code}")
        return False
    except Exception as e:
        logger.error(f"[FAIL] {name}: {e}")
        return False


def docker_running(name: str, container_name: str) -> bool:
    try:
        res = subprocess.run(  # nosec B603 B607
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if res.returncode == 0 and res.stdout.strip().startswith("Up"):
            logger.info(f"[OK] {name}")
            return True
    except Exception as _e:
        logging.warning("Docker check failed for %s: %s", name, _e)
    logger.error(f"[FAIL] {name}")
    return False


def build_url(protocol: str, port_var: str, path: str = "") -> str:
    port = os.getenv(port_var, "")
    if path and not path.startswith("/"):
        path = "/" + path
    if not port:
        # Fallbacks matching .env.example defaults
        fallbacks = {
            "API_PORT": "8000",
            "WEB_UI_PORT": "8085",
            "DOCS_PORT": "8086",
            "THEHIVE_HTTP_PORT": "8100",
            "CORTEX_HTTP_PORT": "8101",
            "SHUFFLE_API_PORT": "5001",
            "SHUFFLE_UI_PORT": "8081",
            "ELASTICSEARCH_PORT": "8200",
            "MISP_PORT": "8083",
            "GRAFANA_PORT": "8084",
        }
        port = fallbacks.get(port_var, "")
    return f"{protocol}://localhost:{port}{path}"


def main():
    load_env()
    ok = True

    print("=== Core SOAR Services ===")
    ok &= http_check("TheHive", build_url("http", "THEHIVE_HTTP_PORT", "/api/status"))
    ok &= http_check("Cortex", build_url("http", "CORTEX_HTTP_PORT", "/api/status"))
    ok &= http_check("Shuffle", build_url("http", "SHUFFLE_API_PORT", "/api/v1/health"))
    ok &= http_check("Elasticsearch", build_url("http", "ELASTICSEARCH_PORT", "_cluster/health"))

    print()
    print("=== API & Management ===")
    ok &= http_check("API", build_url("http", "API_PORT", "/health"))
    ok &= http_check("Web Management", build_url("http", "WEB_UI_PORT"))

    print()
    print("=== Threat Intelligence ===")
    ok &= http_check("MISP", build_url("http", "MISP_PORT"))

    print()
    print("=== Observability ===")
    ok &= http_check("Grafana", build_url("http", "GRAFANA_PORT"))

    print()
    print("=== Infrastructure ===")
    ok &= docker_running("Redis", "soar_redis")
    ok &= docker_running("Nginx", "soar_nginx")
    ok &= docker_running("Tenzir", "soar_tenzir_node")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
