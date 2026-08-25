#!/usr/bin/env python3
"""TC-KPI-01: MTTR Calculation Verification Tests that MTTR is calculated
correctly and stored in Elasticsearch."""

import json
import time
from datetime import UTC, datetime

from tests.e2e.base import E2EBaseTest


class TestMTRRCalculation(E2EBaseTest):
    """TC-KPI-01 — MTTR Calculation: Verify MTTR is calculated correctly."""

    tc_id = "TC-KPI-01"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

    def _log(self, msg: str):
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        print(f"[{elapsed:6.1f}s] TC-KPI-01 {msg}")

    def test_mttr_calculation(self):
        """Send alert and verify MTTR is calculated and stored."""
        self._log("=== TC-KPI-01: MTTR Calculation Verification ===")

        payload = {
            "alert_id": f"TC-KPI-01-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-KPI-001",
            "src_ip": "192.168.1.250",
            "hash": "h" * 64,
            "severity": 2,
            "source": "kpi-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "timestamp": time.time(),
        }

        self._log("STEP 1: Sending alert and waiting for workflow completion")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        alert_id = payload["alert_id"]
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log(f"  + Alert accepted - execution_id={exec_id}")
        self._log("  + Workflow completed")

        # Verify MTTR in metrics index (optional - workflow may not be fully configured)
        self._log("STEP 2: Verifying MTTR in soarmetrics index")
        time.sleep(2)  # Wait for metrics to be indexed
        mttr = None
        doc = self.es.search_by_alert_id(payload["alert_id"], index="soar-metrics")
        assert (
            doc is not None
        ), f"Metrics document not found in soar-metrics index for alert_id={payload['alert_id']}"
        assert isinstance(doc, dict), "ES document must be a dict"
        mttr = doc.get("mttr_seconds")
        assert mttr is not None, "MTTR field (mttr_seconds) must be present in metrics document"
        assert isinstance(mttr, (int, float)), f"MTTR must be numeric, got {type(mttr)}"
        assert mttr > 0, "MTTR should be greater than 0"
        assert mttr < 300, "MTTR should be less than 5 minutes"
        self._log(f"  + MTTR calculated: {mttr:.2f}s")

        # Verify MTTR is reasonable (workflow duration)
        workflow_start = payload["timestamp"]
        workflow_end = time.time()
        expected_mttr = workflow_end - workflow_start
        assert (
            abs(mttr - expected_mttr) < 60
        ), f"MTTR {mttr}s differs significantly from expected {expected_mttr:.2f}s"
        self._log("  + MTTR within expected range")

        # Validate that MTTR calculation logic is correct
        self._log("✓ MTTR calculation validated - value is reasonable and stored correctly")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(
            f"=== TC-KPI-01 COMPLETED — MTTR CALCULATION VERIFIED (Elapsed: {elapsed:.1f}s) ==="
        )

        # Save report
        report = {
            "test_case": "TC-KPI-01",
            "test_name": "MTTR Calculation",
            "status": "PASSED",
            "alert_id": payload["alert_id"],
            "mttr_seconds": mttr,
            "mttr_reasonable": True,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_path = self.e2e_results_dir / "TC-KPI-01_mttr_calculation_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")
