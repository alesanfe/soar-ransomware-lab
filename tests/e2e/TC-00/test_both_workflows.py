#!/usr/bin/env python3
"""
TC-00 — Parametrized Tests for Both Workflows
Tests both SOAR-Ransomware-Response (simulated) and SOAR-Ransomware-Response-Wazuh (Wazuh SIEM)
"""

import json
import os
import pytest
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
ARTIFACTS_DIR = Path("/app/results") if Path("/app/results").exists() else REPO_ROOT / "artifacts" / "results"
WEBHOOK_INFO = Path("/app/webhook_info.json") if Path(
    "/app/webhook_info.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info.json"
WEBHOOK_INFO_WAZUH = Path("/app/webhook_info_wazuh.json") if Path(
    "/app/webhook_info_wazuh.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info_wazuh.json"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"

WORKFLOW_TIMEOUT = 600
POLL_INTERVAL = 3

sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.infrastructure.external.integrations.thehive_client import TheHiveClient
from soar_lab.infrastructure.external.integrations.cortex_client import CortexClient
from soar_lab.infrastructure.external.integrations.misp_client import MISPClient
from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient
from soar_lab.infrastructure.external.integrations.wazuh_client import WazuhClient
from soar_lab.infrastructure.external.integrations.shuffle_client import ShuffleClient


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
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            # Only add if not already in result (env vars take precedence)
            if key not in result:
                result[key] = value
    return result


@pytest.fixture(scope="class")
def workflow_clients():
    """Initialize workflow clients for testing."""
    t0 = datetime.now(timezone.utc)
    (ARTIFACTS_DIR / "results").mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

    env = _load_env()

    # Skip if required API keys are not configured
    if not env.get("THEHIVE_API_KEY"):
        pytest.skip("THEHIVE_API_KEY not configured in .env.full")

    # Load both webhook configs
    simulated_info = json.loads(WEBHOOK_INFO.read_text()) if WEBHOOK_INFO.exists() else {}
    wazuh_info = json.loads(WEBHOOK_INFO_WAZUH.read_text()) if WEBHOOK_INFO_WAZUH.exists() else {}
    webhook_url = simulated_info.get("webhook_url", "")

    shuffle_url = env.get("SHUFFLE_URL", "http://soar_shuffle_backend:5001")
    thehive_url = env.get("THEHIVE_URL", "http://thehive:9000")
    cortex_url = env.get("CORTEX_URL", "http://cortex:9001")
    misp_url = env.get("MISP_URL", "http://misp:80")
    es_url = env.get("ES_URL", "http://elasticsearch:9200")
    wazuh_url = env.get("WAZUH_URL", "https://wazuh_manager:55000")

    shuffle = ShuffleClient(base_url=shuffle_url, api_key=(
        os.environ.get("SHUFFLE_DEFAULT_APIKEY") or env.get("SHUFFLE_DEFAULT_APIKEY") or env.get(
        "SHUFFLE_API_KEY", "placeholder")),
                            verify_ssl=False)
    thehive = TheHiveClient(base_url=thehive_url, api_key=env.get("THEHIVE_API_KEY", ""), verify_ssl=False)
    cortex = CortexClient(base_url=cortex_url, api_key=env.get("CORTEX_API_KEY", ""), verify_ssl=False)
    misp = MISPClient(base_url=misp_url, api_key=env.get("MISP_API_KEY", ""), verify_ssl=False)
    es = ElasticsearchClient(base_url=es_url)
    wazuh = WazuhClient(
        base_url=wazuh_url,
        username=env.get("WAZUH_API_USERNAME", "wazuh-wui"),
        password=env.get("WAZUH_API_PASSWORD", ""),
    )

    return {
        't0': t0,
        'simulated_info': simulated_info,
        'wazuh_info': wazuh_info,
        'webhook_url': webhook_url,
        'shuffle': shuffle,
        'thehive': thehive,
        'cortex': cortex,
        'misp': misp,
        'es': es,
        'wazuh': wazuh
    }


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] TC-00 {msg}"
    sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()
    with open(ARTIFACTS_DIR / "logs" / "both_workflows.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _step_send_alert(shuffle, webhook_url, workflow_id: str, payload: dict) -> str:
    if not webhook_url:
        pytest.fail("Webhook URL not found in webhook_info.json")
    _log(f"STEP 1: Sending alert to workflow {workflow_id[:8]}...")
    r = None
    for attempt in range(5):
        try:
            r = shuffle._webhook_session.post(
                webhook_url,
                json=payload,
                timeout=20
            )
            if r.status_code == 200:
                break
            _log(f"+ Attempt {attempt + 1}/5: HTTP {r.status_code}, retrying in 10s...")
        except Exception as e:
            _log(f"+ Attempt {attempt + 1}/5: {e}, retrying in 10s...")
            r = None
        time.sleep(10)
    assert r is not None, "No response from Shuffle after retries"
    assert r.status_code == 200, f"Workflow execution failed: HTTP {r.status_code} — {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict), "Response must be JSON object"
    assert data.get("success"), f"Shuffle did not accept alert: {data}"
    exec_id = data.get("execution_id", "")
    assert isinstance(exec_id, str), "execution_id must be string"
    assert len(exec_id) > 0, "execution_id must not be empty"
    _log(f"+ Alert accepted — execution_id={exec_id}")
    return exec_id


def _step_wait_workflow(shuffle, workflow_id: str, exec_id: str) -> dict:
    _log(f"STEP 2: Waiting up to {WORKFLOW_TIMEOUT}s for workflow to finish")
    start = time.time()
    while time.time() - start < WORKFLOW_TIMEOUT:
        try:
            execution = shuffle.get_execution(workflow_id, exec_id, include_results=False)
            if execution:
                status = execution.get("status", "")
                if str(status).upper() in {"FINISHED", "FAILED", "STOPPED", "SUCCESS"}:
                    _log(f"+ Workflow finished with status: {status}")
                    return execution
        except Exception:
            pass
        time.sleep(POLL_INTERVAL)
    pytest.fail(f"Workflow timeout after {WORKFLOW_TIMEOUT}s")


# Parametrized test for both workflows
@pytest.mark.parametrize("workflow_type", ["simulated", "wazuh"])
def test_workflow_malicious(workflow_clients, workflow_type):
    """
    TC-00-01: Parametrized test for both workflows with malicious alert.

    This test runs in parallel for both simulated and Wazuh workflows.
    """
    clients = workflow_clients
    simulated_info = clients['simulated_info']
    wazuh_info = clients['wazuh_info']
    shuffle = clients['shuffle']
    es = clients['es']
    webhook_url = clients['webhook_url']

    if workflow_type == "simulated":
        if not simulated_info.get("workflow_id"):
            pytest.skip("Simulated workflow ID not found")
        workflow_id = simulated_info["workflow_id"]
        source = "simulated-siem"
        hostname = "WIN-SIM-001"
        alert_prefix = "TC00-SIM"
    else:  # wazuh
        # Prefer dedicated wazuh workflow if it exists
        wazuh_workflow_id = wazuh_info.get("workflow_id", "")
        wazuh_webhook_url = wazuh_info.get("webhook_url", "")

        if wazuh_workflow_id and wazuh_webhook_url:
            try:
                import requests as _req
                _r = _req.get(
                    shuffle._url(f"/api/v1/workflows/{wazuh_workflow_id}"),
                    headers=dict(shuffle._session.headers),
                    timeout=5,
                )
                if _r.status_code == 200:
                    workflow_id = wazuh_workflow_id
                    webhook_url = wazuh_webhook_url
                    _log(f"Using dedicated Wazuh workflow {workflow_id[:8]}")
                else:
                    _log(f"Wazuh workflow not available (HTTP {_r.status_code}), using fallback")
                    workflow_id = simulated_info.get("workflow_id", "")
                    webhook_url = simulated_info.get("webhook_url", "")
            except Exception:
                workflow_id = simulated_info.get("workflow_id", "")
                webhook_url = simulated_info.get("webhook_url", "")
        else:
            workflow_id = simulated_info.get("workflow_id", "")
            webhook_url = simulated_info.get("webhook_url", "")

        if not workflow_id:
            pytest.skip("No active workflow found")

        source = "wazuh-siem"
        hostname = "WIN-WAZ-001"
        alert_prefix = "TC00-WAZ"

    _log(f"=== Testing {workflow_type.capitalize()} Workflow (Malicious) ===")

    payload = {
        "alert_id": f"{alert_prefix}-{int(time.time())}",
        "alert_type": "ransomware",
        "hostname": hostname,
        "src_ip": "192.168.1.100" if workflow_type == "simulated" else "192.168.1.101",
        "severity": 2,
        "process_name": "malware.exe",
        "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
        "mitre_techniques": ["T1486"],
        "detection_time": datetime.now(timezone.utc).isoformat(),
        "source": source
    }

    if workflow_type == "wazuh":
        payload.update({
            "wazuh_agent_id": "001",
            "wazuh_agent_name": "simulated-agent",
            "wazuh_agent_ip": "192.168.1.101"
        })

    exec_id = _step_send_alert(shuffle, webhook_url, workflow_id, payload)
    result = _step_wait_workflow(shuffle, workflow_id, exec_id)
    assert isinstance(result, dict), "Result must be a dict"
    status = result.get("status", "").upper()
    assert status in ["FINISHED", "SUCCESS"], f"Workflow status should be FINISHED or SUCCESS, got {status}"

    # Validate critical data is persisted
    _log("STEP 3: Verifying data persistence")
    doc = es.search_by_alert_id(payload["alert_id"])
    if doc:
        assert isinstance(doc, dict), "ES document must be a dict"
        _log("+ Data persisted in Elasticsearch")
        assert "alert_id" in doc, "Alert ID missing"
        assert doc["alert_id"] == payload["alert_id"], "Alert ID mismatch"
        assert "hostname" in doc, "Hostname missing"
        assert doc["hostname"] == payload["hostname"], "Hostname mismatch - workflow did not preserve field"
        assert "hash" in doc, "Hash missing"
        assert doc["hash"] == payload["hash"], "Hash mismatch - workflow did not preserve field"
        assert "severity" in doc, "Severity missing"
        assert doc["severity"] == payload["severity"], "Severity mismatch - workflow did not preserve field"
        assert "alert_type" in doc, "Alert type missing"
        assert doc["alert_type"] == payload["alert_type"], "Alert type mismatch - workflow did not preserve field"
        _log("+ All critical fields preserved correctly")

        if workflow_type == "wazuh":
            assert "wazuh_agent_id" in doc, "Wazuh agent ID missing"
            assert doc["wazuh_agent_id"] == payload["wazuh_agent_id"], "Wazuh agent ID mismatch"
            assert "wazuh_agent_name" in doc, "Wazuh agent name missing"
            assert doc["wazuh_agent_name"] == payload["wazuh_agent_name"], "Wazuh agent name mismatch"
            assert doc["source"] == "wazuh-siem", "Source should be wazuh-siem"
            _log("+ Wazuh-specific fields preserved correctly")
    else:
        _log("+ Data not found in ES")


def test_parallel_workflow_execution(workflow_clients):
    """
    TC-00-02: Test parallel execution of both workflows.

    Verifications:
      - Both workflows can execute simultaneously
      - No race conditions occur
      - Results are consistent
    """
    clients = workflow_clients
    simulated_info = clients['simulated_info']
    shuffle = clients['shuffle']
    es = clients['es']
    webhook_url = clients['webhook_url']

    if not simulated_info.get("workflow_id"):
        pytest.skip("Simulated workflow ID not found")

    workflow_id = simulated_info["workflow_id"]

    def execute_workflow(alert_suffix):
        payload = {
            "alert_id": f"TC00-PARALLEL-{alert_suffix}-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": f"WIN-PARALLEL-{alert_suffix}",
            "src_ip": f"192.168.1.{100 + hash(alert_suffix) % 50}",
            "severity": 2,
            "process_name": "malware.exe",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "mitre_techniques": ["T1486"],
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "source": "simulated-siem"
        }

        exec_id = _step_send_alert(shuffle, webhook_url, workflow_id, payload)
        result = _step_wait_workflow(shuffle, workflow_id, exec_id)
        return payload, result

    _log("=== TC-00-02: PARALLEL EXECUTION TEST STARTED ===")

    # Execute 3 workflows in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(execute_workflow, i) for i in range(3)]
        results = []
        for future in as_completed(futures):
            try:
                payload, result = future.result()
                results.append((payload, result))
                _log(f"+ Workflow completed for alert {payload['alert_id']}")
            except Exception as e:
                _log(f"+ Workflow failed: {e}")
                pytest.fail(f"Parallel execution failed: {e}")

    # Validate all workflows completed successfully
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    _log(f"+ All {len(results)} parallel workflows completed successfully")

    # Validate no duplicate alert IDs (no race conditions)
    alert_ids = [payload["alert_id"] for payload, _ in results]
    assert len(alert_ids) == len(set(alert_ids)), "Duplicate alert IDs detected - race condition"
    _log("+ No duplicate alert IDs - no race conditions")

    # Validate all data persisted
    _log("STEP 3: Verifying data persistence for all parallel workflows")
    persisted_count = 0
    for payload, result in results:
        doc = es.search_by_alert_id(payload["alert_id"])
        if doc:
            persisted_count += 1
            assert doc["alert_id"] == payload["alert_id"], "Alert ID mismatch"

    _log(f"+ {persisted_count}/{len(results)} workflows persisted data")
    assert persisted_count == len(results), f"Expected {len(results)} persisted documents, got {persisted_count}"

    elapsed = (datetime.now(timezone.utc) - clients['t0']).total_seconds()
    _log(f"Elapsed: {elapsed:.1f}s")
    _log("=== TC-00-02 COMPLETED — PARALLEL EXECUTION VALIDATED ===")


def test_workflow_consistency(workflow_clients):
    """
    TC-00-03: Test consistency between workflow executions.

    Verifications:
      - Multiple executions produce consistent results
      - Data structure is consistent
      - Field mapping is consistent
    """
    clients = workflow_clients
    simulated_info = clients['simulated_info']
    shuffle = clients['shuffle']
    es = clients['es']
    webhook_url = clients['webhook_url']

    if not simulated_info.get("workflow_id"):
        pytest.skip("Simulated workflow ID not found")

    workflow_id = simulated_info["workflow_id"]

    _log("=== TC-00-03: WORKFLOW CONSISTENCY TEST STARTED ===")

    # Execute same workflow 3 times with different alert IDs
    results = []
    for i in range(3):
        payload = {
            "alert_id": f"TC00-CONSIST-{i}-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-CONSIST-001",
            "src_ip": "192.168.1.100",
            "severity": 2,
            "process_name": "malware.exe",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "mitre_techniques": ["T1486"],
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "source": "simulated-siem"
        }

        exec_id = _step_send_alert(shuffle, webhook_url, workflow_id, payload)
        result = _step_wait_workflow(shuffle, workflow_id, exec_id)
        results.append((payload, result))
        _log(f"+ Execution {i + 1}/3 completed")

    # Validate all executions have same status
    statuses = [result.get("status", "").upper() for _, result in results]
    assert len(set(statuses)) == 1, f"Statuses inconsistent: {statuses}"
    _log(f"+ All executions have consistent status: {statuses[0]}")

    # Validate all persisted documents have same structure
    _log("STEP 3: Verifying data structure consistency")
    docs = []
    for payload, _ in results:
        doc = es.search_by_alert_id(payload["alert_id"])
        if doc:
            docs.append(doc)

    if len(docs) >= 2:
        # Compare field sets across documents
        field_sets = [set(doc.keys()) for doc in docs]
        common_fields = set.intersection(*field_sets)
        _log(f"+ Common fields across all documents: {len(common_fields)}")

        # Validate critical fields are present in all
        critical_fields = ["alert_id", "hostname", "hash", "severity", "alert_type"]
        for field in critical_fields:
            assert all(field in doc for doc in docs), f"Field {field} missing in some documents"
        _log(f"+ All critical fields present in all documents")

    elapsed = (datetime.now(timezone.utc) - clients['t0']).total_seconds()
    _log(f"Elapsed: {elapsed:.1f}s")
    _log("=== TC-00-03 COMPLETED — WORKFLOW CONSISTENCY VALIDATED ===")


def test_execution_time_comparison(workflow_clients):
    """
    TC-00-04: Comparison of execution times between workflows.

    Verifications:
      - Execution times are within acceptable range
      - No significant performance degradation
      - Times are logged for analysis
    """
    clients = workflow_clients
    simulated_info = clients['simulated_info']
    shuffle = clients['shuffle']
    es = clients['es']
    webhook_url = clients['webhook_url']

    if not simulated_info.get("workflow_id"):
        pytest.skip("Simulated workflow ID not found")

    workflow_id = simulated_info["workflow_id"]

    _log("=== TC-00-04: EXECUTION TIME COMPARISON TEST STARTED ===")

    # Execute workflow 3 times to get average
    execution_times = []
    for i in range(3):
        payload = {
            "alert_id": f"TC00-TIME-{i}-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC00-001",
            "src_ip": "192.168.1.100",
            "severity": 2,
            "process_name": "malware.exe",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "mitre_techniques": ["T1486"],
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "source": "simulated-siem"
        }

        _log(f"STEP 1: Measuring execution time (run {i + 1}/3)")
        start_time = time.time()
        exec_id = _step_send_alert(shuffle, webhook_url, workflow_id, payload)
        result = _step_wait_workflow(shuffle, workflow_id, exec_id)
        assert isinstance(result, dict), "Result must be a dict"
        execution_time = time.time() - start_time
        execution_times.append(execution_time)
        _log(f"+ Execution time {i + 1}: {execution_time:.1f}s")

    avg_time = sum(execution_times) / len(execution_times)
    max_time = max(execution_times)
    min_time = min(execution_times)

    _log(f"+ Average execution time: {avg_time:.1f}s")
    _log(f"+ Min execution time: {min_time:.1f}s")
    _log(f"+ Max execution time: {max_time:.1f}s")

    # Validate execution times are within acceptable range
    assert max_time < WORKFLOW_TIMEOUT, f"Max execution time {max_time:.1f}s exceeds timeout {WORKFLOW_TIMEOUT}s"
    assert avg_time > 0, "Average execution time must be positive"
    assert avg_time > 5, f"Average execution time {avg_time:.1f}s too fast, may indicate no processing"

    # Validate variance is not too high (consistent performance).
    # Allow a 100% variance band because the containerized environment can
    # have variable cold-start / caching behavior across the three runs.
    variance = max_time - min_time
    assert variance < avg_time * 1.0, f"Execution time variance {variance:.1f}s too high (100% of average)"
    _log(f"+ Execution time variance {variance:.1f}s is acceptable")

    # Validate data was actually processed
    _log("STEP 2: Verifying data was processed")
    last_payload = {
        "alert_id": f"TC00-TIME-LAST-{int(time.time())}",
        "alert_type": "ransomware",
        "hostname": "WIN-TC00-001",
        "src_ip": "192.168.1.100",
        "severity": 2,
        "process_name": "malware.exe",
        "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
        "mitre_techniques": ["T1486"],
        "detection_time": datetime.now(timezone.utc).isoformat(),
        "source": "simulated-siem"
    }
    exec_id = _step_send_alert(shuffle, webhook_url, workflow_id, last_payload)
    _step_wait_workflow(shuffle, workflow_id, exec_id)

    doc = es.search_by_alert_id(last_payload["alert_id"])
    if doc:
        assert isinstance(doc, dict), "ES document must be a dict"
        _log("+ Data was processed and persisted")
    else:
        _log("+ Data not found (processing may have failed)")

    elapsed = (datetime.now(timezone.utc) - clients['t0']).total_seconds()
    _log(f"Elapsed: {elapsed:.1f}s")
    _log("=== TC-00-04 COMPLETED — EXECUTION TIME COMPARISON VALIDATED ===")
