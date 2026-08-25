#!/usr/bin/env python3
"""SOAR Ransomware Lab - Shuffle Client.

Dedicated client for Shuffle SOAR orchestration.
"""

import threading
from typing import Any

from soar_lab.common.constants import AUTH_BEARER_PREFIX, HEADER_AUTHORIZATION
from soar_lab.config.logging import get_logger
from soar_lab.infrastructure.integrations.base_client import BaseHTTPClient
from soar_lab.infrastructure.integrations.shuffle import shuffle_helpers as helpers

logger = get_logger(__name__)

# Re-export shuffle-specific defaults so existing attribute lookups keep working.
DEFAULT_SHUFFLE_TIMEOUT = helpers.DEFAULT_SHUFFLE_TIMEOUT
DEFAULT_SHUFFLE_POOL_SIZE = helpers.DEFAULT_SHUFFLE_POOL_SIZE
DEFAULT_SHUFFLE_WORKFLOW_EXECUTION_TIMEOUT = helpers.DEFAULT_SHUFFLE_WORKFLOW_EXECUTION_TIMEOUT
DEFAULT_SHUFFLE_WORKFLOW_EXECUTIONS_LIMIT = helpers.DEFAULT_SHUFFLE_WORKFLOW_EXECUTIONS_LIMIT
DEFAULT_SHUFFLE_PROBE_TIMEOUT = helpers.DEFAULT_SHUFFLE_PROBE_TIMEOUT
DEFAULT_SHUFFLE_QUICK_TIMEOUT = helpers.DEFAULT_SHUFFLE_QUICK_TIMEOUT


