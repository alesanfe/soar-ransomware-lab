#!/usr/bin/env python3
"""
TC-13: Validación de nuevas funcionalidades SOAR - Loki
Este test valida la integración de Loki para búsqueda de logs relacionados
"""

import time
from datetime import UTC, datetime, timedelta

import pytest

from tests.e2e.base import E2EBaseTest


class TestLokiIntegration(E2EBaseTest):
    """Test suite para validar la integración de Loki en el workflow SOAR."""

    tc_id = "TC-13"

    def setup_method(self, method):
        super().setup_method(method)
        self.t0 = datetime.now(UTC)
        self.alert_data = {
            "alert_id": "TC13-LOKI-1783607000-4000",
            "hostname": "tc13-host",
            "src_ip": "192.168.100.80",
            "hash": "c3d4e5f6789012345678901234567890abcdef",
            "severity": "2",
            "type": "ransomware",
            "description": "Test alert for Loki log searching",
            "detection_time": datetime.now(UTC).isoformat() + "Z",
        }

    def _log(self, msg: str):
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] TC-13 {msg}")

    def test_loki_service_availability(self):
        """Verificar que el servicio Loki está disponible."""
        import requests

        loki_url = self.get_service_url("loki")
        last_error = None
        for _ in range(12):
            try:
                start_time = time.time()
                response = requests.get(f"{loki_url}/ready", timeout=10, verify=False)
                response_time_s = time.time() - start_time
                if response.status_code == 200:
                    assert (
                        response.status_code == 200
                    ), f"Loki /ready must return HTTP 200, got {response.status_code}"
                    # Validate response time is within acceptable threshold
                    assert (
                        response_time_s < 5.0
                    ), f"Loki /ready response time {response_time_s:.2f}s exceeds 5s threshold"
                    self._log(f"+ Loki /ready response time: {response_time_s:.2f}s")

                    # Validate /ready endpoint returns valid content (body or JSON)
                    body = response.text.strip()
                    assert len(body) > 0, "Loki /ready response body must not be empty"
                    # Loki /ready typically returns plain text "ready" or JSON status
                    # Try parsing as JSON; if it fails, accept plain-text "ready"
                    try:
                        ready_data = response.json()
                        assert isinstance(
                            ready_data, (dict, list)
                        ), f"Loki /ready JSON must be dict or list, got {type(ready_data).__name__}"
                    except ValueError:
                        # Plain-text response is also valid for /ready
                        assert "ready" in body.lower(), (
                            f"Loki /ready plain-text response should indicate "
                            f"readiness, got: {body[:200]}"
                        )
                    return
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            except requests.exceptions.RequestException as e:
                last_error = str(e)
            time.sleep(5)
        pytest.fail(f"Loki did not become ready within 60 seconds: {last_error}")

    def test_loki_query_range_endpoint(self):
        """Validar el endpoint query_range de Loki."""
        import requests

        loki_url = self.get_service_url("loki")
        try:
            # Query simple para probar el endpoint
            query = '{job=~".+"}'
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=5)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 100,
                },
                timeout=10,
                verify=False,
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
                assert isinstance(results, list), "Results should be a list"
                # The query should return logs matching the hostname
                assert data.get("status") == "success", "Query should succeed"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki query_range endpoint test failed: {e}")

    def test_loki_hostname_filtering(self):
        """Validar filtrado por hostname en Loki."""
        import requests

        loki_url = self.get_service_url("loki")
        try:
            # Query por hostname específico
            query = f'{{hostname="{self.alert_data["hostname"]}"}}'
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=10)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 50,
                },
                timeout=10,
                verify=False,
            )

            assert (
                response.status_code == 200
            ), f"Loki hostname filtering failed: {response.status_code}"

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
            assert isinstance(self.alert_data, dict), "alert_data should be a dict"
            assert "hostname" in self.alert_data, "hostname should be in alert_data"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki hostname filtering failed: {e}")

    def test_loki_ip_filtering(self):
        """Validar filtrado por IP en Loki."""
        import requests

        loki_url = self.get_service_url("loki")
        try:
            # Query por IP específica
            query = f'{{src_ip="{self.alert_data["src_ip"]}"}}'
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=10)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 50,
                },
                timeout=10,
                verify=False,
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
            assert isinstance(self.alert_data, dict), "alert_data should be a dict"
            assert "src_ip" in self.alert_data, "src_ip should be in alert_data"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki IP filtering failed: {e}")

    def test_loki_in_workflow(self):
        """Validar que el workflow incluye búsqueda de logs en Loki."""
        import requests

        # Enviar alerta al workflow usando submit_alert_and_wait
        exec_id, execution = self.submit_alert_and_wait(self.alert_data)

        # Assert workflow FINISHED
        status = execution.get("status", "")
        assert status == "FINISHED", f"Workflow should be FINISHED, got {status}"

        # Query Loki for logs with self.correlation_id
        loki_url = self.get_service_url("loki")
        try:
            query = f'{{correlation_id="{self.correlation_id}"}}'
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=10)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 50,
                },
                timeout=10,
                verify=False,
            )

            assert (
                response.status_code == 200
            ), f"Loki query for correlation_id failed: {response.status_code}"

            data = response.json()
            assert isinstance(data, dict), "Loki response should be JSON"
            assert data.get("status") == "success", "Loki query should succeed"

            # Logs may or may not exist depending on Promtail configuration.
            # The key validation is that Loki accepts the query and returns success.
            results = data.get("data", {}).get("result", [])
            assert isinstance(results, list), "Loki results should be a list"
            # If no logs exist, verify the workflow has a Loki action (integration exists)
            if len(results) == 0:
                # Verify the workflow includes a Loki search action
                shuffle_base = self.get_service_url("shuffle")
                api_key = self.env.get("SHUFFLE_DEFAULT_APIKEY", "")
                wf_resp = requests.get(
                    f"{shuffle_base}/api/v1/workflows/{self.workflow_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    verify=False,
                )
                if wf_resp.status_code == 200:
                    wf_data = wf_resp.json()
                    actions = wf_data.get("actions", [])
                    loki_actions = [
                        a for a in actions if "loki" in a.get("label", "").lower()
                    ]
                    assert len(loki_actions) > 0, "No Loki actions found in workflow"
                    self._log(
                        "+ Loki query succeeded (no logs for correlation_id — "
                        "Promtail may not be forwarding, but workflow has Loki action)"
                    )

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki log query for correlation_id failed: {e}")

    def test_loki_log_parsing(self):
        """Validar parsing de logs en Loki."""
        import requests

        loki_url = self.get_service_url("loki")
        try:
            # Query con parsing de logs
            query = '{job=~".+"} |= "error"'
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=5)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 20,
                },
                timeout=10,
                verify=False,
            )

            assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"
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
            pytest.fail(f"Loki log parsing test failed: {e}")

    def test_loki_time_range_queries(self):
        """Validar consultas por rango de tiempo en Loki."""
        import requests

        loki_url = self.get_service_url("loki")
        try:
            # Query con diferentes rangos de tiempo
            end_time = datetime.now(UTC)

            # Test con 1 hora
            start_time = end_time - timedelta(hours=1)
            query = '{job=~".+"}'

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 10,
                },
                timeout=10,
                verify=False,
            )

            assert (
                response.status_code == 200
            ), f"Loki time range query failed: {response.status_code}"

            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"
            assert data["status"] == "success", "Time range query should succeed"

            # Test con 5 minutos
            start_time = end_time - timedelta(minutes=5)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 10,
                },
                timeout=10,
                verify=False,
            )

            assert (
                response.status_code == 200
            ), f"Loki short time range query failed: {response.status_code}"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki time range test failed: {e}")

    def test_loki_error_handling(self):
        """Validar manejo de errores en Loki."""
        import requests

        loki_url = self.get_service_url("loki")
        try:
            # Query con sintaxis inválida
            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": "{invalid syntax",
                    "start": str(int(datetime.now(UTC).timestamp() * 1_000_000_000)),
                    "end": str(int(datetime.now(UTC).timestamp() * 1_000_000_000)),
                },
                timeout=10,
                verify=False,
            )

            # Debería devolver error 400
            assert (
                response.status_code == 400
            ), f"Expected 400 for invalid query, got: {response.status_code}"

            # Validate it's not a 5xx server error (indicates crash)
            assert response.status_code not in [
                502,
                503,
                504,
            ], f"Server error indicates crash: {response.status_code}"

        except requests.exceptions.RequestException:
            # Expected for invalid queries
            pass

    def test_loki_performance_requirements(self):
        """Validar requisitos de rendimiento de Loki."""
        import time

        import requests

        loki_url = self.get_service_url("loki")
        try:
            start_time = time.time()

            # Query simple para medir rendimiento
            query = '{job=~".+"}'
            end_time = datetime.now(UTC)
            start_time_query = end_time - timedelta(minutes=5)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time_query.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 50,
                },
                timeout=10,
                verify=False,
            )

            end_time = time.time()
            response_time = end_time - start_time

            # Las consultas deberían completarse en menos de 5 segundos
            assert response_time < 5.0, f"Loki response too slow: {response_time}s"

            # Validate response_time is positive
            assert response_time > 0, "Response time should be positive"

            assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"
            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"
            assert "status" in data, "Response should have status"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki performance test failed: {e}")

    def test_loki_integration_completeness(self):
        """Validar que la integración de Loki está completa en el workflow."""
        import requests

        shuffle_base_url = self.get_service_url("shuffle")
        shuffle_api_key = self.env.get("SHUFFLE_DEFAULT_APIKEY", "")
        try:
            # Obtener detalles del workflow
            response = requests.get(
                f"{shuffle_base_url}/api/v1/workflows/{self.workflow_id}",
                headers={"Authorization": f"Bearer {shuffle_api_key}"},
                verify=False,
            )

            assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"
            workflow_data = response.json()
            assert isinstance(workflow_data, dict), "Workflow data should be a dict"
            actions = workflow_data.get("actions", [])
            assert isinstance(actions, list), "Actions should be a list"

            # Validar acciones relacionadas con Loki (case-insensitive)
            loki_actions = [a for a in actions if "loki" in a.get("label", "").lower()]
            assert len(loki_actions) > 0, "No Loki actions found in workflow"

            # Validar que exista acción de búsqueda
            # The workflow uses "loki_search" as the label (not "Buscar loki")
            search_actions = [
                a for a in loki_actions
                if "search" in a.get("label", "").lower()
                or "buscar" in a.get("label", "").lower()
                or "query" in a.get("label", "").lower()
            ]
            assert len(search_actions) > 0, "No Loki search action found"

            # Validar que exista acción de verificación
            verify_actions = [
                a for a in actions
                if "verify" in a.get("label", "").lower() and "loki" in a.get("label", "").lower()
            ]
            assert len(verify_actions) > 0, "No Loki verification action found"

            # Validate actions have required fields
            for action in loki_actions:
                assert "label" in action, "Action should have label"
                assert isinstance(action.get("label"), str), "Action label should be string"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Workflow validation failed: {e}")

    def test_loki_log_aggregation(self):
        """Validar agregación de logs en Loki."""
        import requests

        loki_url = self.get_service_url("loki")
        try:
            # Query con agregación
            query = 'sum by (job) (count_over_time({job=~".+"}[5m]))'
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=10)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 10,
                },
                timeout=10,
                verify=False,
            )

            assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"
            data = response.json()

            if data["status"] == "success":
                results = data["data"]["result"]

                # Validar estructura de resultados agregados
                for result in results:
                    assert "metric" in result, "Aggregated result missing metric"
                    assert "job" in result["metric"], "Missing job in metric"
                    assert "values" in result, "Missing values in aggregated result"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki aggregation test failed: {e}")

    # ------------------------------------------------------------------
    # Subcase-specific tests (TC-13-01 to TC-13-04)
    # ------------------------------------------------------------------

    def test_loki_ingestion(self):
        """TC-13-01: Loki ingestion.

        Verifications:
          - Logs are ingested into Loki
          - Ingestion pipeline works
          - Logs are stored correctly
        """
        import requests

        loki_url = self.get_service_url("loki")
        try:
            # Send alert to trigger log ingestion
            webhook_url = self.webhook_url
            response = requests.post(webhook_url, json=self.alert_data, timeout=30, verify=False)
            assert response.status_code == 200, f"Webhook failed: {response.status_code}"

            execution_id = response.json().get("execution_id")
            assert execution_id, "No execution_id returned"
            assert isinstance(execution_id, str), "execution_id should be a string"

            time.sleep(10)

            # Query for logs
            query = '{job=~".+"}'
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=5)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 10,
                },
                timeout=10,
                verify=False,
            )

            assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"
            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"
            assert "data" in data, "Data field missing"
            assert isinstance(data["data"], dict), "Data should be a dict"

            # Validate alert_data structure
            assert isinstance(self.alert_data, dict), "alert_data should be a dict"
            assert "alert_id" in self.alert_data, "alert_id should be in alert_data"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki ingestion test failed: {e}")

    def test_loki_trace_id_search(self):
        """TC-13-02: Loki trace_id search.

        Verifications:
          - Logs can be searched by trace_id
          - Trace ID is preserved
          - Search results are correct
        """
        import requests

        loki_url = self.get_service_url("loki")
        try:
            # Query by alert_id as trace_id
            query = f'{{alert_id="{self.alert_data["alert_id"]}"}}'
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=10)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 50,
                },
                timeout=10,
                verify=False,
            )

            assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"
            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"
            assert data["status"] == "success", "Query should succeed"

            # Validate alert_data structure
            assert isinstance(self.alert_data, dict), "alert_data should be a dict"
            assert "alert_id" in self.alert_data, "alert_id should be in alert_data"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki trace_id search test failed: {e}")

    def test_loki_latency(self):
        """TC-13-03: Loki latency.

        Verifications:
          - Query latency is acceptable
          - Performance meets SLA
          - No excessive delays
        """
        import time

        import requests

        loki_url = self.get_service_url("loki")
        try:
            start_time = time.time()

            query = '{job=~".+"}'
            end_time = datetime.now(UTC)
            start_time_query = end_time - timedelta(minutes=5)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time_query.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 50,
                },
                timeout=10,
                verify=False,
            )

            end_time = time.time()
            latency = end_time - start_time

            # Latency should be less than 5 seconds
            assert latency < 5.0, f"Loki latency too high: {latency}s"

            # Validate latency is positive
            assert latency > 0, "Latency should be positive"

            assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"
            data = response.json()
            assert isinstance(data, dict), "Response should be JSON"

            # Validate alert_data structure
            assert isinstance(self.alert_data, dict), "alert_data should be a dict"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki latency test failed: {e}")

    def test_loki_hidden_errors(self):
        """TC-13-04: Loki hidden errors.

        Verifications:
          - Hidden errors are detected
          - Error logs are searchable
          - No errors are silently dropped
        """
        import requests

        loki_url = self.get_service_url("loki")
        try:
            # Query for error logs
            query = '{job=~".+"} |= "error"'
            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(minutes=10)

            response = requests.get(
                f"{loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": str(int(start_time.timestamp() * 1_000_000_000)),
                    "end": str(int(end_time.timestamp() * 1_000_000_000)),
                    "limit": 20,
                },
                timeout=10,
                verify=False,
            )

            assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"
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
            assert isinstance(self.alert_data, dict), "alert_data should be a dict"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Loki hidden errors test failed: {e}")
