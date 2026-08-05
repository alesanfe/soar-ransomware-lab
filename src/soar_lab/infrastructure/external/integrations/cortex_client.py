#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Cortex Client
Dedicated client for Cortex analysis engine.
"""

from soar_lab.infrastructure.external.integrations.base_client import BaseHTTPClient
from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class CortexClient(BaseHTTPClient):
    """Client for Cortex API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        config_provider: Optional[object] = None,
        verify_ssl: bool = True,
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

        super().__init__(base_url=url, api_key=key, verify_ssl=verify_ssl)

    def _default_headers(self, api_key: Optional[str]) -> Dict[str, str]:
        """Use Bearer token (CORTEX_API_KEY) for Cortex API."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def list_analyzers(self) -> List[Dict[str, Any]]:
        """Return list of available analyzers."""
        # Cortex 3+ uses POST /api/analyzer/_search for listing analyzers
        payload = {"query": {}, "range": "all"}
        result = self.post("/api/analyzer/_search", data=payload)
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

    def list_jobs(self, start: int = 0, count: int = 10) -> List[Dict[str, Any]]:
        """Return recent analyzer jobs.

        Args:
            start: Offset (0-based).
            count: Maximum number of jobs to return.

        Returns:
            List of job dicts.
        """
        result = self.get("/api/job", params={"range": f"{start}-{start + count}"})
        return result if isinstance(result, list) else []

    def list_analyzers_by_type(self, data_type: str) -> List[Dict[str, Any]]:
        """Return analyzers capable of handling a specific data type.

        Args:
            data_type: e.g. "hash", "ip", "domain", "url".

        Returns:
            Filtered list of analyzer dicts.
        """
        # Get all analyzers and filter by data type
        all_analyzers = self.list_analyzers()
        return [a for a in all_analyzers if data_type in a.get("dataTypeList", [])]

    def wait_for_job(
        self,
        job_id: str,
        timeout: int = 60,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Poll a job until it finishes or timeout is reached.

        Args:
            job_id: Cortex job ID.
            timeout: Max seconds to wait.
            poll_interval: Seconds between polls.

        Returns:
            Final job dict (status may be Success, Failure, or still InProgress on timeout).
        """
        import time
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.get_job(job_id)
            if job.get("status") in ("Success", "Failure"):
                return job
            time.sleep(poll_interval)
        return self.get_job(job_id)

    def get_version(self) -> Dict[str, Any]:
        """Return Cortex version and status information."""
        return self.get("/api/version")

    def health_check(self) -> bool:
        """Check if Cortex is reachable."""
        try:
            self.get("/")
            return True
        except Exception:
            return False
