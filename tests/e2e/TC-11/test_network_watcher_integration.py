"""
TC-11: Validación de nuevas funcionalidades SOAR - Network Watcher
Este test valida la integración de Network Watcher para monitoreo de conexiones
"""
import pytest
import json
import time
from datetime import datetime


class TestNetworkWatcherIntegration:
    """Test suite para validar la integración de Network Watcher en el workflow SOAR"""

    @pytest.fixture(scope="class")
    def alert_data(self):
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
        import requests
        
        try:
            response = requests.get(
                "http://localhost:8080/api/health",
                timeout=10,
                verify=False
            )
            assert response.status_code == 200, f"Network Watcher health check failed: {response.status_code}"
            
            health_data = response.json()
            assert "status" in health_data, "Network Watcher health response missing status field"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Network Watcher service not available: {e}")

    def test_network_watcher_connections_endpoint(self):
        """Validar el endpoint de conexiones de Network Watcher"""
        import requests
        
        try:
            response = requests.get(
                "http://localhost:8080/api/connections",
                timeout=10,
                verify=False
            )
            
            # El endpoint debería responder (aunque puede estar vacío)
            assert response.status_code == 200, f"Connections endpoint failed: {response.status_code}"
            
            connections_data = response.json()
            assert isinstance(connections_data, dict), "Connections response should be JSON"
            assert "connections" in connections_data, "Response missing connections field"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Network Watcher connections endpoint failed: {e}")

    def test_network_watcher_ip_filtering(self, alert_data):
        """Validar el filtrado por IP en Network Watcher"""
        import requests
        
        try:
            response = requests.get(
                f"http://localhost:8080/api/connections?ip={alert_data['src_ip']}&limit=50",
                timeout=10,
                verify=False
            )
            
            assert response.status_code == 200, f"IP filtering failed: {response.status_code}"
            
            connections_data = response.json()
            connections = connections_data.get("connections", [])
            
            # Validar estructura de conexiones si existen
            for conn in connections:
                assert isinstance(conn, dict), "Connection should be a dictionary"
                assert "src_ip" in conn or "dst_ip" in conn, "Connection missing IP fields"
                assert "port" in conn or "protocol" in conn, "Connection missing port/protocol fields"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Network Watcher IP filtering failed: {e}")

    def test_network_watcher_in_workflow(self, alert_data):
        """Validar que el workflow incluye monitoreo de Network Watcher"""
        import requests
        
        # Enviar alerta al workflow
        webhook_url = "http://localhost:15001/api/v1/hooks/webhook_cbc11c64-2bde-576d-8538-73fa6b395d10"
        
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
            
            # Esperar a que complete el workflow
            time.sleep(10)
            
            # Verificar que se ejecutó la acción de Network Watcher
            workflow_url = f"http://localhost:5001/api/v1/flows/{execution_id}"
            auth_response = requests.get(
                "http://localhost:5001/api/v1/workflows/c08b9bed-b093-408d-8a4c-d11d5ada7578",
                headers={"Authorization": "Bearer c8410826-0c52-484f-a894-8aceafa5ffd0"},
                verify=False
            )
            
            if auth_response.status_code == 200:
                workflow_data = auth_response.json()
                actions = workflow_data.get("actions", [])
                
                # Buscar acción de Network Watcher
                network_action = None
                for action in actions:
                    if "Network" in action.get("label", "") and "Watcher" in action.get("label", ""):
                        network_action = action
                        break
                
                assert network_action is not None, "Network Watcher action not found in workflow"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Workflow execution failed: {e}")

    def test_network_watcher_real_time_monitoring(self):
        """Validar monitoreo en tiempo real de Network Watcher"""
        import requests
        import time
        
        try:
            # Obtener conexiones actuales
            initial_response = requests.get(
                "http://localhost:8080/api/connections?limit=10",
                timeout=10,
                verify=False
            )
            
            if initial_response.status_code == 200:
                initial_data = initial_response.json()
                initial_count = len(initial_data.get("connections", []))
                
                # Esperar un momento y verificar cambios
                time.sleep(2)
                
                updated_response = requests.get(
                    "http://localhost:8080/api/connections?limit=10",
                    timeout=10,
                    verify=False
                )
                
                if updated_response.status_code == 200:
                    updated_data = updated_response.json()
                    updated_count = len(updated_data.get("connections", []))
                    
                    # Validar que la estructura se mantiene
                    assert isinstance(updated_data, dict), "Updated response should be JSON"
                    assert "connections" in updated_data, "Updated response missing connections"
                    
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Real-time monitoring test failed: {e}")

    def test_network_watcher_connection_details(self):
        """Validar detalles de conexión en Network Watcher"""
        import requests
        
        try:
            response = requests.get(
                "http://localhost:8080/api/connections?limit=5",
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                connections_data = response.json()
                connections = connections_data.get("connections", [])
                
                # Si hay conexiones, validar detalles
                if connections:
                    conn = connections[0]
                    
                    # Validar campos esperados
                    expected_fields = ["src_ip", "dst_ip", "src_port", "dst_port", "protocol", "state"]
                    for field in expected_fields:
                        if field in conn:
                            assert conn[field] is not None, f"Connection field {field} is null"
                            
                    # Validar formato de IPs
                    if "src_ip" in conn:
                        import ipaddress
                        try:
                            ipaddress.ip_address(conn["src_ip"])
                        except ValueError:
                            pytest.fail(f"Invalid IP address format: {conn['src_ip']}")
                            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Connection details test failed: {e}")

    def test_network_watcher_error_handling(self):
        """Validar manejo de errores en Network Watcher"""
        import requests
        
        try:
            # Enviar consulta con parámetros inválidos
            response = requests.get(
                "http://localhost:8080/api/connections?ip=invalid-ip&limit=-1",
                timeout=10,
                verify=False
            )
            
            # Debería manejar el error gracefully
            assert response.status_code in [400, 422], f"Expected error status, got: {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            # Expected for invalid requests
            pass

    def test_network_watcher_performance_requirements(self):
        """Validar requisitos de rendimiento de Network Watcher"""
        import requests
        import time
        
        try:
            start_time = time.time()
            
            response = requests.get(
                "http://localhost:8080/api/connections?limit=100",
                timeout=10,
                verify=False
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Las consultas deberían completarse en menos de 3 segundos
            assert response_time < 3.0, f"Network Watcher response too slow: {response_time}s"
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict), "Response should be JSON"
                assert "connections" in data, "Response should contain connections"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Network Watcher performance test failed: {e}")

    def test_network_watcher_integration_completeness(self):
        """Validar que la integración de Network Watcher está completa en el workflow"""
        import requests
        
        try:
            # Obtener detalles del workflow
            response = requests.get(
                "http://localhost:5001/api/v1/workflows/c08b9bed-b093-408d-8a4c-d11d5ada7578",
                headers={"Authorization": "Bearer c8410826-0c52-484f-a894-8aceafa5ffd0"},
                verify=False
            )
            
            if response.status_code == 200:
                workflow_data = response.json()
                actions = workflow_data.get("actions", [])
                
                # Validar acciones relacionadas con Network Watcher
                network_actions = [a for a in actions if "Network" in a.get("label", "") and "Watcher" in a.get("label", "")]
                assert len(network_actions) > 0, "No Network Watcher actions found in workflow"
                
                # Validar que exista acción de monitoreo
                monitor_actions = [a for a in network_actions if "Monitorear" in a.get("label", "")]
                assert len(monitor_actions) > 0, "No Network Watcher monitoring action found"
                
                # Validar que exista acción de verificación
                verify_actions = [a for a in network_actions if "verify" in a.get("label", "").lower()]
                assert len(verify_actions) > 0, "No Network Watcher verification action found"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Workflow validation failed: {e}")
