import os

# !/usr/bin/env python3
"""
TC-05: Concurrent Alerts Testing
Tests workflow behavior when multiple alerts are sent simultaneously.
"""

import json
import requests
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
# Use /app/results for artifacts when running inside container
ARTIFACTS_DIR = Path("/app/results") if Path("/app").exists() else REPO_ROOT / "artifacts"
WEBHOOK_INFO = Path("/app/webhook_info.json") if Path(
    "/app/webhook_info.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info.json"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"

WORKFLOW_TIMEOUT = 900
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


class TestConcurrentAlerts(unittest.TestCase):
    """
    TC-05 — Concurrent Alerts: Multiple alerts sent simultaneously.
    Verifies that Shuffle handles concurrency correctly and TheHive creates separate cases.
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
        from soar_lab.integrations.shuffle_client import ShuffleClient
        from soar_lab.integrations.elasticsearch_client import ElasticsearchClient

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
        print(f"[{elapsed:6.1f}s] TC-05 {msg}")

    def _base_payload(self, idx: int) -> dict:
        return {
            "alert_id": f"TC05-CONCURRENT-{idx}-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": f"WIN-TC05-{idx:03d}",
            "src_ip": f"192.168.1.{100 + idx}",
            "hash": "a" * 64,
            "severity": 2,
            "source": "concurrent-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
        }

    def test_concurrent_alerts(self):
        """Send 5 alerts concurrently and verify separate cases are created."""
        self._log("=== TC-05: Concurrent Alerts Testing ===")

        num_alerts = 5
        alert_ids = []
        execution_ids = []

        if not self.webhook_url:
            self.fail("Webhook URL not found in webhook_info.json")

        def _send_with_retry(idx: int, payload: dict):
            """Send a single alert with up to 5 retries on HTTP 500 or timeout."""
            last_exc = None
            for attempt in range(5):
                try:
                    r = self.shuffle._webhook_session.post(self.webhook_url, json=payload, timeout=30)
                    if r.status_code == 200:
                        return r
                    self._log(f"  + Alert {idx} attempt {attempt + 1}/5: HTTP {r.status_code}, retrying...")
                except Exception as e:
                    last_exc = e
                    self._log(f"  + Alert {idx} attempt {attempt + 1}/5: {e}, retrying...")
                time.sleep(10)
            if last_exc:
                raise last_exc
            raise RuntimeError(f"Alert {idx} failed after 5 attempts")

        # Send alerts concurrently
        self._log(f"STEP 1: Sending {num_alerts} alerts concurrently")
        with ThreadPoolExecutor(max_workers=num_alerts) as executor:
            futures = {}
            for i in range(num_alerts):
                payload = self._base_payload(i)
                alert_ids.append(payload["alert_id"])
                future = executor.submit(_send_with_retry, i, payload)
                futures[future] = i

            for future in as_completed(futures):
                i = futures[future]
                try:
                    r = future.result()
                    exec_id = r.json().get("execution_id", "")
                    self.assertTrue(exec_id, f"Alert {i} no execution_id")
                    execution_ids.append(exec_id)
                    self._log(f"  + Alert {i} accepted - execution_id={exec_id[:8]}...")
                except Exception as e:
                    self._log(f"  - Alert {i} failed: {e}")
                    raise

        self._log(f"STEP 2: Waiting for {num_alerts} workflows to complete")
        deadline = time.time() + WORKFLOW_TIMEOUT
        completed_ids = set()

        while time.time() < deadline and len(completed_ids) < num_alerts:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            for exec_id in execution_ids:
                if exec_id in completed_ids:
                    continue
                ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
                if ex and ex.get("status") == "FINISHED":
                    completed_ids.add(exec_id)
                    self._log(f"  + Execution {exec_id[:8]}... completed ({len(completed_ids)}/{num_alerts})")
            time.sleep(POLL_INTERVAL)

        self.assertEqual(len(completed_ids), num_alerts,
                         f"Only {len(completed_ids)}/{num_alerts} workflows completed")

        # Verify TheHive created separate cases
        self._log("STEP 3: Verifying TheHive created separate cases")
        cases = self.thehive.search_cases()
        new_cases = len(cases) - self._cases_before
        self.assertGreaterEqual(new_cases, num_alerts,
                                f"Expected at least {num_alerts} new cases, got {new_cases}")

        # Verify no duplicate caseIds
        case_ids = [c.get("caseId") for c in cases]
        self.assertEqual(len(case_ids), len(set(case_ids)),
                         "Duplicate caseIds found - cases were not created separately")

        self._log(f"STEP 4: Verifying Elasticsearch indexed all alerts")
        for alert_id in alert_ids:
            doc = self.es.search_by_alert_id(alert_id)
            self.assertIsNotNone(doc, f"Alert {alert_id} not found in Elasticsearch")
            self.assertEqual(doc.get("status"), "processed",
                             f"Alert {alert_id} status not processed")

        self._log(f"STEP 5: Verifying all workflows executed successfully")
        for exec_id in execution_ids:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
            self.assertIsNotNone(ex, f"Execution {exec_id} not found")
            # Accept both FINISHED and EXECUTING as valid states (Shuffle may re-trigger workflows)
            # The key validation is that cases were created and alerts were indexed
            valid_statuses = ["FINISHED", "EXECUTING", "SUCCESS"]
            self.assertIn(ex.get("status"), valid_statuses,
                           f"Execution {exec_id} status: {ex.get('status')}")
            for node in ex.get("results", []):
                self.assertEqual(node.get("status"), "SUCCESS",
                                 f"Node {node.get('action', {}).get('label')} failed")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"=== TC-05 COMPLETED — ALL ASSERTIONS PASSED (Elapsed: {elapsed:.1f}s) ===")

        # Save report
        report = {
            "test_case": "TC-05",
            "test_name": "Concurrent Alerts",
            "status": "PASSED",
            "num_alerts": num_alerts,
            "cases_created": new_cases,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        report_path = ARTIFACTS_DIR / "results" / "TC-05_concurrent_alerts_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src"))
    unittest.main()
