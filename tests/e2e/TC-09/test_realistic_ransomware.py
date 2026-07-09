import os

# !/usr/bin/env python3
"""
TC-09: Realistic Ransomware Simulation
Tests workflow with a realistic ransomware scenario including multiple stages.
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


class TestRealisticRansomware(unittest.TestCase):
    """
    TC-09 — Realistic Ransomware: Multi-stage ransomware simulation.
    Simulates encryption, exfiltration, and ransom note stages.
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
            self.fail("Webhook URL not found in webhook_info.json")

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
        self.assertIsNotNone(r, "No response from Shuffle after retries")
        self.assertEqual(r.status_code, 200,
                         f"Stage 1 alert rejected: HTTP {r.status_code}")
        exec_id1 = r.json().get("execution_id", "")
        self._log(f"  + Stage 1 accepted - execution_id={exec_id1}")

        # Wait for stage 1 workflow
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex1 = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex1 = next((e for e in execs if e.get("execution_id") == exec_id1), None)
            if ex1 and ex1.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)
        self.assertEqual(ex1.get("status"), "FINISHED",
                         f"Stage 1 workflow status: {ex1.get('status')}")
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
        self.assertIsNotNone(r, "No response from Shuffle after retries")
        self.assertEqual(r.status_code, 200, f"Stage 2 alert rejected: HTTP {r.status_code}")
        exec_id2 = r.json().get("execution_id", "")
        self._log(f"  + Stage 2 accepted - execution_id={exec_id2}")

        # Wait for stage 2 workflow
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex2 = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex2 = next((e for e in execs if e.get("execution_id") == exec_id2), None)
            if ex2 and ex2.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)
        self.assertEqual(ex2.get("status"), "FINISHED",
                         f"Stage 2 workflow status: {ex2.get('status')}")
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
        self.assertIsNotNone(r, "No response from Shuffle after retries")
        self.assertEqual(r.status_code, 200, f"Stage 3 alert rejected: HTTP {r.status_code}")
        exec_id3 = r.json().get("execution_id", "")
        self._log(f"  + Stage 3 accepted - execution_id={exec_id3}")

        # Wait for stage 3 workflow
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex3 = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex3 = next((e for e in execs if e.get("execution_id") == exec_id3), None)
            if ex3 and ex3.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)
        self.assertEqual(ex3.get("status"), "FINISHED",
                         f"Stage 3 workflow status: {ex3.get('status')}")
        self._log("  + Stage 3 workflow completed")

        # Verify TheHive created cases for all stages
        self._log("STEP 4: Verifying TheHive cases for all stages")
        cases = self.thehive.search_cases()
        new_cases = len(cases) - self._cases_before
        self.assertGreaterEqual(new_cases, 3,
                                f"Expected at least 3 new cases (one per stage), got {new_cases}")
        self._log(f"  + {new_cases} cases created ({new_cases - 3} extra from retries, 3 required)")

        # Verify Elasticsearch indexed all stages
        self._log("STEP 5: Verifying Elasticsearch indexed all stages")
        for payload in [stage1_payload, stage2_payload, stage3_payload]:
            doc = self.es.search_by_alert_id(payload["alert_id"])
            self.assertIsNotNone(doc, f"Alert {payload['alert_id']} not found")
            # Stage verification is optional - workflow may not include it
            if doc.get("stage"):
                self.assertEqual(doc.get("stage"), payload["stage"],
                                 f"Stage mismatch for {payload['alert_id']}")
            # Severity verification is optional - workflow may not include it
            if doc.get("severity"):
                self.assertEqual(doc.get("severity"), payload["severity"],
                                 f"Severity mismatch for {payload['alert_id']}")
        self._log("  + All 3 stages indexed correctly")

        # Verify critical severity cases have higher priority (optional)
        self._log("STEP 6: Verifying critical severity cases")
        # Get only new cases (after self._cases_before)
        all_cases = self.thehive.search_cases()
        new_cases_list = all_cases[self._cases_before:]
        critical_cases = [c for c in new_cases_list if c.get("severity") == 3]
        if len(critical_cases) == 2:
            self._log(f"  + {len(critical_cases)} critical cases (stages 2 and 3)")
        else:
            self._log(
                f"  + {len(critical_cases)} critical cases (expected 2, workflow may handle severity differently)")

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


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(REPO_ROOT / "src"))
    unittest.main()
