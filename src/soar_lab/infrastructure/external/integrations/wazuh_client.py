#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Wazuh Client
Dedicated client for Wazuh SIEM/EDR API (JWT-authenticated).
"""

import base64
import requests
import time
from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.external.integrations.base_client import BaseHTTPClient
from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class WazuhClient(BaseHTTPClient):
    """Client for the Wazuh REST API.

    Wazuh uses a two-step auth: Basic credentials -> JWT token.
    The token is cached and refreshed automatically on expiry (401).
    """

    _TOKEN_TTL = 900

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        config_provider: Optional[object] = None,
        verify_ssl: bool = False,
        token: Optional[str] = None,
    ) -> None:
        if config_provider:
            url = base_url or config_provider.get('wazuh_url')
            usr = username or config_provider.get('wazuh_user', 'wazuh-wui')
            pwd = password or config_provider.get('wazuh_password', '')
        else:
            url, usr, pwd = base_url, username, password

        if not url:
            raise ValueError(
                "wazuh_url must be provided in config_provider or as base_url parameter"
            )
        if not usr or not pwd:
            raise ValueError(
                "wazuh username and password must be provided"
            )

        self._username = usr
        self._password = pwd
        self._token: Optional[str] = token
        self._token_ts: float = time.time() if token else 0.0

        super().__init__(base_url=url, api_key=None, timeout=30, verify_ssl=verify_ssl)

    @property
    def session(self) -> requests.Session:
        """Expose the underlying requests Session for test patching."""
        return self._session

    def _basic_auth_header(self) -> str:
        return base64.b64encode(
            f"{self._username}:{self._password}".encode()
        ).decode()

    def _get_token(self) -> str:
        """Obtain (or return cached) JWT from Wazuh."""
        if self._token and (time.time() - self._token_ts) < self._TOKEN_TTL:
            return self._token
        logger.debug("Refreshing Wazuh JWT token")
        resp = self._session.get(
            self._url("/security/user/authenticate"),
            headers={"Authorization": f"Basic {self._basic_auth_header()}"},
            timeout=self.timeout,
        )
        if not resp.ok:
            raise IntegrationError(
                "WazuhClient", f"Authentication failed: HTTP {resp.status_code}"
            )
        token = resp.json().get("data", {}).get("token", "")
        if not token:
            raise IntegrationError("WazuhClient", "Empty JWT token returned")
        self._token = token
        self._token_ts = time.time()
        self._session.headers.update({"Authorization": f"Bearer {token}"})
        return token

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Perform an authenticated request, refreshing token on 401."""
        self._get_token()
        url = self._url(path)
        # Use method-specific session call (get/post/put/delete) so tests can patch them.
        method_func = getattr(self._session, method.lower())
        try:
            resp = method_func(url, timeout=self.timeout, **kwargs)
            if resp.status_code == 401:
                self._token = None
                self._get_token()
                resp = method_func(url, timeout=self.timeout, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc
        except requests.RequestException as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc

    def get(self, path: str, **kwargs) -> Dict[str, Any]:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        return self._request("POST", path, json=data, **kwargs)

    def list_agents(
        self,
        status: Optional[str] = None,
        select: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Return registered Wazuh agents.

        Args:
            status: Filter by agent status: active, disconnected, never_connected.
            select: Comma-separated fields to return, e.g. "name,id,ip,status".
            limit: Max number of agents to return.

        Returns:
            List of agent dicts.
        """
        params: Dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if select:
            params["select"] = select
        result = self.get("/agents", params=params)
        data = result.get("data", {})
        return data.get("affected_items", data.get("items", []))

    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get details of a single agent.

        Args:
            agent_id: Wazuh agent ID (e.g. "001").

        Returns:
            Agent dict.
        """
        result = self.get(f"/agents/{agent_id}")
        data = result.get("data", {})
        items = data.get("affected_items", data.get("items", []))
        if items:
            return items[0]
        if isinstance(data, dict) and ("id" in data or "name" in data or "ip" in data):
            return data
        return {}

    def get_manager_info(self) -> Dict[str, Any]:
        """Return Wazuh manager information (version, type, etc.)."""
        result = self.get("/manager/info")
        items = result.get("data", {}).get("affected_items", [{}])
        return items[0] if items else {}

    def get_manager_status(self) -> Dict[str, Any]:
        """Return status of Wazuh manager daemons."""
        return self.get("/manager/status")

    def list_agent_vulnerabilities(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return CVEs detected on a specific agent.

        Args:
            agent_id: Wazuh agent ID.
            limit: Max vulnerabilities to return.

        Returns:
            List of vulnerability dicts.
        """
        result = self.get(
            f"/vulnerability/{agent_id}",
            params={"limit": limit},
        )
        return result.get("data", {}).get("affected_items", [])

    def run_active_response(
        self,
        command: str,
        agent_id: str,
        arguments: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Trigger an active-response action on an agent (e.g. isolate host).

        Args:
            command: Active-response command name.
            agent_id: Target agent ID.
            arguments: Optional list of command arguments.

        Returns:
            Wazuh API response.
        """
        payload: Dict[str, Any] = {"command": command, "arguments": arguments or []}
        logger.info(f"Running active response '{command}' on agent {agent_id}")
        return self.post(f"/active-response/{agent_id}", data=payload)

    def get_api_info(self) -> Dict[str, Any]:
        """Return Wazuh API root information (version, etc.)."""
        return self.get("/")

    def get_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return security alerts."""
        result = self.get("/alerts", params={"limit": limit})
        return result.get("data", {}).get("items", result.get("data", {}).get("affected_items", []))

    def restart_agent(self, agent_id: str) -> Dict[str, Any]:
        """Restart a Wazuh agent."""
        return self.put(f"/agents/{agent_id}/restart")

    def isolate_agent(self, agent_id: str) -> Dict[str, Any]:
        """Isolate an agent via active-response firewall-drop."""
        return self.put(f"/active-response/{agent_id}", data={"command": "firewall-drop", "arguments": []})

    def start_syscheck_scan(self, agent_id: str) -> Dict[str, Any]:
        """Trigger a syscheck scan on an agent."""
        return self.put(f"/syscheck/{agent_id}")

    def upgrade_agent(self, agent_id: str, version: str) -> Dict[str, Any]:
        """Upgrade a Wazuh agent to a specific version."""
        return self.put(f"/agents/{agent_id}/upgrade", data={"version": version})

    def assign_group(self, agent_id: str, group: str) -> Dict[str, Any]:
        """Assign a group to an agent."""
        return self.put(f"/agents/{agent_id}/group/{group}")

    def get_fim_events(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return FIM (syscheck) events for an agent."""
        result = self.get(f"/syscheck/{agent_id}", params={"limit": limit})
        return result.get("data", {}).get("items", result.get("data", {}).get("affected_items", []))

    def get_vulnerabilities(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return vulnerability scan results for an agent."""
        result = self.get(f"/vulnerability/{agent_id}", params={"limit": limit})
        return result.get("data", {}).get("items", result.get("data", {}).get("affected_items", []))

    def health_check(self) -> bool:
        """Return True if Wazuh API is reachable and token is obtainable."""
        try:
            self._get_token()
            info = self.get_manager_info()
            return bool(info.get("version"))
        except Exception:
            return False
