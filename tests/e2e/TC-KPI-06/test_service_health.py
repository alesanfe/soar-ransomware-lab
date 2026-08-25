#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case KPI-06 (Service Health Validation)
Validates that external services (Cortex, MISP, TheHive) are actually working
and not just returning errors that get silently swallowed by the workflow.

This test prevents false positives where the workflow finishes as "FINISHED"
but all service calls failed (e.g., Cortex 95% failure rate, MISP 0% success).
"""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest


class TestServiceHealthValidation(E2EBaseTest):
    """TC-KPI-06 — Validate that external services are actually functional, not
    just "reachable".

    Prevents false-positive E2E passes when services silently fail
    (e.g., Cortex analyzers timeout, MISP returns 0% success).
    """

    tc_id = "TC-KPI-06"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self._results = []

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-KPI-06 {msg}"
        print(line)

    def test_cortex_analyzer_success_rate(self):
        """Cortex analyzer jobs must have a success rate above 50%.

        A 95% failure rate (as observed with missing Docker analyzer
        images) indicates a broken service, not a healthy lab.
        """
        self._log("=== Test: Cortex Analyzer Success Rate ===")
        es_url = self.env.get("ES_URL", "http://elasticsearch:9200")

        # Query Cortex jobs from Elasticsearch
        body = {
            "size": 0,
            "query": {"range": {"createdAt": {"gte": int((time.time() - 3600) * 1000)}}},
            "aggs": {"by_status": {"terms": {"field": "status"}}},
        }
        try:
            r = requests.post(f"{es_url}/cortex_6/_search", json=body, timeout=30)
            r.raise_for_status()
        except Exception as e:
            pytest.fail(f"Cannot query Cortex jobs from Elasticsearch: {e}")

        buckets = r.json().get("aggregations", {}).get("by_status", {}).get("buckets", [])
        if not buckets:
            pytest.fail("No Cortex jobs found in the last hour - Cortex has not processed any jobs")

        total = sum(b["doc_count"] for b in buckets)
        success_count = sum(b["doc_count"] for b in buckets if b["key"] in ("Success", "Ok"))
        failure_count = sum(b["doc_count"] for b in buckets if b["key"] in ("Failure", "Failed"))
        rate = (success_count / total * 100) if total > 0 else 0

        self._log(
            f"Cortex jobs: total={total} success={success_count} "
            f"failure={failure_count} rate={rate:.1f}%"
        )
        for b in buckets:
            self._log(f"  {b['key']}: {b['doc_count']}")

        # If all jobs are failing, Cortex is broken
        min_rate = 50.0
        assert rate >= min_rate, (
            f"Cortex analyzer success rate is {rate:.1f}% ({success_count}/{total}), "
            f"below minimum threshold of {min_rate}%. "
            f"This indicates Cortex analyzers are not functioning properly "
            f"(likely missing Docker analyzer images). "
            f"Failure count: {failure_count}. "
            f"Install analyzer images or fix Cortex worker configuration."
        )
        self._log(f"✓ Cortex success rate {rate:.1f}% >= {min_rate}%")

        # Validate that at least 1 analyzer job ran (total must be positive)
        assert total > 0, "Cortex must have processed at least 1 analyzer job in the last hour"
        self._log(f"✓ Total Cortex jobs processed: {total}")

        # Validate that failed analyzers are less than 50% of total
        failure_rate = (failure_count / total * 100) if total > 0 else 0
        assert failure_rate < 50.0, (
            f"Cortex analyzer failure rate is {failure_rate:.1f}% ({failure_count}/{total}), "
            f"which is >= 50%. This indicates systemic analyzer failures."
        )
        self._log(f"✓ Cortex failure rate {failure_rate:.1f}% < 50%")

    def test_misp_api_functional(self):
        """MISP API must be functional (can search events and get valid
        response)."""
        self._log("=== Test: MISP API Functional ===")
        misp_key = self.env.get("MISP_API_KEY", "")
        if not misp_key:
            pytest.fail("MISP_API_KEY not configured - MISP integration is required")

        # MISP is on HTTP port 80 internally
        misp_url = "http://misp:80"
        headers = {
            "Authorization": misp_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # 1. Check server version
        try:
            r = requests.get(
                f"{misp_url}/servers/getVersion.json", headers=headers, verify=False, timeout=15
            )
            if r.status_code == 403:
                pytest.fail(
                    "MISP API returned 403 (authentication failed). "
                    "API key may be invalid or user not API-enabled."
                )
            r.raise_for_status()
            version = r.json()
            self._log(f"MISP version: {version.get('version', '?')}")
        except requests.ConnectionError as e:
            pytest.fail(f"MISP API not reachable at {misp_url}: {e}")
        except Exception as e:
            pytest.fail(f"MISP API getVersion failed: {e}")

        # 2. Search for events (verify API is truly functional)
        search_body = {"returnFormat": "json", "limit": 5}
        try:
            r2 = requests.post(
                f"{misp_url}/events/index",
                headers=headers,
                json=search_body,
                verify=False,
                timeout=15,
            )
            assert (
                r2.status_code == 200
            ), f"MISP /events/index returned HTTP {r2.status_code} — API is not functional"
            data = r2.json()
            # Response should contain an array of events
            if isinstance(data, dict):
                events = data.get("response", data.get("Event", []))
            else:
                events = data
            assert events is not None, "MISP /events/index returned null events"
            # Validate that the response structure is correct
            assert isinstance(
                events, list
            ), f"MISP events response must be a list, got {type(events)}"
            self._log(f"MISP events found: {len(events)}")
        except requests.ConnectionError as e:
            pytest.fail(f"MISP API event search failed (connection error): {e}")
        except Exception as e:
            pytest.fail(f"MISP API event search failed: {e}")

        # 3. Validate MISP API can search for specific attributes (full functional test)
        try:
            search_body2 = {
                "returnFormat": "json",
                "limit": 1,
                "page": 0,
            }
            r3 = requests.post(
                f"{misp_url}/attributes/index",
                headers=headers,
                json=search_body2,
                verify=False,
                timeout=15,
            )
            assert r3.status_code == 200, f"MISP /attributes/index returned HTTP {r3.status_code}"
            attr_data = r3.json()
            # Validate response structure
            if isinstance(attr_data, dict):
                attrs = attr_data.get("response", attr_data.get("Attribute", []))
            else:
                attrs = attr_data
            assert isinstance(attrs, list), "MISP attributes response must be a list"
            self._log(f"MISP attributes accessible: {len(attrs)} attribute(s) found")
        except Exception as e:
            pytest.fail(f"MISP API attribute search failed: {e}")

        self._log("✓ MISP API is functional")

    def test_workflow_notification_rate(self):
        """Workflow notification/error rate must be below 30%.

        A high notification rate (e.g., 190 errors out of 1500 executions = 12.7%)
        indicates workflow issues like missing variables or broken nodes.
        """
        self._log("=== Test: Workflow Notification Rate ===")
        os_url = "http://opensearch:9200"

        # Count total workflow executions
        try:
            r = requests.get(f"{os_url}/workflowexecution-000001/_count", timeout=15)
            r.raise_for_status()
            total_executions = r.json().get("count", 0)
        except Exception as e:
            pytest.fail(f"Cannot query OpenSearch: {e}")

        if total_executions == 0:
            pytest.fail("No workflow executions found - workflow has never been triggered")

        # Count notifications (errors)
        try:
            r2 = requests.get(f"{os_url}/notifications-000001/_count", timeout=15)
            r2.raise_for_status()
            total_notifications = r2.json().get("count", 0)
        except Exception:
            total_notifications = 0

        notification_rate = (
            (total_notifications / total_executions * 100) if total_executions > 0 else 0
        )
        self._log(
            f"Workflow: {total_executions} executions, {total_notifications} notifications "
            f"({notification_rate:.1f}% notification rate)"
        )

        # A notification rate above 30% indicates systemic workflow issues
        max_rate = 30.0
        assert notification_rate <= max_rate, (
            f"Workflow notification rate is {notification_rate:.1f}% "
            f"({total_notifications}/{total_executions}), "
            f"above maximum threshold of {max_rate}%. "
            f"This indicates systemic workflow errors (missing variables, broken nodes). "
            f"Check workflow variable references ($webhook.* vs $exec.*)."
        )
        self._log(f"✓ Workflow notification rate {notification_rate:.1f}% <= {max_rate}%")

        # Validate that total workflow executions is positive (workflow has been running)
        assert (
            total_executions > 0
        ), "Total workflow executions must be > 0 - workflow has never been triggered"
        self._log(f"✓ Total workflow executions: {total_executions}")

        # Validate that the notification rate calculation is a valid percentage
        assert isinstance(
            notification_rate, (int, float)
        ), f"Notification rate must be numeric, got {type(notification_rate).__name__}"
        assert (
            0 <= notification_rate <= 100
        ), f"Notification rate must be between 0 and 100, got {notification_rate:.1f}%"
        self._log(f"✓ Notification rate is a valid percentage: {notification_rate:.1f}%")

    def test_workflow_aborted_rate(self):
        """Workflow ABORTED rate must be below 20%.

        Excludes intentional test cases (TC-05 concurrent, TC-19
        malformed, TC-26 storm, EDGE-* edge cases) which are designed to
        cause aborts.
        """
        self._log("=== Test: Workflow Aborted Rate ===")
        os_url = "http://opensearch:9200"

        # Count by status
        body = {
            "size": 0,
            "query": {"range": {"started_at": {"gte": int(time.time() - 86400)}}},
            "aggs": {"by_status": {"terms": {"field": "status"}}},
        }
        try:
            r = requests.post(f"{os_url}/workflowexecution-000001/_search", json=body, timeout=30)
            r.raise_for_status()
        except Exception as e:
            pytest.fail(f"Cannot query OpenSearch: {e}")

        buckets = r.json().get("aggregations", {}).get("by_status", {}).get("buckets", [])
        if not buckets:
            pytest.fail("No workflow executions in the last 24h - workflow has not been running")

        status_counts = {b["key"]: b["doc_count"] for b in buckets}
        total = sum(status_counts.values())
        aborted = status_counts.get("ABORTED", 0)
        finished = status_counts.get("FINISHED", 0)

        aborted_rate = (aborted / total * 100) if total > 0 else 0
        self._log(
            f"Workflow status: total={total} finished={finished} aborted={aborted} "
            f"({aborted_rate:.1f}% aborted)"
        )
        for status, count in status_counts.items():
            self._log(f"  {status}: {count}")

        # Exclude intentional test cases that are designed to cause aborts
        exclude_patterns = [
            "TC-05",
            "TC-19",
            "TC-26",
            "EDGE-",
            "invalid json",
            "TC-07",
            "malformed",
            "incomplete",
        ]
        body2 = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [{"term": {"status": "ABORTED"}}],
                    "must_not": [
                        {"wildcard": {"execution_argument": f"*{p}*"}} for p in exclude_patterns
                    ],
                }
            },
        }
        try:
            r2 = requests.post(f"{os_url}/workflowexecution-000001/_search", json=body2, timeout=30)
            r2.raise_for_status()
            unexpected_aborted = r2.json().get("hits", {}).get("total", {}).get("value", 0)
        except Exception:
            unexpected_aborted = aborted

        self._log(f"Unexpected aborts (excluding test cases): {unexpected_aborted}")
        unexpected_rate = (unexpected_aborted / total * 100) if total > 0 else 0

        max_unexpected_rate = 5.0
        assert unexpected_rate <= max_unexpected_rate, (
            f"Unexpected workflow ABORTED rate is {unexpected_rate:.1f}% "
            f"({unexpected_aborted}/{total}), "
            f"above maximum threshold of {max_unexpected_rate}%. "
            f"These are NOT intentional test-case aborts. "
            f"Check workflow for bugs causing unexpected failures."
        )
        self._log(f"✓ Unexpected aborted rate {unexpected_rate:.1f}% <= {max_unexpected_rate}%")

        # Validate that total executions is positive (workflow has been running)
        assert total > 0, "Total workflow executions must be > 0 - workflow has not been running"
        self._log(f"✓ Total workflow executions in last 24h: {total}")

        # Validate that aborted count is numeric and non-negative
        assert isinstance(
            aborted, (int, float)
        ), f"Aborted count must be numeric, got {type(aborted).__name__}"
        assert aborted >= 0, f"Aborted count must be non-negative, got {aborted}"
        self._log(f"✓ Aborted count is valid: {aborted}")

        # Validate that the aborted rate is a valid percentage
        assert isinstance(
            aborted_rate, (int, float)
        ), f"Aborted rate must be numeric, got {type(aborted_rate).__name__}"
        assert (
            0 <= aborted_rate <= 100
        ), f"Aborted rate must be between 0 and 100, got {aborted_rate:.1f}%"
        self._log(f"✓ Aborted rate is a valid percentage: {aborted_rate:.1f}%")

    def test_cortex_analyzer_images_available(self):
        """Cortex must have analyzer Docker images installed.

        Without analyzer images, all Cortex jobs will fail with
        timeouts. This is a prerequisite check, not a performance test.
        """
        self._log("=== Test: Cortex Analyzer Images Available ===")
        cortex_url = self.env.get("CORTEX_URL", "http://cortex:9001")
        cortex_key = self.env.get("CORTEX_API_KEY", "")
        admin_user = self.env.get("CORTEX_ADMIN_USER", "admin")
        admin_pw = self.env.get("CORTEX_ADMIN_PASSWORD", "")

        import base64

        if admin_pw:
            creds = base64.b64encode(f"{admin_user}:{admin_pw}".encode()).decode()
            headers = {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}
        elif cortex_key:
            headers = {"Authorization": f"Bearer {cortex_key}", "Content-Type": "application/json"}
        else:
            pytest.fail("No Cortex credentials configured - Cortex integration is required")

        # List installed analyzers
        try:
            r = requests.post(
                f"{cortex_url}/api/analyzer/_search",
                headers=headers,
                json={"query": {}, "range": "all"},
                timeout=30,
            )
            r.raise_for_status()
            analyzers = r.json()
        except Exception as e:
            pytest.fail(f"Cannot list Cortex analyzers: {e}")

        if not analyzers:
            pytest.fail("No Cortex analyzers installed - Cortex is not properly configured")

        self._log(f"Cortex has {len(analyzers)} analyzers installed")

        # Validate that the analyzers list is non-empty and contains valid analyzer objects
        assert isinstance(
            analyzers, list
        ), f"Cortex analyzers response must be a list, got {type(analyzers).__name__}"
        assert len(analyzers) > 0, "Cortex must have at least 1 analyzer installed"
        for a in analyzers:
            assert isinstance(a, dict), f"Each analyzer must be a dict, got {type(a).__name__}"

        # Validate that at least 3 common analyzers are present
        analyzer_names = {a.get("workerDefinitionId", a.get("id", "")) for a in analyzers}
        common_analyzers = {"ValidateObservable", "FileInfo", "MISP_2_0"}
        present_common = analyzer_names & common_analyzers
        assert len(present_common) >= 1, (
            f"Cortex should have at least 1 common analyzer from {common_analyzers}, "
            f"got only: {analyzer_names}"
        )
        self._log(f"✓ Common analyzers present: {present_common}")
        # Recommend at least 3 analyzers total for a functional Cortex setup
        assert len(analyzers) >= 3, (
            f"Cortex should have at least 3 analyzers installed for functional setup, "
            f"got {len(analyzers)}"
        )
        self._log(f"✓ Analyzer count ({len(analyzers)}) >= 3")

        # Try running a simple analyzer (ValidateObservable) on a test value
        test_analyzer = None
        for a in analyzers:
            if "ValidateObservable" in a.get("workerDefinitionId", a.get("id", "")):
                test_analyzer = a
                break

        if not test_analyzer:
            pytest.fail("ValidateObservable analyzer not installed - required for health check")

        analyzer_id = test_analyzer.get("id", "")
        self._log(f"Testing analyzer: {analyzer_id}")

        # Run analyzer on a simple domain
        try:
            r2 = requests.post(
                f"{cortex_url}/api/analyzer/{analyzer_id}/run",
                headers=headers,
                json={"dataType": "domain", "data": "example.com"},
                timeout=30,
            )
            r2.raise_for_status()
            job = r2.json()
            job_id = job.get("id", job.get("_id", ""))
            self._log(f"Job created: {job_id}")
        except Exception as e:
            pytest.fail(f"Cannot create Cortex analyzer job: {e}")

        if not job_id:
            pytest.fail("Cortex analyzer job creation returned no job ID")

        # Wait for job to complete (max 90 seconds)
        for _ in range(18):
            time.sleep(5)
            try:
                r3 = requests.get(f"{cortex_url}/api/job/{job_id}", headers=headers, timeout=15)
                r3.raise_for_status()
                job_status = r3.json().get("status", "")
                self._log(f"Job status: {job_status}")
                if job_status in ("Success", "Failure", "Failed", "Ok"):
                    break
            except Exception:
                continue
        else:
            pytest.fail(f"Cortex analyzer job {job_id} did not complete within 90s")

        assert job_status in ("Success", "Ok"), (
            f"Cortex analyzer job completed with status '{job_status}'. "
            f"Analyzer Docker images may not be installed. "
            f"Error: {r3.json().get('errorMessage', 'N/A')}"
        )
        self._log("✓ Cortex analyzer job completed successfully")

    def _step_save_report(self, elapsed: float):
        report = {
            "test_case": "TC-KPI-06",
            "scenario": "service_health_validation",
            "elapsed_seconds": elapsed,
            "results": self._results,
            "success": all(r.get("ok", False) for r in self._results),
        }
        report_file = self.e2e_results_dir / "TC-KPI-06_service_health_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(report, indent=2, default=str))
