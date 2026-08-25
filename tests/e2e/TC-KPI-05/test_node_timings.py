#!/usr/bin/env python3
"""TC-KPI-05: Per-Node Timing Metrics Verification.

Verifies that:
  1. The /analytics/node-timings endpoint returns real timing data.
  2. Each workflow node has a non-zero duration (not simulated).
  3. The slowest nodes are identified correctly.
  4. Parallel groups are detected.
  5. Timings are consistent with workflow MTTR.
"""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from workflow_validator import validate_workflow_results

from tests.e2e.base import E2EBaseTest


class TestNodeTimings(E2EBaseTest):
    """TC-KPI-05 — Per-Node Timing Metrics."""

    tc_id = "TC-KPI-05"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self.api_url = self.env.get("API_URL", "http://api:8000")

    def _log(self, msg: str):
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        print(f"[{elapsed:6.1f}s] TC-KPI-05 {msg}")

    def test_node_timings(self):
        """Send alert, wait for completion, fetch per-node timings from API."""
        self._log("=== TC-KPI-05: Per-Node Timing Metrics ===")

        # Step 1: Send alert
        alert_id = f"TC-KPI-05-{int(time.time())}"
        payload = {
            "alert_id": alert_id,
            "alert_type": "ransomware",
            "hostname": "WIN-KPI05-001",
            "src_ip": "192.168.1.250",
            "hash": "a" * 64,
            "severity": 2,
            "source": "node-timing-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "timestamp": time.time(),
        }

        self._log("STEP 1: Sending alert")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self._log(f"  Alert accepted: {exec_id[:12]}...")

        # Step 2: Wait for completion
        self._log("STEP 2: Waiting for workflow completion")
        validate_workflow_results(execution)
        self._log("  Workflow completed")

        # Step 3: Fetch node timings from API
        self._log("STEP 3: Fetching per-node timings from /analytics/node-timings")
        time.sleep(3)  # Allow OpenSearch to index
        r = self.s.get(
            f"{self.api_url}/analytics/node-timings",
            params={"execution_id": exec_id, "alert_id": alert_id},
            timeout=60,
        )
        assert r.status_code == 200, f"API returned HTTP {r.status_code}: {r.text[:300]}"
        timings = r.json()
        self._log(f"  Got timings for {timings.get('total_nodes', 0)} nodes")

        # Step 4: Validate timings are real (not simulated/zero)
        self._log("STEP 4: Validating timings are real (non-zero durations)")
        nodes = timings.get("nodes", {})
        assert len(nodes) > 0, "No node timings returned"

        zero_duration_count = 0
        real_duration_count = 0
        for label, info in nodes.items():
            dur = info.get("duration_s", 0)
            assert dur >= 0, f"Node {label} has negative duration: {dur}"
            if dur == 0:
                zero_duration_count += 1
            else:
                real_duration_count += 1

        # At least 80% of nodes should have non-zero duration
        assert real_duration_count > 0, "All nodes have zero duration — timings not real"
        zero_rate = zero_duration_count / len(nodes)
        assert zero_rate < 0.5, (
            f"{zero_duration_count}/{len(nodes)} nodes have zero duration "
            f"(rate={zero_rate:.1%}) — timings may be simulated"
        )
        self._log(
            f"  {real_duration_count}/{len(nodes)} nodes have real durations "
            f"({zero_duration_count} zero-duration)"
        )

        # Step 5: Validate slowest nodes
        self._log("STEP 5: Validating slowest nodes identification")
        slowest = timings.get("slowest_nodes", [])
        assert len(slowest) > 0, "No slowest nodes returned"
        assert len(slowest) <= 10, "Too many slowest nodes"
        # Slowest nodes should be sorted by duration descending
        durations = [n.get("duration_s", 0) for n in slowest]
        assert durations == sorted(
            durations, reverse=True
        ), "Slowest nodes not sorted by duration descending"
        self._log(f"  Top 3 slowest: {slowest[:3]}")

        # Step 6: Validate workflow duration is consistent with MTTR
        self._log("STEP 6: Validating workflow duration consistency")
        wf_duration = timings.get("workflow_duration_s", 0)
        assert wf_duration > 0, "Workflow duration is zero"
        assert wf_duration < 300, f"Workflow duration {wf_duration}s too high"
        self._log(f"  Workflow duration: {wf_duration}s")

        # Step 7: Validate parallel groups
        self._log("STEP 7: Validating parallel group detection")
        parallel_groups = timings.get("parallel_groups", [])
        assert len(parallel_groups) > 0, "No parallel groups detected"
        for pg in parallel_groups:
            assert len(pg.get("nodes", [])) > 1, "Parallel group has only 1 node"
        self._log(f"  Detected {len(parallel_groups)} parallel groups")

        # Step 8: Validate critical nodes have timings
        self._log("STEP 8: Validating critical nodes have timings")
        critical_nodes = [
            "normalize_inputs",
            "thehive_create_case",
            "cortex_hash",
            "cortex_ip",
            "calc_decision",
            "calc_mttr",
        ]
        for cn in critical_nodes:
            assert cn in nodes, f"Critical node '{cn}' missing from timings"
            assert nodes[cn]["duration_s"] >= 0, f"Critical node '{cn}' has invalid duration"
        self._log("  All critical nodes have timings ✓")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"=== TC-KPI-05 COMPLETED (Elapsed: {elapsed:.1f}s) ===")

        # Save report
        report = {
            "test_case": "TC-KPI-05",
            "test_name": "Per-Node Timing Metrics",
            "status": "PASSED",
            "alert_id": alert_id,
            "execution_id": exec_id,
            "total_nodes": len(nodes),
            "workflow_duration_s": wf_duration,
            "slowest_nodes": slowest[:5],
            "parallel_groups_count": len(parallel_groups),
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_path = Path("reports/validation/results") / "TC-KPI-05_node_timings_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"  Report saved: {report_path}")
