"""System Metrics Driver - Hardware telemetry abstraction.

This driver encapsulates all hardware and system metrics collection,
isolating the application layer from psutil dependencies.
"""

import os
import psutil
from datetime import datetime, timezone
from typing import Dict, Any


class SystemMetricsDriver:
    """Driver for collecting system hardware and performance metrics."""

    @staticmethod
    def get_hardware_metrics(disk_path: str = None) -> Dict[str, Any]:
        """
        Collect hardware metrics (CPU, memory, disk).

        Args:
            disk_path: Path to check disk usage (defaults to root directory).

        Returns:
            Dict with hardware metrics including percentages and timestamps
        """
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024 ** 3)
            memory_total_gb = memory.total / (1024 ** 3)

            # Disk metrics - use portable path
            if disk_path is None:
                disk_path = os.path.abspath(os.sep)  # Root directory for current OS
            disk = psutil.disk_usage(disk_path)
            disk_percent = disk.percent
            disk_used_gb = disk.used / (1024 ** 3)
            disk_total_gb = disk.total / (1024 ** 3)

            # Network metrics
            network = psutil.net_io_counters()
            bytes_sent = network.bytes_sent
            bytes_recv = network.bytes_recv

            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count
                },
                'memory': {
                    'percent': memory_percent,
                    'used_gb': round(memory_used_gb, 2),
                    'total_gb': round(memory_total_gb, 2)
                },
                'disk': {
                    'percent': disk_percent,
                    'used_gb': round(disk_used_gb, 2),
                    'total_gb': round(disk_total_gb, 2)
                },
                'network': {
                    'bytes_sent': bytes_sent,
                    'bytes_recv': bytes_recv
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            # Return empty metrics if psutil fails
            return {
                'cpu': {'percent': 0, 'count': 0},
                'memory': {'percent': 0, 'used_gb': 0, 'total_gb': 0},
                'disk': {'percent': 0, 'used_gb': 0, 'total_gb': 0},
                'network': {'bytes_sent': 0, 'bytes_recv': 0},
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }

    @staticmethod
    def get_process_metrics() -> Dict[str, Any]:
        """
        Collect process-specific metrics.
        
        Returns:
            Dict with process metrics
        """
        try:
            current_process = psutil.Process()

            return {
                'pid': current_process.pid,
                'cpu_percent': current_process.cpu_percent(),
                'memory_mb': current_process.memory_info().rss / (1024 ** 2),
                'memory_percent': current_process.memory_percent(),
                'num_threads': current_process.num_threads(),
                'create_time': datetime.fromtimestamp(current_process.create_time(), timezone.utc).isoformat(),
                'status': current_process.status(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            return {
                'pid': 0,
                'cpu_percent': 0,
                'memory_mb': 0,
                'memory_percent': 0,
                'num_threads': 0,
                'create_time': '',
                'status': 'unknown',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }

    @staticmethod
    def get_system_load() -> Dict[str, Any]:
        """
        Get system load averages (Unix-like systems).
        
        Returns:
            Dict with load averages or empty dict on Windows
        """
        try:
            if hasattr(psutil, 'getloadavg'):
                load1, load5, load15 = psutil.getloadavg()
                return {
                    'load_1min': load1,
                    'load_5min': load5,
                    'load_15min': load15,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                # Windows doesn't have load averages
                return {
                    'load_1min': 0,
                    'load_5min': 0,
                    'load_15min': 0,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'note': 'Load averages not available on Windows'
                }
        except Exception as e:
            return {
                'load_1min': 0,
                'load_5min': 0,
                'load_15min': 0,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
