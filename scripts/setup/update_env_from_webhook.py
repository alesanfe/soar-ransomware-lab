#!/usr/bin/env python3
"""Persist real Shuffle credentials back to .env.full after init.

Run inside the soar_api container so it can query Shuffle's OpenSearch
users index and update /app/.env.full (which is mounted from the project
root).
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_CANDIDATES = [Path("/app/.env.full"), REPO_ROOT / ".env.full", Path(".env.full")]
WEBHOOK_CANDIDATES = [
    Path("/app/reports/validation/results/webhook_info.json"),
    REPO_ROOT / "reports" / "validation" / "results" / "webhook_info.json",
    Path("webhook_info.json"),
]


def _find_first(paths):
    for p in paths:
        if p.exists():
            return p
    return None


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


def save_env(path: Path, updates: dict[str, str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    remaining = set(updates)
    out_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            out_lines.append(f"{key}={updates[key]}")
            remaining.discard(key)
        else:
            out_lines.append(line)
    for key in sorted(remaining):
        out_lines.append(f"{key}={updates[key]}")
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return True


def es_url_and_auth(env: dict[str, str]) -> tuple[str, tuple[str, str] | None]:
    url = env.get("SHUFFLE_OPENSEARCH_URL") or env.get("OPENSEARCH_URL") or "http://opensearch:9200"
    if not url.startswith("http"):
        url = "http://" + url
    user = env.get("SHUFFLE_OPENSEARCH_USERNAME") or env.get("OPENSEARCH_USERNAME") or ""
    passwd = env.get("SHUFFLE_OPENSEARCH_PASSWORD") or env.get("OPENSEARCH_PASSWORD") or ""
    auth = (user, passwd) if user and passwd else None
    return url, auth


def es_get_json(url: str, auth=None) -> dict | None:
    req = urllib.request.Request(url, method="GET")
    if auth:
        token = base64.b64encode(f"{auth[0]}:{auth[1]}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("  [update_env] WARN: %s -> %s", url, exc)
    return None


def fetch_admin_info(es_url: str, auth=None) -> dict:
    """Fetch the first user from the users index (like
    ShuffleClient._fetch_real_apikey)."""
    data = es_get_json(f"{es_url}/users/_search?size=1", auth)
    if not data:
        return {}
    hits = data.get("hits", {}).get("hits", [])
    if not hits:
        return {}
    return hits[0].get("_source", {}) or {}


def main() -> int:
    env_path = _find_first(ENV_CANDIDATES)
    if not env_path:
        logger.error("[update_env] ERROR: .env.full not found")
        return 1

    env = load_env(env_path)
    es_url, auth = es_url_and_auth(env)
    logger.info("[update_env] Querying %s/users/_search for current admin apikey", es_url)

    src = fetch_admin_info(es_url, auth)
    if not src:
        logger.warning("[update_env] WARN: no user found in OpenSearch; skipping .env.full update")
        return 0

    api_key = src.get("apikey", "")
    if not api_key:
        logger.warning("[update_env] WARN: user has no apikey; skipping")
        return 0

    active_org = src.get("active_org", {})
    org_id = active_org.get("id") if isinstance(active_org, dict) else ""
    if not org_id:
        org_id = env.get("SHUFFLE_ORG_ID", "")

    logger.info("[update_env] Found Shuffle apikey ending in ...%s", api_key[-8:])

    updates: dict[str, str] = {"SHUFFLE_DEFAULT_APIKEY": api_key}
    if org_id:
        updates["SHUFFLE_ORG_ID"] = org_id

    if save_env(env_path, updates):
        logger.info("[update_env] Updated %s", env_path)
    else:
        logger.warning("[update_env] WARN: could not write %s", env_path)

    webhook_path = _find_first(WEBHOOK_CANDIDATES)
    if webhook_path:
        try:
            with open(webhook_path, encoding="utf-8") as f:
                webhook = json.load(f)
            webhook["api_key"] = api_key
            if org_id:
                webhook["org_id"] = org_id
            with open(webhook_path, "w", encoding="utf-8") as f:
                json.dump(webhook, f, indent=2, ensure_ascii=False)
            logger.info("[update_env] Updated %s", webhook_path)
        except Exception as exc:
            logger.warning("[update_env] WARN: could not update webhook file: %s", exc)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
