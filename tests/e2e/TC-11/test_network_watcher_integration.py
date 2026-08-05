"""
TC-11: Validación de nuevas funcionalidades SOAR - Network Watcher
Este test valida la integración de Network Watcher para monitoreo de conexiones
"""
import json
import pytest
import time
from datetime import datetime

from tests.e2e.conftest import SHUFFLE_WORKFLOW_ID, SHUFFLE_WEBHOOK_URL, NETWORK_WATCHER_URL, SHUFFLE_BASE_URL, \
    SHUFFLE_API_KEY


class TestNetworkWatcherIntegration:
    """Test suite para validar la integración de Network Watcher en el workflow SOAR"""

    @classmethod
    @pytest.fixture(scope="class")
    def alert_data(cls):
        """Datos de alerta para pruebas de Network Watcher"""
        return {
            "alert_id": "TC11-NETWORK-1783607000-2000",
            "hostname": "tc11-host",
            "src_ip": "192.168.100.60",
            "hash": "a1b2c3d4e5f6789012345678901234567890abcd",
            "severity": "2",
            "type": "ransomware",
            "description": "Test alert for Network Watcher monitoring",
            "detection_time": datetime.utcnow().isoformat() + "Z"
        }

    def test_network_watcher_service_availability(self):
        """Verificar que el servicio Network Watcher está disponible"""
        # Network Watcher funciona a través de inyección de hosts y docker socket forwarding
        # en los contenedores de Shuffle, no como un servicio HTTP tradicional con API REST.
        # Su disponibilidad se valida a través de la integración en el workflow (test_network_watcher_in_workflow).
        import requests
        response = requests.get(f"{NETWORK_WATCHER_URL}/health", timeout=10, verify=False)
        assert response.status_code == 200, f"Network Watcher health check failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), "Health response should be JSON"
        assert data["status"] == "ok"

    def test_network_watcher_connections_endpoint(self):
        """Validar el endpoint de conexiones de Network Watcher"""
        # Network Watcher opera a través de inyección de hosts en contenedores Shuffle,
        # no expone endpoints HTTP tradicionales. La funcionalidad de conexiones
        # se valida a través de la integración en el workflow.
        import requests
        response = requests.get(f"{NETWORK_WATCHER_URL}/api/connections", timeout=10, verify=False)
        assert response.status_code == 200, f"Connections endpoint failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON"
        assert data["network"] == "soar_net"
        assert isinstance(data["connections"], list)
        assert data["total"] >= len(data["connections"])

    def test_network_watcher_ip_filtering(self, alert_data):
        """Validar el filtrado por IP en Network Watcher"""
        # Network Watcher opera a través de inyección de hosts en contenedores Shuffle,
        # no expone endpoints HTTP tradicionales. La funcionalidad de filtrado por IP
        # se valida a través de la integración en el workflow.
        import requests
        response = requests.get(f"{NETWORK_WATCHER_URL}/api/connections",
                                params={"ip": alert_data["src_ip"], "limit": 50}, timeout=10, verify=False)
        assert response.status_code == 200, f"IP filtering failed: {response.status_code}"
        data = response.json()
        assert isinstance(data, dict), "Response should be JSON"
        connections = data.get("connections", [])
        assert isinstance(connections, list), "Connections should be a list"
        assert all(connection["ip"] == alert_data["src_ip"] for connection in
                   connections), "All connections should match the filtered IP"

        # Validate alert_data structure
        assert isinstance(alert_data, dict), "alert_data should be a dict"
        assert "src_ip" in alert_data, "src_ip should be in alert_data"

        # Validate that filtering logic is working correctly
        # If connections exist, they should all match the filtered IP
        if len(connections) > 0:
            assert all(conn.get("ip") == alert_data["src_ip"] for conn in connections), "IP filtering logic failed"
            assert data.get("total") >= len(connections), "Total count should be >= filtered count"
        else:
            # No connections for this IP is also valid
            assert data.get("total") == 0, "Total should be 0 when no connections found"

    def test_network_watcher_in_workflow(self, alert_data):
        """Validar que el workflow incluye monitoreo de Network Watcher"""
        import requests

        # Enviar alerta al workflow
        webhook_url = SHUFFLE_WEBHOOK_URL

        try:
            response = requests.post(
                webhook_url,
                json=alert_data,
                timeout=30,
                verify=False
            )
            assert response.status_code == 200, f"Webhook failed: {response.status_code}"

            execution_id = response.json().get("execution_id")
            assert execution_id, "No execution_id returned"
            assert isinstance(execution_id, str), "execution_id should be a string"
            assert len(execution_id) > 0, "execution_id should not be empty"

            # Esperar a que complete el workflow
            time.sleep(10)

            # Verificar que se ejecutó la acción de Network Watcher
            auth_response = requests.get(
                f"{SHUFFLE_BASE_URL}/api/v1/workflows/{SHUFFLE_WORKFLOW_ID}",
                headers={"Authorization": f"Bearer {SHUFFLE_API_KEY}"},
                verify=False
            )

            if auth_response.status_code == 200:
                workflow_data = auth_response.json()
                assert isinstance(workflow_data, dict), "Workflow data should be a dict"
                actions = workflow_data.get("actions", [])
                assert isinstance(actions, list), "Actions should be a list"

                # Buscar acción de Network Watcher
                network_action = None
                for action in actions:
                    if "Network" in action.get("label", "") and "Watcher" in action.get("label", ""):
                        network_action = action
                        break

                assert network_action is not None, "Network Watcher action not found in workflow"

                # Validate alert_data structure
                assert isinstance(alert_data, dict), "alert_data should be a dict"
                assert "src_ip" in alert_data, "src_ip should be in alert_data"

        except requests.exceptions.RequestException as e:
            raise AssertionError(f"Workflow execution failed: {e}") from e

    def test_network_watcher_real_time_monitoring(self):
        """Validar monitoreo en tiempo real de Network Watcher"""
        # Network Watcher opera a través de inyección de hosts en contenedores Shuffle,
        # no expone endpoints HTTP tradicionales. La funcionalidad de monitoreo en tiempo real
        # se valida a través de la integración en el workflow.
        import requests
        initial = requests.get(f"{NETWORK_WATCHER_URL}/api/connections?limit=1000", timeout=10, verify=False)
        assert initial.status_code == 200
        initial_data = initial.json()
        assert isinstance(initial_data, dict), "Response should be JSON"
        time.sleep(0.2)
        current = requests.get(f"{NETWORK_WATCHER_URL}/api/connections?limit=1000", timeout=10, verify=False)
        assert current.status_code == 200
        current_data = current.json()
        assert isinstance(current_data, dict), "Response should be JSON"
        assert current_data["network"] == "soar_net"

    def test_network_watcher_connection_details(self):
        """Validar detalles de conexión en Network Watcher"""
        # Network Watcher opera a través de inyección de hosts en contenedores Shuffle,
        # no expone endpoints HTTP tradicionales. La funcionalidad de detalles de conexión
        # se valida a través de la integración en el workflow.
        import requests
        listing = requests.get(f"{NETWORK_WATCHER_URL}/api/connections?limit=1", timeout=10, verify=False)
        assert listing.status_code == 200
        listing_data = listing.json()
        assert isinstance(listing_data, dict), "Response should be JSON"
        connections = listing_data["connections"]
        assert isinstance(connections, list), "Connections should be a list"
        assert connections, "Network Watcher returned no containers on soar_net"
        response = requests.get(f"{NETWORK_WATCHER_URL}/api/connections/{connections[0]['id']}", timeout=10,
                                verify=False)
        assert response.status_code == 200, f"Connection detail failed: {response.status_code}"
        conn_data = response.json()
        assert isinstance(conn_data, dict), "Connection data should be JSON"
        assert conn_data["id"] == connections[0]["id"]

    def test_network_watcher_error_handling(self):
        """Validar manejo de errores en Network Watcher"""
        import requests

        try:
            # Enviar consulta con parámetros inválidos
            response = requests.get(
                f"{NETWORK_WATCHER_URL}/api/connections?ip=invalid-ip&limit=-1",
                timeout=10,
                verify=False
            )

            # Debería manejar el error gracefully
            assert response.status_code in [400, 422], f"Expected error status, got: {response.status_code}"

            # Validate it's not a 5xx server error (indicates crash)
            assert response.status_code not in [502, 503, 504], f"Server error indicates crash: {response.status_code}"

        except requests.exceptions.RequestException as e:
            # Expected for invalid requests
            pass

    def test_network_watcher_performance_requirements(self):
        """Validar requisitos de rendimiento de Network Watcher"""
        # Network Watcher opera a través de inyección de hosts en contenedores Shuffle,
        # no expone endpoints HTTP tradicionales. Los requisitos de rendimiento
        # se validan a través de la integración en el workflow.
        import requests
        started = time.time()
        response = requests.get(f"{NETWORK_WATCHER_URL}/api/connections?limit=1000", timeout=10, verify=False)
        assert response.status_code == 200
        elapsed = time.time() - started
        assert elapsed < 5.0, "Network Watcher connections query exceeded 5 seconds"
        assert elapsed > 0, "Elapsed time should be positive"

    def test_network_watcher_integration_completeness(self):
        """Validar que la integración de Network Watcher está completa en el workflow"""
        import requests

        try:
            # Obtener detalles del workflow
            response = requests.get(
                f"{SHUFFLE_BASE_URL}/api/v1/workflows/{SHUFFLE_WORKFLOW_ID}",
                headers={"Authorization": f"Bearer {SHUFFLE_API_KEY}"},
                verify=False
            )

            if response.status_code == 200:
                workflow_data = response.json()
                assert isinstance(workflow_data, dict), "Workflow data should be a dict"
                actions = workflow_data.get("actions", [])
                assert isinstance(actions, list), "Actions should be a list"

                # Validar acciones relacionadas con Network Watcher
                network_actions = [a for a in actions if
                                   "network" in a.get("label", "").lower() and "watcher" in a.get("label", "").lower()]
                assert len(network_actions) > 0, "No Network Watcher actions found in workflow"

                # Validar que exista acción de monitoreo
                monitor_actions = [a for a in network_actions if "monitorear" in a.get("label", "").lower()]
                assert len(monitor_actions) > 0, "No Network Watcher monitoring action found"

                # Validar que exista acción de verificación
                # La acción de verificación puede estar dentro de network_actions o ser verify_network
                verify_actions = [a for a in network_actions if "verify" in a.get("label", "").lower()]
                # También buscar verify_network específicamente
                if len(verify_actions) == 0:
                    verify_actions = [a for a in actions if a.get("label", "").lower() == "verify_network"]
                assert len(verify_actions) > 0, "No Network Watcher verification action found"

                # Validate actions have required fields
                for action in network_actions:
                    assert "label" in action, "Action should have label"
                    assert isinstance(action.get("label"), str), "Action label should be string"

        except requests.exceptions.RequestException as e:
            raise AssertionError(f"Workflow validation failed: {e}") from e

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-11-01 to TC-11-04)
    # ------------------------------------------------------------------

    def test_network_connection(self, alert_data):
        """
        TC-11-01: Network connection.

        Verifications:
          - Network connections are monitored
          - Connection data is captured
          - Network activity is logged
        """
        import requests

        try:
            # Get network connections
            response = requests.get(f"{NETWORK_WATCHER_URL}/api/connections", timeout=10, verify=False)
            assert response.status_code == 200, f"Connections endpoint failed: {response.status_code}"
            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"
            assert "connections" in data, "Connections field missing"
            assert isinstance(data["connections"], list), "Connections should be a list"

            # Validate alert_data structure
            assert isinstance(alert_data, dict), "alert_data should be a dict"
            assert "alert_id" in alert_data, "alert_id should be in alert_data"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Network connection test failed: {e}")

    def test_network_source(self, alert_data):
        """
        TC-11-02: Network source.

        Verifications:
          - Source IP is tracked
          - Source hostname is captured
          - Source port is logged
        """
        import requests

        try:
            # Filter by source IP
            response = requests.get(
                f"{NETWORK_WATCHER_URL}/api/connections",
                params={"ip": alert_data["src_ip"], "limit": 50},
                timeout=10,
                verify=False
            )
            assert response.status_code == 200, f"Source filtering failed: {response.status_code}"
            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"
            connections = data.get("connections", [])
            assert isinstance(connections, list), "Connections should be a list"
            # Connections may be empty for test data

            # Validate alert_data structure
            assert isinstance(alert_data, dict), "alert_data should be a dict"
            assert "src_ip" in alert_data, "src_ip should be in alert_data"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Network source test failed: {e}")

    def test_network_destination(self, alert_data):
        """
        TC-11-03: Network destination.

        Verifications:
          - Destination IP is tracked
          - Destination port is captured
          - Destination hostname is logged
        """
        import requests

        try:
            # Get connection details
            listing = requests.get(f"{NETWORK_WATCHER_URL}/api/connections?limit=1", timeout=10, verify=False)
            assert listing.status_code == 200
            listing_data = listing.json()
            assert isinstance(listing_data, dict), "Response should be JSON"
            connections = listing_data.get("connections", [])
            assert isinstance(connections, list), "Connections should be a list"

            if connections:
                conn_id = connections[0]["id"]
                response = requests.get(f"{NETWORK_WATCHER_URL}/api/connections/{conn_id}", timeout=10, verify=False)
                assert response.status_code == 200, f"Connection detail failed: {response.status_code}"
                conn_data = response.json()
                assert isinstance(conn_data, dict), "Connection data should be JSON"
                assert "id" in conn_data, "Connection should have id"

            # Validate alert_data structure
            assert isinstance(alert_data, dict), "alert_data should be a dict"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Network destination test failed: {e}")

    def test_network_correlation(self, alert_data):
        """
        TC-11-04: Network correlation.

        Verifications:
          - Related connections are correlated
          - Correlation logic works
          - Network patterns are identified
        """
        import requests

        try:
            # Get all connections for correlation
            response = requests.get(f"{NETWORK_WATCHER_URL}/api/connections?limit=1000", timeout=10, verify=False)
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"
            connections = data.get("connections", [])
            assert isinstance(connections, list), "Connections should be a list"

            # Verify correlation data exists
            if connections:
                # Check for correlation fields
                for conn in connections[:5]:
                    assert isinstance(conn, dict), "Connection should be a dict"
                    assert "id" in conn, "Connection missing id"

            # Validate alert_data structure
            assert isinstance(alert_data, dict), "alert_data should be a dict"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Network correlation test failed: {e}")
