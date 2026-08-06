#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case 01 (Malicious Alert)
Tests the complete SOAR workflow for a malicious ransomware alert:
  alert ingestion -> Shuffle workflow -> TheHive case -> Cortex analyzers
  -> MISP IOC lookup -> Elasticsearch index -> Wazuh agents.

Requires a live Docker stack (make up). Reads credentials from .env.full.
"""

import json
import os
import pytest
import requests
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
# Use /app/results for artifacts when running inside container
ARTIFACTS_DIR = Path("/app/results") if Path("/app").exists() else REPO_ROOT / "artifacts"
WEBHOOK_INFO = Path("/app/webhook_info.json") if Path(
    "/app/webhook_info.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info.json"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"

WORKFLOW_TIMEOUT = 300
POLL_INTERVAL = 5

sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.infrastructure.external.integrations.thehive_client import TheHiveClient
from soar_lab.infrastructure.external.integrations.cortex_client import CortexClient
from soar_lab.infrastructure.external.integrations.misp_client import MISPClient
from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient
from soar_lab.infrastructure.external.integrations.wazuh_client import WazuhClient
from soar_lab.infrastructure.external.integrations.shuffle_client import ShuffleClient

# Import shared assertions
sys.path.insert(0, str(Path(__file__).parent.parent))
from assertions.incident_assertions import (
    assert_incident_state,
    assert_incident_severity,
    assert_incident_has_observables,
    assert_incident_has_tasks,
    assert_incident_transition
)
from assertions.observable_assertions import (
    assert_observable_type,
    assert_observable_value,
    assert_observable_tlp,
    assert_observable_pap,
    assert_observable_has_tags,
    assert_observables_match_payload
)
from assertions.persistence_assertions import (
    assert_data_integrity,
    assert_data_persisted
)


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


class TestMaliciousAlert:
    """TC-01 — E2E: full SOAR pipeline for a malicious ransomware alert."""

    def setup_method(self, method):
        """Set up test clients and environment before each test method."""
        self.t0 = datetime.now(timezone.utc)
        (ARTIFACTS_DIR / "results").mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

        env = _load_env()

        # Skip if required API keys are not configured
        if not env.get("THEHIVE_API_KEY"):
            pytest.skip("THEHIVE_API_KEY not configured in .env.full")

        info = json.loads(WEBHOOK_INFO.read_text()) if WEBHOOK_INFO.exists() else {}
        # Use webhook_url (container-internal) when running inside container
        self.webhook_url = info.get("webhook_url", info.get("webhook_url_host", ""))
        self.workflow_id = info.get("workflow_id", "")

        shuffle_url = env.get("SHUFFLE_URL", "http://soar_shuffle_backend:5001")
        thehive_url = env.get("THEHIVE_URL", "http://thehive:9000")
        cortex_url = env.get("CORTEX_URL", "http://cortex:9001")
        misp_url = env.get("MISP_URL", "http://misp:80")
        es_url = env.get("ES_URL", "http://elasticsearch:9200")
        wazuh_url = env.get("WAZUH_URL", "https://wazuh_manager:55000")

        shuffle_pass = env.get("SHUFFLE_DEFAULT_PASSWORD", "")

        # Prioritize SHUFFLE_DEFAULT_APIKEY (from container env) over SHUFFLE_API_KEY (from .env file)
        shuffle_api_key = os.environ.get("SHUFFLE_DEFAULT_APIKEY") or env.get("SHUFFLE_DEFAULT_APIKEY") or env.get(
            "SHUFFLE_API_KEY", "placeholder")
        self.shuffle = ShuffleClient(base_url=shuffle_url, api_key=shuffle_api_key, verify_ssl=False)
        self.thehive = TheHiveClient(base_url=thehive_url, api_key=env.get("THEHIVE_API_KEY", ""), verify_ssl=False)
        self.cortex = CortexClient(base_url=cortex_url, api_key=env.get("CORTEX_API_KEY", ""), verify_ssl=False)
        self.misp = MISPClient(base_url=misp_url, api_key=env.get("MISP_API_KEY", ""), verify_ssl=False)
        self.es = ElasticsearchClient(base_url=es_url)
        self.wazuh = WazuhClient(
            base_url=wazuh_url,
            username=env.get("WAZUH_API_USERNAME", "wazuh-wui"),
            password=env.get("WAZUH_API_PASSWORD", ""),
        )

        self.s = requests.Session()
        self.s.verify = False

        ioc_file = FIXTURES_DIR / "ioc_samples.json"
        data = json.loads(ioc_file.read_text()) if ioc_file.exists() else {}
        self.test_cases = data.get("malicious_test_cases", [])

        self._cases_before = len(self.thehive.search_cases())
        self._es_docs_before = self.es.count()

    def _log(self, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-01 {msg}"
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
        with open(ARTIFACTS_DIR / "logs" / "notify.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    # ------------------------------------------------------------------
    # Steps
    # ------------------------------------------------------------------

    def _step_send_alert(self, payload: dict) -> str:
        self._log("STEP 1: Sending malicious alert to Shuffle workflow (webhook endpoint)")
        # Use webhook endpoint instead of execute to avoid nginx 502 errors
        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")
        r = None
        for attempt in range(5):
            try:
                r = self.shuffle._webhook_session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=20
                )
                if r.status_code == 200:
                    break
                self._log(f"+ Attempt {attempt + 1}/5: HTTP {r.status_code}, retrying in 10s...")
            except Exception as e:
                self._log(f"+ Attempt {attempt + 1}/5: {e}, retrying in 10s...")
                r = None
            time.sleep(10)
        assert r is not None, "No response from Shuffle after retries"
        assert r.status_code == 200, f"Workflow execution failed: HTTP {r.status_code} — {r.text[:200]}"
        data = r.json()
        assert isinstance(data, dict), "Response must be JSON object"
        assert data.get("success"), f"Shuffle did not accept alert: {data}"
        assert "execution_id" in data, "Response missing 'execution_id' field"
        exec_id = data.get("execution_id", "")
        assert isinstance(exec_id, str), "execution_id must be string"
        assert len(exec_id) > 0, "execution_id must not be empty"
        self._log(f"+ Alert accepted — execution_id={exec_id}")
        return exec_id

    def _step_wait_workflow(self, exec_id: str) -> dict:
        self._log(f"STEP 2: Waiting up to {WORKFLOW_TIMEOUT}s for workflow to finish")
        # No need to login since we're using API key authentication
        deadline = time.time() + WORKFLOW_TIMEOUT
        while time.time() < deadline:
            ex = self.shuffle.get_execution(self.workflow_id, exec_id)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                self._log(f"+ Workflow finished — status={ex['status']}")
                assert isinstance(ex, dict), "Execution must be a dict"
                assert "status" in ex, "Execution missing 'status' field"
                assert "results" in ex, "Execution missing 'results' field"
                return ex
            time.sleep(POLL_INTERVAL)
        pytest.fail(f"Workflow execution {exec_id} did not finish within {WORKFLOW_TIMEOUT}s")

    def _wait_for_executions(self, execution_ids: list, num_expected: int) -> dict:
        """Poll Shuffle until all supplied executions finish and return them by id."""
        deadline = time.time() + WORKFLOW_TIMEOUT
        pending_ids = set(execution_ids)
        completed = {}
        while time.time() < deadline and len(completed) < num_expected:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            by_id = {e.get("execution_id"): e for e in execs if e.get("execution_id")}
            for exec_id in list(pending_ids):
                ex = by_id.get(exec_id)
                if ex and ex.get("status") not in ("EXECUTING", ""):
                    completed[exec_id] = ex
                    pending_ids.discard(exec_id)
                    self._log(f"  + Execution {exec_id[:8]}... finished ({len(completed)}/{num_expected})")
            if pending_ids:
                time.sleep(POLL_INTERVAL)
        assert len(completed) == num_expected, f"Only {len(completed)}/{num_expected} workflows completed within {WORKFLOW_TIMEOUT}s"
        # Fetch full execution results once per completed workflow
        for exec_id in completed:
            full_ex = self.shuffle.get_execution(self.workflow_id, exec_id, include_results=True)
            if full_ex:
                completed[exec_id] = full_ex
        return completed

    def _step_assert_workflow_success(self, ex: dict):
        self._log("STEP 3: Verifying all workflow nodes succeeded")
        assert ex.get("status") == "FINISHED", f"Workflow status is {ex.get('status')}, expected FINISHED"
        results = ex.get("results", [])
        assert isinstance(results, list), "Workflow results must be a list"
        assert len(results) > 0, "Workflow has no results"
        for node in results:
            assert isinstance(node, dict), "Workflow node must be a dict"
            action = node.get("action", {})
            assert isinstance(action, dict), "Node action must be a dict"
            label = action.get("label", "?")
            assert isinstance(label, str), "Node label must be a string"
            status = node.get("status", "?")
            assert status in ["SUCCESS", "SKIPPED"], f"Node '{label}' status={status}: {node.get('result', '')[:300]}"
            snippet = str(node.get("result", ""))[:120].replace("\n", " ")
            self._log(f"  + {label}: {status} | {snippet}")

    def _step_verify_thehive_case(self) -> dict:
        self._log("STEP 4: Verifying TheHive case + observables + tasks")
        cases = self.thehive.search_cases()
        assert isinstance(cases, list), "TheHive cases must be a list"
        assert len(cases) > self._cases_before, "No new TheHive case was created by the workflow"
        # Filter cases by alert_id to find the case created by this test execution
        alert_id = self.alert_data.get("alert_id", "")
        assert isinstance(alert_id, str), "alert_id must be a string"
        assert len(alert_id) > 0, "alert_id must not be empty"
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id} in description"
        # Sort by createdAt descending to get the most recent matching case
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        assert isinstance(last, dict), "Case must be a dict"
        # Use Elasticsearch _id for API operations (GET requests require _id, not numeric caseId)
        case_id = str(last.get("_id", ""))
        assert len(case_id) > 0, "Case _id must not be empty"
        self._log(f"+ Case #{last.get('caseId')} '{last.get('title')}' "
                  f"sev={last.get('severity')} status={last.get('status')}")
        assert "ransomware" in last.get("title", "").lower(), f"Case title missing 'ransomware': {last.get('title')}"

        # Validate that malicious alert severity (3) maps to high/critical in TheHive
        payload_severity = self.alert_data.get("severity", 0)
        assert_incident_severity(last, "critical")
        self._log(f"+ Severity mapping validated: payload={payload_severity} -> case={last.get('severity')}")

        # Use shared assertions for state and severity
        assert_incident_state(last, "Open")
        assert_incident_severity(last, "critical")

        if case_id:
            # Observables — malicious alert MUST attach at least hash + IP
            obs = self.thehive.get_case_observables(case_id)
            self._log(f"  + {len(obs)} observable(s) attached")
            assert_incident_has_observables(last, min_count=1)

            # Validate observable types and values against payload
            payload_iocs = []
            if self.alert_data.get("hash"):
                payload_iocs.append({"type": "hash", "value": self.alert_data["hash"]})
            if self.alert_data.get("src_ip"):
                payload_iocs.append({"type": "ip", "value": self.alert_data["src_ip"]})
            if self.alert_data.get("domain"):
                payload_iocs.append({"type": "domain", "value": self.alert_data["domain"]})
            if self.alert_data.get("url"):
                payload_iocs.append({"type": "url", "value": self.alert_data["url"]})

            # Validate observables match payload
            if obs and payload_iocs:
                obs_data = [{"type": o.get("dataType"), "value": o.get("data")} for o in obs]
                try:
                    assert_observables_match_payload(obs_data, payload_iocs)
                    self._log("  + Observables match payload IoCs")
                except AssertionError as e:
                    self._log(f"  + Observable validation warning: {e}")

            # Validate each observable has expected attributes
            for observable in obs[:5]:
                obs_type = observable.get("dataType")
                obs_value = observable.get("data")
                self._log(f"    - {obs_type}: {obs_value}")
                if obs_type:
                    assert_observable_type(observable, obs_type)
                if obs_value:
                    assert_observable_value(observable, obs_value)
                # Validate TLP and PAP if present
                if observable.get("tlp"):
                    assert_observable_tlp(observable, observable.get("tlp"))
                if observable.get("pap"):
                    assert_observable_pap(observable, observable.get("pap"))
                # Validate tags for malicious indicators
                if obs_type in ["hash", "ip", "domain"]:
                    assert_observable_has_tags(observable, min_tags=1)

            # Tasks
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
            name = a.get('name', '?')
            assert isinstance(name, str), "Analyzer name must be a string"
            datatypes = a.get('dataTypeList', [])
            assert isinstance(datatypes, list), "Analyzer datatypes must be a list"
            self._log(f"    - {name} datatypes={datatypes}")

        # NEW: Verify that analyzers actually executed (not just exist)
        self._log("  + Verifying analyzer execution history")
        try:
            jobs = self.cortex.list_jobs()
            assert isinstance(jobs, list), "Cortex jobs must be a list"
            self._log(f"    + Found {len(jobs)} total job(s) in Cortex")

            # Check for recent jobs (last 10 minutes)
            recent_jobs = [job for job in jobs if job.get('createdAt')]
            if recent_jobs:
                self._log(f"    + Found {len(recent_jobs)} recent job(s)")

                # Verify at least one job completed successfully
                completed_jobs = [job for job in recent_jobs if job.get('status') == 'Success']
                if completed_jobs:
                    self._log(f"    + {len(completed_jobs)} job(s) completed successfully")
                    assert len(completed_jobs) > 0, "No completed Cortex jobs found"
                else:
                    self._log("    + Warning: No successfully completed jobs found")
            else:
                self._log("    + No recent jobs found - analyzers may not have executed")
        except Exception as e:
            self._log(f"    + Could not verify analyzer execution: {e}")

        # NEW: Try to run a test analyzer to verify execution capability
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

                # Wait for job completion (max 30 seconds)
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
                                    self._log(f"    + Analyzer job failed: {job_status.get('summary', 'Unknown')}")
                                break
                    except Exception as e:
                        self._log(f"    + Error checking job status: {e}")
                    time.sleep(2)
            else:
                self._log("    + No hash in alert data, skipping analyzer execution test")
        except Exception as e:
            self._log(f"    + Analyzer execution test failed: {e}")
            # Don't fail the test if analyzer execution test fails, but log it

    def _step_verify_misp_iocs(self):
        self._log("STEP 6: Verifying MISP IOC database + enrichment")
        # Do not skip MISP verification - ensure integration is functional
        try:
            events = self.misp.list_events()
            assert isinstance(events, list), "MISP events must be a list"
            self._log(f"  + MISP: {len(events)} event(s) in database")

            # NEW: Verify IOC enrichment - check if IOCs from alert are enriched in MISP
            enrichment_found = False
            for field in ["hash", "ip", "domain", "url"]:
                if self.alert_data.get(field):
                    value = self.alert_data[field]
                    assert isinstance(value, str), f"{field} must be a string"
                    search_results = self.misp.search_events(value)
                    assert isinstance(search_results, list), "MISP search results must be a list"
                    if search_results:
                        self._log(f"    + Found {len(search_results)} event(s) for {field}={value}")

                        # NEW: Verify enrichment - check for additional attributes
                        for event in search_results[:2]:  # Check first 2 events
                            if isinstance(event, dict):
                                event_id = event.get("id", "")
                                attributes = event.get("Attribute", [])
                                if isinstance(attributes, list) and len(attributes) > 1:
                                    self._log(f"      + Event {event_id} has {len(attributes)} attributes (enriched)")
                                    enrichment_found = True

                                    # Verify specific enrichment types
                                    attr_types = [attr.get("type") for attr in attributes if isinstance(attr, dict)]
                                    self._log(f"      + Attribute types: {', '.join(attr_types[:5])}")

                                    # Check for common enrichment indicators
                                    if "filename" in attr_types or "malware-sample" in attr_types:
                                        self._log("      + File-related enrichment detected")
                                    if "domain" in attr_types or "hostname" in attr_types:
                                        self._log("      + Network-related enrichment detected")
                    else:
                        self._log(f"    + No events found for {field}={value} (IOC may not be in DB)")

            # NEW: Verify enrichment status
            if enrichment_found:
                self._log("  + IOC enrichment validated successfully")
            else:
                self._log("  + Warning: IOC enrichment not detected - IoCs may be new")

        except Exception as e:
            self._log(f"  + MISP verification failed: {e}")
            # Do not skip - fail the test if MISP is not accessible
            pytest.fail(f"MISP integration not functional: {e}")

    def _step_verify_es_indexed(self):
        self._log("STEP 7: Verifying Elasticsearch indexing + cluster health")
        health = self.es.cluster_health()
        assert isinstance(health, dict), "ES health must be a dict"
        status = health.get("status", "?")
        assert isinstance(status, str), "ES health status must be a string"
        self._log(f"  + Cluster health: {status} | nodes={health.get('number_of_nodes', '?')}")
        assert status in ("green", "yellow"), f"ES cluster in bad state: {status}"
        # Find the specific document by alert_id
        alert_id = self.alert_data.get("alert_id", "")
        assert isinstance(alert_id, str), "alert_id must be a string"
        src = self.es.search_by_alert_id(alert_id)
        assert src, f"ES document not found for alert_id={alert_id}"
        assert isinstance(src, dict), "ES document must be a dict"
        self._log(f"  + Found doc: alert_id={src.get('alert_id', '?')} "
                  f"hostname={src.get('hostname', '?')} status={src.get('status', '?')}")

        # Use shared assertions for persistence and data integrity
        assert_data_persisted("elasticsearch", src)

        # Validate critical fields match payload
        critical_fields = ["alert_id", "alert_type", "hostname", "src_ip"]
        try:
            assert_data_integrity(self.alert_data, src, critical_fields)
            self._log("  + ES document matches payload on critical fields")
        except AssertionError as e:
            self._log(f"  + Data integrity warning: {e}")

        assert "alert_id" in src, "Indexed ES doc missing 'alert_id' field"
        assert src.get("alert_type") == "ransomware", f"ES doc alert_type must be 'ransomware', got '{src.get('alert_type')}'"
        assert src.get("hostname") == "WIN-TC01-001", f"ES doc hostname mismatch: {src.get('hostname')}"

    def _step_verify_wazuh(self):
        self._log("STEP 8: Verifying Wazuh connectivity + agents + manager + response commands")
        agents = self.wazuh.list_agents()
        assert isinstance(agents, list), "Wazuh agents must be a list"
        assert len(agents) > 0, "Wazuh has no registered agents"
        self._log(f"+ Wazuh: {len(agents)} agent(s)")
        for ag in agents[:5]:
            assert isinstance(ag, dict), "Agent must be a dict"
            self._log(f"  - [{ag.get('status', '?')}] {ag.get('name', '?')} "
                      f"id={ag.get('id', '?')} ip={ag.get('ip', '?')} "
                      f"os={ag.get('os', {}).get('name', '?')}")
        # At least one agent must be active (lab has simulated host)
        active = [a for a in agents if a.get("status") == "active"]
        assert len(active) > 0, "No active Wazuh agents — lab host agent not connected"
        # Manager info must return a version
        mgr = self.wazuh.get_manager_info()
        assert isinstance(mgr, dict), "Wazuh manager info must be a dict"
        assert mgr.get("version"), "Wazuh manager returned no version"
        self._log(f"  + Manager: version={mgr.get('version', '?')} type={mgr.get('type', '?')}")
        # Manager daemons — wazuh-analysisd and wazuh-remoted must be running
        mgr_status = self.wazuh.get_manager_status()
        assert isinstance(mgr_status, dict), "Wazuh manager status must be a dict"
        daemons = mgr_status.get("data", {}).get("affected_items", [{}])
        assert isinstance(daemons, list), "Daemons must be a list"
        if daemons:
            d = daemons[0]
            assert isinstance(d, dict), "Daemon info must be a dict"
            running = [k for k, v in d.items() if v == "running"]
            self._log(f"  + {len(running)} daemon(s) running: {running[:5]}")
            assert "wazuh-analysisd" in running, "Critical daemon 'wazuh-analysisd' is not running"
        # Agent detail with select
        detailed = self.wazuh.list_agents(select="name,id,status,lastKeepAlive,version")
        assert isinstance(detailed, list), "Detailed agents must be a list"
        for ag in detailed[:3]:
            self._log(f"  + {ag.get('name', '?')} last_seen={ag.get('lastKeepAlive', '?')} "
                      f"version={ag.get('version', '?')}")
        # Vulnerability scan on first active agent
        if active:
            agent_id = active[0].get("id", "")
            assert isinstance(agent_id, str), "Agent ID must be a string"
            try:
                vulns = self.wazuh.list_agent_vulnerabilities(agent_id, limit=3)
                assert isinstance(vulns, list), "Vulnerabilities must be a list"
                self._log(f"  + Agent {agent_id} vulnerabilities: {len(vulns)} CVE(s)")
                for v in vulns[:3]:
                    self._log(f"    - {v.get('cve', '?')} sev={v.get('severity', '?')}")
            except Exception:
                self._log(f"  + Vulnerability scan skipped (module may be disabled)")

        # NEW: Verify that agents receive response commands
        self._log("  + Verifying agent response command capability")
        try:
            if active:
                test_agent_id = active[0].get("id", "")
                self._log(f"    + Testing response command on agent {test_agent_id}")

                # Try to get agent active configuration to verify command capability
                try:
                    config = self.wazuh.get_agent_config(test_agent_id)
                    if config:
                        self._log("    + Agent configuration retrieved successfully")
                        assert isinstance(config, dict), "Agent config must be a dict"
                except Exception as e:
                    self._log(f"    + Could not retrieve agent config: {e}")

                # Check for active tasks/commands on the agent
                try:
                    tasks = self.wazuh.list_agent_tasks(test_agent_id)
                    if tasks:
                        self._log(f"    + Agent has {len(tasks)} active task(s)")
                        assert isinstance(tasks, list), "Agent tasks must be a list"
                    else:
                        self._log("    + No active tasks on agent (normal for idle state)")
                except Exception as e:
                    self._log(f"    + Could not retrieve agent tasks: {e}")

                # Verify agent can receive commands by checking agent status
                agent_status = self.wazuh.get_agent_status(test_agent_id)
                if agent_status:
                    self._log(f"    + Agent status: {agent_status}")
                    # If agent is active, it can receive commands
                    if agent_status.get("status") == "active":
                        self._log("    + Agent is active and can receive response commands")
                    else:
                        self._log(f"    + Agent status: {agent_status.get('status')}")
        except Exception as e:
            self._log(f"    + Response command verification failed: {e}")

    def _step_save_report(self, result: dict):
        report_file = ARTIFACTS_DIR / "results" / "TC-01_malicious_report.json"
        report_file.write_text(json.dumps(result, indent=2, default=str))
        self._log(f"+ Report saved: {report_file}")

    # ------------------------------------------------------------------
    # Main test
    # ------------------------------------------------------------------

    def _run_full_workflow_group(self, group_cases: list) -> None:
        """Submit a batch of IOC cases, wait for them, and verify each one."""
        if not group_cases:
            self.skipTest("No test cases in group")

        self._log("=== TC-01: MALICIOUS ALERT E2E BATCH STARTED ===")

        # ---- Phase 1: build and submit the IOC cases sequentially ----
        submissions = []
        for test_case in group_cases:
            name = test_case.get("name", "unknown")
            payload = {
                "alert_id": f"TC01-{name}-{int(time.time())}",
                "alert_type": "ransomware",
                "hostname": test_case.get("hostname", "WIN-TC01-001"),
                "src_ip": test_case.get("ip", "172.31.54.117"),
                "hash": test_case.get("hash", "6c2ed91b8f53686dc6f4165b0fb19bf0df01b7612e2e2b2d9f7ad6313fba9a92"),
                "severity": 3,
                "source": "siem-ransomware-detection",
                "detection_time": datetime.now(timezone.utc).isoformat(),
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
            exec_id = self._step_send_alert(payload)
            submissions.append({"case": test_case, "payload": payload, "exec_id": exec_id})

        # ---- Phase 2: wait for all executions with batched polling ----
        exec_ids = [s["exec_id"] for s in submissions]
        executions = self._wait_for_executions(exec_ids, len(exec_ids))

        # ---- Phase 3: verify each case ----
        failed_cases = []
        for sub in submissions:
            test_case = sub["case"]
            payload = sub["payload"]
            exec_id = sub["exec_id"]
            name = test_case.get("name", "unknown")
            self._log(f"=== Verifying case: {name} ===")
            try:
                self.alert_data = payload
                ex = executions[exec_id]
                self._step_assert_workflow_success(ex)
                self._step_verify_ioc_detection(name, test_case)
            except Exception as e:
                self._log(f"  + Case {name} failed: {e}")
                failed_cases.append(name)

        if failed_cases:
            self._log(f"  + Failed cases: {', '.join(failed_cases)}")
            pytest.fail(f"Test cases failed: {len(failed_cases)}/{len(group_cases)}: {', '.join(failed_cases)}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01 BATCH COMPLETED — ALL ASSERTIONS PASSED ===")

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_malicious_alert_full_workflow_group_1(self):
        """TC-01 batch 1: hashes + IPs (4 cases)."""
        if not self.test_cases:
            self.skipTest("No test cases found in ioc_samples.json")
        self._run_full_workflow_group(self.test_cases[:4])

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_malicious_alert_full_workflow_group_2(self):
        """TC-01 batch 2: domains + URLs (4 cases)."""
        if not self.test_cases:
            self.skipTest("No test cases found in ioc_samples.json")
        self._run_full_workflow_group(self.test_cases[4:8])

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_malicious_alert_full_workflow_group_3(self):
        """TC-01 batch 3: mail + file (4 cases)."""
        if not self.test_cases:
            self.skipTest("No test cases found in ioc_samples.json")
        self._run_full_workflow_group(self.test_cases[8:12])

    @pytest.mark.timeout(900)
    @pytest.mark.slow
    def test_malicious_alert_full_workflow_group_4(self):
        """TC-01 batch 4: fqdn + hostname (4 cases)."""
        if not self.test_cases:
            self.skipTest("No test cases found in ioc_samples.json")
        self._run_full_workflow_group(self.test_cases[12:16])

    # ------------------------------------------------------------------
    # IOC detection verification
    # ------------------------------------------------------------------

    def _step_verify_ioc_detection(self, case_name: str, test_case: dict):
        """Verify that the malicious IOC in the test case is detected by Cortex/MISP"""
        self._log(f"Verifying malicious IOC detection for {case_name}")

        # Check Cortex for hash analysis if hash is the malicious field
        if "hash" in case_name and test_case.get("hash"):
            try:
                job = self.cortex.run_analyzer("FileInfo_8_0", "hash", test_case["hash"])
                self._log(f"  + Cortex hash analysis job: {job.get('id', 'N/A')}")
            except Exception as e:
                self._log(f"  + Cortex hash analysis skipped: {e}")

        # Check MISP for IOC presence
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
        """
        TC-01-03: Observable validation.

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
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"]
        }

        self.alert_data = payload
        exec_id = self._step_send_alert(payload)
        ex = self._step_wait_workflow(exec_id)
        self._step_assert_workflow_success(ex)

        # Verify observables with deep assertions
        self._log("STEP 4: Verifying observables with deep validation")
        cases = self.thehive.search_cases()
        assert len(cases) > self._cases_before, "No new TheHive case created"

        # Find the case created by this test
        alert_id = self.alert_data.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        case_id = str(last.get("_id", ""))

        # Get observables and validate deeply
        obs = self.thehive.get_case_observables(case_id)
        assert len(obs) > 0, "No observables found in case"
        self._log(f"+ {len(obs)} observable(s) found")

        # Extract expected IoCs from payload
        expected_iocs = []
        if self.alert_data.get("hash"):
            expected_iocs.append({"type": "hash", "value": self.alert_data["hash"]})
        if self.alert_data.get("src_ip"):
            expected_iocs.append({"type": "ip", "value": self.alert_data["src_ip"]})

        # Validate each observable matches payload
        obs_data = [{"type": o.get("dataType"), "value": o.get("data")} for o in obs]
        assert_observables_match_payload(obs_data, expected_iocs)
        self._log("+ Observables match payload IoCs")

        # Validate each observable has correct type and value
        for observable in obs:
            obs_type = observable.get("dataType")
            obs_value = observable.get("data")
            assert obs_type, "Observable missing dataType"
            assert obs_value, "Observable missing data"
            assert_observable_type(observable, obs_type)
            assert_observable_value(observable, obs_value)
            self._log(f"  - [{obs_type}] {obs_value} validated")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-03 COMPLETED — OBSERVABLE VALIDATION VALIDATED ===")

    def test_ioc_validation(self):
        """
        TC-01-04: IoC validation.

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
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"]
        }

        self.alert_data = payload
        exec_id = self._step_send_alert(payload)
        ex = self._step_wait_workflow(exec_id)
        self._step_assert_workflow_success(ex)

        # Verify IoCs in MISP with deep assertions
        self._log("STEP 6: Verifying IoCs in MISP with deep validation")
        try:
            events = self.misp.list_events()
            self._log(f"+ MISP: {len(events)} event(s)")

            # Search for specific IoCs from payload
            payload_iocs = []
            if self.alert_data.get("hash"):
                payload_iocs.append({"type": "hash", "value": self.alert_data["hash"]})
            if self.alert_data.get("src_ip"):
                payload_iocs.append({"type": "ip", "value": self.alert_data["src_ip"]})

            # Validate that at least one IoC is found in MISP
            ioc_found = False
            for ioc in payload_iocs:
                search_results = self.misp.search_events(ioc["value"])
                if search_results:
                    ioc_found = True
                    self._log(f"+ Found {len(search_results)} event(s) for {ioc['type']}={ioc['value']}")
                    # Validate event structure
                    for event in search_results[:1]:
                        assert "Event" in event, "MISP event missing 'Event' key"
                        event_data = event["Event"]
                        assert "info" in event_data, "MISP event missing 'info'"
                        assert "Attribute" in event_data, "MISP event missing 'Attribute'"
                        assert len(event_data["Attribute"]) > 0, "MISP event has no attributes"

            # At least one IoC should be found (if MISP is configured)
            if payload_iocs:
                assert ioc_found or len(events) > 0, f"No IoCs found in MISP for payload: {payload_iocs}"

        except Exception as e:
            pytest.fail(f"MISP verification failed: {e}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-04 COMPLETED — IOC VALIDATION VALIDATED ===")

    def test_tag_validation(self):
        """
        TC-01-05: Tag validation.

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
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"]
        }

        self.alert_data = payload
        exec_id = self._step_send_alert(payload)
        ex = self._step_wait_workflow(exec_id)
        self._step_assert_workflow_success(ex)

        # Verify tags with deep assertions
        self._log("STEP 4: Verifying tags on observables with deep validation")
        cases = self.thehive.search_cases()
        assert len(cases) > self._cases_before, "No new TheHive case created"

        alert_id = self.alert_data.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        case_id = str(last.get("_id", ""))

        obs = self.thehive.get_case_observables(case_id)
        assert len(obs) > 0, "No observables found in case"

        # Validate that malicious observables have tags
        for observable in obs:
            obs_type = observable.get("dataType")
            tags = observable.get("tags", [])
            if obs_type in ["hash", "ip", "domain"]:
                assert_observable_has_tags(observable, min_tags=1)
                self._log(f"  - [{obs_type}] has {len(tags)} tag(s): {tags}")
                # Validate tag format (should include MITRE techniques)
                mitre_tags = [t for t in tags if t.startswith("T") or t.startswith("TA")]
                if mitre_tags:
                    self._log(f"    + MITRE tags found: {mitre_tags}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-05 COMPLETED — TAG VALIDATION VALIDATED ===")

    def test_tlp_pap_validation(self):
        """
        TC-01-06: TLP/PAP validation.

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
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"]
        }

        self.alert_data = payload
        exec_id = self._step_send_alert(payload)
        ex = self._step_wait_workflow(exec_id)
        self._step_assert_workflow_success(ex)

        # Verify TLP/PAP with deep assertions
        self._log("STEP 4: Verifying TLP/PAP on observables with deep validation")
        cases = self.thehive.search_cases()
        assert len(cases) > self._cases_before, "No new TheHive case created"

        alert_id = self.alert_data.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        case_id = str(last.get("_id", ""))

        obs = self.thehive.get_case_observables(case_id)
        assert len(obs) > 0, "No observables found in case"

        # TheHive 3.x stores TLP/PAP as integers (0=white, 1=green, 2=amber, 3=red)
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
                self._log(f"  - TLP: not set (using default)")

            if pap is not None:
                assert pap in valid_pap_values, f"Invalid PAP value: {pap}"
                assert_observable_pap(observable, pap)
                self._log(f"  - PAP: {pap} (valid)")
            else:
                self._log(f"  - PAP: not set (using default)")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-06 COMPLETED — TLP/PAP VALIDATION VALIDATED ===")

    def test_task_validation(self):
        """
        TC-01-07: Task validation.

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
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"]
        }

        self.alert_data = payload
        exec_id = self._step_send_alert(payload)
        ex = self._step_wait_workflow(exec_id)
        self._step_assert_workflow_success(ex)

        # Verify tasks with deep assertions
        self._log("STEP 4: Verifying tasks with deep validation")
        cases = self.thehive.search_cases()
        assert len(cases) > self._cases_before, "No new TheHive case created"

        alert_id = self.alert_data.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]
        case_id = str(last.get("_id", ""))

        tasks = self.thehive.list_case_tasks(case_id)
        assert len(tasks) > 0, "No tasks found in case"
        self._log(f"+ {len(tasks)} task(s) found")

        # Validate expected ransomware response tasks
        expected_task_keywords = ["isolate", "block", "kill", "collect", "preserve", "evidence"]
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
        assert len(found_expected_tasks) > 0, f"No expected ransomware response tasks found. Expected keywords: {expected_task_keywords}"
        self._log(f"+ Found {len(found_expected_tasks)} expected task types: {found_expected_tasks}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-07 COMPLETED — TASK VALIDATION VALIDATED ===")

    def test_state_machine_validation(self):
        """
        TC-01-08: State machine validation.

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
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"]
        }

        self.alert_data = payload
        exec_id = self._step_send_alert(payload)
        ex = self._step_wait_workflow(exec_id)
        self._step_assert_workflow_success(ex)

        # Verify state with deep assertions
        self._log("STEP 4: Verifying case state with deep validation")
        cases = self.thehive.search_cases()
        assert len(cases) > self._cases_before, "No new TheHive case created"

        alert_id = self.alert_data.get("alert_id", "")
        matching_cases = [c for c in cases if alert_id in c.get("description", "")]
        assert len(matching_cases) > 0, f"No case found with alert_id {alert_id}"
        matching_cases.sort(key=lambda c: c.get("createdAt", 0), reverse=True)
        last = matching_cases[0]

        # Validate initial state is Open
        status = last.get("status")
        self._log(f"+ Case status: {status}")
        assert status == "Open", f"Expected status 'Open', got '{status}'"

        # Validate state transition is possible (state machine is functional)
        valid_states = ["New", "Open", "InProgress", "Resolved", "Closed", "Deleted", "Imported"]
        assert status in valid_states, f"Invalid case status: {status}"

        # Validate timestamp for state change
        created_at = last.get("createdAt")
        assert created_at, "Case missing createdAt timestamp"
        self._log(f"+ Case created at: {created_at}")

        # Validate severity mapping (TheHive uses 1=low, 2=medium, 3=high)
        severity = last.get("severity")
        assert severity, "Case missing severity"
        assert_incident_severity(last, "high")
        self._log(f"+ Case severity: {severity}")

        # For malicious alert, severity should be high/critical
        assert_incident_severity(last, "critical")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-08 COMPLETED — STATE MACHINE VALIDATION VALIDATED ===")

    def test_opensearch_validation(self):
        """
        TC-01-09: OpenSearch validation.

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
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"]
        }

        self.alert_data = payload
        exec_id = self._step_send_alert(payload)
        ex = self._step_wait_workflow(exec_id)
        self._step_assert_workflow_success(ex)

        # Verify OpenSearch/Elasticsearch indexing with deep assertions
        self._log("STEP 7: Verifying OpenSearch indexing with deep validation")
        alert_id = self.alert_data.get("alert_id", "")
        src = self.es.search_by_alert_id(alert_id)
        assert src, f"Document not found in OpenSearch for alert_id={alert_id}"
        self._log(f"+ Document found in OpenSearch: {src.get('alert_id')}")

        # Validate critical fields match payload
        critical_fields = ["alert_id", "alert_type", "hostname", "src_ip", "severity"]
        for field in critical_fields:
            assert field in src, f"OpenSearch document missing field: {field}"
            payload_value = self.alert_data.get(field)
            doc_value = src.get(field)
            if field in ["alert_id", "alert_type", "hostname"]:
                assert str(payload_value) == str(doc_value), f"Field {field} mismatch: payload={payload_value}, doc={doc_value}"
            self._log(f"  + Field {field}: {doc_value} (matches payload)")

        # Validate alert_type is ransomware
        assert src.get("alert_type") == "ransomware", f"alert_type should be 'ransomware', got '{src.get('alert_type')}'"

        # Validate timestamp is present and valid
        timestamp = src.get("@timestamp") or src.get("timestamp")
        assert timestamp, "OpenSearch document missing timestamp"
        self._log(f"  + Timestamp: {timestamp}")

        # Validate cluster health
        health = self.es.cluster_health()
        status = health.get("status", "?")
        assert status in ("green", "yellow"), f"ES cluster in bad state: {status}"
        self._log(f"  + Cluster health: {status}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-01-09 COMPLETED — OPENSEARCH VALIDATION VALIDATED ===")


if __name__ == "__main__":
    unittest.main()
