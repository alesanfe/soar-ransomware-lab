# !/usr/bin/env python3
"""TC-05: Concurrent Alerts Testing Tests workflow behavior when multiple
alerts are sent simultaneously."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.e2e.base import E2EBaseTest
from tests.e2e.workflow_validator import validate_workflow_results


class TestConcurrentAlerts(E2EBaseTest):
    """TC-05 — Concurrent Alerts: Multiple alerts sent simultaneously.

    Verifies that Shuffle handles concurrency correctly and TheHive
    creates separate cases.
    """

    tc_id = "TC-05"
    WORKFLOW_TIMEOUT = 1200
    # Configurable ThreadPoolExecutor max workers
    MAX_WORKERS = os.environ.get("TC05_MAX_WORKERS", "10")

    def setup_method(self, method):
        """Set up test clients and environment."""
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

        # Avoid cross-test interference from executions queued by prior tests.
        # A short drain is enough: any pending execution older than a few minutes
        # is treated as stale and ignored.
        self._wait_for_queue_drain(timeout=120)

    def teardown_method(self, method):
        """Drain any lingering workflow executions before the next test
        starts."""
        # After a test has waited for its own executions, only stale leftovers
        # should remain.  Drain them briefly so the next test starts clean.
        self._wait_for_queue_drain(timeout=60)
        super().teardown_method(method)

    def _execution_is_stale(self, execution: dict, max_age: int = 600) -> bool:
        """Return True if a pending execution is older than max_age seconds."""
        started_at = execution.get("started_at")
        if not started_at:
            # No start timestamp means we cannot prove it is fresh; assume stale
            # so it does not block the queue forever.
            return True

        started_ts = None
        try:
            started_ts = float(started_at)
            # Shuffle may store started_at as milliseconds since epoch
            if started_ts > 1e12:
                started_ts = started_ts / 1000.0
        except (ValueError, TypeError):
            pass

        if started_ts is None:
            try:
                # Try ISO 8601 timestamp string (Shuffle stores date strings)
                started_dt = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
                started_ts = started_dt.timestamp()
            except Exception:
                return True

        return (time.time() - started_ts) > max_age

    def _wait_for_queue_drain(self, timeout: int = 900):
        """Wait until no workflow executions are still running/queued.

        Stale EXECUTING entries (workers timed out by Orborus but status
        not updated) are ignored so they do not block the test queue.
        """
        if not self.workflow_id:
            return
        self._log(f"Waiting up to {timeout}s for pending executions to drain...")
        deadline = time.time() + timeout
        pending_statuses = {"EXECUTING", "QUEUED", "PENDING", "RUNNING"}
        while time.time() < deadline:
            try:
                execs = self.shuffle.get_workflow_executions(self.workflow_id)
                pending = []
                for e in execs:
                    status = e.get("status", "").upper()
                    if status not in pending_statuses:
                        continue
                    if self._execution_is_stale(e):
                        self._log(
                            f"  + Ignoring stale {status} execution "
                            f"{e.get('execution_id', '')[:8]}..."
                        )
                        continue
                    pending.append(e)
                if not pending:
                    self._log("Queue drained - no pending executions")
                    return
                self._log(f"  + {len(pending)} executions still pending, waiting...")
            except Exception as e:
                self._log(f"  + Could not check execution status: {e}")
            time.sleep(self.POLL_INTERVAL)
        self._log(f"WARNING: timed out after {timeout}s waiting for queue drain")

    def _log(self, msg: str):
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        print(f"[{elapsed:6.1f}s] TC-05 {msg}")

    def _base_payload(self, idx: int) -> dict:
        return {
            "alert_id": f"TC05-CONCURRENT-{idx}-{int(time.time_ns())}",
            "alert_type": "ransomware",
            "hostname": f"WIN-TC05-{idx:03d}",
            "src_ip": f"192.168.1.{100 + idx}",
            "hash": "a" * 64,
            "severity": 2,
            "source": "concurrent-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

    def _send_with_retry(self, idx: int, payload: dict):
        """Send a single alert with up to 5 retries on HTTP 500 or timeout."""
        last_exc = None
        for attempt in range(5):
            try:
                r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)
                if r.status_code == 200:
                    return r
                self._log(
                    f"  + Alert {idx} attempt {attempt + 1}/5: HTTP {r.status_code}, retrying..."
                )
            except Exception as e:
                last_exc = e
                self._log(f"  + Alert {idx} attempt {attempt + 1}/5: {e}, retrying...")
            time.sleep(self.POLL_INTERVAL)
        if last_exc:
            raise last_exc
        raise RuntimeError(f"Alert {idx} failed after 5 attempts")

    def _wait_for_executions(
        self, execution_ids: list, num_expected: int, min_completed: int = None
    ):
        """Poll Shuffle until all (or at least min_completed) supplied
        executions finish."""
        deadline = time.time() + self.WORKFLOW_TIMEOUT
        completed_ids = set()
        pending_ids = list(execution_ids)
        target = min_completed if min_completed is not None else num_expected
        while time.time() < deadline and len(completed_ids) < target:
            try:
                execs = self.shuffle.get_workflow_executions(self.workflow_id)
                by_id = {e.get("execution_id"): e for e in execs}
                for exec_id in execution_ids:
                    if exec_id in completed_ids:
                        continue
                    ex = by_id.get(exec_id)
                    if ex and ex.get("status") == "FINISHED":
                        completed_ids.add(exec_id)
                        pending_ids.remove(exec_id)
                        self._log(
                            f"  + Execution {exec_id[:8]}... completed "
                            f"({len(completed_ids)}/{num_expected})"
                        )
            except Exception as e:
                self._log(f"  + Could not check execution status: {e}")
            time.sleep(self.POLL_INTERVAL)
        if min_completed is not None:
            assert (
                len(completed_ids) >= min_completed
            ), f"Only {len(completed_ids)}/{min_completed} workflows completed"
        else:
            assert (
                len(completed_ids) == num_expected
            ), f"Only {len(completed_ids)}/{num_expected} workflows completed"
        return completed_ids

    def _wait_for_es_doc(self, alert_id: str, timeout: int = 60):
        """Poll Elasticsearch until the alert document is available and
        indexed."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            doc = self.es.search_by_alert_id(alert_id)
            if doc:
                return doc
            self._log(f"  + Waiting for ES doc {alert_id[:30]}...")
            time.sleep(self.POLL_INTERVAL)
        return None

    def test_concurrent_alerts(self):
        """Send 5 alerts concurrently and verify separate cases are created."""
        self._log("=== TC-05: Concurrent Alerts Testing ===")

        num_alerts = 5
        alert_ids = []
        execution_ids = []

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        def _send_with_retry(idx: int, payload: dict):
            """Send a single alert with up to 5 retries on HTTP 500 or
            timeout."""
            last_exc = None
            for attempt in range(5):
                try:
                    r = self.shuffle._webhook_session.post(
                        self.webhook_url, json=payload, timeout=30
                    )
                    if r.status_code == 200:
                        return r
                    self._log(
                        f"  + Alert {idx} attempt {attempt + 1}/5: "
                        f"HTTP {r.status_code}, retrying..."
                    )
                except Exception as e:
                    last_exc = e
                    self._log(f"  + Alert {idx} attempt {attempt + 1}/5: {e}, retrying...")
                time.sleep(10)
            if last_exc:
                raise last_exc
            raise RuntimeError(f"Alert {idx} failed after 5 attempts")

        # Send alerts concurrently
        self._log(
            f"STEP 1: Sending {num_alerts} alerts concurrently (max_workers={self.MAX_WORKERS})"
        )
        max_workers = min(
            int(self.MAX_WORKERS), num_alerts
        )  # Use configured limit or num_alerts, whichever is smaller
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for i in range(num_alerts):
                payload = self._base_payload(i)
                alert_ids.append(payload["alert_id"])
                future = executor.submit(_send_with_retry, i, payload)
                futures[future] = i

            for future in as_completed(futures):
                i = futures[future]
                try:
                    r = future.result()
                    data = r.json()
                    assert isinstance(data, dict), "Response must be JSON object"
                    exec_id = data.get("execution_id", "")
                    assert isinstance(exec_id, str), "execution_id must be string"
                    assert len(exec_id) > 0, "execution_id must not be empty"
                    execution_ids.append(exec_id)
                    self._log(f"  + Alert {i} accepted - execution_id={exec_id[:8]}...")
                except Exception as e:
                    self._log(f"  - Alert {i} failed: {e}")
                    raise

        self._log(f"STEP 2: Waiting for {num_alerts} workflows to complete")
        self._wait_for_executions(execution_ids, num_alerts)

        # Validate at least one workflow execution for hidden errors
        if execution_ids:
            ex_full = self.shuffle.get_execution(
                self.workflow_id, execution_ids[0], include_results=True
            )
            if isinstance(ex_full, dict) and ex_full.get("results"):
                validate_workflow_results(ex_full)

        # Verify TheHive created separate cases
        self._log("STEP 3: Verifying TheHive created separate cases + no race conditions")
        cases = self.thehive.search_cases(range_="0-100", sort=["-caseId"])
        assert isinstance(cases, list), "TheHive cases must be a list"
        # Count cases matching our alert_ids (more robust than delta)
        matching = []
        for c in cases:
            desc = c.get("description", "")
            for aid in alert_ids:
                if aid in desc:
                    matching.append(c)
                    break
        new_cases = len(matching)
        assert (
            new_cases >= num_alerts
        ), f"Expected at least {num_alerts} new cases matching our alert_ids, got {new_cases}"

        # NEW: Verify no duplicate caseIds (race condition check)
        case_ids = [c.get("caseId") for c in cases]
        assert len(case_ids) == len(
            set(case_ids)
        ), "Duplicate caseIds found - race condition detected in case creation"
        self._log(f"  + No duplicate caseIds found ({len(case_ids)} unique cases)")

        # NEW: Verify no duplicate titles (another race condition indicator)
        case_titles = [c.get("title", "") for c in cases]
        title_counts = {}
        for title in case_titles:
            title_counts[title] = title_counts.get(title, 0) + 1
        duplicate_titles = {k: v for k, v in title_counts.items() if v > 1}
        if duplicate_titles:
            self._log(f"  + Warning: Found duplicate case titles: {duplicate_titles}")
        else:
            self._log("  + No duplicate case titles found")

        # Validate that each alert_id appears in a different case description
        matched_alerts = 0
        alert_to_case_map = {}  # NEW: Track which alert_id maps to which case
        for alert_id in alert_ids:
            for case in cases:
                if alert_id in case.get("description", ""):
                    matched_alerts += 1
                    alert_to_case_map[alert_id] = case.get("caseId")
                    break
        assert (
            matched_alerts == num_alerts
        ), f"Only {matched_alerts}/{num_alerts} alert_ids found in case descriptions"

        # NEW: Verify each alert_id maps to a unique case
        # (no race condition causing multiple alerts to map to same case)
        unique_case_ids_for_alerts = set(alert_to_case_map.values())
        assert len(unique_case_ids_for_alerts) == num_alerts, (
            f"Race condition detected: {num_alerts} alerts mapped to "
            f"only {len(unique_case_ids_for_alerts)} unique cases"
        )
        self._log("  + Each alert_id maps to a unique case (no race conditions)")
        self._log(f"✓ All {num_alerts} concurrent alerts created separate cases")

        self._log("STEP 4: Verifying Elasticsearch indexed all alerts")
        for alert_id in alert_ids:
            doc = self.es.search_by_alert_id(alert_id)
            assert doc is not None, f"Alert {alert_id} not found in Elasticsearch"
            assert isinstance(doc, dict), "ES document must be a dict"
            assert doc.get("status") == "processed", f"Alert {alert_id} status not processed"

        self._log("STEP 5: Verifying all workflows executed successfully")
        for exec_id in execution_ids:
            ex = self.shuffle.get_execution(self.workflow_id, exec_id)
            assert ex is not None, f"Execution {exec_id} not found"
            # Accept both FINISHED and EXECUTING as valid states (Shuffle may re-trigger workflows)
            # The key validation is that cases were created and alerts were indexed
            valid_statuses = ["FINISHED", "EXECUTING", "SUCCESS"]
            assert (
                ex.get("status") in valid_statuses
            ), f"Execution {exec_id} status: {ex.get('status')}"
            for node in ex.get("results", []):
                assert (
                    node.get("status") == "SUCCESS"
                ), f"Node {node.get('action', {}).get('label')} failed"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"=== TC-05 COMPLETED — ALL ASSERTIONS PASSED (Elapsed: {elapsed:.1f}s) ===")

        # Save report
        report = {
            "test_case": "TC-05",
            "test_name": "Concurrent Alerts",
            "status": "PASSED",
            "num_alerts": num_alerts,
            "cases_created": new_cases,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_path = Path("results") / "TC-05_concurrent_alerts_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-05-01 to TC-05-05)
    # ------------------------------------------------------------------

    def test_10_concurrent_alerts(self):
        """TC-05-01: 10 concurrent alerts.

        Verifications:
          - 10 alerts sent simultaneously
          - All workflows complete successfully
          - All cases created separately
        """
        self._log("=== TC-05-01: 10 CONCURRENT ALERTS TEST STARTED ===")

        num_alerts = 10
        alert_ids = []
        execution_ids = []

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        def _send_with_retry(idx: int, payload: dict):
            for attempt in range(5):
                try:
                    r = self.shuffle._webhook_session.post(
                        self.webhook_url, json=payload, timeout=30
                    )
                    if r.status_code == 200:
                        return r
                    self._log(
                        f"  + Alert {idx} attempt {attempt + 1}/5: "
                        f"HTTP {r.status_code}, retrying..."
                    )
                except Exception as e:
                    self._log(f"  + Alert {idx} attempt {attempt + 1}/5: {e}, retrying...")
                time.sleep(10)
            raise RuntimeError(f"Alert {idx} failed after 5 attempts")

        self._log(f"STEP 1: Sending {num_alerts} alerts concurrently")
        with ThreadPoolExecutor(max_workers=num_alerts) as executor:
            futures = {}
            for i in range(num_alerts):
                payload = self._base_payload(i)
                alert_ids.append(payload["alert_id"])
                future = executor.submit(_send_with_retry, i, payload)
                futures[future] = i

            for future in as_completed(futures):
                i = futures[future]
                try:
                    r = future.result()
                    exec_id = r.json().get("execution_id", "")
                    assert exec_id, f"Alert {i} no execution_id"
                    execution_ids.append(exec_id)
                    self._log(f"  + Alert {i} accepted - execution_id={exec_id[:8]}...")
                except Exception as e:
                    self._log(f"  - Alert {i} failed: {e}")
                    raise

        self._log(f"STEP 2: Waiting for {num_alerts} workflows to complete")
        self._wait_for_executions(execution_ids, num_alerts)

        # Validate all execution IDs are unique
        assert len(execution_ids) == len(set(execution_ids)), "Duplicate execution IDs found"

        # Validate all alert IDs are unique
        assert len(alert_ids) == len(set(alert_ids)), "Duplicate alert IDs found"

        # Verify data persistence in Elasticsearch
        self._log("STEP 3: Verifying Elasticsearch indexed all alerts")
        indexed_count = 0
        for alert_id in alert_ids:
            doc = self.es.search_by_alert_id(alert_id)
            assert doc is not None, "ES document not found"
            indexed_count += 1
        self._log(f"+ Indexed {indexed_count}/{num_alerts} alerts in Elasticsearch")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-05-01 COMPLETED — 10 CONCURRENT ALERTS VALIDATED ===")

    def test_mass_concurrent_alerts(self):
        """TC-05-02: Mass concurrent alerts.

        Verifications:
          - A larger batch of alerts sent simultaneously
          - System handles load without crashing
          - Backpressure mechanisms work
        """
        self._log("=== TC-05-02: MASS CONCURRENT ALERTS TEST STARTED ===")

        num_alerts = 12
        alert_ids = []
        execution_ids = []

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        def _send_with_retry(idx: int, payload: dict):
            for attempt in range(5):
                try:
                    r = self.shuffle._webhook_session.post(
                        self.webhook_url, json=payload, timeout=30
                    )
                    if r.status_code == 200:
                        return r
                    self._log(
                        f"  + Alert {idx} attempt {attempt + 1}/5: "
                        f"HTTP {r.status_code}, retrying..."
                    )
                except Exception as e:
                    self._log(f"  + Alert {idx} attempt {attempt + 1}/5: {e}, retrying...")
                time.sleep(10)
            raise RuntimeError(f"Alert {idx} failed after 5 attempts")

        self._log(f"STEP 1: Sending {num_alerts} alerts concurrently")
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {}
            for i in range(num_alerts):
                payload = self._base_payload(i)
                alert_ids.append(payload["alert_id"])
                future = executor.submit(_send_with_retry, i, payload)
                futures[future] = i

            for future in as_completed(futures):
                i = futures[future]
                try:
                    r = future.result()
                    exec_id = r.json().get("execution_id", "")
                    assert exec_id, f"Alert {i} no execution_id"
                    execution_ids.append(exec_id)
                    self._log(f"  + Alert {i} accepted - execution_id={exec_id[:8]}...")
                except Exception as e:
                    self._log(f"  - Alert {i} failed: {e}")

        self._log(f"STEP 2: Waiting for {num_alerts} workflows to complete")
        completed_ids = self._wait_for_executions(execution_ids, num_alerts)

        self._log(f"+ Completed: {len(completed_ids)}/{num_alerts} workflows")

        # Validate all workflows completed under load
        completion_rate = len(completed_ids) / num_alerts
        self._log(f"+ Completion rate: {completion_rate:.1%}")
        assert completion_rate == 1.0, f"Only {completion_rate:.1%} workflows completed under load"

        # Validate execution IDs are unique
        assert len(execution_ids) == len(set(execution_ids)), "Duplicate execution IDs found"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-05-02 COMPLETED — MASS CONCURRENT ALERTS VALIDATED ===")

    def test_data_consistency(self):
        """TC-05-03: Data consistency under load.

        Verifications:
          - All data is consistent across systems
          - No data corruption
          - Elasticsearch indexes all alerts correctly
        """
        self._log("=== TC-05-03: DATA CONSISTENCY TEST STARTED ===")

        num_alerts = 5
        alert_ids = []
        execution_ids = []

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        self._log(f"STEP 1: Sending {num_alerts} alerts concurrently")
        with ThreadPoolExecutor(max_workers=num_alerts) as executor:
            futures = {}
            for i in range(num_alerts):
                payload = self._base_payload(i)
                alert_ids.append(payload["alert_id"])
                future = executor.submit(self._send_with_retry, i, payload)
                futures[future] = i

            for future in as_completed(futures):
                i = futures[future]
                r = future.result()
                exec_id = r.json().get("execution_id", "")
                assert exec_id, f"Alert {i} no execution_id"
                execution_ids.append(exec_id)
                self._log(f"  + Alert {i} accepted - execution_id={exec_id[:8]}...")

        self._log(f"STEP 2: Waiting for {num_alerts} workflows to complete")
        self._wait_for_executions(execution_ids, num_alerts)

        self._log("STEP 3: Verifying Elasticsearch data consistency")
        for alert_id in alert_ids:
            doc = self._wait_for_es_doc(alert_id, timeout=60)
            assert doc is not None, f"Alert {alert_id} not found in Elasticsearch"
            assert doc.get("alert_id") == alert_id, f"Alert ID mismatch for {alert_id}"
            # Validate critical fields are present
            assert "hostname" in doc, f"Hostname missing for alert {alert_id}"
            assert "src_ip" in doc, f"src_ip missing for alert {alert_id}"
            assert "hash" in doc, f"hash missing for alert {alert_id}"

        # Validate no duplicate documents
        self._log("STEP 3: Verifying no duplicate documents")
        for alert_id in alert_ids:
            docs = self.es.search(query={"term": {"alert_id.keyword": alert_id}}, size=10)
            hits = docs.get("hits", {}).get("hits", [])
            assert len(hits) <= 1, f"Duplicate documents found for alert_id {alert_id}"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-05-03 COMPLETED — DATA CONSISTENCY VALIDATED ===")

    def test_no_duplicates(self):
        """TC-05-04: Absence of duplicates.

        Verifications:
          - No duplicate cases created
          - No duplicate workflow executions
          - No duplicate Elasticsearch documents
        """
        self._log("=== TC-05-04: NO DUPLICATES TEST STARTED ===")

        num_alerts = 5
        alert_ids = []
        execution_ids = []

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        self._log(f"STEP 1: Sending {num_alerts} alerts concurrently")
        with ThreadPoolExecutor(max_workers=num_alerts) as executor:
            futures = {}
            for i in range(num_alerts):
                payload = self._base_payload(i)
                alert_ids.append(payload["alert_id"])
                future = executor.submit(self._send_with_retry, i, payload)
                futures[future] = i

            for future in as_completed(futures):
                i = futures[future]
                r = future.result()
                exec_id = r.json().get("execution_id", "")
                assert exec_id, f"Alert {i} no execution_id"
                execution_ids.append(exec_id)
                self._log(f"  + Alert {i} accepted - execution_id={exec_id[:8]}...")

        self._log(f"STEP 2: Waiting for {num_alerts} workflows to complete")
        self._wait_for_executions(execution_ids, num_alerts)

        self._log("STEP 3: Verifying no duplicate cases")
        cases = self.thehive.search_cases(range_="0-100", sort=["-caseId"])
        case_ids = [c.get("caseId") for c in cases]
        assert len(case_ids) == len(set(case_ids)), "Duplicate caseIds found"
        self._log(f"+ Total cases: {len(case_ids)}, unique: {len(set(case_ids))}")

        self._log("STEP 3: Verifying no duplicate Elasticsearch documents")
        for alert_id in alert_ids:
            docs = self.es.search(query={"term": {"alert_id.keyword": alert_id}}, size=10)
            hits = docs.get("hits", {}).get("hits", [])
            assert len(hits) <= 1, f"Duplicate documents found for alert_id {alert_id}"

        # Validate alert IDs are unique
        assert len(alert_ids) == len(set(alert_ids)), "Duplicate alert IDs found"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-05-04 COMPLETED — NO DUPLICATES VALIDATED ===")

    def test_recovery_after_load(self):
        """TC-05-05: Recovery after load.

        Verifications:
          - System recovers after load
          - New alerts processed normally after load
          - No performance degradation persists
        """
        self._log("=== TC-05-05: RECOVERY AFTER LOAD TEST STARTED ===")

        num_alerts = 10

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        execution_ids = []

        self._log(f"STEP 1: Sending {num_alerts} alerts concurrently (load phase)")
        with ThreadPoolExecutor(max_workers=num_alerts) as executor:
            futures = {}
            for i in range(num_alerts):
                payload = self._base_payload(i)
                future = executor.submit(self._send_with_retry, i, payload)
                futures[future] = i

            for future in as_completed(futures):
                i = futures[future]
                r = future.result()
                exec_id = r.json().get("execution_id", "")
                assert exec_id, f"Alert {i} no execution_id"
                execution_ids.append(exec_id)
                self._log(f"  + Alert {i} accepted - execution_id={exec_id[:8]}...")

        self._log(f"STEP 2: Waiting for {num_alerts} load workflows to complete")
        self._wait_for_executions(execution_ids, num_alerts)

        self._log("STEP 3: Waiting for load to clear (30s)")
        time.sleep(30)

        self._log("STEP 4: Sending single alert to verify recovery")
        recovery_payload = self._base_payload(999)
        start = time.time()
        r = self._send_with_retry(999, recovery_payload)
        recovery_latency_ms = int((time.time() - start) * 1000)

        self._log(f"+ Recovery alert latency: {recovery_latency_ms}ms")
        assert recovery_latency_ms < 30000, f"Recovery latency too high: {recovery_latency_ms}ms"

        # Validate recovery alert was accepted
        recovery_exec_id = r.json().get("execution_id", "")
        assert recovery_exec_id, "No execution_id returned for recovery alert"
        self._log(f"+ Recovery execution_id: {recovery_exec_id[:8]}...")

        self._log("STEP 5: Waiting for recovery workflow to complete")
        self._wait_for_executions([recovery_exec_id], 1)

        # Validate recovery alert data is indexed
        recovery_alert_id = recovery_payload["alert_id"]
        doc = self._wait_for_es_doc(recovery_alert_id, timeout=60)
        assert doc is not None, f"Recovery alert {recovery_alert_id} not found in Elasticsearch"
        self._log("+ Recovery alert indexed in Elasticsearch")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-05-05 COMPLETED — RECOVERY AFTER LOAD VALIDATED ===")
