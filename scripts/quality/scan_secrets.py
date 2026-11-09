#!/usr/bin/env python3
"""Secret-exposure scanner for the SOAR Ransomware Lab (SOAR-019).

Three modes:

- ``repo``   — scan tracked files for assignments that look like real
               credentials (high-entropy values next to secret-like names).
               Placeholders (``changeme``, ``example``, ``xxx``...) are
               ignored; ``.env.example`` values are expected placeholders.
- ``logs``   — grep running ``soar_*`` container logs for sensitive values
               taken from ``.env.full`` / ``.env.container``.
- ``images`` — inspect local ``soar*`` / ``shuffle*`` images for secret
               values baked into ENV layers.

Exit code: 0 when clean, 1 when findings exist. Usage:

    python scripts/quality/scan_secrets.py [--mode repo|logs|images|all]
"""

from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

SECRET_NAME = re.compile(
    r"(?i)(api[_-]?key|secret|password|passwd|token|credential|private[_-]?key)"
)
ASSIGNMENT = re.compile(
    r"""(?ix)
    (?:^|[\s"'{,;])
    (?P<name>[A-Za-z0-9_.\-]*?(?:api[_-]?key|secret|password|passwd|token)[A-Za-z0-9_.\-]*)
    \s*[:=]\s*
    (?P<quote>["']?)(?P<value>[A-Za-z0-9+/=_@.\-]{12,})(?P=quote)
    """
)

# Config-style files accept unquoted secrets; code files require a quoted
# literal so identifiers like `api_key = self.api_key` are not flagged.
CONFIG_EXTS = {".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".env", ".conf"}
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

PLACEHOLDER = re.compile(
    r"(?i)(changeme|change_me|example|placeholder|your[_-]|xxx|\.\.\.|<.*>|"
    r"REPLACE|dummy|sample|fake|test[_-]|[_-]test|notreal|admin123|"
    r"password123|secretlab|lab2024|different[_-]|fixture)"
)

TEXT_EXTS = {
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
    ".md",
    ".txt",
    ".sh",
    ".ps1",
    ".bat",
    ".conf",
    ".html",
    ".js",
    ".ts",
}
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "runtime",
    "artifacts",
    "reports",
    ".mypy_cache",
    ".pytest_cache",
    "site-packages",
}
# Files whose secrets are expected/local-only (gitignored or sample data)
ALLOWED_FILES = {".env", ".env.full", ".env.container", ".env.testing", ".env.example"}


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    return -sum((c / len(s)) * math.log2(c / len(s)) for c in counts.values())


def _load_sensitive_values() -> list[str]:
    """Collect real secret values from the canonical env files."""
    values: list[str] = []
    for name in (".env.full", ".env.container"):
        path = ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^([A-Z0-9_]+)=(.*)$", line.strip())
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if SECRET_NAME.search(key) and len(val) >= 12 and not PLACEHOLDER.search(val):
                values.append(val)
    return sorted(set(values), key=len, reverse=True)


def scan_repo() -> int:
    findings = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            rel = fpath.relative_to(ROOT)
            if fname in ALLOWED_FILES or fpath.suffix.lower() not in TEXT_EXTS:
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            is_config = fpath.suffix.lower() in CONFIG_EXTS
            for lineno, line in enumerate(text.splitlines(), 1):
                for m in ASSIGNMENT.finditer(line):
                    value = m.group("value")
                    if not is_config and not m.group("quote"):
                        continue  # unquoted value in code -> identifier/call
                    if IDENTIFIER.fullmatch(value):
                        continue  # variable name, not a literal secret
                    if PLACEHOLDER.search(value) or _entropy(value) < 3.5:
                        continue
                    print(f"FIND  {rel}:{lineno}  {m.group('name')} = <redacted>")
                    findings += 1
    print(f"\nrepo scan: {findings} potential secret(s)")
    return findings


def scan_logs() -> int:
    secrets = _load_sensitive_values()
    if not secrets:
        print("SKIP  logs scan: no env file found to derive secrets from")
        return 0
    proc = subprocess.run(
        ["docker", "ps", "--filter", "name=soar_", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    containers = [c for c in proc.stdout.split() if c]
    if not containers:
        print("SKIP  logs scan: no soar_* containers running")
        return 0
    findings = 0
    for name in containers:
        logs = subprocess.run(
            ["docker", "logs", "--tail", "5000", name],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=60,
        )
        blob = (logs.stdout or "") + (logs.stderr or "")
        hits = sum(1 for s in secrets if s in blob)
        if hits:
            print(f"FIND  {name}: {hits} sensitive value(s) present in logs")
            findings += hits
    print(f"\nlogs scan: {findings} leaked value(s) across {len(containers)} containers")
    return findings


def scan_images() -> int:
    secrets = _load_sensitive_values()
    proc = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    images = [i for i in proc.stdout.split() if i and "soar" in i]
    if not images:
        print("SKIP  images scan: no local soar* images")
        return 0
    findings = 0
    for image in images:
        inspect = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=30,
        )
        hits = sum(1 for s in secrets if s and s in inspect.stdout)
        if hits:
            print(f"FIND  {image}: {hits} sensitive value(s) baked into image ENV")
            findings += hits
    print(f"\nimages scan: {findings} leaked value(s) across {len(images)} images")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["repo", "logs", "images", "all"], default="all")
    args = parser.parse_args()
    total = 0
    if args.mode in ("repo", "all"):
        total += scan_repo()
    if args.mode in ("logs", "all"):
        total += scan_logs()
    if args.mode in ("images", "all"):
        total += scan_images()
    if total:
        print(
            "\nACTION REQUIRED: rotate any real credential found above, scrub\n"
            "the file/log/image, and treat '.env.full' committed in git history\n"
            "as exposed (see docs/04-operations.md 'secret exposure procedure')."
        )
        return 1
    print("\nNo secret exposure detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
