#!/usr/bin/env python3
"""Preserve SOAR service credentials before a make reset.

This script extracts current credentials from TheHive, Cortex, Grafana and other services
and saves them in a JSON file to be restored after a fresh deploy.

Usage:
    python preserve_credentials.py
"""

import json
import logging
import os
from pathlib import Path

import requests

from soar_lab.common.constants import (
    AUTH_BASIC_PREFIX,
    AUTH_BEARER_PREFIX,
    HEADER_AUTHORIZATION,
)

logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv(".env.full", override=False)
except ImportError:
    pass

# Configuration
# Save directly to the host so it survives the reset
CREDENTIALS_FILE_HOST = Path("reports/validation/results/credentials_backup.json")
CREDENTIALS_FILE = Path("/app/reports/validation/results/credentials_backup.json")

# Service URLs (use Docker Compose service names, not container names)
THEHIVE_URL = os.environ.get("THEHIVE_URL", "http://thehive:9000")
CORTEX_URL = os.environ.get("CORTEX_URL", "http://cortex:9001")
GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://grafana:3000")
SHUFFLE_URL = os.environ.get("SHUFFLE_BACKEND_URL", "http://shuffle-backend:5001")

# Current credentials
THEHIVE_API_KEY = os.environ.get("THEHIVE_API_KEY", "")
CORTEX_API_KEY = os.environ.get("CORTEX_API_KEY", "")
SHUFFLE_API_KEY = os.environ.get("SHUFFLE_DEFAULT_APIKEY", "")
GRAFANA_USER = os.environ.get("GRAFANA_ADMIN_USER", "admin")
GRAFANA_PASS = os.environ.get("GRAFANA_ADMIN_PASSWORD", "")


def preserve_thehive_credentials():
    """Preserve the current TheHive API key."""
    if not THEHIVE_API_KEY:
        logger.warning("[WARN] THEHIVE_API_KEY not found in environment")
        return None

    # Verify that the key is valid. TheHive 5 accepts Bearer token.
    try:
        r = requests.get(
            f"{THEHIVE_URL}/api/user/current",
            headers={HEADER_AUTHORIZATION: f"{AUTH_BEARER_PREFIX} {THEHIVE_API_KEY}"},
            timeout=10,
        )
        if r.ok:
            logger.info("[OK] Valid TheHive API key")
            return THEHIVE_API_KEY
        else:
            logger.warning(f"[WARN] TheHive API key invalid: HTTP {r.status_code}")
            return None
    except Exception as e:
        logger.warning(f"[WARN] Error checking TheHive API key: {e}")
        return None


def preserve_cortex_credentials():
    """Preserve the current Cortex credentials."""
    # Cortex does NOT support Bearer/API key auth — only Basic auth.
    # Use admin credentials from .env.full to verify connectivity.
    import base64

    cortex_user = os.environ.get("CORTEX_ADMIN_USER", "admin")
    cortex_pass = os.environ.get("CORTEX_ADMIN_PASSWORD", "")

    if not cortex_pass:
        logger.warning("[WARN] CORTEX_ADMIN_PASSWORD not found in environment")
        return None

    try:
        credentials = base64.b64encode(f"{cortex_user}:{cortex_pass}".encode()).decode()
        r = requests.get(
            f"{CORTEX_URL}/api/user/current",
            headers={HEADER_AUTHORIZATION: f"{AUTH_BASIC_PREFIX} {credentials}"},
            timeout=10,
        )
        if r.ok:
            logger.info("[OK] Valid Cortex credentials (Basic auth)")
            return {"user": cortex_user, "password": cortex_pass}
        else:
            logger.warning(f"[WARN] Cortex credentials invalid: HTTP {r.status_code}")
            return None
    except Exception as e:
        logger.warning(f"[WARN] Error checking Cortex credentials: {e}")
        return None


def preserve_shuffle_credentials():
    """Preserve the current Shuffle API key."""
    if not SHUFFLE_API_KEY:
        logger.warning("[WARN] SHUFFLE_DEFAULT_APIKEY not found in environment")
        return None

    # Shuffle API key is generated on every fresh deploy, there is no point in preserving it
    # We only save it if it exists
    logger.info("[INFO] Shuffle API key: set")
    return SHUFFLE_API_KEY


def preserve_grafana_credentials():
    """Preserve Grafana credentials."""
    # Grafana uses static credentials, not rotating API keys
    # We only save current credentials
    logger.info(f"[INFO] Grafana credentials: {GRAFANA_USER} / <redacted>")
    return {"user": GRAFANA_USER, "password": GRAFANA_PASS}


def main():
    """Main function."""
    print("=" * 60)
    print("PRESERVING SOAR SERVICES CREDENTIALS")
    print("=" * 60)

    credentials = {
        "thehive_api_key": preserve_thehive_credentials(),
        "cortex_credentials": preserve_cortex_credentials(),
        "shuffle_api_key": preserve_shuffle_credentials(),
        "grafana": preserve_grafana_credentials(),
        "timestamp": None,  # Will be added when saving
    }

    # Save to file
    from datetime import datetime

    credentials["timestamp"] = datetime.now().isoformat()

    # Create directory if it does not exist
    for _ in range(5):
        try:
            CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
            break
        except FileExistsError as e:
            p = Path(e.filename)
            if p.exists() and not p.is_dir():
                p.unlink()
                continue
            raise

    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(credentials, f, indent=2)

    print(f"[OK] Credentials saved in: {CREDENTIALS_FILE}")
    print(
        f"[INFO] Manual copy to host required: docker cp"
        f" soar_api:{CREDENTIALS_FILE} {CREDENTIALS_FILE_HOST}"
    )

    print("=" * 60)
    print("PRESERVATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
