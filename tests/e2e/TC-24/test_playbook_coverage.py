#!/usr/bin/env python3
"""TC-24 ext: playbook/detection coverage beyond ransomware — phishing/BEC,
exfiltration, credential stuffing, webshell. Rules must be well-formed
sigma with MITRE tags; typed alerts must flow the pipeline to a decision."""

import time

import pytest
import requests
import yaml

from tests.e2e.base import E2EBaseTest

pytestmark = [pytest.mark.e2e, pytest.mark.functional]

DETECTIONS = "/app/detections/sigma"
API = "http://api:8000"
ES = "https://elasticsearch:9200/soar-metrics"

RULES = {
    "phishing-bec.yml": {"attack.t1566"},
    "data-exfiltration.yml": {"attack.t1048"},
    "credential-stuffing.yml": {"attack.t1110.004"},
    "webshell-activity.yml": {"attack.t1505.003"},
}


class TestPlaybookCoverage(E2EBaseTest):
    tc_id = "TC-24"

    def test_rules_wellformed_sigma_with_mitre_tags(self):
        """Every playbook rule parses as sigma: title, logsource, detection
        with a condition, and MITRE ATT&CK tags for coverage mapping."""
        import glob
        for fname, tags in RULES.items():
            path = f"{DETECTIONS}/{fname}"
            rule = yaml.safe_load(open(path))
            assert rule.get("title") and rule.get("id"), fname
            assert rule.get("logsource"), fname
            det = rule.get("detection") or {}
            assert det.get("condition"), f"{fname}: no condition"
            assert set(rule.get("tags", [])) >= tags, (
                f"{fname}: missing MITRE tags {tags}"
            )
        assert len(glob.glob(f"{DETECTIONS}/*.yml")) >= 6

    def test_typed_alerts_admitted_by_pipeline(self):
        """One alert per playbook type must be admitted — the pipeline
        cannot route what it refuses to accept."""
        h = {"X-Service-Token": self.env.get("INTERNAL_SERVICE_TOKEN", "")}
        payloads = {
            "phishing": {"alert_type": "phishing",
                         "domain": "login-verify.example", "severity": 3},
            "exfiltration": {"alert_type": "data_exfiltration",
                             "domain": "x.trycloudflare.com", "severity": 3},
            "credstuffing": {"alert_type": "auth_failed",
                             "event_type": "auth_failed",
                             "fail_count": 50, "severity": 3},
            "webshell": {"alert_type": "webshell",
                         "url": "/uploads/x.php?cmd=id", "severity": 4},
        }
        for name, extra in payloads.items():
            r = requests.post(
                f"{API}/api/v1/alerts",
                json={"alert_id": f"tc24-{name}-{time.time_ns()}",
                      "timestamp": "2026-01-01T00:00:00Z",
                      "source": "tc24", **extra},
                headers=h, timeout=15)
            assert r.status_code in (200, 202), f"{name}: {r.status_code}"

    @pytest.mark.slow
    def test_playbook_alert_reaches_a_decision(self):
        """End-to-end: a typed alert is accepted by the playbook — a real
        workflowexecution doc for its alert_id must appear (bounded), and
        when the metrics doc lands it must carry a recorded decision."""
        aid = f"tc24-e2e-{int(time.time())}"
        payload = self.build_alert_payload(
            alert_id=aid, alert_type="data_exfiltration",
            domain="leak.trycloudflare.com", severity=3)
        self.submit_alert(payload)
        os_url = self.env.get(
            "SHUFFLE_OPENSEARCH_URL",
            self.env.get("OPENSEARCH_URL", "https://opensearch:9200"))
        deadline = time.time() + 150
        found = None
        while time.time() < deadline:
            q = requests.post(
                f"{os_url}/workflowexecution/_search",
                auth=self.s.auth,
                verify=self.s.verify,
                json={"size": 5, "sort": [{"started_at": "desc"}],
                      "query": {"match": {"result": aid}}},
                timeout=15).json()
            if q["hits"]["hits"]:
                found = q["hits"]["hits"][0]
                break
            time.sleep(8)
        assert found, f"playbook never executed typed alert {aid}"
        # If metrics already landed, a decision must be recorded.
        q = requests.post(
            f"{ES}/_search",
            auth=self.s.auth,
            verify=self.s.verify,
            json={"size": 1,
                  "query": {"term": {"alert_id.keyword": aid}}},
            timeout=15).json()
        hits = q["hits"]["hits"]
        if hits:
            assert hits[0]["_source"].get("decision") is not None
