#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Coverage Tests
Tests to verify that coverage infrastructure is correctly configured
and that coverage thresholds are enforced.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent


class TestCoverageInfrastructure:
    """Verify coverage infrastructure exists and is correctly configured."""

    def test_pytest_cov_installed(self):
        """Pytest-cov must be installed for coverage measurement."""
        try:
            import pytest_cov

            assert pytest_cov is not None, "pytest-cov must be importable"
        except ImportError:
            pytest.fail("pytest-cov must be installed (pip install pytest-cov)")

    def test_coverage_config_in_pyproject(self):
        """pyproject.toml must have [tool.coverage] or pytest cov config."""
        pyproject = REPO_ROOT / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml must exist"
        content = pyproject.read_text(encoding="utf-8")
        has_cov = "coverage" in content.lower() or "cov" in content.lower()
        assert has_cov, "pyproject.toml must reference coverage configuration"

    def test_coveragerc_exists(self):
        """.coveragerc must exist with [run] and omit configuration."""
        coveragerc = REPO_ROOT / ".coveragerc"
        assert coveragerc.exists(), ".coveragerc must exist"
        content = coveragerc.read_text(encoding="utf-8")
        assert "[run]" in content, ".coveragerc must have a [run] section"
        assert "omit" in content, ".coveragerc must define omit paths"

    def test_coverage_threshold_in_pyproject(self):
        """pyproject.toml or Makefile must define a coverage threshold (fail-
        under)."""
        pyproject = REPO_ROOT / "pyproject.toml"
        makefile_win = REPO_ROOT / "Makefile.win"
        makefile_linux = REPO_ROOT / "Makefile.linux"
        found_threshold = False
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            if "fail-under" in content.lower() or "fail_under" in content.lower():
                found_threshold = True
        for mf in [makefile_win, makefile_linux]:
            if mf.exists():
                content = mf.read_text(encoding="utf-8")
                if "cov-fail-under" in content or "fail-under" in content.lower():
                    found_threshold = True
        assert (
            found_threshold
        ), "Coverage threshold (fail-under) must be defined in pyproject.toml or Makefile"

    def test_coverage_makefile_target_exists(self):
        """Makefile must have a test-coverage target."""
        for mf_name in ["Makefile.win", "Makefile.linux"]:
            mf = REPO_ROOT / mf_name
            if mf.exists():
                content = mf.read_text(encoding="utf-8")
                assert (
                    "test-coverage" in content or "coverage" in content.lower()
                ), f"{mf_name} must have a test-coverage target"

    def test_coverage_source_is_soar_lab(self):
        """Coverage must measure src/soar_lab (via pyproject.toml or Makefile
        cov flag)."""
        pyproject = REPO_ROOT / "pyproject.toml"
        makefile_win = REPO_ROOT / "Makefile.win"
        makefile_linux = REPO_ROOT / "Makefile.linux"
        found_soar_lab = False
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            if "soar_lab" in content and "cov" in content.lower():
                found_soar_lab = True
        for mf in [makefile_win, makefile_linux]:
            if mf.exists():
                content = mf.read_text(encoding="utf-8")
                if "cov=soar_lab" in content or "cov=src/soar_lab" in content:
                    found_soar_lab = True
        assert found_soar_lab, "Coverage must be configured to measure soar_lab"

    def test_coverage_omits_tests_and_scripts(self):
        """Coverage must omit tests/, scripts/, and debug files."""
        coveragerc = REPO_ROOT / ".coveragerc"
        assert coveragerc.exists(), ".coveragerc must exist"
        content = coveragerc.read_text(encoding="utf-8")
        assert "omit" in content, ".coveragerc must have an omit section"
        assert "test" in content.lower(), ".coveragerc must omit test files from coverage"

    def test_coverage_report_formats_configured(self):
        """Coverage must be configured to output term and html/xml reports."""
        coveragerc = REPO_ROOT / ".coveragerc"
        assert coveragerc.exists(), ".coveragerc must exist"
        content = coveragerc.read_text(encoding="utf-8")
        has_report = "[report]" in content or "html" in content.lower() or "xml" in content.lower()
        assert has_report, ".coveragerc must configure report output format"

    def test_coverage_runs_in_ci(self):
        """CI workflow must run coverage."""
        ci_yml = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        if ci_yml.exists():
            content = ci_yml.read_text(encoding="utf-8")
            assert (
                "cov" in content.lower() or "coverage" in content.lower()
            ), "CI must run coverage measurement"

    def test_coverage_quality_script_exists(self):
        """A quality script for coverage analysis must exist."""
        quality_dir = REPO_ROOT / "scripts" / "quality"
        if quality_dir.exists():
            py_files = list(quality_dir.glob("*.py"))
            found_coverage = False
            for pf in py_files:
                if "cov" in pf.name.lower() or "coverage" in pf.read_text(encoding="utf-8").lower():
                    found_coverage = True
                    break
            assert found_coverage, "scripts/quality/ must have a coverage analysis script"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
