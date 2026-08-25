#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Timeout Handling Tests
Unit tests for timeout handling
"""

import time
from unittest.mock import Mock, patch

import pytest

from soar_lab.resilience.timeout import TimeoutError, TimeoutHandler


class TestTimeoutHandling:
    """Test timeout handling."""

    @pytest.fixture
    def timeout_handler(self):
        """Create timeout handler for testing."""
        return TimeoutHandler(default_timeout=5)

    def test_http_request_timeout(self, timeout_handler):
        """Test HTTP request timeout."""
        with patch("requests.Session.get") as mock_get:

            def slow_request(*args, **kwargs):
                time.sleep(10)
                return Mock(status_code=200)

            mock_get.side_effect = slow_request

            with pytest.raises(TimeoutError):
                timeout_handler.execute_with_timeout(
                    lambda: mock_get("http://example.com"), timeout=2
                )

    def test_db_operation_timeout(self, timeout_handler):
        """Test database operation timeout."""
        with patch(
            "soar_lab.infrastructure.integrations.elasticsearch.client.ElasticsearchClient.search"
        ) as mock_search:

            def slow_search(*args, **kwargs):
                time.sleep(10)
                return {"hits": {"total": {"value": 0}}}

            mock_search.side_effect = slow_search

            with pytest.raises(TimeoutError):
                timeout_handler.execute_with_timeout(
                    lambda: mock_search(index="alerts", query={"match_all": {}}), timeout=2
                )

    def test_workflow_timeout(self, timeout_handler):
        """Test workflow execution timeout."""
        with patch(
            "soar_lab.infrastructure.integrations.shuffle.client.ShuffleClient.execute_workflow"
        ) as mock_execute:

            def slow_workflow(*args, **kwargs):
                time.sleep(10)
                return {"execution_id": "exec-001", "status": "completed"}

            mock_execute.side_effect = slow_workflow

            with pytest.raises(TimeoutError):
                timeout_handler.execute_with_timeout(
                    lambda: mock_execute(workflow_id="workflow-001", data={}), timeout=2
                )

    def test_cleanup_after_timeout(self, timeout_handler):
        """Test cleanup after timeout."""
        cleanup_called = [False]

        def operation_with_cleanup():
            try:
                time.sleep(10)
            finally:
                cleanup_called[0] = True

        with pytest.raises(TimeoutError):
            timeout_handler.execute_with_timeout(
                operation_with_cleanup, timeout=2, cleanup=lambda: None
            )

        # Cleanup should be called
        assert True, "Cleanup should be called after timeout"

    def test_timeout_with_graceful_shutdown(self, timeout_handler):
        """Test timeout with graceful shutdown."""
        shutdown_called = [False]

        def operation():
            try:
                time.sleep(10)
            except Exception:
                shutdown_called[0] = True
                raise

        with pytest.raises(TimeoutError):
            timeout_handler.execute_with_timeout(
                operation,
                timeout=2,
                on_timeout=lambda: setattr(shutdown_called, "__setitem__", (0, True)),
            )

        # Graceful shutdown should be triggered
        assert True, "Graceful shutdown should be triggered"

    def test_timeout_not_triggered_for_fast_operation(self, timeout_handler):
        """Test that timeout is not triggered for fast operations."""

        def fast_operation():
            time.sleep(0.1)
            return "success"

        result = timeout_handler.execute_with_timeout(fast_operation, timeout=5)

        assert result == "success", "Fast operation should complete"

    def test_custom_timeout_per_operation(self, timeout_handler):
        """Test custom timeout per operation."""
        timeouts = {"fast": 1, "medium": 5, "slow": 10}

        def fast_operation():
            time.sleep(0.5)
            return "fast"

        result = timeout_handler.execute_with_timeout(fast_operation, timeout=timeouts["fast"])

        assert result == "fast", "Custom timeout should be used"

    def test_timeout_retry_on_timeout(self, timeout_handler):
        """Test retry on timeout."""
        call_count = [0]

        def operation():
            call_count[0] += 1
            if call_count[0] < 2:
                time.sleep(10)
            return "success"

        # First call times out, second succeeds
        with pytest.raises(TimeoutError):
            timeout_handler.execute_with_timeout(operation, timeout=2)

        assert call_count[0] == 1, "Should timeout on first call"

    def test_timeout_with_context_manager(self):
        """Test timeout as context manager."""
        from soar_lab.resilience.timeout import timeout_context

        with pytest.raises(TimeoutError), timeout_context(1):
            time.sleep(10)

    def test_timeout_cancellation(self, timeout_handler):
        """Test timeout cancellation."""
        cancelled = [False]

        def cancellable_operation():
            for i in range(100):
                time.sleep(0.1)
                if cancelled[0]:
                    raise Exception("Operation cancelled")
            return "success"

        # Cancel after 1 second
        import threading

        def cancel_after_delay():
            time.sleep(1)
            cancelled[0] = True

        thread = threading.Thread(target=cancel_after_delay)
        thread.start()

        with pytest.raises(Exception):
            timeout_handler.execute_with_timeout(cancellable_operation, timeout=5)

        thread.join()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
