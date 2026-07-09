#!/usr/bin/env python3
"""
Unit tests for generate_kpi_data module
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.services.generate_kpi_data import (
    generate_simulated_alerts,
    calculate_kpis,
    main
)


class TestGenerateSimulatedAlerts:
    """Tests for generate_simulated_alerts function."""

    def test_generate_simulated_alerts_default_count(self):
        """Test generating alerts with default count."""
        alerts = generate_simulated_alerts()

        assert len(alerts) == 100
        for alert in alerts:
            assert "alert_id" in alert
            assert "timestamp" in alert
            assert "severity" in alert
            assert "processing_time" in alert
            assert "mttr" in alert
            assert "success" in alert
            assert alert["severity"] in [1, 2, 3]
            assert 30 <= alert["processing_time"] <= 300
            if alert["success"]:
                assert alert["mttr"] is not None
                assert 300 <= alert["mttr"] <= 7200
            else:
                assert alert["mttr"] is None

    def test_generate_simulated_alerts_custom_count(self):
        """Test generating alerts with custom count."""
        alerts = generate_simulated_alerts(num_alerts=50)

        assert len(alerts) == 50

    def test_generate_simulated_alerts_structure(self):
        """Test that generated alerts have correct structure."""
        alerts = generate_simulated_alerts(num_alerts=10)

        for i, alert in enumerate(alerts):
            assert alert["alert_id"] == f"alert_{i:04d}"
            assert alert["thehive_case_created"] == alert["success"]
            assert alert["cortex_analyzed"] == alert["success"]
            assert alert["misp_searched"] == alert["success"]
            assert alert["es_indexed"] == alert["success"]
            assert alert["wazuh_queried"] == alert["success"]

    def test_generate_simulated_alerts_severity_distribution(self):
        """Test that severity distribution follows expected weights."""
        alerts = generate_simulated_alerts(num_alerts=1000)

        severity_counts = {1: 0, 2: 0, 3: 0}
        for alert in alerts:
            severity_counts[alert["severity"]] += 1

        # With weights [0.6, 0.3, 0.1], expect roughly 60%, 30%, 10%
        # Allow some variance (±5%)
        assert 550 <= severity_counts[1] <= 650
        assert 250 <= severity_counts[2] <= 350
        assert 50 <= severity_counts[3] <= 150


class TestCalculateKPIs:
    """Tests for calculate_kpis function."""

    def test_calculate_kpis_empty_alerts(self):
        """Test calculating KPIs with empty alerts list."""
        kpis = calculate_kpis([])

        assert kpis["total_alerts"] == 0
        assert kpis["successful_alerts"] == 0
        assert kpis["success_rate"] == 0
        assert kpis["processing_time"]["mean"] == 0
        assert kpis["mttr"]["mean"] == 0

    def test_calculate_kpis_all_successful(self):
        """Test calculating KPIs with all successful alerts."""
        alerts = [
            {
                "alert_id": "alert_0001",
                "processing_time": 100.0,
                "mttr": 500.0,
                "success": True,
                "thehive_case_created": True,
                "cortex_analyzed": True,
                "misp_searched": True,
                "es_indexed": True,
                "wazuh_queried": True
            },
            {
                "alert_id": "alert_0002",
                "processing_time": 150.0,
                "mttr": 600.0,
                "success": True,
                "thehive_case_created": True,
                "cortex_analyzed": True,
                "misp_searched": True,
                "es_indexed": True,
                "wazuh_queried": True
            }
        ]

        kpis = calculate_kpis(alerts)

        assert kpis["total_alerts"] == 2
        assert kpis["successful_alerts"] == 2
        assert kpis["success_rate"] == 1.0
        assert kpis["processing_time"]["mean"] == 125.0
        assert kpis["mttr"]["mean"] == 550.0
        assert kpis["service_success_rates"]["thehive"] == 1.0
        assert kpis["service_success_rates"]["cortex"] == 1.0
        assert kpis["service_success_rates"]["misp"] == 1.0
        assert kpis["service_success_rates"]["elasticsearch"] == 1.0
        assert kpis["service_success_rates"]["wazuh"] == 1.0

    def test_calculate_kpis_mixed_success(self):
        """Test calculating KPIs with mixed success alerts."""
        alerts = [
            {
                "alert_id": "alert_0001",
                "processing_time": 100.0,
                "mttr": 500.0,
                "success": True,
                "thehive_case_created": True,
                "cortex_analyzed": True,
                "misp_searched": True,
                "es_indexed": True,
                "wazuh_queried": True
            },
            {
                "alert_id": "alert_0002",
                "processing_time": 150.0,
                "mttr": None,
                "success": False,
                "thehive_case_created": False,
                "cortex_analyzed": False,
                "misp_searched": False,
                "es_indexed": False,
                "wazuh_queried": False
            }
        ]

        kpis = calculate_kpis(alerts)

        assert kpis["total_alerts"] == 2
        assert kpis["successful_alerts"] == 1
        assert kpis["success_rate"] == 0.5
        assert kpis["processing_time"]["mean"] == 125.0
        assert kpis["mttr"]["mean"] == 500.0  # Only successful alert
        assert kpis["service_success_rates"]["thehive"] == 0.5
        assert kpis["service_success_rates"]["cortex"] == 0.5
        assert kpis["service_success_rates"]["misp"] == 0.5
        assert kpis["service_success_rates"]["elasticsearch"] == 0.5
        assert kpis["service_success_rates"]["wazuh"] == 0.5

    def test_calculate_kpis_no_mttr_values(self):
        """Test calculating KPIs when no alerts have MTTR values."""
        alerts = [
            {
                "alert_id": "alert_0001",
                "processing_time": 100.0,
                "mttr": None,
                "success": False,
                "thehive_case_created": False,
                "cortex_analyzed": False,
                "misp_searched": False,
                "es_indexed": False,
                "wazuh_queried": False
            }
        ]

        kpis = calculate_kpis(alerts)

        assert kpis["total_alerts"] == 1
        assert kpis["successful_alerts"] == 0
        assert kpis["success_rate"] == 0.0
        assert kpis["processing_time"]["mean"] == 100.0
        assert kpis["mttr"]["mean"] == 0
        assert kpis["mttr"]["median"] == 0
        assert kpis["mttr"]["p50"] == 0
        assert kpis["mttr"]["p95"] == 0
        assert kpis["mttr"]["p99"] == 0

    def test_calculate_kpis_percentiles(self):
        """Test that percentiles are calculated correctly."""
        alerts = [
            {
                "alert_id": f"alert_{i:04d}",
                "processing_time": float(i * 10),
                "mttr": float(i * 100) if i > 0 else None,
                "success": i > 0,
                "thehive_case_created": i > 0,
                "cortex_analyzed": i > 0,
                "misp_searched": i > 0,
                "es_indexed": i > 0,
                "wazuh_queried": i > 0
            }
            for i in range(1, 101)
        ]

        kpis = calculate_kpis(alerts)

        assert kpis["total_alerts"] == 100
        assert kpis["successful_alerts"] == 100
        assert kpis["processing_time"]["p50"] > 0
        assert kpis["processing_time"]["p95"] > 0
        assert kpis["processing_time"]["p99"] > 0
        assert kpis["mttr"]["p50"] > 0
        assert kpis["mttr"]["p95"] > 0
        assert kpis["mttr"]["p99"] > 0


class TestMain:
    """Tests for main function."""

    @patch('builtins.open', new_callable=Mock)
    @patch('json.dump')
    @patch('builtins.print')
    def test_main_generates_and_saves_kpis(self, mock_print, mock_json_dump, mock_open):
        """Test main function generates alerts, calculates KPIs, and saves to file."""
        mock_open.return_value.__enter__ = Mock()
        mock_open.return_value.__exit__ = Mock()
        mock_open.return_value.write = Mock()

        main()

        # Verify generate_simulated_alerts was called
        mock_print.assert_any_call("Generando datos simulados de alertas...")
        mock_print.assert_any_call("Calculando KPIs...")
        mock_print.assert_any_call("\n=== KPIs Calculados ===")
        mock_print.assert_any_call("\nResultados guardados en: src/soar_lab/infrastructure/artifacts/kpi_results.json")

        # Verify json.dump was called to save results
        assert mock_json_dump.called

    @patch('builtins.open', new_callable=Mock)
    @patch('json.dump')
    @patch('builtins.print')
    @patch('soar_lab.services.generate_kpi_data.generate_simulated_alerts')
    @patch('soar_lab.services.generate_kpi_data.calculate_kpis')
    def test_main_uses_correct_functions(self, mock_calculate_kpis, mock_generate_alerts, mock_print, mock_json_dump, mock_open):
        """Test main function uses generate_simulated_alerts and calculate_kpis."""
        mock_open.return_value.__enter__ = Mock()
        mock_open.return_value.__exit__ = Mock()
        mock_open.return_value.write = Mock()
        mock_generate_alerts.return_value = [{"alert_id": "test"}]
        mock_calculate_kpis.return_value = {"total_alerts": 1}

        main()

        mock_generate_alerts.assert_called_once_with(100)
        mock_calculate_kpis.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
