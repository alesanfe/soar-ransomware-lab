#!/usr/bin/env python3
"""Unit tests for SystemMetricsDriver."""

from unittest.mock import MagicMock, patch

from soar_lab.infrastructure.monitoring.system_metrics_driver import SystemMetricsDriver


class TestSystemMetricsDriver:
    """Test SystemMetricsDriver with mocked psutil."""

    @patch("soar_lab.infrastructure.monitoring.system_metrics_driver.psutil")
    def test_get_hardware_metrics_success(self, mock_psutil):
        """Test successful hardware metrics collection."""
        # Mock psutil responses
        mock_psutil.cpu_percent.return_value = 50.0
        mock_psutil.cpu_count.return_value = 4

        mock_memory = MagicMock()
        mock_memory.percent = 75.0
        mock_memory.used = 8 * (1024**3)  # 8 GB
        mock_memory.total = 16 * (1024**3)  # 16 GB
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.percent = 60.0
        mock_disk.used = 100 * (1024**3)  # 100 GB
        mock_disk.total = 500 * (1024**3)  # 500 GB
        mock_psutil.disk_usage.return_value = mock_disk

        mock_network = MagicMock()
        mock_network.bytes_sent = 1000000
        mock_network.bytes_recv = 2000000
        mock_psutil.net_io_counters.return_value = mock_network

        result = SystemMetricsDriver.get_hardware_metrics()

        assert "cpu" in result
        assert result["cpu"]["percent"] == 50.0
        assert result["cpu"]["count"] == 4

        assert "memory" in result
        assert result["memory"]["percent"] == 75.0
        assert result["memory"]["used_gb"] == 8.0
        assert result["memory"]["total_gb"] == 16.0

        assert "disk" in result
        assert result["disk"]["percent"] == 60.0
        assert result["disk"]["used_gb"] == 100.0
        assert result["disk"]["total_gb"] == 500.0

        assert "network" in result
        assert result["network"]["bytes_sent"] == 1000000
        assert result["network"]["bytes_recv"] == 2000000

        assert "timestamp" in result
        assert "error" not in result

    @patch("soar_lab.infrastructure.monitoring.system_metrics_driver.psutil")
    def test_get_hardware_metrics_exception(self, mock_psutil):
        """Test hardware metrics collection with exception."""
        mock_psutil.cpu_percent.side_effect = Exception("psutil error")

        result = SystemMetricsDriver.get_hardware_metrics()

        assert "cpu" in result
        assert result["cpu"]["percent"] == 0
        assert result["cpu"]["count"] == 0

        assert "memory" in result
        assert result["memory"]["percent"] == 0

        assert "disk" in result
        assert result["disk"]["percent"] == 0

        assert "error" in result
        assert "psutil error" in result["error"]

    @patch("soar_lab.infrastructure.monitoring.system_metrics_driver.psutil")
    def test_get_process_metrics_success(self, mock_psutil):
        """Test successful process metrics collection."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.cpu_percent.return_value = 25.0
        mock_process.memory_info.return_value.rss = 512 * (1024**2)  # 512 MB
        mock_process.memory_percent.return_value = 10.0
        mock_process.num_threads.return_value = 8
        mock_process.create_time.return_value = 1609459200.0
        mock_process.status.return_value = "running"
        mock_psutil.Process.return_value = mock_process

        result = SystemMetricsDriver.get_process_metrics()

        assert result["pid"] == 12345
        assert result["cpu_percent"] == 25.0
        assert result["memory_mb"] == 512.0
        assert result["memory_percent"] == 10.0
        assert result["num_threads"] == 8
        assert result["status"] == "running"
        assert "timestamp" in result
        assert "error" not in result

    @patch("soar_lab.infrastructure.monitoring.system_metrics_driver.psutil")
    def test_get_process_metrics_exception(self, mock_psutil):
        """Test process metrics collection with exception."""
        mock_psutil.Process.side_effect = Exception("process error")

        result = SystemMetricsDriver.get_process_metrics()

        assert result["pid"] == 0
        assert result["cpu_percent"] == 0
        assert result["memory_mb"] == 0
        assert result["status"] == "unknown"
        assert "error" in result
        assert "process error" in result["error"]

    @patch("soar_lab.infrastructure.monitoring.system_metrics_driver.psutil")
    def test_get_system_load_unix(self, mock_psutil):
        """Test system load on Unix-like systems."""
        mock_psutil.getloadavg.return_value = (1.5, 2.0, 2.5)
        mock_psutil.getloadavg.__name__ = "getloadavg"

        result = SystemMetricsDriver.get_system_load()

        assert result["load_1min"] == 1.5
        assert result["load_5min"] == 2.0
        assert result["load_15min"] == 2.5
        assert "timestamp" in result
        assert "error" not in result
        assert "note" not in result

    @patch("soar_lab.infrastructure.monitoring.system_metrics_driver.psutil")
    def test_get_system_load_windows(self, mock_psutil):
        """Test system load on Windows (no getloadavg)"""
        # Simulate Windows by removing getloadavg
        delattr(mock_psutil, "getloadavg")

        result = SystemMetricsDriver.get_system_load()

        assert result["load_1min"] == 0
        assert result["load_5min"] == 0
        assert result["load_15min"] == 0
        assert "note" in result
        assert "Windows" in result["note"]

    @patch("soar_lab.infrastructure.monitoring.system_metrics_driver.psutil")
    def test_get_system_load_exception(self, mock_psutil):
        """Test system load with exception."""
        mock_psutil.getloadavg.side_effect = Exception("load error")

        result = SystemMetricsDriver.get_system_load()

        assert result["load_1min"] == 0
        assert result["load_5min"] == 0
        assert result["load_15min"] == 0
        assert "error" in result
        assert "load error" in result["error"]
