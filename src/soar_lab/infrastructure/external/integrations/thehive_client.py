#!/usr/bin/env python3
"""
SOAR Ransomware Lab - TheHive Client
Dedicated client for TheHive incident management platform.
"""

import json

from soar_lab.infrastructure.external.integrations.base_client import BaseHTTPClient
from typing import Any, Dict, List, Optional, Union

from soar_lab.config.logging import get_logger

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

        super().__init__(base_url=url, api_key=key, timeout=60, verify_ssl=verify_ssl)

    def create_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Create an alert in TheHive.

        Args:
            alert: Alert payload dict.

        Returns:
            TheHive API response.
        """
        logger.info(f"Creating alert in TheHive: {alert.get('title', 'unknown')}")
        return self.post("/api/alert", data=alert)

    def create_case(
        self,
        case: Optional[Dict[str, Any]] = None,
        title: str = "",
        description: str = "",
        severity: int = 2,
        tlp: int = 2,
        pap: int = 2,
        tags: Optional[List[str]] = None,
        template: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a case in TheHive.

        Args can be supplied either as a single payload dict (`case`) or as
        individual fields. Extra kwargs are merged into the payload.

        Returns:
            TheHive API response.
        """
        if case is not None:
            payload = dict(case)
        else:
            payload = {
                "title": title,
                "description": description,
                "severity": severity,
                "tlp": tlp,
                "pap": pap,
            }
            if tags:
                payload["tags"] = tags
            if template:
                payload["template"] = template
        payload.update(kwargs)
        logger.info(f"Creating case in TheHive: {payload.get('title', 'unknown')}")
        return self.post("/api/case", data=payload)

    def get_case(self, case_id: str) -> Dict[str, Any]:
        """Retrieve a case by ID."""
        return self.get(f"/api/case/{case_id}")

    def delete_case(self, case_id: str) -> Dict[str, Any]:
        """Delete a case by ID."""
        return self.delete(f"/api/case/{case_id}")

    def add_observable(self, case_id: str, observable: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Add an observable (artifact) to a case."""
        logger.info(f"Adding observable to case {case_id}")
        if observable is not None:
            payload = dict(observable)
        else:
            payload = dict(kwargs)
        payload["caseId"] = case_id
        return self.post("/api/case_observable", data=payload)

    def create_observable(
        self,
        case_id: str,
        data_type: str = "",
        data: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """Create an observable for a case.

        Args:
            case_id: Target case ID.
            data_type: Observable data type, e.g. "ip", "domain", "hash".
            data: Observable value.

        Returns:
            TheHive API response.
        """
        return self.add_observable(
            case_id=case_id,
            dataType=data_type,
            data=data,
            **kwargs,
        )

    def list_cases(
        self,
        range_: str = "all",
        sort: Optional[Union[List, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return cases from TheHive.

        Args:
            range_: Pagination range, e.g. "all", "0-50".
            sort: Optional sort spec, e.g. ["-caseId"] for newest first.

        Returns:
            List of case dicts.
        """
        params: Dict[str, Any] = {"range": range_}
        if sort:
            params["sort"] = json.dumps(sort) if isinstance(sort, list) else sort
        # TheHive 3.5 /api/case with GET and a range query returns a list of cases
        result = self.get("/api/case", params=params)
        return result if isinstance(result, list) else []

    def search_cases(
        self,
        query: Optional[Dict] = None,
        range_: str = "all",
        sort: Optional[Union[List, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search cases using TheHive's list/search endpoint.

        Args:
            query: TheHive filter dict (empty dict = all cases).
            range_: Pagination range, e.g. "all", "0-50".
            sort: Optional sort spec, e.g. ["-caseId"] for newest first.

        Returns:
            List of case dicts.
        """
        if query or sort or range_ != "all":
            data: Dict[str, Any] = {"query": query or {}}
            if sort:
                data["sort"] = sort
            if range_ != "all":
                data["range"] = range_
            result = self.post("/api/case/_search", data=data)
            return result if isinstance(result, list) else []
        # Fall back to plain list endpoint for all cases
        return self.list_cases(range_=range_)

    def get_case_observables(self, case_id: str) -> List[Dict[str, Any]]:
        """Return observables (artifacts) attached to a case."""
        logger.info(f"Listing observables for case {case_id}")
        result = self.post(f"/api/case/{case_id}/artifact/_search",
                           data={"query": {}, "range": "all"})
        return result if isinstance(result, list) else []

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

    def get_version(self) -> Dict[str, Any]:
        """Return TheHive version and status information."""
        return self.get("/api/status")

    def migrate_case_format(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate an old case format to the current format."""
        migrated = dict(case)
        severity = migrated.get("severity")
        if isinstance(severity, str):
            try:
                migrated["severity"] = int(severity)
            except ValueError:
                pass
        migrated.setdefault("tags", [])
        return migrated

    def rollback_data_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Roll back a data structure to the previous supported format."""
        rolled = dict(data)
        for key in list(rolled.keys()):
            if key.startswith("new_"):
                rolled.pop(key, None)
        rolled["version"] = "4.0.0"
        return rolled

    def check_schema_compatibility(self, old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> bool:
        """Check whether a new schema is backward-compatible with an old schema."""
        return set(old_schema.keys()).issubset(set(new_schema.keys()))

    def process_deprecated_fields(self, case: Dict[str, Any]) -> Dict[str, Any]:
        """Remove deprecated fields from a case while preserving valid ones."""
        deprecated_prefixes = ("old_", "deprecated_")
        processed = {k: v for k, v in case.items() if not k.startswith(deprecated_prefixes)}
        return processed

    def check_version_compatibility(self, current_version: str, minimum_version: str) -> bool:
        """Return True if current_version is >= minimum_version (semver-like)."""
        def parse(v: str):
            return [int(x) for x in v.split(".") if x.isdigit()]

        try:
            return parse(current_version) >= parse(minimum_version)
        except ValueError:
            return False

    def health_check(self) -> bool:
        """Check if TheHive is reachable."""
        try:
            self.get("/api/health")
            return True
        except Exception:
            return False
