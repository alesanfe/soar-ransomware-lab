#!/usr/bin/env python3
"""UI-GLOBAL-001: validate that every published host port has an entry in
docs/ui-inventory.json — and that no inventory entry points at a port that is
not actually published.

Usage: python scripts/quality/check_ui_inventory.py [--compose-files f1 f2 ...]

Exit 0 on full coverage, 1 on drift.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs" / "ui-inventory.json"


def published_ports() -> set[int]:
    """Ports published by the running compose stack (authoritative)."""
    out = subprocess.run(
        ["docker", "ps", "--format", "{{.Ports}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    ports = set()
    for m in re.finditer(r"(?:0\.0\.0\.0|127\.0\.0\.1):(\d+)->", out):
        ports.add(int(m.group(1)))
    return ports


def inventory_ports() -> dict[int, str]:
    inv = json.loads(INVENTORY.read_text())
    found: dict[int, str] = {}
    for s in inv["surfaces"]:
        for p in str(s["port"]).split(","):
            p = p.strip()
            if p.isdigit():
                found[int(p)] = s["id"]
    return found


def main() -> int:
    published = published_ports()
    if not published:
        print("ERROR: no published ports found — is the stack up?")
        return 1
    inv = inventory_ports()
    missing = published - set(inv)
    stale = set(inv) - published
    for p in sorted(missing):
        print(f"MISSING  :{p} published but not in docs/ui-inventory.json")
    for p in sorted(stale):
        print(f"STALE    :{p} in inventory ({inv[p]}) but not published")
    if missing or stale:
        print(f"\ncoverage: {len(set(inv) & published)}/{len(published)} — FAIL")
        return 1
    print(f"coverage: {len(published)}/{len(published)} published ports inventoried — OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
