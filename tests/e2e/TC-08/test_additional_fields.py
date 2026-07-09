import os

# !/usr/bin/env python3
"""
TC-08: Additional Fields Testing
Tests workflow behavior with additional fields (mitre_techniques, process_name).
"""

import json
import requests
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
# Use /app/results for artifacts when running inside container
ARTIFACTS_DIR = Path("/app/results") if Path("/app").exists() else REPO_ROOT / "artifacts"
WEBHOOK_INFO = Path("/app/webhook_info.json") if Path(
    "/app/webhook_info.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info.json"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"

WORKFLOW_TIMEOUT = 900  # seconds (increased from 300 to handle complex workflows)
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


class TestAdditionalFields(unittest.TestCase):
    """
    TC-08 — Additional Fields: Alert with mitre_techniques and process_name.
    Verifies that additional fields are preserved and used in the workflow.
    """

    def setUp(self):
        self.t0 = datetime.now(timezone.utc)
        (ARTIFACTS_DIR / "results").mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

        env = _load_env()

        # Skip if required API keys are not configured
        if not env.get("THEHIVE_API_KEY"):
            self.skipTest("THEHIVE_API_KEY not configured in .env.full")

        info = json.loads(WEBHOOK_INFO.read_text()) if WEBHOOK_INFO.exists() else {}
        self.webhook_url = info.get("webhook_url", "")
        self.workflow_id = info.get("workflow_id", "")

        if not self.workflow_id:
            self.skipTest("Workflow ID not found. Run init_shuffle_webhook.py first.")

        # Import clients
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from soar_lab.integrations.thehive_client import TheHiveClient
        from soar_lab.integrations.elasticsearch_client import ElasticsearchClient
        from soar_lab.integrations.shuffle_client import ShuffleClient

        shuffle_url = env.get("SHUFFLE_URL", "http://soar_shuffle_backend:5001")
        self.shuffle = ShuffleClient(base_url=shuffle_url, api_key=(
                    os.environ.get("SHUFFLE_DEFAULT_APIKEY") or env.get("SHUFFLE_DEFAULT_APIKEY") or env.get(
                "SHUFFLE_API_KEY", "placeholder")),
                                     verify_ssl=False)

        self.thehive = TheHiveClient(
            base_url=env.get("THEHIVE_URL", "http://thehive:9000"),
            api_key=env.get("THEHIVE_API_KEY", ""),
            verify_ssl=False
        )
        self.es = ElasticsearchClient(
            base_url=env.get("ES_URL", "http://elasticsearch:9200"),
            index="soar-alerts"
        )

        self._cases_before = len(self.thehive.search_cases())

    def _log(self, msg: str):
        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        print(f"[{elapsed:6.1f}s] TC-08 {msg}")

    def test_additional_fields(self):
        """Send alert with additional fields and verify they are preserved."""
        self._log("=== TC-08: Additional Fields Testing ===")

        mitre_techniques = ["T1486", "T1059", "T1068"]  # Ransomware techniques
        process_name = "malware.exe"

        payload = {
            "alert_id": f"TC08-ADDITIONAL-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC08-001",
            "src_ip": "192.168.1.210",
            "hash": "d" * 64,
            "severity": 2,
            "source": "additional-fields-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": mitre_techniques,
            "process_name": process_name,
        }

        if not self.webhook_url:
            self.fail("Webhook URL not found in webhook_info.json")
        self._log("STEP 1: Sending alert with additional fields")
        r = self.shuffle._webhook_session.post(
            self.webhook_url,
            json=payload,
            timeout=30
        )
        self.assertEqual(r.status_code, 200,
                         f"Alert rejected: HTTP {r.status_code}")
        exec_id = r.json().get("execution_id", "")
        self.assertTrue(exec_id, "No execution_id returned")
        self._log(f"  + Alert accepted - execution_id={exec_id}")

        # Wait for workflow completion
        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)

        self.assertIsNotNone(ex, f"Execution {exec_id} not found in Shuffle")
        self.assertEqual(ex.get("status"), "FINISHED",
                         f"Workflow status: {ex.get('status')}")
        self._log("  + Workflow completed successfully")

        # Verify TheHive case
        self._log("STEP 3: Verifying TheHive case")
        cases = self.thehive.search_cases()
        self.assertGreater(len(cases), self._cases_before,
                           "No new TheHive case was created")
        last = max(cases, key=lambda c: c.get("caseId", 0))
        self._log(f"  + Case #{last.get('caseId')} created")

        # Verify Elasticsearch preserved additional fields
        self._log("STEP 4: Verifying Elasticsearch preserved additional fields")
        doc = self.es.search_by_alert_id(payload["alert_id"])
        self.assertIsNotNone(doc, "Alert not found in Elasticsearch")

        # Verify mitre_techniques (may be JSON string or list)
        es_mitre = doc.get("mitre_techniques", [])
        if isinstance(es_mitre, str):
            import json as _json_mod
            es_mitre = _json_mod.loads(es_mitre)
        self.assertEqual(sorted(es_mitre), sorted(mitre_techniques),
                         f"MITRE techniques mismatch: {es_mitre} vs {mitre_techniques}")
        self._log(f"  + MITRE techniques preserved: {es_mitre}")

        # Verify process_name
        es_process = doc.get("process_name", "")
        self.assertEqual(es_process, process_name,
                         f"Process name mismatch: {es_process} vs {process_name}")
        self._log(f"  + Process name preserved: {es_process}")

        # Verify workflow nodes
        self._log("STEP 5: Verifying all workflow nodes succeeded")
        for node in ex.get("results", []):
            label = node.get("action", {}).get("label", "?")
            status = node.get("status", "?")
            self.assertEqual(status, "SUCCESS",
                             f"Node {label} failed with status {status}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"=== TC-08 COMPLETED — ALL ASSERTIONS PASSED (Elapsed: {elapsed:.1f}s) ===")

        # Save report
        report = {
            "test_case": "TC-08",
            "test_name": "Additional Fields",
            "status": "PASSED",
            "alert_id": payload["alert_id"],
            "mitre_techniques": mitre_techniques,
            "process_name": process_name,
            "fields_preserved": True,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        report_path = ARTIFACTS_DIR / "results" / "TC-08_additional_fields_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src"))
    unittest.main()
