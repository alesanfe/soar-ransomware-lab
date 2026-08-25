"""
TC-11: Validación de nuevas funcionalidades SOAR - Network Watcher
Este test valida la integración de Network Watcher para monitoreo de conexiones
"""

import time
from datetime import UTC, datetime

from tests.e2e.base import E2EBaseTest


class TestNetworkWatcherIntegration(E2EBaseTest):
    """Test suite para validar la integración de Network Watcher en el workflow
    SOAR."""

    tc_id = "TC-11"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self.alert_data = {
            "alert_id": "TC11-NETWORK-1783607000-2000",
            "hostname": "tc11-host",
            "src_ip": "192.168.100.60",
            "hash": "a1b2c3d4e5f6789012345678901234567890abcd",
            "severity": "2",
            "type": "ransomware",
            "description": "Test alert for Network Watcher monitoring",
            "detection_time": datetime.now(UTC).isoformat() + "Z",
        }

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] TC-11 {msg}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _nw_url(self) -> str:
        return self.get_service_url("network_watcher")

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_network_watcher_service_availability(self):
        """Verificar que el servicio Network Watcher está disponible (HTTP 200
        en /health)."""
        import requests

        response = requests.get(f"{self._nw_url()}/health", timeout=10, verify=False)
        assert (
            response.status_code == 200
        ), f"Network Watcher health check failed: HTTP {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), "Health response should be JSON"
        assert (
            data.get("status") == "ok"
        ), f"Network Watcher health status not 'ok': {data.get('status')}"

    def test_network_watcher_connections_endpoint(self):
        """Validar el endpoint de conexiones de Network Watcher."""
        import requests

        response = requests.get(f"{self._nw_url()}/api/connections", timeout=10, verify=False)
        assert (
            response.status_code == 200
        ), f"Connections endpoint failed: HTTP {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON"
        assert (
            data.get("network") == "soar_net"
        ), f"Expected network 'soar_net', got '{data.get('network')}'"
        assert isinstance(data.get("connections"), list), "Connections should be a list"
        assert data.get("total", 0) >= len(
            data.get("connections", [])
        ), "Total count should be >= connections list length"

    def test_network_watcher_connection_monitoring(self):
        """Validar que el workflow incluye monitoreo de Network Watcher y
        captura conexiones."""
        import requests

        self.alert_data["alert_id"] = f"TC11-MON-{int(time.time())}"
        exec_id, execution = self.submit_alert_and_wait(self.alert_data)
        self.execution_id = exec_id
        self.execution = execution

        # Assert workflow FINISHED — validate_workflow_execution checks status, nodes, services
        self.validate_workflow_execution(execution, alert_id=self.alert_data["alert_id"])

        # Assert Network Watcher API returns connection data
        response = requests.get(
            f"{self._nw_url()}/api/connections?limit=1000", timeout=10, verify=False
        )
        assert (
            response.status_code == 200
        ), f"Network Watcher connections query failed: HTTP {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON"
        assert (
            data.get("network") == "soar_net"
        ), f"Expected network 'soar_net', got '{data.get('network')}'"
        connections = data.get("connections", [])
        assert isinstance(connections, list), "Connections should be a list"
        # Assert connections are non-empty — the workflow should produce network activity
        assert (
            len(connections) > 0
        ), "Network Watcher returned no connections after workflow execution"

    def test_network_watcher_real_time_monitoring(self):
        """Validar monitoreo en tiempo real de Network Watcher."""
        import requests

        initial = requests.get(
            f"{self._nw_url()}/api/connections?limit=1000", timeout=10, verify=False
        )
        assert (
            initial.status_code == 200
        ), f"Initial connections query failed: HTTP {initial.status_code}"
        initial_data = initial.json()
        assert isinstance(initial_data, dict), "Response should be JSON"
        assert (
            initial_data.get("network") == "soar_net"
        ), "Initial query network should be 'soar_net'"

        time.sleep(0.2)
        current = requests.get(
            f"{self._nw_url()}/api/connections?limit=1000", timeout=10, verify=False
        )
        assert (
            current.status_code == 200
        ), f"Current connections query failed: HTTP {current.status_code}"
        current_data = current.json()
        assert isinstance(current_data, dict), "Response should be JSON"
        assert (
            current_data.get("network") == "soar_net"
        ), "Current query network should be 'soar_net'"
        # Assert the monitoring endpoint is consistently responsive
        assert isinstance(
            current_data.get("connections"), list
        ), "Current connections should be a list"

    def test_network_watcher_error_handling(self):
        """Validar manejo de errores en Network Watcher."""
        import requests

        # Enviar consulta con parámetros inválidos
        response = requests.get(
            f"{self._nw_url()}/api/connections?ip=invalid-ip&limit=-1",
            timeout=10,
            verify=False,
        )
        # Debería manejar el error gracefully
        assert response.status_code in [
            400,
            422,
        ], f"Expected error status 400/422, got: {response.status_code}"
        # Validate it's not a 5xx server error (indicates crash)
        assert response.status_code not in [
            502,
            503,
            504,
        ], f"Server error indicates crash: {response.status_code}"

    def test_network_watcher_performance_requirements(self):
        """Validar requisitos de rendimiento de Network Watcher."""
        import requests

        started = time.time()
        response = requests.get(
            f"{self._nw_url()}/api/connections?limit=1000", timeout=10, verify=False
        )
        elapsed = time.time() - started
        assert response.status_code == 200, f"Connections query failed: HTTP {response.status_code}"
        assert elapsed < 5.0, f"Network Watcher connections query exceeded 5 seconds: {elapsed}s"

    def test_network_watcher_integration_completeness(self):
        """Validar que la integración de Network Watcher está completa en el
        workflow."""
        import requests

        shuffle_base = self.get_service_url("shuffle")
        api_key = self.env.get("SHUFFLE_DEFAULT_APIKEY", "")
        response = requests.get(
            f"{shuffle_base}/api/v1/workflows/{self.workflow_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            verify=False,
        )
        assert response.status_code in (
            200,
            401,
        ), f"Workflow fetch failed: HTTP {response.status_code}"
        assert response.status_code == 200, "Shuffle API key must be valid (got 401)"
        workflow_data = response.json()
        assert isinstance(workflow_data, dict), "Workflow data should be a dict"
        actions = workflow_data.get("actions", [])
        assert isinstance(actions, list), "Actions should be a list"

        # Validar acciones relacionadas con Network Watcher
        # The workflow uses labels like "network_watch" (not "network watcher")
        network_actions = [
            a
            for a in actions
            if "network" in a.get("label", "").lower() and (
                "watch" in a.get("label", "").lower()
                or "watcher" in a.get("label", "").lower()
            )
        ]
        # Also accept "network_watch" as a network watcher action
        if len(network_actions) == 0:
            network_actions = [
                a for a in actions if a.get("label", "").lower().startswith("network")
            ]
        assert len(network_actions) > 0, "No Network Watcher actions found in workflow"

        # Validar que exista acción de monitoreo (label "network_watch" counts)
        monitor_actions = [
            a for a in network_actions
            if "monitorear" in a.get("label", "").lower()
            or "monitor" in a.get("label", "").lower()
            or "watch" in a.get("label", "").lower()
        ]
        assert len(monitor_actions) > 0, "No Network Watcher monitoring action found"

        # Validar que exista acción de verificación
        verify_actions = [a for a in network_actions if "verify" in a.get("label", "").lower()]
        # También buscar verify_network específicamente
        if len(verify_actions) == 0:
            verify_actions = [a for a in actions if a.get("label", "").lower() == "verify_network"]
        assert len(verify_actions) > 0, "No Network Watcher verification action found"

        # Validate actions have required fields
        for action in network_actions:
            assert "label" in action, "Action should have label"
            assert isinstance(action.get("label"), str), "Action label should be string"

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-11-01 to TC-11-04)
    # ------------------------------------------------------------------

    def test_network_connection(self):
        """TC-11-01: Network connection.

        Verifications:
          - Network connections are monitored on soar_net
          - Connection data is captured with required fields
          - Network activity is logged with container IDs
        """
        import requests

        # Get network connections
        response = requests.get(f"{self._nw_url()}/api/connections", timeout=10, verify=False)
        assert (
            response.status_code == 200
        ), f"Connections endpoint failed: HTTP {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON"
        assert "connections" in data, "Connections field missing"
        assert isinstance(data["connections"], list), "Connections should be a list"
        assert (
            data.get("network") == "soar_net"
        ), f"Expected network 'soar_net', got '{data.get('network')}'"
        # Assert connections are non-empty — the soar_net should have active containers
        connections = data["connections"]
        assert len(connections) > 0, "No connections monitored on soar_net"
        for conn in connections:
            assert isinstance(conn, dict), "Connection should be a dict"
            assert "id" in conn, "Connection missing 'id' field"

    def test_network_source(self):
        """TC-11-02: Network source.

        Verifications:
          - Source IP filtering works correctly
          - Filtered connections match the requested IP
          - Total count is consistent with filtered results
        """
        import requests

        # Filter by source IP
        response = requests.get(
            f"{self._nw_url()}/api/connections",
            params={"ip": self.alert_data["src_ip"], "limit": 50},
            timeout=10,
            verify=False,
        )
        assert response.status_code == 200, f"Source filtering failed: HTTP {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON"
        connections = data.get("connections", [])
        assert isinstance(connections, list), "Connections should be a list"
        # Assert IP filtering logic: all returned connections match the filtered IP
        for conn in connections:
            assert isinstance(conn, dict), "Connection should be a dict"
            assert conn.get("ip") == self.alert_data["src_ip"], (
                f"Connection IP mismatch: expected {self.alert_data['src_ip']}, "
                f"got {conn.get('ip')}"
            )
        # Assert total count is consistent
        assert data.get("total", 0) >= len(
            connections
        ), "Total count should be >= filtered connections count"

    def test_network_destination(self):
        """TC-11-03: Network destination.

        Verifications:
          - Destination connection details are retrievable
          - Connection detail endpoint returns correct data
          - Connection IDs are consistent between listing and detail
        """
        import requests

        listing = requests.get(
            f"{self._nw_url()}/api/connections?limit=1", timeout=10, verify=False
        )
        assert listing.status_code == 200, f"Connections listing failed: HTTP {listing.status_code}"
        listing_data = listing.json()
        assert isinstance(listing_data, dict), "Response should be JSON"
        connections = listing_data.get("connections", [])
        assert isinstance(connections, list), "Connections should be a list"
        assert connections, "No connections available for destination detail test"

        conn_id = connections[0].get("id")
        assert conn_id, "Connection missing 'id' field"
        response = requests.get(
            f"{self._nw_url()}/api/connections/{conn_id}", timeout=10, verify=False
        )
        assert response.status_code == 200, f"Connection detail failed: HTTP {response.status_code}"
        conn_data = response.json()
        assert isinstance(conn_data, dict), "Connection data should be JSON"
        assert "id" in conn_data, "Connection detail missing 'id' field"
        assert (
            conn_data["id"] == conn_id
        ), f"Connection detail id mismatch: expected {conn_id}, got {conn_data.get('id')}"

    def test_network_correlation(self):
        """TC-11-04: Network correlation.

        Verifications:
          - All connections on soar_net are retrievable for correlation
          - Connection records have required correlation fields
          - Network patterns can be identified from connection data
        """
        import requests

        # Get all connections for correlation
        response = requests.get(
            f"{self._nw_url()}/api/connections?limit=1000", timeout=10, verify=False
        )
        assert response.status_code == 200, f"Connections query failed: HTTP {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON"
        assert (
            data.get("network") == "soar_net"
        ), f"Expected network 'soar_net', got '{data.get('network')}'"
        connections = data.get("connections", [])
        assert isinstance(connections, list), "Connections should be a list"
        assert len(connections) > 0, "No connections available for correlation analysis"

        # Verify correlation data exists — each connection has required fields
        for conn in connections[:5]:
            assert isinstance(conn, dict), "Connection should be a dict"
            assert "id" in conn, "Connection missing 'id' for correlation"
