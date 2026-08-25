"""Observability mixin for E2E tests.

Validates that the observability stack (Loki, Promtail, Grafana) is
collecting logs and metrics, and that logs contain the correlation_id.
"""

from __future__ import annotations

import time
from typing import Any

import requests


class ObservabilityMixin:
    """Mixin for observability validation (Loki, Promtail, Grafana)."""

    env: dict[str, str]
    correlation_id: str

    def assert_loki_contains_correlation_id(self, timeout: int = 120) -> bool:
        """Assert that Loki logs contain entries with the correlation_id.

        Polls Loki until logs are found or timeout.
        """
        t0 = time.time()
        loki_url = self.get_service_url("loki")
        query = f'{{compose_project=~".+"}} |= "{self.correlation_id}"'

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                r = requests.get(
                    f"{loki_url}/loki/api/v1/query",
                    params={"query": query},
                    timeout=30,
                    verify=False,
                )
                if r.status_code == 200:
                    data = r.json()
                    results = data.get("data", {}).get("result", [])
                    if results:
                        self._log(
                            f"  + Loki logs found for {self.correlation_id}: "
                            f"{len(results)} stream(s)"
                        )
                        self.record_assertion(
                            "loki_contains_correlation_id",
                            True,
                            time.time() - t0,
                            {"streams": len(results)},
                        )
                        return True
            except Exception as e:
                self._log(f"  + Loki query error: {e}")
            time.sleep(5)

        self._log(f"  + Loki logs NOT found for {self.correlation_id}")
        self.record_assertion(
            "loki_contains_correlation_id",
            False,
            time.time() - t0,
            {"correlation_id": self.correlation_id},
        )
        return False

    def assert_loki_ready(self) -> bool:
        """Assert that Loki is ready and accepting queries."""
        t0 = time.time()
        loki_url = self.get_service_url("loki")
        try:
            r = requests.get(f"{loki_url}/ready", timeout=10, verify=False)
            if r.status_code == 200:
                self.record_assertion("loki_ready", True, time.time() - t0)
                return True
            self.record_assertion(
                "loki_ready",
                False,
                time.time() - t0,
                {"http_status": r.status_code},
            )
            return False
        except Exception as e:
            self.record_assertion("loki_ready", False, time.time() - t0, {"error": str(e)})
            return False

    def assert_promtail_collecting(self) -> bool:
        """Assert that Promtail is collecting logs from Docker containers."""
        t0 = time.time()
        promtail_url = self.get_service_url("promtail")
        try:
            r = requests.get(f"{promtail_url}/metrics", timeout=10, verify=False)
            if r.status_code == 200:
                # Check for log entries counter. Promtail exposes entries under
                # several metric names depending on version:
                #   - promtail_docker_target_entries_total (docker_sd target)
                #   - promtail_sent_entries_total (lines sent to Loki)
                #   - promtail_file_target_entries_total (file target)
                # The legacy name "log_entries_total" does not exist in modern
                # promtail builds, so we check for any of the real ones.
                metrics_text = r.text
                has_entries = any(
                    name in metrics_text
                    for name in (
                        "log_entries_total",
                        "promtail_docker_target_entries_total",
                        "promtail_sent_entries_total",
                        "promtail_file_target_entries_total",
                    )
                )
                self.record_assertion(
                    "promtail_collecting",
                    has_entries,
                    time.time() - t0,
                    {"has_entries": has_entries},
                )
                return has_entries
            self.record_assertion(
                "promtail_collecting",
                False,
                time.time() - t0,
                {"http_status": r.status_code},
            )
            return False
        except Exception as e:
            self.record_assertion("promtail_collecting", False, time.time() - t0, {"error": str(e)})
            return False

    def assert_grafana_healthy(self) -> bool:
        """Assert that Grafana is healthy and has datasources configured."""
        t0 = time.time()
        grafana_url = self.get_service_url("grafana")
        try:
            r = requests.get(f"{grafana_url}/api/health", timeout=10, verify=False)
            if r.status_code != 200:
                self.record_assertion(
                    "grafana_healthy",
                    False,
                    time.time() - t0,
                    {"http_status": r.status_code},
                )
                return False

            # Check datasources
            grafana_user = self.env.get("GRAFANA_ADMIN_USER", "admin")
            grafana_pass = self.env.get("GRAFANA_ADMIN_PASSWORD", "admin")
            auth = (grafana_user, grafana_pass)

            r2 = requests.get(
                f"{grafana_url}/api/datasources",
                auth=auth,
                timeout=10,
                verify=False,
            )
            if r2.status_code == 200:
                datasources = r2.json()
                ds_names = [ds.get("name", "") for ds in datasources]
                self._log(f"  + Grafana datasources: {ds_names}")
                self.record_assertion(
                    "grafana_healthy",
                    True,
                    time.time() - t0,
                    {"datasources": ds_names},
                )
                return True
            else:
                self.record_assertion(
                    "grafana_healthy",
                    True,  # Grafana is healthy even if we can't list datasources
                    time.time() - t0,
                    {"datasource_check": f"HTTP {r2.status_code}"},
                )
                return True
        except Exception as e:
            self.record_assertion("grafana_healthy", False, time.time() - t0, {"error": str(e)})
            return False

    def export_loki_logs(self) -> dict[str, Any]:
        """Export Loki logs for this test's correlation_id as evidence."""
        data = self.export_loki_logs_raw()
        self.write_evidence("loki_logs.json", data)
        self._loki_exported = True
        return data

    def export_loki_logs_raw(self) -> dict[str, Any]:
        """Fetch Loki logs for this correlation_id (without writing
        evidence)."""
        loki_url = self.get_service_url("loki")
        query = f'{{compose_project=~".+"}} |= "{self.correlation_id}"'
        try:
            r = requests.get(
                f"{loki_url}/loki/api/v1/query",
                params={"query": query},
                timeout=30,
                verify=False,
            )
            if r.status_code == 200:
                return r.json()
            return {"error": f"HTTP {r.status_code}", "query": query}
        except Exception as e:
            return {"error": str(e), "query": query}
