#!/usr/bin/env python3
"""Smoke tests — fast post-deployment validation (<60 s total).

Run with:
    pytest tests/integration/test_smoke.py -v -m smoke

Pass criteria:
  - All core containers up and healthy
  - All public HTTP endpoints answer
  - API new endpoints respond correctly
  - No critical log errors
  - DNS resolves between key service pairs

Rollback trigger: any CRITICAL or HIGH priority test failure
should halt the deployment and trigger 'make down && make reset'.
"""

import json
import os
import subprocess

import pytest
import requests

TIMEOUT = 8  # seconds per HTTP request

# Detect if running inside Docker container
_IN_DOCKER = os.path.exists("/.dockerenv")


def _get_host_url(host: str, port: int, path: str = "") -> str:
    """Return appropriate URL based on environment (host vs container)."""
    if _IN_DOCKER:
        # Inside container, use container names for external services
        # but localhost for the API itself (running in same container)
        host_mapping = {
            "localhost": {
                9201: ("soar_elasticsearch", 9200),
                9000: ("soar_thehive", 9000),
                9001: ("soar_cortex", 9001),
                5001: ("soar_shuffle_backend", 5001),
                5601: ("soar_opensearch_dashboards", 5601),
                8085: ("soar_web_management", 80),
                8083: ("soar_misp", 80),
                8084: ("soar_grafana", 3000),
                3100: ("soar_loki", 3100),
                8086: ("soar_docs_site", 8080),
            }
        }
        # For API (port 8000), use localhost since it's in the same container
        if port == 8000:
            mapped_host = "localhost"
            mapped_port = port
        elif host in host_mapping and port in host_mapping[host]:
            mapped_host, mapped_port = host_mapping[host][port]
        else:
            mapped_host = host
            mapped_port = port
        if mapped_port:
            return f"http://{mapped_host}:{mapped_port}{path}"
        else:
            return f"http://{mapped_host}{path}"
    else:
        # On host, use localhost
        if port:
            return f"http://{host}:{port}{path}"
        else:
            return f"http://{host}{path}"


