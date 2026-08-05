#!/usr/bin/env python3
"""Update Wazuh indexer internal_users.yml bcrypt hashes from .env.full.

Wazuh 4.14.0 mounts internal_users.yml into the indexer container. The admin
and kibanaserver hashes must match WAZUH_INDEXER_PASSWORD and
WAZUH_DASHBOARD_PASSWORD respectively, otherwise the indexer healthcheck and
dashboard authentication fail.

This script uses the httpd:2.4-alpine image's htpasswd tool to compute bcrypt
hashes without requiring host Python dependencies.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_FILE = REPO_ROOT / ".env.full"
INTERNAL_USERS = REPO_ROOT / "infra" / "docker" / "wazuh" / "config" / "wazuh_indexer" / "internal_users.yml"
HTTPD_IMAGE = "httpd:2.4-alpine"


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _hash_password(user: str, password: str) -> str:
    """Return bcrypt hash using htpasswd from httpd:2.4-alpine."""
    cmd = [
        "docker", "run", "--rm",
        HTTPD_IMAGE,
        "htpasswd", "-bnB", "-C", "12",
        user, password,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip() or result.stderr.strip()
    match = re.search(rf"^{re.escape(user)}:([$]2[aby][$][^\s]+)", output)
    if not match:
        raise RuntimeError(f"Failed to compute bcrypt hash for {user}: {output}")
    return match.group(1)


def _pull_image() -> None:
    """Ensure the httpd helper image is available."""
    check = subprocess.run(
        ["docker", "image", "inspect", HTTPD_IMAGE],
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        print(f"[update-wazuh-hashes] Pulling {HTTPD_IMAGE}...")
        pull = subprocess.run(["docker", "pull", HTTPD_IMAGE], capture_output=True, text=True)
        if pull.returncode != 0:
            raise RuntimeError(f"Failed to pull {HTTPD_IMAGE}: {pull.stderr}")


def _update_internal_users(indexer_password: str, dashboard_password: str) -> None:
    if not INTERNAL_USERS.exists():
        raise FileNotFoundError(f"internal_users.yml not found: {INTERNAL_USERS}")

    admin_hash = _hash_password("admin", indexer_password)
    kibana_hash = _hash_password("kibanaserver", dashboard_password)

    text = INTERNAL_USERS.read_text(encoding="utf-8")
    text = re.sub(
        r"(?m)^(admin:\n\s+hash:\s*)['\"][^'\"\n]+['\"]",
        rf"\1{admin_hash!r}",
        text,
    )
    text = re.sub(
        r"(?m)^(kibanaserver:\n\s+hash:\s*)['\"][^'\"\n]+['\"]",
        rf"\1{kibana_hash!r}",
        text,
    )
    INTERNAL_USERS.write_text(text, encoding="utf-8")
    print("[update-wazuh-hashes] Updated admin and kibanaserver hashes")


def main() -> int:
    if not ENV_FILE.exists():
        print(f"ERROR: {ENV_FILE} not found; run 'make generate-secrets' first", file=sys.stderr)
        return 1

    env = _read_env(ENV_FILE)
    indexer_password = env.get("WAZUH_INDEXER_PASSWORD")
    dashboard_password = env.get("WAZUH_DASHBOARD_PASSWORD")
    if not indexer_password or not dashboard_password:
        print("ERROR: WAZUH_INDEXER_PASSWORD and WAZUH_DASHBOARD_PASSWORD must be set", file=sys.stderr)
        return 1

    _pull_image()
    _update_internal_users(indexer_password, dashboard_password)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
