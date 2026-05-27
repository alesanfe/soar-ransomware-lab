"""KPI Analyzer - Pure calculation logic for KPI metrics.

This module contains the KPIAnalyzer class which is responsible for
calculating KPI metrics from raw data. It depends only on domain ports
and contains no orchestration or I/O logic.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from soar_lab.domain.ports import StatisticalCalculatorInterface


class KPIAnalyzer:
    """Pure calculation logic for KPI metrics.

    This class contains no I/O or orchestration logic - it only calculates
    metrics from provided data. This makes it easy to test and reuse.
    """

    def __init__(self, statistical_calculator: StatisticalCalculatorInterface):
        """
        Initialize KPIAnalyzer with injected StatisticalCalculator.

        Args:
            statistical_calculator: StatisticalCalculatorInterface instance (required)
        """
        if not statistical_calculator:
            raise ValueError("statistical_calculator is required for KPIAnalyzer")
        self._statistical_calculator = statistical_calculator

    @staticmethod
    def calculate_performance_kpis(test_results: List[Dict[str, Any]], hours: int = 24) -> Dict[str, Any]:
        """
        Calculate performance KPIs from test results.
        
        Args:
            test_results: List of test result dictionaries
            hours: Time period in hours for KPI calculation
            
        Returns:
            Dict with performance KPIs
        """
        total_tests = len(test_results)
        passed_tests = sum(1 for t in test_results if t.get('status') == 'passed')

        # Calculate test success rate
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Calculate average coverage
        avg_coverage = sum(
            t.get('coverage_percent', 0) for t in test_results) / total_tests if total_tests > 0 else 0

        # Calculate average duration
        avg_duration = sum(
            t.get('duration_seconds', 0) for t in test_results) / total_tests if total_tests > 0 else 0

        return {
            "period_hours": hours,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": round(success_rate, 2),
            "average_coverage": round(avg_coverage, 2),
            "average_duration_seconds": round(avg_duration, 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def calculate_health_score(
            self,
            cpu_percent: float,
            memory_percent: float,
            disk_percent: float,
            test_coverage: float
    ) -> Dict[str, Any]:
        """
        Calculate overall system health score from component metrics.

        Args:
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            disk_percent: Disk usage percentage
            test_coverage: Test coverage percentage

        Returns:
            Dict with health score and components
        """
        health_score = self._statistical_calculator.calculate_health_score(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            test_coverage=test_coverage
        )
        health_score["timestamp"] = datetime.now(timezone.utc).isoformat()
        return health_score

    def calculate_mttr_metrics(self, execution_times: List[float]) -> Dict[str, Any]:
        """
        Calculate MTTR (Mean Time To Respond) metrics from execution times.

        Args:
            execution_times: List of execution time values in seconds

        Returns:
            Dict with MTTR metrics including p50, p90, mean, etc.
        """
        return self._statistical_calculator.calculate_statistical_metrics(execution_times)

    @staticmethod
    def calculate_comprehensive_kpis(
            mttr_metrics: Dict[str, Any],
            performance_kpis: Dict[str, Any],
            health_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combine all KPI metrics into a comprehensive report.

        Args:
            mttr_metrics: MTTR metrics from calculate_mttr_metrics
            performance_kpis: Performance KPIs from calculate_performance_kpis
            health_score: Health score from calculate_health_score

        Returns:
            Dict with comprehensive KPIs
        """
        return {
            "mttr": mttr_metrics,
            "performance": performance_kpis,
            "health": health_score,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
