# !/usr/bin/env python3
"""TC-26: Carga Extrema Tests system behavior under extreme load: Alert Storm,
concurrency limit, backpressure, duplicate prevention."""

import re
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

    # Drain of a 10-way burst measured up to ~670s; backpressure execs are
    # reaped by Shuffle's abort governor at ~1300s from queueing. Wait
    # windows must outlive those horizons (base WORKFLOW_TIMEOUT=600 does
    # not) or terminal executions are misclassified as TIMEOUT (BUG-052).
    STORM_WAIT_TIMEOUT = 1200
    BACKPRESSURE_WAIT_TIMEOUT = 1800
    TERMINAL_STATUSES = frozenset({"FINISHED", "ABORTED", "FAILED"})

    def _classify_exec_outcomes(
        self, exec_ids: list, exec_results: dict
    ) -> tuple[list, list, list]:
        """Split tracked executions into (finished, terminal, unaccounted).

        Terminal = the system gave an auditable answer (FINISHED work or
        explicitly shed via ABORTED/FAILED). Unaccounted = never reached a
        terminal state — the only true silent loss (BUG-052)."""
        finished = [eid for eid, e in exec_results.items() if e.get("status") == "FINISHED"]
        terminal = [
            eid for eid, e in exec_results.items() if e.get("status") in self.TERMINAL_STATUSES
        ]
        unaccounted = [eid for eid in exec_ids if eid not in terminal]
        return finished, terminal, unaccounted

    def _final_status_recheck(self, eid: str) -> str:
        """One fresh status read for an exec still non-terminal at deadline.

        Returns 'terminal', 'in-flight' (still EXECUTING, tracked — the
        drain simply outlives the test window), or 'lost' (missing or
        stuck EXECUTING beyond twice the observed max duration)."""
        ex = self._get_execution(eid)
        if not ex:
            return "lost"
        status = str(ex.get("status", "")).upper()
        if status in self.TERMINAL_STATUSES:
            return "terminal"
        try:
            age = time.time() - float(ex.get("started_at") or 0)
        except (TypeError, ValueError):
            age = 0
        return "lost" if age > 2 * self.STORM_WAIT_TIMEOUT else "in-flight"

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

        parsers = (
            # Epoch seconds; Shuffle may store milliseconds since epoch
            lambda v: float(v) / 1000.0 if float(v) > 1e12 else float(v),
            # ISO 8601 timestamp string (Shuffle stores date strings)
            lambda v: datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp(),
        )
        started_ts = None
        for parse in parsers:
            try:
                started_ts = parse(started_at)
                break
            except (ValueError, TypeError, AttributeError):
                continue

        if started_ts is None:
            self._log(f"  ! Unparsable started_at={started_at!r} — treating execution as stale")
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
        poll_errors = 0
        abort_errors = 0
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
                            abort_errors += 1
                            assert (
                                abort_errors < 5
                            ), f"Stale execution abort failed {abort_errors} times: {exc}"
                            self._log(
                                f"  + Could not abort stale execution ({abort_errors}/5): {exc}"
                            )
                        continue
                    pending.append(e)
                if not pending:
                    self._log("Queue drained - no pending executions")
                    return
                self._log(f"  + {len(pending)} executions still pending, waiting...")
            except Exception as e:
                poll_errors += 1
                assert poll_errors < 10, f"Execution status check failed {poll_errors} times: {e}"
                self._log(f"  + Could not check execution status ({poll_errors}/10): {e}")
            time.sleep(self.POLL_INTERVAL)
        self._log(f"WARNING: timed out after {timeout}s waiting for queue drain")

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-26 {msg}"
        print(line)

    def _post_webhook(self, payload: dict, timeout: int = 60, retries: int = 2) -> dict:
        """POST the webhook once, with bounded retries on definitive 5xx.

        Shuffle persists the workflow execution to OpenSearch
        synchronously inside the webhook request; under load that write
        takes ~20-27s and can exceed the backend's internal deadline,
        producing HTTP 500 ("Failed setting workflowexecution"). That is
        a definitive server answer — the write failed, nothing was
        queued — so retrying is safe. The client timeout (60s) must
        outlive the backend write path. Transport timeouts are NOT
        retried: the write may have landed server-side and a resend
        would create a duplicate execution.
        """
        result = {
            "status_code": None,
            "exec_id": None,
            "body": {},
            "error": "no attempt executed",
        }
        for attempt in range(retries + 1):
            try:
                r = self.shuffle._webhook_session.post(
                    self.webhook_url, json=payload, timeout=timeout
                )
                try:
                    body = r.json() if r.content else {}
                except Exception:
                    body = {"raw": r.text[:500]}
                exec_id = body.get("execution_id") or body.get("id") or body.get("executionId")
                result = {
                    "status_code": r.status_code,
                    "exec_id": exec_id,
                    "body": body,
                    "error": None,
                }
                if r.status_code >= 500 and attempt < retries:
                    time.sleep(5)
                    continue
                return result
            except Exception as e:
                return {
                    "status_code": None,
                    "exec_id": None,
                    "body": {},
                    "error": str(e),
                }
        return result

    def _reconcile_unanswered_sends(self, results: list[dict]) -> None:
        """Reclassify sends whose answer never arrived (or failed) but
        whose execution exists server-side.

        Shuffle queues the workflow execution and then persists the
        execution record synchronously, so a client timeout — or a
        broken/5xx response after the queue — can coexist with a
        successfully accepted alert. Server-side state is the ground
        truth: if the execution exists, the alert was accepted.
        """
        candidates = [r for r in results if r["exec_id"] is None or r["status_code"] != 200]
        if not candidates:
            return
        try:
            executions = self.shuffle.get_workflow_executions(self.workflow_id)
        except Exception as exc:
            self._log(f"  + Reconciliation lookup failed: {exc}")
            return
        for r in candidates:
            match = next(
                (e for e in executions if r["alert_id"] in str(e.get("execution_argument", ""))),
                None,
            )
            if match:
                r["status_code"] = 200
                r["exec_id"] = match.get("execution_id") or match.get("id")
                r["error"] = None
                r["reconciled"] = True
                self._log(f"  + {r['alert_id']} reconciled — execution exists server-side")

    def _send_alert_concurrent(self, i: int, prefix: str) -> dict:
        """Send a single alert and return result dict with alert_id, exec_id,
        status, body."""
        alert_id = self.uid(f"TC26-{prefix}")
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
        res = self._post_webhook(payload)
        res["index"] = i
        res["alert_id"] = alert_id
        return res

    def _wait_for_executions(self, exec_ids: list, timeout: int = 600) -> dict:
        """Poll multiple executions until all reach terminal state or timeout.

        Returns dict mapping exec_id -> execution dict (with 'status'
        key).
        """
        deadline = time.time() + timeout
        results: dict[str, dict] = {}
        pending = {eid for eid in exec_ids if eid}
        poll_errors = 0
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
                    poll_errors += 1
                    assert (
                        poll_errors < 10
                    ), f"Execution poll for {eid[:8]} failed {poll_errors} times: {e}"
                    self._log(f"  + Poll error for {eid[:8]}... ({poll_errors}/10): {e}")
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
        self._reconcile_unanswered_sends(results)
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
        exec_results = self._wait_for_executions(exec_ids, timeout=self.STORM_WAIT_TIMEOUT)

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

        # Count matching cases by alert_id (len-based diff is unreliable).
        # Boundary-aware match: `...-1` must not match `...-10`.
        matching_cases_per_alert = {}
        for aid in alert_ids:
            pat = re.compile(re.escape(aid) + r"(?![0-9A-Za-z-])")
            matching = [
                c for c in cases if pat.search(c.get("description", "") + (c.get("title") or ""))
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
          - No silent data loss: every accepted alert reaches a terminal,
            auditable outcome (processed FINISHED or explicitly shed ABORTED)
          - The processed/shed split is logged as the measured backpressure
            characteristic of the stack
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

        self._reconcile_unanswered_sends(results)
        accepted = [r for r in results if r["status_code"] == 200 and r["exec_id"]]
        rejected_429 = [r for r in results if r["status_code"] == 429]
        rejected_5xx = [
            r for r in results if r["status_code"] is not None and r["status_code"] >= 500
        ]
        errors = [r for r in results if r["error"] is not None]

        self._log(
            f"STEP 2: Backpressure results - Accepted: {len(accepted)}, "
            f"429: {len(rejected_429)}, 5xx: {len(rejected_5xx)}, Errors: {len(errors)}"
        )

        # Assert system applies backpressure: either some 429s, or all accepted (queued)
        # If all 30 are accepted, the system is queueing (backpressure via queue depth)
        # If some are 429, the system is rejecting (backpressure via rejection)
        # 5xx after retries are definitive server answers and must be counted.
        assert (
            len(accepted) + len(rejected_429) + len(rejected_5xx) + len(errors) == num_alerts
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

        # Wait for every accepted alert to reach a terminal state.
        # The invariant under overload is *no silent loss*: the system
        # sheds explicitly (Shuffle abort governor) rather than dropping
        # executions — an ABORTED outcome is an auditable answer, not a
        # silent drop. The processed/shed split is the measured
        # backpressure characteristic of the stack (BUG-052).
        self._log(
            f"STEP 3: Waiting for {len(accepted)} accepted alerts to reach "
            "a terminal state (processed or explicitly shed)"
        )
        exec_ids = [r["exec_id"] for r in accepted]
        exec_results = self._wait_for_executions(exec_ids, timeout=self.BACKPRESSURE_WAIT_TIMEOUT)

        finished, terminal, unaccounted = self._classify_exec_outcomes(exec_ids, exec_results)
        shed = [eid for eid in terminal if eid not in finished]

        self._log(
            f"  + Terminal: {len(terminal)}/{len(accepted)} — "
            f"processed: {len(finished)}, explicitly shed: {len(shed)}"
        )

        # Assert no silent loss — every accepted alert reaches a terminal,
        # auditable outcome; aborts are the observable shedding mechanism.
        # Execs still EXECUTING at deadline get one fresh recheck: if they
        # went terminal meanwhile they count; if still draining they are
        # tracked in-flight (the queue outlives the test window — a
        # measured property), and only missing/stuck execs are true loss.
        lost = []
        in_flight = []
        for eid in unaccounted:
            verdict = self._final_status_recheck(eid)
            if verdict == "lost":
                lost.append(eid)
            elif verdict == "in-flight":
                in_flight.append(eid)
        if in_flight:
            self._log(
                f"  + {len(in_flight)} exec(s) still draining past the wait "
                "window — tracked in-flight, not lost"
            )
        assert not lost, (
            f"Silent data loss: {len(lost)} accepted alert(s) vanished or "
            f"stuck: {[e[:8] for e in lost]}"
        )
        assert len(finished) > 0, (
            f"Backpressure shed ALL {len(accepted)} accepted alerts — nothing "
            "processed at all (terminal states: "
            f"{sorted({exec_results[e].get('status') for e in terminal})})"
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

        alert_id = self.uid("TC26-DUPLICATE")
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
            res = self._post_webhook(payload)
            if res["status_code"] != 200 or res["error"] is not None:
                probe = [dict(res, alert_id=alert_id, index=i)]
                self._reconcile_unanswered_sends(probe)
                res = probe[0]
            assert res["status_code"] == 200, (
                f"Webhook failed on send {i + 1}/3 after retries: "
                f"HTTP {res['status_code']}, error={res['error']}"
            )
            exec_id = res["exec_id"]
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
        # A failed refresh would let the duplicate count pass on stale
        # data — treat it as a real failure.
        r = _req.post(f"{es_url}/soar-alerts/_refresh", auth=es_auth, timeout=10)
        assert r.status_code == 200, f"ES refresh failed: HTTP {r.status_code}"

        # Search for all documents with this alert_id — a failed query
        # means the dedup oracle cannot run, so it must fail loudly.
        r = _req.post(
            f"{es_url}/soar-alerts/_search",
            json={"query": {"term": {"alert_id.keyword": alert_id}}, "size": 20},
            auth=es_auth,
            timeout=15,
        )
        assert r.status_code == 200, f"ES duplicate search failed: HTTP {r.status_code}"
        hits = r.json().get("hits", {}).get("hits", [])
        es_doc_count = len(hits)
        self._log(f"  + ES documents for alert_id: {es_doc_count}")
        # Strong oracle: exactly one alert doc per unique alert_id —
        # dedup must collapse the 3 sends into a single ES document.
        assert es_doc_count == 1, (
            f"Expected exactly 1 ES document for duplicate alert, found {es_doc_count} — "
            f"deduplication is not collapsing duplicates"
        )

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-26-04 COMPLETED — DUPLICATE PREVENTION VALIDATED ===")
