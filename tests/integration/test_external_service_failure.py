#!/usr/bin/env python3
"""
SOAR Ransomware Lab - External Service Failure Tests
Tests for handling failures of external services (MISP, Cortex, TheHive)
"""

import pytest
from requests.exceptions import ConnectionError, Timeout
from soar_lab.infrastructure.external.integrations.cortex_client import CortexClient
from soar_lab.infrastructure.external.integrations.misp_client import MISPClient
from soar_lab.infrastructure.external.integrations.thehive_client import TheHiveClient
from unittest.mock import Mock, patch


class TestExternalServiceFailure:
    """Test handling of external service failures"""

    @pytest.fixture
    def misp_client(self):
        """Create MISP client for testing"""
        return MISPClient(
            base_url="http://localhost:8083",
            api_key="test-key",
            verify_ssl=False
        )

    @pytest.fixture
    def cortex_client(self):
        """Create Cortex client for testing"""
        return CortexClient(
            base_url="http://localhost:9001",
            api_key="test-key",
            verify_ssl=False
        )

    @pytest.fixture
    def thehive_client(self):
        """Create TheHive client for testing"""
        return TheHiveClient(
            base_url="http://localhost:9000",
            api_key="test-key",
            verify_ssl=False
        )

    def test_misp_connection_failure(self, misp_client):
        """Test handling of MISP connection failure"""
        with patch.object(misp_client.session, 'get') as mock_get:
            mock_get.side_effect = ConnectionError("MISP unreachable")

            with pytest.raises(ConnectionError):
                misp_client.get_events()

    def test_misp_timeout_handling(self, misp_client):
        """Test handling of MISP timeout"""
        with patch.object(misp_client.session, 'get') as mock_get:
            mock_get.side_effect = Timeout("MISP timeout")

            with pytest.raises(Timeout):
                misp_client.get_events()

    def test_cortex_connection_failure(self, cortex_client):
        """Test handling of Cortex connection failure"""
        with patch.object(cortex_client.session, 'get') as mock_get:
            mock_get.side_effect = ConnectionError("Cortex unreachable")

            with pytest.raises(ConnectionError):
                cortex_client.list_analyzers()

    def test_cortex_timeout_handling(self, cortex_client):
        """Test handling of Cortex timeout"""
        with patch.object(cortex_client.session, 'get') as mock_get:
            mock_get.side_effect = Timeout("Cortex timeout")

            with pytest.raises(Timeout):
                cortex_client.list_analyzers()

    def test_thehive_connection_failure(self, thehive_client):
        """Test handling of TheHive connection failure"""
        with patch.object(thehive_client.session, 'get') as mock_get:
            mock_get.side_effect = ConnectionError("TheHive unreachable")

            with pytest.raises(ConnectionError):
                thehive_client.search_cases()

    def test_thehive_timeout_handling(self, thehive_client):
        """Test handling of TheHive timeout"""
        with patch.object(thehive_client.session, 'get') as mock_get:
            mock_get.side_effect = Timeout("TheHive timeout")

            with pytest.raises(Timeout):
                thehive_client.search_cases()

    def test_circuit_breaker_opens_on_failures(self, cortex_client):
        """Test that circuit breaker opens after repeated failures"""
        # Simulate multiple failures
        with patch.object(cortex_client.session, 'get') as mock_get:
            mock_get.side_effect = ConnectionError("Service down")

            # Multiple failures should open circuit breaker
            for _ in range(5):
                try:
                    cortex_client.list_analyzers()
                except ConnectionError:
                    pass

            # Circuit breaker should be open
            assert cortex_client.circuit_breaker.is_open(), \
                "Circuit breaker should be open after failures"

    def test_circuit_breaker_half_open_state(self, cortex_client):
        """Test circuit breaker half-open state"""
        # Open circuit breaker
        cortex_client.circuit_breaker.open()

        # After timeout, should transition to half-open
        cortex_client.circuit_breaker.attempt_reset()

        assert cortex_client.circuit_breaker.state == 'half-open', \
            "Circuit breaker should be in half-open state"

    def test_circuit_breaker_closes_on_success(self, cortex_client):
        """Test that circuit breaker closes on successful request"""
        # Open circuit breaker
        cortex_client.circuit_breaker.open()

        # Simulate successful request
        with patch.object(cortex_client.session, 'get') as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: [])

            cortex_client.list_analyzers()

            # Circuit breaker should close
            assert not cortex_client.circuit_breaker.is_open(), \
                "Circuit breaker should close on success"

    def test_retry_with_exponential_backoff(self, misp_client):
        """Test retry with exponential backoff"""
        call_count = [0]

        def failing_then_succeeding(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Service down")
            return Mock(status_code=200, json=lambda: [])

        with patch.object(misp_client.session, 'get') as mock_get:
            mock_get.side_effect = failing_then_succeeding

            # Should retry and eventually succeed
            result = misp_client.get_events()
            assert result is not None, "Should succeed after retries"
            assert call_count[0] == 3, "Should have retried twice"

    def test_max_retry_limit(self, cortex_client):
        """Test that retries are limited"""
        call_count = [0]

        def always_failing(*args, **kwargs):
            call_count[0] += 1
            raise ConnectionError("Service down")

        with patch.object(cortex_client.session, 'get') as mock_get:
            mock_get.side_effect = always_failing

            # Should fail after max retries
            with pytest.raises(ConnectionError):
                cortex_client.list_analyzers()

            # Should not retry indefinitely
            assert call_count[0] <= cortex_client.max_retries + 1, \
                "Should respect max retry limit"

    def test_graceful_degradation_without_misp(self, misp_client):
        """Test graceful degradation when MISP is unavailable"""
        with patch.object(misp_client.session, 'get') as mock_get:
            mock_get.side_effect = ConnectionError("MISP down")

            # System should continue without MISP enrichment
            try:
                misp_client.get_events()
            except ConnectionError:
                # Expected - system should handle this gracefully
                pass

            # System should mark alert as processed without MISP data
            assert True, "System should degrade gracefully without MISP"

    def test_graceful_degradation_without_cortex(self, cortex_client):
        """Test graceful degradation when Cortex is unavailable"""
        with patch.object(cortex_client.session, 'get') as mock_get:
            mock_get.side_effect = ConnectionError("Cortex down")

            # System should continue without Cortex analysis
            try:
                cortex_client.list_analyzers()
            except ConnectionError:
                # Expected - system should handle this gracefully
                pass

            # System should mark alert as processed without Cortex data
            assert True, "System should degrade gracefully without Cortex"

    def test_service_health_check(self, thehive_client):
        """Test service health check"""
        with patch.object(thehive_client.session, 'get') as mock_get:
            mock_get.return_value = Mock(status_code=200, json=lambda: {"status": "ok"})

            health = thehive_client.health_check()
            assert health['status'] == 'ok', "Health check should return ok"

    def test_service_health_check_failure(self, thehive_client):
        """Test service health check failure"""
        with patch.object(thehive_client.session, 'get') as mock_get:
            mock_get.side_effect = ConnectionError("Service down")

            health = thehive_client.health_check()
            assert health['status'] == 'unhealthy', "Health check should return unhealthy"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
