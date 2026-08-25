#!/usr/bin/env python3
"""TC-00 — Parametrized Tests for Both Workflows Tests the SOAR-Ransomware-
Response (simulated) workflow."""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import pytest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest


class TestBothWorkflows(E2EBaseTest):
    """TC-00 — Parametrized tests for the SOAR workflow."""

    tc_id = "TC-00"

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-00 {msg}"
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()

    def _build_payload(self, prefix: str = "TC00-SIM", hostname: str = "WIN-SIM-001") -> dict:
        return {
            "alert_id": f"{prefix}-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": hostname,
            "src_ip": "192.168.1.100",
            "severity": 2,
            "process_name": "malware.exe",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "mitre_techniques": ["T1486"],
            "detection_time": datetime.now(UTC).isoformat(),
            "source": "simulated-siem",
        }

    @pytest.mark.timeout(600)
    @pytest.mark.slow
    def test_workflow_malicious(self):
        """TC-00-01: Malicious alert through the workflow with full
        validation."""
        self._log("=== TC-00-01: WORKFLOW MALICIOUS TEST STARTED ===")
        payload = self._build_payload()
        self.alert_data = payload
        alert_id = payload["alert_id"]
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)

        doc = self.es.search_by_alert_id(alert_id)
        assert doc is not None, "ES document not found"
        assert doc["alert_id"] == alert_id
        assert doc["hostname"] == payload["hostname"]
        assert doc["hash"] == payload["hash"]
        assert doc["severity"] == payload["severity"]
        assert doc["alert_type"] == payload["alert_type"]
        self._log("+ All critical fields preserved correctly")
        self._log("=== TC-00-01 COMPLETED ===")

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_parallel_workflow_execution(self):
        """TC-00-02: Parallel execution — no race conditions."""
        self._log("=== TC-00-02: PARALLEL EXECUTION TEST STARTED ===")

        def execute_one(suffix):
            payload = self._build_payload(
                prefix=f"TC00-PARALLEL-{suffix}", hostname=f"WIN-PARALLEL-{suffix}"
            )
            exec_id, execution = self.submit_alert_and_wait(payload)
            return payload, exec_id, execution

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(execute_one, i) for i in range(3)]
            results = []
            for future in as_completed(futures):
                payload, exec_id, execution = future.result()
                results.append((payload, exec_id, execution))
                self._log(f"+ Workflow completed for alert {payload['alert_id']}")

        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        alert_ids = [p["alert_id"] for p, _, _ in results]
        assert len(alert_ids) == len(set(alert_ids)), "Duplicate alert IDs — race condition"
        self._log("+ No duplicate alert IDs — no race conditions")

        for payload, _, _ in results:
            doc = self.es.search_by_alert_id(payload["alert_id"])
            assert doc, f"ES document not found for {payload['alert_id']}"
            assert doc["alert_id"] == payload["alert_id"]
        self._log(f"+ All {len(results)} parallel workflows persisted data")
        self._log("=== TC-00-02 COMPLETED ===")

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_workflow_consistency(self):
        """TC-00-03: Multiple executions produce consistent results."""
        self._log("=== TC-00-03: WORKFLOW CONSISTENCY TEST STARTED ===")
        results = []
        for i in range(3):
            payload = self._build_payload(prefix=f"TC00-CONSIST-{i}", hostname="WIN-CONSIST-001")
            exec_id, execution = self.submit_alert_and_wait(payload)
            results.append((payload, execution))
            self._log(f"+ Execution {i + 1}/3 completed")

        statuses = [ex.get("status", "").upper() for _, ex in results]
        assert len(set(statuses)) == 1, f"Statuses inconsistent: {statuses}"
        self._log(f"+ All executions have consistent status: {statuses[0]}")

        docs = []
        for payload, _ in results:
            doc = self.es.search_by_alert_id(payload["alert_id"])
            assert doc is not None, "ES document not found"
            docs.append(doc)
        if len(docs) >= 2:
            field_sets = [set(d.keys()) for d in docs]
            set.intersection(*field_sets)
            for field in ["alert_id", "hostname", "hash", "severity", "alert_type"]:
                assert all(field in d for d in docs), f"Field {field} missing in some documents"
        self._log("=== TC-00-03 COMPLETED ===")

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_execution_time_comparison(self):
        """TC-00-04: Execution times are within acceptable range."""
        self._log("=== TC-00-04: EXECUTION TIME COMPARISON TEST STARTED ===")
        execution_times = []
        for i in range(3):
            payload = self._build_payload(prefix=f"TC00-TIME-{i}")
            start = time.time()
            exec_id, execution = self.submit_alert_and_wait(payload)
            elapsed = time.time() - start
            execution_times.append(elapsed)
            self._log(f"+ Execution time {i + 1}: {elapsed:.1f}s")

        avg = sum(execution_times) / len(execution_times)
        mx = max(execution_times)
        mn = min(execution_times)
        self._log(f"+ Average: {avg:.1f}s  Min: {mn:.1f}s  Max: {mx:.1f}s")

        assert mx < self.WORKFLOW_TIMEOUT, f"Max {mx:.1f}s exceeds timeout"
        assert avg > 5, f"Average {avg:.1f}s too fast, may indicate no processing"
        variance = mx - mn
        assert variance < avg * 1.0, f"Variance {variance:.1f}s too high"
        self._log("=== TC-00-04 COMPLETED ===")
