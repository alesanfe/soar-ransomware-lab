#!/usr/bin/env python3
"""CI gate: Makefile.win and Makefile.linux must expose the same targets.

The root ``Makefile`` delegates by OS, so any target that exists on only
one side silently breaks the other platform. This gate fails the build
when the target sets drift apart — recipes may differ (POSIX vs Windows
shell), target *names* may not.

Usage::

    python scripts/ci/check_makefile_parity.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# ``name:`` but not ``name :=``/``name ::=``/``name =`` variable
# assignments — the lookahead rejects a colon followed by '=' or ':'.
TARGET_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:(?![:=])", re.MULTILINE)

FILES = ("Makefile.win", "Makefile.linux")


def targets(path: Path) -> set[str]:
    return set(TARGET_RE.findall(path.read_text(encoding="utf-8")))


def main() -> int:
    win = targets(ROOT / FILES[0])
    lin = targets(ROOT / FILES[1])
    ok = True
    for name, missing_in, present_in in (
        ("win-only", lin, win),
        ("linux-only", win, lin),
    ):
        only = present_in - missing_in
        if only:
            ok = False
            other = FILES[0] if name == "linux-only" else FILES[1]
            print(f"Targets only in {name.split('-')[0]} file, missing from {other}:")
            for t in sorted(only):
                print(f"  - {t}:")
    if not ok:
        print("\nMakefile target parity violated — port the missing targets.")
        return 1
    print(f"Makefile parity OK: {len(win)} targets on both sides.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
