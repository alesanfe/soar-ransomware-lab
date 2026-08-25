#!/usr/bin/env python3
"""Credential validation script.

Verifies that all credentials in .env.full match defaults in docker-
compose files and Python scripts.
"""

import logging
import re
import sys
from collections.abc import Callable
from pathlib import Path

from soar_lab.common.constants import (
    CRITICAL_CREDENTIAL_ENV_VARS,
    ENV_CORTEX_SECRET,
    ENV_ELASTIC_PASSWORD,
    ENV_THEHIVE_SECRET,
    PLACEHOLDER_VALUES,
)

logger = logging.getLogger(__name__)

__all__ = [
    "parse_env_file",
    "extract_defaults_from_docker_compose",
    "extract_defaults_from_python",
    "extract_hardcoded_values",
    "PLACEHOLDER_VALUES",
    "validate_credentials",
]

_RE_DOCKER = r"\$\{([A-Z_][A-Z0-9_]*):-(.*?)\}"
_RE_PYTHON = r'os\.environ\.get\(["\']([A-Z_][A-Z0-9_]*)["\'],\s*["\'](.*?)["\']\)'
_CONF_MAP = {
    "thehive.conf": [(ENV_THEHIVE_SECRET, r'"play":\s*\{\s*"secret":\s*"([^"]+)"')],
    "cortex.conf": [
        (ENV_CORTEX_SECRET, r'"play":\s*\{\s*"secret":\s*"([^"]+)"'),
        (ENV_ELASTIC_PASSWORD, r'"search":\s*\{[^}]*"password":\s*"([^"]+)"'),
    ],
}