class ShuffleClient(BaseHTTPClient):
    """Client for the Shuffle SOAR orchestration API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        config_provider: Any | None = None,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize the Shuffle client.

        Args:
            base_url: Shuffle base URL (may be empty when ``config_provider``
                supplies ``shuffle_url``).
            api_key: Shuffle API key / Bearer token (may be empty when
                ``config_provider`` supplies ``shuffle_api_key``).
            config_provider: Optional mapping that provides ``shuffle_url``,
                ``shuffle_api_key`` and ``siem_webhook_token``.
            verify_ssl: Whether to verify TLS certificates.

        Raises:
            ValueError: When neither ``base_url``/``api_key`` nor the
                ``config_provider`` supply the required Shuffle URL/key.
        """
        if config_provider:
            url = base_url or config_provider.get("shuffle_url")
            key = api_key or config_provider.get("shuffle_api_key")
            self._config_provider = config_provider
        else:
            url = base_url
            key = api_key
            self._config_provider = None

        if not url:
            raise ValueError(
                "shuffle_url must be provided in config_provider or as base_url parameter"
            )
        if not key:
            raise ValueError(
                "shuffle_api_key must be provided in config_provider or as api_key parameter"
            )

        super().__init__(
            base_url=url, api_key=key, timeout=DEFAULT_SHUFFLE_TIMEOUT, verify_ssl=verify_ssl
        )

        self._keepalive_thread: threading.Thread | None = None
        self._session.headers["Connection"] = "close"
        import requests as _req
        from requests.adapters import HTTPAdapter as _HTTPAdapter

        self._webhook_session = _req.Session()
        self._webhook_session.verify = verify_ssl
        _webhook_adapter = _HTTPAdapter(
            pool_connections=DEFAULT_SHUFFLE_POOL_SIZE, pool_maxsize=DEFAULT_SHUFFLE_POOL_SIZE
        )
        self._webhook_session.mount("http://", _webhook_adapter)
        self._webhook_session.mount("https://", _webhook_adapter)
        self._keepalive_stop = threading.Event()
        # Skip eager network init in test/CI contexts to avoid NameResolution errors.
        import os as _os

        if _os.environ.get("SOAR_SKIP_EAGER_INIT") not in ("1", "true", "yes"):
            self._keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            self._keepalive_thread.start()
            self._warm_cache()
        else:
            self._keepalive_thread = None

    def close(self) -> None:
        """Stop the keepalive thread and release resources.

        Should be called when the client is no longer needed to avoid
        leaking background threads (especially important in test suites
        that create many short-lived clients).
        """
        self._keepalive_stop.set()
        if self._keepalive_thread is not None:
            self._keepalive_thread.join(timeout=5)
            self._keepalive_thread = None
        # Close requests sessions to release socket connections
        try:
            self._session.close()
        except Exception:
            pass
        try:
            self._webhook_session.close()
        except Exception:
            pass

    def __del__(self) -> None:
        """Best-effort cleanup of the keepalive thread on garbage.

        collection.
        """
        try:
            self.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal helpers (thin wrappers around shuffle_helpers functions)
    # ------------------------------------------------------------------
    def _load_password(self) -> str:
        """Read the Shuffle default password (delegates to helpers)."""
        return helpers.load_password()

    def _do_login(self) -> bool:
        """POST ``/api/v1/login`` once (delegates to helpers)."""
        return helpers.do_login(self)

    def _set_org_id_header(self) -> None:
        """Set the ``Org-Id`` session header from OpenSearch (delegates to.

        helpers).
        """
        helpers.set_org_id_header(self)

    def _fetch_real_apikey(self) -> str:
        """Fetch the real apikey from OpenSearch (delegates to helpers)."""
        return helpers.fetch_real_apikey()

    def _warm_cache(self) -> None:
        """Heal a stale apikey and warm Shuffle's auth cache (delegates to.

        helpers).
        """
        helpers.warm_cache(self)

    def _keepalive_loop(self, interval: int = 25) -> None:
        """Background loop keeping Shuffle's in-memory user cache alive."""
        helpers.keepalive_loop(self, self._keepalive_stop, interval)

    @staticmethod
    def _read_env_credentials() -> Any:
        """Read OpenSearch credentials from env/``.env.full`` (delegates to.

        helpers).
        """
        return helpers.read_env_credentials()

    def _get_es_connection(self) -> Any:
        """Resolve the OpenSearch connection for Shuffle's datastore (delegates.

        to helpers).
        """
        return helpers.get_es_connection()

    def _es_lookup_execution(
        self, execution_id: str, include_results: bool
    ) -> dict[str, Any] | None:
        """Targeted OpenSearch lookup for a single execution (delegates to.

        helpers).
        """
        return helpers.es_lookup_execution(self, execution_id, include_results)

    @staticmethod
    def _match_execution(data: Any, execution_id: str) -> dict[str, Any] | None:
        """Extract a matching execution dict from an API response (delegates to.

        helpers).
        """
        return helpers.match_execution(data, execution_id)

    def _api_lookup_execution(self, workflow_id: str, execution_id: str) -> dict[str, Any] | None:
        """API fallback execution lookup (delegates to helpers)."""
        return helpers.api_lookup_execution(self, workflow_id, execution_id)

    def _list_lookup_execution(self, workflow_id: str, execution_id: str) -> dict[str, Any] | None:
        """List-scan fallback execution lookup (delegates to helpers)."""
        return helpers.list_lookup_execution(self, workflow_id, execution_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def send_webhook_payload(self, webhook_url: str, payload: dict, timeout: int = 30) -> dict:
        """POST a payload to a webhook URL using an unauthenticated session.

        Webhooks do not require authentication. Using a separate session prevents
        the Bearer token session from being affected by the webhook connection.

        Args:
            webhook_url: Full webhook URL.
            payload: JSON payload to send.
            timeout: Request timeout in seconds.

        Returns:
            Response JSON dict.

        Raises:
            IntegrationError: If the webhook request fails with an HTTPError
                or RequestException.
        """
        import requests as _req

        from soar_lab.common.exceptions import IntegrationError

        s = _req.Session()
        s.verify = self._session.verify
        try:
            resp = s.post(webhook_url, json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except _req.HTTPError as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc
        except _req.RequestException as exc:
            raise IntegrationError(self.__class__.__name__, str(exc)) from exc

    def send_webhook(
        self,
        webhook_id: str,
        payload: dict[str, Any],
        token: str | None = None,
    ) -> dict[str, Any]:
        """Send an alert payload to a Shuffle webhook.

        Args:
            webhook_id: Webhook identifier from Shuffle workflow.
            payload: Alert / event data to forward.
            token: Optional bearer token override (uses config from constructor if None).

        Returns:
            Shuffle API response.
        """
        effective_token = token
        if effective_token is None and self._config_provider:
            effective_token = self._config_provider.get("siem_webhook_token")
        headers = {}
        if effective_token:
            headers[HEADER_AUTHORIZATION] = f"{AUTH_BEARER_PREFIX} {effective_token}"

        logger.info("Sending webhook %s to Shuffle", webhook_id)
        path = f"/api/v1/hooks/{webhook_id}"
        return dict(self.post(path, data=payload, headers=headers))

    def list_apps(self) -> list[dict[str, Any]]:
        """Return list of installed Shuffle apps.

        Returns:
            List of app dicts; empty list if the response is not a list or no
            apps are installed.

        Raises:
            IntegrationError: If the Shuffle API request fails.
        """
        result = self.get("/api/v1/apps")
        return result if isinstance(result, list) else []

    def download_remote_apps(self, url: str, force_update: bool = False) -> bool:
        """Download apps from a remote GitHub repository.

        Args:
            url: GitHub repo URL, e.g. 'https://github.com/shuffle/python-apps'.
            force_update: If True, re-download even if already present.

        Returns:
            True if the request was accepted.
        """
        try:
            resp = self._session.post(
                self._url("/api/v1/apps/download_remote"),
                json={"url": url, "force_update": force_update},
                timeout=DEFAULT_SHUFFLE_WORKFLOW_EXECUTION_TIMEOUT,
            )
            return resp.ok
        except Exception:
            return False

    def list_workflows(self) -> list[dict[str, Any]]:
        """Return list of workflows.

        Returns:
            List of workflow dicts; empty list if the response is not a list or
            no workflows exist.

        Raises:
            IntegrationError: If the Shuffle API request fails.
        """
        result = self.get("/api/v1/workflows")
        return result if isinstance(result, list) else []

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Get a specific workflow by ID.

        Args:
            workflow_id: Shuffle workflow UUID to retrieve.

        Returns:
            Workflow definition as returned by Shuffle.

        Raises:
            IntegrationError: If the Shuffle API request fails.
        """
        return dict(self.get(f"/api/v1/workflows/{workflow_id}"))

    def get_workflow_executions(
        self,
        workflow_id: str,
        retries: int = 2,
        retry_delay: float = 1.0,
        execution_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return execution history for a workflow.

        The Shuffle API caps execution history at 100 entries. When an older
        execution is pruned from the API response, we fall back to the internal
        Elasticsearch datastore where every execution is stored.

        Args:
            workflow_id: Shuffle workflow UUID.
            retries: Number of retries on transient API errors (kept for API mode).
            retry_delay: Seconds to wait between retries.
            execution_ids: Optional list of execution IDs to restrict the query to.

        Returns:
            List of execution dicts (most recent first).
        """
        # ES datastore keeps every execution; the Shuffle API truncates at 100.
        es_result = helpers.es_workflow_executions(workflow_id, execution_ids)
        if es_result:
            return es_result
        # Fallback to API if ES is unavailable.
        return helpers.api_workflow_executions(self, workflow_id, retries, retry_delay)

    def get_execution(
        self,
        workflow_id: str,
        execution_id: str,
        include_results: bool = True,
    ) -> dict[str, Any] | None:
        """Find a specific execution by ID.

        Args:
            workflow_id: Shuffle workflow UUID.
            execution_id: Execution UUID returned by the webhook trigger.
            include_results: When False, avoid fetching the (potentially huge)
                workflow `results` blob and hit the lightweight ES index first.
                Use this for status-polling loops.

        Returns:
            Execution dict or None if not found.
        """
        # Fast path: ES query.
        result = self._es_lookup_execution(execution_id, include_results)
        if result:
            return result
        # API fallbacks - only when full execution data is requested.
        if not include_results:
            return None
        return self._api_lookup_execution(workflow_id, execution_id) or self._list_lookup_execution(
            workflow_id, execution_id
        )

    def login(self, username: str, password: str) -> bool:
        """Authenticate against Shuffle and update the session cookie/token.

        Args:
            username: Shuffle admin username.
            password: Shuffle admin password.

        Returns:
            True if login succeeded.
        """
        try:
            resp = self._session.post(
                self._url("/api/v1/login"),
                json={"username": username, "password": password},
                timeout=self.timeout,
            )
            return resp.ok
        except Exception:
            return False

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow by ID.

        Args:
            workflow_id: Shuffle workflow UUID.

        Returns:
            True if deleted successfully.
        """
        try:
            resp = self._session.delete(
                self._url(f"/api/v1/workflows/{workflow_id}"),
                timeout=self.timeout,
            )
            return resp.ok
        except Exception:
            return False

    def execute_workflow(self, workflow_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Trigger a workflow execution with the provided payload.

        Args:
            workflow_id: Workflow UUID to execute.
            data: Payload / arguments for the workflow execution.

        Returns:
            Shuffle API response for the execution request.
        """
        return dict(self.post(f"/api/v1/workflows/{workflow_id}/execute", data=data))

    def health_check(self) -> bool:
        """Check if the Shuffle API is reachable.

        Returns:
            True if the Shuffle API is reachable, False otherwise.
        """
        try:
            self.get("/api/v1/health")
            return True
        except Exception:
            return False
