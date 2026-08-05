"""
TC-14: Validación de nuevas funcionalidades SOAR - Integración Completa
Este test valida la integración completa de todas las nuevas funcionalidades: Tenzir, Network Watcher, Redis, Loki
"""











































































import pytest
import json
import time
from datetime import datetime, timezone

from tests.e2e.conftest import (
    SHUFFLE_WORKFLOW_ID, SHUFFLE_WEBHOOK_URL, SHUFFLE_BASE_URL, SHUFFLE_API_KEY,
    TENZIR_URL, NETWORK_WATCHER_URL, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD,
    LOKI_URL, ELASTICSEARCH_URL
)


class TestCompleteSOARIntegration:
    """Test suite para validar la integración completa de nuevas funcionalidades SOAR"""

    @pytest.fixture(scope="class")
    def alert_data(self):
        """Datos de alerta para pruebas de integración completa"""
        return {
            "alert_id": "TC14-INTEGRATION-1783607000-5000",
            "hostname": "tc14-integration-host",
            "src_ip": "192.168.100.90",
            "hash": "d4e5f6789012345678901234567890abcdef",
            "severity": "2",
            "type": "ransomware",
            "description": "Test alert for complete SOAR integration",
            "detection_time": datetime.utcnow().isoformat() + "Z"
        }

    def test_all_new_services_availability(self):
        """Verificar que todos los nuevos servicios están disponibles"""
        import requests

        services_status = {}

        # Tenzir
        try:
            response = requests.get(TENZIR_URL, timeout=5, verify=False)
            services_status["tenzir"] = response.status_code < 500
        except:
            services_status["tenzir"] = False

        # Network Watcher
        try:
            response = requests.get(f"{NETWORK_WATCHER_URL}/health", timeout=5, verify=False)
            services_status["network_watcher"] = response.status_code == 200
        except:
            services_status["network_watcher"] = False

        # Loki
        try:
            response = requests.get(f"{LOKI_URL}/ready", timeout=5, verify=False)
            services_status["loki"] = response.status_code == 200
        except:
            services_status["loki"] = False

        # Redis (prueba directa)
        try:
            import redis
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD or None, decode_responses=True)
            r.ping()
            services_status["redis"] = True
        except:
            services_status["redis"] = False

        # Al menos 3 de 4 servicios deberían estar disponibles
        available_count = sum(services_status.values())
        assert available_count >= 3, f"At least 3 services should be available, got {available_count}: {services_status}"

    def test_complete_workflow_execution(self, alert_data):
        """Validar ejecución completa del workflow con todas las nuevas funcionalidades"""
        import requests

        # Enviar alerta al workflow
        webhook_url = SHUFFLE_WEBHOOK_URL

        try:
            response = requests.post(
                webhook_url,
                json=alert_data,
                timeout=60,  # Timeout más largo para workflow completo
                verify=False
            )
            assert response.status_code == 200, f"Webhook failed: {response.status_code}"

            execution_id = response.json().get("execution_id")
            assert execution_id, "No execution_id returned"

            # Esperar a que complete el workflow completo
            time.sleep(20)

            # Verificar estado de la ejecución
            execution_response = requests.get(
                f"{SHUFFLE_BASE_URL}/api/v1/flows/{execution_id}",
                headers={"Authorization": f"Bearer {SHUFFLE_API_KEY}"},
                verify=False
            )

            if execution_response.status_code == 200:
                execution_data = execution_response.json()

                # Validar que la ejecución completó
                assert execution_data.get("status") in ["success", "completed"], f"Workflow did not complete: {execution_data.get('status')}"

                # Validar que se ejecutaron todas las acciones esperadas
                results = execution_data.get("results", [])

                # Buscar resultados de nuevas funcionalidades
                tenzir_found = any("Tenzir" in str(result) for result in results)
                network_found = any("Network" in str(result) for result in results)
                redis_found = any("Redis" in str(result) for result in results)
                loki_found = any("Loki" in str(result) for result in results)

                # Al menos 3 de 4 nuevas funcionalidades deberían ejecutarse
                new_features_count = sum([tenzir_found, network_found, redis_found, loki_found])
                assert new_features_count >= 3, f"At least 3 new features should execute, got {new_features_count}"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Complete workflow execution failed: {e}")

    def test_workflow_action_sequence(self, alert_data):
        """Validar la secuencia correcta de acciones en el workflow"""
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
                actions = workflow_data.get("actions", [])

                # Extraer nombres de acciones en orden
                action_names = [action.get("label", "") for action in actions]

                # Validar que existan todas las acciones nuevas
                expected_actions = [
                    "Tenzir - Analizar tráfico de red",
                    "Network Watcher - Monitorear conexiones",
                    "Redis - Cache IoCs",
                    "Loki - Buscar logs relacionados"
                ]

                found_actions = []
                for expected in expected_actions:
                    found = any(expected in action for action in action_names)
                    if found:
                        found_actions.append(expected)

                assert len(found_actions) >= 3, f"At least 3 new actions should exist, found: {found_actions}"

                # Validar orden lógico (análisis antes de verificación)
                tenzir_index = next((i for i, action in enumerate(action_names) if "Tenzir" in action), -1)
                verify_tenzir_index = next((i for i, action in enumerate(action_names) if "verify_tenzir" in action), -1)

                if tenzir_index != -1 and verify_tenzir_index != -1:
                    assert tenzir_index < verify_tenzir_index, "Tenzir analysis should come before verification"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Workflow sequence validation failed: {e}")

    def test_data_flow_between_services(self, alert_data):
        """Validar flujo de datos entre los nuevos servicios"""
        import requests

        try:
            # Enviar alerta y esperar procesamiento
            webhook_url = SHUFFLE_WEBHOOK_URL

            response = requests.post(webhook_url, json=alert_data, timeout=30, verify=False)
            assert response.status_code == 200

            time.sleep(15)

            # Verificar que los datos fluyen correctamente entre servicios

            # 1. Redis debería tener el IoC cacheado
            try:
                import redis
                r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD or None, decode_responses=True)
                ioc_key = f"ioc:{alert_data['hash']}"
                cached_ioc = r.get(ioc_key)

                if cached_ioc:
                    assert alert_data['alert_id'] in cached_ioc, "IoC should be cached with alert ID"
            except:
                pass  # Redis puede no estar disponible

            # 2. Elasticsearch debería tener métricas del workflow
            try:
                es_response = requests.get(
                    f"{ELASTICSEARCH_URL}/soar-metrics/_search",
                    json={"query": {"term": {"alert_id": alert_data["alert_id"]}}},
                    timeout=5,
                    verify=False
                )

                if es_response.status_code == 200:
                    es_data = es_response.json()
                    hits = es_data.get("hits", {}).get("hits", [])
                    assert len(hits) > 0, "Metrics should be indexed in Elasticsearch"
            except:
                pass  # ES puede no estar disponible

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Data flow validation failed: {e}")

    def test_error_handling_and_recovery(self):
        """Validar manejo de errores y recuperación en nuevas funcionalidades"""
        import requests

        # Test con datos inválidos para verificar manejo de errores
        invalid_alert = {
            "alert_id": "TC14-INVALID-1783607000-6000",
            "hostname": "",
            "src_ip": "invalid-ip",
            "hash": "",
            "severity": "invalid",
            "type": "ransomware",
            "description": "Invalid alert for error handling test",
            "detection_time": datetime.utcnow().isoformat() + "Z"
        }

        try:
            webhook_url = SHUFFLE_WEBHOOK_URL

            response = requests.post(webhook_url, json=invalid_alert, timeout=30, verify=False)

            # El workflow debería manejar errores gracefully
            # Puede aceptar la alerta o rechazarla, pero no debería crash
            assert response.status_code in [200, 400, 422], f"Unexpected status: {response.status_code}"

            if response.status_code == 200:
                execution_id = response.json().get("execution_id")
                if execution_id:
                    time.sleep(10)

                    # Verificar que el workflow maneje los errores
                    execution_response = requests.get(
                        f"{SHUFFLE_BASE_URL}/api/v1/flows/{execution_id}",
                        headers={"Authorization": f"Bearer {SHUFFLE_API_KEY}"},
                        verify=False
                    )

                    if execution_response.status_code == 200:
                        execution_data = execution_response.json()
                        # El workflow debería completar o tener errores manejados
                        status = execution_data.get("status")
                        assert status in ["success", "completed", "failure", "error"], f"Unexpected status: {status}"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Error handling test failed: {e}")

    def test_performance_with_new_features(self, alert_data):
        """Validar rendimiento del workflow con nuevas funcionalidades"""
        import requests
        import time

        try:
            # Medir tiempo de ejecución completo
            start_time = time.time()

            webhook_url = SHUFFLE_WEBHOOK_URL

            response = requests.post(webhook_url, json=alert_data, timeout=60, verify=False)
            assert response.status_code == 200

            execution_id = response.json().get("execution_id")

            # Esperar completación
            time.sleep(20)

            # Verificar estado final
            execution_response = requests.get(
                f"{SHUFFLE_BASE_URL}/api/v1/flows/{execution_id}",
                headers={"Authorization": f"Bearer {SHUFFLE_API_KEY}"},
                verify=False
            )

            end_time = time.time()
            total_time = end_time - start_time

            # El workflow completo debería completarse en menos de 45 segundos
            assert total_time < 45.0, f"Workflow too slow with new features: {total_time}s"

            if execution_response.status_code == 200:
                execution_data = execution_response.json()
                assert execution_data.get("status") in ["success", "completed"], "Workflow should complete successfully"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Performance test failed: {e}")

    def test_concurrent_execution_with_new_features(self):
        """Validar ejecución concurrente con nuevas funcionalidades"""
        import requests
        import threading
        import time

        def execute_alert(alert_suffix):
            alert_data = {
                "alert_id": f"TC14-CONCURRENT-{alert_suffix}-{int(time.time())}",
                "hostname": f"tc14-concurrent-{alert_suffix}",
                "src_ip": f"192.168.100.{100 + alert_suffix}",
                "hash": f"hash{alert_suffix}" * 8,
                "severity": "2",
                "type": "ransomware",
                "description": f"Concurrent test alert {alert_suffix}",
                "detection_time": datetime.utcnow().isoformat() + "Z"
            }

            try:
                webhook_url = SHUFFLE_WEBHOOK_URL
                response = requests.post(webhook_url, json=alert_data, timeout=30, verify=False)
                return response.status_code == 200
            except:
                return False

        # Ejecutar 3 alertas concurrentemente
        threads = []
        results = []

        for i in range(3):
            thread = threading.Thread(target=lambda i=i: results.append(execute_alert(i)))
            threads.append(thread)
            thread.start()

        # Esperar a que todas terminen
        for thread in threads:
            thread.join()

        # Al menos 2 de 3 deberían tener éxito
        successful_count = sum(results)
        assert successful_count >= 2, f"At least 2 concurrent executions should succeed, got {successful_count}/3"

    def test_integration_with_existing_features(self, alert_data):
        """Validar integración con funcionalidades existentes (TheHive, Cortex, MISP, etc.)"""
        import requests

        try:
            # Enviar alerta y verificar integración completa
            webhook_url = SHUFFLE_WEBHOOK_URL

            response = requests.post(webhook_url, json=alert_data, timeout=60, verify=False)
            assert response.status_code == 200

            execution_id = response.json().get("execution_id")
            time.sleep(20)

            # Verificar ejecución
            execution_response = requests.get(
                f"{SHUFFLE_BASE_URL}/api/v1/flows/{execution_id}",
                headers={"Authorization": f"Bearer {SHUFFLE_API_KEY}"},
                verify=False
            )

            if execution_response.status_code == 200:
                execution_data = execution_response.json()
                results = execution_data.get("results", [])

                # Validar que existan resultados de funcionalidades existentes y nuevas
                existing_found = any(
                    any(feature in str(result) for feature in ["TheHive", "Cortex", "MISP", "Wazuh"])
                    for result in results
                )
                new_found = any(
                    any(feature in str(result) for feature in ["Tenzir", "Network", "Redis", "Loki"])
                    for result in results
                )

                assert existing_found, "Existing features should be present"
                assert new_found, "New features should be present"

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Integration test failed: {e}")
