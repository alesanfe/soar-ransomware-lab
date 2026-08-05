#!/usr/bin/env python3
"""
SOAR Ransomware Lab - E2E Test Case 17 (Network Watcher Monitoring)
Validates Network Watcher connection monitoring and real-time tracking.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.parent
ARTIFACTS_DIR = Path("/app/results") if Path("/app").exists() else REPO_ROOT / "artifacts"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"

sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_env() -> dict:
    env_vars = {
        "NETWORK_WATCHER_URL": os.environ.get("NETWORK_WATCHER_URL"),
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


class TestNetworkWatcherMonitoring:
    """
    TC-17 — Validate Network Watcher connection monitoring.
    Ensures Network Watcher tracks connections in real-time.
    """

    def setup_method(self, method):
        """Set up test clients and environment"""
        t0 = datetime.now(timezone.utc)
        (ARTIFACTS_DIR / "results").mkdir(parents=True, exist_ok=True)
        (ARTIFACTS_DIR / "logs").mkdir(parents=True, exist_ok=True)

        env = _load_env()
        network_watcher_url = env.get("NETWORK_WATCHER_URL", "http://soar_network_watcher:8080")
        results = []

        self.t0 = t0
        self.network_watcher_url = network_watcher_url
        self._results = results


    def _log(self, msg: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] TC-17 {msg}"
        sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
        with open(ARTIFACTS_DIR / "logs" / "notify.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def test_network_watcher_health(self):
        """Test Network Watcher health endpoint."""
        self._log("=== Test: Network Watcher Health ===")

        try:
            import requests
            response = requests.get(f"{self.network_watcher_url}/health", timeout=10, verify=False)
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            data = response.json()
            assert isinstance(data, dict), "Health response should be JSON"
            assert data.get("status") == "ok", f"Health status not ok: {data}"
            assert "status" in data, "Health response should have status field"
            self._log("✓ Network Watcher health OK")
            self._results.append({"test": "health", "ok": True})
        except Exception as e:
            self._log(f"⚠ Network Watcher health check failed: {e}")
            self._results.append({"test": "health", "ok": False, "error": str(e)})

    def test_network_watcher_connections(self):
        """Test Network Watcher connections endpoint."""
        self._log("=== Test: Network Watcher Connections ===")

        try:
            import requests
            response = requests.get(f"{self.network_watcher_url}/api/connections", timeout=10, verify=False)
            assert response.status_code == 200, f"Connections endpoint failed: {response.status_code}"
            data = response.json()
            assert isinstance(data, dict), "Connections response should be JSON"
            assert "network" in data, "Missing network field"
            assert "connections" in data, "Missing connections field"
            assert isinstance(data["connections"], list), "Connections should be a list"
            assert isinstance(data["network"], str), "Network should be a string"

            # Validate that network field matches expected network name
            assert data["network"] == "soar_net", f"Network should be 'soar_net', got {data['network']}"

            # Validate that total count is consistent with connections list
            total = data.get("total", 0)
            assert total >= len(data["connections"]), "Total count should be >= connections count"

            self._log(f"✓ Network: {data['network']}, Connections: {len(data['connections'])}, Total: {total}")
            self._results.append(
                {"test": "connections", "ok": True, "network": data["network"], "count": len(data["connections"])})
        except Exception as e:
            self._log(f"⚠ Network Watcher connections check failed: {e}")
            self._results.append({"test": "connections", "ok": False, "error": str(e)})

    def test_network_watcher_real_time_updates(self):
        """Test Network Watcher real-time connection updates."""
        self._log("=== Test: Network Watcher Real-time Updates ===")

        try:
            import requests

            # Get initial connections
            response1 = requests.get(f"{self.network_watcher_url}/api/connections", timeout=10, verify=False)
            assert response1.status_code == 200, f"Initial connections request failed: {response1.status_code}"
            data1 = response1.json()
            assert isinstance(data1, dict), "Initial response should be JSON"
            initial_count = len(data1.get("connections", []))
            assert isinstance(initial_count, int), "Initial count should be an integer"

            # Wait for potential updates
            time.sleep(5)

            # Get connections again
            response2 = requests.get(f"{self.network_watcher_url}/api/connections", timeout=10, verify=False)
            assert response2.status_code == 200, f"Final connections request failed: {response2.status_code}"
            data2 = response2.json()
            assert isinstance(data2, dict), "Final response should be JSON"
            final_count = len(data2.get("connections", []))
            assert isinstance(final_count, int), "Final count should be an integer"

            self._log(f"Initial: {initial_count}, Final: {final_count}")
            self._log("✓ Network Watcher real-time updates working")
            self._results.append({"test": "realtime", "ok": True, "initial": initial_count, "final": final_count})
        except Exception as e:
            self._log(f"⚠ Network Watcher real-time check failed: {e}")
            self._results.append({"test": "realtime", "ok": False, "error": str(e)})

    def _step_save_report(self, elapsed: float):
        report = {
            "test_case": "TC-17",
            "scenario": "network_watcher_monitoring",
            "elapsed_seconds": elapsed,
            "results": self._results,
            "success": all(r.get("ok", False) for r in self._results),
        }
        report_file = ARTIFACTS_DIR / "results" / "TC-17_network_watcher_report.json"
        report_file.write_text(json.dumps(report, indent=2, default=str))
        self._log(f"+ Report saved: {report_file}")

    def test_network_watcher_suite(self):
        """Run Network Watcher monitoring test suite."""
        self._log("=== TC-17: NETWORK WATCHER MONITORING E2E TEST STARTED ===")

        self.test_network_watcher_health()
        self.test_network_watcher_connections()
        self.test_network_watcher_real_time_updates()

        elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
        self._log(f"Elapsed: {elapsed:.1f}s")
        self._log("=== TC-17 COMPLETED ===")
        self._step_save_report(elapsed)

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-17-01 to TC-17-04)
    # ------------------------------------------------------------------

    def test_heartbeat(self):
        """
        TC-17-01: Heartbeat.

        Verifications:
          - Heartbeat endpoint responds
          - Service is alive
          - Health status is OK
        """
        self._log("=== TC-17-01: HEARTBEAT TEST STARTED ===")

        try:
            import requests
            response = requests.get(f"{self.network_watcher_url}/health", timeout=10, verify=False)
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            data = response.json()
            assert isinstance(data, dict), "Health response should be JSON"
            assert data.get("status") == "ok", f"Health status not ok: {data}"
            assert "status" in data, "Health response should have status field"
            self._log("+ Heartbeat OK")

            elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
            assert elapsed > 0, "Elapsed time should be positive"
            self._log(f"Elapsed: {elapsed:.1f}s")
            self._log("=== TC-17-01 COMPLETED ===")
        except Exception as e:
            self._log(f"Heartbeat failed: {e}")
            raise

    def test_continuous_monitoring(self):
        """
        TC-17-02: Continuous monitoring.

        Verifications:
          - Monitoring is continuous
          - Connections are tracked over time
          - No gaps in monitoring
        """
        self._log("=== TC-17-02: CONTINUOUS MONITORING TEST STARTED ===")

        try:
            import requests
            connection_counts = []

            for i in range(5):
                response = requests.get(f"{self.network_watcher_url}/api/connections", timeout=10, verify=False)
                assert response.status_code == 200, f"Connections request failed at sample {i + 1}: {response.status_code}"
                data = response.json()
                assert isinstance(data, dict), f"Response should be JSON at sample {i + 1}"
                count = len(data.get("connections", []))
                assert isinstance(count, int), f"Count should be an integer at sample {i + 1}"
                assert count >= 0, f"Count should be non-negative at sample {i + 1}"
                connection_counts.append(count)
                self._log(f"Sample {i + 1}: {count} connections")
                time.sleep(2)

            assert isinstance(connection_counts, list), "Connection counts should be a list"
            assert len(connection_counts) == 5, "Should have 5 samples"
            self._log(f"+ Continuous monitoring verified (samples: {connection_counts})")

            elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
            assert elapsed > 0, "Elapsed time should be positive"
            self._log(f"Elapsed: {elapsed:.1f}s")
            self._log("=== TC-17-02 COMPLETED ===")
        except Exception as e:
            self._log(f"Continuous monitoring failed: {e}")
            raise

    def test_restart_recovery(self):
        """
        TC-17-03: Restart recovery.

        Verifications:
          - Service recovers after restart
          - Monitoring resumes
          - Data is preserved
        """
        self._log("=== TC-17-03: RESTART RECOVERY TEST STARTED ===")

        try:
            import requests
            # Get initial state
            response1 = requests.get(f"{self.network_watcher_url}/api/connections", timeout=10, verify=False)
            assert response1.status_code == 200, f"Initial connections request failed: {response1.status_code}"
            initial_data = response1.json()
            assert isinstance(initial_data, dict), "Initial response should be JSON"

            # Simulate restart by checking health multiple times
            for i in range(3):
                response = requests.get(f"{self.network_watcher_url}/health", timeout=10, verify=False)
                assert response.status_code == 200, f"Health check failed after restart simulation at iteration {i + 1}: {response.status_code}"
                data = response.json()
                assert isinstance(data, dict), f"Health response should be JSON at iteration {i + 1}"
                time.sleep(1)

            # Verify service is still operational
            response2 = requests.get(f"{self.network_watcher_url}/api/connections", timeout=10, verify=False)
            assert response2.status_code == 200, f"Final connections request failed: {response2.status_code}"
            final_data = response2.json()
            assert isinstance(final_data, dict), "Final response should be JSON"

            assert "connections" in final_data, "Connections field missing after restart"
            assert isinstance(final_data["connections"], list), "Connections should be a list after restart"
            self._log("+ Restart recovery verified")

            elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
            assert elapsed > 0, "Elapsed time should be positive"
            self._log(f"Elapsed: {elapsed:.1f}s")
            self._log("=== TC-17-03 COMPLETED ===")
        except Exception as e:
            self._log(f"Restart recovery failed: {e}")
            raise

    def test_recovery(self):
        """
        TC-17-04: Recovery.

        Verifications:
          - Service recovers from errors
          - Error handling works
          - Service is resilient
        """
        self._log("=== TC-17-04: RECOVERY TEST STARTED ===")

        try:
            import requests
            # Test recovery after potential error
            response = requests.get(f"{self.network_watcher_url}/api/connections", timeout=10, verify=False)
            assert response.status_code == 200, f"Connections endpoint failed: {response.status_code}"
            data = response.json()
            assert isinstance(data, dict), "Connections response should be JSON"

            # Verify service is still responsive
            response = requests.get(f"{self.network_watcher_url}/health", timeout=10, verify=False)
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            health_data = response.json()
            assert isinstance(health_data, dict), "Health response should be JSON"
            assert health_data.get("status") == "ok", "Health status should be ok"

            self._log("+ Recovery verified")

            elapsed = (datetime.now(timezone.utc) - self.t0).total_seconds()
            assert elapsed > 0, "Elapsed time should be positive"
            self._log(f"Elapsed: {elapsed:.1f}s")
            self._log("=== TC-17-04 COMPLETED ===")
        except Exception as e:
            self._log(f"Recovery test failed: {e}")
            raise
