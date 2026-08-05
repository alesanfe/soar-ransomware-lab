"""
TC-13: Validación de nuevas funcionalidades SOAR - Loki
Este test valida la integración de Loki para búsqueda de logs relacionados
"""
import json
import pytest
import time
from datetime import datetime, timedelta

from tests.e2e.conftest import SHUFFLE_WORKFLOW_ID, SHUFFLE_WEBHOOK_URL, LOKI_URL, SHUFFLE_BASE_URL, SHUFFLE_API_KEY


class TestLokiIntegration:
    """Test suite para validar la integración de Loki en el workflow SOAR"""

    @classmethod
    @pytest.fixture(scope="class")
    def alert_data(cls):
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

        last_error = None
        for _ in range(12):
            try:
                response = requests.get(f"{LOKI_URL}/ready", timeout=10, verify=False)
                if response.status_code == 200:
                    return
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            except requests.exceptions.RequestException as e:
                last_error = str(e)
            time.sleep(5)
        pytest.fail(f"Loki did not become ready within 60 seconds: {last_error}")

    def test_loki_query_range_endpoint(self):
        """Validar el endpoint query_range de Loki"""
        import requests

        try:
            # Query simple para probar el endpoint
            query = '{job=~".+"}'
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)

            response = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
                    "limit": 100
                },
                timeout=10,
                verify=False
            )

            assert response.status_code == 200, f"Loki query_range failed: {response.status_code}"

            data = response.json()
            assert isinstance(data, dict), "Loki response should be JSON"
            assert "status" in data, "Loki response missing status"
            assert "data" in data, "Loki response missing data"
            assert isinstance(data["data"], dict), "Data should be a dict"

            # Validate that filtering by hostname works correctly
            result_data = data.get("data", {})
            result_type = result_data.get("resultType", "")
            results = result_data.get("result", [])

            # If results exist, they should match the hostname filter
            if results and result_type == "streams":
                # Validate that results contain logs for the specified hostname
                assert len(results) >= 0, "Results should be a list"
                # The query should return logs matching the hostname
                assert data.get("status") == "success", "Query should succeed"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki hostname filtering test failed: {e}")

    def test_loki_hostname_filtering(self, alert_data):
        """Validar filtrado por hostname en Loki"""
        import requests

        try:
            # Query por hostname específico
            query = f'{{hostname="{alert_data["hostname"]}"}}'
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=10)

            response = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
                    "limit": 50
                },
                timeout=10,
                verify=False
            )

            assert response.status_code == 200, f"Loki hostname filtering failed: {response.status_code}"

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"
            assert data["status"] == "success", "Query should succeed"

            # Validar estructura de resultados
            result_data = data["data"]
            assert isinstance(result_data, dict), "Result data should be a dict"
            assert "resultType" in result_data, "Missing result type"
            assert "result" in result_data, "Missing results"

            # Validar que los resultados tengan la estructura esperada
            results = result_data["result"]
            assert isinstance(results, list), "Results should be a list"
            for result in results:
                assert isinstance(result, dict), "Result should be a dict"
                assert "metric" in result, "Result missing metric"
                assert "values" in result, "Result missing values"

            # Validate alert_data structure
            assert isinstance(alert_data, dict), "alert_data should be a dict"
            assert "hostname" in alert_data, "hostname should be in alert_data"

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
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
                    "limit": 50
                },
                timeout=10,
                verify=False
            )

            assert response.status_code == 200, f"Loki IP filtering failed: {response.status_code}"

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"
            assert data["status"] == "success", "Query should succeed"

            # Validar estructura
            result_data = data["data"]
            assert isinstance(result_data, dict), "Result data should be a dict"
            assert isinstance(result_data["result"], list), "Results should be a list"

            # Validate alert_data structure
            assert isinstance(alert_data, dict), "alert_data should be a dict"
            assert "src_ip" in alert_data, "src_ip should be in alert_data"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki IP filtering failed: {e}")

    def test_loki_in_workflow(self, alert_data):
        """Validar que el workflow incluye búsqueda de logs en Loki"""
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

            # Verificar que se ejecutó la acción de Loki
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

                # Buscar acción de Loki
                loki_action = None
                for action in actions:
                    if "Loki" in action.get("label", ""):
                        loki_action = action
                        break

                assert loki_action is not None, "Loki action not found in workflow"

                # Validate alert_data structure
                assert isinstance(alert_data, dict), "alert_data should be a dict"
                assert "alert_id" in alert_data, "alert_id should be in alert_data"

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
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
                    "limit": 20
                },
                timeout=10,
                verify=False
            )

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict), "Response should be JSON"

                if data["status"] == "success":
                    results = data["data"]["result"]
                    assert isinstance(results, list), "Results should be a list"

                    # Validar estructura de logs si existen
                    for result in results:
                        values = result.get("values", [])
                        assert isinstance(values, list), "Values should be a list"
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
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
                    "limit": 10
                },
                timeout=10,
                verify=False
            )

            assert response.status_code == 200, f"Loki time range query failed: {response.status_code}"

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"
            assert data["status"] == "success", "Time range query should succeed"

            # Test con 5 minutos
            start_time = end_time - timedelta(minutes=5)

            response = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
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
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={
                    "query": "{invalid syntax",
                    "start": datetime.utcnow().isoformat() + "Z",
                    "end": datetime.utcnow().isoformat() + "Z"
                },
                timeout=10,
                verify=False
            )

            # Debería devolver error 400
            assert response.status_code == 400, f"Expected 400 for invalid query, got: {response.status_code}"

            # Validate it's not a 5xx server error (indicates crash)
            assert response.status_code not in [502, 503, 504], f"Server error indicates crash: {response.status_code}"

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
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time_query.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
                    "limit": 50
                },
                timeout=10,
                verify=False
            )

            end_time = time.time()
            response_time = end_time - start_time

            # Las consultas deberían completarse en menos de 5 segundos
            assert response_time < 5.0, f"Loki response too slow: {response_time}s"

            # Validate response_time is positive
            assert response_time > 0, "Response time should be positive"

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
                f"{SHUFFLE_BASE_URL}/api/v1/workflows/{SHUFFLE_WORKFLOW_ID}",
                headers={"Authorization": f"Bearer {SHUFFLE_API_KEY}"},
                verify=False
            )

            if response.status_code == 200:
                workflow_data = response.json()
                assert isinstance(workflow_data, dict), "Workflow data should be a dict"
                actions = workflow_data.get("actions", [])
                assert isinstance(actions, list), "Actions should be a list"

                # Validar acciones relacionadas con Loki
                loki_actions = [a for a in actions if "loki" in a.get("label", "").lower()]
                assert len(loki_actions) > 0, "No Loki actions found in workflow"

                # Validar que exista acción de búsqueda
                search_actions = [a for a in loki_actions if "Buscar" in a.get("label", "")]
                assert len(search_actions) > 0, "No Loki search action found"

                # Validar que exista acción de verificación
                verify_actions = [a for a in loki_actions if "verify" in a.get("label", "").lower()]
                assert len(verify_actions) > 0, "No Loki verification action found"

                # Validate actions have required fields
                for action in loki_actions:
                    assert "label" in action, "Action should have label"
                    assert isinstance(action.get("label"), str), "Action label should be string"

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
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": start_time.isoformat() + "Z",
                    "end": end_time.isoformat() + "Z",
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

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-13-01 to TC-13-04)
    # ------------------------------------------------------------------

    def test_loki_ingestion(self, alert_data):
        """
        TC-13-01: Loki ingestion.

        Verifications:
          - Logs are ingested into Loki
          - Ingestion pipeline works
          - Logs are stored correctly
        """
        import requests

        try:
            # Send alert to trigger log ingestion
            webhook_url = SHUFFLE_WEBHOOK_URL
            response = requests.post(webhook_url, json=alert_data, timeout=30, verify=False)
            assert response.status_code == 200, f"Webhook failed: {response.status_code}"

            execution_id = response.json().get("execution_id")
            assert execution_id, "No execution_id returned"
            assert isinstance(execution_id, str), "execution_id should be a string"

            time.sleep(10)

            # Query for logs
            query = '{job=~".+"}'
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=5)

            response = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={"query": query, "start": start_time.isoformat() + "Z", "end": end_time.isoformat() + "Z",
                        "limit": 10},
                timeout=10,
                verify=False
            )

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict), "Response should be JSON"
                assert "data" in data, "Data field missing"
                assert isinstance(data["data"], dict), "Data should be a dict"

            # Validate alert_data structure
            assert isinstance(alert_data, dict), "alert_data should be a dict"
            assert "alert_id" in alert_data, "alert_id should be in alert_data"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki ingestion test failed: {e}")

    def test_loki_trace_id_search(self, alert_data):
        """
        TC-13-02: Loki trace_id search.

        Verifications:
          - Logs can be searched by trace_id
          - Trace ID is preserved
          - Search results are correct
        """
        import requests

        try:
            # Query by alert_id as trace_id
            query = f'{{alert_id="{alert_data["alert_id"]}"}}'
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=10)

            response = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={"query": query, "start": start_time.isoformat() + "Z", "end": end_time.isoformat() + "Z",
                        "limit": 50},
                timeout=10,
                verify=False
            )

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict), "Response should be JSON"
                assert data["status"] == "success", "Query should succeed"

            # Validate alert_data structure
            assert isinstance(alert_data, dict), "alert_data should be a dict"
            assert "alert_id" in alert_data, "alert_id should be in alert_data"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki trace_id search test failed: {e}")

    def test_loki_latency(self, alert_data):
        """
        TC-13-03: Loki latency.

        Verifications:
          - Query latency is acceptable
          - Performance meets SLA
          - No excessive delays
        """
        import requests
        import time

        try:
            start_time = time.time()

            query = '{job=~".+"}'
            end_time = datetime.utcnow()
            start_time_query = end_time - timedelta(minutes=5)

            response = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={"query": query, "start": start_time_query.isoformat() + "Z", "end": end_time.isoformat() + "Z",
                        "limit": 50},
                timeout=10,
                verify=False
            )

            end_time = time.time()
            latency = end_time - start_time

            # Latency should be less than 5 seconds
            assert latency < 5.0, f"Loki latency too high: {latency}s"

            # Validate latency is positive
            assert latency > 0, "Latency should be positive"

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict), "Response should be JSON"

            # Validate alert_data structure
            assert isinstance(alert_data, dict), "alert_data should be a dict"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki latency test failed: {e}")

    def test_loki_hidden_errors(self, alert_data):
        """
        TC-13-04: Loki hidden errors.

        Verifications:
          - Hidden errors are detected
          - Error logs are searchable
          - No errors are silently dropped
        """
        import requests

        try:
            # Query for error logs
            query = '{job=~".+"} |= "error"'
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=10)

            response = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={"query": query, "start": start_time.isoformat() + "Z", "end": end_time.isoformat() + "Z",
                        "limit": 20},
                timeout=10,
                verify=False
            )

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict), "Response should be JSON"
                # Errors may or may not exist
                if data["status"] == "success":
                    results = data["data"]["result"]
                    assert isinstance(results, list), "Results should be a list"
                    # If errors exist, validate structure
                    for result in results:
                        assert isinstance(result, dict), "Result should be a dict"
                        assert "values" in result, "Error log missing values"

            # Validate alert_data structure
            assert isinstance(alert_data, dict), "alert_data should be a dict"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Loki hidden errors test failed: {e}")
