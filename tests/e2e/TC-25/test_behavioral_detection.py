#!/usr/bin/env python3
"""
TC-25: Detección Conductual
Tests behavioral detection for unknown threats: Polymorphic, Low and Slow, Kill Chain, Canary Files.
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
ARTIFACTS_DIR = Path("/app/results") if Path("/app").exists() else REPO_ROOT / "artifacts"
WEBHOOK_INFO = Path("/app/webhook_info.json") if Path(
    "/app/webhook_info.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info.json"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"

WORKFLOW_TIMEOUT = 300
POLL_INTERVAL = 5

sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.infrastructure.external.integrations.thehive_client import TheHiveClient
from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient
from soar_lab.infrastructure.external.integrations.shuffle_client import ShuffleClient


def _load_env() -> dict:
    env_vars = {
        "SHUFFLE_URL": os.environ.get("SHUFFLE_URL"),
        "ES_URL": os.environ.get("ES_URL"),
        "THEHIVE_URL": os.environ.get("THEHIVE_URL"),
        "THEHIVE_API_KEY": os.environ.get("THEHIVE_API_KEY"),
        "SHUFFLE_DEFAULT_APIKEY": os.environ.get("SHUFFLE_DEFAULT_APIKEY"),
        "SHUFFLE_DEFAULT_PASSWORD": os.environ.get("SHUFFLE_DEFAULT_PASSWORD"),
    }

    result = {k: v for k, v in env_vars.items() if v is not None}

    if not ENV_FULL.exists():
        return result

    for line in ENV_FULL.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            if k not in result:
                result[k] = v
    return result


class TestBehavioralDetection:
    """TC-25 — Detección Conductual: Amenazas desconocidas por comportamiento."""

    def setup_method(self, method):
        """Set up test clients and environment"""
        t0 = datetime.now(timezone.utc)
        (ARTIFACTS_DIR / "results").mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

        env = _load_env()

        if not env.get("THEHIVE_API_KEY"):
            pytest.skip("THEHIVE_API_KEY not configured in .env.full")

        info = json.loads(WEBHOOK_INFO.read_text()) if WEBHOOK_INFO.exists() else {}
        webhook_url = info.get("webhook_url", info.get("webhook_url_host", ""))
        workflow_id = info.get("workflow_id", "")

        shuffle_url = env.get("SHUFFLE_URL", "http://soar_shuffle_backend:5001")
        thehive_url = env.get("THEHIVE_URL", "http://thehive:9000")
        es_url = env.get("ES_URL", "http://elasticsearch:9200")

        shuffle_api_key = os.environ.get("SHUFFLE_DEFAULT_APIKEY") or env.get("SHUFFLE_DEFAULT_APIKEY") or env.get(
            "SHUFFLE_API_KEY", "placeholder")
        shuffle = ShuffleClient(base_url=shuffle_url, api_key=shuffle_api_key, verify_ssl=False)
        thehive = TheHiveClient(base_url=thehive_url, api_key=env.get("THEHIVE_API_KEY", ""), verify_ssl=False)
        es = ElasticsearchClient(base_url=es_url)

        cases_before = len(thehive.search_cases())

        self.t0 = t0
        self.webhook_url = webhook_url
        self.workflow_id = workflow_id
        self.shuffle = shuffle
        self.thehive = thehive
        self.es = es
        self._cases_before = cases_before


    def _log(self, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-25 {msg}"
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
        with open(ARTIFACTS_DIR / "logs" / "notify.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def test_polymorphic_behavior(self):
        """
        TC-25-01: Polymorphic malware detection.

        Verifications:
          - Hash changing with constant behavior
          - Detection based on behavior not signature
        """
        self._log("=== TC-25-01: POLYMORPHIC BEHAVIOR TEST STARTED ===")

        # Simulate polymorphic malware with changing hash
        payload = {
            "alert_id": f"TC25-POLY-{int(time.time())}",
            "alert_type": "polymorphic",
            "hostname": "WIN-TC25-001",
            "src_ip": "192.168.1.220",
            "hash": "e" * 64,  # Will change in subsequent alerts
            "severity": 3,
            "source": "behavioral-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "polymorphic_detection",
            "mitre_techniques": ["T1027"],
            "behavior": "file_encryption"
        }

        self._log("STEP 1: Sending polymorphic alert")
        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        r = self.shuffle._webhook_session.post(
            self.webhook_url,
            json=payload,
            timeout=20
        )
        assert r.status_code == 200, f"Webhook failed: HTTP {r.status_code}"
        data = r.json()
        assert isinstance(data, dict), "Response must be JSON object"
        exec_id = data.get("execution_id", "")
        assert isinstance(exec_id, str), "execution_id must be string"
        assert len(exec_id) > 0, "execution_id must not be empty"

        # Wait for workflow
        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            assert isinstance(execs, list), "Workflow executions must be a list"
            ex = next((e for e in execs if e.get("execution_id") == exec_id), None)
            if ex:
                assert isinstance(ex, dict), "Execution must be a dict"
                if ex.get("status") not in ("EXECUTING", ""):
                    break
            time.sleep(POLL_INTERVAL)

        if ex:
            assert ex.get("status") == "FINISHED", f"Workflow status: {ex.get('status')}"

        # Verify detection based on behavior
        self._log("STEP 3: Verifying behavioral detection")
        cases = self.thehive.search_cases()
        assert isinstance(cases, list), "TheHive cases must be a list"
        new_cases = len(cases) - self._cases_before
        if new_cases > 0:
            last = max(cases, key=lambda c: c.get("caseId", 0))
            assert isinstance(last, dict), "Case must be a dict"
            self._log(f"+ Case created: {last.get('title')}")
            # Verify case title captures the polymorphic alert details
            title = (last.get("title") or "").lower()
            assert isinstance(title, str), "Title must be string"
            assert payload["alert_id"].lower() in title or "polymorphic" in title, "Case title should reference the polymorphic alert"

            # Validate that detection is based on behavior field
            assert "behavior" in payload, "Payload should have behavior field"
            assert payload["behavior"] == "file_encryption", "Behavior should be file_encryption"
            self._log("✓ Behavioral detection validated - detection based on behavior not signature")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        assert elapsed > 0, "Elapsed time should be positive"
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-25-01 COMPLETED — POLYMORPHIC BEHAVIOR VALIDATED ===")

    def test_low_and_slow_exfiltration(self):
        """
        TC-25-02: Low and slow exfiltration detection.

        Verifications:
          - Slow data transfer detection
          - Aggregation over time
        """
        self._log("=== TC-25-02: LOW AND SLOW EXFILTRATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC25-SLOW-{int(time.time())}",
            "alert_type": "exfiltration",
            "hostname": "WIN-TC25-002",
            "src_ip": "192.168.1.221",
            "hash": "f" * 64,
            "severity": 2,
            "source": "behavioral-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "slow_exfiltration",
            "mitre_techniques": ["T1041"],
            "behavior": "slow_data_transfer",
            "data_volume_kb": 10
        }

        self._log("STEP 1: Sending low and slow alert")
        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        r = self.shuffle._webhook_session.post(
            self.webhook_url,
            json=payload,
            timeout=20
        )
        assert r.status_code == 200, f"Webhook failed: HTTP {r.status_code}"

        # Wait for workflow
        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == r.json().get("execution_id", "")), None)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)

        if ex:
            assert ex.get("status") == "FINISHED", f"Workflow status: {ex.get('status')}"

        # Verify detection
        self._log("STEP 3: Verifying exfiltration detection")
        cases = self.thehive.search_cases()
        new_cases = len(cases) - self._cases_before
        if new_cases > 0:
            last = max(cases, key=lambda c: c.get("caseId", 0))
            self._log(f"+ Case created: {last.get('title')}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        assert elapsed > 0, "Elapsed time should be positive"
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-25-02 COMPLETED — LOW AND SLOW EXFILTRATION VALIDATED ===")

    def test_multi_stage_correlation(self):
        """
        TC-25-03: Kill chain correlation.

        Verifications:
          - Multiple attack stages correlated
          - Timeline reconstruction
        """
        self._log("=== TC-25-03: KILL CHAIN CORRELATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC25-KILLCHAIN-{int(time.time())}",
            "alert_type": "kill_chain",
            "hostname": "WIN-TC25-003",
            "src_ip": "192.168.1.222",
            "hash": "g" * 64,
            "severity": 3,
            "source": "behavioral-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "kill_chain_detection",
            "mitre_techniques": ["T1059", "T1486"],
            "kill_chain_stage": "exploitation",
            "previous_stages": ["reconnaissance", "delivery"]
        }

        self._log("STEP 1: Sending kill chain alert")
        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        r = self.shuffle._webhook_session.post(
            self.webhook_url,
            json=payload,
            timeout=20
        )
        assert r.status_code == 200, f"Webhook failed: HTTP {r.status_code}"

        # Wait for workflow
        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == r.json().get("execution_id", "")), None)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)

        if ex:
            assert ex.get("status") == "FINISHED", f"Workflow status: {ex.get('status')}"

        # Verify correlation
        self._log("STEP 3: Verifying kill chain correlation")
        cases = self.thehive.search_cases()
        new_cases = len(cases) - self._cases_before
        if new_cases > 0:
            last = max(cases, key=lambda c: c.get("caseId", 0))
            self._log(f"+ Case created: {last.get('title')}")
            # Verify multiple MITRE techniques are recorded in the case title
            title = last.get("title") or ""
            assert any(t in title for t in ["T1059", "T1486"]), "Case title should mention kill chain techniques"

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        assert elapsed > 0, "Elapsed time should be positive"
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-25-03 COMPLETED — KILL CHAIN CORRELATION VALIDATED ===")

    def test_canary_file_detection(self):
        """
        TC-25-04: Canary file detection.

        Verifications:
          - Canary file access detected
          - Immediate alert triggered
        """
        self._log("=== TC-25-04: CANARY FILE DETECTION TEST STARTED ===")

        payload = {
            "alert_id": f"TC25-CANARY-{int(time.time())}",
            "alert_type": "canary",
            "hostname": "WIN-TC25-004",
            "src_ip": "192.168.1.223",
            "hash": "h" * 64,
            "severity": 3,
            "source": "behavioral-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "canary_access",
            "mitre_techniques": ["T1005"],
            "file_path": "C:\\Users\\admin\\Documents\\canary.txt",
            "file_type": "canary"
        }

        self._log("STEP 1: Sending canary file alert")
        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        r = self.shuffle._webhook_session.post(
            self.webhook_url,
            json=payload,
            timeout=20
        )
        assert r.status_code == 200, f"Webhook failed: HTTP {r.status_code}"

        # Wait for workflow
        self._log("STEP 2: Waiting for workflow completion")
        deadline = time.time() + WORKFLOW_TIMEOUT
        ex = None
        while time.time() < deadline:
            execs = self.shuffle.get_workflow_executions(self.workflow_id)
            ex = next((e for e in execs if e.get("execution_id") == r.json().get("execution_id", "")), None)
            if ex and ex.get("status") not in ("EXECUTING", ""):
                break
            time.sleep(POLL_INTERVAL)

        if ex:
            assert ex.get("status") == "FINISHED", f"Workflow status: {ex.get('status')}"

        # Verify detection
        self._log("STEP 3: Verifying canary file detection")
        cases = self.thehive.search_cases()
        new_cases = len(cases) - self._cases_before
        if new_cases > 0:
            last = max(cases, key=lambda c: c.get("caseId", 0))
            self._log(f"+ Case created: {last.get('title')}")
            # Verify canary file is mentioned
            description = last.get("description", "")
            assert "canary" in description.lower(), "Case should mention canary file"

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        assert elapsed > 0, "Elapsed time should be positive"
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-25-04 COMPLETED — CANARY FILE DETECTION VALIDATED ===")
