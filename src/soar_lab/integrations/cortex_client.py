#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Cortex Client
Dedicated client for Cortex analysis engine.
"""

from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger
from soar_lab.integrations.base_client import BaseHTTPClient

logger = get_logger(__name__)


class CortexClient(BaseHTTPClient):
    """Client for Cortex API."""

    def __init__(
            self,
            base_url: str,
            api_key: str,
            config_provider: Optional[object] = None,
    ) -> None:
        if config_provider:
            url = base_url or config_provider.get('cortex_url')
            key = api_key or config_provider.get('cortex_api_key')
        else:
            url = base_url
            key = api_key

        # Validate required parameters
        if not url:
            raise ValueError("cortex_url must be provided in config_provider or as base_url parameter")
        if not key:
            raise ValueError("cortex_api_key must be provided in config_provider or as api_key parameter")

        super().__init__(base_url=url, api_key=key)

    def list_analyzers(self) -> List[Dict[str, Any]]:
        """Return list of available analyzers."""
        result = self.get("/api/analyzer")
        return result if isinstance(result, list) else []

    def run_analyzer(
            self,
            analyzer_id: str,
            data_type: str,
            data: str,
    ) -> Dict[str, Any]:
        """Submit an observable for analysis.

        Args:
            analyzer_id: ID of the Cortex analyzer.
            data_type: e.g. "ip", "domain", "hash".
            data: The value to analyze.

        Returns:
            Cortex job creation response.
        """
        logger.info(f"Running Cortex analyzer {analyzer_id} on {data_type}: {data}")
        payload = {
            "analyzerId": analyzer_id,
            "dataType": data_type,
            "data": data,
        }
        return self.post("/api/analyzer/run", data=payload)

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get the status of an analyzer job."""
        return self.get(f"/api/job/{job_id}")

    def get_job_report(self, job_id: str) -> Dict[str, Any]:
        """Get the full report for a completed job."""
        return self.get(f"/api/job/{job_id}/report")

    def health_check(self) -> bool:
        """Check if Cortex is reachable."""
        try:
            self.get("/")
            return True
        except Exception:
            return False
