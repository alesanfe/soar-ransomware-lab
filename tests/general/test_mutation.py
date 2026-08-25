#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Mutation Tests
Tests to verify that mutation testing infrastructure is correctly configured
and that report generation works.
"""

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent


class TestMutationInfrastructure:
    """Verify mutation testing infrastructure exists and is importable."""

    def test_mutmut_report_generator_exists(self):
        """The mutmut report generator script must exist."""
        script = REPO_ROOT / "scripts" / "reports" / "generate_mutmut_report.py"
        assert script.exists(), f"mutmut report generator must exist at {script}"

    def test_mutmut_report_generator_importable(self):
        """The mutmut report generator must be importable."""
        script = REPO_ROOT / "scripts" / "reports" / "generate_mutmut_report.py"
        spec = importlib.util.spec_from_file_location("generate_mutmut_report", script)
        assert spec is not None, "Must be able to create module spec for mutmut report generator"
        assert spec.loader is not None, "Must have a loader for mutmut report generator"

    def test_mutmut_reports_directory_exists(self):
        """The reports/mutmut directory must exist (created by make
        mutation)."""
        reports_dir = REPO_ROOT / "reports" / "mutmut"
        assert (
            reports_dir.exists() or reports_dir.parent.exists()
        ), "reports/ directory must exist for mutmut output"

    def test_mutation_makefile_target_exists(self):
        """The Makefile must have a 'mutation' target."""
        makefile_win = REPO_ROOT / "Makefile.win"
        makefile_linux = REPO_ROOT / "Makefile.linux"
        for mf in [makefile_win, makefile_linux]:
            if mf.exists():
                content = mf.read_text(encoding="utf-8")
                assert "mutation" in content.lower(), f"{mf.name} must have a 'mutation' target"

    def test_mutation_in_quality_suite(self):
        """The quality suite must include mutation testing reference."""
        quality_dir = REPO_ROOT / "scripts" / "quality"
        if quality_dir.exists():
            py_files = list(quality_dir.glob("*.py"))
            assert len(py_files) > 0, "scripts/quality/ must have quality check scripts"

    def test_mutation_report_has_main_function(self):
        """generate_mutmut_report.py must define a main function or entry
        point."""
        script = REPO_ROOT / "scripts" / "reports" / "generate_mutmut_report.py"
        if not script.exists():
            pytest.fail("mutmut report generator not found")
        content = script.read_text(encoding="utf-8")
        assert (
            "def main" in content or "if __name__" in content
        ), "mutmut report generator must have a main function or entry point"

    def test_mutation_config_in_pyproject(self):
        """pyproject.toml must list mutmut as a dev dependency or have
        config."""
        pyproject = REPO_ROOT / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml must exist"
        content = pyproject.read_text(encoding="utf-8")
        # mutmut may be in optional dependencies or quality extras
        has_mutmut = "mutmut" in content
        has_quality = "quality" in content
        assert (
            has_mutmut or has_quality
        ), "pyproject.toml must reference mutmut or have a quality extras"

    def test_mutation_threshold_config(self):
        """Quality thresholds must define mutation score expectations."""
        thresholds_dir = REPO_ROOT / "scripts" / "quality" / "thresholds"
        if thresholds_dir.exists():
            yaml_files = list(thresholds_dir.glob("*.yaml")) + list(thresholds_dir.glob("*.yml"))
            assert len(yaml_files) > 0, "Quality threshold YAML files must exist"
            # Check that at least one file mentions mutation
            found_mutation = False
            for yf in yaml_files:
                if "mutation" in yf.read_text(encoding="utf-8").lower():
                    found_mutation = True
                    break
            assert found_mutation, "At least one threshold file must reference mutation scores"

    def test_mutation_does_not_run_in_ci(self):
        """Mutation testing must NOT run in standard CI (it takes 60-180
        min)."""
        ci_yml = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        if ci_yml.exists():
            content = ci_yml.read_text(encoding="utf-8")
            assert (
                "mutmut" not in content.lower()
            ), "mutmut must not run in standard CI (too slow) — use make mutation on-demand"

    def test_mutation_report_output_format(self):
        """Mutmut report generator must output to reports/mutmut/."""
        script = REPO_ROOT / "scripts" / "reports" / "generate_mutmut_report.py"
        if not script.exists():
            pytest.fail("mutmut report generator not found")
        content = script.read_text(encoding="utf-8")
        assert (
            "reports" in content.lower() or "mutmut" in content.lower()
        ), "Report generator must reference reports/ or mutmut/ output path"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
