#!/usr/bin/env python3
"""SOAR Ransomware Lab - TheHive Client.

Dedicated client for TheHive incident management platform.
"""

import json
from contextlib import suppress
from typing import Any

from soar_lab.common.constants import DEFAULT_THEHIVE_TIMEOUT
from soar_lab.config.logging import get_logger
from soar_lab.infrastructure.integrations.base_client import BaseHTTPClient

logger = get_logger(__name__)


class TheHiveClient(BaseHTTPClient):
    """Client for TheHive API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        config_provider: Any | None = None,
        verify_ssl: bool = True,
    ) -> None:
        if config_provider:
            url = base_url or config_provider.get("thehive_url")
            key = api_key or config_provider.get("thehive_api_key")
        else:
            url = base_url
            key = api_key

        # Validate required parameters
        if not url:
            raise ValueError(
                "thehive_url must be provided in config_provider or as base_url parameter"
            )
        if not key:
            raise ValueError(
                "thehive_api_key must be provided in config_provider or as api_key parameter"
            )

        super().__init__(
            base_url=url, api_key=key, timeout=DEFAULT_THEHIVE_TIMEOUT, verify_ssl=verify_ssl
        )

    def create_alert(self, alert: dict[str, Any]) -> dict[str, Any]:
        """Create an alert in TheHive.

        Args:
            alert: Alert payload dict.

        Returns:
            TheHive API response.
        """
        logger.info("Creating alert in TheHive: %s", alert.get("title", "unknown"))
        return dict(self.post("/api/alert", data=alert))

    def create_case(
        self,
        case: dict[str, Any] | None = None,
        title: str = "",
        description: str = "",
        severity: int = 2,
        tlp: int = 2,
        pap: int = 2,
        tags: list[str] | None = None,
        template: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a case in TheHive.

        Args can be supplied either as a single payload dict (`case`) or as
        individual fields. Extra kwargs are merged into the payload.

        Args:
            case: Optional payload dict. When provided, takes precedence over
                the individual field arguments.
            title: Case title (used when ``case`` is ``None``).
            description: Case description (used when ``case`` is ``None``).
            severity: Case severity level (0-3). Defaults to 2.
            tlp: Traffic Light Protocol level (0-3). Defaults to 2.
            pap: Permissible Action Protocol level (0-3). Defaults to 2.
            tags: Optional list of tags to attach to the case.
            template: Optional case template name to apply.
            **kwargs: Additional fields merged into the case payload.

        Returns:
            dict[str, Any]: TheHive API response for the created case.

        Raises:
            Exception: If the underlying HTTP request fails.
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
        logger.info("Creating case in TheHive: %s", payload.get("title", "unknown"))
        return dict(self.post("/api/case", data=payload))

    def get_case(self, case_id: str) -> dict[str, Any]:
        """Retrieve a case by ID.

        Args:
            case_id: The unique identifier of the case to retrieve.

        Returns:
            dict[str, Any]: TheHive API response containing the case data.

        Raises:
            Exception: If the underlying HTTP request fails.
        """
        return dict(self.get(f"/api/case/{case_id}"))

    def update_case(self, case_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update an existing case by ID.

        Args:
            case_id: The unique identifier of the case to update.
            **kwargs: Fields to update on the case (e.g. ``title``,
                ``status``, ``severity``).

        Returns:
            dict[str, Any]: TheHive API response for the updated case.

        Raises:
            Exception: If the underlying HTTP request fails.
        """
        logger.info("Updating case %s", case_id)
        return self.patch(f"/api/case/{case_id}", data=kwargs)

    def delete_case(self, case_id: str) -> dict[str, Any]:
        """Delete a case by ID.

        Args:
            case_id: The unique identifier of the case to delete.

        Returns:
            dict[str, Any]: TheHive API response for the deleted case.

        Raises:
            Exception: If the underlying HTTP request fails.
        """
        return dict(self.delete(f"/api/case/{case_id}"))

    def add_observable(
        self, case_id: str, observable: dict[str, Any] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Add an observable (artifact) to a case.

        Args:
            case_id: The unique identifier of the case to attach the
                observable to.
            observable: Optional payload dict describing the observable. When
                ``None``, ``kwargs`` are used as the payload.
            **kwargs: Additional observable fields used when ``observable`` is
                ``None`` (e.g. ``dataType``, ``data``, ``tlp``).

        Returns:
            dict[str, Any]: TheHive API response for the created observable.

        Raises:
            Exception: If the underlying HTTP request fails.
        """
        logger.info("Adding observable to case %s", case_id)
        payload = dict(observable) if observable is not None else kwargs.copy()
        payload.setdefault("tlp", 2)
        payload.setdefault("ioc", True)
        payload.setdefault("sighted", False)
        payload.setdefault("tags", [])
        payload.setdefault("message", "")
        return dict(self.post(f"/api/case/{case_id}/artifact", data=payload))

    def create_observable(
        self, case_id: str, data_type: str = "", data: str = "", **kwargs: Any
    ) -> dict[str, Any]:
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
            tlp=kwargs.pop("tlp", 2),
            ioc=kwargs.pop("ioc", True),
            sighted=kwargs.pop("sighted", False),
            tags=kwargs.pop("tags", []),
            message=kwargs.pop("message", ""),
            **kwargs,
        )

    def list_cases(
        self,
        range_: str = "0-1000",
        sort: list | str | None = None,
    ) -> list[dict[str, Any]]:
        """Return cases from TheHive.

        Args:
            range_: Pagination range, e.g. "0-1000", "0-50".
            sort: Optional sort spec, e.g. ["-caseId"] for newest first.

        Returns:
            List of case dicts.
        """
        params: dict[str, Any] = {"range": range_}
        if sort:
            params["sort"] = json.dumps(sort) if isinstance(sort, list) else sort
        # TheHive 3.5 /api/case with GET and a range query returns a list of cases
        result = self.get("/api/case", params=params)
        if not isinstance(result, list):
            return []
        # TheHive performs soft-delete; "Deleted" cases must be filtered out
        # so that case-counting logic in tests is not skewed by stale cases.
        return [c for c in result if c.get("status") != "Deleted"]

    def search_cases(
        self,
        query: dict | None = None,
        range_: str = "0-1000",
        sort: list | str | None = None,
    ) -> list[dict[str, Any]]:
        """Search cases using TheHive's list/search endpoint.

        Args:
            query: TheHive filter dict (empty dict = all cases).
            range_: Pagination range, e.g. "0-1000", "0-50".
            sort: Optional sort spec, e.g. ["-caseId"] for newest first.

        Returns:
            List of case dicts.
        """
        if query or sort or range_ != "0-1000":
            data: dict[str, Any] = {"query": query or {}}
            if sort:
                data["sort"] = sort
            if range_ != "0-1000":
                data["range"] = range_
            result = self.post("/api/case/_search", data=data)
            if not isinstance(result, list):
                return []
            # Filter soft-deleted cases (see list_cases for rationale)
            return [c for c in result if c.get("status") != "Deleted"]
        # Fall back to plain list endpoint for all cases
        return self.list_cases(range_=range_)

    def get_case_observables(self, case_id: str) -> list[dict[str, Any]]:
        """Return observables attached to a TheHive case.

        Args:
            case_id: The unique identifier of the case whose observables are
                being retrieved.

        Returns:
            list[dict[str, Any]]: List of observable dicts attached to the
            case. Returns an empty list if none are found.

        Raises:
            Exception: If the underlying HTTP request fails.
        """
        logger.info("Listing observables for case %s", case_id)
        result = self.post(
            f"/api/case/{case_id}/artifact/_search", data={"query": {}, "range": "all"}
        )
        return result if isinstance(result, list) else []

    def close_case(
        self, case_id: str, resolution: str = "TruePositive", summary: str = ""
    ) -> dict[str, Any]:
        """Close a case by updating its status to Resolved.

        Args:
            case_id: The unique identifier of the case to close.
            resolution: Resolution status to set, e.g. "TruePositive",
                "FalsePositive", "Indeterminate". Defaults to "TruePositive".
            summary: Optional textual summary of the case resolution.

        Returns:
            dict[str, Any]: TheHive API response for the closed case.

        Raises:
            Exception: If the underlying HTTP request fails.
        """
        logger.info("Closing TheHive case %s", case_id)
        return dict(
            self.post(
                f"/api/case/{case_id}",
                data={
                    "status": "Resolved",
                    "resolutionStatus": resolution,
                    "summary": summary,
                },
            )
        )

    def list_case_tasks(self, case_id: str) -> list[dict[str, Any]]:
        """List tasks assigned to a case.

        Args:
            case_id: The unique identifier of the case whose tasks are being
                listed.

        Returns:
            list[dict[str, Any]]: List of task dicts assigned to the case.
            Returns an empty list if none are found.

        Raises:
            Exception: If the underlying HTTP request fails.
        """
        result = self.post(f"/api/case/{case_id}/task/_search", data={"query": {}, "range": "all"})
        return result if isinstance(result, list) else []

    def get_version(self) -> dict[str, Any]:
        """Return TheHive version and status information.

        Returns:
            dict: TheHive status with version, services, etc.
        """
        return dict(self.get("/api/status"))

    def migrate_case_format(self, case: dict[str, Any]) -> dict[str, Any]:
        """Migrate an old case format to the current format.

        Args:
            case: Case dict in the old format to be migrated.

        Returns:
            dict[str, Any]: A new case dict with the current format, including
            a normalized integer ``severity`` and a default ``tags`` list.
        """
        migrated = case.copy()
        severity = migrated.get("severity")
        if isinstance(severity, str):
            with suppress(ValueError):
                migrated["severity"] = int(severity)
        migrated.setdefault("tags", [])
        return migrated

    def rollback_data_format(self, data: dict[str, Any]) -> dict[str, Any]:
        """Roll back a data structure to the previous supported format.

        Args:
            data: Data dict in the current format to be rolled back.

        Returns:
            dict[str, Any]: A new dict with ``new_``-prefixed keys removed and
            ``version`` set to "4.0.0".
        """
        rolled = data.copy()
        for key in list(rolled.keys()):
            if key.startswith("new_"):
                rolled.pop(key, None)
        rolled["version"] = "4.0.0"
        return rolled

    def check_schema_compatibility(
        self, old_schema: dict[str, Any], new_schema: dict[str, Any]
    ) -> bool:
        """Check whether a new schema is backward-compatible with an old.

        schema.

        Args:
            old_schema: The previous schema dict whose keys must be supported.
            new_schema: The new schema dict to check for compatibility.

        Returns:
            bool: ``True`` if every key in ``old_schema`` is present in
            ``new_schema``, ``False`` otherwise.
        """
        return set(old_schema.keys()).issubset(set(new_schema.keys()))

    def process_deprecated_fields(self, case: dict[str, Any]) -> dict[str, Any]:
        """Remove deprecated fields from a case while preserving valid ones.

        Args:
            case: Case dict potentially containing deprecated fields.

        Returns:
            dict[str, Any]: A new case dict with keys prefixed by ``old_`` or
            ``deprecated_`` removed; all other fields are preserved.
        """
        deprecated_prefixes = ("old_", "deprecated_")
        return {k: v for k, v in case.items() if not k.startswith(deprecated_prefixes)}

    def check_version_compatibility(self, current_version: str, minimum_version: str) -> bool:
        """Return True if current_version is >= minimum_version (semver-like).

        Args:
            current_version: The current semantic version string (e.g. "5.1.0").
            minimum_version: The minimum required semantic version string.

        Returns:
            bool: ``True`` if ``current_version`` is greater than or equal to
            ``minimum_version``, ``False`` otherwise or if either version is
            unparseable.
        """

        def parse(v: str) -> Any:
            return [int(x) for x in v.split(".") if x.isdigit()]

        try:
            return bool(parse(current_version) >= parse(minimum_version))
        except ValueError:
            return False

    def health_check(self) -> bool:
        """Check if TheHive is reachable.

        Returns:
            bool: True if ``/api/health`` responds, False on error.
        """
        try:
            self.get("/api/health")
            return True
        except Exception as exc:
            logger.debug("TheHive health check failed: %s", exc)
            return False
