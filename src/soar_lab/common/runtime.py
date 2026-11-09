"""Runtime environment helpers shared across modules."""

from __future__ import annotations

import os
from contextlib import suppress
from pathlib import Path


def is_inside_container() -> bool:
    """Best-effort detection of whether we are running inside a Docker.

    container.
    """
    return Path("/.dockerenv").exists() or Path("/app").exists()


def repo_root() -> Path:
    """Resolve the repository root from this module's location.

    ``common/runtime.py`` lives at ``src/soar_lab/common/`` — the repo
    root is four ancestors up (``common→soar_lab→src→repo``). Never uses
    the CWD: relative lookups silently break under different launch dirs.
    """
    return Path(__file__).resolve().parents[3]


def dotenv_lookup(env_file: Path, var_name: str) -> str:
    """Return ``var_name``'s value from a dotenv file, or ``""``.

    Strict ``KEY=value`` parsing: comments and blank lines are skipped, the
    key must match exactly (no substring matches), the first ``=`` splits
    key/value, and surrounding quotes are stripped.
    """
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition("=")
        if sep and key.strip() == var_name:
            return value.strip().strip("\"'")
    return ""


# Docker Swarm / Compose secrets mount point; ``DOCKER_SECRETS_DIR``
# overrides it for tests and non-Linux runtimes.
_SECRETS_DIR_ENV = "DOCKER_SECRETS_DIR"  # pragma: allowlist secret
_DEFAULT_SECRETS_DIR = Path("/run/secrets")


def _docker_secret(name: str) -> str:
    """Read a mounted Docker secret file, or ``""`` when absent/unreadable."""
    secrets_dir = Path(os.environ.get(_SECRETS_DIR_ENV, str(_DEFAULT_SECRETS_DIR)))
    with suppress(OSError):
        secret_file = secrets_dir / name
        if secret_file.is_file():
            return secret_file.read_text(encoding="utf-8", errors="replace").strip()
    return ""


def resolve_secret(*names: str, env_file: Path | None = None) -> str:
    """Resolve the first available secret among *names*, tier by tier.

    BL-SEC-012: single credential-resolution contract so callers stop
    re-implementing env/dotenv fallbacks. Precedence is checked across ALL
    names within one tier before moving to the next — an env var for an
    alias beats a file entry for the primary name:

      1. ``os.environ[<name>]`` (first non-empty, in order)
      2. Docker secrets mount ``/run/secrets/<name>``
         (or ``$DOCKER_SECRETS_DIR/<name>``)
      3. ``env_file`` (default ``repo_root() / ".env.full"``) via
         :func:`dotenv_lookup`

    Args:
        names: Candidate variable names, most specific first.
        env_file: Dotenv fallback file; defaults to the repo's
            ``.env.full``. Pass ``None``-like ``Path()`` to skip.

    Returns:
        The resolved value, or ``""`` when nothing resolves.
    """
    for name in names:
        value = os.environ.get(name, "")
        if value:
            return value
    for name in names:
        value = _docker_secret(name)
        if value:
            return value
    env_file = env_file if env_file is not None else repo_root() / ".env.full"
    for name in names:
        value = dotenv_lookup(env_file, name)
        if value:
            return value
    return ""
