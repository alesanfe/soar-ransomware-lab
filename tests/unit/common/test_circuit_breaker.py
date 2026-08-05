#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Circuit Breaker Tests
Unit tests for circuit breaker pattern
"""

import pytest
import time
from soar_lab.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerState
from unittest.mock import Mock


class TestCircuitBreaker:
    """Test circuit breaker pattern"""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing"""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5,
            expected_exception=Exception
        )

    def test_circuit_breaker_initial_state(self, circuit_breaker):
        """Test that circuit breaker starts in closed state"""
        assert circuit_breaker.state == CircuitBreakerState.CLOSED, \
            "Circuit breaker should start in closed state"

    def test_circuit_breaker_opens_on_failures(self, circuit_breaker):
        """Test that circuit breaker opens after threshold failures"""
        # Simulate failures
        for _ in range(3):
            try:
                circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test failure")))
            except Exception:
                pass

        assert circuit_breaker.state == CircuitBreakerState.OPEN, \
            "Circuit breaker should open after threshold failures"

    def test_circuit_breaker_blocks_requests_when_open(self, circuit_breaker):
        """Test that circuit breaker blocks requests when open"""
        # Open the circuit breaker
        for _ in range(3):
            try:
                circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test failure")))
            except Exception:
                pass

        # Try to call when open
        with pytest.raises(Exception):
            circuit_breaker.call(lambda: "success")

    def test_circuit_breaker_transitions_to_half_open(self, circuit_breaker):
        """Test that circuit breaker transitions to half-open after timeout"""
        # Open the circuit breaker
        for _ in range(3):
            try:
                circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test failure")))
            except Exception:
                pass

        # Wait for recovery timeout
        time.sleep(6)

        # Successful call in half-open state should close the circuit
        result = circuit_breaker.call(lambda: "success")

        assert result == "success"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED, \
            "Circuit breaker should close on a successful half-open call"

    def test_circuit_breaker_closes_on_success(self, circuit_breaker):
        """Test that circuit breaker closes on successful call in half-open"""
        # Open the circuit breaker
        for _ in range(3):
            try:
                circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test failure")))
            except Exception:
                pass

        # Wait for recovery timeout
        time.sleep(6)

        # Successful call should close circuit
        result = circuit_breaker.call(lambda: "success")

        assert result == "success", "Call should succeed"
        assert circuit_breaker.state == CircuitBreakerState.CLOSED, \
            "Circuit breaker should close on success"

    def test_circuit_breaker_reopens_on_half_open_failure(self, circuit_breaker):
        """Test that circuit breaker reopens on failure in half-open"""
        # Open the circuit breaker
        for _ in range(3):
            try:
                circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test failure")))
            except Exception:
                pass

        # Wait for recovery timeout
        time.sleep(6)

        # Failed call should reopen circuit
        try:
            circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test failure")))
        except Exception:
            pass

        assert circuit_breaker.state == CircuitBreakerState.OPEN, \
            "Circuit breaker should reopen on half-open failure"

    def test_circuit_breaker_failure_count_reset(self, circuit_breaker):
        """Test that failure count resets on success"""
        # Simulate 2 failures (below threshold)
        for _ in range(2):
            try:
                circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test failure")))
            except Exception:
                pass

        # Successful call should reset failure count
        circuit_breaker.call(lambda: "success")

        # Should still be closed and need 3 more failures to open
        assert circuit_breaker.state == CircuitBreakerState.CLOSED, \
            "Circuit breaker should still be closed after success"

    def test_circuit_breaker_custom_threshold(self):
        """Test circuit breaker with custom threshold"""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=5)

        # Should not open until 5 failures
        for _ in range(4):
            try:
                cb.call(lambda: (_ for _ in ()).throw(Exception("Test failure")))
            except Exception:
                pass

        assert cb.state == CircuitBreakerState.CLOSED, \
            "Circuit breaker should not open before threshold"

    def test_circuit_breaker_custom_exception(self):
        """Test circuit breaker with custom exception type"""
        cb = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5,
            expected_exception=ValueError
        )

        # Other exceptions should not count as failures
        for _ in range(3):
            try:
                cb.call(lambda: (_ for _ in ()).throw(KeyError("Test")))
            except KeyError:
                pass

        assert cb.state == CircuitBreakerState.CLOSED, \
            "Circuit breaker should not open on different exception type"

    def test_circuit_breaker_context_manager(self, circuit_breaker):
        """Test circuit breaker as context manager"""
        # Open the circuit breaker
        for _ in range(3):
            try:
                circuit_breaker.call(lambda: (_ for _ in ()).throw(Exception("Test failure")))
            except Exception:
                pass

        # Use as context manager
        with pytest.raises(Exception):
            with circuit_breaker:
                pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
