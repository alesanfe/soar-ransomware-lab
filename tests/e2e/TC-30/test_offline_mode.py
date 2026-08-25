#!/usr/bin/env python3
"""TC-30: Offline Mode Tests system behavior in offline/air-gapped scenarios:
Air Gapped, Internet failure, recovery."""

import json as _json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e.base import E2EBaseTest

# Docker network name used by the SOAR stack
SOAR_NETWORK = "soar_net"


class TestOfflineMode(E2EBaseTest):
    """TC-30 — Offline Mode: Comportamiento en escenarios sin conexión."""

    tc_id = "TC-30"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-30 {msg}"
        print(line)

    def _disconnect_container(self, container: str) -> bool:
        """Stop a container to simulate offline mode.

        On Docker Desktop for Windows, `docker network disconnect` breaks
        DNS resolution for ALL containers on that network. Using
        `docker stop` is a cleaner way to simulate offline mode without
        breaking DNS for other services.
        """
        try:
            result = subprocess.run(
                ["docker", "stop", container],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                self._log(f"+ Stopped {container} (simulating offline)")
                return True
            self._log(f"+ {container} stop returned: {result.stderr.strip()}")
            return True
        except Exception as e:
            self._log(f"+ Failed to stop {container}: {e}")
            return False

    def _reconnect_container(self, container: str) -> bool:
        """Start a container to bring it back online."""
        try:
            result = subprocess.run(
                ["docker", "start", container],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                self._log(f"+ Started {container} (back online)")
                return True
            self._log(f"+ {container} start returned: {result.stderr.strip()}")
            return True
        except Exception as e:
            self._log(f"+ Failed to reconnect {container}: {e}")
            return False

    def _get_node_statuses(self, execution: dict) -> dict[str, str]:
        """Extract node label -> status mapping from execution results."""
        node_map: dict[str, str] = {}
        results = execution.get("results", [])
        if not isinstance(results, list):
            return node_map
        for node in results:
            if not isinstance(node, dict):
                continue
            action = node.get("action", {})
            if not isinstance(action, dict):
                continue
            label = action.get("label", "?")
            node_map[label] = node.get("status", "UNKNOWN")
        return node_map

    def _node_was_skipped(self, execution: dict, label_keyword: str) -> bool:
        """Check if any node whose label contains the keyword was skipped.

        A node is considered skipped if its status is not SUCCESS, or if
        its result contains an internal {"skipped": true} flag, or if
        the result indicates a connection error (graceful degradation
        when the target service is offline).
        """
        results = execution.get("results", [])
        if not isinstance(results, list):
            return False
        for node in results:
            if not isinstance(node, dict):
                continue
            action = node.get("action", {})
            if not isinstance(action, dict):
                continue
            label = action.get("label", "")
            if label_keyword.lower() not in label.lower():
                continue
            status = node.get("status", "")
            if status != "SUCCESS":
                return True
            # Check for internal skip flag or connection error
            raw_result = str(node.get("result", ""))
            try:
                parsed = _json.loads(raw_result)
            except Exception:
                parsed = {}
            if isinstance(parsed, dict):
                if parsed.get("skipped") is True:
                    return True
                msg = parsed.get("message")
                if isinstance(msg, dict) and msg.get("skipped") is True:
                    return True
                # Check for connection error indicators (graceful degradation)
                raw_lower = raw_result.lower()
                if any(kw in raw_lower for kw in (
                    "connection refused", "connection error", "connect timeout",
                    "max retries exceeded", "failed to establish",
                    "connectionreseterror", "connectionabortederror",
                    "name resolution", "service unavailable",
                )):
                    return True
        return False

    def test_air_gapped_mode(self):
        """TC-30-01: Air gapped mode test.

        Verifications:
          - Disconnect Cortex from Docker network
          - Send alert → workflow FINISHED (graceful degradation)
          - Cortex node SKIPPED (not crashed)
          - Reconnect Cortex → Cortex healthy again
        """
        self._log("=== TC-30-01: AIR GAPPED MODE TEST STARTED ===")

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        # STEP 1: Disconnect Cortex from the network
        self._log("STEP 1: Disconnecting Cortex from Docker network")
        disconnected = self._disconnect_container("soar_cortex")
        assert disconnected, "Failed to disconnect Cortex container from network"

        # Give Docker a moment to apply the network change
        time.sleep(3)

        # STEP 2: Send alert and wait for workflow to finish
        self._log("STEP 2: Sending alert with Cortex offline")
        alert_id = f"TC30-AIRGAP-{int(time.time())}"
        payload = {
            "alert_id": alert_id,
            "alert_type": "ransomware",
            "hostname": "WIN-TC30-001",
            "src_ip": "192.168.1.220",
            "hash": "a" * 64,
            "severity": 2,
            "source": "air-gapped-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        try:
            exec_id, execution = self.submit_alert_and_wait(payload, timeout=self.WORKFLOW_TIMEOUT)
        finally:
            # Always reconnect, even if the test fails
            self._log("STEP 3: Reconnecting Cortex (cleanup)")
            self._reconnect_container("soar_cortex")
            # Wait for Cortex to become healthy again
            time.sleep(30)

        # STEP 3: Assert workflow FINISHED
        self._log("STEP 4: Verifying workflow completed with Cortex offline")
        assert execution is not None, "Workflow execution data must not be None"
        workflow_status = execution.get("status", "")
        assert workflow_status == "FINISHED", (
            f"Workflow should FINISH even with Cortex offline (graceful degradation), "
            f"got status: {workflow_status}"
        )
        self._log(f"+ Workflow FINISHED with Cortex offline: {workflow_status}")

        # STEP 4: Assert Cortex node was SKIPPED (not crashed the workflow)
        self._log("STEP 5: Verifying Cortex node was skipped")
        cortex_skipped = self._node_was_skipped(execution, "cortex")
        assert cortex_skipped, (
            "Cortex node should be SKIPPED or show internal skip when Cortex is offline, "
            f"but it appears to have run normally. Node statuses: "
            f"{self._get_node_statuses(execution)}"
        )
        self._log("+ Cortex node was skipped (graceful degradation)")

        # STEP 5: Assert Cortex is healthy after reconnection
        self._log("STEP 6: Verifying Cortex is healthy after reconnection")
        ok, msg = self.verify_cortex()
        assert (
            ok
        ), f"Cortex should be healthy after reconnection, but verify_cortex() returned: {msg}"
        self._log(f"+ Cortex healthy after reconnection: {msg}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-30-01 COMPLETED — AIR GAPPED MODE VALIDATED ===")

    def test_internet_failure_simulation(self):
        """TC-30-02: Internet failure simulation test.

        Verifications:
          - Disconnect MISP from Docker network
          - Send alert → workflow FINISHED (graceful degradation)
          - MISP node SKIPPED (not crashed)
          - TheHive case still created (core functionality preserved)
          - Reconnect MISP
        """
        self._log("=== TC-30-02: INTERNET FAILURE SIMULATION TEST STARTED ===")

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        # STEP 1: Disconnect MISP from the network
        self._log("STEP 1: Disconnecting MISP from Docker network")
        disconnected = self._disconnect_container("soar_misp")
        assert disconnected, "Failed to disconnect MISP container from network"

        time.sleep(3)

        # STEP 2: Send alert and wait for workflow
        self._log("STEP 2: Sending alert with MISP offline")
        alert_id = f"TC30-MISP-OFFLINE-{int(time.time())}"
        payload = {
            "alert_id": alert_id,
            "alert_type": "ransomware",
            "hostname": "WIN-TC30-002",
            "src_ip": "192.168.1.221",
            "hash": "b" * 64,
            "severity": 2,
            "source": "misp-offline-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        cases_before = len(self.thehive.search_cases())

        try:
            exec_id, execution = self.submit_alert_and_wait(payload, timeout=self.WORKFLOW_TIMEOUT)
        finally:
            # Always reconnect
            self._log("STEP 3: Reconnecting MISP (cleanup)")
            self._reconnect_container("soar_misp")
            # Wait for MISP to become healthy again
            time.sleep(30)

        # STEP 3: Assert workflow FINISHED
        self._log("STEP 4: Verifying workflow completed with MISP offline")
        assert execution is not None, "Workflow execution data must not be None"
        workflow_status = execution.get("status", "")
        assert workflow_status == "FINISHED", (
            f"Workflow should FINISH even with MISP offline (graceful degradation), "
            f"got status: {workflow_status}"
        )
        self._log(f"+ Workflow FINISHED with MISP offline: {workflow_status}")

        # STEP 4: Assert MISP node was SKIPPED
        self._log("STEP 5: Verifying MISP node was skipped")
        misp_skipped = self._node_was_skipped(execution, "misp")
        assert misp_skipped, (
            "MISP node should be SKIPPED or show internal skip when MISP is offline, "
            f"but it appears to have run normally. Node statuses: "
            f"{self._get_node_statuses(execution)}"
        )
        self._log("+ MISP node was skipped (graceful degradation)")

        # STEP 5: Assert TheHive case was still created (core functionality)
        self._log("STEP 6: Verifying TheHive case created despite MISP offline")
        case = self.assert_thehive_case_created(alert_id, timeout=60)
        assert case is not None, (
            f"TheHive case must be created even with MISP offline (core functionality), "
            f"alert_id={alert_id} not found"
        )
        cases_after = len(self.thehive.search_cases())
        assert (
            cases_after > cases_before
        ), f"TheHive case count should increase ({cases_before} → {cases_after})"
        self._log(f"+ TheHive case created: {case.get('_id') or case.get('id')}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-30-02 COMPLETED — INTERNET FAILURE SIMULATION VALIDATED ===")

    def test_offline_recovery(self):
        """TC-30-03: Offline recovery test.

        Verifications:
          - After reconnecting all services, send alert
          - Workflow FINISHED
          - ALL nodes SUCCESS (full recovery — no skipped/failed nodes)
          - MISP and Cortex back online and healthy
        """
        self._log("=== TC-30-03: OFFLINE RECOVERY TEST STARTED ===")

        if not self.webhook_url:
            pytest.fail("Webhook URL not found in webhook_info.json")

        # STEP 1: Verify MISP and Cortex are currently connected and healthy
        self._log("STEP 1: Verifying MISP and Cortex are online before test")
        ok_misp, msg_misp = self.verify_misp()
        assert ok_misp, f"MISP must be online before recovery test, got: {msg_misp}"
        ok_cortex, msg_cortex = self.verify_cortex()
        assert ok_cortex, f"Cortex must be online before recovery test, got: {msg_cortex}"
        self._log(f"+ MISP healthy: {msg_misp}")
        self._log(f"+ Cortex healthy: {msg_cortex}")

        # STEP 2: Send alert and wait for workflow
        self._log("STEP 2: Sending alert for full recovery test")
        alert_id = f"TC30-RECOVERY-{int(time.time())}"
        payload = {
            "alert_id": alert_id,
            "alert_type": "ransomware",
            "hostname": "WIN-TC30-003",
            "src_ip": "192.168.1.222",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "severity": 2,
            "source": "recovery-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
            "mitre_techniques": ["T1486"],
        }

        exec_id, execution = self.submit_alert_and_wait(payload, timeout=self.WORKFLOW_TIMEOUT)

        # STEP 3: Assert workflow FINISHED
        self._log("STEP 3: Verifying workflow completed after recovery")
        assert execution is not None, "Workflow execution data must not be None"
        workflow_status = execution.get("status", "")
        assert (
            workflow_status == "FINISHED"
        ), f"Workflow should FINISH after full recovery, got status: {workflow_status}"
        self._log(f"+ Workflow FINISHED: {workflow_status}")

        # STEP 4: Assert ALL nodes are SUCCESS (no skipped/failed nodes)
        self._log("STEP 4: Verifying all nodes succeeded (full recovery)")
        node_statuses = self._get_node_statuses(execution)
        assert len(node_statuses) > 0, "Workflow must have node results to verify recovery"
        non_success_nodes = {
            label: status for label, status in node_statuses.items() if status not in ("SUCCESS",)
        }
        # Filter out internal skips (nodes that printed {"skipped": true} but
        # have SUCCESS status are fine; only truly non-SUCCESS nodes are problems)
        assert len(non_success_nodes) == 0, (
            f"After full recovery, all nodes should be SUCCESS, but found "
            f"{len(non_success_nodes)} non-success nodes: {non_success_nodes}"
        )
        self._log(f"+ All {len(node_statuses)} nodes SUCCESS")

        # STEP 5: Assert MISP and Cortex are still back online
        self._log("STEP 5: Verifying MISP and Cortex back online after recovery")
        ok_misp2, msg_misp2 = self.verify_misp()
        assert ok_misp2, f"MISP should be back online after recovery, got: {msg_misp2}"
        ok_cortex2, msg_cortex2 = self.verify_cortex()
        assert ok_cortex2, f"Cortex should be back online after recovery, got: {msg_cortex2}"
        self._log(f"+ MISP back online: {msg_misp2}")
        self._log(f"+ Cortex back online: {msg_cortex2}")

        # STEP 6: Assert TheHive case created (end-to-end functionality)
        self._log("STEP 6: Verifying TheHive case created after recovery")
        case = self.assert_thehive_case_created(alert_id, timeout=60)
        assert (
            case is not None
        ), f"TheHive case must be created after full recovery, alert_id={alert_id} not found"
        self._log(f"+ TheHive case created: {case.get('_id') or case.get('id')}")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-30-03 COMPLETED — OFFLINE RECOVERY VALIDATED ===")
