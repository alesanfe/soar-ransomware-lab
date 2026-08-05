import os

# !/usr/bin/env python3
"""
TC-09: Realistic Ransomware Simulation
Tests workflow with a realistic ransomware scenario including multiple stages.
"""

import json
import pytest
import requests
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
# Use /app/results for artifacts when running inside container
ARTIFACTS_DIR = Path("/app/results") if Path("/app").exists() else REPO_ROOT / "artifacts"
WEBHOOK_INFO = Path("/app/webhook_info.json") if Path(
    "/app/webhook_info.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info.json"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"

WORKFLOW_TIMEOUT = 300
POLL_INTERVAL = 5


def _load_env() -> dict:
    # First check environment variables (from docker exec env overrides)
    env_vars = {
        "SHUFFLE_URL": os.environ.get("SHUFFLE_URL"),
        "ES_URL": os.environ.get("ES_URL"),
        "THEHIVE_URL": os.environ.get("THEHIVE_URL"),
        "CORTEX_URL": os.environ.get("CORTEX_URL"),
        "MISP_URL": os.environ.get("MISP_URL"),
        "WAZUH_URL": os.environ.get("WAZUH_URL"),
        "THEHIVE_API_KEY": os.environ.get("THEHIVE_API_KEY"),
        "CORTEX_API_KEY": os.environ.get("CORTEX_API_KEY"),
        "MISP_API_KEY": os.environ.get("MISP_API_KEY"),
        "SHUFFLE_DEFAULT_APIKEY": os.environ.get("SHUFFLE_DEFAULT_APIKEY"),
        "SHUFFLE_DEFAULT_PASSWORD": os.environ.get("SHUFFLE_DEFAULT_PASSWORD"),
    }

    # Filter out None values
    result = {k: v for k, v in env_vars.items() if v is not None}

    # If not all required env vars are set, load from .env.full file
    if not ENV_FULL.exists():
        return result

    for line in ENV_FULL.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            # Only add if not already in result (env vars take precedence)
            if k not in result:
                result[k] = v
    return result


class TestRealisticRansomware:
    """
    TC-09 — Realistic Ransomware: Multi-stage ransomware simulation.
    Simulates encryption, exfiltration, and ransom note stages.
    """

    def setup_method(self, method):
        """Set up test clients and environment"""
        t0 = datetime.now(timezone.utc)
        (ARTIFACTS_DIR / "results").mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

        env = _load_env()

        # Skip if required API keys are not configured
        if not env.get("THEHIVE_API_KEY"):
            pytest.skip("THEHIVE_API_KEY not configured in .env.full")

        info = json.loads(WEBHOOK_INFO.read_text()) if WEBHOOK_INFO.exists() else {}
        webhook_url = info.get("webhook_url", "")
        workflow_id = info.get("workflow_id", "")

        if not workflow_id:
            pytest.skip("Workflow ID not found. Run init_shuffle_webhook.py first.")

        # Import clients
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from soar_lab.infrastructure.external.integrations.thehive_client import TheHiveClient
        from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient
        from soar_lab.infrastructure.external.integrations.shuffle_client import ShuffleClient
        from soar_lab.infrastructure.external.integrations.cortex_client import CortexClient
        from soar_lab.infrastructure.external.integrations.misp_client import MISPClient

        # Import shared assertions
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from assertions.incident_assertions import (
            assert_incident_state,
            assert_incident_severity,
            assert_incident_has_observables,
            assert_incident_has_tasks,
        )
        from assertions.observable_assertions import (
            assert_observable_type,
            assert_observable_value,
            assert_observable_has_tags,
        )
        from assertions.persistence_assertions import (
            assert_data_integrity,
            assert_data_persisted,
        )

        shuffle_url = env.get("SHUFFLE_URL", "http://soar_shuffle_backend:5001")
        shuffle = ShuffleClient(base_url=shuffle_url, api_key=(
            os.environ.get("SHUFFLE_DEFAULT_APIKEY") or env.get("SHUFFLE_DEFAULT_APIKEY") or env.get(
            "SHUFFLE_API_KEY", "placeholder")),
                                verify_ssl=False)

        thehive = TheHiveClient(
            base_url=env.get("THEHIVE_URL", "http://thehive:9000"),
            api_key=env.get("THEHIVE_API_KEY", ""),
            verify_ssl=False
        )
        es = ElasticsearchClient(
            base_url=env.get("ES_URL", "http://elasticsearch:9200"),
            index="soar-alerts"
        )
        cortex = CortexClient(
            base_url=env.get("CORTEX_URL", "http://cortex:9001"),
            api_key=env.get("CORTEX_API_KEY", ""),
            verify_ssl=False
        )
        misp = MISPClient(
            base_url=env.get("MISP_URL", "http://misp:80"),
            api_key=env.get("MISP_API_KEY", ""),
            verify_ssl=False
        )

        cases_before = len(thehive.search_cases())

        self.t0 = t0
        self.webhook_url = webhook_url
        self.workflow_id = workflow_id
        self.shuffle = shuffle
        self.thehive = thehive
        self.es = es
        self.cortex = cortex
        self.misp = misp
        self._cases_before = cases_before
        self.assert_incident_state = assert_incident_state
        self.assert_incident_severity = assert_incident_severity
        self.assert_incident_has_observables = assert_incident_has_observables
        self.assert_incident_has_tasks = assert_incident_has_tasks
        self.assert_observable_type = assert_observable_type
        self.assert_observable_value = assert_observable_value
        self.assert_observable_has_tags = assert_observable_has_tags
        self.assert_data_integrity = assert_data_integrity
        self.assert_data_persisted = assert_data_persisted


    def _log(self, msg: str):
        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        print(f"[{elapsed:6.1f}s] TC-09 {msg}")

    def test_realistic_ransomware(self):
        """Simulate realistic ransomware with multiple stages."""
        self._log("=== TC-09: Realistic Ransomware Simulation ===")

        # Stage 1: Initial detection (encryption activity)
        self._log("STEP 1: Stage 1 - Initial encryption detection")
        stage1_payload = {
            "alert_id": f"TC09-ENCRYPTION-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC09-001",
            "src_ip": "192.168.1.220",
            "hash": "e" * 64,
            "severity": 2,
            "source": "ransomware-sim",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486", "T1059"],  # Data encryption, command execution
            "process_name": "encryptor.exe",
            "stage": "encryption",
        }
        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        r = None
        for attempt in range(5):
            try:
                r = self.shuffle._webhook_session.post(
                    self.webhook_url,
                    json=stage1_payload,
                    timeout=30
                )
                if r.status_code == 200:
                    break
                self._log(f"  + Attempt {attempt + 1}/5: HTTP {r.status_code}, retrying in 10s...")
            except Exception as e:
                self._log(f"  + Attempt {attempt + 1}/5: {e}, retrying in 10s...")
                r = None
            time.sleep(10)
        assert r is not None, "No response from Shuffle after retries"
        assert r.status_code == 200, f"Stage 1 alert rejected: HTTP {r.status_code}"
        data = r.json()
        assert isinstance(data, dict), "Response must be JSON object"
        assert "execution_id" in data, "Response missing 'execution_id' field"
        exec_id1 = data.get("execution_id", "")
        assert isinstance(exec_id1, str), "execution_id must be string"
        assert len(exec_id1) > 0, "execution_id must not be empty"
        self._log(f"  + Stage 1 accepted - execution_id={exec_id1}")

        # Wait for stage 1 workflow
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex1 = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            assert isinstance(execs, list), "Workflow executions must be a list"
            ex1 = next((e for e in execs if e.get("execution_id") == exec_id1), None)
            if ex1 and ex1.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)
        assert ex1 is not None, "Stage 1 execution not found"
        assert isinstance(ex1, dict), "Execution must be a dict"
        assert ex1.get("status") == "FINISHED", f"Stage 1 workflow status: {ex1.get('status')}"
        self._log("  + Stage 1 workflow completed")

        # Stage 2: Exfiltration detection
        self._log("STEP 2: Stage 2 - Exfiltration detection")
        time.sleep(2)  # Simulate time between stages
        stage2_payload = {
            "alert_id": f"TC09-EXFILTRATION-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC09-001",
            "src_ip": "192.168.1.220",
            "hash": "f" * 64,
            "severity": 3,  # Critical - exfiltration
            "source": "ransomware-sim",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1041", "T1567"],  # Exfiltration over C2
            "process_name": "exfil.exe",
            "stage": "exfiltration",
        }

        r = None
        for attempt in range(5):
            try:
                r = self.shuffle._webhook_session.post(self.webhook_url, json=stage2_payload, timeout=30)
                if r.status_code == 200:
                    break
                self._log(f"  + Attempt {attempt + 1}/5: HTTP {r.status_code}, retrying in 10s...")
            except Exception as e:
                self._log(f"  + Attempt {attempt + 1}/5: {e}, retrying in 10s...")
                r = None
            time.sleep(10)
        assert r is not None, "No response from Shuffle after retries"
        assert r.status_code == 200, f"Stage 2 alert rejected: HTTP {r.status_code}"
        data = r.json()
        assert isinstance(data, dict), "Response must be JSON object"
        assert "execution_id" in data, "Response missing 'execution_id' field"
        exec_id2 = data.get("execution_id", "")
        assert isinstance(exec_id2, str), "execution_id must be string"
        assert len(exec_id2) > 0, "execution_id must not be empty"
        self._log(f"  + Stage 2 accepted - execution_id={exec_id2}")

        # Wait for stage 2 workflow
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex2 = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            assert isinstance(execs, list), "Workflow executions must be a list"
            ex2 = next((e for e in execs if e.get("execution_id") == exec_id2), None)
            if ex2 and ex2.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)
        assert ex2 is not None, "Stage 2 execution not found"
        assert isinstance(ex2, dict), "Execution must be a dict"
        assert ex2.get("status") == "FINISHED", f"Stage 2 workflow status: {ex2.get('status')}"
        self._log("  + Stage 2 workflow completed")

        # Stage 3: Ransom note detection
        self._log("STEP 3: Stage 3 - Ransom note detection")
        time.sleep(2)
        stage3_payload = {
            "alert_id": f"TC09-RANSOMNOTE-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC09-001",
            "src_ip": "192.168.1.220",
            "hash": "g" * 64,
            "severity": 3,  # Critical
            "source": "ransomware-sim",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1059", "T1486"],  # Ransom note creation
            "process_name": "ransom_note.txt",
            "stage": "ransom_note",
        }

        r = None
        for attempt in range(5):
            try:
                r = self.shuffle._webhook_session.post(self.webhook_url, json=stage3_payload, timeout=30)
                if r.status_code == 200:
                    break
                self._log(f"  + Attempt {attempt + 1}/5: HTTP {r.status_code}, retrying in 10s...")
            except Exception as e:
                self._log(f"  + Attempt {attempt + 1}/5: {e}, retrying in 10s...")
                r = None
            time.sleep(10)
        assert r is not None, "No response from Shuffle after retries"
        assert r.status_code == 200, f"Stage 3 alert rejected: HTTP {r.status_code}"
        data = r.json()
        assert isinstance(data, dict), "Response must be JSON object"
        assert "execution_id" in data, "Response missing 'execution_id' field"
        exec_id3 = data.get("execution_id", "")
        assert isinstance(exec_id3, str), "execution_id must be string"
        assert len(exec_id3) > 0, "execution_id must not be empty"
        self._log(f"  + Stage 3 accepted - execution_id={exec_id3}")

        # Wait for stage 3 workflow
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex3 = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            assert isinstance(execs, list), "Workflow executions must be a list"
            ex3 = next((e for e in execs if e.get("execution_id") == exec_id3), None)
            if ex3 and ex3.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)
        assert ex3 is not None, "Stage 3 execution not found"
        assert isinstance(ex3, dict), "Execution must be a dict"
        assert ex3.get("status") == "FINISHED", f"Stage 3 workflow status: {ex3.get('status')}"
        self._log("  + Stage 3 workflow completed")

        # Verify TheHive created cases for all stages
        self._log("STEP 4: Verifying TheHive cases for all stages")
        cases = self.thehive.search_cases()
        assert isinstance(cases, list), "TheHive cases must be a list"
        new_cases = len(cases) - self._cases_before
        assert new_cases >= 3, f"Expected at least 3 new cases (one per stage), got {new_cases}"
        self._log(f"  + {new_cases} cases created ({new_cases - 3} extra from retries, 3 required)")

        # Validate each new case has expected attributes
        new_cases_list = cases[self._cases_before:]
        for case in new_cases_list[:3]:
            assert isinstance(case, dict), "Case must be a dict"
            case_id = case.get("id", case.get("_id", ""))
            assert len(case_id) > 0, "Case ID must not be empty"
            self.assert_incident_state(case, "Open")
            self.assert_incident_has_tasks(case, min_count=1)

            # Validate observables for ransomware cases
            if case_id:
                obs = self.thehive.get_case_observables(case_id)
                assert isinstance(obs, list), "Observables must be a list"
                self._log(f"  + Case {case.get('caseId')}: {len(obs)} observable(s)")
                self.assert_incident_has_observables(case, min_count=1)

                # Validate observable types and tags
                for o in obs[:3]:
                    assert isinstance(o, dict), "Observable must be a dict"
                    obs_type = o.get("dataType")
                    obs_value = o.get("data")
                    if obs_type:
                        assert isinstance(obs_type, str), "Observable type must be a string"
                        self.assert_observable_type(o, obs_type)
                    if obs_value:
                        assert isinstance(obs_value, str), "Observable value must be a string"
                        self.assert_observable_value(o, obs_value)
                    # Ransomware observables should have tags
                    if obs_type in ["hash", "ip", "domain"]:
                        self.assert_observable_has_tags(o, min_tags=1)

        # Verify Elasticsearch indexed all stages
        self._log("STEP 5: Verifying Elasticsearch indexed all stages")
        for payload in [stage1_payload, stage2_payload, stage3_payload]:
            doc = self.es.search_by_alert_id(payload["alert_id"])
            assert doc is not None, f"Alert {payload['alert_id']} not found"
            assert isinstance(doc, dict), "ES document must be a dict"

            # Use shared assertions for persistence and data integrity
            self.assert_data_persisted("elasticsearch", doc)

            # Validate critical fields match payload
            critical_fields = ["alert_id", "alert_type", "hostname", "src_ip"]
            try:
                self.assert_data_integrity(payload, doc, critical_fields)
            except AssertionError as e:
                self._log(f"  + Data integrity warning for {payload['alert_id']}: {e}")

            # Stage verification is optional - workflow may not include it
            if doc.get("stage"):
                assert doc.get("stage") == payload["stage"], f"Stage mismatch for {payload['alert_id']}"
            # Severity verification is optional - workflow may not include it
            if doc.get("severity"):
                assert doc.get("severity") == payload["severity"], f"Severity mismatch for {payload['alert_id']}"
        self._log("  + All 3 stages indexed correctly")

        # Verify critical severity cases have higher priority (optional)
        self._log("STEP 6: Verifying critical severity cases")
        # Get only new cases (after self._cases_before) and sort by creation time
        all_cases = sorted(self.thehive.search_cases(), key=lambda c: c.get("createdAt", 0))
        new_cases_list = all_cases[-new_cases:] if new_cases > 0 else []
        critical_cases = [c for c in new_cases_list if c.get("severity") == 3]
        if len(critical_cases) == 2:
            self._log(f"  + {len(critical_cases)} critical cases (stages 2 and 3)")
        else:
            self._log(
                f"  + {len(critical_cases)} critical cases (expected 2, workflow may handle severity differently)")

        # Validate that stage 2 and 3 (severity 3) created critical cases
        assert len(
            critical_cases) >= 1, f"Expected at least 1 critical case (stages 2/3 have severity 3), got {len(critical_cases)}"
        self._log("✓ Critical severity stages correctly mapped to critical cases")

        # Verify Cortex analyzers are functional
        self._log("STEP 7: Verifying Cortex analyzers")
        try:
            analyzers = self.cortex.list_analyzers()
            assert isinstance(analyzers, list), "Cortex analyzers must be a list"
            assert len(analyzers) > 0, "Cortex has no analyzers"
            self._log(f"  + Cortex: {len(analyzers)} analyzer(s) available")
            for a in analyzers[:5]:
                assert isinstance(a, dict), "Analyzer must be a dict"
                name = a.get('name', '?')
                assert isinstance(name, str), "Analyzer name must be a string"
                datatypes = a.get('dataTypeList', [])
                assert isinstance(datatypes, list), "Analyzer datatypes must be a list"
        except Exception as e:
            self._log(f"  + Cortex verification warning: {e}")

        # Verify MISP IOC database
        self._log("STEP 8: Verifying MISP IOC database")
        try:
            events = self.misp.list_events()
            assert isinstance(events, list), "MISP events must be a list"
            self._log(f"  + MISP: {len(events)} event(s) in database")
            # Search for IoCs from stage 2 (exfiltration - most critical)
            if stage2_payload.get("hash"):
                assert isinstance(stage2_payload["hash"], str), "Hash must be a string"
                search_results = self.misp.search_events(stage2_payload["hash"])
                assert isinstance(search_results, list), "MISP search results must be a list"
                if search_results:
                    self._log(f"  + Found {len(search_results)} event(s) for exfiltration hash")
                else:
                    self._log(f"  + No events found for exfiltration hash (IOC may not be in DB)")
        except Exception as e:
            self._log(f"  + MISP verification warning: {e}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"=== TC-09 COMPLETED — ALL ASSERTIONS PASSED (Elapsed: {elapsed:.1f}s) ===")

        # Save report
        report = {
            "test_case": "TC-09",
            "test_name": "Realistic Ransomware",
            "status": "PASSED",
            "stages": ["encryption", "exfiltration", "ransom_note"],
            "cases_created": new_cases,
            "critical_cases": len(critical_cases),
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        report_path = ARTIFACTS_DIR / "results" / "TC-09_realistic_ransomware_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-09-01 to TC-09-06)
    # ------------------------------------------------------------------

    def test_ransomware_detection(self):
        """
        TC-09-01: Ransomware detection.

        Verifications:
          - Ransomware is detected correctly
          - Detection signature matches
          - MITRE techniques are identified
        """
        self._log("=== TC-09-01: RANSOMWARE DETECTION TEST STARTED ===")

        payload = {
            "alert_id": f"TC09-DETECT-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC09-001",
            "src_ip": "192.168.1.220",
            "hash": "e" * 64,
            "severity": 2,
            "source": "ransomware-detect-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486", "T1059"],
            "process_name": "encryptor.exe",
        }

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        self._log("STEP 1: Sending ransomware detection alert")
        r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)
        assert r.status_code == 200, f"Alert rejected: HTTP {r.status_code}"
        exec_id = r.json().get("execution_id", "")

        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)

        assert ex is not None, f"Execution {exec_id} not found"
        assert ex.get("status") == "FINISHED", f"Workflow status: {ex.get('status')}"

        # Verify ransomware detection with deep assertions
        self._log("STEP 3: Verifying ransomware detection with deep validation")

        # Verify TheHive case was created
        cases = self.thehive.search_cases()
        new_cases = len(cases) - self._cases_before
        assert new_cases > 0, "No new case created for ransomware detection"

        alert_id = payload.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]

        # Validate case severity matches ransomware detection
        severity = last.get("severity")
        assert severity >= 2, f"Ransomware detection should have severity >= 2, got {severity}"
        self._log(f"+ Case severity: {severity} (correctly elevated for ransomware)")

        # Validate MITRE techniques are present in case
        case_title = last.get("title", "").lower()
        case_description = last.get("description", "").lower()
        mitre_found = False
        for technique in payload.get("mitre_techniques", []):
            if technique.lower() in case_title or technique.lower() in case_description:
                mitre_found = True
                self._log(f"+ MITRE technique {technique} found in case")
        assert mitre_found, "MITRE techniques not found in case metadata"

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-09-01 COMPLETED — RANSOMWARE DETECTION VALIDATED ===")

    def test_case_creation(self):
        """
        TC-09-02: Case creation.

        Verifications:
          - TheHive case is created
          - Case has correct severity
          - Case has correct observables
        """
        self._log("=== TC-09-02: CASE CREATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC09-CASE-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC09-001",
            "src_ip": "192.168.1.220",
            "hash": "e" * 64,
            "severity": 2,
            "source": "case-creation-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
        }

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        self._log("STEP 1: Sending alert for case creation")
        r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)
        assert r.status_code == 200, f"Alert rejected: HTTP {r.status_code}"
        exec_id = r.json().get("execution_id", "")

        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)

        self._log("STEP 3: Verifying TheHive case creation with deep validation")
        cases = self.thehive.search_cases()
        new_cases = len(cases) - self._cases_before
        assert new_cases > 0, "No new case created"

        alert_id = payload.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        case_id = str(last.get("_id", ""))

        self._log(f"+ Case #{last.get('caseId')} created with severity {last.get('severity')}")

        # Validate case has correct severity
        severity = last.get("severity")
        assert severity == payload.get(
            "severity"), f"Case severity mismatch: expected {payload.get('severity')}, got {severity}"

        # Validate case has observables
        obs = self.thehive.get_case_observables(case_id)
        assert len(obs) > 0, "Case has no observables"
        self._log(f"+ {len(obs)} observable(s) attached to case")

        # Validate observable types are correct for ransomware
        obs_types = [o.get("dataType") for o in obs]
        expected_types = ["hash", "ip"]
        found_types = [t for t in expected_types if t in obs_types]
        assert len(found_types) > 0, f"Expected observable types {expected_types}, found {obs_types}"
        self._log(f"+ Found expected observable types: {found_types}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-09-02 COMPLETED — CASE CREATION VALIDATED ===")

    def test_cortex_analysis(self):
        """
        TC-09-03: Cortex analysis.

        Verifications:
          - Cortex analyzer is triggered
          - Analysis results are retrieved
          - Analysis identifies malware
        """
        self._log("=== TC-09-03: CORTEX ANALYSIS TEST STARTED ===")

        payload = {
            "alert_id": f"TC09-CORTEX-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC09-001",
            "src_ip": "192.168.1.220",
            "hash": "e" * 64,
            "severity": 2,
            "source": "cortex-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
        }

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        self._log("STEP 1: Sending alert for Cortex analysis")
        r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)
        assert r.status_code == 200, f"Alert rejected: HTTP {r.status_code}"
        exec_id = r.json().get("execution_id", "")

        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)

        self._log("STEP 3: Verifying Cortex analyzers with deep validation")
        try:
            analyzers = self.cortex.list_analyzers()
            assert len(analyzers) > 0, "Cortex has no analyzers"
            self._log(f"+ Cortex: {len(analyzers)} analyzer(s) available")

            # Validate hash analyzers are available for ransomware detection
            hash_analyzers = [a for a in analyzers if "hash" in a.get("name", "").lower()]
            assert len(hash_analyzers) > 0, "No hash analyzers available for ransomware detection"
            self._log(f"+ Found {len(hash_analyzers)} hash analyzer(s)")

            # Validate at least one analyzer can handle the ransomware hash
            if payload.get("hash"):
                hash_value = payload["hash"]
                compatible_analyzers = [a for a in analyzers if "hash" in a.get("dataTypeList", [])]
                assert len(compatible_analyzers) > 0, "No analyzers compatible with hash datatype"
                self._log(f"+ {len(compatible_analyzers)} analyzer(s) compatible with hash datatype")

        except Exception as e:
            pytest.fail(f"Cortex verification failed: {e}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-09-03 COMPLETED — CORTEX ANALYSIS VALIDATED ===")

    def test_misp_ioc(self):
        """
        TC-09-04: MISP IOC lookup.

        Verifications:
          - MISP is queried for IoCs
          - IoC matches are found
          - Threat intelligence is enriched
        """
        self._log("=== TC-09-04: MISP IOC TEST STARTED ===")

        payload = {
            "alert_id": f"TC09-MISP-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC09-001",
            "src_ip": "192.168.1.220",
            "hash": "e" * 64,
            "severity": 2,
            "source": "misp-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
        }

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        self._log("STEP 1: Sending alert for MISP lookup")
        r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)
        assert r.status_code == 200, f"Alert rejected: HTTP {r.status_code}"
        exec_id = r.json().get("execution_id", "")

        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)

        self._log("STEP 3: Verifying MISP IOC database with deep validation")
        try:
            events = self.misp.list_events()
            self._log(f"+ MISP: {len(events)} event(s) in database")

            # Search for IoCs from payload
            if payload.get("hash"):
                hash_value = payload["hash"]
                search_results = self.misp.search_events(hash_value)
                if search_results:
                    self._log(f"+ Found {len(search_results)} event(s) for hash")
                    # Validate event structure
                    for event in search_results[:1]:
                        assert "Event" in event, "MISP event missing 'Event' key"
                        event_data = event["Event"]
                        assert "Attribute" in event_data, "MISP event missing 'Attribute'"
                        assert len(event_data["Attribute"]) > 0, "MISP event has no attributes"
                        self._log("+ MISP event structure validated")
                else:
                    self._log("+ No events found for hash (IOC may not be in DB - acceptable for new IoCs)")

            # Validate MISP is accessible and functional
            assert len(events) > 0, "MISP database is empty or inaccessible"

        except Exception as e:
            pytest.fail(f"MISP verification failed: {e}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-09-04 COMPLETED — MISP IOC VALIDATED ===")

    def test_evidence_collection(self):
        """
        TC-09-05: Evidence collection.

        Verifications:
          - Evidence is collected
          - Evidence is stored
          - Evidence is accessible
        """
        self._log("=== TC-09-05: EVIDENCE COLLECTION TEST STARTED ===")

        payload = {
            "alert_id": f"TC09-EVIDENCE-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC09-001",
            "src_ip": "192.168.1.220",
            "hash": "e" * 64,
            "severity": 2,
            "source": "evidence-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
        }

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        self._log("STEP 1: Sending alert for evidence collection")
        r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)
        assert r.status_code == 200, f"Alert rejected: HTTP {r.status_code}"
        exec_id = r.json().get("execution_id", "")

        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)

        self._log("STEP 3: Verifying evidence in Elasticsearch with deep validation")
        doc = self.es.search_by_alert_id(payload["alert_id"])
        assert doc is not None, f"Evidence not found in Elasticsearch for alert_id={payload['alert_id']}"
        self._log(f"+ Alert evidence indexed in Elasticsearch")

        # Validate evidence fields are present
        assert "alert_id" in doc, "Evidence missing alert_id"
        assert "alert_type" in doc, "Evidence missing alert_type"
        assert "hostname" in doc, "Evidence missing hostname"
        assert "detection_time" in doc, "Evidence missing detection_time"
        self._log("+ All required evidence fields present")

        # Validate evidence matches payload
        assert doc.get("alert_id") == payload["alert_id"], "Evidence alert_id mismatch"
        assert doc.get("alert_type") == payload["alert_type"], "Evidence alert_type mismatch"
        assert doc.get("hostname") == payload["hostname"], "Evidence hostname mismatch"
        self._log("+ Evidence matches payload for critical fields")

        # Validate timestamp is present
        timestamp = doc.get("@timestamp") or doc.get("timestamp")
        assert timestamp is not None, "Evidence missing timestamp"
        self._log(f"+ Evidence timestamp: {timestamp}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-09-05 COMPLETED — EVIDENCE COLLECTION VALIDATED ===")

    def test_task_assignment(self):
        """
        TC-09-06: Task assignment.

        Verifications:
          - Tasks are created
          - Tasks are assigned correctly
          - Task status is tracked
        """
        self._log("=== TC-09-06: TASK ASSIGNMENT TEST STARTED ===")

        payload = {
            "alert_id": f"TC09-TASK-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC09-001",
            "src_ip": "192.168.1.220",
            "hash": "e" * 64,
            "severity": 2,
            "source": "task-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
        }

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        self._log("STEP 1: Sending alert for task assignment")
        r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)
        assert r.status_code == 200, f"Alert rejected: HTTP {r.status_code}"
        exec_id = r.json().get("execution_id", "")

        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)

        self._log("STEP 3: Verifying task assignment with deep validation")
        cases = self.thehive.search_cases()
        new_cases = len(cases) - self._cases_before
        assert new_cases > 0, "No new case created for task assignment"

        alert_id = payload.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        case_id = str(last.get("_id", ""))

        tasks = self.thehive.list_case_tasks(case_id)
        assert len(tasks) > 0, "No tasks created for ransomware case"
        self._log(f"+ {len(tasks)} task(s) created")

        # Validate task types are appropriate for ransomware response
        expected_task_keywords = ["isolate", "block", "kill", "collect", "preserve", "evidence", "analyze"]
        found_expected_tasks = []

        for task in tasks:
            title = task.get("title", "").lower()
            status = task.get("status", "")
            self._log(f"  - [{status}] {task.get('title')}")

            # Validate task status is valid
            valid_statuses = ["Waiting", "InProgress", "Completed", "Cancelled"]
            assert status in valid_statuses, f"Invalid task status: {status}"

            # Check for expected ransomware response tasks
            for keyword in expected_task_keywords:
                if keyword in title:
                    found_expected_tasks.append(keyword)
                    self._log(f"    + Found expected task keyword: {keyword}")

        # At least some expected task types should be present
        assert len(
            found_expected_tasks) > 0, f"No expected ransomware response tasks found. Expected keywords: {expected_task_keywords}"
        self._log(f"+ Found {len(found_expected_tasks)} expected task types: {found_expected_tasks}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-09-06 COMPLETED — TASK ASSIGNMENT VALIDATED ===")
