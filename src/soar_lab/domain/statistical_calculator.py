"""Statistical Calculator - Pure domain logic for statistical metrics.

This module contains pure statistical calculations without any infrastructure dependencies,
following the Single Responsibility Principle and hexagonal architecture.
"""

import math
import statistics
from datetime import datetime
from typing import List, Dict, Any


class StatisticalCalculator:
    """Pure domain logic for statistical calculations."""

    @staticmethod
    def calculate_statistical_metrics(execution_times: List[float]) -> Dict[str, Any]:
        """
        Calculate statistical metrics from execution times.

        Args:
            execution_times: List of execution times in seconds

        Returns:
            Dict with statistical metrics including mean, median, p50, p90, std_dev, etc.
        """
        if not execution_times:
            return {
                'total_executions': 0,
                'mean': 0.0,
                'median': 0.0,
                'p50': 0.0,
                'p90': 0.0,
                'min': 0.0,
                'max': 0.0,
                'std_dev': 0.0,
                'mttr_seconds': 0.0,
                'mttr_minutes': 0.0
            }

        # Filter out invalid times
        valid_times = [t for t in execution_times if 0 < t < 3600]  # Max 1 hour per execution

        if not valid_times:
            return StatisticalCalculator.calculate_statistical_metrics([])

        # Calculate statistical metrics
        mean_time = statistics.mean(valid_times)
        median_time = statistics.median(valid_times)

        # Calculate percentiles
        sorted_times = sorted(valid_times)
        n = len(sorted_times)

        # p50: median
        p50 = statistics.median(sorted_times)

        # p90: nearest-rank method
        p90_idx = min(math.ceil(n * 0.9) - 1, n - 1)
        if p90_idx < 0:
            p90_idx = 0
        p90 = sorted_times[p90_idx]

        # Standard deviation
        std_dev = statistics.stdev(valid_times) if len(valid_times) > 1 else 0.0

        return {
            'total_executions': len(valid_times),
            'mean': round(mean_time, 2),
            'median': round(median_time, 2),
            'p50': round(p50, 2),
            'p90': round(p90, 2),
            'min': round(min(valid_times), 2),
            'max': round(max(valid_times), 2),
            'std_dev': round(std_dev, 2),
            'mttr_seconds': round(mean_time, 2),
            'mttr_minutes': round(mean_time / 60, 2)
        }

    @staticmethod
    def calculate_health_score(
            cpu_percent: float,
            memory_percent: float,
            disk_percent: float,
            test_coverage: float
    ) -> Dict[str, Any]:
        """
        Calculate overall system health score based on various metrics.

        Args:
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            disk_percent: Disk usage percentage
            test_coverage: Test coverage percentage

        Returns:
            Dict with health score and components
        """
        # Calculate individual scores (0-100)
        cpu_score = max(0, 100 - cpu_percent)  # Lower CPU is better
        memory_score = max(0, 100 - memory_percent)  # Lower memory is better
        disk_score = max(0, 100 - disk_percent)  # Lower disk is better

        # Overall health score (weighted average)
        overall_score = round((cpu_score * 0.3 + memory_score * 0.3 + disk_score * 0.2 + test_coverage * 0.2), 2)

        # Determine health status
        if overall_score >= 80:
            status = "excellent"
        elif overall_score >= 60:
            status = "good"
        elif overall_score >= 40:
            status = "warning"
        else:
            status = "critical"

        return {
            "overall_score": overall_score,
            "status": status,
            "components": {
                "cpu": round(cpu_score, 2),
                "memory": round(memory_score, 2),
                "disk": round(disk_score, 2),
                "tests": round(test_coverage, 2)
            }
        }

    @staticmethod
    def calculate_execution_times(alert_steps: Dict[str, List[datetime]]) -> List[float]:
        """
        Calculate execution times from alert steps.

        Args:
            alert_steps: Dict mapping step names to list of timestamps

        Returns:
            List of execution times in seconds
        """
        alert_times = alert_steps.get('Alert received', [])
        containment_times = alert_steps.get('Containment executed', [])

        if alert_times and containment_times:
            # Pair up alerts with their corresponding containment actions
            min_pairs = min(len(alert_times), len(containment_times))
            execution_times = []
            for i in range(min_pairs):
                try:
                    delta = (containment_times[i] - alert_times[i]).total_seconds()
                    if delta > 0:
                        execution_times.append(delta)
                except Exception:
                    continue
            return execution_times

        # Fallback: use actual notify.log format where steps have description strings
        # Step 1 key variants (first step = alert sent)
        step1_keys = [k for k in alert_steps if 'Sending' in k or 'STEP 1' in k or 'alert' in k.lower()]
        # STARTED/PASSED pairs
        started_keys = [k for k in alert_steps if 'STARTED' in k]
        passed_keys = [k for k in alert_steps if 'PASSED' in k or 'FAILED' in k]

        if started_keys and passed_keys:
            starts = sorted([ts for k in started_keys for ts in alert_steps[k]])
            ends = sorted([ts for k in passed_keys for ts in alert_steps[k]])
            min_pairs = min(len(starts), len(ends))
            return [
                (ends[i] - starts[i]).total_seconds()
                for i in range(min_pairs)
                if (ends[i] - starts[i]).total_seconds() > 0
            ]

        # Last fallback: consecutive Step 1 timestamps give inter-arrival time (approximation)
        if step1_keys:
            all_ts = sorted([ts for k in step1_keys for ts in alert_steps[k]])
            return [
                (all_ts[i + 1] - all_ts[i]).total_seconds()
                for i in range(len(all_ts) - 1)
                if 0 < (all_ts[i + 1] - all_ts[i]).total_seconds() < 3600
            ]

        return []
