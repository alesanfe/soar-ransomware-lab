"""Runtime environment helpers shared across modules."""

from __future__ import annotations

from pathlib import Path


def is_inside_container() -> bool:
    """Best-effort detection of whether we are running inside a Docker.

    container.
    """
    return Path("/.dockerenv").exists() or Path("/app").exists()
