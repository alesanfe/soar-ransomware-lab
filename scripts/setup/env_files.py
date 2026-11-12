#!/usr/bin/env python3
"""Propagate rotated credentials to the container env snapshot.

``build_local_env.py`` generates ``.env.container`` as a snapshot of
``.env.full``; the API container mounts it read-only and the test suite loads
it from there. Rotation scripts historically rewrote only ``.env.full``, so
containers kept authenticating with the previous key until the next
``make up`` (BUG-062). This helper applies a ``KEY=value`` substitution (or
append) to ``.env.full`` **and** to ``.env.container`` when it exists next to
it.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

CONTAINER_ENV_NAME = ".env.container"


def _apply(content: str, key: str, value: str) -> str:
    """Replace ``key=...`` in *content* or append the line when absent."""
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(content):
        return pattern.sub(f"{key}={value}", content)
    return content.rstrip("\n") + f"\n{key}={value}\n"


def update_env_files(
    pairs: dict[str, str],
    env_file: str | Path = ".env.full",
) -> list[Path]:
    """Write *pairs* into ``.env.full`` and its sibling ``.env.container``.

    Args:
        pairs: ``{KEY: value}`` substitutions to apply to both files.
        env_file: Path of the primary env file (``config.ENV_FILE`` callers
            pass their resolved path here).

    Returns:
        List of paths actually written (``[]`` when *env_file* is missing).
    """
    env_path = Path(env_file)
    if not env_path.exists():
        return []

    container_path = env_path.parent / CONTAINER_ENV_NAME
    targets = [env_path]
    if container_path.exists():
        targets.append(container_path)

    for target in targets:
        content = target.read_text(encoding="utf-8")
        for key, value in pairs.items():
            content = _apply(content, key, value)
        target.write_text(content, encoding="utf-8")
        _chmod_600(target)
    return targets


def _chmod_600(path: Path) -> None:
    """Restrict env files holding real secrets to owner-only (ISO A.8 /
    NIST 800-57 key protection). Best-effort: no-op where POSIX modes do
    not apply (Windows NTFS) or the chmod fails."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
