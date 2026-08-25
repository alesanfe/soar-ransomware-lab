#!/usr/bin/env python3
"""Unit tests for kpi_formatter.py."""

from soar_lab.infrastructure.kpi_formatter import CSVKPIFormatter


class TestCSVKPIFormatter:
    """Test CSVKPIFormatter infrastructure adapter."""

    def test_format_csv(self):
        """Test formatting metrics as CSV."""
        formatter = CSVKPIFormatter()
        metrics = {"mttr_seconds": 120.5, "total_alerts": 10, "resolved_alerts": 8}

        result = formatter.format_csv(metrics)

        assert "mttr_seconds" in result
        assert "total_alerts" in result
        assert "resolved_alerts" in result
        assert "120.5" in result

    def test_format_csv_empty_metrics(self):
        """Test formatting empty metrics."""
        formatter = CSVKPIFormatter()
        metrics = {}

        result = formatter.format_csv(metrics)

        # CSV with header only (accounting for Windows line endings)
        assert result.strip() == ""

    def test_format_csv_single_metric(self):
        """Test formatting single metric."""
        formatter = CSVKPIFormatter()
        metrics = {"value": 42}

        result = formatter.format_csv(metrics)

        assert "value" in result
        assert "42" in result
