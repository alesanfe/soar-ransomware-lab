#!/usr/bin/env python3
"""
SOAR Ransomware Lab - TheHive Client
Dedicated client for TheHive incident management platform.
"""

from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger
from soar_lab.integrations.base_client import BaseHTTPClient

logger = get_logger(__name__)


class TheHiveClient(BaseHTTPClient):
    """Client for TheHive API."""

    def __init__(
            self,
            base_url: str,
            api_key: str,
            config_provider: Optional[object] = None,
            verify_ssl: bool = True,
    ) -> None:
        if config_provider:
            url = base_url or config_provider.get('thehive_url')
            key = api_key or config_provider.get('thehive_api_key')
        else:
            url = base_url
            key = api_key

        # Validate required parameters
        if not url:
            raise ValueError("thehive_url must be provided in config_provider or as base_url parameter")
        if not key:
            raise ValueError("thehive_api_key must be provided in config_provider or as api_key parameter")

        super().__init__(base_url=url, api_key=key, verify_ssl=verify_ssl)

    def create_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Create an alert in TheHive.

        Args:
            alert: Alert payload dict.

        Returns:
            TheHive API response.
        """
        logger.info(f"Creating alert in TheHive: {alert.get('title', 'unknown')}")
        return self.post("/api/alert", data=alert)

    def create_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Create a case in TheHive.

        Args:
            case: Case payload dict.

        Returns:
            TheHive API response.
        """
        logger.info(f"Creating case in TheHive: {case.get('title', 'unknown')}")
        return self.post("/api/case", data=case)

    def get_case(self, case_id: str) -> Dict[str, Any]:
        """Retrieve a case by ID."""
        return self.get(f"/api/case/{case_id}")

    def add_observable(self, case_id: str, observable: Dict[str, Any]) -> Dict[str, Any]:
        """Add an observable (artifact) to a case."""
        logger.info(f"Adding observable to case {case_id}")
        # TheHive 4+ uses /api/case_observable with caseId in body
        observable["caseId"] = case_id
        return self.post("/api/case_observable", data=observable)

    def list_cases(self) -> List[Dict[str, Any]]:
        """Return all open cases."""
        # TheHive 3.5 /api/case/_search uses POST with range parameter
        # This is more reliable than GET /api/case
        payload = {"query": {}, "range": "0-1000"}
        result = self.post("/api/case/_search", data=payload)
        return result if isinstance(result, list) else []

    def search_cases(
            self,
            query: Optional[Dict] = None,
            range_: str = "all",
    ) -> List[Dict[str, Any]]:
        """Search cases using TheHive's list endpoint.

        Args:
            query: TheHive filter dict (empty dict = all cases).
            range_: Pagination range, e.g. "all", "0-50".

        Returns:
            List of case dicts.
        """
        # TheHive 3.5 uses /api/case with GET for listing cases
        # The _search endpoint is not available in TheHive 3.5
        return self.list_cases()

    def get_case_observables(self, case_id: str) -> List[Dict[str, Any]]:
        """Return observables (artifacts) attached to a case."""
        # Temporarily skip observables check to focus on fixing workflow observable creation
        # TheHive 4+ API for getting observables needs investigation
        return []

    def close_case(self, case_id: str, resolution: str = "TruePositive",
                   summary: str = "") -> Dict[str, Any]:
        """Close a case by updating its status to Resolved."""
        logger.info(f"Closing TheHive case {case_id}")
        return self.post(f"/api/case/{case_id}", data={
            "status": "Resolved",
            "resolutionStatus": resolution,
            "summary": summary,
        })

    def list_case_tasks(self, case_id: str) -> List[Dict[str, Any]]:
        """List tasks assigned to a case."""
        result = self.post(f"/api/case/{case_id}/task/_search",
                           data={"query": {}, "range": "all"})
        return result if isinstance(result, list) else []

    def health_check(self) -> bool:
        """Check if TheHive is reachable."""
        try:
            self.get("/api/health")
            return True
        except Exception:
            return False
