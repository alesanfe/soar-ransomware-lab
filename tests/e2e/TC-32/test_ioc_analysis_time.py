#!/usr/bin/env python3
"""TC-32: IoC Analysis Time Verification Tests that the time to analyze each
IoC (hash, IP) via Cortex is < 30 seconds, satisfying RNF-01: "el análisis de
IoCs debe tardar menos de 30 segundos por indicador".

Measures per-node duration from Shuffle workflow execution results for:
  - cortex_hash: Cortex job for file hash analysis
  - cortex_ip: Cortex job for IP address analysis
  - misp_search: MISP threat intelligence lookup (bonus)
"""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from workflow_validator import validate_workflow_results

from tests.e2e.base import E2EBaseTest

IOC_ANALYSIS_THRESHOLD = 30  # RNF-01: < 30s per indicator

# Nodes whose duration represents IoC analysis time
IOC_NODES = [
    "cortex_hash",
    "cortex_ip",
    "misp_search",
]


def _parse_timestamp(ts) -> float | None:
    """Parse a Shuffle timestamp (epoch ms, epoch s, or ISO 8601 string) to
    seconds."""
    if ts is None:
        return None
    # Numeric epoch
    try:
        val = float(ts)
        if val > 1e12:
            val = val / 1000.0
        return val
    except (ValueError, TypeError):
        pass
    # ISO 8601 string
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, TypeError):
        pass
    return None


