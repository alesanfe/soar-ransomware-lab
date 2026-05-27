#!/usr/bin/env python3
"""
Unit tests for analytics_service.py
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from soar_lab.services.analytics_service import AnalyticsService


class TestAnalyticsService:
    """Test AnalyticsService"""

    def test_initialization_success(self):
        """Test successful initialization with all dependencies"""
        mock_repo = Mock()
        mock_metrics = Mock()
        mock_fs = Mock()
        mock_log_parser = Mock()
        mock_kpi_formatter = Mock()
        mock_stat_calc = Mock()
        mock_kpi_analyzer = Mock()
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        assert service.data_repository == mock_repo
        assert service.system_metrics == mock_metrics
        assert service.file_system == mock_fs
        assert service.log_parser == mock_log_parser
        assert service.kpi_formatter == mock_kpi_formatter
        assert service.statistical_calculator == mock_stat_calc
        assert service.kpi_analyzer == mock_kpi_analyzer

    def test_requires_log_parser(self):
        """Test that log_parser is required"""
        with pytest.raises(ValueError, match="log_parser is required"):
            AnalyticsService(
                data_repository=Mock(),
                system_metrics=Mock(),
                file_system=Mock(),
                log_parser=None
            )

    def test_requires_kpi_formatter(self):
        """Test that kpi_formatter is required"""
        with pytest.raises(ValueError, match="kpi_formatter is required"):
            AnalyticsService(
                data_repository=Mock(),
                system_metrics=Mock(),
                file_system=Mock(),
                log_parser=Mock(),
                kpi_formatter=None
            )

    def test_requires_statistical_calculator(self):
        """Test that statistical_calculator is required"""
        with pytest.raises(ValueError, match="statistical_calculator is required"):
            AnalyticsService(
                data_repository=Mock(),
                system_metrics=Mock(),
                file_system=Mock(),
                log_parser=Mock(),
                kpi_formatter=Mock(),
                statistical_calculator=None
            )

    def test_requires_kpi_analyzer(self):
        """Test that kpi_analyzer is required"""
        with pytest.raises(ValueError, match="kpi_analyzer is required"):
            AnalyticsService(
                data_repository=Mock(),
                system_metrics=Mock(),
                file_system=Mock(),
                log_parser=Mock(),
                kpi_formatter=Mock(),
                statistical_calculator=Mock(),
                kpi_analyzer=None
            )

    def test_get_comprehensive_system_stats(self):
        """Test getting comprehensive system stats"""
        mock_repo = Mock()
        mock_repo.count_alerts.return_value = 10
        mock_repo.count_alerts_by_status.return_value = 5
        mock_repo.count_cases.return_value = 3
        mock_repo.count_cases_by_status.return_value = 2
        mock_repo.count_backups_by_status.return_value = 1
        mock_repo.get_average_test_coverage.return_value = 85.5
        
        mock_metrics = Mock()
        mock_metrics.get_hardware_metrics.return_value = {"cpu": 50, "memory": 60, "disk": 70}
        mock_metrics.get_process_metrics.return_value = {"processes": 100}
        
        mock_fs = Mock()
        mock_log_parser = Mock()
        mock_kpi_formatter = Mock()
        mock_stat_calc = Mock()
        mock_kpi_analyzer = Mock()
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        result = service.get_comprehensive_system_stats()
        
        assert "application" in result
        assert "hardware" in result
        assert "process" in result
        assert "timestamp" in result
        assert result["hardware"] == {"cpu": 50, "memory": 60, "disk": 70}

    def test_get_application_stats(self):
        """Test getting application stats"""
        mock_repo = Mock()
        mock_repo.count_alerts.return_value = 10
        mock_repo.count_alerts_by_status.return_value = 5
        mock_repo.count_cases.return_value = 3
        mock_repo.count_cases_by_status.return_value = 2
        mock_repo.count_backups_by_status.return_value = 1
        mock_repo.get_average_test_coverage.return_value = 85.5
        
        mock_metrics = Mock()
        mock_fs = Mock()
        mock_log_parser = Mock()
        mock_kpi_formatter = Mock()
        mock_stat_calc = Mock()
        mock_kpi_analyzer = Mock()
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        result = service._get_application_stats()
        
        assert result["alerts"]["total"] == 10
        assert result["alerts"]["new"] == 5
        assert result["cases"]["total"] == 3
        assert result["cases"]["open"] == 2
        assert result["backups"]["completed"] == 1
        assert result["tests"]["avg_coverage_24h"] == 85.5

    def test_get_performance_kpis(self):
        """Test getting performance KPIs"""
        mock_repo = Mock()
        mock_repo.get_test_results.return_value = {"passed": 10, "failed": 2}
        
        mock_metrics = Mock()
        mock_fs = Mock()
        mock_log_parser = Mock()
        mock_kpi_formatter = Mock()
        mock_stat_calc = Mock()
        mock_kpi_analyzer = Mock()
        mock_kpi_analyzer.calculate_performance_kpis.return_value = {"mttr": 120}
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        result = service.get_performance_kpis(hours=24)
        
        assert result == {"mttr": 120}
        mock_kpi_analyzer.calculate_performance_kpis.assert_called_once()

    def test_get_health_score(self):
        """Test getting health score"""
        mock_repo = Mock()
        mock_repo.count_alerts.return_value = 10
        mock_repo.count_alerts_by_status.return_value = 5
        mock_repo.count_cases.return_value = 3
        mock_repo.count_cases_by_status.return_value = 2
        mock_repo.count_backups_by_status.return_value = 1
        mock_repo.get_average_test_coverage.return_value = 85.5
        
        mock_metrics = Mock()
        mock_metrics.get_hardware_metrics.return_value = {"cpu": 50, "memory": 60, "disk": 70}
        
        mock_fs = Mock()
        mock_log_parser = Mock()
        mock_kpi_formatter = Mock()
        mock_stat_calc = Mock()
        mock_kpi_analyzer = Mock()
        mock_kpi_analyzer.calculate_health_score.return_value = {"score": 90}
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        result = service.get_health_score()
        
        assert result == {"score": 90}
        mock_kpi_analyzer.calculate_health_score.assert_called_once()

    def test_parse_execution_logs(self):
        """Test parsing execution logs"""
        mock_repo = Mock()
        mock_metrics = Mock()
        mock_fs = Mock()
        mock_fs.read_file.return_value = "[2024-01-01 10:00:00] STEP: Alert received"
        
        mock_log_parser = Mock()
        mock_log_parser.parse.return_value = {"Alert received": [datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)]}
        
        mock_kpi_formatter = Mock()
        mock_stat_calc = Mock()
        mock_kpi_analyzer = Mock()
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        result = service.parse_execution_logs("/path/to/log.txt")
        
        assert "Alert received" in result
        mock_fs.read_file.assert_called_once_with("/path/to/log.txt")
        mock_log_parser.parse.assert_called_once()

    def test_calculate_mttr_metrics_with_log_file(self):
        """Test calculating MTTR metrics with log file path"""
        mock_repo = Mock()
        mock_metrics = Mock()
        mock_fs = Mock()
        mock_fs.read_file.return_value = "log content"
        
        mock_log_parser = Mock()
        mock_log_parser.parse.return_value = {"step1": [datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)]}
        
        mock_stat_calc = Mock()
        mock_stat_calc.calculate_execution_times.return_value = [120.5]
        
        mock_kpi_formatter = Mock()
        mock_kpi_analyzer = Mock()
        mock_kpi_analyzer.calculate_mttr_metrics.return_value = {"mean": 120.5}
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        result = service.calculate_mttr_metrics(log_file_path="/path/to/log.txt")
        
        assert result == {"mean": 120.5}

    def test_calculate_mttr_metrics_without_log_file_raises(self):
        """Test calculating MTTR metrics without log file raises error when no log_reader"""
        mock_repo = Mock()
        mock_metrics = Mock()
        mock_fs = Mock()
        mock_log_parser = Mock()
        mock_kpi_formatter = Mock()
        mock_stat_calc = Mock()
        mock_kpi_analyzer = Mock()
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        with pytest.raises(ValueError, match="log_file_path is required"):
            service.calculate_mttr_metrics()

    def test_calculate_mttr_metrics_with_log_reader(self):
        """Test calculating MTTR metrics with log_reader providing default path"""
        mock_repo = Mock()
        mock_metrics = Mock()
        mock_fs = Mock()
        mock_fs.read_file.return_value = "log content"
        
        mock_log_reader = Mock()
        mock_log_reader.get_default_log_path.return_value = "/default/log.txt"
        
        mock_log_parser = Mock()
        mock_log_parser.parse.return_value = {"step1": [datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)]}
        
        mock_stat_calc = Mock()
        mock_stat_calc.calculate_execution_times.return_value = [120.5]
        
        mock_kpi_formatter = Mock()
        mock_kpi_analyzer = Mock()
        mock_kpi_analyzer.calculate_mttr_metrics.return_value = {"mean": 120.5}
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_reader=mock_log_reader,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        result = service.calculate_mttr_metrics()
        
        assert result == {"mean": 120.5}
        mock_fs.read_file.assert_called_once_with("/default/log.txt")

    def test_save_kpis_to_csv(self):
        """Test saving KPIs to CSV"""
        mock_repo = Mock()
        mock_metrics = Mock()
        mock_fs = Mock()
        mock_log_parser = Mock()
        mock_kpi_formatter = Mock()
        mock_kpi_formatter.format_csv.return_value = "header\nvalue"
        mock_stat_calc = Mock()
        mock_kpi_analyzer = Mock()
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        metrics = {"mttr": 120.5}
        service.save_kpis_to_csv(metrics, output_path="/output/kpis.csv")
        
        mock_fs.ensure_directory_exists.assert_called_once_with("/output/kpis.csv")
        mock_kpi_formatter.format_csv.assert_called_once_with(metrics)
        mock_fs.write_file.assert_called_once_with("/output/kpis.csv", "header\nvalue")

    def test_save_kpis_to_csv_default_path(self):
        """Test saving KPIs to CSV with default path"""
        mock_repo = Mock()
        mock_metrics = Mock()
        mock_fs = Mock()
        mock_log_parser = Mock()
        mock_kpi_formatter = Mock()
        mock_kpi_formatter.format_csv.return_value = "header\nvalue"
        mock_stat_calc = Mock()
        mock_kpi_analyzer = Mock()
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        metrics = {"mttr": 120.5}
        service.save_kpis_to_csv(metrics)
        
        mock_fs.write_file.assert_called_once_with("kpis.csv", "header\nvalue")

    def test_get_comprehensive_kpis(self):
        """Test getting comprehensive KPIs"""
        mock_repo = Mock()
        mock_repo.count_alerts.return_value = 10
        mock_repo.count_alerts_by_status.return_value = 5
        mock_repo.count_cases.return_value = 3
        mock_repo.count_cases_by_status.return_value = 2
        mock_repo.count_backups_by_status.return_value = 1
        mock_repo.get_average_test_coverage.return_value = 85.5
        mock_repo.get_test_results.return_value = {"passed": 10}
        
        mock_metrics = Mock()
        mock_metrics.get_hardware_metrics.return_value = {"cpu": 50, "memory": 60, "disk": 70}
        
        mock_fs = Mock()
        mock_fs.read_file.return_value = "log content"
        
        mock_log_parser = Mock()
        mock_log_parser.parse.return_value = {"step1": [datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)]}
        
        mock_stat_calc = Mock()
        mock_stat_calc.calculate_execution_times.return_value = [120.5]
        
        mock_kpi_formatter = Mock()
        mock_kpi_analyzer = Mock()
        mock_kpi_analyzer.calculate_mttr_metrics.return_value = {"mttr": 120.5}
        mock_kpi_analyzer.calculate_performance_kpis.return_value = {"performance": 90}
        mock_kpi_analyzer.calculate_health_score.return_value = {"health": 95}
        mock_kpi_analyzer.calculate_comprehensive_kpis.return_value = {"comprehensive": "data"}
        
        service = AnalyticsService(
            data_repository=mock_repo,
            system_metrics=mock_metrics,
            file_system=mock_fs,
            log_parser=mock_log_parser,
            kpi_formatter=mock_kpi_formatter,
            statistical_calculator=mock_stat_calc,
            kpi_analyzer=mock_kpi_analyzer
        )
        
        result = service.get_comprehensive_kpis(log_file_path="/path/to/log.txt")
        
        assert result == {"comprehensive": "data"}
        mock_kpi_analyzer.calculate_comprehensive_kpis.assert_called_once()
