"""KPI Analyzer - Pure calculation logic for KPI metrics.

This module contains the KPIAnalyzer class which is responsible for
calculating KPI metrics from raw data. It depends only on domain ports
and contains no orchestration or I/O logic.
"""

from datetime import UTC, datetime
from typing import Any

from soar_lab.domain.ports import StatisticalCalculatorInterface


class KPIAnalyzer:
    """Pure calculation logic for KPI metrics.

    This class contains no I/O or orchestration logic - it only calculates
    metrics from provided data. This makes it easy to test and reuse.
    """

    def __init__(self, statistical_calculator: StatisticalCalculatorInterface) -> None:
        """Initialize KPIAnalyzer with injected StatisticalCalculator.

        Args:
            statistical_calculator: StatisticalCalculatorInterface instance (required)
        """
        if not statistical_calculator:
            raise ValueError("statistical_calculator is required for KPIAnalyzer")
        self._statistical_calculator = statistical_calculator

    @staticmethod
    def calculate_performance_kpis(
        test_results: list[dict[str, Any]], hours: int = 24
    ) -> dict[str, Any]:
        """Calculate performance KPIs from test results.

        Args:
            test_results: List of test result dictionaries
            hours: Time period in hours for KPI calculation

        Returns:
            Dict with performance KPIs
        """
        total_tests = len(test_results)
        passed_tests = sum(1 for t in test_results if t.get("status") == "passed")

        # Calculate test success rate
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Calculate average coverage
        avg_coverage = (
            sum(t.get("coverage_percent", 0) for t in test_results) / total_tests
            if total_tests > 0
            else 0
        )

        # Calculate average duration
        avg_duration = (
            sum(t.get("duration_seconds", 0) for t in test_results) / total_tests
            if total_tests > 0
            else 0
        )

        return {
            "period_hours": hours,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": round(success_rate, 2),
            "average_coverage": round(avg_coverage, 2),
            "average_duration_seconds": round(avg_duration, 2),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def calculate_health_score(
        self, cpu_percent: float, memory_percent: float, disk_percent: float, test_coverage: float
    ) -> dict[str, Any]:
        """Calculate overall system health score from component metrics.

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
            test_coverage=test_coverage,
        )
        health_score["timestamp"] = datetime.now(UTC).isoformat()
        return health_score

    def calculate_mttr_metrics(self, execution_times: list[float]) -> dict[str, Any]:
        """Calculate MTTR (Mean Time To Respond) metrics from execution times.

        Args:
            execution_times: List of execution time values in seconds

        Returns:
            Dict with MTTR metrics including p50, p90, mean, etc.
        """
        return self._statistical_calculator.calculate_statistical_metrics(execution_times)

    @staticmethod
    def calculate_comprehensive_kpis(
        mttr_metrics: dict[str, Any], performance_kpis: dict[str, Any], health_score: dict[str, Any]
    ) -> dict[str, Any]:
        """Combine all KPI metrics into a comprehensive report.

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
            "timestamp": datetime.now(UTC).isoformat(),
        }

    @staticmethod
    def calculate_kpis_by_alert_type(
        metrics_data: list[dict[str, Any]], hours: int = 24
    ) -> dict[str, Any]:
        """Calculate KPIs separated by alert type.

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
                    "critical_count": 0,
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
            "timestamp": datetime.now(UTC).isoformat(),
            "by_alert_type": {},
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
                "critical_rate": (
                    round(data["critical_count"] / data["count"] * 100, 2)
                    if data["count"] > 0
                    else 0
                ),
            }

        return result

    @staticmethod
    def _check_service_success(value: Any) -> bool:
        """Return True if the value indicates a service success.

        A value indicates success if it is a non-empty string, or a dict
        with a truthy "success" key.

        Args:
            value: The value to check (string, dict, or other)

        Returns:
            True if the value indicates success, False otherwise
        """
        if isinstance(value, str):
            return True
        if isinstance(value, dict):
            return bool(value.get("success"))
        return False

    @staticmethod
    def _check_cortex_success(metric: dict[str, Any]) -> bool:
        """Check whether a metric indicates Cortex success.

        Cortex is considered successful if either the hash job or the IP job
        indicates success.

        Args:
            metric: A single metric document from Elasticsearch

        Returns:
            True if Cortex succeeded for this metric, False otherwise
        """
        cortex_hash_job = metric.get("cortex_hash_job")
        cortex_ip_job = metric.get("cortex_ip_job")
        if cortex_hash_job and KPIAnalyzer._check_service_success(cortex_hash_job):
            return True
        if cortex_ip_job and KPIAnalyzer._check_service_success(cortex_ip_job):
            return True
        return False

    @staticmethod
    def _classify_metric_services(metric: dict[str, Any]) -> dict[str, str]:
        """Classify each service as "success" or "failure" for a single metric.

        Args:
            metric: A single metric document from Elasticsearch

        Returns:
            Dict mapping each service name to either "success" or "failure"
        """
        classification: dict[str, str] = {}

        # Check TheHive (case_id indicates success)
        thehive_case_id = metric.get("thehive_case_id")
        if thehive_case_id and KPIAnalyzer._check_service_success(thehive_case_id):
            classification["thehive"] = "success"
        else:
            classification["thehive"] = "failure"

        # Check Cortex (job IDs indicate success)
        if KPIAnalyzer._check_cortex_success(metric):
            classification["cortex"] = "success"
        else:
            classification["cortex"] = "failure"

        # Check MISP (results indicate success)
        misp_results = metric.get("misp_results")
        if misp_results and KPIAnalyzer._check_service_success(misp_results):
            classification["misp"] = "success"
        else:
            classification["misp"] = "failure"

        # Elasticsearch is always successful if metric is indexed
        classification["elasticsearch"] = "success"

        return classification

    @staticmethod
    def calculate_service_integration_kpis(
        metrics_data: list[dict[str, Any]], hours: int = 24
    ) -> dict[str, Any]:
        """Calculate KPIs for service integrations (TheHive, Cortex, MISP, ES).

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
        }

        for metric in metrics_data:
            classification = KPIAnalyzer._classify_metric_services(metric)
            for service, status in classification.items():
                services[service][status] += 1

        # Calculate success rates
        result = {
            "period_hours": hours,
            "timestamp": datetime.now(UTC).isoformat(),
            "services": {},
        }

        for service, data in services.items():
            total = data["success"] + data["failure"]
            success_rate = (data["success"] / total * 100) if total > 0 else 0
            result["services"][service] = {
                "success_count": data["success"],
                "failure_count": data["failure"],
                "total": total,
                "success_rate_percent": round(success_rate, 2),
            }

        return result
