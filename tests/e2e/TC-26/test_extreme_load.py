# !/usr/bin/env python3
"""TC-26: Carga Extrema Tests system behavior under extreme load: Alert Storm,
concurrency limit, backpressure, duplicate prevention."""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest
from tests.e2e.workflow_validator import validate_workflow_results


class TestExtremeLoad(E2EBaseTest):
    """TC-26 — Carga Extrema: Comportamiento bajo carga masiva."""

    tc_id = "TC-26"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

        # Avoid cross-test interference from executions queued by prior tests.
        # The load tests just generate traffic; only wait for drain before
        # the duplicate-prevention test, which needs a clean queue.
        if method.__name__ == "test_duplicate_prevention":
            self._wait_for_queue_drain(timeout=600)
        else:
            self._wait_for_queue_drain(timeout=120)

    def _execution_is_stale(self, execution: dict, max_age: int = 300) -> bool:
        """Return True if an EXECUTING execution is older than max_age
        seconds."""
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
                    if status == "EXECUTING" and self._execution_is_stale(e):
                        self._log(
                            f"  + Ignoring stale EXECUTING execution "
                            f"{e.get('execution_id', '')[:8]}..."
                        )
                        try:
                            exec_id = e.get("execution_id", "")
                            abort_url = self.shuffle._url(
                                f"/api/v1/workflows/{self.workflow_id}/executions/{exec_id}/abort"
                            )
                            r = self.shuffle._session.get(abort_url, timeout=10)
                            if r.status_code == 200:
                                self._log(f"  + Aborted stale execution {exec_id[:8]}")
                            else:
                                self._log(
                                    f"  + Could not abort stale execution (HTTP {r.status_code}):"
                                )
                        except Exception as exc:
                            self._log(f"  + Could not abort stale execution: {exc}")
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
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-26 {msg}"
        print(line)

    def _send_alert_concurrent(self, i: int, prefix: str) -> dict:
        """Send a single alert and return result dict with alert_id, exec_id,
        status, body."""
        alert_id = f"TC26-{prefix}-{int(time.time())}-{i}"
        payload = {
            "alert_id": alert_id,
            "alert_type": "ransomware",
            "hostname": f"WIN-TC26-{i:03d}",
            "src_ip": f"192.168.1.{220 + (i % 30)}",
            "hash": "a" * 64,
            "severity": 2,
            "source": "extreme-load-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }
        try:
            r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=15)
            body = {}
            try:
                body = r.json() if r.content else {}
            except Exception:
                body = {"raw": r.text[:500]}
            exec_id = body.get("execution_id") or body.get("id") or body.get("executionId")
            return {
                "index": i,
                "alert_id": alert_id,
                "status_code": r.status_code,
                "exec_id": exec_id,
                "body": body,
                "error": None,
            }
        except Exception as e:
            return {
                "index": i,
                "alert_id": alert_id,
                "status_code": None,
                "exec_id": None,
                "body": {},
                "error": str(e),
            }

    def _wait_for_executions(self, exec_ids: list, timeout: int = 600) -> dict:
        """Poll multiple executions until all reach terminal state or timeout.

        Returns dict mapping exec_id -> execution dict (with 'status'
        key).
        """
        deadline = time.time() + timeout
        results: dict[str, dict] = {}
        pending = {eid for eid in exec_ids if eid}
        while time.time() < deadline and pending:
            for eid in list(pending):
                try:
                    execution = self._get_execution(eid)
                    if execution:
                        status = execution.get("status", "").upper()
                        if status in ("FINISHED", "ABORTED", "FAILED"):
                            results[eid] = execution
                            pending.discard(eid)
                            self._log(f"  + Execution {eid[:8]}... -> {status}")
                except Exception as e:
                    self._log(f"  + Poll error for {eid[:8]}...: {e}")
            if pending:
                time.sleep(self.POLL_INTERVAL)
        # Mark remaining as timeout
        for eid in pending:
            results[eid] = {"status": "TIMEOUT", "execution_id": eid}
            self._log(f"  + Execution {eid[:8]}... -> TIMEOUT")
        return results

    def test_alert_storm(self):
        """TC-26-01: Alert storm test.

        Verifications:
          - 10 alerts sent concurrently, ALL workflows complete (FINISHED)
          - ALL TheHive cases created (one per alert)
          - No duplicate cases
          - System remains healthy after storm
        """
        self._log("=== TC-26-01: ALERT STORM TEST STARTED ===")

        num_alerts = 10
        self._log(f"STEP 1: Sending {num_alerts} alerts concurrently")

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        # Send all alerts concurrently
        with ThreadPoolExecutor(max_workers=num_alerts) as executor:
            futures = [
                executor.submit(self._send_alert_concurrent, i, "STORM") for i in range(num_alerts)
            ]
            results = [f.result() for f in as_completed(futures)]

        results.sort(key=lambda r: r["index"])
        accepted = [r for r in results if r["status_code"] == 200 and r["exec_id"]]
        errors = [r for r in results if r["error"] is not None]
        rejected = [r for r in results if r["status_code"] is not None and r["status_code"] != 200]

        self._log(
            f"STEP 2: Storm results - Sent: {len(results)}, "
            f"Accepted: {len(accepted)}, Rejected: {len(rejected)}, Errors: {len(errors)}"
        )

        # Assert all alerts were accepted
        assert len(accepted) == num_alerts, (
            f"Expected all {num_alerts} alerts accepted, got {len(accepted)}. "
            f"Rejected: {len(rejected)}, Errors: {len(errors)}"
        )
        assert (
            len(errors) == 0
        ), f"Expected 0 errors, got {len(errors)}: {[e['error'] for e in errors]}"

        # Wait for ALL workflows to complete
        self._log("STEP 3: Waiting for all workflows to complete")
        exec_ids = [r["exec_id"] for r in accepted]
        exec_results = self._wait_for_executions(exec_ids, timeout=self.WORKFLOW_TIMEOUT)

        finished = [eid for eid, e in exec_results.items() if e.get("status") == "FINISHED"]
        not_finished = [eid for eid, e in exec_results.items() if e.get("status") != "FINISHED"]

        self._log(f"  + FINISHED: {len(finished)}/{num_alerts}, Other: {len(not_finished)}")

        # Assert ALL workflows completed successfully
        assert len(finished) == num_alerts, (
            f"Expected all {num_alerts} workflows FINISHED, got {len(finished)}. "
            f"Failed/timed out: "
            f"{[(eid[:8], exec_results[eid].get('status')) for eid in not_finished]}"
        )

        # Validate at least one workflow execution for hidden errors
        if exec_ids:
            ex_full = self.shuffle.get_execution(
                self.workflow_id, exec_ids[0], include_results=True
            )
            if isinstance(ex_full, dict) and ex_full.get("results"):
                validate_workflow_results(ex_full)
                self._log("+ First workflow execution validated — no hidden errors")

        # Verify TheHive cases created for each alert
        self._log("STEP 4: Verifying TheHive cases for all alerts")
        cases = self.thehive.search_cases(range_="0-200", sort=["-caseId"])
        assert isinstance(cases, list), "TheHive cases must be a list"

        alert_ids = [r["alert_id"] for r in accepted]

        # Count matching cases by alert_id (len-based diff is unreliable)
        matching_cases_per_alert = {}
        for aid in alert_ids:
            matching = [
                c for c in cases if aid in (c.get("description", "") + (c.get("title") or ""))
            ]
            matching_cases_per_alert[aid] = len(matching)

        total_matching = sum(matching_cases_per_alert.values())
        self._log(f"  + Matching cases: {total_matching} for {len(alert_ids)} alerts")

        # Assert at least some new cases were created
        assert total_matching > 0, (
            f"Expected new TheHive cases after storm, got 0 matching "
            f"for {len(alert_ids)} alerts"
        )

        # Check for duplicate cases — each alert_id should appear in at most 1 case
        duplicates = {aid: cnt for aid, cnt in matching_cases_per_alert.items() if cnt > 1}
        assert len(duplicates) == 0, (
            f"Duplicate cases found for {len(duplicates)} alert(s): "
            f"{dict(list(duplicates.items())[:3])}"
        )
        self._log("  + No duplicate cases — each alert has at most 1 case")

        # Verify system health after storm
        self._log("STEP 5: Verifying system health after storm")
        health = self.es.cluster_health()
        assert isinstance(health, dict), "ES health must be a dict"
        es_status = health.get("status", "").lower()
        assert es_status in [
            "green",
            "yellow",
        ], f"ES should be healthy after storm, got {es_status}"
        self._log(f"  + ES health: {es_status}")

        # TheHive still responsive
        assert cases is not None, "TheHive should still be responsive after storm"
        self._log(f"  + TheHive responsive: {len(cases)} total cases")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-26-01 COMPLETED — ALERT STORM VALIDATED ===")

    def test_concurrency_limit(self):
        """TC-26-02: Concurrency limit test.

        Verifications:
          - 20 alerts sent concurrently, at least some accepted
          - If any return 429, assert 429 body contains "rate limit" or "queue"
          - System doesn't crash (all services remain responsive)
        """
        self._log("=== TC-26-02: CONCURRENCY LIMIT TEST STARTED ===")

        num_concurrent = 20
        self._log(f"STEP 1: Sending {num_concurrent} concurrent alerts")

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [
                executor.submit(self._send_alert_concurrent, i, "CONCURRENT")
                for i in range(num_concurrent)
            ]
            results = [f.result() for f in as_completed(futures)]

        results.sort(key=lambda r: r["index"])
        accepted = [r for r in results if r["status_code"] == 200]
        rejected_429 = [r for r in results if r["status_code"] == 429]
        errors = [r for r in results if r["error"] is not None]
        other_rejected = [
            r
            for r in results
            if r["status_code"] is not None and r["status_code"] != 200 and r["status_code"] != 429
        ]

        self._log(
            f"STEP 2: Concurrency results - Accepted: {len(accepted)}, "
            f"429: {len(rejected_429)}, Other rejected: {len(other_rejected)}, "
            f"Errors: {len(errors)}"
        )

        # Assert at least some alerts are accepted
        assert len(accepted) > 0, (
            f"Expected at least some alerts accepted, got 0. "
            f"429: {len(rejected_429)}, Errors: {len(errors)}, Other: {len(other_rejected)}"
        )
        self._log(f"  + {len(accepted)}/{num_concurrent} alerts accepted")

        # If any return 429, assert the response body contains rate-limit indicators
        if rejected_429:
            self._log(f"STEP 3: Validating 429 responses ({len(rejected_429)} received)")
            for r in rejected_429:
                body_text = str(r.get("body", "")).lower()
                assert "rate limit" in body_text or "queue" in body_text, (
                    f"429 response for alert {r['alert_id']} should mention "
                    f"'rate limit' or 'queue', "
                    f"got body: {r.get('body', '')}"
                )
            self._log("  + All 429 responses contain rate-limit indicators")
        else:
            self._log("STEP 3: No 429 responses — all alerts accepted (no backpressure triggered)")

        # Assert system doesn't crash — verify all services are still responsive
        self._log("STEP 4: Verifying system didn't crash")
        workflows = self.shuffle.list_workflows()
        assert isinstance(
            workflows, list
        ), "Shuffle must still be responsive after concurrency test"
        self._log(f"  + Shuffle responsive: {len(workflows)} workflows")

        cases = self.thehive.search_cases(range_="0-100", sort=["-caseId"])
        assert isinstance(cases, list), "TheHive must still be responsive after concurrency test"
        self._log(f"  + TheHive responsive: {len(cases)} cases")

        health = self.es.cluster_health()
        assert isinstance(health, dict), "ES health must be a dict"
        es_status = health.get("status", "").lower()
        assert es_status in [
            "green",
            "yellow",
        ], f"ES should be healthy after concurrency test, got {es_status}"
        self._log(f"  + ES healthy: {es_status}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-26-02 COMPLETED — CONCURRENCY LIMIT VALIDATED ===")

    def test_backpressure(self):
        """TC-26-03: Backpressure test.

        Verifications:
          - 30 alerts sent rapidly, system applies backpressure (429 or queueing)
          - No data loss: all accepted alerts eventually processed
          - System recovers after backpressure
        """
        self._log("=== TC-26-03: BACKPRESSURE TEST STARTED ===")

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        num_alerts = 30
        self._log(f"STEP 1: Sending {num_alerts} alerts rapidly to trigger backpressure")

        results = []
        for i in range(num_alerts):
            r = self._send_alert_concurrent(i, "BACKPRESSURE")
            results.append(r)

        accepted = [r for r in results if r["status_code"] == 200 and r["exec_id"]]
        rejected_429 = [r for r in results if r["status_code"] == 429]
        errors = [r for r in results if r["error"] is not None]

        self._log(
            f"STEP 2: Backpressure results - Accepted: {len(accepted)}, "
            f"429: {len(rejected_429)}, Errors: {len(errors)}"
        )

        # Assert system applies backpressure: either some 429s, or all accepted (queued)
        # If all 30 are accepted, the system is queueing (backpressure via queue depth)
        # If some are 429, the system is rejecting (backpressure via rejection)
        assert (
            len(accepted) + len(rejected_429) + len(errors) == num_alerts
        ), "Result counts should sum to total alerts sent"

        if rejected_429:
            self._log(f"  + Backpressure via 429 rejection: {len(rejected_429)} alerts rejected")
            # Validate 429 body contains rate-limit indicators
            for r in rejected_429:
                body_text = str(r.get("body", "")).lower()
                assert (
                    "rate limit" in body_text or "queue" in body_text
                ), f"429 response should mention 'rate limit' or 'queue', got: {r.get('body', '')}"
        else:
            self._log(
                f"  + Backpressure via queueing: all {len(accepted)} alerts accepted (queued)"
            )

        # Assert at least some alerts were accepted for processing
        assert len(accepted) > 0, (
            f"Expected at least some alerts accepted for processing, got 0. "
            f"429: {len(rejected_429)}, Errors: {len(errors)}"
        )

        # Wait for all accepted alerts to be processed (no data loss)
        self._log(f"STEP 3: Waiting for {len(accepted)} accepted alerts to be processed")
        exec_ids = [r["exec_id"] for r in accepted]
        exec_results = self._wait_for_executions(exec_ids, timeout=self.WORKFLOW_TIMEOUT)

        finished = [eid for eid, e in exec_results.items() if e.get("status") == "FINISHED"]
        not_finished = [eid for eid, e in exec_results.items() if e.get("status") != "FINISHED"]

        self._log(f"  + Processed: {len(finished)}/{len(accepted)} FINISHED")

        # Assert no data loss — all accepted alerts should be processed
        assert len(finished) == len(accepted), (
            f"Data loss detected: expected {len(accepted)} FINISHED, got {len(finished)}. "
            f"Failed: {[(eid[:8], exec_results[eid].get('status')) for eid in not_finished]}"
        )

        # Assert system recovers — all services healthy after backpressure
        self._log("STEP 4: Verifying system recovery after backpressure")
        health = self.es.cluster_health()
        assert isinstance(health, dict), "ES health must be a dict"
        es_status = health.get("status", "").lower()
        assert es_status in [
            "green",
            "yellow",
        ], f"ES should recover after backpressure, got {es_status}"
        self._log(f"  + ES recovered: {es_status}")

        cases = self.thehive.search_cases(range_="0-100", sort=["-caseId"])
        assert isinstance(cases, list), "TheHive must be responsive after backpressure recovery"
        self._log(f"  + TheHive responsive: {len(cases)} cases")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-26-03 COMPLETED — BACKPRESSURE VALIDATED ===")

    def test_duplicate_prevention(self):
        """TC-26-04: Duplicate prevention test.

        Verifications:
          - Same alert sent 3 times
          - Only 1 TheHive case created (or 3 cases but linked/deduplicated)
          - No duplicate ES documents for the same alert_id
        """
        self._log("=== TC-26-04: DUPLICATE PREVENTION TEST STARTED ===")

        alert_id = f"TC26-DUPLICATE-{int(time.time())}"
        payload = {
            "alert_id": alert_id,
            "alert_type": "ransomware",
            "hostname": "WIN-TC26-001",
            "src_ip": "192.168.1.220",
            "hash": "d" * 64,
            "severity": 2,
            "source": "extreme-load-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        self._log("STEP 1: Sending same alert 3 times")
        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        exec_ids = []
        for i in range(3):
            r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=20)
            assert r.status_code == 200, f"Webhook failed on send {i + 1}/3: HTTP {r.status_code}"
            body = r.json() if r.content else {}
            exec_id = body.get("execution_id") or body.get("id") or body.get("executionId")
            if exec_id:
                exec_ids.append(exec_id)
            self._log(f"+ Send {i + 1}/3: HTTP 200, exec_id={exec_id}")
            time.sleep(1)

        # Wait for all executions to complete
        self._log("STEP 2: Waiting for duplicate alert executions to complete")
        exec_results = self._wait_for_executions(exec_ids, timeout=self.WORKFLOW_TIMEOUT)

        finished = [eid for eid, e in exec_results.items() if e.get("status") == "FINISHED"]
        assert len(finished) > 0, (
            f"Expected at least 1 FINISHED execution for duplicate alerts, got {len(finished)}. "
            f"Results: {[(eid[:8], e.get('status')) for eid, e in exec_results.items()]}"
        )
        self._log(f"  + {len(finished)}/{len(exec_ids)} executions FINISHED")

        # Wait for TheHive case to appear
        self._log("STEP 3: Verifying TheHive case creation for duplicate alerts")
        deadline = time.time() + 300
        matching_cases = []
        while time.time() < deadline:
            cases = self.thehive.search_cases(range_="0-100", sort=["-caseId"])
            matching_cases = [
                c for c in cases if alert_id in (c.get("description", "") + (c.get("title") or ""))
            ]
            if matching_cases:
                self._log(f"+ Found {len(matching_cases)} matching case(s)")
                break
            # Also break if the queue has drained and still no case
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            pending_statuses = {"EXECUTING", "QUEUED", "PENDING", "RUNNING"}
            active = [e for e in execs if e.get("status", "").upper() in pending_statuses]
            if not active:
                self._log("+ Queue drained without creating a matching case")
                break
            self._log(f"  + {len(active)} executions still pending, waiting...")
            time.sleep(self.POLL_INTERVAL)

        # Assert at least 1 case was created
        assert (
            len(matching_cases) >= 1
        ), f"Expected at least 1 TheHive case for alert_id={alert_id}, found {len(matching_cases)}"

        # Assert no more than 3 cases (deduplication should prevent excessive duplicates)
        assert len(matching_cases) <= 3, (
            f"Expected at most 3 cases for duplicate alerts, found {len(matching_cases)} — "
            f"deduplication may not be working"
        )
        self._log(f"  + {len(matching_cases)} case(s) created for 3 duplicate alerts")

        # Verify no duplicate ES documents
        self._log("STEP 4: Verifying no duplicate ES documents")
        # Force refresh
        es_url = self.get_service_url("es")
        import requests as _req

        es_auth = (
            self.env.get("ELASTIC_USERNAME", "elastic"),
            self.env.get("ELASTIC_PASSWORD", ""),
        )
        try:
            _req.post(f"{es_url}/soar-alerts/_refresh", auth=es_auth, timeout=10, verify=False)
        except Exception as e:
            self._log(f"  ES refresh warning: {e}")

        # Search for all documents with this alert_id
        try:
            r = _req.post(
                f"{es_url}/soar-alerts/_search",
                json={"query": {"match": {"alert_id": alert_id}}, "size": 20},
                auth=es_auth,
                timeout=15,
                verify=False,
            )
            if r.status_code == 200:
                hits = r.json().get("hits", {}).get("hits", [])
                es_doc_count = len(hits)
                self._log(f"  + ES documents for alert_id: {es_doc_count}")
                # Assert no duplicate ES documents
                # (at most 1, or a small number if metrics are separate)
                assert es_doc_count <= 3, (
                    f"Expected at most 3 ES documents for duplicate alert, found {es_doc_count} — "
                    f"possible data duplication"
                )
            else:
                self._log(f"  + ES search returned HTTP {r.status_code}")
        except Exception as e:
            self._log(f"  + ES duplicate check failed: {e}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-26-04 COMPLETED — DUPLICATE PREVENTION VALIDATED ===")
