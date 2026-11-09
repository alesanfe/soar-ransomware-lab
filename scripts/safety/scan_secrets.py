#!/usr/bin/env python3
"""BL-SEC-013: repository secret scanner.

Scans tracked files (``git ls-files``, falling back to a directory walk
outside git contexts) for high-confidence secret patterns — private key
blocks, cloud provider keys, and ``KEY=value`` assignments with
non-placeholder values. Exits non-zero when findings exist so CI can
gate on it.

Allowlist markers:
  - a line containing ``# nosecret`` is skipped (documented exception)
  - placeholder values (``changeme``, ``example``, ``<...>``, env-var
    references like ``${VAR}``/``$VAR``) are not findings
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# High-confidence patterns — each is (name, regex).
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("generic-api-key", re.compile(r"\bapi[_-]?key['\"]?\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,})['\"]?", re.I)),
    ("generic-secret", re.compile(r"\b(secret|password|passwd)['\"]?\s*[:=]\s*['\"]([^'\"\s]{8,})['\"]", re.I)),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
]

# File patterns always skipped (binary-ish or expected-secret metadata).
SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".whl", ".pyc", ".lock",
}
SKIP_PARTS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
# .env files are the sanctioned secret store — scanning them produces
# only noise; CI guards them via .gitignore instead.
SKIP_NAMES = {".env.full", ".env.container", ".env", ".env.testing", "package-lock.json"}

_PLACEHOLDER_RE = re.compile(
    r"^(changeme|change_me|example|placeholder|dummy|test|xxx+|<[^>]*>|"
    r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|your[_-].*|redacted|\*+)$",
    re.IGNORECASE,
)
# ALL_CAPS_SNAKE (case-SENSITIVE — must live outside the IGNORECASE
# regex) is an env-var name reference, not a secret value.
_ENVVAR_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{5,}$")


def _tracked_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode == 0:
            return [ROOT / line for line in out.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError):
        pass
    return [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and not any(part in SKIP_PARTS for part in p.parts)
    ]


def _is_placeholder(value: str) -> bool:
    value = value.strip()
    return bool(_PLACEHOLDER_RE.match(value)) or bool(_ENVVAR_NAME_RE.match(value))


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return [(lineno, pattern-name, line)] findings for one file."""
    findings: list[tuple[int, str, str]] = []
    if path.suffix.lower() in SKIP_SUFFIXES or path.name in SKIP_NAMES:
        return findings
    if any(part in SKIP_PARTS for part in path.parts):
        return findings
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings
    for lineno, line in enumerate(text.splitlines(), start=1):
        if "# nosecret" in line:
            continue
        for name, pattern in PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            captured = match.group(match.lastindex or 0)
            if _is_placeholder(captured):
                continue
            # `api_key = some_generator()` assigns a call result, not a
            # literal — the captured identifier is a function name.
            rest = line[match.end() :].lstrip()
            if rest.startswith("("):
                continue
            # pytest fixtures and test doubles are not real credentials —
            # require a pattern hit on a non-test path OR an explicit
            # high-entropy signature (aws/github/slack/private-key).
            if (
                name in {"generic-api-key", "generic-secret"}
                and ("test" in path.parts or "tests" in path.parts)
            ):
                continue
            findings.append((lineno, name, line.strip()[:120]))
            break
    return findings


def main() -> int:
    files = _tracked_files()
    findings: list[tuple[Path, int, str, str]] = []
    for path in files:
        for lineno, name, line in scan_file(path):
            findings.append((path, lineno, name, line))

    for path, lineno, name, line in findings:
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        print(f"{rel}:{lineno}: [{name}] {line}")
    if findings:
        print(f"\n{len(findings)} potential secret(s) found. Remove them or mark a")
        print("documented false positive with a trailing '# nosecret' comment.")
        return 1
    print(f"scanned {len(files)} files — no secrets found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
