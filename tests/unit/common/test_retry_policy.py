#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Retry Policy Tests
Unit tests for retry policy
"""

import pytest
import time
from soar_lab.resilience.retry import RetryPolicy, RetryStrategy
from unittest.mock import Mock


class TestRetryPolicy:
    """Test retry policy"""

    @pytest.fixture
    def retry_policy(self):
        """Create retry policy for testing"""
        return RetryPolicy(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=0.1
        )

    def test_exponential_backoff(self, retry_policy):
        """Test exponential backoff strategy"""
        call_count = [0]

        def failing_operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return "success"

        result = retry_policy.execute(failing_operation)

        assert result == "success", "Operation should succeed after retries"
        assert call_count[0] == 3, "Should have retried twice"

    def test_max_retries_limit(self, retry_policy):
        """Test that retries are limited to max_retries"""
        call_count = [0]

        def always_failing():
            call_count[0] += 1
            raise Exception("Always fails")

        with pytest.raises(Exception):
            retry_policy.execute(always_failing)

        assert call_count[0] == retry_policy.max_retries + 1, \
            "Should not exceed max retries"

    def test_retry_with_different_error_codes(self):
        """Test retry with different error codes"""
        retry_policy = RetryPolicy(
            max_retries=3,
            retryable_errors=[ConnectionError, TimeoutError],
            non_retryable_errors=[ValueError]
        )

        connection_count = [0]
        value_count = [0]

        def connection_error():
            connection_count[0] += 1
            raise ConnectionError("Connection failed")

        def value_error():
            value_count[0] += 1
            raise ValueError("Invalid value")

        # ConnectionError should be retried
        with pytest.raises(ConnectionError):
            retry_policy.execute(connection_error)
        assert connection_count[0] == 4, "ConnectionError should be retried"

        # ValueError should not be retried
        with pytest.raises(ValueError):
            retry_policy.execute(value_error)
        assert value_count[0] == 1, "ValueError should not be retried"

    def test_retry_idempotent(self, retry_policy):
        """Test that retry is idempotent"""
        call_count = [0]

        def idempotent_operation():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Temporary failure")
            return "success"

        result1 = retry_policy.execute(idempotent_operation)
        result2 = retry_policy.execute(idempotent_operation)

        assert result1 == result2, "Results should be identical"

    def test_linear_backoff(self):
        """Test linear backoff strategy"""
        retry_policy = RetryPolicy(
            max_retries=3,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            base_delay=0.1
        )

        call_count = [0]
        delays = []

        def failing_operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return "success"

        result = retry_policy.execute(failing_operation)

        assert result == "success", "Operation should succeed"

    def test_no_retry_on_success(self, retry_policy):
        """Test that successful operations are not retried"""
        call_count = [0]

        def successful_operation():
            call_count[0] += 1
            return "success"

        result = retry_policy.execute(successful_operation)

        assert result == "success", "Operation should succeed"
        assert call_count[0] == 1, "Should not retry successful operation"

    def test_retry_with_jitter(self):
        """Test retry with jitter"""
        retry_policy = RetryPolicy(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF_WITH_JITTER,
            base_delay=0.1,
            jitter_factor=0.1
        )

        call_count = [0]

        def failing_operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return "success"

        result = retry_policy.execute(failing_operation)

        assert result == "success", "Operation should succeed with jitter"

    def test_retry_timeout(self):
        """Test retry with overall timeout"""
        retry_policy = RetryPolicy(
            max_retries=10,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=0.1,
            timeout=1.0
        )

        call_count = [0]

        def slow_failing_operation():
            call_count[0] += 1
            time.sleep(0.2)
            raise Exception("Slow failure")

        with pytest.raises(Exception):
            retry_policy.execute(slow_failing_operation)

        # Should timeout before max retries
        assert call_count[0] < 10, "Should timeout before max retries"

    def test_retry_callback(self):
        """Test retry callback invocation"""
        callback_calls = []

        def retry_callback(attempt, error):
            callback_calls.append((attempt, str(error)))

        retry_policy = RetryPolicy(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            base_delay=0.1,
            on_retry=retry_callback
        )

        call_count = [0]

        def failing_operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return "success"

        result = retry_policy.execute(failing_operation)

        assert result == "success", "Operation should succeed"
        assert len(callback_calls) == 2, "Callback should be called for each retry"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
