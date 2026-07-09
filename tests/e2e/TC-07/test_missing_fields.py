import os

# !/usr/bin/env python3
"""
TC-07: Missing Fields Testing
Tests workflow behavior when hash or IP fields are empty or invalid.
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


class TestMissingFields(unittest.TestCase):
    """
    TC-07 — Missing Fields: Alert with empty/invalid hash and IP.
    Verifies workflow handles missing fields gracefully.
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
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
        }

        if not self.webhook_url:
            self.fail("Webhook URL not found in webhook_info.json")
        self._log("STEP 1: Sending alert with empty hash and IP")
        r = self.shuffle._webhook_session.post(
            self.webhook_url,
            json=payload,
            timeout=30
        )
        # Workflow should still accept the alert even with empty fields
        self.assertLess(r.status_code, 500,
                        f"Alert caused server error: HTTP {r.status_code}")
        if r.status_code == 200:
            exec_id = r.json().get("execution_id", "")
            self._log(f"  + Alert accepted - execution_id={exec_id}")
        else:
            self._log(f"  + Alert rejected with HTTP {r.status_code} (acceptable)")
            return  # Test passes if alert is rejected gracefully

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
        self._log(f"  + Workflow status: {ex.get('status')}")

        # Verify TheHive case was still created
        self._log("STEP 3: Verifying TheHive case creation")
        cases = self.thehive.search_cases()
        new_cases = len(cases) - self._cases_before
        if new_cases > 0:
            last = max(cases, key=lambda c: c.get("caseId", 0))
            self._log(f"  + Case #{last.get('caseId')} created despite missing fields")

            # Verify observables - should be minimal or skipped
            case_id = last.get("id", last.get("_id", ""))
            if case_id:
                obs = self.thehive.get_case_observables(case_id)
                self._log(f"  + {len(obs)} observable(s) attached (expected 0 or minimal)")
        else:
            self._log("  + No case created (acceptable for missing fields)")

        # Verify Elasticsearch
        self._log("STEP 4: Verifying Elasticsearch indexing")
        doc = self.es.search_by_alert_id(payload["alert_id"])
        if doc:
            self._log(f"  + Alert indexed in Elasticsearch with empty fields")
            self.assertEqual(doc.get("hash"), "", "Hash should be empty")
            self.assertEqual(doc.get("src_ip"), "", "IP should be empty")
        else:
            self._log("  + Alert not indexed (acceptable)")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"=== TC-07 COMPLETED — WORKFLOW HANDLED MISSING FIELDS (Elapsed: {elapsed:.1f}s) ===")

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
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        report_path = ARTIFACTS_DIR / "results" / "TC-07_missing_fields_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src"))
    unittest.main()
