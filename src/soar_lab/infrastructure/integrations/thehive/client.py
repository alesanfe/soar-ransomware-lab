#!/usr/bin/env python3
"""SOAR Ransomware Lab - TheHive Client.

Dedicated client for TheHive incident management platform.
Targets the TheHive 5 API under ``/api/v1`` (query API for listings).
"""

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
        return dict(self.post("/api/v1/alert", data=alert))

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
        return self._alias(dict(self.post("/api/v1/case", data=payload)))

    def get_case(self, case_id: str) -> dict[str, Any]:
        """Retrieve a case by ID.

        Args:
            case_id: The unique identifier of the case to retrieve.

        Returns:
            dict[str, Any]: TheHive API response containing the case data.

        Raises:
            Exception: If the underlying HTTP request fails.
        """
        return self._alias(dict(self.get(f"/api/v1/case/{case_id}")))

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
        return self.patch(f"/api/v1/case/{case_id}", data=kwargs)

    def delete_case(self, case_id: str) -> dict[str, Any]:
        """Delete a case by ID.

        Args:
            case_id: The unique identifier of the case to delete.

        Returns:
            dict[str, Any]: TheHive API response for the deleted case.

        Raises:
            Exception: If the underlying HTTP request fails.
        """
        return dict(self.delete(f"/api/v1/case/{case_id}"))

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
        result = self.post(f"/api/v1/case/{case_id}/observable", data=payload)
        # TheHive 5 returns a list of created observables on full success and
        # a multi-status {"success": [...], "failure": [...]} on partials.
        if isinstance(result, list):
            return self._alias(dict(result[0])) if result else {}
        if isinstance(result, dict) and "success" in result:
            if result["success"]:
                return self._alias(dict(result["success"][0]))
            raise RuntimeError(f"TheHive observable creation failed: {result.get('failure', [])}")
        return self._alias(dict(result))

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

    @staticmethod
    def _page(range_: str) -> tuple[int, int]:
        """Parse "0-50" style ranges into (from, to) for the query API."""
        try:
            start, end = range_.split("-", 1)
            return max(0, int(start)), max(0, int(end))
        except (ValueError, AttributeError):
            return 0, 1000

    def _query(self, operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Run a TheHive 5 query-API call: POST /api/v1/query {"query": [...]}."""
        result = self.post("/api/v1/query", data={"query": operations})
        return result if isinstance(result, list) else []

    @staticmethod
    def _alias(entity: dict[str, Any]) -> dict[str, Any]:
        """Expose TH3-compatible field aliases on a TH5 entity dict.

        TheHive 5 identifies entities by ``_id`` and numbers cases with
        ``number``; lab code written against TheHive 3 reads ``id`` /
        ``caseId``. Aliases are set only when absent so callers get one
        stable field name regardless of the backend version.
        """
        if isinstance(entity, dict):
            if "id" not in entity and "_id" in entity:
                entity["id"] = entity["_id"]
            if "caseId" not in entity and "number" in entity:
                entity["caseId"] = entity["number"]
            for plain, underscored in (
                ("createdAt", "_createdAt"),
                ("updatedAt", "_updatedAt"),
                ("createdBy", "_createdBy"),
                ("updatedBy", "_updatedBy"),
            ):
                if plain not in entity and underscored in entity:
                    entity[plain] = entity[underscored]
            cf = entity.get("customFields")
            if isinstance(cf, list):
                # TH5 returns customFields as [{name, type, <value-key>, ...}]
                # entries; TH3 consumers read {name: {<value-key>: value}}.
                entity["customFields"] = {
                    item["name"]: {k: v for k, v in item.items() if k != "name"}
                    for item in cf
                    if isinstance(item, dict) and "name" in item
                }
        return entity

    def _alias_list(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply :meth:`_alias` to every entity in a result list."""
        return [self._alias(e) for e in entities]

    def list_cases(
        self,
        range_: str = "0-1000",
        sort: list | str | None = None,
    ) -> list[dict[str, Any]]:
        """Return cases from TheHive.

        Args:
            range_: Pagination range, e.g. "0-1000", "0-50".
            sort: Optional sort spec, e.g. ["-createdAt"] for newest first.

        Returns:
            List of case dicts.
        """
        from_, to = self._page(range_)
        ops: list[dict[str, Any]] = [{"_name": "listCase"}]
        ops.extend(
            (
                {"_name": "sort", "_fields": self._sort_fields(sort)},
                {"_name": "page", "from": from_, "to": to},
            )
        )
        result = self._query(ops)
        # TheHive performs soft-delete; "Deleted" cases must be filtered out
        # so that case-counting logic in tests is not skewed by stale cases.
        return self._alias_list([c for c in result if c.get("status") != "Deleted"])

    @staticmethod
    def _sort_fields(sort: list | str | None) -> list[dict[str, str]]:
        """Translate ["-createdAt"]/"-createdAt" into query-API sort fields."""
        # TheHive 5 case number field is `number`; `caseId` does not exist.
        _ALIASES = {"caseId": "number", "createdAt": "_createdAt", "updatedAt": "_updatedAt"}
        if not sort:
            return [{"number": "desc"}]
        if isinstance(sort, str):
            sort = [sort]
        fields = []
        for spec in sort:
            spec = str(spec)
            if spec.startswith("-"):
                fields.append({_ALIASES.get(spec[1:], spec[1:]): "desc"})
            elif spec.startswith("+"):
                fields.append({_ALIASES.get(spec[1:], spec[1:]): "asc"})
            else:
                fields.append({_ALIASES.get(spec, spec): "asc"})
        return fields or [{"number": "desc"}]

    def search_cases(
        self,
        query: dict | None = None,
        range_: str = "0-1000",
        sort: list | str | None = None,
    ) -> list[dict[str, Any]]:
        """Search cases using TheHive's list/search endpoint.

        Args:
            query: Optional TheHive 5 filter operation, e.g.
                ``{"_name": "filter", "_eq": {"_field": "status",
                "_value": "Indeterminate"}}`` or a plain ``{field: value}``
                equality dict.
            range_: Pagination range, e.g. "0-1000", "0-50".
            sort: Optional sort spec, e.g. ["-createdAt"] for newest first.

        Returns:
            List of case dicts.
        """
        from_, to = self._page(range_)
        ops: list[dict[str, Any]] = [{"_name": "listCase"}]
        if query:
            ops.append({"_name": "filter", **query})
        ops.extend(
            (
                {"_name": "sort", "_fields": self._sort_fields(sort)},
                {"_name": "page", "from": from_, "to": to},
            )
        )
        result = self._query(ops)
        # Filter soft-deleted cases (see list_cases for rationale)
        return self._alias_list([c for c in result if c.get("status") != "Deleted"])

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
        return self._alias_list(
            self._query(
                [
                    {"_name": "getCase", "idOrName": case_id},
                    {"_name": "observables"},
                ]
            )
        )

    def close_case(
        self, case_id: str, resolution: str = "TruePositive", summary: str = ""
    ) -> dict[str, Any]:
        """Close a case by updating its status to a Closed-stage status.

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
        # TheHive 5 case status is a vertex value (New, InProgress,
        # TruePositive, FalsePositive, Indeterminate, Duplicated, Other) —
        # closing means setting a Closed-stage status directly.
        return dict(
            self.patch(
                f"/api/v1/case/{case_id}",
                data={"status": resolution, "summary": summary},
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
        return self._alias_list(
            self._query(
                [
                    {"_name": "getCase", "idOrName": case_id},
                    {"_name": "tasks"},
                ]
            )
        )

    def get_version(self) -> dict[str, Any]:
        """Return TheHive version and status information.

        Returns:
            dict: TheHive status with ``versions`` (``TheHive``, ``Play``…)
            and public ``config`` — served by the unauthenticated
            ``/api/status`` endpoint.
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
            unparsable.
        """

        def parse(v: str) -> Any:
            return [int(x) for x in v.split(".") if x.isdigit()]

        try:
            cur, minimum = parse(current_version), parse(minimum_version)
            if not cur or not minimum:
                return False
            width = max(len(cur), len(minimum))
            cur += [0] * (width - len(cur))
            minimum += [0] * (width - len(minimum))
            return bool(cur >= minimum)
        except ValueError:
            return False

    def health_check(self) -> bool:
        """Check if TheHive is reachable.

        Returns:
            bool: True if ``/api/v1/status/public`` responds, False on error.
        """
        try:
            self.get("/api/v1/status/public")
            return True
        except Exception as exc:
            logger.debug("TheHive health check failed: %s", exc)
            return False
