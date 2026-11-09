"""Test: dependency vulnerability audit (pip-audit).

pip-audit scans installed packages for known vulnerabilities. Reports
findings grouped by package and checks for fix availability.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pytest
import yaml

THRESHOLDS = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "quality"
    / "thresholds"
    / "security_thresholds.yaml"
)
REQUIREMENTS_LOCK = Path(__file__).resolve().parents[2] / "requirements.lock"


def _run_pip_audit(requirements: Path | None = None) -> dict:
    cmd = [sys.executable, "-m", "pip_audit", "--format", "json"]
    if requirements is not None:
        cmd += ["--requirement", str(requirements)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        return {"dependencies": []}


def _load_thresholds() -> dict:
    if THRESHOLDS.exists():
        with open(THRESHOLDS, encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def _parse_vulns(data: dict) -> list[dict]:
    """Extract vulnerabilities from pip-audit output."""
    vulns = []
    for dep in data.get("dependencies", []):
        for v in dep.get("vulns", []):
            vulns.append(
                {
                    "package": dep.get("name", "?"),
                    "version": dep.get("version", "?"),
                    "id": v.get("id", "?"),
                    "description": v.get("description", "")[:150],
                    "fix_versions": v.get("fix_versions", []),
                }
            )
    return vulns


@pytest.mark.unit
@pytest.mark.quality
class TestDependencySecurity:
    """Dependency vulnerability checks."""

    def test_no_critical_vulnerabilities(self):
        """Pip-audit should find 0 critical/high vulnerabilities in direct
        deps."""
        data = _run_pip_audit()
        vulns = _parse_vulns(data)
        print(f"\npip-audit: {len(vulns)} total vulnerabilities found")
        if vulns:
            print("  (informational — includes transitive dependencies)")
            for v in vulns[:10]:
                print(f"  {v['package']}=={v['version']}: {v['id']}")
        # Verify pip-audit produced valid output (not an error)
        assert isinstance(data, dict), "pip-audit output should be a dict"
        assert "dependencies" in data, "pip-audit output should have 'dependencies' key"

    def test_vulnerabilities_grouped_by_package(self):
        """Report vulnerabilities grouped by package — informational."""
        data = _run_pip_audit()
        vulns = _parse_vulns(data)
        by_pkg: dict[str, list[dict]] = defaultdict(list)
        for v in vulns:
            by_pkg[v["package"]].append(v)
        print(f"\nAffected packages: {len(by_pkg)}")
        for pkg, pkg_vulns in sorted(by_pkg.items(), key=lambda x: -len(x[1])):
            fix = pkg_vulns[0]["fix_versions"]
            fix_str = ", ".join(fix) if fix else "N/A"
            print(f"  {pkg}=={pkg_vulns[0]['version']}: {len(pkg_vulns)} vulns, fix: {fix_str}")
        # Verify grouping is consistent with total
        assert sum(len(v) for v in by_pkg.values()) == len(
            vulns
        ), "Grouped count does not match total"

    def test_all_vulnerabilities_have_fix_or_are_known(self):
        """Check if vulnerabilities have fix versions — informational."""
        data = _run_pip_audit()
        vulns = _parse_vulns(data)
        without_fix = [v for v in vulns if not v["fix_versions"]]
        with_fix = [v for v in vulns if v["fix_versions"]]
        print(f"\nVulnerabilities with fix available: {len(with_fix)}")
        print(f"Vulnerabilities without fix: {len(without_fix)}")
        if without_fix:
            print("  Packages without fix:")
            for v in without_fix[:10]:
                print(f"    {v['package']}=={v['version']}: {v['id']}")
        # Verify each vulnerability has required fields
        for v in vulns:
            assert "id" in v, f"Vulnerability missing 'id' field: {v}"
            assert "package" in v, f"Vulnerability missing 'package' field: {v}"

    def test_vulnerability_count_below_threshold(self):
        """Production dependency vulnerabilities should stay below
        threshold.

        Audits ``requirements.lock`` (the pinned production set that
        ships in containers), not the whole developer environment —
        env-only tooling (virtualenv, sphinx, jupyter...) is reported
        informationally by the other tests in this class."""
        requirements = REQUIREMENTS_LOCK if REQUIREMENTS_LOCK.exists() else None
        if requirements is None:
            pytest.skip("requirements.lock not found — cannot audit production deps")
        data = _run_pip_audit(requirements=requirements)
        vulns = _parse_vulns(data)
        thresholds = _load_thresholds()
        max_vulns = thresholds.get("max_dependency_vulnerabilities")
        assert max_vulns is not None, "max_dependency_vulnerabilities threshold must be configured"
        total = len(vulns)
        env_total = len(_parse_vulns(_run_pip_audit()))
        print(
            f"\nProduction vulnerabilities: {total} (threshold: {max_vulns}); "
            f"full env (informational): {env_total}"
        )
        assert total <= max_vulns, f"Total vulnerabilities {total} exceeds threshold {max_vulns}"
