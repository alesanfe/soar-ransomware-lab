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

    @staticmethod
    def calculate_kpis_by_alert_type(metrics_data: List[Dict[str, Any]], hours: int = 24) -> Dict[str, Any]:
        """
        Calculate KPIs separated by alert type.

        Args:
            metrics_data: List of metric documents from Elasticsearch
            hours: Time period in hours

        Returns:
            Dict with KPIs by alert type
        """
        # Group by alert type
        kpis_by_type = {}
        for metric in metrics_data:
            alert_type = metric.get("alert_type", "unknown")
            mttr_field = metric.get("mttr_seconds", 0)
            severity = metric.get("severity", 0)

            # Extract MTTR value from dictionary if needed
            mttr = 0
            if isinstance(mttr_field, dict):
                mttr_str = mttr_field.get("message", "")
                if "MTTR:" in mttr_str:
                    try:
                        mttr = float(mttr_str.split("MTTR:")[1].split("s")[0].strip())
                    except (ValueError, IndexError):
                        mttr = 0
            elif isinstance(mttr_field, (int, float)):
                mttr = mttr_field

            if alert_type not in kpis_by_type:
                kpis_by_type[alert_type] = {
                    "count": 0,
                    "mttr_values": [],
                    "severity_sum": 0,
                    "critical_count": 0
                }

            kpis_by_type[alert_type]["count"] += 1
            if mttr:
                kpis_by_type[alert_type]["mttr_values"].append(mttr)
            kpis_by_type[alert_type]["severity_sum"] += severity
            if severity == 3:
                kpis_by_type[alert_type]["critical_count"] += 1

        # Calculate statistics for each type
        result = {
            "period_hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "by_alert_type": {}
        }

        for alert_type, data in kpis_by_type.items():
            mttr_values = data["mttr_values"]
            avg_mttr = sum(mttr_values) / len(mttr_values) if mttr_values else 0
            avg_severity = data["severity_sum"] / data["count"] if data["count"] > 0 else 0

            result["by_alert_type"][alert_type] = {
                "count": data["count"],
                "avg_mttr_seconds": round(avg_mttr, 2),
                "avg_severity": round(avg_severity, 2),
                "critical_count": data["critical_count"],
                "critical_rate": round(data["critical_count"] / data["count"] * 100, 2) if data["count"] > 0 else 0
            }

        return result

    @staticmethod
    def calculate_service_integration_kpis(metrics_data: List[Dict[str, Any]], hours: int = 24) -> Dict[str, Any]:
        """
        Calculate KPIs for service integrations (TheHive, Cortex, MISP, ES, Wazuh).

        Args:
            metrics_data: List of metric documents from Elasticsearch
            hours: Time period in hours

        Returns:
            Dict with service integration KPIs
        """
        # Track service success/failure
        services = {
            "thehive": {"success": 0, "failure": 0},
            "cortex": {"success": 0, "failure": 0},
            "misp": {"success": 0, "failure": 0},
            "elasticsearch": {"success": 0, "failure": 0},
            "wazuh": {"success": 0, "failure": 0}
        }

        for metric in metrics_data:
            # Check TheHive (case_id indicates success)
            thehive_case_id = metric.get("thehive_case_id")
            if thehive_case_id and (isinstance(thehive_case_id, str) or (
                isinstance(thehive_case_id, dict) and thehive_case_id.get("success"))):
                services["thehive"]["success"] += 1
            else:
                services["thehive"]["failure"] += 1

            # Check Cortex (job IDs indicate success)
            cortex_hash_job = metric.get("cortex_hash_job")
            cortex_ip_job = metric.get("cortex_ip_job")
            if (cortex_hash_job and (isinstance(cortex_hash_job, str) or (
                isinstance(cortex_hash_job, dict) and cortex_hash_job.get("success")))) or \
                (cortex_ip_job and (isinstance(cortex_ip_job, str) or (
                    isinstance(cortex_ip_job, dict) and cortex_ip_job.get("success")))):
                services["cortex"]["success"] += 1
            else:
                services["cortex"]["failure"] += 1

            # Check MISP (results indicate success)
            misp_results = metric.get("misp_results")
            if misp_results and (
                isinstance(misp_results, str) or (isinstance(misp_results, dict) and misp_results.get("success"))):
                services["misp"]["success"] += 1
            else:
                services["misp"]["failure"] += 1

            # Elasticsearch is always successful if metric is indexed
            services["elasticsearch"]["success"] += 1

            # Wazuh is checked via workflow execution
            if metric.get("metric_type") == "workflow_execution":
                services["wazuh"]["success"] += 1

        # Calculate success rates
        result = {
            "period_hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {}
        }

        for service, data in services.items():
            total = data["success"] + data["failure"]
            success_rate = (data["success"] / total * 100) if total > 0 else 0
            result["services"][service] = {
                "success_count": data["success"],
                "failure_count": data["failure"],
                "total": total,
                "success_rate_percent": round(success_rate, 2)
            }

        return result
