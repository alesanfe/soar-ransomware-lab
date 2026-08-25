#!/usr/bin/env python3
"""SOAR Ransomware Lab - Cortex Client.

Dedicated client for Cortex analysis engine.
"""

from typing import Any

from soar_lab.common.constants import (
    AUTH_BASIC_PREFIX,
    AUTH_BEARER_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_ACCEPT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)
from soar_lab.config.logging import get_logger
from soar_lab.infrastructure.integrations.base_client import BaseHTTPClient

logger = get_logger(__name__)


class CortexClient(BaseHTTPClient):
    """Client for Cortex API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        config_provider: Any | None = None,
        verify_ssl: bool = True,
        admin_user: str | None = None,
        admin_password: str | None = None,
        timeout: int = 30,
    ) -> None:
        if config_provider:
            url = base_url or config_provider.get("cortex_url")
            key = api_key or config_provider.get("cortex_api_key")
            admin_user = admin_user or config_provider.get("cortex_admin_user", "admin")
            admin_password = admin_password or config_provider.get("cortex_admin_password", "")
        else:
            url = base_url
            key = api_key

        # Validate required parameters
        if not url:
            raise ValueError(
                "cortex_url must be provided in config_provider or as base_url parameter"
            )
        if not key and not admin_password:
            raise ValueError("Either cortex_api_key or cortex_admin_password must be provided")

        self._admin_user = admin_user or "admin"
        self._admin_password = admin_password or ""
        super().__init__(base_url=url, api_key=key, verify_ssl=verify_ssl, timeout=timeout)
        # Cortex uses Play Framework sessions via CORTEX_SESSION cookie.
        # When we send Basic Auth on every request, the cookie conflicts with
        # the auth and Cortex returns 403 on the second request. Disable cookie
        # persistence since we authenticate statelessly with Basic Auth.
        self._session.cookies.clear()
        # Use a cookie policy that rejects all cookies from Cortex
        from http.cookiejar import CookieJar

        class _NoCookieJar(CookieJar):
            def set_cookie(self, _cookie: Any) -> None:
                pass

        self._session.cookies = _NoCookieJar()

    def _default_headers(self, api_key: str | None) -> dict[str, str]:
        """Use Basic Auth or Bearer token for Cortex API depending on available.

        credentials.
        """
        import base64

        headers = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON, HEADER_ACCEPT: CONTENT_TYPE_JSON}
        # Prefer Basic auth with admin credentials (works with all Cortex versions)
        if self._admin_password:
            credentials = base64.b64encode(
                f"{self._admin_user}:{self._admin_password}".encode()
            ).decode()
            headers[HEADER_AUTHORIZATION] = f"{AUTH_BASIC_PREFIX} {credentials}"
        elif api_key:
            # Cortex 3.x uses Bearer token with API key
            headers[HEADER_AUTHORIZATION] = f"{AUTH_BEARER_PREFIX} {api_key}"
        return headers

    def list_analyzers(self) -> list[dict[str, Any]]:
        """Return list of available analyzers.

        Returns:
            list[dict[str, Any]]: List of analyzer dictionaries. Returns an
            empty list if the API response is not a list.

        Raises:
            Exception: If the request to the Cortex API fails.
        """
        # Cortex 3+ uses POST /api/analyzer/_search for listing analyzers
        payload = {"query": {}, "range": "all"}
        result = self.post("/api/analyzer/_search", data=payload)
        return result if isinstance(result, list) else []

    def run_analyzer(
        self,
        analyzer_id: str,
        data_type: str,
        data: str,
    ) -> dict[str, Any]:
        """Submit an observable for analysis.

        Args:
            analyzer_id: ID of the Cortex analyzer.
            data_type: e.g. "ip", "domain", "hash".
            data: The value to analyze.

        Returns:
            Cortex job creation response.
        """
        logger.info("Running Cortex analyzer %s on %s: %s", analyzer_id, data_type, data)
        payload = {
            "dataType": data_type,
            "data": data,
        }
        return dict(self.post(f"/api/analyzer/{analyzer_id}/run", data=payload))

    def get_job(self, job_id: str) -> dict[str, Any]:
        """Get the status of an analyzer job.

        Args:
            job_id: Cortex job ID.

        Returns:
            dict[str, Any]: Job dictionary containing the current status and
            metadata of the analyzer job.

        Raises:
            Exception: If the request to the Cortex API fails.
        """
        return dict(self.get(f"/api/job/{job_id}"))

    def get_job_report(self, job_id: str) -> dict[str, Any]:
        """Get the full report for a completed job.

        Args:
            job_id: Cortex job ID.

        Returns:
            dict[str, Any]: Full report for the completed job, including
            analyzer output and artifacts.

        Raises:
            Exception: If the request to the Cortex API fails.
        """
        return dict(self.get(f"/api/job/{job_id}/report"))

    def list_jobs(self, start: int = 0, count: int = 10) -> list[dict[str, Any]]:
        """Return recent analyzer jobs.

        Args:
            start: Offset (0-based).
            count: Maximum number of jobs to return.

        Returns:
            List of job dicts.
        """
        result = self.get("/api/job", params={"range": f"{start}-{start + count}"})
        return result if isinstance(result, list) else []

    def list_analyzers_by_type(self, data_type: str) -> list[dict[str, Any]]:
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
    ) -> dict[str, Any]:
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

    def get_version(self) -> dict[str, Any]:
        """Return Cortex version and status information.

        Returns:
            dict[str, Any]: Dictionary containing Cortex version and status
            information.

        Raises:
            Exception: If the request to the Cortex API fails.
        """
        return dict(self.get("/api/version"))

    def list_analyzer_definitions(self) -> list[dict[str, Any]]:
        """Return all analyzer definitions available in the Cortex catalog.

        This queries ``GET /api/analyzerdefinition`` which returns the full
        catalog of analyzers that *can* be enabled for the current
        organization (including those not yet installed).

        Returns:
            list[dict[str, Any]]: List of analyzer definition dicts. Returns
            an empty list if the API response is not a list.

        Raises:
            Exception: If the request to the Cortex API fails.
        """
        result = self.get("/api/analyzerdefinition")
        return result if isinstance(result, list) else []

    def install_analyzer(
        self,
        definition_id: str,
        configuration: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Enable an analyzer from the catalog for the current organization.

        This calls ``POST /api/organization/analyzer/{definition_id}`` to
        install (enable) an analyzer definition. If the analyzer is already
        enabled, Cortex returns HTTP 409 (Conflict) which is treated as
        success.

        Args:
            definition_id: The analyzer definition ID (e.g.
                ``"Virusshare_2_0"``).
            configuration: Optional configuration dict. When ``None``, a
                permissive default is used (``max_tlp=3``, ``max_pap=3``,
                no TLP/PAP checks, no auto-extract).

        Returns:
            dict[str, Any]: The API response for the installed analyzer.

        Raises:
            Exception: If the request fails with a non-conflict error.
        """
        if configuration is None:
            configuration = {
                "max_tlp": 3,
                "max_pap": 3,
                "check_tlp": False,
                "check_pap": False,
                "auto_extract_artifacts": False,
            }
        payload = {"name": definition_id, "configuration": configuration}
        return dict(self.post(f"/api/organization/analyzer/{definition_id}", data=payload))

    def health_check(self) -> bool:
        """Check if Cortex is reachable.

        Returns:
            bool: True if Cortex is reachable, False otherwise.
        """
        try:
            self.get("/")
            return True
        except Exception:
            return False
