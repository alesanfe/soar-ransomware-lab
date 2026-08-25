"""Credential provider — validate passwords and resolve API keys.

The rest of the system asks this module for the keys it needs and never
knows *how* they were obtained (env var, .env file, Docker exec, etc.).
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time

from . import config, env_files

logger = logging.getLogger(__name__)


# ── Public API ─────────────────────────────────────────────────────────────────


def validate_required_passwords() -> None:
    """Exit if any mandatory password is missing."""
    config.check_required_passwords()


def fetch_thehive_key() -> str:
    """Return the TheHive API key persisted by ``init_thehive.py``."""
    # Wait for the file to be updated by init_thehive.py
    for _ in range(15):
        if os.path.exists(config.ENV_FILE):
            with open(config.ENV_FILE) as f:
                content = f.read()
            m = re.search(r"^THEHIVE_API_KEY=(.+)$", content, re.MULTILINE)
            if m:
                existing = m.group(1).strip().strip('"')
                if len(existing) > 10:
                    logger.info("[key] TheHive API key (from %s)", config.ENV_FILE)
                    return existing
        time.sleep(2)

    key_env = os.environ.get("THEHIVE_API_KEY", "")
    if key_env and len(key_env) > 10:
        logger.info("[key] TheHive API key (from THEHIVE_API_KEY env)")
        return key_env
    logger.warning(
        "[key] WARN: no THEHIVE_API_KEY in %s — run init_thehive.py first", config.ENV_FILE
    )
    return ""


def fetch_cortex_key() -> str:
    """Return the Cortex API key saved by ``reset_cortex.py`` in .env."""
    for _ in range(15):
        if os.path.exists(config.ENV_FILE):
            with open(config.ENV_FILE) as f:
                content = f.read()
            m = re.search(r"^CORTEX_API_KEY=(.+)$", content, re.MULTILINE)
            if m:
                existing = m.group(1).strip().strip('"')
                if len(existing) > 10:
                    logger.info("[key] Cortex API key (from %s)", config.ENV_FILE)
                    return existing
        time.sleep(2)

    key_env = os.environ.get("CORTEX_API_KEY", "")
    if key_env and len(key_env) > 10:
        logger.info("[key] Cortex API key (from CORTEX_API_KEY env)")
        return key_env
    logger.warning(
        "[key] WARN: no CORTEX_API_KEY in %s — run reset_cortex.py first", config.ENV_FILE
    )
    return ""


def fetch_misp_key(admin_email: str) -> str:
    """Get the MISP API key — first from env, then via docker exec."""
    # 1. Env var directa
    key_env = os.environ.get("MISP_API_KEY", "")
    if len(key_env) == 40 and key_env.isalnum():
        logger.info("[key] MISP API key (from MISP_API_KEY env)")
        return key_env
    if key_env:
        logger.warning("[key] WARN: MISP_API_KEY must have 40 alphanumeric characters")
    # 2. Read from .env
    if os.path.exists(config.ENV_FILE):
        with open(config.ENV_FILE) as f:
            content = f.read()
        m = re.search(r"^MISP_API_KEY=(.+)$", content, re.MULTILINE)
        if m:
            existing = m.group(1).strip()
            if len(existing) == 40 and existing.isalnum():
                logger.info("[key] MISP API key (from %s)", config.ENV_FILE)
                return existing
            logger.warning("[key] WARN: MISP_API_KEY in %s has invalid format", config.ENV_FILE)
    # 3. Fallback: docker exec in soar_misp_db
    db_user = os.environ.get("MISP_DB_USER", "misp")
    db_pass = os.environ.get("MISP_DB_PASSWORD", "")
    db_name = os.environ.get("MISP_DB_NAME", "misp")
    db_container = os.environ.get("MISP_DB_CONTAINER", "soar_misp_db")
    try:
        # Validate email format to prevent SQL injection via docker exec.
        # MISP admin emails are always simple RFC-like addresses; reject
        # anything containing quotes, semicolons, or shell metacharacters.
        if not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", admin_email):
            logger.warning("[key] WARN: invalid MISP admin email format, skipping DB query")
            return ""
        # nosec B603 B607 — admin_email is validated by regex above
        sql = f"SELECT authkey FROM users WHERE email='{admin_email}' LIMIT 1;"
        res = subprocess.run(
            [
                "docker",
                "exec",
                db_container,
                "mysql",
                f"-u{db_user}",
                f"-p{db_pass}",
                db_name,
                "-e",
                sql,
                "-s",
                "--skip-column-names",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        key = res.stdout.strip()
        if key and len(key) > 10:
            logger.info("[key] MISP API key via DB")
            return key
    except Exception as e:
        logger.error("[key] MISP DB exception: %s", e)
    logger.warning("[key] WARN: could not get MISP API key")
    return ""


def fetch_password_from_env(key: str, default: str = "") -> str:
    """Fetch a password from .env.full (delegates to env_files)."""
    return env_files.read_key(key, default)


def save_keys(thehive_key: str, cortex_key: str, misp_key: str) -> None:
    """Persist API keys to env files (delegates to env_files)."""
    env_files.save_keys_to_env(thehive_key, cortex_key, misp_key)


def resolve_all_keys() -> tuple[str, str, str]:
    """Fetch TheHive, Cortex and MISP API keys.

    Returns ``(thehive_key, cortex_key, misp_key)``. Raises
    ``RuntimeError`` if TheHive key is missing (hard requirement).
    """
    thehive_key = fetch_thehive_key()
    cortex_key = fetch_cortex_key()
    misp_key = fetch_misp_key(config.MISP_ADMIN_EMAIL)

    if not thehive_key:
        logger.error("[key] ERROR: could not get TheHive API key")
        raise RuntimeError("Could not get TheHive API key — run init_thehive.py first")

    try:
        save_keys(thehive_key, cortex_key, misp_key)
    except (OSError, PermissionError) as e:
        logger.warning("Could not save keys in .env.full: %s", e)
        logger.warning("Continuing with the obtained keys...")

    return thehive_key, cortex_key, misp_key
