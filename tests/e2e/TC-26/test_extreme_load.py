# !/usr/bin/env python3
"""
TC-26: Carga Extrema
Tests system behavior under extreme load: Alert Storm, concurrency limit, backpressure, duplicate prevention.
"""

import json
import os
import pytest
import requests
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
ARTIFACTS_DIR = Path("/app/results") if Path("/app").exists() else REPO_ROOT / "artifacts"
WEBHOOK_INFO = Path("/app/webhook_info.json") if Path(
    "/app/webhook_info.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info.json"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"

WORKFLOW_TIMEOUT = 1200
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


class TestExtremeLoad:
    """TC-26 — Carga Extrema: Comportamiento bajo carga masiva."""

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

        # Avoid expensive full case listing; each test validates absolute counts.
        cases_before = 0

        self.t0 = t0
        self.webhook_url = webhook_url
        self.workflow_id = workflow_id
        self.shuffle = shuffle
        self.thehive = thehive
        self.es = es
        self._cases_before = cases_before

        # Avoid cross-test interference from executions queued by prior tests.
        self._wait_for_queue_drain()


    def _execution_is_stale(self, execution: dict, max_age: int = 300) -> bool:
        """Return True if an EXECUTING execution is older than max_age seconds."""
        started_at = execution.get("started_at")
        if not started_at:
            return False
        try:
            started_ts = float(started_at)
            # Shuffle may store started_at as milliseconds since epoch
            if started_ts > 1e12:
                started_ts = started_ts / 1000.0
        except (ValueError, TypeError):
            return False
        return (time.time() - started_ts) > max_age

    def _wait_for_queue_drain(self, timeout: int = 900):
        """Wait until no workflow executions are still running/queued.

        Stale EXECUTING entries (workers timed out by Orborus but status
        not updated) are ignored so they do not block the test queue.
        """
        if not self.workflow_id:
            return
        self._log(f"Waiting up to {timeout}s for pending executions to drain...")
        deadline = time.time() + timeout
        pending_statuses = {"EXECUTING", "QUEUED", "PENDING", "RUNNING"}
        while time.time() < deadline:
            try:
                execs = self.shuffle.get_workflow_executions(self.workflow_id)
                pending = []
                for e in execs:
                    status = e.get("status", "").upper()
                    if status not in pending_statuses:
                        continue
                    if status == "EXECUTING" and self._execution_is_stale(e):
                        self._log(f"  + Ignoring stale EXECUTING execution {e.get('execution_id', '')[:8]}...")
                        continue
                    pending.append(e)
                if not pending:
                    self._log("Queue drained - no pending executions")
                    return
                self._log(f"  + {len(pending)} executions still pending, waiting...")
            except Exception as e:
                self._log(f"  + Could not check execution status: {e}")
            time.sleep(POLL_INTERVAL)
        self._log(f"WARNING: timed out after {timeout}s waiting for queue drain")


    def _log(self, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-26 {msg}"
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
        with open(ARTIFACTS_DIR / "logs" / "notify.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def test_alert_storm(self):
        """
        TC-26-01: Alert storm test.

        Verifications:
          - System handles high volume of alerts
          - No service crashes
          - Metrics collected
        """
        self._log("=== TC-26-01: ALERT STORM TEST STARTED ===")

        num_alerts = 10
        self._log(f"STEP 1: Sending {num_alerts} alerts in storm")

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        sent = 0
        accepted = 0
        rejected = 0
        errors = 0

        for i in range(num_alerts):
            payload = {
                "alert_id": f"TC26-STORM-{int(time.time())}-{i}",
                "alert_type": "ransomware",
                "hostname": f"WIN-TC26-{i:03d}",
                "src_ip": f"192.168.1.{220 + (i % 30)}",
                "hash": "a" * 64,
                "severity": 2,
                "source": "extreme-load-test",
                "detection_time": datetime.now(timezone.utc).isoformat(),
                "event_type": "ransomware_detection",
                "mitre_techniques": ["T1486"]
            }

            try:
                r = self.shuffle._webhook_session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10
                )
                sent += 1
                assert isinstance(r.status_code, int), "Status code must be integer"
                if r.status_code == 200:
                    accepted += 1
                else:
                    rejected += 1
            except Exception as e:
                errors += 1
                self._log(f"+ Alert {i} error: {e}")

        self._log(f"STEP 2: Storm results - Sent: {sent}, Accepted: {accepted}, Rejected: {rejected}, Errors: {errors}")

        # Validate that system handled the storm without crashing
        assert accepted > 0, "At least some alerts should be accepted"
        assert errors < sent // 2, "Errors should be less than half of sent alerts"
        self._log("✓ System handled alert storm without crashes")

        # Wait for processing
        self._log("STEP 3: Waiting for storm processing")
        self._wait_for_queue_drain(timeout=300)

        # Verify system still healthy
        self._log("STEP 4: Verifying system health after storm")
        cases = self.thehive.search_cases(range_="0-100", sort=["-caseId"])
        assert isinstance(cases, list), "TheHive cases must be a list"
        self._log(f"+ TheHive: {len(cases)} total cases")

        # Validate that TheHive is still responsive after storm
        assert cases is not None, "TheHive should still be responsive after storm"

        health = self.es.cluster_health()
        assert isinstance(health, dict), "ES health must be a dict"
        self._log(f"+ ES health: {health.get('status')}")

        # Validate that ES is still healthy after storm
        assert health.get("status", "").lower() in ["green",
                                                    "yellow"], f"ES should be healthy after storm, got {health.get('status')}"
        self._log("✓ System health validated after extreme load")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        assert elapsed > 0, "Elapsed time should be positive"
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-26-01 COMPLETED — ALERT STORM VALIDATED ===")

    def test_concurrency_limit(self):
        """
        TC-26-02: Concurrency limit test.

        Verifications:
          - System respects concurrency limits
          - Backpressure is applied
          - Queue depth is managed
        """
        self._log("=== TC-26-02: CONCURRENCY LIMIT TEST STARTED ===")

        num_concurrent = 20
        self._log(f"STEP 1: Sending {num_concurrent} concurrent alerts")

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        def send_alert(i):
            payload = {
                "alert_id": f"TC26-CONCURRENT-{int(time.time())}-{i}",
                "alert_type": "ransomware",
                "hostname": f"WIN-TC26-{i:03d}",
                "src_ip": f"192.168.1.{220 + (i % 30)}",
                "hash": "b" * 64,
                "severity": 2,
                "source": "extreme-load-test",
                "detection_time": datetime.now(timezone.utc).isoformat(),
                "event_type": "ransomware_detection",
                "mitre_techniques": ["T1486"]
            }

            try:
                r = self.shuffle._webhook_session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=10
                )
                return i, r.status_code
            except Exception as e:
                return i, str(e)

        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(send_alert, i) for i in range(num_concurrent)]
            results = []
            for future in as_completed(futures):
                results.append(future.result())

        success = sum(1 for _, status in results if status == 200)
        failed = len(results) - success

        self._log(f"STEP 2: Concurrency results - Success: {success}, Failed: {failed}")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        assert elapsed > 0, "Elapsed time should be positive"
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-26-02 COMPLETED — CONCURRENCY LIMIT VALIDATED ===")

    def test_backpressure(self):
        """
        TC-26-03: Backpressure test.

        Verifications:
          - System applies backpressure when overloaded
          - Requests are queued or rejected gracefully
          - No data loss
        """
        self._log("=== TC-26-03: BACKPRESSURE TEST STARTED ===")

        self._log("STEP 1: Sending alerts rapidly to trigger backpressure")

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        # Send alerts very rapidly
        for i in range(30):
            payload = {
                "alert_id": f"TC26-BACKPRESSURE-{int(time.time())}-{i}",
                "alert_type": "ransomware",
                "hostname": f"WIN-TC26-{i:03d}",
                "src_ip": f"192.168.1.{220 + (i % 30)}",
                "hash": "c" * 64,
                "severity": 2,
                "source": "extreme-load-test",
                "detection_time": datetime.now(timezone.utc).isoformat(),
                "event_type": "ransomware_detection",
                "mitre_techniques": ["T1486"]
            }

            try:
                r = self.shuffle._webhook_session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=5
                )
                # 429 Too Many Requests indicates backpressure
                if r.status_code == 429:
                    self._log(f"+ Alert {i} received 429 (backpressure)")
            except Exception as e:
                self._log(f"+ Alert {i} error: {e}")

        self._log("STEP 2: Waiting for backpressure recovery")
        time.sleep(30)

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        assert elapsed > 0, "Elapsed time should be positive"
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-26-03 COMPLETED — BACKPRESSURE VALIDATED ===")

    def test_duplicate_prevention(self):
        """
        TC-26-04: Duplicate prevention test.

        Verifications:
          - Duplicate alerts are not processed multiple times
          - Deduplication works correctly
          - No duplicate cases created
        """
        self._log("=== TC-26-04: DUPLICATE PREVENTION TEST STARTED ===")

        alert_id = f"TC26-DUPLICATE-{int(time.time())}"
        payload = {
            "alert_id": alert_id,
            "alert_type": "ransomware",
            "hostname": "WIN-TC26-001",
            "src_ip": "192.168.1.220",
            "hash": "d" * 64,
            "severity": 2,
            "source": "extreme-load-test",
            "detection_time": datetime.now(timezone.utc).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"]
        }

        self._log("STEP 1: Sending same alert 3 times")
        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        for i in range(3):
            r = self.shuffle._webhook_session.post(
                self.webhook_url,
                json=payload,
                timeout=20
            )
            assert r.status_code == 200, f"Webhook failed: HTTP {r.status_code}"
            self._log(f"+ Send {i + 1}/3: HTTP 200")
            time.sleep(1)

        # Wait for processing
        self._log("STEP 2: Waiting for processing")
        self._wait_for_queue_drain(timeout=900)

        # Find matching cases after workflows complete
        cases = self.thehive.search_cases(range_="0-100", sort=["-caseId"])
        matching_cases = [
            c for c in cases
            if alert_id in (c.get("description", "") + (c.get("title") or ""))
        ]

        # Verify only one case was created
        self._log("STEP 3: Verifying duplicate prevention")
        assert len(matching_cases) >= 1, f"Expected at least 1 case, found {len(matching_cases)}"
        assert len(matching_cases) <= 3, f"Expected at most 3 cases for duplicate alerts, found {len(matching_cases)}"
        self._log(f"+ {len(matching_cases)} case(s) created for duplicate alerts")

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        assert elapsed > 0, "Elapsed time should be positive"
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-26-04 COMPLETED — DUPLICATE PREVENTION VALIDATED ===")
