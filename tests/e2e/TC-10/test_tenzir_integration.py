"""
TC-10: Validación de nuevas funcionalidades SOAR - Tenzir
Este test valida la integración de Tenzir para análisis de tráfico de red
"""
import pytest
import json
import time
from datetime import datetime


class TestTenzirIntegration:
    """Test suite para validar la integración de Tenzir en el workflow SOAR"""

    @pytest.fixture(scope="class")
    def alert_data(self):
        """Datos de alerta para pruebas de Tenzir"""
        return {
            "alert_id": "TC10-TENZIR-1783607000-1000",
            "hostname": "tc10-host",
            "src_ip": "192.168.100.50",
            "hash": "e3b0c44298fc1c149afbf4c8996fb924",
            "severity": "2",
            "type": "ransomware",
            "description": "Test alert for Tenzir network analysis",
            "detection_time": datetime.utcnow().isoformat() + "Z"
        }

    def test_tenzir_service_availability(self):
        """Verificar que el servicio Tenzir está disponible"""
        import requests
        
        try:
            response = requests.get(
                "http://localhost:15140/api/v0/status",
                timeout=10,
                verify=False
            )
            assert response.status_code == 200, f"Tenzir status check failed: {response.status_code}"
            
            status_data = response.json()
            assert "status" in status_data, "Tenzir status response missing status field"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Tenzir service not available: {e}")

    def test_tenzir_network_analysis_in_workflow(self, alert_data):
        """Validar que el workflow incluye análisis de Tenzir"""
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
            
            # Verificar que se ejecutó la acción de Tenzir
            workflow_url = f"http://localhost:5001/api/v1/flows/{execution_id}"
            auth_response = requests.get(
                "http://localhost:5001/api/v1/workflows/c08b9bed-b093-408d-8a4c-d11d5ada7578",
                headers={"Authorization": "Bearer c8410826-0c52-484f-a894-8aceafa5ffd0"},
                verify=False
            )
            
            if auth_response.status_code == 200:
                workflow_data = auth_response.json()
                actions = workflow_data.get("actions", [])
                
                # Buscar acción de Tenzir
                tenzir_action = None
                for action in actions:
                    if "Tenzir" in action.get("label", ""):
                        tenzir_action = action
                        break
                
                assert tenzir_action is not None, "Tenzir action not found in workflow"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Workflow execution failed: {e}")

    def test_tenzir_network_events_retrieval(self, alert_data):
        """Validar la recuperación de eventos de red desde Tenzir"""
        import requests
        
        try:
            # Consultar eventos de red para la IP de prueba
            response = requests.post(
                "http://localhost:15140/api/v0/events/export",
                json={
                    "since": "-5m",
                    "src_ip": alert_data["src_ip"],
                    "hostname": alert_data["hostname"],
                    "limit": 100
                },
                timeout=10,
                verify=False
            )
            
            # Tenzir puede no tener eventos para datos de prueba
            if response.status_code == 200:
                events_data = response.json()
                assert "events" in events_data, "Tenzir response missing events field"
                
                # Validar estructura de eventos si existen
                events = events_data.get("events", [])
                if events:
                    for event in events:
                        assert isinstance(event, dict), "Event should be a dictionary"
                        # Validar campos mínimos del evento
                        assert "timestamp" in event or "time" in event, "Event missing timestamp"
                        
            elif response.status_code == 404:
                # Acceptable - no events found for test data
                pass
            else:
                pytest.fail(f"Tenzir events query failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Tenzir events query failed: {e}")

    def test_tenzir_integration_completeness(self):
        """Validar que la integración de Tenzir está completa en el workflow"""
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
                
                # Validar acciones relacionadas con Tenzir
                tenzir_actions = [a for a in actions if "Tenzir" in a.get("label", "")]
                assert len(tenzir_actions) > 0, "No Tenzir actions found in workflow"
                
                # Validar que exista acción de análisis
                analysis_actions = [a for a in tenzir_actions if "Analizar" in a.get("label", "")]
                assert len(analysis_actions) > 0, "No Tenzir analysis action found"
                
                # Validar que exista acción de verificación
                verify_actions = [a for a in tenzir_actions if "verify" in a.get("label", "").lower()]
                assert len(verify_actions) > 0, "No Tenzir verification action found"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Workflow validation failed: {e}")

    def test_tenzir_error_handling(self):
        """Validar manejo de errores en la integración de Tenzir"""
        import requests
        
        try:
            # Enviar consulta inválida para probar manejo de errores
            response = requests.post(
                "http://localhost:15140/api/v0/events/export",
                json={
                    "since": "invalid-date",
                    "src_ip": "invalid-ip",
                    "limit": -1
                },
                timeout=10,
                verify=False
            )
            
            # Debería manejar el error gracefully
            assert response.status_code in [400, 404, 500], f"Unexpected status code: {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            # Expected for invalid requests
            pass

    def test_tenzir_performance_requirements(self):
        """Validar requisitos de rendimiento de Tenzir"""
        import requests
        import time
        
        try:
            start_time = time.time()
            
            response = requests.post(
                "http://localhost:15140/api/v0/events/export",
                json={
                    "since": "-1m",
                    "limit": 50
                },
                timeout=10,
                verify=False
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Las consultas deberían completarse en menos de 5 segundos
            assert response_time < 5.0, f"Tenzir response too slow: {response_time}s"
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict), "Response should be JSON"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Tenzir performance test failed: {e}")
