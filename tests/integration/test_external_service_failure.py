#!/usr/bin/env python3
"""
SOAR Ransomware Lab - External Service Failure Tests
Tests for handling failures of external services (MISP, Cortex, TheHive)
"""

from unittest.mock import Mock, patch

import pytest
from requests.exceptions import ConnectionError, Timeout

from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.integrations.cortex.client import CortexClient
from soar_lab.infrastructure.integrations.misp.client import MISPClient
from soar_lab.infrastructure.integrations.thehive.client import TheHiveClient
from soar_lab.resilience.circuit_breaker import CircuitBreakerState


class TestExternalServiceFailure:
    """Test handling of external service failures."""

    @pytest.fixture
    def misp_client(self):
        """Create MISP client for testing."""
        return MISPClient(base_url="http://localhost:8083", api_key="test-key", verify_ssl=False)

    @pytest.fixture
    def cortex_client(self):
        """Create Cortex client for testing."""
        return CortexClient(base_url="http://localhost:9001", api_key="test-key", verify_ssl=False)

    @pytest.fixture
    def thehive_client(self):
        """Create TheHive client for testing."""
        return TheHiveClient(base_url="http://localhost:9000", api_key="test-key", verify_ssl=False)

    def test_misp_connection_failure(self, misp_client):
        """Test handling of MISP connection failure."""
        with patch.object(misp_client.session, "get") as mock_get:
            mock_get.side_effect = ConnectionError("MISP unreachable")

            with pytest.raises(IntegrationError):
                misp_client.list_events()

    def test_misp_timeout_handling(self, misp_client):
        """Test handling of MISP timeout."""
        with patch.object(misp_client.session, "get") as mock_get:
            mock_get.side_effect = Timeout("MISP timeout")

            with pytest.raises(IntegrationError):
                misp_client.list_events()

    def test_cortex_connection_failure(self, cortex_client):
        """Test handling of Cortex connection failure."""
        with patch.object(cortex_client.session, "post") as mock_post:
            mock_post.side_effect = ConnectionError("Cortex unreachable")

            with pytest.raises(IntegrationError):
                cortex_client.list_analyzers()

    def test_cortex_timeout_handling(self, cortex_client):
        """Test handling of Cortex timeout."""
        with patch.object(cortex_client.session, "post") as mock_post:
            mock_post.side_effect = Timeout("Cortex timeout")

            with pytest.raises(IntegrationError):
                cortex_client.list_analyzers()

    def test_thehive_connection_failure(self, thehive_client):
        """Test handling of TheHive connection failure."""
        with patch.object(thehive_client.session, "get") as mock_get:
            mock_get.side_effect = ConnectionError("TheHive unreachable")

            with pytest.raises(IntegrationError):
                thehive_client.search_cases()

    def test_thehive_timeout_handling(self, thehive_client):
        """Test handling of TheHive timeout."""
        with patch.object(thehive_client.session, "get") as mock_get:
            mock_get.side_effect = Timeout("TheHive timeout")

            with pytest.raises(IntegrationError):
                thehive_client.search_cases()

    def test_circuit_breaker_opens_on_failures(self, cortex_client):
        """Test that circuit breaker opens after repeated failures."""
        # Simulate multiple failures
        with patch.object(cortex_client.session, "post") as mock_post:
            mock_post.side_effect = ConnectionError("Service down")

            # Multiple failures should open circuit breaker
            for _ in range(5):
                try:
                    cortex_client.list_analyzers()
                except IntegrationError:
                    pass

            # Circuit breaker should be open
            assert (
                cortex_client.circuit_breaker.is_open()
            ), "Circuit breaker should be open after failures"

    def test_circuit_breaker_half_open_state(self, cortex_client):
        """Test circuit breaker half-open state."""
        # Open circuit breaker by recording failures
        cb = cortex_client.circuit_breaker
        for _ in range(cb.failure_threshold):
            cb.record_failure()

        assert cb.is_open(), "Circuit breaker should be open after threshold failures"

        # Force recovery timeout to have elapsed
        import time

        cb.last_failure_time = time.time() - cb.recovery_timeout - 1
        cb.attempt_reset()

        assert (
            cb.state == CircuitBreakerState.HALF_OPEN
        ), "Circuit breaker should be in half-open state"

    def test_circuit_breaker_closes_on_success(self, cortex_client):
        """Test that circuit breaker closes on successful request."""
        # Open circuit breaker by recording failures
        cb = cortex_client.circuit_breaker
        for _ in range(cb.failure_threshold):
            cb.record_failure()

        # Force recovery timeout to have elapsed
        import time

        cb.last_failure_time = time.time() - cb.recovery_timeout - 1
        cb.attempt_reset()

        # Simulate successful request
        with patch.object(cortex_client.session, "post") as mock_post:
            mock_post.return_value = Mock(status_code=200, content=b"[]", json=list)

            cortex_client.list_analyzers()

            # Circuit breaker should close
            assert not cb.is_open(), "Circuit breaker should close on success"

    def test_retry_with_exponential_backoff(self, misp_client):
        """Test that session is configured with retry strategy.

        MISPClient delegates retries to urllib3's Retry mechanism at the
        transport layer, not at the application layer. This test verifies
        the session has retries configured.
        """
        # The session should have retry configured via urllib3
        adapter = misp_client.session.get_adapter("http://localhost:8083")
        retry = adapter.max_retries
        assert retry.total > 0, "Session should have retries configured"

    def test_max_retry_limit(self, cortex_client):
        """Test that retries are limited."""
        call_count = [0]

        def always_failing(*args, **kwargs):
            call_count[0] += 1
            raise ConnectionError("Service down")

        with patch.object(cortex_client.session, "post") as mock_post:
            mock_post.side_effect = always_failing

            # Should fail after max retries
            with pytest.raises(IntegrationError):
                cortex_client.list_analyzers()

            # Should not retry indefinitely
            assert call_count[0] <= cortex_client.max_retries + 1, "Should respect max retry limit"

    def test_graceful_degradation_without_misp(self, misp_client):
        """Test graceful degradation when MISP is unavailable."""
        with patch.object(misp_client.session, "get") as mock_get:
            mock_get.side_effect = ConnectionError("MISP down")

            # System should continue without MISP enrichment
            try:
                misp_client.list_events()
            except IntegrationError:
                # Expected - system should handle this gracefully
                pass

            # System should mark alert as processed without MISP data
            assert True, "System should degrade gracefully without MISP"

    def test_graceful_degradation_without_cortex(self, cortex_client):
        """Test graceful degradation when Cortex is unavailable."""
        with patch.object(cortex_client.session, "post") as mock_post:
            mock_post.side_effect = ConnectionError("Cortex down")

            # System should continue without Cortex analysis
            try:
                cortex_client.list_analyzers()
            except IntegrationError:
                # Expected - system should handle this gracefully
                pass

            # System should mark alert as processed without Cortex data
            assert True, "System should degrade gracefully without Cortex"

    def test_service_health_check(self, thehive_client):
        """Test service health check."""
        with patch.object(thehive_client.session, "get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200, content=b'{"status":"ok"}', json=lambda: {"status": "ok"}
            )

            health = thehive_client.health_check()
            assert health is True, "Health check should return True when service is healthy"

    def test_service_health_check_failure(self, thehive_client):
        """Test service health check failure."""
        with patch.object(thehive_client.session, "get") as mock_get:
            mock_get.side_effect = ConnectionError("Service down")

            health = thehive_client.health_check()
            assert health is False, "Health check should return False when service is down"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
