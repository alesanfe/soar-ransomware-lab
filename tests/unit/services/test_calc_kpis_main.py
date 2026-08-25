#!/usr/bin/env python3
"""Unit tests for calc_kpis.py main() function.

Tests the CLI entry point with mocked Elasticsearch and log file sources,
covering both 'es' and 'log' data source paths.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.data.calc_kpis import main

__all__ = [
    "TestCalcKpisMainEsSource",
    "TestCalcKpisMainLogSource",
]


class TestCalcKpisMainEsSource:
    """Tests for calc_kpis main() with 'es' source."""

    @patch("soar_lab.data.calc_kpis._fetch_mttr_from_es")
    @patch("soar_lab.config.settings.create_settings")
    @patch("soar_lab.infrastructure.config_provider.InfrastructureConfigProvider")
    @patch("soar_lab.infrastructure.path_service.PathService")
    @patch("soar_lab.infrastructure.log_parser.ExecutionLogParser")
    @patch("soar_lab.infrastructure.kpi_formatter.CSVKPIFormatter")
    @patch("soar_lab.domain.statistical_calculator.StatisticalCalculator")
    @patch("soar_lab.domain.services.kpi_analyzer.KPIAnalyzer")
    @patch("requests.get")
    def test_main_es_source_with_mttr_data(
        self,
        mock_requests_get,
        mock_kpi_analyzer,
        mock_stat_calc,
        mock_csv_formatter,
        mock_log_parser,
        mock_path_service,
        mock_config_provider,
        mock_create_settings,
        mock_fetch_mttr,
        tmp_path,
    ):
        """Test main() with ES source when MTTR data is found."""
        mock_fetch_mttr.return_value = [120.0, 90.0, 150.0]
        mock_kpi_analyzer_inst = Mock()
        mock_kpi_analyzer.return_value = mock_kpi_analyzer_inst
        mock_kpi_analyzer_inst.calculate_mttr_metrics.return_value = {"mttr_mean": 120.0}

        # Mock the aggregation request
        mock_agg_response = Mock()
        mock_agg_response.json.return_value = {
            "hits": {"total": {"value": 10}},
            "aggregations": {
                "critical": {"doc_count": 3},
                "thehive_ok": {"doc_count": 8},
                "by_type": {"buckets": [{"key": "ransomware", "doc_count": 7}]},
            },
        }
        mock_requests_get.return_value = mock_agg_response

        mock_csv_formatter_inst = Mock()
        mock_csv_formatter.return_value = mock_csv_formatter_inst
        mock_csv_formatter_inst.format_csv.return_value = "mttr_mean\n120.0\n"

        output_path = str(tmp_path / "kpis.csv")

        with patch("sys.argv", ["calc_kpis", "--source", "es", "--output", output_path]):
            main()

        # Verify CSV was written
        assert Path(output_path).exists()

    @patch("soar_lab.data.calc_kpis._fetch_mttr_from_es")
    @patch("soar_lab.config.settings.create_settings")
    @patch("soar_lab.infrastructure.config_provider.InfrastructureConfigProvider")
    @patch("soar_lab.infrastructure.path_service.PathService")
    @patch("soar_lab.infrastructure.log_parser.ExecutionLogParser")
    @patch("soar_lab.infrastructure.kpi_formatter.CSVKPIFormatter")
    @patch("soar_lab.domain.statistical_calculator.StatisticalCalculator")
    @patch("soar_lab.domain.services.kpi_analyzer.KPIAnalyzer")
    def test_main_es_no_mttr_falls_back_to_log(
        self,
        mock_kpi_analyzer,
        mock_stat_calc,
        mock_csv_formatter,
        mock_log_parser,
        mock_path_service,
        mock_config_provider,
        mock_create_settings,
        mock_fetch_mttr,
        tmp_path,
    ):
        """Test main() falls back to log source when ES has no MTTR data."""
        mock_fetch_mttr.return_value = []

        # Mock log parser to return steps
        mock_log_parser_inst = Mock()
        mock_log_parser.return_value = mock_log_parser_inst
        mock_log_parser_inst.parse.return_value = [{"step": "test"}]

        # Mock stat calc to return execution times
        mock_stat_calc_inst = Mock()
        mock_stat_calc.return_value = mock_stat_calc_inst
        mock_stat_calc_inst.calculate_execution_times.return_value = [100.0, 200.0]

        mock_kpi_analyzer_inst = Mock()
        mock_kpi_analyzer.return_value = mock_kpi_analyzer_inst
        mock_kpi_analyzer_inst.calculate_mttr_metrics.return_value = {"mttr_mean": 150.0}

        mock_csv_formatter_inst = Mock()
        mock_csv_formatter.return_value = mock_csv_formatter_inst
        mock_csv_formatter_inst.format_csv.return_value = "mttr_mean\n150.0\n"

        # Create a log file
        log_file = tmp_path / "notify.log"
        log_file.write_text("test log content", encoding="utf-8")

        output_path = str(tmp_path / "kpis.csv")

        with patch(
            "sys.argv",
            ["calc_kpis", "--source", "es", "--log-file", str(log_file), "--output", output_path],
        ):
            main()

        assert Path(output_path).exists()


class TestCalcKpisMainLogSource:
    """Tests for calc_kpis main() with 'log' source."""

    @patch("soar_lab.config.settings.create_settings")
    @patch("soar_lab.infrastructure.config_provider.InfrastructureConfigProvider")
    @patch("soar_lab.infrastructure.path_service.PathService")
    @patch("soar_lab.infrastructure.log_parser.ExecutionLogParser")
    @patch("soar_lab.infrastructure.kpi_formatter.CSVKPIFormatter")
    @patch("soar_lab.domain.statistical_calculator.StatisticalCalculator")
    @patch("soar_lab.domain.services.kpi_analyzer.KPIAnalyzer")
    def test_main_log_source_success(
        self,
        mock_kpi_analyzer,
        mock_stat_calc,
        mock_csv_formatter,
        mock_log_parser,
        mock_path_service,
        mock_config_provider,
        mock_create_settings,
        tmp_path,
    ):
        """Test main() with log source and valid log file."""
        mock_log_parser_inst = Mock()
        mock_log_parser.return_value = mock_log_parser_inst
        mock_log_parser_inst.parse.return_value = [{"step": "test"}]

        mock_stat_calc_inst = Mock()
        mock_stat_calc.return_value = mock_stat_calc_inst
        mock_stat_calc_inst.calculate_execution_times.return_value = [100.0, 200.0]

        mock_kpi_analyzer_inst = Mock()
        mock_kpi_analyzer.return_value = mock_kpi_analyzer_inst
        mock_kpi_analyzer_inst.calculate_mttr_metrics.return_value = {"mttr_mean": 150.0}

        mock_csv_formatter_inst = Mock()
        mock_csv_formatter.return_value = mock_csv_formatter_inst
        mock_csv_formatter_inst.format_csv.return_value = "mttr_mean\n150.0\n"

        log_file = tmp_path / "notify.log"
        log_file.write_text("test log content", encoding="utf-8")

        output_path = str(tmp_path / "kpis.csv")

        with patch(
            "sys.argv",
            ["calc_kpis", "--source", "log", "--log-file", str(log_file), "--output", output_path],
        ):
            main()

        assert Path(output_path).exists()

    @patch("soar_lab.config.settings.create_settings")
    @patch("soar_lab.infrastructure.config_provider.InfrastructureConfigProvider")
    @patch("soar_lab.infrastructure.path_service.PathService")
    @patch("soar_lab.infrastructure.log_parser.ExecutionLogParser")
    @patch("soar_lab.infrastructure.kpi_formatter.CSVKPIFormatter")
    @patch("soar_lab.domain.statistical_calculator.StatisticalCalculator")
    @patch("soar_lab.domain.services.kpi_analyzer.KPIAnalyzer")
    def test_main_log_source_file_not_found(
        self,
        mock_kpi_analyzer,
        mock_stat_calc,
        mock_csv_formatter,
        mock_log_parser,
        mock_path_service,
        mock_config_provider,
        mock_create_settings,
        tmp_path,
    ):
        """Test main() exits with code 1 when log file does not exist."""
        output_path = str(tmp_path / "kpis.csv")

        with patch(
            "sys.argv",
            [
                "calc_kpis",
                "--source",
                "log",
                "--log-file",
                str(tmp_path / "nonexistent.log"),
                "--output",
                output_path,
            ],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    @patch("soar_lab.config.settings.create_settings")
    @patch("soar_lab.infrastructure.config_provider.InfrastructureConfigProvider")
    @patch("soar_lab.infrastructure.path_service.PathService")
    @patch("soar_lab.infrastructure.log_parser.ExecutionLogParser")
    @patch("soar_lab.infrastructure.kpi_formatter.CSVKPIFormatter")
    @patch("soar_lab.domain.statistical_calculator.StatisticalCalculator")
    @patch("soar_lab.domain.services.kpi_analyzer.KPIAnalyzer")
    def test_main_log_source_no_steps(
        self,
        mock_kpi_analyzer,
        mock_stat_calc,
        mock_csv_formatter,
        mock_log_parser,
        mock_path_service,
        mock_config_provider,
        mock_create_settings,
        tmp_path,
    ):
        """Test main() exits with code 1 when no execution steps found in log."""
        mock_log_parser_inst = Mock()
        mock_log_parser.return_value = mock_log_parser_inst
        mock_log_parser_inst.parse.return_value = []

        log_file = tmp_path / "notify.log"
        log_file.write_text("empty log", encoding="utf-8")

        output_path = str(tmp_path / "kpis.csv")

        with patch(
            "sys.argv",
            ["calc_kpis", "--source", "log", "--log-file", str(log_file), "--output", output_path],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
