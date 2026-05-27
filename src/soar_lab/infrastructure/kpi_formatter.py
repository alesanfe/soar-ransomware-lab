"""KPI Formatter - Infrastructure implementation for formatting KPI metrics.

This adapter encapsulates KPI formatting logic (CSV, JSON, etc.),
allowing the application layer to remain format-agnostic.
"""

import csv
import io
from typing import Dict, Any

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class CSVKPIFormatter:
    """Infrastructure implementation of KPIFormatter port for CSV formatting."""

    def format_csv(self, metrics: Dict[str, Any]) -> str:
        """
        Format KPI metrics as CSV string.

        Args:
            metrics: KPI metrics dictionary

        Returns:
            CSV formatted string
        """
        csv_output = io.StringIO()
        w = csv.DictWriter(csv_output, fieldnames=metrics.keys())
        w.writeheader()
        w.writerow(metrics)
        return csv_output.getvalue()
