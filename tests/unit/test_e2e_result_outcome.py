"""Regression tests for BUG-065: result/TC artifacts must reflect the real
pytest outcome, not only the count of recorded assertions.

Before the fix, ``write_test_result`` derived ``status``/``all_passed`` solely
from ``self._assertions``.  A test that failed via a bare ``assert`` or an
exception (i.e. without calling ``record_assertion``) produced artifacts that
claimed ``PASSED`` while pytest reported ``FAILED`` — corrupting the evidence
bundle and every report generated from it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# tests/ is not a package; import the e2e base mixin directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "e2e"))

from base.run_context_mixin import RunContextMixin


def _make_instance(tmp_path: Path) -> RunContextMixin:
    """Create a minimal RunContextMixin instance with writable dirs."""
    inst = RunContextMixin()
    inst.e2e_results_dir = tmp_path / "e2e"
    inst.validation_results_dir = tmp_path / "results"
    inst.validation_results_dir.mkdir(parents=True, exist_ok=True)
    inst.test_name = "test_outcome"
    inst.workflow_name = "SOAR-Ransomware-Response"
    inst.tc_id = "TC-99"
    inst.create_run_context()
    return inst


def _read_result(inst: RunContextMixin) -> dict:
    return json.loads((inst.test_results_dir / "result.json").read_text(encoding="utf-8"))


def _read_tc_summary(inst: RunContextMixin) -> dict:
    tc_file = next(inst.validation_results_dir.glob("TC-99_*.json"))
    return json.loads(tc_file.read_text(encoding="utf-8"))


class TestArtifactReflectsPytestOutcome:
    """BUG-065: artifacts must not claim PASSED when pytest failed."""

    def test_unrecorded_pytest_failure_marks_result_failed(self, tmp_path: Path):
        """Bare assert/exception (no record_assertion) → artifact FAILED."""
        inst = _make_instance(tmp_path)
        inst.record_assertion("webhook_accepted", True)
        inst._pytest_failed = True  # set by the conftest makereport hook

        inst.write_test_result()

        result = _read_result(inst)
        assert result["all_passed"] is False

    def test_unrecorded_pytest_failure_marks_tc_summary_failed(self, tmp_path: Path):
        """The TC-*_*.json summary consumed by the e2e report must agree."""
        inst = _make_instance(tmp_path)
        inst.record_assertion("case_created", True)
        inst._pytest_failed = True

        inst.write_test_result()

        assert _read_tc_summary(inst)["status"] == "FAILED"

    def test_passing_test_still_reports_passed(self, tmp_path: Path):
        """Adjacent case: a genuine pass must not be poisoned by the flag."""
        inst = _make_instance(tmp_path)
        inst.record_assertion("case_created", True)

        inst.write_test_result()

        result = _read_result(inst)
        assert result["all_passed"] is True
        assert _read_tc_summary(inst)["status"] == "PASSED"

    def test_recorded_assertion_failure_marks_failed_without_flag(self, tmp_path: Path):
        """Recorded failures already worked — keep them working."""
        inst = _make_instance(tmp_path)
        inst.record_assertion("execution_success", False)

        inst.write_test_result()

        assert _read_result(inst)["all_passed"] is False

    def test_outcome_exposed_for_consumers(self, tmp_path: Path):
        """Artifacts should carry the pytest outcome for report consumers."""
        inst = _make_instance(tmp_path)
        inst._pytest_failed = True

        inst.write_test_result()

        assert _read_result(inst)["pytest_failed"] is True


class TestOutcomeDiscriminator:
    """EVID-001: artifacts carry a formal outcome discriminator
    (passed|failed|warning|skipped|not_applicable), not just booleans."""

    def test_passed_outcome(self, tmp_path: Path):
        inst = _make_instance(tmp_path)
        inst.record_assertion("case_created", True)
        inst.write_test_result()
        assert _read_result(inst)["outcome"] == "passed"
        assert _read_tc_summary(inst)["outcome"] == "passed"

    def test_failed_outcome(self, tmp_path: Path):
        inst = _make_instance(tmp_path)
        inst.record_assertion("case_created", False)
        inst.write_test_result()
        assert _read_result(inst)["outcome"] == "failed"
        assert _read_tc_summary(inst)["outcome"] == "failed"

    def test_skipped_outcome_from_pytest(self, tmp_path: Path):
        inst = _make_instance(tmp_path)
        inst._pytest_outcome = "skipped"  # set by the conftest makereport hook
        inst.write_test_result()
        assert _read_result(inst)["outcome"] == "skipped"
        assert _read_tc_summary(inst)["outcome"] == "skipped"

    def test_warning_outcome(self, tmp_path: Path):
        inst = _make_instance(tmp_path)
        inst.record_assertion("case_created", True)
        inst.record_check("residual_containers", "warning", details={"count": 2})
        inst.write_test_result()
        result = _read_result(inst)
        assert result["outcome"] == "warning"
        assert result["all_passed"] is True  # warning is not a failure

    def test_not_applicable_outcome_all_na(self, tmp_path: Path):
        inst = _make_instance(tmp_path)
        inst.record_check("misp_sync", "not_applicable", details={"reason": "MISP down"})
        inst.write_test_result()
        assert _read_result(inst)["outcome"] == "not_applicable"

    def test_not_applicable_mark(self, tmp_path: Path):
        inst = _make_instance(tmp_path)
        inst.record_assertion("webhook_accepted", True)
        inst.mark_not_applicable("no SSO overlay deployed")
        inst.write_test_result()
        assert _read_result(inst)["outcome"] == "not_applicable"

    def test_outcome_precedence_failed_over_warning(self, tmp_path: Path):
        inst = _make_instance(tmp_path)
        inst.record_check("residual_containers", "warning")
        inst.record_assertion("execution_success", False)
        inst.write_test_result()
        assert _read_result(inst)["outcome"] == "failed"

    def test_outcome_precedence_skipped_over_failed_assertions(self, tmp_path: Path):
        inst = _make_instance(tmp_path)
        inst._pytest_outcome = "skipped"
        inst.record_assertion("setup_check", False)
        inst.write_test_result()
        assert _read_result(inst)["outcome"] == "skipped"

    def test_assertion_entries_carry_outcome(self, tmp_path: Path):
        inst = _make_instance(tmp_path)
        inst.record_assertion("a", True)
        inst.record_check("b", "warning")
        entries = inst._assertions
        assert entries[0]["outcome"] == "passed"
        assert entries[1]["outcome"] == "warning"

    def test_invalid_outcome_rejected(self, tmp_path: Path):
        inst = _make_instance(tmp_path)
        with pytest.raises(ValueError, match="Invalid assertion outcome"):
            inst.record_assertion("a", True, outcome="bogus")


class TestConftestOutcomeHook:
    """The e2e conftest must flag failed test calls on the instance."""

    def test_makereport_hook_marks_failed_call(self):
        conftest_path = Path(__file__).resolve().parent.parent / "e2e" / "conftest.py"
        source = conftest_path.read_text(encoding="utf-8")
        assert "pytest_runtest_makereport" in source
        assert "_pytest_failed" in source
        # EVID-001: skips propagate too.
        assert "_pytest_outcome" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
