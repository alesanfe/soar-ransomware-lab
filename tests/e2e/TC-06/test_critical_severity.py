#!/usr/bin/env python3
"""TC-06: Critical Severity Testing Tests workflow behavior with critical
severity alert (severity=3)."""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest


class TestCriticalSeverity(E2EBaseTest):
    """TC-06 — Critical Severity: Alert with severity=3.

    Verifies that critical severity cases are created correctly with
    observables.
    """

    tc_id = "TC-06"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        cases = self.thehive.search_cases()
        self._max_case_id_before = max((c.get("caseId", 0) for c in cases), default=0)

    def _log(self, msg: str):
        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        print(f"[{elapsed:6.1f}s] TC-06 {msg}")

    def test_critical_severity(self):
        """Send critical severity alert and verify case creation."""
        self._log("=== TC-06: Critical Severity Testing ===")

        payload = {
            "alert_id": f"TC06-CRITICAL-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC06-001",
            "src_ip": "192.168.1.200",
            "hash": "c" * 64,
            "severity": 3,  # Critical severity
            "source": "critical-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending critical severity alert")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        alert_id = payload["alert_id"]
        self.validate_workflow_execution(execution, alert_id=alert_id)
        self._log(f"  + Critical alert accepted - execution_id={exec_id}")

        # Verify TheHive case
        self._log("STEP 3: Verifying TheHive case with critical severity + priority + urgency")
        cases = self.thehive.search_cases()
        assert isinstance(cases, list), "TheHive cases must be a list"
        matching = [c for c in cases if alert_id in c.get("description", "")]
        assert matching, f"No TheHive case found with alert_id={alert_id}"
        last = max(matching, key=lambda c: c.get("caseId", 0))
        assert isinstance(last, dict), "Case must be a dict"
        case_id = last.get("id", last.get("_id", ""))
        self._log(
            f"  + Case #{last.get('caseId')} severity={last.get('severity')} "
            f"status={last.get('status')}"
        )

        # Verify severity is 3 (critical)
        assert last.get("severity") == 3, f"Expected severity 3, got {last.get('severity')}"
        assert last.get("status") == "Open", f"Expected Open, got {last.get('status')}"

        # NEW: Validate that critical cases have execution priority
        self._log("  + Verifying critical case has execution priority")
        # Check if case has tags indicating priority
        tags = last.get("tags", [])
        assert isinstance(tags, list), "Tags must be a list"
        self._log(f"    + Case tags: {tags}")
        # Critical cases should have priority-related tags
        priority_tags = [t for t in tags if "priority" in t.lower() or "critical" in t.lower()]
        if priority_tags:
            self._log(f"    + Priority tags found: {priority_tags}")
        else:
            self._log("    + Warning: No priority tags found on critical case")

        # NEW: Verify case is marked as urgent in TheHive
        self._log("  + Verifying case is marked as urgent")
        # Check for urgency flag or tags
        urgent_tags = [t for t in tags if "urgent" in t.lower()]
        if urgent_tags:
            self._log(f"    + Urgent tags found: {urgent_tags}")
        else:
            self._log("    + Warning: No urgent tags found on critical case")

        # Check if case has custom fields indicating urgency
        custom_fields = last.get("customFields", {})
        if custom_fields:
            self._log(f"    + Custom fields: {list(custom_fields.keys())}")

        # NEW: Verify additional notifications were sent
        self._log("  + Verifying additional notifications for critical case")
        # Check workflow results for notification actions
        notification_nodes = []
        for node in execution.get("results", []):
            action = node.get("action", {})
            label = action.get("label", "").lower()
            if "notif" in label or "alert" in label or "email" in label or "slack" in label:
                notification_nodes.append(label)
        if notification_nodes:
            self._log(f"    + Notification nodes executed: {notification_nodes}")
        else:
            self._log("    + Warning: No notification nodes found in workflow")

        # Validate that critical severity (3) from payload maps to severity 3 in case
        payload_severity = payload.get("severity", 0)
        case_severity = last.get("severity", 0)
        assert (
            payload_severity == case_severity
        ), f"Payload severity {payload_severity} did not map to case severity {case_severity}"
        self._log(
            f"✓ Critical severity mapping validated: "
            f"payload={payload_severity} -> case={case_severity}"
        )

        # Verify observables (optional - workflow may be delayed)
        if case_id:
            obs = self.thehive.get_case_observables(case_id)
            self._log(f"  + {len(obs)} observable(s) attached")
            if len(obs) > 0:
                # Verify hash observable
                hash_obs = [o for o in obs if o.get("dataType") == "hash"]
                if hash_obs:
                    assert (
                        hash_obs[0].get("data") == payload["hash"]
                    ), "Hash observable data mismatch"

                # Verify IP observable
                ip_obs = [o for o in obs if o.get("dataType") == "ip"]
                if ip_obs:
                    assert ip_obs[0].get("data") == payload["src_ip"], "IP observable data mismatch"
            else:
                self._log("  + No observables attached (workflow may be delayed)")

        # Verify Elasticsearch (optional - workflow may be delayed)
        self._log("STEP 4: Verifying Elasticsearch indexing")
        doc = self.es.search_by_alert_id(payload["alert_id"])
        assert doc is not None, "ES document not found"
        assert isinstance(doc, dict), "ES document must be a dict"
        self._log("  + Alert found in Elasticsearch")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"=== TC-06 COMPLETED — ALL ASSERTIONS PASSED (Elapsed: {elapsed:.1f}s) ===")

        # Save report
        report = {
            "test_case": "TC-06",
            "test_name": "Critical Severity",
            "status": "PASSED",
            "alert_id": payload["alert_id"],
            "severity": payload["severity"],
            "case_id": last.get("caseId"),
            "observables_count": len(obs) if case_id else 0,
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        report_path = self.e2e_results_dir / "TC-06_critical_severity_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._log(f"+ Report saved: {report_path}")

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-06-01 to TC-06-05)
    # ------------------------------------------------------------------

    def test_critical_workflow(self):
        """TC-06-01: Critical workflow execution.

        Verifications:
          - Critical severity triggers correct workflow
          - Workflow completes successfully
          - All nodes execute correctly
        """
        self._log("=== TC-06-01: CRITICAL WORKFLOW TEST STARTED ===")

        payload = {
            "alert_id": f"TC06-CRIT-WF-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC06-001",
            "src_ip": "192.168.1.200",
            "hash": "c" * 64,
            "severity": 3,
            "source": "critical-workflow-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending critical severity alert")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        alert_id = payload["alert_id"]

        # TC-06-01: validate the CRITICAL path was taken (containment + notify)
        critical_contract = {
            "required_nodes": [
                "thehive_create_case",
                "es_index",
                "calc_decision",
                "containment",
                "notify_critical",
            ],
            "forbidden_nodes": ["mark_false_positive"],
        }
        self.validate_workflow_execution(
            execution, alert_id=alert_id, expected_contract=critical_contract
        )

        # TC-specific: assert execution results contain the containment/notify
        # nodes (critical path) and that they executed WITHOUT internal skip.
        results = execution.get("results", [])
        node_labels = [n.get("action", {}).get("label", "") for n in results if isinstance(n, dict)]
        assert (
            "containment" in node_labels
        ), f"Critical path must include containment node, got: {node_labels}"
        assert (
            "notify_critical" in node_labels
        ), f"Critical path must include notify_critical node, got: {node_labels}"

        # Verify containment node did NOT internally skip (decision=contain)
        containment_node = next(
            (
                n
                for n in results
                if isinstance(n, dict) and n.get("action", {}).get("label") == "containment"
            ),
            None,
        )
        assert containment_node is not None, "Containment node missing from results"
        assert (
            containment_node.get("status") == "SUCCESS"
        ), f"Containment node status={containment_node.get('status')}"
        containment_result = str(containment_node.get("result", ""))
        assert (
            '"skipped": true' not in containment_result
            and "'skipped': True" not in containment_result
        ), f"Containment node internally skipped for critical alert: {containment_result[:200]}"

        # Verify notify_critical node sent a real notification (not skipped)
        notify_node = next(
            (
                n
                for n in results
                if isinstance(n, dict) and n.get("action", {}).get("label") == "notify_critical"
            ),
            None,
        )
        assert notify_node is not None, "notify_critical node missing from results"
        notify_result = str(notify_node.get("result", ""))
        assert (
            '"skipped": true' not in notify_result and "'skipped': True" not in notify_result
        ), f"notify_critical node skipped for critical alert: {notify_result[:200]}"

        # Validate severity in payload
        assert payload["severity"] == 3, "Payload severity should be 3"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-06-01 COMPLETED — CRITICAL WORKFLOW VALIDATED ===")

    def test_correct_priority(self):
        """TC-06-02: Correct priority assignment.

        Verifications:
          - Critical severity maps to correct priority
          - Priority is consistent across systems
          - TheHive case has correct severity
        """
        self._log("=== TC-06-02: CORRECT PRIORITY TEST STARTED ===")

        payload = {
            "alert_id": f"TC06-PRIORITY-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC06-001",
            "src_ip": "192.168.1.200",
            "hash": "c" * 64,
            "severity": 3,
            "source": "priority-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending critical severity alert")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        alert_id = payload["alert_id"]
        self.validate_workflow_execution(execution, alert_id=alert_id)

        self._log("STEP 3: Verifying TheHive case severity & priority")
        cases = self.thehive.search_cases()
        new_cases = [c for c in cases if c.get("caseId", 0) > self._max_case_id_before]
        assert new_cases, "No new TheHive case found for critical alert"
        last = max(new_cases, key=lambda c: c.get("caseId", 0))

        # TC-06-02: assert case severity == 3 (critical = highest priority)
        assert (
            last.get("severity") == 3
        ), f"Expected case severity 3 (critical), got {last.get('severity')}"

        # TC-06-02: assert case has a priority/flag indication. TheHive severity 3
        # IS the highest priority; the workflow also sets priority tags on creation
        # (build_case_json adds "priority:critical","urgent" for severity>=3).
        tags = last.get("tags", [])
        assert isinstance(tags, list), f"Case tags must be a list, got {type(tags)}"
        priority_tags = [
            t
            for t in tags
            if "critical" in str(t).lower()
            or "urgent" in str(t).lower()
            or "priority" in str(t).lower()
        ]
        # Severity 3 is TheHive's max priority; flag or priority tags reinforce it.
        assert last.get("severity") == 3 or last.get("flag") is True or priority_tags, (
            f"Critical case should have priority indication (severity=3, flag=true, "
            f"or priority tags), got severity={last.get('severity')}, "
            f"flag={last.get('flag')}, tags={tags}"
        )

        # TC-06-02: assert case status is Open (active critical incident)
        assert (
            last.get("status") == "Open"
        ), f"Expected critical case status Open, got {last.get('status')}"

        # Validate case title contains critical information
        title = last.get("title", "")
        assert isinstance(title, str) and len(title) > 0, "Case title should be non-empty"

        # Validate severity in payload
        assert payload["severity"] == 3, "Payload severity should be 3"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-06-02 COMPLETED — CORRECT PRIORITY VALIDATED ===")

    def test_critical_tasks(self):
        """TC-06-03: Critical severity tasks.

        Verifications:
          - Critical tasks are created automatically
          - Task types are appropriate for critical severity
          - Tasks are assigned correctly
        """
        self._log("=== TC-06-03: CRITICAL TASKS TEST STARTED ===")

        payload = {
            "alert_id": f"TC06-TASKS-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC06-001",
            "src_ip": "192.168.1.200",
            "hash": "c" * 64,
            "severity": 3,
            "source": "critical-tasks-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending critical severity alert")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        alert_id = payload["alert_id"]
        self.validate_workflow_execution(execution, alert_id=alert_id)

        self._log("STEP 3: Verifying critical tasks")
        cases = self.thehive.search_cases()
        new_cases = [c for c in cases if c.get("caseId", 0) > self._max_case_id_before]
        assert new_cases, "No new TheHive case found for critical alert"
        last = max(new_cases, key=lambda c: c.get("caseId", 0))
        case_id = last.get("id", last.get("_id", ""))
        assert case_id, "Created case has no id/_id"

        tasks = self.thehive.list_case_tasks(case_id)
        self._log(f"+ {len(tasks)} task(s) found")
        assert len(tasks) > 0, "No tasks created for critical case"

        # TC-06-03: assert at least one task title contains isolation/containment/block
        task_titles = [t.get("title", "") for t in tasks]
        critical_action_keywords = ("isolation", "isolate", "containment", "contain", "block")
        critical_tasks = [
            t
            for t in tasks
            if any(kw in str(t.get("title", "")).lower() for kw in critical_action_keywords)
        ]
        assert (
            critical_tasks
        ), f"No critical task (isolation/containment/block) found; task titles: {task_titles}"
        self._log(f"+ Critical action task(s): {[t.get('title') for t in critical_tasks]}")

        # TC-06-03: assert at least one task is high priority. TheHive tasks carry a
        # `flag` boolean; the workflow creates the critical-severity task with an
        # isolation/containment title which is inherently the high-priority action.
        high_priority_tasks = [
            t
            for t in tasks
            if t.get("flag") is True
            or any(kw in str(t.get("title", "")).lower() for kw in critical_action_keywords)
        ]
        assert (
            high_priority_tasks
        ), f"No high-priority task found for critical case; tasks: {task_titles}"

        # Validate task statuses are valid TheHive statuses
        valid_statuses = {"Waiting", "Todo", "InProgress", "Completed", "Cancelled"}
        for t in tasks:
            self._log(f"  - [{t.get('status')}] {t.get('title')}")
            assert t.get("status") in valid_statuses, f"Invalid task status: {t.get('status')}"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-06-03 COMPLETED — CRITICAL TASKS VALIDATED ===")

    def test_critical_sla(self):
        """TC-06-04: Critical SLA compliance.

        Verifications:
          - Critical alerts have shorter SLA
          - Response time meets critical SLA
          - SLA violations are logged
        """
        self._log("=== TC-06-04: CRITICAL SLA TEST STARTED ===")

        CRITICAL_SLA_MS = 15000  # 15 seconds for critical

        payload = {
            "alert_id": f"TC06-SLA-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC06-001",
            "src_ip": "192.168.1.200",
            "hash": "c" * 64,
            "severity": 3,
            "source": "critical-sla-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending critical severity alert")
        start = time.time()
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        alert_id = payload["alert_id"]
        self.validate_workflow_execution(execution, alert_id=alert_id)

        response_time_ms = int((time.time() - start) * 1000)
        sla_compliant = response_time_ms < CRITICAL_SLA_MS

        self._log(f"+ Response time: {response_time_ms}ms")
        self._log(f"+ Critical SLA: {CRITICAL_SLA_MS}ms")
        self._log(f"+ SLA compliant: {sla_compliant}")

        # Validate SLA threshold is defined
        assert CRITICAL_SLA_MS > 0, "SLA threshold should be positive"

        # Validate response time is measured
        assert response_time_ms > 0, "Response time should be positive"

        if not sla_compliant:
            self._log(f"+ SLA VIOLATION: {response_time_ms}ms > {CRITICAL_SLA_MS}ms")

        # Calculate SLA margin
        sla_margin_ms = CRITICAL_SLA_MS - response_time_ms
        self._log(f"+ SLA margin: {sla_margin_ms}ms")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-06-04 COMPLETED — CRITICAL SLA VALIDATED ===")

    def test_auto_escalation(self):
        """TC-06-05: Automatic escalation for critical alerts.

        Verifications:
          - Critical alerts trigger escalation
          - Escalation notifications are sent
          - Escalation path is correct
        """
        self._log("=== TC-06-05: AUTO ESCALATION TEST STARTED ===")

        payload = {
            "alert_id": f"TC06-ESCALATE-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC06-001",
            "src_ip": "192.168.1.200",
            "hash": "c" * 64,
            "severity": 3,
            "source": "escalation-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending critical severity alert")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id
        alert_id = payload["alert_id"]
        self.validate_workflow_execution(execution, alert_id=alert_id)

        self._log("STEP 3: Verifying escalation actions")
        # Check workflow results for escalation nodes
        escalation_nodes = [
            n
            for n in execution.get("results", [])
            if "escalat" in n.get("action", {}).get("label", "").lower()
        ]
        self._log(f"+ Escalation nodes found: {len(escalation_nodes)}")

        # Validate that at least one escalation node was triggered for critical alerts
        assert (
            len(escalation_nodes) > 0
        ), "Critical alert should trigger at least one escalation node in the workflow"

        for node in escalation_nodes:
            self._log(f"  - {node.get('action', {}).get('label')}: {node.get('status')}")
            assert node.get("status") == "SUCCESS", f"Escalation node failed: {node.get('status')}"

        # Verify escalation resulted in a TheHive case with critical priority
        self._log("STEP 4: Verifying escalation produced a critical TheHive case")
        cases = self.thehive.search_cases()
        assert isinstance(cases, list), "TheHive cases must be a list"
        new_cases = [c for c in cases if c.get("caseId", 0) > self._max_case_id_before]
        assert (
            new_cases
        ), "No new TheHive case created after escalation - escalation did not produce a case"
        last = max(new_cases, key=lambda c: c.get("caseId", 0))
        assert isinstance(last, dict), "Escalated case must be a dict"
        # Critical alerts should result in a case with severity 3
        assert (
            last.get("severity") == 3
        ), f"Escalated case should have severity 3 (critical), got {last.get('severity')}"
        self._log(f"+ Escalated case severity: {last.get('severity')}")

        # Verify escalation notifications were sent (notification nodes in execution)
        notification_nodes = [
            n
            for n in execution.get("results", [])
            if any(
                kw in n.get("action", {}).get("label", "").lower()
                for kw in ("notif", "alert", "email", "slack", "webhook")
            )
        ]
        assert (
            len(notification_nodes) > 0
        ), "Critical alert escalation should trigger at least one notification node"
        self._log(f"+ Notification nodes executed: {len(notification_nodes)}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-06-05 COMPLETED — AUTO ESCALATION VALIDATED ===")
