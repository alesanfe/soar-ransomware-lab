#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case 33 (Containment Endpoint)
Tests the /api/v1/contain endpoint that the Shuffle workflow calls (Node 27)
when the decision node classifies an alert as malicious.

Verifications:
  1. POST /api/v1/contain returns 200 with correct response structure.
  2. Response contains status="simulated".
  3. Response includes simulated actions (network_isolation, process_termination, account_lockdown).
  4. Response echoes back alert_id, case_id, and hostname from request.
  5. Timestamp is present and valid ISO format.
  6. Invalid requests (missing fields) return 422 validation error.

Requires a live Docker stack (make up). Reads API URL from environment.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest


class TestContainmentEndpoint(E2EBaseTest):
    """TC-31 — E2E: /api/v1/contain simulated containment endpoint."""

    tc_id = "TC-31"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self.api_url = self.get_service_url("api")
        self.s.headers.update({"Content-Type": "application/json"})

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-31 {msg}"
        print(line)

    def test_containment_endpoint_success(self):
        """TC-31-01: POST /api/v1/contain returns simulated containment
        response."""
        self._log("=== TC-31-01: CONTAINMENT ENDPOINT SUCCESS TEST STARTED ===")

        payload = {
            "alert_id": f"TC33-CONTAIN-{int(datetime.now(UTC).timestamp())}",
            "case_id": "test-case-id-12345",
            "hostname": "INFECTED-WIN-001",
            "mode": "simulation",
        }

        self._log(f"STEP 1: Sending POST /api/v1/contain with payload: {payload['alert_id']}")
        try:
            r = self.s.post(f"{self.api_url}/api/v1/contain", json=payload, timeout=15)
        except requests.exceptions.ConnectionError:
            pytest.fail(f"API not accessible at {self.api_url}")

        assert r.status_code == 200, f"Expected HTTP 200, got {r.status_code}: {r.text[:300]}"
        self._log(f"+ Response status: {r.status_code}")

        data = r.json()
        assert isinstance(data, dict), "Response must be a JSON object"

        # Verify status field
        assert (
            data.get("status") == "simulated"
        ), f"Expected status 'simulated', got '{data.get('status')}'"
        self._log(f"+ Status: {data['status']}")

        # Verify echoed fields
        assert (
            data.get("alert_id") == payload["alert_id"]
        ), f"alert_id mismatch: sent={payload['alert_id']}, got={data.get('alert_id')}"
        assert (
            data.get("case_id") == payload["case_id"]
        ), f"case_id mismatch: sent={payload['case_id']}, got={data.get('case_id')}"
        assert (
            data.get("hostname") == payload["hostname"]
        ), f"hostname mismatch: sent={payload['hostname']}, got={data.get('hostname')}"
        self._log("+ Echoed fields match: alert_id, case_id, hostname")

        # Verify simulated actions
        actions = data.get("actions", [])
        assert isinstance(actions, list), "Actions must be a list"
        assert len(actions) > 0, "Actions list must not be empty"
        expected_actions = {"network_isolation", "process_termination", "account_lockdown"}
        actual_actions = set(actions)
        assert expected_actions.issubset(
            actual_actions
        ), f"Expected actions {expected_actions}, got {actual_actions}"
        self._log(f"+ Simulated actions: {actions}")

        # Verify timestamp
        timestamp = data.get("timestamp", "")
        assert timestamp, "Response missing timestamp"
        assert "T" in timestamp, f"Timestamp should be ISO format, got: {timestamp}"
        self._log(f"+ Timestamp: {timestamp}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-31-01 COMPLETED — CONTAINMENT ENDPOINT VALIDATED ===")

    def test_containment_endpoint_validation_error(self):
        """TC-31-02: POST /api/v1/contain with missing fields returns 422."""
        self._log("=== TC-31-02: CONTAINMENT ENDPOINT VALIDATION ERROR TEST STARTED ===")

        # Missing required fields (alert_id, case_id, hostname)
        incomplete_payload = {"mode": "simulation"}

        self._log("STEP 1: Sending POST /api/v1/contain with incomplete payload")
        try:
            r = self.s.post(f"{self.api_url}/api/v1/contain", json=incomplete_payload, timeout=15)
        except requests.exceptions.ConnectionError:
            pytest.fail(f"API not accessible at {self.api_url}")

        assert (
            r.status_code == 422
        ), f"Expected HTTP 422 validation error, got {r.status_code}: {r.text[:300]}"
        self._log(f"+ Validation error returned: {r.status_code}")

        # Validate that the error response is JSON (FastAPI validation error format)
        try:
            error_data = r.json()
        except ValueError:
            pytest.fail(f"422 response must be valid JSON, got: {r.text[:300]}")
        assert isinstance(
            error_data, dict
        ), f"422 error response must be a JSON dict, got {type(error_data).__name__}"

        # Validate that the error detail mentions missing required fields
        detail = error_data.get("detail", [])
        assert isinstance(
            detail, list
        ), f"422 error 'detail' must be a list of validation errors, got {type(detail).__name__}"
        assert len(detail) > 0, "422 error must contain at least one validation error detail"

        # Check that the validation errors reference the missing required fields
        detail_fields = [d.get("loc", []) for d in detail if isinstance(d, dict)]
        missing_field_names = [
            loc[-1] for loc in detail_fields if isinstance(loc, list) and len(loc) > 0
        ]
        expected_missing = {"alert_id", "case_id", "hostname"}
        found_missing = set(missing_field_names) & expected_missing
        assert len(found_missing) > 0, (
            f"422 validation error should mention missing required fields {expected_missing}, "
            f"got fields: {missing_field_names}"
        )
        self._log(f"+ Missing fields reported in validation error: {found_missing}")

        # Validate that no containment action was recorded (no side effects from invalid request)
        # The response should only contain error info, not a containment result
        assert (
            "actions" not in error_data
        ), "422 validation error response must not contain containment 'actions'"
        assert (
            "status" not in error_data or error_data["status"] != "simulated"
        ), "422 validation error must not report a successful containment status"
        self._log("+ No containment action recorded for invalid request")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-31-02 COMPLETED — VALIDATION ERROR CONFIRMED ===")

    def test_containment_endpoint_default_mode(self):
        """TC-31-03: POST /api/v1/contain without mode field uses default
        'simulation'."""
        self._log("=== TC-31-03: CONTAINMENT ENDPOINT DEFAULT MODE TEST STARTED ===")

        payload = {
            "alert_id": f"TC33-DEFMODE-{int(datetime.now(UTC).timestamp())}",
            "case_id": "test-case-id-67890",
            "hostname": "WORKSTATION-002",
        }

        self._log("STEP 1: Sending POST /api/v1/contain without mode field")
        try:
            r = self.s.post(f"{self.api_url}/api/v1/contain", json=payload, timeout=15)
        except requests.exceptions.ConnectionError:
            pytest.fail(f"API not accessible at {self.api_url}")

        assert r.status_code == 200, f"Expected HTTP 200, got {r.status_code}: {r.text[:300]}"
        self._log(f"+ Response status: {r.status_code}")

        data = r.json()
        assert isinstance(data, dict), "Response must be a JSON object"
        assert (
            data.get("status") == "simulated"
        ), f"Expected status 'simulated', got '{data.get('status')}'"
        self._log("+ Default mode works correctly (status=simulated)")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-31-03 COMPLETED — DEFAULT MODE VALIDATED ===")
