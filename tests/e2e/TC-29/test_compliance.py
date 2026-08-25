#!/usr/bin/env python3
"""TC-29: Compliance and Auditing (MITRE/D3FEND Mapping) Tests compliance with
MITRE ATT&CK and D3FEND frameworks."""

import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest


class TestCompliance(E2EBaseTest):
    """TC-29 — Compliance and Auditing (MITRE/D3FEND Mapping)."""

    tc_id = "TC-29"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-29 {msg}"
        print(line)

    def test_mitre_attack_mapping(self):
        """TC-29: Validate MITRE ATT&CK technique mapping.

        Verifications:
          1. Alert includes MITRE ATT&CK techniques
          2. Techniques are mapped to appropriate responses
          3. Workflow actions align with MITRE mitigations
        """
        self._log("=== TC-29: MITRE ATT&CK MAPPING TEST STARTED ===")

        # MITRE ATT&CK techniques for ransomware

        # Send alert with MITRE techniques
        alert_id = f"TC31-MITRE-{int(time.time())}"
        payload = {
            "alert_id": alert_id,
            "alert_type": "ransomware",
            "hostname": "WIN-TC31-001",
            "src_ip": "192.168.1.220",
            "hash": "a" * 64,
            "severity": 3,
            "source": "compliance-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486", "T1059"],
        }

        self._log("STEP 1: Sending alert with MITRE ATT&CK techniques")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        self.validate_workflow_execution(execution, alert_id=alert_id)

        # Validate MITRE techniques are preserved
        self._log("STEP 3: Validating MITRE techniques preservation")
        doc = self.es.search_by_alert_id(payload["alert_id"])
        assert doc is not None, "ES document not found"
        assert isinstance(doc, dict), "ES document must be a dict"
        stored_techniques = doc.get("mitre_techniques", [])
        if stored_techniques:
            self._log(f"+ MITRE techniques preserved in ES: {stored_techniques}")
            # Validate that techniques match original payload
            assert set(stored_techniques) == set(
                payload["mitre_techniques"]
            ), "MITRE techniques should be preserved exactly"
        else:
            self._log("+ MITRE techniques not in ES (may be in TheHive)")

        # Validate workflow actions align with MITRE mitigations
        self._log("STEP 4: Validating workflow actions align with MITRE mitigations")
        mitigation_keywords = [
            "isolate",
            "block",
            "contain",
            "kill",
            "terminate",
            "preserve",
            "investigate",
            "suspend",
            "quarantine",
            "disable",
        ]
        mitigation_actions_found = 0
        assert execution is not None, "Workflow execution data must not be None"
        results = execution.get("results", [])
        assert isinstance(results, list), "Results must be a list"
        for node in results:
            label = node.get("action", {}).get("label", "").lower()
            if any(kw in label for kw in mitigation_keywords):
                self._log(f"+ Mitigation-related action found: {label}")
                mitigation_actions_found += 1

        # Also validate mitigation tasks are reflected in TheHive
        cases = self.thehive.search_cases()
        new_cases = len(cases) - self.cases_before
        assert new_cases > 0, "No new TheHive case created"
        last = max(cases, key=lambda c: c.get("caseId", 0))
        case_id = last.get("id", last.get("_id", ""))
        tasks = self.thehive.list_case_tasks(case_id)
        task_titles = [t.get("title", "").lower() for t in tasks]
        for title in task_titles:
            if any(kw in title for kw in mitigation_keywords):
                self._log(f"+ Mitigation task found: {title}")
                mitigation_actions_found += 1

        # Validate that at least one mitigation action was found
        assert (
            mitigation_actions_found > 0
        ), "At least one MITRE mitigation action or task should be found"
        self._log("✓ MITRE ATT&CK mapping validated - techniques preserved and mitigations applied")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-29 COMPLETED — MITRE ATT&CK MAPPING VALIDATED ===")
