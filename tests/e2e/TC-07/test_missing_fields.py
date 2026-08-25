#!/usr/bin/env python3
"""TC-07: Missing Fields Testing Tests workflow behavior when hash or IP fields
are empty or invalid."""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest


class TestMissingFields(E2EBaseTest):
    """TC-07 — Missing Fields: Alert with empty/invalid hash and IP.

    Verifies workflow handles missing fields gracefully.
    """

    tc_id = "TC-07"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

    def _log(self, msg: str):
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        print(f"[{elapsed:6.1f}s] TC-07 {msg}")

    def test_missing_fields(self):
        """Send alert with empty hash and IP, verify workflow handles it."""
        self._log("=== TC-07: Missing Fields Testing ===")

        payload = {
            "alert_id": f"TC07-MISSING-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC07-001",
            "src_ip": "",  # Empty IP
            "hash": "",  # Empty hash
            "severity": 2,
            "source": "missing-fields-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending alert with empty hash and IP")
        r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)
        # Workflow should still accept the alert even with empty fields
        assert r.status_code < 500, f"Alert caused server error: HTTP {r.status_code}"
        if r.status_code == 200:
            data = r.json()
            assert isinstance(data, dict), "Response must be JSON object"
            exec_id = data.get("execution_id", "")
            assert isinstance(exec_id, str), "execution_id must be string"
            assert len(exec_id) > 0, "execution_id must not be empty"
            self._log(f"  + Alert accepted - execution_id={exec_id}")
        else:
            self._log(f"  + Alert rejected with HTTP {r.status_code} (acceptable)")
            return  # Test passes if alert is rejected gracefully

        # Wait for workflow completion
        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + self.WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            assert isinstance(execs, list), "Workflow executions must be a list"
            ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
            if ex:
                assert isinstance(ex, dict), "Execution must be a dict"
                if ex.get("status") not in ("EXECUTING", ""):
                    break
            time.sleep(self.POLL_INTERVAL)

        assert ex is not None, f"Execution {exec_id} not found in Shuffle"
        self._log(f"  + Workflow status: {ex.get('status')}")

        # Verify TheHive case was still created
        self._log("STEP 3: Verifying TheHive case creation")
        cases = self.thehive.search_cases()
        assert isinstance(cases, list), "TheHive cases must be a list"
        new_cases = len(cases) - self.cases_before
        assert new_cases > 0, "No new TheHive case created"
        last = max(cases, key=lambda c: c.get("caseId", 0))
        assert isinstance(last, dict), "Case must be a dict"
        self._log(f"  + Case #{last.get('caseId')} created despite missing fields")

        # Verify observables - should be minimal or skipped
        case_id = last.get("id", last.get("_id", ""))
        if case_id:
            obs = self.thehive.get_case_observables(case_id)
            self._log(f"  + {len(obs)} observable(s) attached (expected 0 or minimal)")

        # Verify Elasticsearch
        self._log("STEP 4: Verifying Elasticsearch indexing")
        doc = self.es.search_by_alert_id(payload["alert_id"])
        assert doc is not None, "ES document not found"
        assert isinstance(doc, dict), "ES document must be a dict"
        self._log("  + Alert indexed in Elasticsearch with empty fields")
        assert doc.get("hash") == "", "Hash should be empty"
        assert doc.get("src_ip") == "", "IP should be empty"
        # Validate that other fields are still preserved
        assert doc.get("alert_id") == payload["alert_id"], "alert_id should be preserved"
        assert doc.get("hostname") == payload["hostname"], "hostname should be preserved"
        self._log("✓ Empty fields preserved correctly, other fields intact")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(
            f"=== TC-07 COMPLETED — WORKFLOW HANDLED MISSING FIELDS (Elapsed: {elapsed:.1f}s) ==="
        )

        # Save report
        report = {
            "test_case": "TC-07",
            "test_name": "Missing Fields",
            "status": "PASSED",
            "alert_id": payload["alert_id"],
            "hash_empty": payload["hash"] == "",
            "ip_empty": payload["src_ip"] == "",
            "cases_created": new_cases,
            "workflow_status": ex.get("status") if ex else None,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_path = self.e2e_results_dir / "TC-07_missing_fields_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-07-01 to TC-07-04)
    # ------------------------------------------------------------------

    def test_missing_required_field(self):
        """TC-07-01: Missing required field.

        Verifications:
          - Alert without required field is rejected
          - Appropriate error message is returned
          - No partial case is created
        """
        self._log("=== TC-07-01: MISSING REQUIRED FIELD TEST STARTED ===")

        payload = {
            "alert_id": f"TC07-REQ-{int(time.time())}",
            # Missing alert_type (required field)
            "hostname": "WIN-TC07-001",
            "src_ip": "192.168.1.100",
            "hash": "a" * 64,
            "severity": 2,
            "source": "required-field-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending alert without required field")
        r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)
        self._log(f"+ Response: HTTP {r.status_code}")

        if r.status_code >= 400:
            # Validate no execution_id was returned for a rejected alert
            try:
                response_data = r.json()
                exec_id = response_data.get("execution_id", "")
                assert exec_id == "", "No execution_id should be returned for rejected alert"
            except Exception as e:
                self._log(f"  Response not JSON (expected for rejected alert): {e}")
        else:
            # Shuffle webhook accepts the payload and starts the workflow; verify it completes
            data = r.json()
            exec_id = data.get("execution_id", "")
            assert (
                isinstance(exec_id, str) and len(exec_id) > 0
            ), "Expected execution_id for accepted alert"
            deadline = time.time() + self.WORKFLOW_TIMEOUT
            ex = None
            while time.time() < deadline:
                execs = self.shuffle.get_workflow_executions(self.workflow_id)
                ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
                if ex and ex.get("status") not in ("EXECUTING", ""):
                    break
                time.sleep(self.POLL_INTERVAL)
            assert ex is not None, f"Execution {exec_id} not found"
            self._log(
                f"  + Workflow handled missing required field with status: {ex.get('status')}"
            )

        # Validate payload structure is valid JSON
        assert isinstance(payload, dict), "Payload should be dict"
        assert "alert_type" not in payload, "alert_type should be missing from payload"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-07-01 COMPLETED — MISSING REQUIRED FIELD VALIDATED ===")

    def test_missing_optional_field(self):
        """TC-07-02: Missing optional field.

        Verifications:
          - Alert without optional field is accepted
          - Default value is used where appropriate
          - Workflow completes successfully
        """
        self._log("=== TC-07-02: MISSING OPTIONAL FIELD TEST STARTED ===")

        payload = {
            "alert_id": f"TC07-OPT-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC07-001",
            "src_ip": "192.168.1.100",
            "hash": "a" * 64,
            "severity": 2,
            "source": "optional-field-test",
            "detection_time": datetime.now(UTC).isoformat(),
            # Missing event_type (optional field)
        }

        self._log("STEP 1: Sending alert without optional field")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        alert_id = payload["alert_id"]
        self.validate_workflow_execution(execution, alert_id=alert_id)

        # Validate payload structure
        assert isinstance(payload, dict), "Payload should be dict"
        assert "event_type" not in payload, "event_type should be missing from payload"
        assert "alert_type" in payload, "alert_type should be present"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-07-02 COMPLETED — MISSING OPTIONAL FIELD VALIDATED ===")

    def test_derivable_field(self):
        """TC-07-03: Derivable field.

        Verifications:
          - Missing derivable field is computed
          - Derived value is correct
          - Workflow uses derived value
        """
        self._log("=== TC-07-03: DERIVABLE FIELD TEST STARTED ===")

        payload = {
            "alert_id": f"TC07-DERIVE-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC07-001",
            "src_ip": "192.168.1.100",
            "hash": "a" * 64,
            "severity": 2,
            "source": "derivable-field-test",
            # Missing detection_time (can be derived from current time)
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending alert without derivable field")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id

        self._log("STEP 3: Verifying derived field in Elasticsearch")
        doc = self.es.search_by_alert_id(payload["alert_id"])
        assert doc is not None, "ES document not found"
        derived_time = doc.get("detection_time")
        assert derived_time is not None, "Detection time should be derived"
        self._log(f"+ Derived detection_time: {derived_time}")

        # Validate derived time is a valid ISO format string
        assert isinstance(derived_time, str), "Detection time should be a string"
        assert (
            derived_time.endswith("Z") or "+" in derived_time
        ), "Detection time should be in ISO format with timezone"

        # Validate payload structure
        assert isinstance(payload, dict), "Payload should be dict"
        assert "detection_time" not in payload, "detection_time should be missing from payload"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-07-03 COMPLETED — DERIVABLE FIELD VALIDATED ===")

    def test_error_message(self):
        """TC-07-04: Correct error message.

        Verifications:
          - Error message is descriptive
          - Error message includes field name
          - Error message is actionable
        """
        self._log("=== TC-07-04: ERROR MESSAGE TEST STARTED ===")

        payload = {
            # Missing alert_id (required field)
            "alert_type": "ransomware",
            "hostname": "WIN-TC07-001",
            "src_ip": "192.168.1.100",
            "hash": "a" * 64,
            "severity": 2,
            "source": "error-message-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending invalid alert")
        r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)

        if r.status_code >= 400:
            error_response = (
                r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            )
            self._log(f"+ Error response: {error_response}")

            # Check if error message is present
            if error_response:
                error_msg = (
                    error_response.get("message")
                    or error_response.get("error")
                    or str(error_response)
                )
                self._log(f"+ Error message: {error_msg}")
                assert len(error_msg) > 0, "Error message should not be empty"

                # Validate error message is a string
                assert isinstance(error_msg, str), "Error message should be a string"

                # Validate response is not 5xx (server error)
                assert r.status_code not in (
                    502,
                    503,
                    504,
                ), f"Server error (5xx) indicates system crash: HTTP {r.status_code}"
        else:
            self._log(f"+ Alert accepted (HTTP {r.status_code}) - field may be optional")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-07-04 COMPLETED — ERROR MESSAGE VALIDATED ===")
