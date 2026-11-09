#!/usr/bin/env python3
"""ARC-003/006 — architectural fitness ratchet.

import-linter enforces the *direction* of dependencies. This test adds a
growth ratchet for function-level (lazy) imports of ``soar_lab`` inside
``src/``: they exist to break cycles, so the count must never grow — only
shrink as modules are properly decoupled.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "soar_lab"

# Baseline measured 2026-11-06 (79). Lower is better; raise → FAIL.
LAZY_IMPORT_BASELINE = 79

_LAZY = re.compile(r"^\s+(?:from|import)\s+soar_lab")


def _count_lazy_imports() -> tuple[int, list[str]]:
    total = 0
    offenders: list[str] = []
    for f in SRC.rglob("*.py"):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if _LAZY.match(line):
                total += 1
                offenders.append(f"{f.relative_to(ROOT)}:{i}")
    return total, offenders


def test_lazy_imports_do_not_grow():
    total, offenders = _count_lazy_imports()
    assert (
        total <= LAZY_IMPORT_BASELINE
    ), f"Lazy soar_lab imports grew {LAZY_IMPORT_BASELINE} → {total}. " f"New ones:\n" + "\n".join(
        offenders[-10:]
    )


def test_application_has_no_requests_import():
    """ARC-001 regression: application layer must not import requests."""
    app = SRC / "application"
    hits = [
        f
        for f in app.rglob("*.py")
        if re.search(r"^(?:from|import)\s+requests\b", f.read_text(encoding="utf-8"), re.MULTILINE)
    ]
    assert hits == [], f"requests imported in application layer: {hits}"


def test_domain_has_no_framework_imports():
    """Domain stays pure: no fastapi/requests/infrastructure imports."""
    dom = SRC / "domain"
    bad = []
    for f in dom.rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        for pat in (
            r"^(?:from|import)\s+fastapi\b",
            r"^(?:from|import)\s+requests\b",
            r"^(?:from|import)\s+soar_lab\.infrastructure",
        ):
            if re.search(pat, text, re.MULTILINE):
                bad.append(f.name)
                break
    assert bad == [], f"framework/infra imports in domain: {bad}"
