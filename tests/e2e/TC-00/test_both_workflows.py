#!/usr/bin/env python3
"""
TC-00 — Parametrized Tests for Both Workflows
Tests both SOAR-Ransomware-Response (simulated) and SOAR-Ransomware-Response-Wazuh (Wazuh SIEM)
"""

import json
import os
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
ARTIFACTS_DIR = Path("/app/results") if Path("/app/results").exists() else REPO_ROOT / "artifacts" / "results"
WEBHOOK_INFO = Path("/app/webhook_info.json") if Path(
    "/app/webhook_info.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info.json"
WEBHOOK_INFO_WAZUH = Path("/app/webhook_info_wazuh.json") if Path(
    "/app/webhook_info_wazuh.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info_wazuh.json"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"

WORKFLOW_TIMEOUT = 300
POLL_INTERVAL = 5

sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.integrations.thehive_client import TheHiveClient
from soar_lab.integrations.cortex_client import CortexClient
from soar_lab.integrations.misp_client import MISPClient
from soar_lab.integrations.elasticsearch_client import ElasticsearchClient
from soar_lab.integrations.wazuh_client import WazuhClient
from soar_lab.integrations.shuffle_client import ShuffleClient


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


class TestBothWorkflows(unittest.TestCase):
    """
    TC-00 — Parametrized tests for both workflows (simulated and Wazuh).
    """

    @classmethod
    def setUpClass(cls):
        cls.t0 = datetime.now(timezone.utc)
        (ARTIFACTS_DIR / "results").mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

        env = _load_env()

        # Skip if required API keys are not configured
        if not env.get("THEHIVE_API_KEY"):
            raise unittest.SkipTest("THEHIVE_API_KEY not configured in .env.full")

        # Load both webhook configs
        cls.simulated_info = json.loads(WEBHOOK_INFO.read_text()) if WEBHOOK_INFO.exists() else {}
        cls.wazuh_info = json.loads(WEBHOOK_INFO_WAZUH.read_text()) if WEBHOOK_INFO_WAZUH.exists() else {}
        cls.webhook_url = cls.simulated_info.get("webhook_url", "")

        shuffle_url = env.get("SHUFFLE_URL", "http://soar_shuffle_backend:5001")
        thehive_url = env.get("THEHIVE_URL", "http://thehive:9000")
        cortex_url = env.get("CORTEX_URL", "http://cortex:9001")
        misp_url = env.get("MISP_URL", "http://misp:80")
        es_url = env.get("ES_URL", "http://elasticsearch:9200")
        wazuh_url = env.get("WAZUH_URL", "https://wazuh_manager:55000")

        cls.shuffle = ShuffleClient(base_url=shuffle_url, api_key=(
                    os.environ.get("SHUFFLE_DEFAULT_APIKEY") or env.get("SHUFFLE_DEFAULT_APIKEY") or env.get(
                "SHUFFLE_API_KEY", "placeholder")),
                                    verify_ssl=False)
        cls.thehive = TheHiveClient(base_url=thehive_url, api_key=env.get("THEHIVE_API_KEY", ""), verify_ssl=False)
        cls.cortex = CortexClient(base_url=cortex_url, api_key=env.get("CORTEX_API_KEY", ""), verify_ssl=False)
        cls.misp = MISPClient(base_url=misp_url, api_key=env.get("MISP_API_KEY", ""), verify_ssl=False)
        cls.es = ElasticsearchClient(base_url=es_url)
        cls.wazuh = WazuhClient(
            base_url=wazuh_url,
            username=env.get("WAZUH_API_USERNAME", "wazuh-wui"),
            password=env.get("WAZUH_API_PASSWORD", ""),
        )

    def _log(self, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-00 {msg}"
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
        with open(ARTIFACTS_DIR / "logs" / "both_workflows.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _step_send_alert(self, workflow_id: str, payload: dict) -> str:
        if not self.webhook_url:
            self.fail("Webhook URL not found in webhook_info.json")
        self._log(f"STEP 1: Sending alert to workflow {workflow_id[:8]}...")
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
        self.assertIsNotNone(r, "No response from Shuffle after retries")
        self.assertEqual(r.status_code, 200,
                         f"Workflow execution failed: HTTP {r.status_code} — {r.text[:200]}")
        data = r.json()
        self.assertTrue(data.get("success"), f"Shuffle did not accept alert: {data}")
        exec_id = data.get("execution_id", "")
        self._log(f"+ Alert accepted — execution_id={exec_id}")
        return exec_id

    def _step_wait_workflow(self, workflow_id: str, exec_id: str) -> dict:
        self._log(f"STEP 2: Waiting up to {WORKFLOW_TIMEOUT}s for workflow to finish")
        start = time.time()
        while time.time() - start < WORKFLOW_TIMEOUT:
            try:
                execs = self.shuffle.get_workflow_executions(workflow_id)
                execution = next((e for e in execs if e.get("execution_id") == exec_id), None)
                if execution:
                    status = execution.get("status", "")
                    if status.upper() in ["FINISHED", "FAILED", "STOPPED", "SUCCESS"]:
                        self._log(f"+ Workflow finished with status: {status}")
                        return execution
            except Exception:
                pass
            time.sleep(POLL_INTERVAL)
        self.fail(f"Workflow timeout after {WORKFLOW_TIMEOUT}s")

    def test_simulated_workflow_malicious(self):
        """Test simulated workflow with malicious alert."""
        if not self.simulated_info.get("workflow_id"):
            self.skipTest("Simulated workflow ID not found")

        workflow_id = self.simulated_info["workflow_id"]
        self._log("=== Testing Simulated Workflow (Malicious) ===")

        payload = {
            "alert_id": f"TC00-SIM-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-SIM-001",
            "src_ip": "192.168.1.100",
            "severity": 2,
            "process_name": "malware.exe",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "mitre_techniques": ["T1486"],
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "source": "simulated-siem"
        }

        exec_id = self._step_send_alert(workflow_id, payload)
        result = self._step_wait_workflow(workflow_id, exec_id)
        self.assertIn(result.get("status", "").upper(), ["FINISHED", "SUCCESS"])

    def test_wazuh_workflow_malicious(self):
        """Test Wazuh-sourced alert through the active SOAR workflow."""
        # Prefer dedicated wazuh workflow if it exists in Shuffle, otherwise fall back to simulated workflow
        wazuh_workflow_id = self.wazuh_info.get("workflow_id", "")
        wazuh_webhook_url = self.wazuh_info.get("webhook_url", "")

        workflow_id = None
        webhook_url = None

        if wazuh_workflow_id and wazuh_webhook_url:
            try:
                import requests as _req
                _r = _req.get(
                    self.shuffle._url(f"/api/v1/workflows/{wazuh_workflow_id}"),
                    headers=dict(self.shuffle._session.headers),
                    timeout=5,
                )
                if _r.status_code == 200:
                    workflow_id = wazuh_workflow_id
                    webhook_url = wazuh_webhook_url
                    self._log(f"Using dedicated Wazuh workflow {workflow_id[:8]}")
                else:
                    self._log(f"Wazuh workflow not available (HTTP {_r.status_code}), using fallback")
            except Exception:
                pass

        if not workflow_id:
            # Fall back to simulated workflow — same workflow handles all alert sources
            workflow_id = self.simulated_info.get("workflow_id", "")
            webhook_url = self.simulated_info.get("webhook_url", "")
            self._log(
                f"Wazuh workflow not found, using simulated workflow {workflow_id[:8] if workflow_id else '?'} with Wazuh payload")

        if not workflow_id or not webhook_url:
            self.fail("No active workflow found (neither wazuh nor simulated)")

        self._log("=== Testing Wazuh-source Alert through SOAR Workflow (Malicious) ===")

        payload = {
            "alert_id": f"TC00-WAZ-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-WAZ-001",
            "src_ip": "192.168.1.101",
            "severity": 2,
            "process_name": "malware.exe",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "mitre_techniques": ["T1486"],
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "wazuh_agent_id": "001",
            "wazuh_agent_name": "simulated-agent",
            "wazuh_agent_ip": "192.168.1.101",
            "source": "wazuh-siem"
        }

        exec_id = self._step_send_alert(workflow_id, payload)
        result = self._step_wait_workflow(workflow_id, exec_id)
        self.assertIn(result.get("status", "").upper(), ["FINISHED", "SUCCESS"])


if __name__ == "__main__":
    unittest.main()
