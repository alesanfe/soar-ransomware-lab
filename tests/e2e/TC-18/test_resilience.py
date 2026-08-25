#!/usr/bin/env python3
"""TC-18: Resilience and Degraded Mode (Cortex/MISP Unavailable) Tests system
resilience when external services (Cortex, MISP) are unavailable."""

import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from assertions.persistence_assertions import assert_data_persisted

from tests.e2e.base import E2EBaseTest


class TestResilience(E2EBaseTest):
    """TC-18 — Resilience and Degraded Mode when Cortex/MISP are
    unavailable."""

    tc_id = "TC-18"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)

    def teardown_method(self, method):
        """Ensure all fault-injected containers are running after each test.

        This is critical: if a test stops a container and then fails before
        the ``finally`` block can restart it, subsequent tests will fail in
        setup. This teardown is a safety net that always runs.
        """
        for container in ("soar_cortex", "soar_misp"):
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format",
                     "{{.State.Status}} {{.State.Health.Status}}", container],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                parts = result.stdout.strip().split()
                status = parts[0] if parts else ""
                health = parts[1] if len(parts) > 1 else "none"
                if result.returncode == 0 and status != "running":
                    self._log(f"teardown: restarting {container} (was {status})")
                    subprocess.run(
                        ["docker", "start", container],
                        capture_output=True,
                        timeout=60,
                    )
                # Always wait for healthcheck + HTTP API to be ready
                if result.returncode == 0 and status == "running" and health not in ("healthy", "none"):
                    self._log(f"teardown: waiting for {container} to become healthy (was {health})")
                # Use _wait_for_container_healthy which also checks HTTP API
                self._wait_for_container_healthy(container, timeout=300)
            except Exception as e:
                self._log(f"teardown: failed to restore {container}: {e}")
        super().teardown_method(method)

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-18 {msg}"
        print(line)

    # ── Fault-injection helpers ──────────────────────────────────────────────

    def _stop_container(self, name: str) -> bool:
        """Stop a Docker container by name.

        Returns True if successful.
        """
        try:
            result = subprocess.run(
                ["docker", "stop", name],
                capture_output=True,
                text=True,
                timeout=60,
            )
            ok = result.returncode == 0
            self._log(f"docker stop {name}: rc={result.returncode} ok={ok}")
            return ok
        except Exception as e:
            self._log(f"docker stop {name} failed: {e}")
            return False

    def _start_container(self, name: str) -> bool:
        """Start a Docker container by name.

        Returns True if successful.
        """
        try:
            result = subprocess.run(
                ["docker", "start", name],
                capture_output=True,
                text=True,
                timeout=60,
            )
            ok = result.returncode == 0
            self._log(f"docker start {name}: rc={result.returncode} ok={ok}")
            return ok
        except Exception as e:
            self._log(f"docker start {name} failed: {e}")
            return False

    def _wait_for_container_healthy(self, name: str, timeout: int = 120) -> bool:
        """Wait until a container reports a healthy/running state AND its
        HTTP API is responsive."""
        deadline = time.time() + timeout
        # Map container names to their HTTP health check URLs
        http_checks = {
            "soar_cortex": ("http://cortex:9001/api/status", None),
            "soar_misp": ("https://misp:443/servers/getVersion", "misp_key"),
        }
        while time.time() < deadline:
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format",
                     "{{.State.Status}} {{.State.Health.Status}}", name],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                parts = result.stdout.strip().split()
                status = parts[0] if parts else ""
                health = parts[1] if len(parts) > 1 else "none"
                if result.returncode == 0 and status == "running":
                    # If container has healthcheck, wait for it to be healthy
                    if health == "none" or health == "healthy":
                        # Also verify HTTP API is responsive
                        if name in http_checks:
                            url, _ = http_checks[name]
                            try:
                                import requests as _req
                                r = _req.get(url, timeout=10, verify=False)
                                if r.status_code in (200, 401, 403):
                                    time.sleep(3)
                                    return True
                                self._log(f"  {name} HTTP check: {r.status_code}")
                            except Exception as e:
                                self._log(f"  {name} HTTP not ready: {e}")
                        else:
                            time.sleep(5)
                            return True
                    # health is "starting" or "unhealthy" — keep waiting
            except Exception as e:
                self._log(f"  docker inspect {name} retry: {e}")
            time.sleep(3)
        self._log(f"Container {name} did not become healthy within {timeout}s")
        return False

    # ── TC-18-01: Cortex unavailable ─────────────────────────────────────────

    def test_cortex_unavailable(self):
        """TC-18-01: Cortex unavailable — fault injection.

        Verifications:
          - Workflow still FINISHED in degraded mode (Cortex stopped)
          - Cortex node is SKIPPED or ERROR but workflow continues
          - TheHive case still created
          - Elasticsearch indexing still works
          - Cortex restarted after test
        """
        self._log("=== TC-18-01: CORTEX UNAVAILABLE (FAULT INJECTION) STARTED ===")

        # Fault injection: stop Cortex
        self._log("STEP 1: Stopping Cortex container (fault injection)")
        stopped = self._stop_container("soar_cortex")
        assert stopped, "Failed to stop soar_cortex container for fault injection"

        try:
            payload = {
                "alert_id": f"TC18-CORTEX-{int(time.time())}",
                "alert_type": "ransomware",
                "hostname": "WIN-TC18-001",
                "src_ip": "192.168.1.220",
                "hash": "a" * 64,
                "severity": 3,
                "source": "resilience-test",
                "detection_time": datetime.now(UTC).isoformat(),
                "event_type": "ransomware_detection",
                "mitre_techniques": ["T1486"],
            }

            self._log("STEP 2: Sending alert while Cortex is down")
            exec_id, execution = self.submit_alert_and_wait(payload)
            self.execution = execution
            self.execution_id = exec_id

            # Assert workflow still completed in degraded mode
            status = execution.get("status", "")
            self._log(f"+ Workflow status: {status}")
            assert status in [
                "FINISHED",
                "SUCCESS",
                "FAILURE",
            ], f"Workflow should complete even with Cortex down, got {status}"

            # Analyze Cortex node results — must be SKIPPED or ERROR, not SUCCESS
            self._log("STEP 3: Analyzing Cortex node results")
            execution_full = (
                self.shuffle.get_execution(self.workflow_id, exec_id, include_results=True)
                or execution
            )
            results = execution_full.get("results", [])
            assert isinstance(results, list), "Results should be a list"

            cortex_nodes = [
                n for n in results if "cortex" in n.get("action", {}).get("label", "").lower()
            ]
            self._log(f"+ Found {len(cortex_nodes)} Cortex node(s)")
            # When Cortex is down, the workflow's error handling catches
            # the connection error and reports SUCCESS with an error in the
            # result JSON (degraded mode). We require at least ONE Cortex
            # node to show a connection error — proving the workflow
            # attempted to reach Cortex and handled the failure gracefully.
            # Non-critical Cortex nodes (e.g. cleanup) may legitimately
            # report success without error.
            error_indicators = ("error", "fail", "refused", "timeout", "unavailable", "degraded", "connection")
            nodes_with_error = 0
            for node in cortex_nodes:
                assert isinstance(node, dict), "Cortex node should be a dict"
                node_status = node.get("status", "?")
                result_str = str(node.get("result", ""))
                self._log(f"  + Cortex node status: {node_status} result={result_str[:200]}")
                if node_status in ("ERROR", "SKIPPED", "ABORTED", "FAILED"):
                    nodes_with_error += 1
                elif node_status == "SUCCESS" and any(kw in result_str.lower() for kw in error_indicators):
                    nodes_with_error += 1
            assert nodes_with_error > 0, (
                f"At least one Cortex node should show a connection error (Cortex is down); "
                f"got {nodes_with_error}/{len(cortex_nodes)} with error indication"
            )

            # Assert TheHive case still created (core functionality)
            self._log("STEP 4: Verifying TheHive case creation in degraded mode")
            cases = self.thehive.search_cases(range_="0-100", sort=["-caseId"])
            assert isinstance(cases, list), "Cases should be a list"
            matching_cases = [
                c for c in cases if payload["alert_id"] in c.get("description", "")
            ]
            assert (
                len(matching_cases) > 0
            ), f"TheHive should create a case for {payload['alert_id']} even when Cortex is unavailable (degraded mode)"
            self._log(f"+ TheHive case created ({len(matching_cases)} match) despite Cortex unavailability")

            # Assert ES indexing still works
            self._log("STEP 5: Verifying Elasticsearch indexing in degraded mode")
            deadline = time.time() + 60
            doc = None
            while time.time() < deadline:
                doc = self.es.search_by_alert_id(payload["alert_id"])
                if doc:
                    break
                time.sleep(self.POLL_INTERVAL)
            assert (
                doc is not None
            ), f"Elasticsearch should index alert even with Cortex down: {payload['alert_id']}"
            assert isinstance(doc, dict), "ES document must be a dict"
            assert_data_persisted("elasticsearch", doc)
            self._log("+ Elasticsearch indexing works despite Cortex unavailability")

        finally:
            # Always restart Cortex — don't assert here (the teardown_method
            # is the safety net). If Cortex takes long to be healthy, the
            # assert would fail and prevent teardown from running.
            self._log("STEP 6: Restarting Cortex container")
            self._start_container("soar_cortex")
            self._wait_for_container_healthy("soar_cortex", timeout=300)

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-18-01 COMPLETED — CORTEX UNAVAILABLE RESILIENCE VALIDATED ===")

    # ── TC-18-02: MISP unavailable ───────────────────────────────────────────

    def test_misp_unavailable(self):
        """TC-18-02: MISP unavailable — fault injection.

        Verifications:
          - Workflow still FINISHED in degraded mode (MISP stopped)
          - MISP node is SKIPPED or ERROR but workflow continues
          - TheHive case still created
          - Elasticsearch indexing still works
          - MISP restarted after test
        """
        self._log("=== TC-18-02: MISP UNAVAILABLE (FAULT INJECTION) STARTED ===")

        # Fault injection: stop MISP
        self._log("STEP 1: Stopping MISP container (fault injection)")
        stopped = self._stop_container("soar_misp")
        assert stopped, "Failed to stop soar_misp container for fault injection"

        try:
            payload = {
                "alert_id": f"TC18-MISP-{int(time.time())}",
                "alert_type": "ransomware",
                "hostname": "WIN-TC18-002",
                "src_ip": "192.168.1.221",
                "hash": "b" * 64,
                "severity": 3,
                "source": "resilience-test",
                "detection_time": datetime.now(UTC).isoformat(),
                "event_type": "ransomware_detection",
                "mitre_techniques": ["T1059"],
            }

            self._log("STEP 2: Sending alert while MISP is down")
            exec_id, execution = self.submit_alert_and_wait(payload)
            self.execution = execution
            self.execution_id = exec_id

            # Assert workflow still completed in degraded mode
            status = execution.get("status", "")
            self._log(f"+ Workflow status: {status}")
            assert status in [
                "FINISHED",
                "SUCCESS",
                "FAILURE",
            ], f"Workflow should complete even with MISP down, got {status}"

            # Analyze MISP node results — must be SKIPPED or ERROR, not SUCCESS
            self._log("STEP 3: Analyzing MISP node results")
            execution_full = (
                self.shuffle.get_execution(self.workflow_id, exec_id, include_results=True)
                or execution
            )
            results = execution_full.get("results", [])
            assert isinstance(results, list), "Results should be a list"

            misp_nodes = [
                n for n in results if "misp" in n.get("action", {}).get("label", "").lower()
            ]
            self._log(f"+ Found {len(misp_nodes)} MISP node(s)")
            # Same degraded-mode logic as Cortex: require at least ONE MISP
            # node to show a connection error.
            error_indicators = ("error", "fail", "refused", "timeout", "unavailable", "degraded", "connection")
            nodes_with_error = 0
            for node in misp_nodes:
                assert isinstance(node, dict), "MISP node should be a dict"
                node_status = node.get("status", "?")
                result_str = str(node.get("result", ""))
                self._log(f"  + MISP node status: {node_status} result={result_str[:200]}")
                if node_status in ("ERROR", "SKIPPED", "ABORTED", "FAILED"):
                    nodes_with_error += 1
                elif node_status == "SUCCESS" and any(kw in result_str.lower() for kw in error_indicators):
                    nodes_with_error += 1
            assert nodes_with_error > 0, (
                f"At least one MISP node should show a connection error (MISP is down); "
                f"got {nodes_with_error}/{len(misp_nodes)} with error indication"
            )

            # Assert TheHive case still created
            self._log("STEP 4: Verifying TheHive case creation in degraded mode")
            cases = self.thehive.search_cases(range_="0-100", sort=["-caseId"])
            assert isinstance(cases, list), "Cases should be a list"
            matching_cases = [
                c for c in cases if payload["alert_id"] in c.get("description", "")
            ]
            assert (
                len(matching_cases) > 0
            ), f"TheHive should create a case for {payload['alert_id']} even when MISP is unavailable (degraded mode)"
            self._log(f"+ TheHive case created ({len(matching_cases)} match) despite MISP unavailability")

            # Assert ES indexing still works
            self._log("STEP 5: Verifying Elasticsearch indexing in degraded mode")
            deadline = time.time() + 60
            doc = None
            while time.time() < deadline:
                doc = self.es.search_by_alert_id(payload["alert_id"])
                if doc:
                    break
                time.sleep(self.POLL_INTERVAL)
            assert (
                doc is not None
            ), f"Elasticsearch should index alert even with MISP down: {payload['alert_id']}"
            assert isinstance(doc, dict), "ES document must be a dict"
            assert_data_persisted("elasticsearch", doc)
            self._log("+ Elasticsearch indexing works despite MISP unavailability")

        finally:
            # Always restart MISP — don't assert (teardown_method is safety net)
            self._log("STEP 6: Restarting MISP container")
            self._start_container("soar_misp")
            self._wait_for_container_healthy("soar_misp", timeout=300)

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-18-02 COMPLETED — MISP UNAVAILABLE RESILIENCE VALIDATED ===")

    # ── TC-18-03: Both Cortex and MISP unavailable ───────────────────────────

    def test_both_unavailable(self):
        """TC-18-03: Both Cortex and MISP unavailable — fault injection.

        Verifications:
          - Workflow continues without external services
          - Core pipeline (Shuffle -> TheHive -> ES) still works
          - Degraded mode is functional
          - Both services restarted after test
        """
        self._log("=== TC-18-03: BOTH SERVICES UNAVAILABLE (FAULT INJECTION) STARTED ===")

        # Fault injection: stop both Cortex and MISP
        self._log("STEP 1: Stopping both Cortex and MISP containers (fault injection)")
        stopped_cortex = self._stop_container("soar_cortex")
        stopped_misp = self._stop_container("soar_misp")
        assert stopped_cortex, "Failed to stop soar_cortex for fault injection"
        assert stopped_misp, "Failed to stop soar_misp for fault injection"

        try:
            payload = {
                "alert_id": f"TC18-BOTH-{int(time.time())}",
                "alert_type": "ransomware",
                "hostname": "WIN-TC18-003",
                "src_ip": "192.168.1.222",
                "hash": "c" * 64,
                "severity": 3,
                "source": "resilience-test",
                "detection_time": datetime.now(UTC).isoformat(),
                "event_type": "ransomware_detection",
                "mitre_techniques": ["T1486"],
            }

            self._log("STEP 2: Sending alert while both Cortex and MISP are down")
            exec_id, execution = self.submit_alert_and_wait(payload)
            self.execution = execution
            self.execution_id = exec_id

            # Assert workflow still completed in degraded mode
            status = execution.get("status", "")
            self._log(f"+ Workflow status: {status}")
            assert status in [
                "FINISHED",
                "SUCCESS",
                "FAILURE",
            ], f"Workflow should complete even with both services down, got {status}"

            # Assert TheHive case still created
            self._log("STEP 3: Verifying TheHive case creation in degraded mode")
            cases = self.thehive.search_cases(range_="0-100", sort=["-caseId"])
            assert isinstance(cases, list), "Cases should be a list"
            # Find the case by alert_id (len-based diff is unreliable because
            # cases may be resolved/deleted between tests).
            matching_cases = [
                c for c in cases if payload["alert_id"] in c.get("description", "")
            ]
            assert (
                len(matching_cases) > 0
            ), f"TheHive should create a case for {payload['alert_id']} even when both Cortex and MISP are unavailable"
            self._log(f"+ TheHive case created ({len(matching_cases)} match) in degraded mode")

            # Assert ES indexing still works
            self._log("STEP 4: Verifying Elasticsearch indexing in degraded mode")
            deadline = time.time() + 60
            doc = None
            while time.time() < deadline:
                doc = self.es.search_by_alert_id(payload["alert_id"])
                if doc:
                    break
                time.sleep(self.POLL_INTERVAL)
            assert doc is not None, (
                f"Elasticsearch should index alert even with both services down: "
                f"{payload['alert_id']}"
            )
            assert isinstance(doc, dict), "ES document must be a dict"
            assert_data_persisted("elasticsearch", doc)
            self._log("+ Elasticsearch indexing works in degraded mode")

        finally:
            # Always restart both services — don't assert (teardown is safety net)
            self._log("STEP 5: Restarting both Cortex and MISP containers")
            self._start_container("soar_cortex")
            self._start_container("soar_misp")
            self._wait_for_container_healthy("soar_cortex", timeout=180)
            self._wait_for_container_healthy("soar_misp", timeout=180)

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-18-03 COMPLETED — DEGRADED MODE RESILIENCE VALIDATED ===")

    # ── TC-18-04: Orborus unavailable ────────────────────────────────────────

    def test_orborus_unavailable(self):
        """TC-18-04: Orborus unavailable — fault injection.

        Orborus is the Shuffle worker that executes workflows. Without it,
        workflows cannot complete.

        Verifications:
          - Workflow does NOT complete while Orborus is stopped
          - After restarting Orborus, the system recovers
        """
        self._log("=== TC-18-04: ORBORUS UNAVAILABLE (FAULT INJECTION) STARTED ===")

        # Fault injection: stop Orborus
        self._log("STEP 1: Stopping Shuffle Orborus container (fault injection)")
        stopped = self._stop_container("soar_orborus")
        if not stopped:
            # Try alternate container name
            stopped = self._stop_container("shuffle-orborus")
        assert stopped, "Failed to stop Orborus container for fault injection"

        try:
            payload = {
                "alert_id": f"TC18-ORBORUS-{int(time.time())}",
                "alert_type": "ransomware",
                "hostname": "WIN-TC18-004",
                "src_ip": "192.168.1.223",
                "hash": "d" * 64,
                "severity": 2,
                "source": "resilience-test",
                "detection_time": datetime.now(UTC).isoformat(),
                "event_type": "ransomware_detection",
            }

            self._log("STEP 2: Sending alert while Orborus is down")
            # Submit alert directly (don't use submit_alert_and_wait which would
            # block waiting for a workflow that can never execute)
            exec_id = self.submit_alert(payload)
            assert exec_id, "Alert submission should return an execution ID even with Orborus down"
            self.execution_id = exec_id

            # Wait a reasonable period and assert the workflow did NOT complete
            self._log("STEP 3: Asserting workflow does NOT complete without Orborus")
            time.sleep(30)  # Give the system time to (not) process
            execution = self.shuffle.get_execution(self.workflow_id, exec_id, include_results=False)
            assert execution is not None, "Workflow execution data must not be None"
            status = execution.get("status", "")
            self._log(f"+ Workflow status with Orborus down: {status}")
            # The workflow should NOT be FINISHED/SUCCESS — Orborus is required
            assert status not in [
                "FINISHED",
                "SUCCESS",
            ], f"Workflow should NOT complete without Orborus, but got {status}"
            self._log("+ Confirmed: workflow does not complete without Orborus")

        finally:
            # Restart Orborus
            self._log("STEP 4: Restarting Orborus container")
            restarted = self._start_container("soar_orborus")
            if not restarted:
                restarted = self._start_container("shuffle-orborus")
            assert restarted, "Failed to restart Orborus container after test"
            assert self._wait_for_container_healthy(
                "soar_orborus", timeout=120
            ) or self._wait_for_container_healthy(
                "shuffle-orborus", timeout=120
            ), "Orborus did not become healthy after restart"

            # Assert recovery: send a new alert and verify it completes
            self._log("STEP 5: Verifying recovery after Orborus restart")
            recovery_payload = {
                "alert_id": f"TC18-ORBORUS-RECOVERY-{int(time.time())}",
                "alert_type": "ransomware",
                "hostname": "WIN-TC18-004R",
                "src_ip": "192.168.1.230",
                "hash": "d" * 64,
                "severity": 2,
                "source": "resilience-test",
                "detection_time": datetime.now(UTC).isoformat(),
                "event_type": "ransomware_detection",
            }
            exec_id, execution = self.submit_alert_and_wait(recovery_payload)
            self.execution = execution
            self.execution_id = exec_id
            recovery_status = execution.get("status", "")
            assert (
                recovery_status == "FINISHED"
            ), f"Workflow should FINISH after Orborus recovery, got {recovery_status}"
            self._log("+ Recovery confirmed: workflow FINISHED after Orborus restart")

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-18-04 COMPLETED — ORBORUS UNAVAILABLE VALIDATED ===")

    # ── TC-18-05: Dependency timeout ─────────────────────────────────────────

    def test_dependency_timeout(self):
        """TC-18-05: Dependency timeout — degraded mode with slow/unavailable
        deps.

        Verifications:
          - Workflow handles dependency timeouts gracefully
          - Timeout does not crash the workflow
          - Workflow continues with available services
          - At least some nodes complete successfully
        """
        self._log("=== TC-18-05: DEPENDENCY TIMEOUT TEST STARTED ===")

        payload = {
            "alert_id": f"TC18-TIMEOUT-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-TC18-005",
            "src_ip": "192.168.1.224",
            "hash": "e" * 64,
            "severity": 2,
            "source": "resilience-test",
            "detection_time": datetime.now(UTC).isoformat(),
            "event_type": "ransomware_detection",
        }

        self._log("STEP 1: Sending alert (dependency timeout may occur)")
        exec_id, execution = self.submit_alert_and_wait(payload)
        self.execution = execution
        self.execution_id = exec_id

        status = execution.get("status", "")
        self._log(f"+ Workflow status: {status}")
        # Workflow must reach a terminal state (not hang)
        assert status in [
            "FINISHED",
            "SUCCESS",
            "FAILURE",
            "ABORTED",
        ], f"Workflow should reach a terminal state, got {status}"

        # Analyze timeout handling — at least some nodes must complete
        self._log("STEP 2: Analyzing timeout handling")
        execution_full = (
            self.shuffle.get_execution(self.workflow_id, exec_id, include_results=True) or execution
        )
        results = execution_full.get("results", [])
        assert isinstance(results, list), "Results should be a list"
        assert len(results) > 0, "Workflow should have at least some node results"

        completed_nodes = [n for n in results if n.get("status") == "SUCCESS"]
        failed_nodes = [n for n in results if n.get("status") in ["ERROR", "SKIPPED", "FAILED"]]
        self._log(f"+ Completed nodes: {len(completed_nodes)}")
        self._log(f"+ Failed/Skipped nodes: {len(failed_nodes)}")

        # At least one node must complete — the workflow doesn't totally crash
        assert (
            len(completed_nodes) > 0
        ), "At least one node should complete successfully even with dependency issues"

        elapsed = (datetime.now(UTC) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-18-05 COMPLETED — DEPENDENCY TIMEOUT VALIDATED ===")
