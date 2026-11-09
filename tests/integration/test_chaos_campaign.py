"""Tests for the chaos campaign runner (scripts/perf/chaos_campaign.py)."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "chaos_campaign", ROOT / "scripts" / "perf" / "chaos_campaign.py"
)
mod = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("chaos_campaign", mod)
_SPEC.loader.exec_module(mod)


class TestCampaignVerdict:
    def test_all_pass(self):
        v, reasons = mod.campaign_verdict(
            [{"scenario": "a", "scenario_pass": True}, {"scenario": "b", "scenario_pass": True}]
        )
        assert v == "PASS"
        assert reasons == []

    def test_fails_when_scenario_fails(self):
        v, reasons = mod.campaign_verdict(
            [
                {"scenario": "a", "scenario_pass": True},
                {
                    "scenario": "b",
                    "scenario_pass": False,
                    "chaos_lite_rc": 1,
                    "workflow_status": "FINISHED",
                },
            ]
        )
        assert v == "FAIL"
        assert any("b:" in r and "rc=1" in r for r in reasons)

    def test_fails_when_recovery_slow(self):
        v, reasons = mod.campaign_verdict(
            [
                {
                    "scenario": "a",
                    "scenario_pass": False,
                    "chaos_lite_rc": 0,
                    "recovery_ok": False,
                    "recovery_s": 120.0,
                }
            ]
        )
        assert v == "FAIL"
        assert "recovery" in reasons[0]

    def test_reason_names_workflow_status(self):
        _, reasons = mod.campaign_verdict(
            [
                {
                    "scenario": "x",
                    "scenario_pass": False,
                    "chaos_lite_rc": 0,
                    "workflow_status": "ABORTED",
                }
            ]
        )
        assert "ABORTED" in reasons[0]


class TestScenarios:
    def test_default_scenarios_are_critical_backends(self):
        targets = {s["target"] for s in mod.DEFAULT_SCENARIOS}
        assert "soar_cortex" in targets
        assert "soar_thehive" in targets
        assert "soar_misp" in targets
        # Pauses are bounded — never an unbounded kill/stop.
        assert all(0 < s["pause"] <= 120 for s in mod.DEFAULT_SCENARIOS)


class TestScenarioFilter:
    def test_unknown_scenario_rejected(self, capsys):
        import pytest

        with pytest.raises(SystemExit):
            mod.main(["--scenario", "nonexistent", "--dry-run"])
