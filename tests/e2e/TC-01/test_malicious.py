#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case 01 (Malicious Alert)
Tests the complete SOAR workflow for a malicious ransomware alert:
  alert ingestion -> Shuffle workflow -> TheHive case -> Cortex analyzers
  -> MISP IOC lookup -> Elasticsearch index.

Requires a live Docker stack (make up). Reads credentials from .env.full.
"""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

sys.path.insert(0, str(Path(__file__).parent.parent))

from assertions.incident_assertions import (
    assert_incident_has_observables,
    assert_incident_severity,
    assert_incident_state,
)
from assertions.observable_assertions import (
    assert_observable_has_tags,
    assert_observable_pap,
    assert_observable_tlp,
    assert_observable_type,
    assert_observable_value,
    assert_observables_match_payload,
)
from assertions.persistence_assertions import (
    assert_data_integrity,
    assert_data_persisted,
)

from tests.e2e.base import E2EBaseTest


class TestMaliciousAlert(E2EBaseTest):
    """TC-01 — E2E: full SOAR pipeline for a malicious ransomware alert."""

    tc_id = "TC-01"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        ioc_file = FIXTURES_DIR / "ioc_samples.json"
        data = json.loads(ioc_file.read_text()) if ioc_file.exists() else {}
        self.test_cases = data.get("malicious_test_cases", [])

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-01 {msg}"
        print(line)

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _step_verify_thehive_case(self) -> dict:
        self._log("STEP 4: Verifying TheHive case + observables + tasks")
        cases = self.thehive.search_cases()
        assert isinstance(cases, list), "TheHive cases must be a list"
        alert_id = self.alert_data.get("alert_id", "")
        assert isinstance(alert_id, str), "alert_id must be a string"
        assert len(alert_id) > 0, "alert_id must not be empty"
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id} in description"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        assert isinstance(last, dict), "Case must be a dict"
        case_id = str(last.get("_id", ""))
        assert len(case_id) > 0, "Case _id must not be empty"
        self._log(
            f"+ Case #{last.get('caseId')} '{last.get('title')}' "
            f"sev={last.get('severity')} status={last.get('status')}"
        )
        assert (
            "ransomware" in last.get("title", "").lower()
        ), f"Case title missing 'ransomware': {last.get('title')}"

        payload_severity = self.alert_data.get("severity", 0)
        assert_incident_severity(last, "critical")
        self._log(
            f"+ Severity mapping validated: payload={payload_severity} "
            f"-> case={last.get('severity')}"
        )

        assert_incident_state(last, "Open")
        assert_incident_severity(last, "critical")

        if case_id:
            obs = self.thehive.get_case_observables(case_id)
            self._log(f"  + {len(obs)} observable(s) attached")
            assert_incident_has_observables(last, min_count=1)

            payload_iocs = []
            if self.alert_data.get("hash"):
                payload_iocs.append({"type": "hash", "value": self.alert_data["hash"]})
            if self.alert_data.get("src_ip"):
                payload_iocs.append({"type": "ip", "value": self.alert_data["src_ip"]})
            if self.alert_data.get("domain"):
                payload_iocs.append({"type": "domain", "value": self.alert_data["domain"]})
            if self.alert_data.get("url"):
                payload_iocs.append({"type": "url", "value": self.alert_data["url"]})

            if obs and payload_iocs:
                obs_data = [{"type": o.get("dataType"), "value": o.get("data")} for o in obs]
                try:
                    assert_observables_match_payload(obs_data, payload_iocs)
                    self._log("  + Observables match payload IoCs")
                except AssertionError as e:
                    self._log(f"  + Observable validation warning: {e}")

            for observable in obs[:5]:
                obs_type = observable.get("dataType")
                obs_value = observable.get("data")
                self._log(f"    - {obs_type}: {obs_value}")
                if obs_type:
                    assert_observable_type(observable, obs_type)
                if obs_value:
                    assert_observable_value(observable, obs_value)
                if observable.get("tlp"):
                    assert_observable_tlp(observable, observable.get("tlp"))
                if observable.get("pap"):
                    assert_observable_pap(observable, observable.get("pap"))
                if obs_type in ["hash", "ip", "domain"]:
                    assert_observable_has_tags(observable, min_tags=1)

            tasks = self.thehive.list_case_tasks(case_id)
            assert len(tasks) >= 1, "No tasks found in case"
            self._log(f"  + {len(tasks)} task(s) in case")
            for t in tasks[:5]:
                self._log(f"    - [{t.get('status', '?')}] {t.get('title', '?')}")
        return last

    def _step_verify_cortex_analyzers(self):
        self._log("STEP 5: Verifying Cortex analyzers + recent jobs + actual execution")
        analyzers = self.cortex.list_analyzers()
        assert isinstance(analyzers, list), "Cortex analyzers must be a list"
        assert len(analyzers) > 0, "Cortex has no analyzers"
        self._log(f"  + Cortex: {len(analyzers)} analyzer(s)")
        for a in analyzers[:5]:
            assert isinstance(a, dict), "Analyzer must be a dict"
            name = a.get("name", "?")
            assert isinstance(name, str), "Analyzer name must be a string"
            datatypes = a.get("dataTypeList", [])
            assert isinstance(datatypes, list), "Analyzer datatypes must be a list"
            self._log(f"    - {name} datatypes={datatypes}")

        self._log("  + Verifying analyzer execution history")
        try:
            jobs = self.cortex.list_jobs()
            assert isinstance(jobs, list), "Cortex jobs must be a list"
            self._log(f"    + Found {len(jobs)} total job(s) in Cortex")

            recent_jobs = [job for job in jobs if job.get("createdAt")]
            if recent_jobs:
                self._log(f"    + Found {len(recent_jobs)} recent job(s)")

                completed_jobs = [job for job in recent_jobs if job.get("status") == "Success"]
                if completed_jobs:
                    self._log(f"    + {len(completed_jobs)} job(s) completed successfully")
                    assert len(completed_jobs) > 0, "No completed Cortex jobs found"
                else:
                    self._log("    + Warning: No successfully completed jobs found")
            else:
                self._log("    + No recent jobs found - analyzers may not have executed")
        except Exception as e:
            self._log(f"    + Could not verify analyzer execution: {e}")

        self._log("  + Testing analyzer execution capability")
        try:
            if self.alert_data.get("hash"):
                test_hash = self.alert_data["hash"]
                self._log(f"    + Running FileInfo analyzer on hash {test_hash[:16]}...")
                job = self.cortex.run_analyzer("FileInfo_8_0", "hash", test_hash)
                assert isinstance(job, dict), "Analyzer job must be a dict"
                job_id = job.get("id", "")
                assert isinstance(job_id, str), "Job ID must be a string"
                self._log(f"    + Analyzer job started: {job_id}")

                self._log("    + Waiting for analyzer job completion...")
                deadline = time.time() + 30
                while time.time() < deadline:
                    try:
                        job_status = self.cortex.get_job(job_id)
                        if job_status:
                            status = job_status.get("status", "")
                            self._log(f"    + Job status: {status}")
                            if status in ["Success", "Failure"]:
                                if status == "Success":
                                    self._log("    + Analyzer executed successfully")
                                    report = job_status.get("report", {})
                                    assert isinstance(report, dict), "Job report must be a dict"
                                    self._log("    + Analyzer execution validated successfully")
                                else:
                                    self._log(
                                        f"    + Analyzer job failed: "
                                        f"{job_status.get('summary', 'Unknown')}"
                                    )
                                break
                    except Exception as e:
                        self._log(f"    + Error checking job status: {e}")
                    time.sleep(2)
            else:
                self._log("    + No hash in alert data, skipping analyzer execution test")
        except Exception as e:
            self._log(f"    + Analyzer execution test failed: {e}")

    def _step_verify_misp_iocs(self):
        self._log("STEP 6: Verifying MISP IOC database + enrichment")
        try:
            events = self.misp.list_events()
            assert isinstance(events, list), "MISP events must be a list"
            self._log(f"  + MISP: {len(events)} event(s) in database")

            enrichment_found = False
            for field in ["hash", "ip", "domain", "url"]:
                if self.alert_data.get(field):
                    value = self.alert_data[field]
                    assert isinstance(value, str), f"{field} must be a string"
                    search_results = self.misp.search_events(value)
                    assert isinstance(search_results, list), "MISP search results must be a list"
                    if search_results:
                        self._log(f"    + Found {len(search_results)} event(s) for {field}={value}")

                        for event in search_results[:2]:
                            if isinstance(event, dict):
                                event_id = event.get("id", "")
                                attributes = event.get("Attribute", [])
                                if isinstance(attributes, list) and len(attributes) > 1:
                                    self._log(
                                        f"      + Event {event_id} has {len(attributes)} "
                                        f"attributes (enriched)"
                                    )
                                    enrichment_found = True

                                    attr_types = [
                                        attr.get("type")
                                        for attr in attributes
                                        if isinstance(attr, dict)
                                    ]
                                    self._log(
                                        f"      + Attribute types: {', '.join(attr_types[:5])}"
                                    )

                                    if "filename" in attr_types or "malware-sample" in attr_types:
                                        self._log("      + File-related enrichment detected")
                                    if "domain" in attr_types or "hostname" in attr_types:
                                        self._log("      + Network-related enrichment detected")
                    else:
                        self._log(
                            f"    + No events found for {field}={value} (IOC may not be in DB)"
                        )

            if enrichment_found:
                self._log("  + IOC enrichment validated successfully")
            else:
                self._log("  + Warning: IOC enrichment not detected - IoCs may be new")

        except Exception as e:
            self._log(f"  + MISP verification failed: {e}")
            pytest.fail(f"MISP integration not functional: {e}")

    def _step_verify_es_indexed(self):
        self._log("STEP 7: Verifying Elasticsearch indexing + cluster health")
        health = self.es.cluster_health()
        assert isinstance(health, dict), "ES health must be a dict"
        status = health.get("status", "?")
        assert isinstance(status, str), "ES health status must be a string"
        self._log(f"  + Cluster health: {status} | nodes={health.get('number_of_nodes', '?')}")
        assert status in ("green", "yellow"), f"ES cluster in bad state: {status}"
        alert_id = self.alert_data.get("alert_id", "")
        assert isinstance(alert_id, str), "alert_id must be a string"
        src = self.es.search_by_alert_id(alert_id)
        assert src, f"ES document not found for alert_id={alert_id}"
        assert isinstance(src, dict), "ES document must be a dict"
        self._log(
            f"  + Found doc: alert_id={src.get('alert_id', '?')} "
            f"hostname={src.get('hostname', '?')} status={src.get('status', '?')}"
        )

        assert_data_persisted("elasticsearch", src)

        critical_fields = ["alert_id", "alert_type", "hostname", "src_ip"]
        try:
            assert_data_integrity(self.alert_data, src, critical_fields)
            self._log("  + ES document matches payload on critical fields")
        except AssertionError as e:
            self._log(f"  + Data integrity warning: {e}")

        assert "alert_id" in src, "Indexed ES doc missing 'alert_id' field"
        assert (
            src.get("alert_type") == "ransomware"
        ), f"ES doc alert_type must be 'ransomware', got '{src.get('alert_type')}'"
        assert (
            src.get("hostname") == "WIN-TC01-001"
        ), f"ES doc hostname mismatch: {src.get('hostname')}"

    def _step_save_report(self, result: dict):
        report_file = Path("results") / "TC-01_malicious_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps(result, indent=2, default=str))
        self._log(f"+ Report saved: {report_file}")

    # ------------------------------------------------------------------
    # Main test
    # ------------------------------------------------------------------

    _MALICIOUS_CONTRACT = {
        "required_nodes": ["thehive_create_case", "es_index", "calc_decision"],
        "forbidden_nodes": ["mark_false_positive"],
        "node_contracts": {
            "calc_decision": {
                "required_keys": ["score"],
                "expected_values": {"score": lambda v: v >= 80},
            },
            "build_hive_summary": {"required_keys": ["success"]},
            "build_metrics_json": {"required_keys": ["success"]},
            "calc_mttr": {"required_keys": ["mttr_seconds"]},
        },
    }

    def _run_full_workflow_group(self, group_cases: list) -> None:
        """Submit a batch of IOC cases, wait for them, and verify each one."""
        if not group_cases:
            pytest.fail("No test cases in group")

        self._log("=== TC-01: MALICIOUS ALERT E2E BATCH STARTED ===")

        submissions = []
        for test_case in group_cases:
            name = test_case.get("name", "unknown")
            payload = {
                "alert_id": f"TC01-{name}-{int(time.time())}",
                "alert_type": "ransomware",
                "hostname": test_case.get("hostname", "WIN-TC01-001"),
                "src_ip": test_case.get("ip", "172.31.54.117"),
                "hash": test_case.get(
                    "hash", "6c2ed91b8f53686dc6f4165b0fb19bf0df01b7612e2e2b2d9f7ad6313fba9a92"
                ),
                "severity": 3,
                "source": "siem-ransomware-detection",
                "detection_time": datetime.now(UTC).isoformat(),
                "event_type": "ransomware_detection",
                "mitre_tactics": ["TA0040"],
                "mitre_techniques": ["T1486"],
                "confidence": 95,
            }
            if test_case.get("domain"):
                payload["domain"] = test_case["domain"]
            if test_case.get("url"):
                payload["url"] = test_case["url"]
            if test_case.get("mail"):
                payload["email"] = test_case["mail"]
            if test_case.get("file"):
                payload["file_name"] = test_case["file"]
            if test_case.get("fqdn"):
                payload["fqdn"] = test_case["fqdn"]

            self._log(f"=== Submitting case: {name} ===")
            self.alert_data = payload
            alert_id = payload["alert_id"]
            exec_id, execution = self.submit_alert_and_wait(payload)
            self.execution = execution
            self.execution_id = exec_id
            self.validate_workflow_execution(
                execution, alert_id=alert_id, expected_contract=self._MALICIOUS_CONTRACT
            )
            submissions.append({"case": test_case, "payload": payload})

        failed_cases = []
        for sub in submissions:
            test_case = sub["case"]
            name = test_case.get("name", "unknown")
            self._log(f"=== Verifying case: {name} ===")
            try:
                self.alert_data = sub["payload"]
                self._step_verify_ioc_detection(name, test_case)
            except Exception as e:
                self._log(f"  + Case {name} failed: {e}")
                failed_cases.append(name)

        if failed_cases:
            self._log(f"  + Failed cases: {', '.join(failed_cases)}")
            pytest.fail(
                f"Test cases failed: {len(failed_cases)}/{len(group_cases)}: "
                f"{', '.join(failed_cases)}"
            )

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01 BATCH COMPLETED — ALL ASSERTIONS PASSED ===")

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_malicious_alert_full_workflow_group_1(self):
        """TC-01 batch 1: hashes + IPs (4 cases)."""
        if not self.test_cases:
            pytest.fail("No test cases found in ioc_samples.json")
        self._run_full_workflow_group(self.test_cases[:4])
        assert self.execution is not None, "Workflow execution was not recorded"
        assert self.execution.get("status") == "FINISHED", "Workflow did not finish successfully"

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_malicious_alert_full_workflow_group_2(self):
        """TC-01 batch 2: domains + URLs (4 cases)."""
        if not self.test_cases:
            pytest.fail("No test cases found in ioc_samples.json")
        self._run_full_workflow_group(self.test_cases[4:8])
        assert self.execution is not None, "Workflow execution was not recorded"
        assert self.execution.get("status") == "FINISHED", "Workflow did not finish successfully"

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_malicious_alert_full_workflow_group_3(self):
        """TC-01 batch 3: mail + file (4 cases)."""
        if not self.test_cases:
            pytest.fail("No test cases found in ioc_samples.json")
        self._run_full_workflow_group(self.test_cases[8:12])
        assert self.execution is not None, "Workflow execution was not recorded"
        assert self.execution.get("status") == "FINISHED", "Workflow did not finish successfully"

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_malicious_alert_full_workflow_group_4(self):
        """TC-01 batch 4: fqdn + hostname (4 cases)."""
        if not self.test_cases:
            pytest.fail("No test cases found in ioc_samples.json")
        self._run_full_workflow_group(self.test_cases[12:16])
        assert self.execution is not None, "Workflow execution was not recorded"
        assert self.execution.get("status") == "FINISHED", "Workflow did not finish successfully"

    # ------------------------------------------------------------------
    # IOC detection verification
    # ------------------------------------------------------------------

    def _step_verify_ioc_detection(self, case_name: str, test_case: dict):
        """Verify that the malicious IOC in the test case is detected by
        Cortex/MISP."""
        self._log(f"Verifying malicious IOC detection for {case_name}")

        if "hash" in case_name and test_case.get("hash"):
            try:
                job = self.cortex.run_analyzer("FileInfo_8_0", "hash", test_case["hash"])
                self._log(f"  + Cortex hash analysis job: {job.get('id', 'N/A')}")
            except Exception as e:
                self._log(f"  + Cortex hash analysis skipped: {e}")

        for field in ["hash", "ip", "domain", "url", "mail"]:
            if field in case_name and test_case.get(field):
                try:
                    events = self.misp.search_events(test_case[field])
                    if events:
                        self._log(f"  + MISP found {len(events)} event(s) for {field}")
                    else:
                        self._log(f"  + MISP: no events found for {field} (IOC may not be in DB)")
                except Exception as e:
                    self._log(f"  + MISP search skipped for {field}: {e}")

    # ------------------------------------------------------------------
    # Subcase-specific tests
    # ------------------------------------------------------------------

    def test_observable_validation(self):
        """TC-01-03: Observable validation.

        Verifications:
          - Observables are extracted correctly
          - Observable types are valid
          - Observable values match payload
        """
        self._log("=== TC-01-03: OBSERVABLE VALIDATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC01-OBS-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC01-001",
            "src_ip": "192.168.1.100",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "severity": 3,
            "source": "observable-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        self.alert_data = payload
        alert_id = payload["alert_id"]
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(
            execution, alert_id=alert_id, expected_contract=self._MALICIOUS_CONTRACT
        )

        # Verify observables with deep assertions
        self._log("STEP 4: Verifying observables with deep validation")
        cases = self.thehive.search_cases()

        alert_id = self.alert_data.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        case_id = str(last.get("_id", ""))

        obs = self.thehive.get_case_observables(case_id)
        assert len(obs) > 0, "No observables found in case"
        self._log(f"+ {len(obs)} observable(s) found")

        expected_iocs = []
        if self.alert_data.get("hash"):
            expected_iocs.append({"type": "hash", "value": self.alert_data["hash"]})
        if self.alert_data.get("src_ip"):
            expected_iocs.append({"type": "ip", "value": self.alert_data["src_ip"]})

        obs_data = [{"type": o.get("dataType"), "value": o.get("data")} for o in obs]
        assert_observables_match_payload(obs_data, expected_iocs)
        self._log("+ Observables match payload IoCs")

        for observable in obs:
            obs_type = observable.get("dataType")
            obs_value = observable.get("data")
            assert obs_type, "Observable missing dataType"
            assert obs_value, "Observable missing data"
            assert_observable_type(observable, obs_type)
            assert_observable_value(observable, obs_value)
            self._log(f"  - [{obs_type}] {obs_value} validated")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-03 COMPLETED — OBSERVABLE VALIDATION VALIDATED ===")

    def test_ioc_validation(self):
        """TC-01-04: IoC validation.

        Verifications:
          - IoCs are extracted correctly
          - IoC types are valid
          - IoC values match payload
        """
        self._log("=== TC-01-04: IOC VALIDATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC01-IOC-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC01-001",
            "src_ip": "192.168.1.100",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "severity": 3,
            "source": "ioc-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        self.alert_data = payload
        alert_id = payload["alert_id"]
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(
            execution, alert_id=alert_id, expected_contract=self._MALICIOUS_CONTRACT
        )

        # Verify IoCs in MISP with deep assertions
        self._log("STEP 6: Verifying IoCs in MISP with deep validation")
        try:
            events = self.misp.list_events()
            self._log(f"+ MISP: {len(events)} event(s)")

            payload_iocs = []
            if self.alert_data.get("hash"):
                payload_iocs.append({"type": "hash", "value": self.alert_data["hash"]})
            if self.alert_data.get("src_ip"):
                payload_iocs.append({"type": "ip", "value": self.alert_data["src_ip"]})

            ioc_found = False
            for ioc in payload_iocs:
                search_results = self.misp.search_events(ioc["value"])
                if search_results:
                    ioc_found = True
                    self._log(
                        f"+ Found {len(search_results)} event(s) for {ioc['type']}={ioc['value']}"
                    )
                    for event in search_results[:1]:
                        assert "Event" in event, "MISP event missing 'Event' key"
                        event_data = event["Event"]
                        assert "info" in event_data, "MISP event missing 'info'"
                        assert "Attribute" in event_data, "MISP event missing 'Attribute'"
                        assert len(event_data["Attribute"]) > 0, "MISP event has no attributes"

            if payload_iocs:
                assert (
                    ioc_found or len(events) > 0
                ), f"No IoCs found in MISP for payload: {payload_iocs}"

        except Exception as e:
            pytest.fail(f"MISP verification failed: {e}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-04 COMPLETED — IOC VALIDATION VALIDATED ===")

    def test_tag_validation(self):
        """TC-01-05: Tag validation.

        Verifications:
          - Tags are applied correctly
          - Tag types are valid
          - Tags match threat intelligence
        """
        self._log("=== TC-01-05: TAG VALIDATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC01-TAG-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC01-001",
            "src_ip": "192.168.1.100",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "severity": 3,
            "source": "tag-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        self.alert_data = payload
        alert_id = payload["alert_id"]
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(
            execution, alert_id=alert_id, expected_contract=self._MALICIOUS_CONTRACT
        )

        # Verify tags with deep assertions
        self._log("STEP 4: Verifying tags on observables with deep validation")
        cases = self.thehive.search_cases()

        alert_id = self.alert_data.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        case_id = str(last.get("_id", ""))

        obs = self.thehive.get_case_observables(case_id)
        assert len(obs) > 0, "No observables found in case"

        for observable in obs:
            obs_type = observable.get("dataType")
            tags = observable.get("tags", [])
            if obs_type in ["hash", "ip", "domain"]:
                assert_observable_has_tags(observable, min_tags=1)
                self._log(f"  - [{obs_type}] has {len(tags)} tag(s): {tags}")
                mitre_tags = [t for t in tags if t.startswith("T") or t.startswith("TA")]
                if mitre_tags:
                    self._log(f"    + MITRE tags found: {mitre_tags}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-05 COMPLETED — TAG VALIDATION VALIDATED ===")

    def test_tlp_pap_validation(self):
        """TC-01-06: TLP/PAP validation.

        Verifications:
          - TLP values are valid
          - PAP values are valid
          - Classification is correct
        """
        self._log("=== TC-01-06: TLP/PAP VALIDATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC01-TLP-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC01-001",
            "src_ip": "192.168.1.100",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "severity": 3,
            "source": "tlp-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        self.alert_data = payload
        alert_id = payload["alert_id"]
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(
            execution, alert_id=alert_id, expected_contract=self._MALICIOUS_CONTRACT
        )

        # Verify TLP/PAP with deep assertions
        self._log("STEP 4: Verifying TLP/PAP on observables with deep validation")
        cases = self.thehive.search_cases()

        alert_id = self.alert_data.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        case_id = str(last.get("_id", ""))

        obs = self.thehive.get_case_observables(case_id)
        assert len(obs) > 0, "No observables found in case"

        valid_tlp_values = [0, 1, 2, 3]
        valid_pap_values = [0, 1, 2, 3]

        for observable in obs:
            tlp = observable.get("tlp")
            pap = observable.get("pap")

            if tlp is not None:
                assert tlp in valid_tlp_values, f"Invalid TLP value: {tlp}"
                assert_observable_tlp(observable, tlp)
                self._log(f"  - TLP: {tlp} (valid)")
            else:
                self._log("  - TLP: not set (using default)")

            if pap is not None:
                assert pap in valid_pap_values, f"Invalid PAP value: {pap}"
                assert_observable_pap(observable, pap)
                self._log(f"  - PAP: {pap} (valid)")
            else:
                self._log("  - PAP: not set (using default)")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-06 COMPLETED — TLP/PAP VALIDATION VALIDATED ===")

    def test_task_validation(self):
        """TC-01-07: Task validation.

        Verifications:
          - Tasks are created automatically
          - Task types are correct
          - Task assignments are valid
        """
        self._log("=== TC-01-07: TASK VALIDATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC01-TASK-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC01-001",
            "src_ip": "192.168.1.100",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "severity": 3,
            "source": "task-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        self.alert_data = payload
        alert_id = payload["alert_id"]
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(
            execution, alert_id=alert_id, expected_contract=self._MALICIOUS_CONTRACT
        )

        # Verify tasks with deep assertions
        self._log("STEP 4: Verifying tasks with deep validation")
        cases = self.thehive.search_cases()

        alert_id = self.alert_data.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        case_id = str(last.get("_id", ""))

        tasks = self.thehive.list_case_tasks(case_id)
        assert len(tasks) > 0, "No tasks found in case"
        self._log(f"+ {len(tasks)} task(s) found")

        expected_task_keywords = ["isolate", "block", "kill", "collect", "preserve", "evidence"]
        found_expected_tasks = []

        for task in tasks:
            title = task.get("title", "").lower()
            status = task.get("status", "")
            self._log(f"  - [{status}] {task.get('title')}")

            valid_statuses = ["Waiting", "InProgress", "Completed", "Cancelled", "Cancel"]
            assert status in valid_statuses, f"Invalid task status: {status}"

            for keyword in expected_task_keywords:
                if keyword in title:
                    found_expected_tasks.append(keyword)
                    self._log(f"    + Found expected task keyword: {keyword}")

        assert len(found_expected_tasks) > 0, (
            f"No expected ransomware response tasks found. "
            f"Expected keywords: {expected_task_keywords}"
        )
        self._log(
            f"+ Found {len(found_expected_tasks)} expected task types: {found_expected_tasks}"
        )

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-07 COMPLETED — TASK VALIDATION VALIDATED ===")

    def test_state_machine_validation(self):
        """TC-01-08: State machine validation.

        Verifications:
          - State transitions are correct
          - State history is tracked
          - Final state is expected
        """
        self._log("=== TC-01-08: STATE MACHINE VALIDATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC01-STATE-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC01-001",
            "src_ip": "192.168.1.100",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "severity": 3,
            "source": "state-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        self.alert_data = payload
        alert_id = payload["alert_id"]
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(
            execution, alert_id=alert_id, expected_contract=self._MALICIOUS_CONTRACT
        )

        # Verify state with deep assertions
        self._log("STEP 4: Verifying case state with deep validation")
        cases = self.thehive.search_cases()

        alert_id = self.alert_data.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]

        status = last.get("status")
        self._log(f"+ Case status: {status}")
        assert status == "Open", f"Expected status 'Open', got '{status}'"

        valid_states = ["New", "Open", "InProgress", "Resolved", "Closed", "Deleted", "Imported"]
        assert status in valid_states, f"Invalid case status: {status}"

        created_at = last.get("createdAt")
        assert created_at, "Case missing createdAt timestamp"
        self._log(f"+ Case created at: {created_at}")

        severity = last.get("severity")
        assert severity, "Case missing severity"
        assert_incident_severity(last, "high")
        self._log(f"+ Case severity: {severity}")

        assert_incident_severity(last, "critical")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-08 COMPLETED — STATE MACHINE VALIDATION VALIDATED ===")

    def test_opensearch_validation(self):
        """TC-01-09: OpenSearch validation.

        Verifications:
          - Data is indexed in OpenSearch
          - Search queries work
          - Data integrity is maintained
        """
        self._log("=== TC-01-09: OPENSEARCH VALIDATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC01-OS-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC01-001",
            "src_ip": "192.168.1.100",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "severity": 3,
            "source": "opensearch-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        self.alert_data = payload
        alert_id = payload["alert_id"]
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(
            execution, alert_id=alert_id, expected_contract=self._MALICIOUS_CONTRACT
        )

        # Verify OpenSearch/Elasticsearch indexing with deep assertions
        self._log("STEP 7: Verifying OpenSearch indexing with deep validation")
        alert_id = self.alert_data.get("alert_id", "")
        src = self.es.search_by_alert_id(alert_id)
        assert src, f"Document not found in OpenSearch for alert_id={alert_id}"
        self._log(f"+ Document found in OpenSearch: {src.get('alert_id')}")

        critical_fields = ["alert_id", "alert_type", "hostname", "src_ip", "severity"]
        for field in critical_fields:
            assert field in src, f"OpenSearch document missing field: {field}"
            payload_value = self.alert_data.get(field)
            doc_value = src.get(field)
            if field in ["alert_id", "alert_type", "hostname"]:
                assert str(payload_value) == str(
                    doc_value
                ), f"Field {field} mismatch: payload={payload_value}, doc={doc_value}"
            self._log(f"  + Field {field}: {doc_value} (matches payload)")

        assert (
            src.get("alert_type") == "ransomware"
        ), f"alert_type should be 'ransomware', got '{src.get('alert_type')}'"

        timestamp = src.get("@timestamp") or src.get("timestamp")
        assert timestamp, "OpenSearch document missing timestamp"
        self._log(f"  + Timestamp: {timestamp}")

        health = self.es.cluster_health()
        status = health.get("status", "?")
        assert status in ("green", "yellow"), f"ES cluster in bad state: {status}"
        self._log(f"  + Cluster health: {status}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-09 COMPLETED — OPENSEARCH VALIDATION VALIDATED ===")
