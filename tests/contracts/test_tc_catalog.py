#!/usr/bin/env python3
"""A-01: conformance test for the declarative E2E catalog.

``tests/e2e/TC_catalog.yaml`` is the machine-readable inventory of every
E2E/KPI test case. This test keeps it honest:

  1. Every catalog entry's directory, file and test function exists.
  2. Every ``TC-*`` directory under ``tests/e2e`` appears in the catalog
     (no untracked suites).
  3. Every catalog ``make_target`` exists in ``Makefile.win``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = REPO_ROOT / "tests" / "e2e" / "TC_catalog.yaml"
# Inside soar_api only Makefile.linux is mounted; on the host both exist.
MAKEFILES = [REPO_ROOT / "Makefile.win", REPO_ROOT / "Makefile.linux"]


@pytest.fixture(scope="module")
def catalog() -> dict:
    return yaml.safe_load(CATALOG.read_text(encoding="utf-8"))


def test_catalog_parses(catalog):
    tcs = catalog["test_cases"]
    assert len(tcs) >= 40, f"catalog holds {len(tcs)} TCs — expected >= 40"
    assert all(tc.get("tests") for tc in tcs), "every TC must list >= 1 test"


def test_every_catalog_test_exists(catalog):
    missing = []
    for tc in catalog["test_cases"]:
        for t in tc["tests"]:
            f = REPO_ROOT / tc["dir"] / t["file"]
            if not f.exists():
                missing.append(f"{tc['id']}: file {t['file']} missing")
                continue
            src = f.read_text(encoding="utf-8")
            if f"def {t['name']}(" not in src:
                missing.append(f"{tc['id']}: test {t['name']} not in {t['file']}")
    assert not missing, "\n".join(missing[:20])


def test_every_e2e_dir_cataloged(catalog):
    on_disk = {
        d.name for d in (REPO_ROOT / "tests" / "e2e").iterdir()
        if d.is_dir() and d.name.startswith("TC-")
    }
    in_catalog = {tc["id"] for tc in catalog["test_cases"]}
    assert on_disk == in_catalog, (
        f"uncataloged: {sorted(on_disk - in_catalog)} "
        f"phantom: {sorted(in_catalog - on_disk)}"
    )


def test_every_disk_test_cataloged(catalog):
    """Reverse direction: no test_ function may exist on disk without a
    catalog entry (prevents partially-cataloged suites like TC-35 was)."""
    on_disk = {}
    for d in (REPO_ROOT / "tests" / "e2e").glob("TC-*"):
        if not d.is_dir():
            continue
        for f in d.glob("test_*.py"):
            on_disk.setdefault(d.name, set()).update(
                re.findall(r"def (test_\w+)\(", f.read_text(encoding="utf-8"))
            )
    uncataloged = []
    for tc_id, names in on_disk.items():
        cat_names = {
            t["name"]
            for tc in catalog["test_cases"]
            if tc["id"] == tc_id
            for t in tc["tests"]
        }
        for n in sorted(names - cat_names):
            uncataloged.append(f"{tc_id}: {n}")
    assert not uncataloged, f"tests on disk missing from catalog: {uncataloged[:20]}"


def test_every_catalog_target_in_makefile(catalog):
    mk_path = next((m for m in MAKEFILES if m.exists()), None)
    if mk_path is None:
        pytest.skip("no Makefile available in this environment")
    mk = mk_path.read_text(encoding="utf-8")
    targets = set(re.findall(r"^([a-zA-Z0-9_-]+):", mk, re.MULTILINE))
    missing = [
        tc["make_target"] for tc in catalog["test_cases"]
        if tc["make_target"] not in targets
    ]
    assert not missing, f"make targets missing: {missing}"