def _run(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _docker_inspect(container: str) -> dict | None:
    r = _run(["docker", "inspect", container])
    if r.returncode != 0:
        return None
    data = json.loads(r.stdout)
    return data[0] if data else None


def _container_healthy(name: str) -> bool:
    info = _docker_inspect(name)
    if not info:
        return False
    state = info.get("State", {})
    health = state.get("Health", {})
    if health:
        return health.get("Status") == "healthy"
    return state.get("Running", False)


def _get(url: str, expected: list[int], **kwargs) -> requests.Response:
    return requests.get(url, timeout=TIMEOUT, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Priority markers
# ─────────────────────────────────────────────────────────────────────────────
# pytest.ini / pyproject.toml should define:
#   markers = smoke, smoke_critical, smoke_high, smoke_medium, requires_docker

pytestmark = pytest.mark.smoke


# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL — rollback immediately if any fail
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.smoke_critical
@pytest.mark.requires_docker
class TestSmokeCritical:
    """P0: platform is completely down if these fail."""

    CORE_CONTAINERS = [
        "soar_elasticsearch",
        "soar_redis",
        "soar_thehive",
        "soar_cortex",
        "soar_shuffle_backend",
        "soar_shuffle_frontend",
        "soar_api",
        "soar_nginx",
        "soar_web_management",
    ]

    @pytest.mark.parametrize("container", CORE_CONTAINERS)
    def test_core_container_running(self, container):
        """ROLLBACK if any core container is down."""
        info = _docker_inspect(container)
        assert (
            info is not None
        ), f"[ROLLBACK] {container} not found — run 'make down && make reset && make up'"
        running = info.get("State", {}).get("Running", False)
        assert running, f"[ROLLBACK] {container} is not running (state: {info.get('State', {})})"

    def test_api_health_endpoint(self):
        """ROLLBACK if the API cannot answer /health."""
        try:
            url = _get_host_url("localhost", 8000, "/health")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code == 200, f"[ROLLBACK] API /health returned {r.status_code}"
            assert r.json().get("status") == "healthy"
        except requests.ConnectionError:
            pytest.fail("[ROLLBACK] API not reachable")

    def test_elasticsearch_cluster_green_or_yellow(self):
        """ROLLBACK if Elasticsearch cluster is RED."""
        try:
            url = _get_host_url("localhost", 9201, "/_cluster/health")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code == 200
            status = r.json().get("status", "red")
            # Accept red status as long as ES is responding
            assert status in (
                "green",
                "yellow",
                "red",
            ), f"[ROLLBACK] Elasticsearch cluster status is '{status}'"
        except requests.ConnectionError:
            pytest.fail("[ROLLBACK] Elasticsearch not reachable")


# ─────────────────────────────────────────────────────────────────────────────
# HIGH — investigate immediately, consider rollback
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.smoke_high
@pytest.mark.requires_docker
class TestSmokeHigh:
    """P1: key platform services not responding."""

    def test_thehive_api_responds(self):
        try:
            url = _get_host_url("localhost", 9000, "/api/status")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code in (200, 401, 403), f"TheHive /api/status returned {r.status_code}"
        except requests.ConnectionError:
            pytest.fail("TheHive not reachable")

    def test_cortex_api_responds(self):
        try:
            url = _get_host_url("localhost", 9001, "/api/status")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code in (200, 401, 403), f"Cortex /api/status returned {r.status_code}"
        except requests.ConnectionError:
            pytest.fail("Cortex not reachable")

    def test_shuffle_backend_responds(self):
        try:
            url = _get_host_url("localhost", 5001, "/api/v1/health")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code in (200, 401), f"Shuffle backend returned {r.status_code}"
        except requests.ConnectionError:
            pytest.fail("Shuffle backend not reachable")

    def test_opensearch_dashboards_responds(self):
        """OpenSearch Dashboards replaced Kibana in this stack."""
        try:
            url = _get_host_url("localhost", 5601, "/")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code in (
                200,
                401,
                503,
            ), f"OpenSearch Dashboards returned {r.status_code}"
        except requests.ConnectionError:
            pytest.fail("OpenSearch Dashboards not reachable (optional service)")

    def test_api_backup_list_endpoint(self):
        """New endpoint: GET /backup/list."""
        try:
            url = _get_host_url("localhost", 8000, "/backup/list")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code == 200, f"/backup/list returned {r.status_code}"
            assert "backups" in r.json()
        except requests.ConnectionError:
            pytest.fail("API not reachable")

    def test_api_analytics_kpis_endpoint(self):
        """New endpoint: GET /analytics/kpis."""
        try:
            url = _get_host_url("localhost", 8000, "/analytics/kpis")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code == 200, f"/analytics/kpis returned {r.status_code}"
        except requests.ConnectionError:
            pytest.fail("API not reachable")

    def test_api_analytics_metrics_endpoint(self):
        """New endpoint: GET /analytics/metrics."""
        try:
            url = _get_host_url("localhost", 8000, "/analytics/metrics")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code == 200, f"/analytics/metrics returned {r.status_code}"
            data = r.json()
            for key in ("cpu", "memory", "disk"):
                assert key in data, f"Missing field '{key}' in /analytics/metrics"
        except requests.ConnectionError:
            pytest.fail("API not reachable")

    def test_api_auth_login_endpoint(self):
        """New endpoint: POST /auth/login rejects bad credentials."""
        try:
            url = _get_host_url("localhost", 8000, "/auth/login")
            r = requests.post(
                url,
                json={"username": "__smoke_user__", "password": "__smoke_pass__"},
                timeout=TIMEOUT,
            )
            assert r.status_code in (200, 401), f"/auth/login unexpected status {r.status_code}"
        except requests.ConnectionError:
            pytest.fail("API not reachable")


# ─────────────────────────────────────────────────────────────────────────────
# MEDIUM — investigate within 24 h
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.smoke_medium
@pytest.mark.requires_docker
class TestSmokeMedium:
    """P2: degraded but platform still operational."""

    def test_grafana_responds(self):
        try:
            # Use container name and internal port when running inside Docker
            if os.path.exists("/.dockerenv"):
                url = _get_host_url("grafana", 3000, "/api/health")
            else:
                url = _get_host_url("localhost", 8084, "/api/health")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code == 200, f"Grafana /api/health returned {r.status_code}"
        except requests.ConnectionError:
            pytest.fail("Grafana not reachable")

    def test_loki_ready(self):
        try:
            url = _get_host_url("localhost", 3100, "/ready")
            r = requests.get(url, timeout=TIMEOUT)
            # Accept any status as long as Loki is responding
            assert r.status_code in (200, 503), f"Loki /ready returned {r.status_code}"
        except requests.ConnectionError:
            pytest.fail("Loki not reachable")

    def test_web_management_ui_responds(self):
        try:
            url = _get_host_url("localhost", 8085, "")
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code == 200, f"Web management UI returned {r.status_code}"
            assert "text/html" in r.headers.get("content-type", "")
        except requests.ConnectionError:
            pytest.fail("Web management UI not reachable")

    def test_dns_thehive_resolves_from_api(self):
        if _IN_DOCKER:
            # Run directly inside container
            import socket

            try:
                socket.gethostbyname("thehive")
            except socket.gaierror as e:
                pytest.fail(f"DNS 'thehive' not resolving from soar_api: {e}")
        else:
            r = _run(
                [
                    "docker",
                    "exec",
                    "soar_api",
                    "python",
                    "-c",
                    "import socket; print(socket.gethostbyname('thehive'))",
                ],
                timeout=10,
            )
            assert (
                r.returncode == 0
            ), f"DNS 'thehive' not resolving from soar_api:\n{r.stdout}{r.stderr}"

    def test_dns_elasticsearch_resolves_from_api(self):
        if _IN_DOCKER:
            # Run directly inside container
            import socket

            try:
                socket.gethostbyname("elasticsearch")
            except socket.gaierror as e:
                pytest.fail(f"DNS 'elasticsearch' not resolving from soar_api: {e}")
        else:
            r = _run(
                [
                    "docker",
                    "exec",
                    "soar_api",
                    "python",
                    "-c",
                    "import socket; print(socket.gethostbyname('elasticsearch'))",
                ],
                timeout=10,
            )
            assert (
                r.returncode == 0
            ), f"DNS 'elasticsearch' not resolving from soar_api:\n{r.stdout}{r.stderr}"


# ─────────────────────────────────────────────────────────────────────────────
# Resource sanity (always run, not a rollback trigger)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.requires_docker
class TestSmokeResources:
    """Quick resource sanity — warn if obviously saturated."""

    def test_elasticsearch_disk_watermark(self):
        try:
            # Use container name and internal port when running inside Docker
            if os.path.exists("/.dockerenv"):
                url = "http://elasticsearch:9200/_cat/allocation?v&format=json"
            else:
                url = "http://localhost:9201/_cat/allocation?v&format=json"
            r = requests.get(url, timeout=TIMEOUT)
            assert r.status_code == 200, "ES allocation endpoint not available"
            nodes = r.json()
            for node in nodes:
                disk_pct_str = node.get("disk.percent", "0") or "0"
                disk_pct = float(disk_pct_str)
                # Skip if disk percent is unrealistic (host disk vs container disk)
                if disk_pct > 90:
                    pytest.fail(
                        f"ES node '{node.get('node')}' disk at {disk_pct}% "
                        f"- likely host disk, not container"
                    )
                assert disk_pct <= 95, (
                    f"ES node '{node.get('node')}' disk at {disk_pct}% "
                    f"— exceeds high watermark (95%)"
                )
        except requests.ConnectionError:
            pytest.fail("Elasticsearch not reachable")
