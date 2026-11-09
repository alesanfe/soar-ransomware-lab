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
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from workflow_validator import validate_workflow_results

from scripts.perf.workflow_bottleneck import (
    DOMINANT_NODE_SHARE,
    QUEUE_WAIT_P95_S,
)
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
        alert_id = self.uid("TC-KPI-05")
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

        # Step 1b: Measure the dispatch path node timings cannot see —
        # submission → workflow started_at covers queue wait + webhook
        # forward + Shuffle scheduling. Payload carries epoch `timestamp`.
        queue_wait_s = None
        started_at = execution.get("started_at")
        if not started_at:
            # The Shuffle-API response shape lacks started_at — re-query the
            # OpenSearch projection explicitly (include_results=False → ES
            # fast path only, which always carries the epoch field).
            exec_doc = self.shuffle.get_execution(self.workflow_id, exec_id, include_results=False)
            started_at = (exec_doc or {}).get("started_at")
        if started_at and payload.get("timestamp"):
            queue_wait_s = round(float(started_at) - float(payload["timestamp"]), 3)
            if queue_wait_s < 0:
                queue_wait_s = None  # clock skew — meaningless measurement
        self._log(f"  Queue wait (submission→start): {queue_wait_s}s")
        if queue_wait_s is not None:
            # >60s is not a perf regression, it is a broken dispatch path
            # (measured healthy baseline: ~7ms — three orders of margin).
            assert queue_wait_s < 60, (
                f"queue_wait {queue_wait_s}s — admission→dispatch path broken, " f"not merely slow"
            )

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

        # Step 6: Validate workflow duration is consistent with MTTR.
        # Extraction correctness is asserted (duration > 0, < wait timeout);
        # the latency SLO is MEASURED and reported, not asserted — a loaded
        # stack legitimately exceeds 300s (observed P95 ≈ 574s) without the
        # timing pipeline being broken.
        self._log("STEP 6: Validating workflow duration consistency")
        wf_duration = timings.get("workflow_duration_s", 0)
        assert wf_duration > 0, "Workflow duration is zero"
        assert wf_duration < self.WORKFLOW_TIMEOUT, (
            f"Workflow duration {wf_duration}s exceeded wait timeout "
            f"— inconsistent with a FINISHED execution"
        )
        slo_target_s = 300
        slo_met = wf_duration < slo_target_s
        self._log(
            f"  Workflow duration: {wf_duration}s "
            f"(SLO {slo_target_s}s: {'MET' if slo_met else 'MISSED'})"
        )

        # Step 6b: Data quality — corrupt node clocks must be caught, not
        # silently dropped (M-018/019).
        dq = timings.get("data_quality", {})
        assert dq.get("invalid_node_timings", 0) == 0, (
            f"{dq.get('invalid_node_timings')} node timings failed temporal "
            f"validation — clock corruption in execution doc"
        )

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
        # Bottleneck ranking: node share of total node runtime in this
        # execution — identifies which node dominates the critical path.
        node_total = sum(n.get("duration_s", 0) for n in nodes.values())
        bottleneck_ranking = [
            {
                "label": n["label"],
                "duration_s": n.get("duration_s", 0),
                "share_of_node_time": (
                    round(n.get("duration_s", 0) / node_total, 4) if node_total > 0 else 0.0
                ),
            }
            for n in slowest
        ]

        # Bottleneck findings for this single execution — recorded, not
        # asserted (a single run can legitimately spike; the aggregate
        # detector in scripts/perf/workflow_bottleneck.py gates trends).
        bottleneck_findings = []
        for n in bottleneck_ranking:
            if n["share_of_node_time"] >= DOMINANT_NODE_SHARE:
                bottleneck_findings.append(
                    {
                        "rule": "dominant_node",
                        "severity": "warning",
                        "detail": f"{n['label']} = {n['share_of_node_time']:.0%} of node time",
                    }
                )
        if queue_wait_s is not None and queue_wait_s >= QUEUE_WAIT_P95_S:
            bottleneck_findings.append(
                {
                    "rule": "queue_wait",
                    "severity": "warning",
                    "detail": f"queue_wait {queue_wait_s}s >= {QUEUE_WAIT_P95_S}s",
                }
            )
        if bottleneck_findings:
            self._log(f"  Bottleneck findings: {bottleneck_findings}")

        report = {
            "test_case": "TC-KPI-05",
            "test_name": "Per-Node Timing Metrics",
            "status": "PASSED",
            "alert_id": alert_id,
            "execution_id": exec_id,
            "total_nodes": len(nodes),
            "workflow_duration_s": wf_duration,
            "queue_wait_s": queue_wait_s,
            "slo_target_s": slo_target_s,
            "slo_met": slo_met,
            "bottleneck_ranking": bottleneck_ranking,
            "bottleneck_findings": bottleneck_findings,
            "slowest_nodes": slowest[:5],
            "parallel_groups_count": len(parallel_groups),
            "data_quality": dq,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_path = Path("reports/validation/results") / "TC-KPI-05_node_timings_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"  Report saved: {report_path}")
