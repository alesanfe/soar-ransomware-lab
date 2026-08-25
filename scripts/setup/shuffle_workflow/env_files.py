"""Repository for ``.env`` / ``.env.full`` files.

Reads and updates environment files without exposing the decision of
*which* keys are needed — that responsibility belongs to
:mod:`credentials`.
"""

from __future__ import annotations

import logging
import os
import re

from . import config

logger = logging.getLogger(__name__)


def get_env_file() -> str:
    """Return the highest-priority env file that exists (or the default)."""
    return config.ENV_FILE


def read_key(key: str, default: str = "") -> str:
    """Fetch a value from the priority env file."""
    env_file = config.ENV_FILE
    if os.path.exists(env_file):
        with open(env_file) as f:
            content = f.read()
        m = re.search(rf"^{key}=(.+)$", content, re.MULTILINE)
        if m:
            return m.group(1).strip().strip('"')
    return default


def _save_keys_to_env_file(thehive_key: str, cortex_key: str, misp_key: str, env_file: str) -> None:
    """Persist the API keys in a single .env file (idempotent)."""
    if not os.path.exists(env_file):
        return
    with open(env_file) as f:
        content = f.read()
    replacements = [
        ("THEHIVE_API_KEY", thehive_key),
        ("CORTEX_API_KEY", cortex_key),
        ("MISP_API_KEY", misp_key),
    ]
    for var, val in replacements:
        if not val:
            continue
        if re.search(rf"^{var}=", content, re.MULTILINE):
            content = re.sub(rf"^{var}=.*", f"{var}={val}", content, flags=re.MULTILINE)
        else:
            content += f"\n{var}={val}"
    try:
        with open(env_file, "w") as f:
            f.write(content)
        logger.info("[keys] Saved to %s", env_file)
    except (PermissionError, OSError) as e:
        logger.warning("[keys] WARN: could not write %s (%s). Keys only in memory.", env_file, e)


def save_keys_to_env(
    thehive_key: str, cortex_key: str, misp_key: str, env_file: str | None = None
) -> None:
    """Persist the API keys in .env and .env.full to reuse them without
    rotating."""
    target_files: list[str] = []
    if env_file:
        target_files.append(env_file)
    else:
        # Keep .env.full (container mount) and .env (docker compose env-file) in sync
        if os.path.exists("/app/.env.full"):
            target_files.append("/app/.env.full")
        elif os.path.exists(".env.full"):
            target_files.append(".env.full")
        if os.path.exists(".env"):
            target_files.append(".env")
    for target in set(target_files):
        _save_keys_to_env_file(thehive_key, cortex_key, misp_key, target)
