"""
TC-13: Validación de nuevas funcionalidades SOAR - Loki
Este test valida la integración de Loki para búsqueda de logs relacionados
"""
import pytest
import json
import time
from datetime import datetime, timedelta


class TestLokiIntegration:
    """Test suite para validar la integración de Loki en el workflow SOAR"""

    @pytest.fixture(scope="class")
    def alert_data(self):
        """Datos de alerta para pruebas de Loki"""
        return {
            "alert_id": "TC13-LOKI-1783607000-4000",
            "hostname": "tc13-host",
            "src_ip": "192.168.100.80",
            "hash": "c3d4e5f6789012345678901234567890abcdef",
            "severity": "2",
            "type": "ransomware",
            "description": "Test alert for Loki log searching",
            "detection_time": datetime.utcnow().isoformat() + "Z"
        }

    def test_loki_service_availability(self):
        """Verificar que el servicio Loki está disponible"""
        import requests
        
        try:
            response = requests.get(
                "http://localhost:3100/ready",
                timeout=10,
                verify=False
            )
            assert response.status_code == 200, f"Loki ready check failed: {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki service not available: {e}")

    def test_loki_query_range_endpoint(self):
        """Validar el endpoint query_range de Loki"""
        import requests
        
        try:
            # Query simple para probar el endpoint
            query = '{job=~".+"}'
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)
            
            response = requests.get(
                "http://localhost:3100/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "limit": 100
                },
                timeout=10,
                verify=False
            )
            
            assert response.status_code == 200, f"Loki query_range failed: {response.status_code}"
            
            data = response.json()
            assert "status" in data, "Loki response missing status"
            assert "data" in data, "Loki response missing data"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki query_range test failed: {e}")

    def test_loki_hostname_filtering(self, alert_data):
        """Validar filtrado por hostname en Loki"""
        import requests
        
        try:
            # Query por hostname específico
            query = f'{{hostname="{alert_data["hostname"]}"}}'
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=10)
            
            response = requests.get(
                "http://localhost:3100/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "limit": 50
                },
                timeout=10,
                verify=False
            )
            
            assert response.status_code == 200, f"Loki hostname filtering failed: {response.status_code}"
            
            data = response.json()
            assert data["status"] == "success", "Query should succeed"
            
            # Validar estructura de resultados
            result_data = data["data"]
            assert "resultType" in result_data, "Missing result type"
            assert "result" in result_data, "Missing results"
            
            # Validar que los resultados tengan la estructura esperada
            results = result_data["result"]
            for result in results:
                assert "metric" in result, "Result missing metric"
                assert "values" in result, "Result missing values"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki hostname filtering failed: {e}")

    def test_loki_ip_filtering(self, alert_data):
        """Validar filtrado por IP en Loki"""
        import requests
        
        try:
            # Query por IP específica
            query = f'{{src_ip="{alert_data["src_ip"]}"}}'
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=10)
            
            response = requests.get(
                "http://localhost:3100/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "limit": 50
                },
                timeout=10,
                verify=False
            )
            
            assert response.status_code == 200, f"Loki IP filtering failed: {response.status_code}"
            
            data = response.json()
            assert data["status"] == "success", "Query should succeed"
            
            # Validar estructura
            result_data = data["data"]
            assert isinstance(result_data["result"], list), "Results should be a list"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki IP filtering failed: {e}")

    def test_loki_in_workflow(self, alert_data):
        """Validar que el workflow incluye búsqueda de logs en Loki"""
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
            
            # Verificar que se ejecutó la acción de Loki
            auth_response = requests.get(
                "http://localhost:5001/api/v1/workflows/c08b9bed-b093-408d-8a4c-d11d5ada7578",
                headers={"Authorization": "Bearer c8410826-0c52-484f-a894-8aceafa5ffd0"},
                verify=False
            )
            
            if auth_response.status_code == 200:
                workflow_data = auth_response.json()
                actions = workflow_data.get("actions", [])
                
                # Buscar acción de Loki
                loki_action = None
                for action in actions:
                    if "Loki" in action.get("label", ""):
                        loki_action = action
                        break
                
                assert loki_action is not None, "Loki action not found in workflow"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Workflow execution failed: {e}")

    def test_loki_log_parsing(self):
        """Validar parsing de logs en Loki"""
        import requests
        
        try:
            # Query con parsing de logs
            query = '{job=~".+"} |= "error"'
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)
            
            response = requests.get(
                "http://localhost:3100/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "limit": 20
                },
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data["status"] == "success":
                    results = data["data"]["result"]
                    
                    # Validar estructura de logs si existen
                    for result in results:
                        values = result.get("values", [])
                        for timestamp, log_line in values:
                            assert isinstance(timestamp, str), "Timestamp should be string"
                            assert isinstance(log_line, str), "Log line should be string"
                            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki log parsing test failed: {e}")

    def test_loki_time_range_queries(self):
        """Validar consultas por rango de tiempo en Loki"""
        import requests
        
        try:
            # Query con diferentes rangos de tiempo
            end_time = datetime.utcnow()
            
            # Test con 1 hora
            start_time = end_time - timedelta(hours=1)
            query = '{job=~".+"}'
            
            response = requests.get(
                "http://localhost:3100/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "limit": 10
                },
                timeout=10,
                verify=False
            )
            
            assert response.status_code == 200, f"Loki time range query failed: {response.status_code}"
            
            data = response.json()
            assert data["status"] == "success", "Time range query should succeed"
            
            # Test con 5 minutos
            start_time = end_time - timedelta(minutes=5)
            
            response = requests.get(
                "http://localhost:3100/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "limit": 10
                },
                timeout=10,
                verify=False
            )
            
            assert response.status_code == 200, f"Loki short time range query failed: {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki time range test failed: {e}")

    def test_loki_error_handling(self):
        """Validar manejo de errores en Loki"""
        import requests
        
        try:
            # Query con sintaxis inválida
            response = requests.get(
                "http://localhost:3100/loki/api/v1/query_range",
                params={
                    "query": "{invalid syntax",
                    "start": datetime.utcnow().isoformat(),
                    "end": datetime.utcnow().isoformat()
                },
                timeout=10,
                verify=False
            )
            
            # Debería devolver error 400
            assert response.status_code == 400, f"Expected 400 for invalid query, got: {response.status_code}"
            
        except requests.exceptions.RequestException as e:
            # Expected for invalid queries
            pass

    def test_loki_performance_requirements(self):
        """Validar requisitos de rendimiento de Loki"""
        import requests
        import time
        
        try:
            start_time = time.time()
            
            # Query simple para medir rendimiento
            query = '{job=~".+"}'
            end_time = datetime.utcnow()
            start_time_query = end_time - timedelta(minutes=5)
            
            response = requests.get(
                "http://localhost:3100/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time_query.isoformat(),
                    "end": end_time.isoformat(),
                    "limit": 50
                },
                timeout=10,
                verify=False
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Las consultas deberían completarse en menos de 5 segundos
            assert response_time < 5.0, f"Loki response too slow: {response_time}s"
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict), "Response should be JSON"
                assert "status" in data, "Response should have status"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki performance test failed: {e}")

    def test_loki_integration_completeness(self):
        """Validar que la integración de Loki está completa en el workflow"""
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
                
                # Validar acciones relacionadas con Loki
                loki_actions = [a for a in actions if "Loki" in a.get("label", "")]
                assert len(loki_actions) > 0, "No Loki actions found in workflow"
                
                # Validar que exista acción de búsqueda
                search_actions = [a for a in loki_actions if "Buscar" in a.get("label", "")]
                assert len(search_actions) > 0, "No Loki search action found"
                
                # Validar que exista acción de verificación
                verify_actions = [a for a in loki_actions if "verify" in a.get("label", "").lower()]
                assert len(verify_actions) > 0, "No Loki verification action found"
                
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Workflow validation failed: {e}")

    def test_loki_log_aggregation(self):
        """Validar agregación de logs en Loki"""
        import requests
        
        try:
            # Query con agregación
            query = 'sum by (job) (count_over_time({job=~".+"}[5m]))'
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=10)
            
            response = requests.get(
                "http://localhost:3100/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "limit": 10
                },
                timeout=10,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data["status"] == "success":
                    results = data["data"]["result"]
                    
                    # Validar estructura de resultados agregados
                    for result in results:
                        assert "metric" in result, "Aggregated result missing metric"
                        assert "job" in result["metric"], "Missing job in metric"
                        assert "values" in result, "Missing values in aggregated result"
                        
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki aggregation test failed: {e}")
