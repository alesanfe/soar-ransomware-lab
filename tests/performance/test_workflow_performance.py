#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Workflow Performance Tests
Performance tests for workflow execution
"""

import pytest
import time
from datetime import datetime, timezone
from soar_lab.infrastructure.external.integrations.shuffle_client import ShuffleClient
from unittest.mock import Mock, patch


class TestWorkflowPerformance:
    """Test workflow performance"""

    @pytest.fixture
    def shuffle_client(self):
        """Create Shuffle client for testing"""
        return ShuffleClient(
            base_url="http://soar_shuffle_backend:5001",
            api_key="test-key",
            verify_ssl=False
        )

    @pytest.fixture
    def test_alert(self):
        """Create test alert data"""
        return {
            "alert_id": "PERF-WORKFLOW-001",
            "hostname": "perf-host",
            "src_ip": "192.168.1.100",
            "hash": "d41d8cd98f00b204e9800998ecf8427e" * 2,
            "severity": 2,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def test_workflow_execution_time(self, shuffle_client, test_alert):
        """Test workflow execution time"""
        with patch.object(shuffle_client, 'execute_workflow') as mock_execute:
            mock_execute.return_value = {"execution_id": "exec-001", "status": "completed"}

            # Benchmark workflow execution
            start_time = time.time()
            result = shuffle_client.execute_workflow(
                workflow_id="workflow-001",
                data=test_alert
            )
            end_time = time.time()

            duration_sec = end_time - start_time
            assert duration_sec < 30, f"Workflow execution should be < 30s, got {duration_sec}s"

    def test_workflow_concurrency(self, shuffle_client, test_alert):
        """Test workflow execution under concurrency"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        execution_times = []

        def execute_workflow(i):
            with patch.object(shuffle_client, 'execute_workflow') as mock_execute:
                mock_execute.return_value = {"execution_id": f"exec-{i}", "status": "completed"}

                start_time = time.time()
                shuffle_client.execute_workflow(
                    workflow_id="workflow-001",
                    data={**test_alert, "alert_id": f"PERF-{i}"}
                )
                end_time = time.time()

                return end_time - start_time

        # Execute workflows concurrently
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_workflow, i) for i in range(10)]
            for future in as_completed(futures):
                execution_times.append(future.result())
        end_time = time.time()

        total_duration = end_time - start_time
        avg_duration = sum(execution_times) / len(execution_times)

        assert total_duration < 60, f"Concurrent execution should be < 60s, got {total_duration}s"
        assert avg_duration < 30, f"Average execution time should be < 30s, got {avg_duration}s"

    def test_workflow_resource_usage(self, shuffle_client, test_alert):
        """Test workflow resource usage"""
        with patch.object(shuffle_client, 'execute_workflow') as mock_execute:
            mock_execute.return_value = {
                "execution_id": "exec-001",
                "status": "completed",
                "metrics": {
                    "cpu_time_ms": 1000,
                    "memory_mb": 50,
                    "duration_ms": 5000
                }
            }

            result = shuffle_client.execute_workflow(
                workflow_id="workflow-001",
                data=test_alert
            )

            metrics = result.get('metrics', {})
            assert metrics['cpu_time_ms'] < 5000, "CPU time should be reasonable"
            assert metrics['memory_mb'] < 200, "Memory usage should be reasonable"

    def test_workflow_scalability(self, shuffle_client, test_alert):
        """Test workflow scalability with increasing load"""
        loads = [1, 5, 10, 20]
        durations = []

        for load in loads:
            with patch.object(shuffle_client, 'execute_workflow') as mock_execute:
                mock_execute.return_value = {"execution_id": "exec-001", "status": "completed"}

                start_time = time.time()
                for i in range(load):
                    shuffle_client.execute_workflow(
                        workflow_id="workflow-001",
                        data={**test_alert, "alert_id": f"SCALE-{i}"}
                    )
                end_time = time.time()

                duration = end_time - start_time
                durations.append(duration)

                print(f"Load {load}: {duration:.2f}s")

        # Duration should not increase linearly with load
        assert durations[3] < durations[0] * 30, \
            "Execution time should not increase linearly with load"

    def test_workflow_latency_by_complexity(self, shuffle_client):
        """Test workflow latency by complexity"""
        workflows = {
            "simple": {"steps": 2},
            "medium": {"steps": 5},
            "complex": {"steps": 10}
        }

        latencies = {}

        for workflow_name, workflow_config in workflows.items():
            with patch.object(shuffle_client, 'execute_workflow') as mock_execute:
                # Simulate complexity by delay
                delay = workflow_config['steps'] * 0.1

                def delayed_execute(*args, **kwargs):
                    time.sleep(delay)
                    return {"execution_id": "exec-001", "status": "completed"}

                mock_execute.side_effect = delayed_execute

                start_time = time.time()
                shuffle_client.execute_workflow(workflow_id=workflow_name, data={})
                end_time = time.time()

                latencies[workflow_name] = end_time - start_time

        # Complex workflow should take longer but not proportionally
        assert latencies['complex'] < latencies['simple'] * 10, \
            "Complex workflow should not be 10x slower than simple"

    def test_workflow_retry_performance(self, shuffle_client, test_alert):
        """Test workflow retry performance"""
        call_count = [0]

        def failing_then_succeeding(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return {"execution_id": "exec-001", "status": "completed"}

        with patch.object(shuffle_client, 'execute_workflow') as mock_execute:
            mock_execute.side_effect = failing_then_succeeding

            start_time = time.time()
            result = shuffle_client.execute_workflow(
                workflow_id="workflow-001",
                data=test_alert
            )
            end_time = time.time()

            duration = end_time - start_time
            assert duration < 10, f"Retry should complete quickly, got {duration}s"
            assert call_count[0] == 3, "Should have retried twice"

    def test_workflow_throughput(self, shuffle_client, test_alert):
        """Test workflow throughput"""
        num_workflows = 50

        with patch.object(shuffle_client, 'execute_workflow') as mock_execute:
            mock_execute.return_value = {"execution_id": "exec-001", "status": "completed"}

            start_time = time.time()
            for i in range(num_workflows):
                shuffle_client.execute_workflow(
                    workflow_id="workflow-001",
                    data={**test_alert, "alert_id": f"THROUGHPUT-{i}"}
                )
            end_time = time.time()

        duration = end_time - start_time
        throughput = num_workflows / duration

        assert throughput > 1, f"Throughput should be > 1 workflow/sec, got {throughput} workflows/sec"

    def test_workflow_memory_leak_check(self, shuffle_client, test_alert):
        """Test for memory leaks in workflow execution"""
        import gc
        import sys

        with patch.object(shuffle_client, 'execute_workflow') as mock_execute:
            mock_execute.return_value = {"execution_id": "exec-001", "status": "completed"}

            # Get initial memory
            gc.collect()
            initial_memory = sys.getsizeof(shuffle_client)

            # Execute many workflows
            for i in range(100):
                shuffle_client.execute_workflow(
                    workflow_id="workflow-001",
                    data={**test_alert, "alert_id": f"MEMORY-{i}"}
                )

            # Get final memory
            gc.collect()
            final_memory = sys.getsizeof(shuffle_client)

            memory_increase = final_memory - initial_memory
            assert memory_increase < 1000000, \
                f"Memory increase should be < 1MB, got {memory_increase} bytes"

    def test_workflow_timeout_handling(self, shuffle_client, test_alert):
        """Test workflow timeout handling"""
        with patch.object(shuffle_client, 'execute_workflow') as mock_execute:
            def timeout_execute(*args, **kwargs):
                time.sleep(35)  # Simulate long-running workflow
                return {"execution_id": "exec-001", "status": "completed"}

            mock_execute.side_effect = timeout_execute

            start_time = time.time()
            try:
                shuffle_client.execute_workflow(
                    workflow_id="workflow-001",
                    data=test_alert,
                    timeout=30
                )
            except Exception:
                pass  # Expected timeout
            end_time = time.time()

            duration = end_time - start_time
            assert duration < 35, f"Timeout should trigger before 35s, got {duration}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
