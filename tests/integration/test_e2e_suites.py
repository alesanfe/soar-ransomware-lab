#!/usr/bin/env python3
"""Regression tests for scripts/ci/e2e_suites.py.

BUG-042: ``_prepare_suites`` parsed ``E2E_SUITE_START`` with a bare
``int()`` and used it as a list index — a non-numeric value crashed with
``ValueError`` and an out-of-range value with ``IndexError``, instead of
being ignored/clamped.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
_spec = importlib.util.spec_from_file_location(
    "e2e_suites", ROOT / "scripts" / "ci" / "e2e_suites.py"
)
suites_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(suites_mod)


def _suites(monkeypatch, n=5):
    monkeypatch.setattr(suites_mod, "discover_suites", lambda: [f"TC-{i:02d}" for i in range(n)])


def test_start_non_numeric_does_not_crash(monkeypatch):
    _suites(monkeypatch)
    monkeypatch.setenv("E2E_SUITE_START", "abc")
    assert suites_mod._prepare_suites() == [f"TC-{i:02d}" for i in range(5)]


def test_start_out_of_range_does_not_crash(monkeypatch):
    _suites(monkeypatch)
    monkeypatch.setenv("E2E_SUITE_START", "99")
    assert suites_mod._prepare_suites() == []


def test_start_valid_still_works(monkeypatch):
    _suites(monkeypatch)
    monkeypatch.setenv("E2E_SUITE_START", "3")
    assert suites_mod._prepare_suites() == ["TC-03", "TC-04"]


def test_kpi_suite_maps_to_real_make_target():
    """BUG-068: ``suite_to_target("TC-KPI-01")`` produced ``test-e2e-kpi01``
    but the Makefile defines ``test-e2e-kpi-01`` — all six KPI suites died
    with ``No rule to make target`` in the 2026-11-05 chain run."""
    assert suites_mod.suite_to_target("TC-KPI-01") == "test-e2e-kpi-01"
    assert suites_mod.suite_to_target("TC-KPI-06") == "test-e2e-kpi-06"
    assert suites_mod.suite_to_target("TC-04") == "test-e2e-tc04"
    assert suites_mod.suite_to_target("TC-33") == "test-e2e-tc33"


def test_all_discovered_suites_have_make_targets():
    """Every suite dir must map to a target that exists in Makefile.win —
    the same check e2e_suites.py's validator performs, kept green here."""
    import re

    makefile = (ROOT / "Makefile.win").read_text(encoding="utf-8")
    targets = set(re.findall(r"^(test-e2e[-a-z0-9]+):", makefile, re.MULTILINE))
    missing = {
        s: suites_mod.suite_to_target(s)
        for s in suites_mod.discover_suites()
        if suites_mod.suite_to_target(s) not in targets
    }
    assert not missing, f"Suites without make target: {missing}"


def test_makefile_pytest_selectors_exist():
    """BUG-069: every ``pytest "tests/e2e/...::Class::method"`` selector in
    Makefile.win must resolve to a real test node. In the 2026-11-05 chain
    run, 12 stale selectors (renamed/moved methods, one moved file) killed
    five suites mid-chain with ``ERROR: not found``."""
    import ast
    import re

    makefile = (ROOT / "Makefile.win").read_text(encoding="utf-8")
    selectors = re.findall(r'pytest "(tests/e2e/[^"]+)"', makefile)
    stale = []
    for sel in selectors:
        parts = sel.split("::")
        fpath = ROOT / parts[0]
        if not fpath.exists():
            stale.append((sel, "file missing"))
            continue
        if len(parts) < 3:
            continue
        tree = ast.parse(fpath.read_text(encoding="utf-8"))
        cls, meth = parts[1], parts[2]
        ok = any(
            isinstance(n, ast.ClassDef)
            and n.name == cls
            and any(
                isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == meth
                for m in n.body
            )
            for n in ast.walk(tree)
        )
        if not ok:
            stale.append((sel, "node missing"))
    assert not stale, f"Stale Makefile selectors: {stale}"


def test_stress_percentile_empty_data(monkeypatch):
    """BUG-043: StressTester.percentile([]) crashed with IndexError —
    index=-0.5 is not integral so it fell through to sorted_data[0] on an
    empty list. test_load._percentile has the empty guard; this one didn't."""
    spec = importlib.util.spec_from_file_location(
        "test_stress", ROOT / "tests" / "performance" / "test_stress.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.StressTester().percentile([], 50) == 0
