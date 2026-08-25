"""
TC-12: Validación de nuevas funcionalidades SOAR - Redis
Este test valida la integración de Redis para cache de IoCs
"""

import time
from datetime import UTC, datetime

import pytest

from tests.e2e.base import E2EBaseTest


class TestRedisIntegration(E2EBaseTest):
    """Test suite para validar la integración de Redis en el workflow SOAR."""

    tc_id = "TC-12"

    @pytest.fixture(scope="class")
    def alert_data(self):
        """Datos de alerta para pruebas de Redis."""
        return {
            "alert_id": "TC12-REDIS-1783607000-3000",
            "hostname": "tc12-host",
            "src_ip": "192.168.100.70",
            "hash": "b2c3d4e5f6789012345678901234567890abcdef",
            "severity": "2",
            "type": "ransomware",
            "description": "Test alert for Redis IoC caching",
            "detection_time": datetime.now(UTC).isoformat() + "Z",
        }

    def test_redis_service_availability(self):
        """Verificar que el servicio Redis está disponible."""
        try:
            import redis

            r = redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password() or None,
                decode_responses=True,
            )
            result = r.ping()
            assert result is True, "Redis ping should return True"

            # Validate Redis server info is accessible and has expected fields
            info = r.info()
            assert isinstance(
                info, dict
            ), f"Redis info() must return a dict, got {type(info).__name__}"
            assert (
                "redis_version" in info
            ), f"Redis info must contain 'redis_version', got keys: {list(info.keys())[:10]}"
            self._log(f"+ Redis version: {info['redis_version']}")

            # Validate that Redis has active connections
            connected_clients = info.get("connected_clients", 0)
            assert isinstance(
                connected_clients, int
            ), f"connected_clients must be an integer, got {type(connected_clients).__name__}"
            assert (
                connected_clients > 0
            ), f"Redis should have at least 1 connected client, got {connected_clients}"
            self._log(f"+ Redis connected clients: {connected_clients}")
        except ImportError as e:
            pytest.fail(f"Redis library not available: {e}")
        except Exception as e:
            pytest.fail(f"Redis not available: {e}")

    def test_redis_direct_connection(self):
        """Validar conexión directa a Redis."""
        try:
            import redis

            r = redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password() or None,
                decode_responses=True,
            )

            # Probar ping
            result = r.ping()
            assert result, "Redis ping failed"

            # Probar set/get básico
            test_key = "test_connection"
            test_value = "test_value"

            r.set(test_key, test_value)
            retrieved = r.get(test_key)

            assert retrieved == test_value, "Redis set/get failed"

            # Limpiar
            r.delete(test_key)

        except ImportError as e:
            pytest.fail(f"Redis library not available: {e}")
        except Exception as e:
            pytest.fail(f"Redis direct connection failed: {e}")

    def test_redis_ioc_caching_in_workflow(self, alert_data):
        """Validar que el workflow incluye cache de IoCs en Redis."""
        # Enviar alerta al workflow usando submit_alert_and_wait
        exec_id, execution = self.submit_alert_and_wait(alert_data)

        # Assert workflow FINISHED
        status = execution.get("status", "")
        assert status == "FINISHED", f"Workflow should be FINISHED, got {status}"

        # Check Redis for cached IoC keys
        try:
            import redis

            r = redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password() or None,
                decode_responses=True,
            )

            # Search for IoC keys related to this alert
            ioc_keys = r.keys("ioc:*")
            assert isinstance(ioc_keys, list), "IoC keys should be a list"

            # Assert at least one IoC is cached
            assert (
                len(ioc_keys) > 0
            ), "At least one IoC should be cached in Redis after workflow execution"

            # Validate that cached IoCs have proper structure
            for key in ioc_keys[:5]:
                value = r.get(key)
                assert value is not None, f"Cached IoC key {key} should have a value"

        except ImportError as e:
            pytest.fail(f"Redis library not available: {e}")
        except Exception as e:
            pytest.fail(f"Redis IoC caching verification failed: {e}")

    def test_redis_ioc_storage(self, alert_data):
        """Validar almacenamiento de IoCs en Redis."""
        try:
            import redis

            r = redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password() or None,
                decode_responses=True,
            )

            # Simular almacenamiento de IoC como lo hace el workflow
            ioc_key = f"ioc:{alert_data['hash']}"
            ioc_value = f"{alert_data['alert_id']}:{alert_data['detection_time']}"

            # Almacenar IoC
            r.set(ioc_key, ioc_value, ex=3600)  # 1 hora TTL

            # Verificar almacenamiento
            stored_value = r.get(ioc_key)
            assert stored_value == ioc_value, "IoC storage failed"

            # Verificar TTL
            ttl = r.ttl(ioc_key)
            assert ttl > 0, "TTL not set correctly"
            assert ttl <= 3600, "TTL too high"

            # Limpiar
            r.delete(ioc_key)

        except ImportError as e:
            pytest.fail(f"Redis library not available: {e}")
        except Exception as e:
            pytest.fail(f"Redis IoC storage test failed: {e}")

    def test_redis_ioc_retrieval(self, alert_data):
        """Validar recuperación de IoCs desde Redis."""
        try:
            import redis

            r = redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password() or None,
                decode_responses=True,
            )

            # Preparar datos de prueba
            ioc_key = f"ioc:{alert_data['hash']}"
            ioc_value = f"{alert_data['alert_id']}:{alert_data['detection_time']}"

            # Almacenar IoC
            r.set(ioc_key, ioc_value, ex=3600)

            # Recuperar IoC
            retrieved_value = r.get(ioc_key)
            assert retrieved_value is not None, "IoC retrieval failed"

            # Parsear valor recuperado
            parts = retrieved_value.split(":")
            assert len(parts) >= 2, "Invalid IoC value format"

            retrieved_alert_id = parts[0]
            retrieved_timestamp = ":".join(parts[1:])  # Por si el timestamp tiene :

            assert retrieved_alert_id == alert_data["alert_id"], "Alert ID mismatch"
            assert retrieved_timestamp == alert_data["detection_time"], "Timestamp mismatch"

            # Limpiar
            r.delete(ioc_key)

        except ImportError as e:
            pytest.fail(f"Redis library not available: {e}")
        except Exception as e:
            pytest.fail(f"Redis IoC retrieval test failed: {e}")

    def test_redis_cache_expiration(self):
        """Validar expiración de cache en Redis."""
        try:
            import redis

            r = redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password() or None,
                decode_responses=True,
            )

            # Almacenar con TTL corto
            test_key = "test_expiration"
            test_value = "test_value"

            r.set(test_key, test_value, ex=2)  # 2 segundos

            # Verificar que existe
            assert r.get(test_key) is not None, "Key should exist immediately"

            # Esperar expiración
            time.sleep(3)

            # Verificar que expiró
            assert r.get(test_key) is None, "Key should have expired"

        except ImportError as e:
            pytest.fail(f"Redis library not available: {e}")
        except Exception as e:
            pytest.fail(f"Redis expiration test failed: {e}")

    def test_redis_pattern_matching(self):
        """Validar búsqueda por patrones en Redis."""
        try:
            import redis

            r = redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password() or None,
                decode_responses=True,
            )

            # Preparar múltiples IoCs
            test_iocs = [
                ("ioc:hash1", "alert1:timestamp1"),
                ("ioc:hash2", "alert2:timestamp2"),
                ("ioc:hash3", "alert3:timestamp3"),
                ("other:key1", "value1"),
            ]

            # Almacenar IoCs
            for key, value in test_iocs:
                r.set(key, value, ex=3600)

            # Buscar IoCs por patrón (filter to only our test keys)
            ioc_keys = r.keys("ioc:hash*")
            assert len(ioc_keys) >= 3, f"Expected at least 3 IoC keys, got {len(ioc_keys)}"

            # Verificar que todos los keys encontrados son IoCs
            for key in ioc_keys:
                assert key.startswith("ioc:"), f"Non-IoC key found: {key}"

            # Limpiar
            for key, _ in test_iocs:
                r.delete(key)

        except ImportError as e:
            pytest.fail(f"Redis library not available: {e}")
        except Exception as e:
            pytest.fail(f"Redis pattern matching test failed: {e}")

    def test_redis_performance_requirements(self):
        """Validar requisitos de rendimiento de Redis."""
        try:
            import redis

            r = redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password() or None,
                decode_responses=True,
            )

            # Probar rendimiento de operaciones básicas
            start_time = time.time()

            # Realizar múltiples operaciones
            for i in range(100):
                key = f"perf_test_{i}"
                value = f"value_{i}"
                r.set(key, value, ex=3600)
                retrieved = r.get(key)
                assert retrieved == value, f"Performance test failed at iteration {i}"

            end_time = time.time()
            total_time = end_time - start_time

            # 100 operaciones deberían completarse en menos de 1 segundo
            assert total_time < 1.0, f"Redis performance too slow: {total_time}s for 100 operations"

            # Limpiar
            for i in range(100):
                r.delete(f"perf_test_{i}")

        except ImportError as e:
            pytest.fail(f"Redis library not available: {e}")
        except Exception as e:
            pytest.fail(f"Redis performance test failed: {e}")

    def test_redis_error_handling(self):
        """Validar manejo de errores en Redis."""
        try:
            import redis

            r = redis.Redis(
                host=self.get_redis_host(),
                port=self.get_redis_port(),
                password=self.get_redis_password() or None,
                decode_responses=True,
            )

            # Probar operación con key que no existe
            result = r.get("non_existent_key")
            assert result is None, "Should return None for non-existent key"

            # Probar TTL en key que no existe
            ttl = r.ttl("non_existent_key")
            assert ttl == -2, "Should return -2 for non-existent key"

            # Probar delete en key que no existe
            result = r.delete("non_existent_key")
            assert result == 0, "Should return 0 for non-existent key"

        except ImportError as e:
            pytest.fail(f"Redis library not available: {e}")
        except Exception as e:
            pytest.fail(f"Redis error handling test failed: {e}")

    def test_redis_integration_completeness(self):
        """Validar que la integración de Redis está completa en el workflow."""
        import requests

        try:
            # Obtener detalles del workflow
            response = requests.get(
                f"{self.get_service_url('shuffle')}/api/v1/workflows/{self.workflow_id}",
                headers={"Authorization": f"Bearer {self.env.get('SHUFFLE_DEFAULT_APIKEY', '')}"},
                verify=False,
            )

            assert response.status_code in (
                200,
                401,
            ), f"Workflow API failed: {response.status_code}"
            assert response.status_code == 200, "Shuffle API key must be valid (got 401)"

            workflow_data = response.json()
            actions = workflow_data.get("actions", [])

            # Validar acciones relacionadas con Redis (case-insensitive)
            redis_actions = [a for a in actions if "redis" in a.get("label", "").lower()]
            assert len(redis_actions) > 0, "No Redis actions found in workflow"

            # Validar que exista acción de cache (case-insensitive)
            cache_actions = [a for a in redis_actions if "cache" in a.get("label", "").lower()]
            assert len(cache_actions) > 0, "No Redis cache action found"

            # Validar que exista acción de verificación
            verify_actions = [
                a for a in actions
                if "verify" in a.get("label", "").lower() and "redis" in a.get("label", "").lower()
            ]
            assert len(verify_actions) > 0, "No Redis verification action found in workflow"

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Workflow validation failed: {e}")
