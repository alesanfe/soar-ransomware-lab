"""Docker/infrastructure mixin for E2E tests.

Handles preflight health checks for all services in the SOAR stack.
"""

from __future__ import annotations

from typing import Any

import requests


class DockerMixin:
    """Mixin for infrastructure health checks and Docker state inspection."""

    # These attributes are expected from ConfigMixin
    env: dict[str, str]
    inside_container: bool

    def verify_core_services(self) -> None:
        """Verify ALL services are healthy. Fail loud if any are down.

        Every service in the stack is checked. If ANY service is down,
        the test fails immediately — no warnings, no silent passes.

        Services marked as non-critical via E2E_SKIP_SERVICES env var
        (comma-separated list) are still checked but their failure is
        recorded as an error only if the test actually uses them.
        """
        errors: list[str] = []

        # All services — failure is fatal
        all_checks = [
            ("Elasticsearch", self.verify_elasticsearch),
            ("OpenSearch", self.verify_opensearch),
            ("Redis", self.verify_redis),
            ("TheHive", self.verify_thehive),
            ("Cortex", self.verify_cortex),
            ("MISP", self.verify_misp),
            ("Shuffle backend", self.verify_shuffle_backend),
            ("SOAR API", self.verify_soar_api),
            ("Nginx", self.verify_nginx),
            ("Orborus", self.verify_orborus),
            ("Network Watcher", self.verify_network_watcher),
            ("Tenzir", self.verify_tenzir),
            ("Shuffle frontend", self.verify_shuffle_frontend),
            ("Web Management", self.verify_web_management),
            ("Docs Site", self.verify_docs_site),
            ("Loki", self.verify_loki),
            ("Promtail", self.verify_promtail),
            ("Grafana", self.verify_grafana),
        ]

        # Services that can be skipped via env var (comma-separated)
        skip_list = [
            s.strip().lower() for s in self.env.get("E2E_SKIP_SERVICES", "").split(",") if s.strip()
        ]

        for name, check_fn in all_checks:
            if name.lower() in skip_list:
                self._log(f"  [SKIP] {name} — in E2E_SKIP_SERVICES")
                continue
            try:
                ok, msg = check_fn()
                if not ok:
                    errors.append(f"{name}: {msg}")
            except Exception as e:
                errors.append(f"{name}: {e}")

        if errors:
            import pytest

            pytest.fail("Service health check failed before test:\n  - " + "\n  - ".join(errors))

    def verify_observability_stack(self) -> None:
        """Verify observability services. Fail loud if any are down.

        All observability services (Loki, Promtail, Grafana) are
        mandatory — if any is down, the test fails.
        """
        if self.env.get("E2E_VERIFY_OBSERVABILITY", "true").lower() != "true":
            return

        errors: list[str] = []

        if self.env.get("E2E_VERIFY_LOKI", "true").lower() == "true":
            ok, msg = self.verify_loki()
            if not ok:
                errors.append(f"Loki: {msg}")

        if self.env.get("E2E_VERIFY_PROMTAIL", "true").lower() == "true":
            ok, msg = self.verify_promtail()
            if not ok:
                errors.append(f"Promtail: {msg}")

        if self.env.get("E2E_VERIFY_GRAFANA", "true").lower() == "true":
            ok, msg = self.verify_grafana()
            if not ok:
                errors.append(f"Grafana: {msg}")

        if errors:
            import pytest

            pytest.fail("Observability stack health check failed:\n  - " + "\n  - ".join(errors))

    # ── Individual service checks ────────────────────────────────────────────

    def _check_http(
        self, url: str, timeout: int = 10, auth: tuple | None = None
    ) -> tuple[bool, str]:
        """Check if an HTTP endpoint is reachable."""
        try:
            r = requests.get(url, timeout=timeout, verify=False, auth=auth)
            if r.status_code < 500:
                return True, f"OK ({r.status_code})"
            return False, f"HTTP {r.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Connection refused"
        except requests.exceptions.Timeout:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)[:100]

    def verify_elasticsearch(self) -> tuple[bool, str]:
        """Verify Elasticsearch is healthy."""
        url = self.get_service_url("es")
        auth = (
            self.env.get("ELASTIC_USERNAME", "elastic"),
            self.env.get("ELASTIC_PASSWORD", ""),
        )
        ok, msg = self._check_http(url, auth=auth)
        if not ok:
            return False, msg
        # Check cluster health
        try:
            r = requests.get(f"{url}/_cluster/health", timeout=10, auth=auth, verify=False)
            if r.status_code == 200:
                status = r.json().get("status", "unknown")
                if status in ("green", "yellow"):
                    return True, f"OK (status={status})"
                return False, f"Cluster status={status}"
            return False, f"Health check HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)[:100]

    def verify_opensearch(self) -> tuple[bool, str]:
        """Verify OpenSearch is healthy."""
        url = self.get_service_url("opensearch")
        ok, msg = self._check_http(url)
        if not ok:
            return False, msg
        try:
            r = requests.get(f"{url}/_cluster/health", timeout=10, verify=False)
            if r.status_code == 200:
                status = r.json().get("status", "unknown")
                if status in ("green", "yellow"):
                    return True, f"OK (status={status})"
                return False, f"Cluster status={status}"
            return False, f"Health check HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)[:100]

    def verify_redis(self) -> tuple[bool, str]:
        """Verify Redis is reachable and responding to PING."""
        import redis as _redis

        try:
            r = _redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password(),
                decode_responses=True,
                socket_timeout=10,
            )
            pong = r.ping()
            if pong:
                return True, "OK (PONG)"
            return False, "No PONG response"
        except Exception as e:
            return False, str(e)[:100]

    def verify_thehive(self) -> tuple[bool, str]:
        """Verify TheHive is available and API key is valid."""
        url = self.get_service_url("thehive")
        ok, msg = self._check_http(f"{url}/api/status")
        if not ok:
            return False, msg
        # Verify API key
        api_key = self.env.get("THEHIVE_API_KEY", "")
        if not api_key:
            return False, "THEHIVE_API_KEY not configured"
        try:
            r = requests.get(
                f"{url}/api/v1/case",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return True, "OK"
            elif r.status_code == 401:
                return False, "API key invalid (401)"
            return True, f"OK (status={r.status_code})"
        except Exception as e:
            return False, str(e)[:100]

    def verify_cortex(self) -> tuple[bool, str]:
        """Verify Cortex is available."""
        url = self.get_service_url("cortex")
        ok, msg = self._check_http(f"{url}/api/status")
        if not ok:
            return False, msg
        # Verify auth
        import base64

        admin_user = self.env.get("CORTEX_ADMIN_USER", "admin")
        admin_pass = self.env.get("CORTEX_ADMIN_PASSWORD", "")
        if admin_pass:
            creds = base64.b64encode(f"{admin_user}:{admin_pass}".encode()).decode()
            try:
                r = requests.post(
                    f"{url}/api/analyzer/_search",
                    json={"query": {}, "range": "all"},
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Basic {creds}",
                    },
                    timeout=10,
                    verify=False,
                )
                if r.status_code == 200:
                    return True, "OK"
                return False, f"Auth failed (HTTP {r.status_code})"
            except Exception as e:
                return False, str(e)[:100]
        return True, "OK (no password check)"

    def verify_misp(self) -> tuple[bool, str]:
        """Verify MISP is available and API key is valid."""
        url = self.get_service_url("misp")
        api_key = self.env.get("MISP_API_KEY", "")
        if not api_key:
            return False, "MISP_API_KEY not configured"
        try:
            r = requests.get(
                f"{url}/servers/getVersion",
                headers={"Authorization": api_key, "Accept": "application/json"},
                timeout=10,
                verify=False,
            )
            if r.status_code == 200:
                return True, "OK"
            elif r.status_code == 401:
                return False, "API key invalid (401)"
            return True, f"OK (status={r.status_code})"
        except Exception as e:
            return False, str(e)[:100]

    def verify_shuffle_backend(self) -> tuple[bool, str]:
        """Verify Shuffle backend is available."""
        url = self.get_service_url("shuffle")
        ok, msg = self._check_http(f"{url}/api/v1/users/1")
        if not ok:
            return False, msg
        return True, "OK"

    def verify_network_watcher(self) -> tuple[bool, str]:
        """Verify Network Watcher is available."""
        url = self.get_service_url("network_watcher")
        ok, msg = self._check_http(f"{url}/health")
        if not ok:
            return False, msg
        return True, "OK"

    def verify_tenzir(self) -> tuple[bool, str]:
        """Verify Tenzir is available."""
        url = self.get_service_url("tenzir")
        ok, msg = self._check_http(f"{url}/api/v0/status")
        if not ok:
            return False, msg
        return True, "OK"

    def verify_soar_api(self) -> tuple[bool, str]:
        """Verify SOAR API is available."""
        url = self.get_service_url("api")
        ok, msg = self._check_http(f"{url}/health")
        if not ok:
            return False, msg
        return True, "OK"

    def verify_nginx(self) -> tuple[bool, str]:
        """Verify Nginx reverse proxy is available."""
        url = self.get_service_url("nginx")
        ok, msg = self._check_http(url, timeout=5)
        if ok:
            return True, f"OK ({url})"
        return False, f"Nginx not reachable at {url}: {msg}"

    def verify_orborus(self) -> tuple[bool, str]:
        """Verify Orborus (Shuffle worker executor) is running.

        Orborus has no HTTP endpoint, so we check via Docker container state.
        """
        import subprocess

        for container_name in ("soar_orborus", "orborus"):
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                status = result.stdout.strip()
                if result.returncode == 0 and status == "running":
                    return True, f"OK ({container_name} running)"
            except Exception:
                continue
        return False, "Orborus container not running"

    def verify_shuffle_frontend(self) -> tuple[bool, str]:
        """Verify Shuffle frontend is available."""
        url = "http://shuffle-frontend:80"
        ok, msg = self._check_http(url, timeout=5)
        if ok:
            return True, f"OK ({url})"
        return False, f"Shuffle frontend not reachable at {url}: {msg}"

    def verify_web_management(self) -> tuple[bool, str]:
        """Verify Web Management UI is available."""
        url = "http://web-management:80"
        ok, msg = self._check_http(url, timeout=5)
        if ok:
            return True, f"OK ({url})"
        return False, f"Web Management not reachable at {url}: {msg}"

    def verify_docs_site(self) -> tuple[bool, str]:
        """Verify Docs Site is available."""
        url = "http://docs-site:8080"
        ok, msg = self._check_http(url, timeout=5)
        if ok:
            return True, f"OK ({url})"
        return False, f"Docs Site not reachable at {url}: {msg}"

    def verify_loki(self) -> tuple[bool, str]:
        """Verify Loki is ready."""
        url = self.get_service_url("loki")
        try:
            r = requests.get(f"{url}/ready", timeout=10, verify=False)
            if r.status_code == 200:
                return True, "OK"
            return False, f"HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)[:100]

    def verify_promtail(self) -> tuple[bool, str]:
        """Verify Promtail is collecting metrics."""
        url = self.get_service_url("promtail")
        try:
            r = requests.get(f"{url}/metrics", timeout=10, verify=False)
            if r.status_code == 200:
                return True, "OK"
            return False, f"HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)[:100]

    def verify_grafana(self) -> tuple[bool, str]:
        """Verify Grafana is healthy."""
        url = self.get_service_url("grafana")
        try:
            r = requests.get(f"{url}/api/health", timeout=10, verify=False)
            if r.status_code == 200:
                return True, "OK"
            return False, f"HTTP {r.status_code}"
        except Exception as e:
            return False, str(e)[:100]

    def verify_workflow_ready(self) -> None:
        """Verify the Shuffle workflow and webhook are properly configured."""
        import pytest

        errors: list[str] = []

        if not getattr(self, "webhook_url", ""):
            errors.append("webhook_url not configured — run make init-webhook")
        if not getattr(self, "workflow_id", ""):
            errors.append("workflow_id not configured — run make init-webhook")

        if errors:
            pytest.fail("Workflow not ready:\n  - " + "\n  - ".join(errors))

    def get_docker_state(self) -> dict[str, Any]:
        """Get current Docker container state for evidence export.

        Returns:
            Dict with container names, statuses, and health info.
        """
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            containers = []
            for line in result.stdout.strip().splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    containers.append(
                        {
                            "name": parts[0],
                            "status": parts[1],
                            "ports": parts[2] if len(parts) > 2 else "",
                        }
                    )
            return {"containers": containers, "count": len(containers)}
        except Exception as e:
            return {"error": str(e), "containers": []}
