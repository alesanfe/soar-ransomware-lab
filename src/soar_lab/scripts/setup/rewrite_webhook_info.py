#!/usr/bin/env python3
"""
Rewrite host-facing URLs in webhook_info*.json files while preserving internal
canonical URLs (webhook_url). This script is invoked by `make up` after the
webhook artifact has been copied out of the soar_api container.
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[4]
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "results"

INTERNAL_BASE = "http://soar_shuffle_backend:5001"
HOST_BASE = "http://localhost:5001"

HOST_REPLACEMENTS = [
    # (pattern, replacement)
    (r"https?://soar_shuffle_backend:5001", "http://localhost:5001"),
    (r"https?://soar_shuffle_frontend/api/v1/hooks", "http://localhost:5001/api/v1/hooks"),
    (r"https?://soar_shuffle_frontend:80/api/v1/hooks", "http://localhost:5001/api/v1/hooks"),
    (r"https?://thehive:9000", "http://localhost:19000"),
    (r"https?://soar_thehive:9000", "http://localhost:19000"),
    (r"https?://cortex:9001", "http://localhost:19001"),
    (r"https?://soar_cortex:9001", "http://localhost:19001"),
    (r"https?://soar_misp:80", "http://localhost:8083"),
    (r"https?://soar_misp:443", "http://localhost:8083"),
    (r"https?://misp:80", "http://localhost:8083"),
    (r"https?://elasticsearch:9200", "http://localhost:19200"),
    (r"https?://soar_elasticsearch:9200", "http://localhost:19200"),
    (r"https?://wazuh-manager:55000", "https://localhost:55100"),
    (r"https?://soar_wazuh_manager:55000", "https://localhost:55100"),
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
    for file_path in ARTIFACTS_DIR.glob("webhook_info*.json"):
        print(f"[rewrite_webhook_info] Rewriting host URLs in {file_path}")
        rewrite(file_path)


if __name__ == "__main__":
    main()
