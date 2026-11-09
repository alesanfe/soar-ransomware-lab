#!/usr/bin/env python3
"""TC-KPI-01: MTTR Calculation Verification Tests that MTTR is calculated
correctly and stored in Elasticsearch."""

import json
import time
from datetime import UTC, datetime

from tests.e2e.base import E2EBaseTest


def _iso_to_epoch(value: str) -> float | None:
    """Parse an ISO-8601 timestamp to epoch; None when not ISO."""
    parsed = None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        parsed = None
    return parsed


def _detection_epoch(detection_time, fallback: float) -> float:
    """Parse detection_time (ISO or epoch) to epoch seconds."""
    if isinstance(detection_time, str) and detection_time:
        iso = _iso_to_epoch(detection_time)
        if iso is not None:
            return iso
    try:
        return float(detection_time)
    except (TypeError, ValueError):
        return float(fallback)


def _exec_ts(value) -> float | None:
    """Execution timestamps may be epoch int/float or ISO strings."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        return _iso_to_epoch(value)
    return None


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
            "alert_id": self.uid("TC-KPI-01"),
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

        # Verify MTTR is consistent with the execution record.
        # calc_mttr measures detection_time -> the calc_mttr node, which
        # runs inside the workflow's tail (decision -> notify -> calc_mttr
        # -> summary -> enrich -> metrics). Therefore:
        #   lower bound: started_at - detection (node can't run before the
        #                execution starts)
        #   upper bound: completed_at - detection + clock skew (the node
        #                runs before workflow completion)
        # Comparing against test wall-clock is wrong — it includes
        # submission queueing, polling interval and evidence collection.
        det_ts = _detection_epoch(payload.get("detection_time"), payload["timestamp"])
        exec_start = _exec_ts(self.execution.get("started_at"))
        exec_end = _exec_ts(self.execution.get("completed_at"))
        if exec_start and exec_end:
            lo = exec_start - det_ts - 5
            hi = exec_end - det_ts + 15
            assert lo <= mttr <= hi, (
                f"MTTR {mttr}s outside execution-derived bounds "
                f"[{lo:.1f}, {hi:.1f}] (exec {exec_start}..{exec_end}, "
                f"detection {det_ts})"
            )
        else:
            # Execution lacks timestamps — fall back to a loose sanity
            # bound: MTTR cannot exceed detection -> now.
            assert mttr <= time.time() - det_ts + 15, f"MTTR {mttr}s exceeds detection->now bound"
        self._log("  + MTTR within execution-derived bounds")

        # STEP 3: cross-execution consistency — recent metrics docs all
        # carry a sane MTTR, not just the fresh one (single-sample risk).
        self._log("STEP 3: Verifying MTTR sanity across recent metrics documents")
        resp = self.es.search(
            index="soar-metrics",
            size=10,
            sort=[{"@timestamp": {"order": "desc"}}],
        )
        hits = resp.get("hits", {}).get("hits", [])
        assert hits, "No documents in soar-metrics — MTTR pipeline is not writing"
        bad = [
            (h.get("_source") or {}).get("alert_id")
            for h in hits
            if not isinstance((h.get("_source") or {}).get("mttr_seconds"), (int, float))
            or not (0 < (h.get("_source") or {}).get("mttr_seconds", 0) < 300)
        ]
        assert not bad, (
            f"{len(bad)}/{len(hits)} recent metrics docs lack a sane "
            f"mttr_seconds (0<mttr<300): {bad[:3]}"
        )
        self._log(f"  + {len(hits)} recent metrics docs all carry sane mttr_seconds")

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