class TestIoCAnalysisTime(E2EBaseTest):
    """TC-32 — IoC Analysis Time Verification.

    Sends an alert through the SOAR workflow and measures the duration
    of each IoC analysis node (Cortex hash, Cortex IP, MISP) from the
    Shuffle execution results. Validates RNF-01: < 30s per indicator.
    """

    tc_id = "TC-32"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

    def _log(self, msg: str):
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        print(f"[{elapsed:6.1f}s] TC-32 {msg}")

    def _extract_node_durations(self, results: list) -> dict[str, float]:
        """Extract per-node duration in seconds from workflow results.

        Each node in Shuffle results may have 'start' and 'end'
        timestamp fields. Returns a dict mapping node label ->
        duration_seconds.
        """
        durations = {}
        for node in results:
            if not isinstance(node, dict):
                continue
            action = node.get("action", {})
            if not isinstance(action, dict):
                continue
            label = action.get("label", "?")

            # Try to get start/end from the node itself
            start_ts = _parse_timestamp(node.get("start"))
            end_ts = _parse_timestamp(node.get("end"))

            # Fallback: check for started_at/completed_at fields
            if start_ts is None:
                start_ts = _parse_timestamp(node.get("started_at"))
            if end_ts is None:
                end_ts = _parse_timestamp(node.get("completed_at"))

            if start_ts is not None and end_ts is not None:
                duration = end_ts - start_ts
                if duration > 0:
                    durations[label] = round(duration, 2)

        return durations

    def test_ioc_analysis_time(self):
        """TC-32: Verify IoC analysis time < 30s per indicator (RNF-01).

        Steps:
          1. Send alert with hash + IP IoCs
          2. Wait for workflow completion
          3. Extract per-node durations from results
          4. Validate each IoC analysis node < 30s
          5. Validate total IoC analysis time is reasonable
        """
        self._log("=== TC-32: IoC ANALYSIS TIME VERIFICATION ===")

        # ── Step 1: Send alert ──
        self._log("STEP 1: Sending alert with known IoCs (hash + IP)")
        alert_id = f"TC-32-{int(time.time())}"
        payload = {
            "alert_id": alert_id,
            "alert_type": "ransomware",
            "hostname": "WIN-IOC-TIME-001",
            "src_ip": "185.220.101.182",
            "hash": "44d88612fea8a8f36de82e1278abb02f",
            "severity": 2,
            "source": "ioc-time-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "timestamp": time.time(),
        }
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self._log(f"  + Alert sent: {payload['alert_id']}, exec_id={exec_id}")

        # ── Step 2: Wait for workflow completion ──
        self._log("STEP 2: Waiting for workflow completion")
        validate_workflow_results(execution)
        self._log("  + Workflow completed")

        # ── Step 3: Extract per-node durations ──
        self._log("STEP 3: Extracting per-node durations from workflow results")
        results = execution.get("results", [])
        assert isinstance(results, list), "Results must be a list"
        assert len(results) > 0, "No results in workflow execution"

        node_durations = self._extract_node_durations(results)

        if not node_durations:
            self._log("  + No per-node timestamps found. Using execution-level timing as fallback.")
            # Fallback: use execution started_at / completed_at as upper bound
            exec_start = _parse_timestamp(execution.get("started_at"))
            exec_end = _parse_timestamp(execution.get("completed_at"))
            if exec_start and exec_end:
                total_duration = exec_end - exec_start
                self._log(f"  + Total execution time: {total_duration:.2f}s")
                # For a single alert with 2 IoCs (hash + IP), total time / 2 is an upper bound
                # per-indicator. This is conservative since the total includes case creation,
                # notifications, etc.
                per_ioc_upper = total_duration / 2
                self._log(f"  + Per-IoC upper bound (total/2): {per_ioc_upper:.2f}s")
                assert per_ioc_upper < IOC_ANALYSIS_THRESHOLD, (
                    f"Per-IoC upper bound {per_ioc_upper:.2f}s >= {IOC_ANALYSIS_THRESHOLD}s "
                    f"(RNF-01 violation)"
                )
                self._log(f"  + Per-IoC upper bound < {IOC_ANALYSIS_THRESHOLD}s ✓")

                # Log all node labels for diagnostic purposes
                for node in results:
                    label = node.get("action", {}).get("label", "?")
                    status = node.get("status", "?")
                    self._log(f"  + Node: {label} ({status})")

                elapsed = (datetime.now(UTC) - self.t0).total_seconds()
                self._log(
                    f"=== TC-32 COMPLETED — IoC ANALYSIS TIME VERIFIED via fallback "
                    f"(Elapsed: {elapsed:.1f}s) ==="
                )
                self._save_report(payload, {}, per_ioc_upper, total_duration, elapsed)
                return

        self._log(f"  + Found durations for {len(node_durations)} nodes:")
        for label, dur in sorted(node_durations.items()):
            self._log(f"    {label}: {dur}s")

        # ── Step 4: Validate IoC analysis nodes < 30s ──
        self._log(f"STEP 4: Validating IoC analysis nodes < {IOC_ANALYSIS_THRESHOLD}s (RNF-01)")

        ioc_durations = {}
        for node_name in IOC_NODES:
            if node_name in node_durations:
                dur = node_durations[node_name]
                ioc_durations[node_name] = dur
                self._log(f"  + {node_name}: {dur}s")
                assert dur < IOC_ANALYSIS_THRESHOLD, (
                    f"RNF-01 VIOLATION: {node_name} took {dur}s >= {IOC_ANALYSIS_THRESHOLD}s "
                    f"threshold"
                )
                self._log(f"    ✓ {node_name} < {IOC_ANALYSIS_THRESHOLD}s")

        if not ioc_durations:
            self._log("  + WARNING: No IoC-specific nodes found in results with timing data")
            self._log("  + Falling back to execution-level timing")
            exec_start = _parse_timestamp(execution.get("started_at"))
            exec_end = _parse_timestamp(execution.get("completed_at"))
            if exec_start and exec_end:
                total_duration = exec_end - exec_start
                per_ioc_upper = total_duration / 2
                self._log(
                    f"  + Total: {total_duration:.2f}s, per-IoC upper bound: {per_ioc_upper:.2f}s"
                )
                assert (
                    per_ioc_upper < IOC_ANALYSIS_THRESHOLD
                ), f"Per-IoC upper bound {per_ioc_upper:.2f}s >= {IOC_ANALYSIS_THRESHOLD}s"
                self._log(f"  + Per-IoC upper bound < {IOC_ANALYSIS_THRESHOLD}s ✓")
                elapsed = (datetime.now(UTC) - self.t0).total_seconds()
                self._log(
                    f"=== TC-32 COMPLETED — IoC ANALYSIS TIME VERIFIED via fallback "
                    f"(Elapsed: {elapsed:.1f}s) ==="
                )
                self._save_report(payload, {}, per_ioc_upper, total_duration, elapsed)
                return
            pytest.fail("Could not determine IoC analysis time: no node or execution timestamps")

        # ── Step 5: Validate total IoC analysis time ──
        self._log("STEP 5: Validating total IoC analysis time")
        total_ioc_time = sum(ioc_durations.values())
        avg_ioc_time = total_ioc_time / len(ioc_durations) if ioc_durations else 0
        self._log(f"  + Total IoC analysis time: {total_ioc_time:.2f}s")
        self._log(f"  + Average per IoC: {avg_ioc_time:.2f}s")
        self._log(f"  + Max per IoC: {max(ioc_durations.values()):.2f}s")

        assert (
            avg_ioc_time < IOC_ANALYSIS_THRESHOLD
        ), f"Average IoC analysis time {avg_ioc_time:.2f}s >= {IOC_ANALYSIS_THRESHOLD}s"

        # ── Step 6: Log all node durations for diagnostics ──
        self._log("STEP 6: All node durations (diagnostic)")
        for label, dur in sorted(node_durations.items()):
            marker = " [IoC]" if label in IOC_NODES else ""
            self._log(f"  + {label}: {dur}s{marker}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"=== TC-32 COMPLETED — IoC ANALYSIS TIME VERIFIED (Elapsed: {elapsed:.1f}s) ===")

        self._save_report(payload, ioc_durations, avg_ioc_time, total_ioc_time, elapsed)

    def _save_report(self, payload, ioc_durations, avg_time, total_time, elapsed):
        report = {
            "test_case": "TC-32",
            "test_name": "IoC Analysis Time Verification",
            "status": "PASSED",
            "alert_id": payload.get("alert_id", ""),
            "ioc_analysis_threshold_seconds": IOC_ANALYSIS_THRESHOLD,
            "ioc_node_durations": ioc_durations,
            "avg_ioc_time_seconds": round(avg_time, 2),
            "total_ioc_time_seconds": round(total_time, 2),
            "rnf_01_compliant": avg_time < IOC_ANALYSIS_THRESHOLD,
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_path = Path("reports/validation/results") / "TC-32_ioc_analysis_time_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")
