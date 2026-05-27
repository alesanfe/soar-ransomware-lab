"""Analytics Service for SOAR Lab - Centralized KPI and Metrics Management"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from soar_lab.config.logging import get_logger
from soar_lab.domain.ports import (
    AlertRepository, SystemMetricsInterface, FileSystemInterface,
    LogReader, LogParser, KPIFormatter, StatisticalCalculatorInterface
)

logger = get_logger(__name__)


class AnalyticsService:
    """Service for analytics, KPIs, and system metrics"""

    def __init__(self, data_repository: AlertRepository, system_metrics: SystemMetricsInterface,
                 file_system: FileSystemInterface, log_reader: Optional[LogReader] = None,
                 log_parser: LogParser = None, kpi_formatter: KPIFormatter = None,
                 statistical_calculator: StatisticalCalculatorInterface = None,
                 kpi_analyzer=None):
        """
        Initialize analytics service with injected dependencies.

        Args:
            data_repository: Repository for accessing application data
            system_metrics: System metrics provider (injected dependency)
            file_system: File system provider (injected dependency)
            log_reader: Log reader provider (injected dependency for reading log files)
            log_parser: Log parser provider (injected dependency for parsing logs) - REQUIRED
            kpi_formatter: KPI formatter provider (injected dependency for formatting metrics) - REQUIRED
            statistical_calculator: Statistical calculator provider (injected dependency) - REQUIRED
            kpi_analyzer: KPI analyzer provider (injected dependency) - REQUIRED
        """
        self.data_repository = data_repository
        self.system_metrics = system_metrics
        self.file_system = file_system
        self.log_reader = log_reader
        if not log_parser:
            raise ValueError("log_parser is required for AnalyticsService")
        self.log_parser = log_parser
        if not kpi_formatter:
            raise ValueError("kpi_formatter is required for AnalyticsService")
        self.kpi_formatter = kpi_formatter
        if not statistical_calculator:
            raise ValueError("statistical_calculator is required for AnalyticsService")
        self.statistical_calculator = statistical_calculator
        if not kpi_analyzer:
            raise ValueError("kpi_analyzer is required for AnalyticsService")
        self.kpi_analyzer = kpi_analyzer

    def get_comprehensive_system_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics combining application and hardware metrics.
        
        Returns:
            Dict with complete system statistics
        """
        try:
            # Get application data stats
            app_stats = self._get_application_stats()

            # Get hardware metrics
            hw_stats = self.system_metrics.get_hardware_metrics()

            # Get process metrics
            proc_stats = self.system_metrics.get_process_metrics()

            return {
                "application": app_stats,
                "hardware": hw_stats,
                "process": proc_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting comprehensive system stats: {e}")
            raise

    def _get_application_stats(self) -> Dict[str, Any]:
        """
        Get application-specific statistics from data repository.
        
        Returns:
            Dict with application statistics
        """
        try:
            # Alert stats
            total_alerts = self.data_repository.count_alerts()
            new_alerts = self.data_repository.count_alerts_by_status("new")

            # Case stats
            total_cases = self.data_repository.count_cases()
            open_cases = self.data_repository.count_cases_by_status("open")

            # Backup stats
            completed_backups = self.data_repository.count_backups_by_status("completed")

            # Test stats
            avg_coverage = self.data_repository.get_average_test_coverage(hours=24)

            return {
                "alerts": {
                    "total": total_alerts,
                    "new": new_alerts
                },
                "cases": {
                    "total": total_cases,
                    "open": open_cases
                },
                "backups": {
                    "completed": completed_backups
                },
                "tests": {
                    "avg_coverage_24h": round(avg_coverage, 2) if avg_coverage else 0
                }
            }
        except Exception as e:
            logger.error(f"Error getting application stats: {e}")
            raise

    def get_performance_kpis(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance KPIs for the specified time period.

        Args:
            hours: Time period in hours for KPI calculation

        Returns:
            Dict with performance KPIs
        """
        try:
            # Get test results for KPI calculation (orchestration)
            test_results = self.data_repository.get_test_results(hours=hours)

            # Delegate calculation to KPIAnalyzer (pure calculation)
            return self.kpi_analyzer.calculate_performance_kpis(test_results, hours)
        except Exception as e:
            logger.error(f"Error calculating performance KPIs: {e}")
            raise

    def get_health_score(self) -> Dict[str, Any]:
        """
        Calculate overall system health score based on various metrics.

        Returns:
            Dict with health score and components
        """
        try:
            # Get hardware metrics (orchestration)
            hw_metrics = self.system_metrics.get_hardware_metrics()

            # Get application stats (orchestration)
            app_stats = self._get_application_stats()

            # Delegate calculation to KPIAnalyzer (pure calculation)
            return self.kpi_analyzer.calculate_health_score(
                cpu_percent=hw_metrics["cpu"],
                memory_percent=hw_metrics["memory"],
                disk_percent=hw_metrics["disk"],
                test_coverage=app_stats["tests"]["avg_coverage_24h"]
            )
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            raise

    # MTTR and KPI Calculation Methods (Consolidated from calc_kpis.py)
    def parse_execution_logs(self, log_file_path: str) -> Dict[str, List[datetime]]:
        """
        Parse execution logs to extract timestamps for MTTR calculation.

        Args:
            log_file_path: Path to execution log file

        Returns:
            Dict mapping step names to list of timestamps
        """
        try:
            log_content = self.file_system.read_file(log_file_path)
            return self.log_parser.parse(log_content)
        except Exception as e:
            logger.error(f"Error parsing execution logs: {e}")
            raise

    def calculate_mttr_metrics(self, log_file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate MTTR (Mean Time To Respond) metrics from execution logs.

        Args:
            log_file_path: Path to execution log file (optional, uses default if not provided)

        Returns:
            Dict with MTTR metrics including p50, p90, mean, etc.
        """
        try:
            # Use default log path from log_reader if not provided (orchestration)
            if not log_file_path:
                if self.log_reader and hasattr(self.log_reader, 'get_default_log_path'):
                    log_file_path = self.log_reader.get_default_log_path()
                else:
                    raise ValueError("log_file_path is required when log_reader does not provide default path")

            # Parse log file (orchestration)
            alert_steps = self.parse_execution_logs(log_file_path)

            # Calculate execution times using injected StatisticalCalculator (orchestration)
            execution_times = self.statistical_calculator.calculate_execution_times(alert_steps)

            # Delegate calculation to KPIAnalyzer (pure calculation)
            return self.kpi_analyzer.calculate_mttr_metrics(execution_times)

        except Exception as e:
            logger.error(f"Error calculating MTTR metrics: {e}")
            raise

    def save_kpis_to_csv(self, metrics: Dict[str, Any], output_path: Optional[str] = None) -> None:
        """
        Save KPI metrics to CSV file.

        Args:
            metrics: KPI metrics dictionary
            output_path: Output file path (optional, uses default if not provided)
        """
        try:
            # Use default path if not provided
            if not output_path:
                output_path = "kpis.csv"  # Simple filename, let storage provider handle full path

            # Ensure directory exists using injected file system
            self.file_system.ensure_directory_exists(output_path)

            # Generate CSV content using injected formatter
            csv_content = self.kpi_formatter.format_csv(metrics)

            # Write file using injected file system
            self.file_system.write_file(output_path, csv_content)

            logger.info(f"KPIs saved to {output_path}")

        except Exception as e:
            logger.error(f"Error saving KPIs to CSV: {e}")
            raise

    def get_comprehensive_kpis(self, log_file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive KPIs including MTTR, performance, and health metrics.

        Args:
            log_file_path: Path to execution log file (optional)

        Returns:
            Dict with comprehensive KPIs
        """
        try:
            # Get MTTR metrics (orchestration)
            mttr_metrics = self.calculate_mttr_metrics(log_file_path)

            # Get performance KPIs (orchestration)
            performance_kpis = self.get_performance_kpis()

            # Get health score (orchestration)
            health_score = self.get_health_score()

            # Delegate combination to KPIAnalyzer (pure calculation)
            return self.kpi_analyzer.calculate_comprehensive_kpis(
                mttr_metrics=mttr_metrics,
                performance_kpis=performance_kpis,
                health_score=health_score
            )

        except Exception as e:
            logger.error(f"Error getting comprehensive KPIs: {e}")
            raise