def _read_text(p: Path) -> str:
    """Read file content as UTF-8 text, returning empty string if missing.

    This helper centralises the open/read pattern used by several
    extraction functions so that file-not-found handling is kept
    in a single place rather than duplicated across each caller.

    Returns the full file content as a string, or an empty string
    when the specified path does not exist on disk.

    Callers can safely pass the result to regex functions since an
    empty string produces no matches.
    """
    if not p.exists():
        return ""
    with open(p, encoding="utf-8") as f:
        return f.read()


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse .env file and return dict of variables.

    Reads a .env file line by line, skipping blank lines and comments,
    and returns a dictionary mapping variable names to their values.
    Returns an empty dict if the file does not exist.

    Each non-comment line containing ``=`` is split into a key-value
    pair, with both sides stripped of surrounding whitespace.

    Lines starting with ``#`` are treated as comments and skipped.
    Blank lines are also ignored. All other lines must contain an
    equals sign to be considered valid variable assignments.
    """
    if not env_path.exists():
        logger.error(f"ERROR: File {env_path} not found")
        return {}
    with open(env_path, encoding="utf-8") as f:
        return {
            k.strip(): v.strip()
            for raw in f
            if "=" in (line := raw.strip()) and not line.startswith("#")
            for k, v in [line.split("=", 1)]
        }


def extract_defaults_from_docker_compose(compose_path: Path) -> dict[str, str]:
    """Extract default env var values from docker-compose files.

    Scans for ``${VAR_NAME:-default_value}`` patterns and returns a
    mapping of variable names to their default values.

    Returns an empty dict when the file does not exist.

    The regex pattern used is ``$\\{VAR:-default\\}`` which matches
    the docker-compose variable interpolation syntax with defaults.
    """
    return dict(re.findall(_RE_DOCKER, _read_text(compose_path)))


def extract_defaults_from_python(script_path: Path) -> dict[str, str]:
    """Extract default env var values from Python scripts.

    Scans for ``os.environ.get("VAR_NAME", "default_value")`` patterns
    and returns a mapping of variable names to their defaults.

    Returns an empty dict when the file does not exist.

    The regex pattern matches both single and double quoted strings
    in the os.environ.get call, capturing the variable name and its
    default value as group 1 and group 2 respectively.
    """
    return dict(re.findall(_RE_PYTHON, _read_text(script_path)))


def extract_hardcoded_values(file_path: Path, patterns: list[str]) -> dict[str, str]:
    """Extract hardcoded values from config files.

    Applies each regex pattern to the file content and returns a mapping
    of matched keys to their values. When a match is a tuple, the first
    element is used as the key and the second as the value; otherwise
    the pattern itself is used as the key.

    Returns an empty dict when the file does not exist.

    This function is useful for finding hardcoded credentials in
    configuration files that should be synchronized with .env.full.
    """
    values = {}
    for pat in patterns:
        for m in re.findall(pat, _read_text(file_path)):
            key, val = (m[0], m[1]) if isinstance(m, tuple) else (pat, m)
            values[key] = val
    return values


def _sync_config_file(cp: Path, ev: dict[str, str]) -> list[str]:
    """Synchronize TheHive/Cortex config files with .env.full values.

    Returns a list of human-readable messages describing changes made
    to the config file to align hardcoded secrets with .env.full values.

    The function reads the config file, applies regex-based replacements
    for each known credential mapping, and writes back only when the
    content has actually changed.

    The credential mappings are defined in ``_CONF_MAP`` which maps
    config file names to lists of (env_key, regex) pairs. Each regex
    captures the current hardcoded value in the first capture group.
    """
    if not cp.exists():
        return []
    original = content = cp.read_text(encoding="utf-8")
    changes = []
    for env_key, regex in _CONF_MAP.get(cp.name, []):
        if env_key not in ev:
            continue
        for match in re.finditer(regex, content):
            old, new = match.group(1), ev[env_key]
            if old != new:
                mt = match.group(0)
                content = content.replace(mt, mt.replace(f'"{old}"', f'"{new}"', 1), 1)
                changes.append(f"{cp.name}: updated {env_key} value")
    if content != original:
        cp.write_text(content, encoding="utf-8")
    return changes


def _get_file_lists(rr: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """Return (docker_compose_files, python_scripts, config_files).

    Builds the three lists of files that need to be validated against
    the .env.full credentials, using path components relative to the
    repository root.

    The docker-compose files are located in the ``infra/docker/compose``
    directory, Python scripts in ``src/soar_lab/scripts/setup``, and
    config files in ``infra/docker`` with application-specific subdirs.
    """
    cd = rr / "infra" / "docker" / "compose"
    dc = [cd / f"docker-compose.{n}.yml" for n in ("core", "misp", "api")] + [
        cd / "logging" / "docker-compose.logging.yml"
    ]
    sd = rr / "src" / "soar_lab" / "scripts" / "setup"
    py = [
        sd / f"{n}.py"
        for n in (
            "init_thehive",
            "init_shuffle_webhook",
            "fix_org_users",
            "reset_cortex",
            "setup_analyzers_and_iocs",
        )
    ] + [
        rr
        / "src"
        / "soar_lab"
        / "infrastructure"
        / "external"
        / "integrations"
        / "cortex_client.py"
    ]
    cd2 = rr / "infra" / "docker"
    cf = [
        cd2 / "thehive.application.conf" / "thehive.conf",
        cd2 / "cortex.application.conf" / "cortex.conf",
    ]
    return dc, py, cf


def _validate_file_defaults(
    files: list[Path],
    ev: dict[str, str],
    cv: dict[str, str],
    extract_fn: Callable[[Path], dict[str, str]],
) -> tuple[list[str], list[str]]:
    """Validate a set of files against env vars. Returns (info, warnings).

    For each file, extracts default values using *extract_fn* and records
    informational messages when .env.full overrides a default, plus
    warnings for missing files.

    The *extract_fn* parameter is one of the ``extract_defaults_from_*``
    functions, selected by the caller based on the file type being
    validated (docker-compose or Python script).
    """
    info: list[str] = []
    warnings: list[str] = []
    for f in files:
        if not f.exists():
            warnings.append(f"File not found: {f}")
            continue
        defaults = extract_fn(f)
        logger.info(f"  {f.name}: {len(defaults)} defaults found")
        info.extend(
            f"{f.name}: {var} - .env.full overrides default '{defaults[var]}'"
            for var in cv
            if var in defaults and ev.get(var) != defaults[var]
        )
    return info, warnings


def _report_results(errors: list[str], warnings: list[str], info: list[str]) -> bool:
    """Log validation results and return success status.

    Outputs informational, warning, and error messages in order, then
    returns False if any errors were found, True otherwise.

    The final line indicates whether validation succeeded or failed.
    Errors indicate placeholder values that must be fixed, while
    warnings typically indicate missing files that were skipped.
    """
    for level, label, items in (
        ("info", "INFO", info),
        ("warning", "WARNING", warnings),
        ("error", "ERROR", errors),
    ):
        if not items:
            continue
        log = getattr(logger, level)
        log(f"\n[{label}] ({len(items)}):")
        for item in items:
            log(f"  - {item}")
    if errors:
        logger.error(
            "\n[FAIL] Validation failed: Credentials contain placeholders or are not synchronized"
        )
        return False
    logger.info("\n[OK] Validation successful: Credentials are valid and synchronized")
    return True


def validate_credentials() -> bool:
    """Validate that credentials are synchronized and not placeholders.

    Parses .env.full, checks for placeholder values, validates defaults
    in docker-compose and Python files, syncs config files, and reports
    results. Returns True if validation passes, False otherwise.

    This is the main entry point for the credential validation workflow.
    It orchestrates the individual validation steps by calling helper
    functions for each file type and aggregating their results.
    """
    rr = Path(__file__).parent.parent.parent.parent
    env_full = rr / ".env.full"
    logger.info("=== Credential Validation ===\n")
    ev = parse_env_file(env_full)
    if not ev:
        logger.error("ERROR: Could not read .env.full")
        return False
    logger.info(f"[OK] Read {len(ev)} variables from .env.full")

    dc, py, cf = _get_file_lists(rr)
    cv = list(CRITICAL_CREDENTIAL_ENV_VARS)
    errors = [
        f".env.full: {var} contains a placeholder or weak value"
        for var in cv
        if var in ev and ev[var].lower() in PLACEHOLDER_VALUES
    ]

    logger.info("\n--- Validating docker-compose files ---")
    di, dw = _validate_file_defaults(dc, ev, cv, extract_defaults_from_docker_compose)
    logger.info("\n--- Validating Python scripts ---")
    pi, pw = _validate_file_defaults(py, ev, cv, extract_defaults_from_python)
    logger.info("\n--- Validating config files ---")
    ci, cw = [], []
    for c in cf:
        if c.exists():
            ci.extend(_sync_config_file(c, ev))
        else:
            cw.append(f"File not found: {c}")

    return _report_results(errors, dw + pw + cw, di + pi + ci)


if __name__ == "__main__":
    sys.exit(0 if validate_credentials() else 1)
