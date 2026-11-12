#!/usr/bin/env python3
"""Rewrite host-facing URLs in webhook_info*.json files while preserving
internal canonical URLs (webhook_url).

This script is invoked by `make up` after the webhook info file has been
copied out of the soar_api container.
"""

import json
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = REPO_ROOT / "reports" / "validation" / "results"

INTERNAL_BASE = os.environ.get("SHUFFLE_BACKEND_URL", "https://shuffle-backend:5443")
HOST_BASE = os.environ.get(
    "SHUFFLE_BACKEND_HOST_URL",
    f"https://localhost:{os.environ.get('SHUFFLE_API_PORT', '5001')}",
)
_SHUFFLE_HOST = HOST_BASE

HOST_REPLACEMENTS = [
    # (pattern, replacement) — handles both service names and container names
    (r"https?://shuffle-backend:(5001|5443)", _SHUFFLE_HOST),
    (r"https?://soar_shuffle_backend:5001", _SHUFFLE_HOST),
    (r"https?://shuffle-frontend/api/v1/hooks", _SHUFFLE_HOST + "/api/v1/hooks"),
    (r"https?://shuffle-frontend:80/api/v1/hooks", _SHUFFLE_HOST + "/api/v1/hooks"),
    (r"https?://soar_shuffle_frontend/api/v1/hooks", _SHUFFLE_HOST + "/api/v1/hooks"),
    (r"https?://soar_shuffle_frontend:80/api/v1/hooks", _SHUFFLE_HOST + "/api/v1/hooks"),
    (r"https?://thehive:(9000|9443)", "https://localhost:8100"),
    (r"https?://soar_thehive:(9000|9443)", "https://localhost:8100"),
    (r"https?://cortex:(9001|9443)", "https://localhost:8101"),
    (r"https?://soar_cortex:(9001|9443)", "https://localhost:8101"),
    (r"https?://misp:80", "http://localhost:8083"),
    (r"https?://soar_misp:80", "http://localhost:8083"),
    (r"https?://misp:443", "https://localhost:8083"),
    (r"https?://soar_misp:443", "https://localhost:8083"),
    (r"https?://elasticsearch:9200", "https://localhost:19200"),
    (r"https?://soar_elasticsearch:9200", "https://localhost:19200"),
]


def _to_host_url(url: str) -> str:
    for pattern, replacement in HOST_REPLACEMENTS:
        url = re.sub(pattern, replacement, url, flags=re.IGNORECASE)
    return url


def _rewrite_text(text: str) -> str:
    for pattern, replacement in HOST_REPLACEMENTS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _canonical_webhook_url(trigger_id: str) -> str:
    return f"{INTERNAL_BASE}/api/v1/hooks/webhook_{trigger_id}"


def _host_webhook_url(trigger_id: str) -> str:
    return f"{HOST_BASE}/api/v1/hooks/webhook_{trigger_id}"


def rewrite(path: Path) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))

    trigger_id = data.get("trigger_id", "")
    if trigger_id:
        # Canonical internal URL for use inside containers; host URL for host scripts
        data["webhook_url"] = _canonical_webhook_url(trigger_id)
        data["webhook_url_host"] = _host_webhook_url(trigger_id)
    elif "webhook_url" in data:
        # Fallback: ensure webhook_url_host is host-facing if webhook_url exists
        data["webhook_url_host"] = _to_host_url(data["webhook_url"])

    # Rewrite descriptive action strings for human consumption / host scripts
    if isinstance(data.get("actions"), dict):
        for key, value in data["actions"].items():
            if isinstance(value, str):
                data["actions"][key] = _rewrite_text(value)

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    for file_path in REPORTS_DIR.glob("webhook_info*.json"):
        logger.info("[rewrite_webhook_info] Rewriting host URLs in %s", file_path)
        rewrite(file_path)


if __name__ == "__main__":
    main()
