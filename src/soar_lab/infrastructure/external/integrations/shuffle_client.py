#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Shuffle Client
Dedicated client for Shuffle SOAR orchestration.
"""

import threading
import time
from soar_lab.infrastructure.external.integrations.base_client import BaseHTTPClient
from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger

logger = get_logger(__name__)


class ShuffleClient(BaseHTTPClient):
    """Client for Shuffle API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        config_provider: Optional[object] = None,
        verify_ssl: bool = True,
    ) -> None:
        if config_provider:
            url = base_url or config_provider.get('shuffle_url')
            key = api_key or config_provider.get('shuffle_api_key')
            self._config_provider = config_provider
        else:
            url = base_url
            key = api_key
            self._config_provider = None

        # Validate required parameters
        if not url:
            raise ValueError("shuffle_url must be provided in config_provider or as base_url parameter")
        if not key:
            raise ValueError("shuffle_api_key must be provided in config_provider or as api_key parameter")

        super().__init__(base_url=url, api_key=key, timeout=30, verify_ssl=verify_ssl)
        self._session.headers["Connection"] = "close"
        import requests as _req
        from requests.adapters import HTTPAdapter as _HTTPAdapter
        self._webhook_session = _req.Session()
        self._webhook_session.verify = verify_ssl
        _webhook_adapter = _HTTPAdapter(pool_connections=50, pool_maxsize=50)
        self._webhook_session.mount("http://", _webhook_adapter)
        self._webhook_session.mount("https://", _webhook_adapter)
        self._keepalive_stop = threading.Event()
        # Skip eager network init in test/CI contexts to avoid NameResolution errors
        if __import__("os").environ.get("SOAR_SKIP_EAGER_INIT") not in ("1", "true", "yes"):
            self._keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            self._keepalive_thread.start()
            self._warm_cache()
        else:
            self._keepalive_thread = None

    def _load_password(self) -> str:
        """Read SHUFFLE_DEFAULT_PASSWORD from env or .env.full."""
        import os as _os
        pw = _os.environ.get("SHUFFLE_DEFAULT_PASSWORD", "")
        if pw:
            return pw
        try:
            from pathlib import Path as _P
            for _f in [_P(".env.full"), _P(__file__).parent.parent.parent.parent / ".env.full"]:
                if _f.exists():
                    for _l in _f.read_text(errors="replace").splitlines():
                        if "SHUFFLE_DEFAULT_PASSWORD" in _l and "=" in _l:
                            return _l.split("=", 1)[1].strip()
        except Exception:
            pass
        return ""

    def _do_login(self) -> bool:
        """POST /api/v1/login once. Returns True on HTTP 200."""
        import os as _os, requests as _req
        username = _os.environ.get("SHUFFLE_DEFAULT_USERNAME", "admin")
        password = self._load_password()
        if not (username and password):
            return False
        try:
            r = _req.post(
                self._url("/api/v1/login"),
                json={"username": username, "password": password},
                timeout=10,
                verify=self._session.verify,
            )
            logger.debug("Shuffle login: HTTP %s", r.status_code)
            return r.status_code == 200
        except Exception as e:
            logger.debug("Shuffle login error: %s", e)
            return False

    def _set_org_id_header(self) -> None:
        """Read active_org.id from Elasticsearch and set it as Org-Id session header.

        Shuffle's Bearer-token auth flow looks up the org_id from the request
        (via Org-Id header, or else the user's active_org).  When its in-memory
        cache is cold it re-reads the user from ES, then verifies org membership.
        Sending an explicit Org-Id header bypasses the org-inference and makes
        the membership check deterministic.
        """
        if self._session.headers.get("Org-Id"):
            return
        try:
            import requests as _req2
            es_url, auth, verify = self._get_es_connection()
            er = _req2.get(
                f"{es_url}/users/_search",
                auth=auth,
                timeout=5, verify=verify,
            )
            if er.status_code == 200:
                hits = er.json().get("hits", {}).get("hits", [])
                if hits:
                    org_id = hits[0]["_source"].get("active_org", {}).get("id", "")
                    if org_id:
                        self._session.headers["Org-Id"] = org_id
                        logger.debug("Shuffle Org-Id header set from OpenSearch: %s", org_id)
        except Exception as _e:
            logger.debug("Could not set Org-Id header: %s", _e)

    def _fetch_real_apikey(self) -> str:
        """Return the real apikey from OpenSearch (Shuffle API redacts it).

        Reads active user's apikey directly from the OpenSearch users index.
        Falls back gracefully if OpenSearch is not accessible.
        """
        import requests as _req
        try:
            es_url, auth, verify = self._get_es_connection()
            _r = _req.get(f"{es_url}/users/_search?size=1",
                          auth=auth,
                          timeout=5, verify=verify)
            if _r.status_code == 200:
                _hits = _r.json().get("hits", {}).get("hits", [])
                if _hits:
                    _key = _hits[0]["_source"].get("apikey", "")
                    if _key:
                        logger.debug("_fetch_real_apikey from OpenSearch: %s...", _key[:8])
                        return _key
        except Exception as _e:
            logger.debug("_fetch_real_apikey error: %s", _e)
        return ""

    def _warm_cache(self) -> None:
        """Heal stale apikey, set Org-Id, then confirm Bearer token works."""
        self._set_org_id_header()

        # Detect stale apikey: try Bearer GET first
        _bearer_ok = False
        try:
            _probe = self._session.get(self._url("/api/v1/workflows"), timeout=10)
            _bearer_ok = (_probe.status_code == 200)
        except Exception:
            pass

        if not _bearer_ok:
            # Bearer token is stale — fetch the real apikey via login+session
            _real_key = self._fetch_real_apikey()
            if _real_key and _real_key != self._session.headers.get("Authorization", "").replace("Bearer ", ""):
                logger.debug("Shuffle apikey healed from %s... to %s...",
                             self._session.headers.get("Authorization", "")[-8:],
                             _real_key[-8:])
                self._session.headers["Authorization"] = f"Bearer {_real_key}"
            # One login to warm the in-memory cache for the (now correct) apikey
            self._do_login()
            # Confirm
            try:
                _r2 = self._session.get(self._url("/api/v1/workflows"), timeout=10)
                logger.debug("Shuffle auth after apikey heal: HTTP %s", _r2.status_code)
            except Exception:
                pass

    def _keepalive_loop(self, interval: int = 25) -> None:
        """Background thread: keep Shuffle's in-memory user cache alive."""
        while not self._keepalive_stop.wait(interval):
            try:
                self._session.get(self._url("/api/v1/workflows"), timeout=5)
            except Exception:
                pass

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
        payload: Dict[str, Any],
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an alert payload to a Shuffle webhook.

        Args:
            webhook_id: Webhook identifier from Shuffle workflow.
            payload: Alert / event data to forward.
            token: Optional bearer token override (uses config from constructor if None).

        Returns:
            Shuffle API response.
        """
        if token is not None:
            effective_token = token
        elif self._config_provider:
            effective_token = self._config_provider.get('siem_webhook_token', "")
        else:
            effective_token = ""
        headers = {}
        if effective_token:
            headers["Authorization"] = f"Bearer {effective_token}"

        logger.info(f"Sending webhook {webhook_id} to Shuffle")
        path = f"/api/v1/hooks/{webhook_id}"
        return self.post(path, data=payload, headers=headers)

    def list_apps(self) -> List[Dict[str, Any]]:
        """Return list of installed Shuffle apps."""
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
                timeout=300,
            )
            return resp.ok
        except Exception:
            return False

    def list_workflows(self) -> List[Dict[str, Any]]:
        """Return list of workflows."""
        result = self.get("/api/v1/workflows")
        return result if isinstance(result, list) else []

    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get a specific workflow by ID."""
        return self.get(f"/api/v1/workflows/{workflow_id}")

    def _get_es_connection(self):
        """Resolve OpenSearch URL and credentials for the internal Shuffle datastore.

        Shuffle stores workflow executions, users and hooks in its own OpenSearch
        index (workflowexecution-000001).  This is separate from the project's
        Elasticsearch indices (soar-alerts, soar-metrics).
        """
        import os as _os
        from pathlib import Path as _P

        es_url = _os.environ.get("SHUFFLE_OPENSEARCH_URL", "")
        es_user = _os.environ.get("SHUFFLE_OPENSEARCH_USERNAME", _os.environ.get("OPENSEARCH_USERNAME", ""))
        es_pass = _os.environ.get("SHUFFLE_OPENSEARCH_PASSWORD", _os.environ.get("OPENSEARCH_PASSWORD", ""))

        env_files = [_P(".env.full"), _P(__file__).parent.parent.parent.parent / ".env.full"]
        if not es_url:
            for _f in env_files:
                if _f.exists():
                    for _l in _f.read_text(errors="replace").splitlines():
                        if not _l.startswith("#") and "=" in _l:
                            k, _, v = _l.partition("=")
                            k, v = k.strip(), v.strip()
                            if k == "SHUFFLE_OPENSEARCH_URL" and not es_url:
                                es_url = v
                            elif k == "OPENSEARCH_USERNAME" and not es_user:
                                es_user = v
                            elif k == "OPENSEARCH_PASSWORD" and not es_pass:
                                es_pass = v
                            elif k == "SHUFFLE_OPENSEARCH_USERNAME" and not es_user:
                                es_user = v
                            elif k == "SHUFFLE_OPENSEARCH_PASSWORD" and not es_pass:
                                es_pass = v

        if not es_url:
            # Inside Docker the OpenSearch service is available as 'opensearch:9200';
            # on the host use the mapped port from .env.full or the standard default.
            in_docker = _os.path.exists("/.dockerenv")
            es_url = "http://opensearch:9200" if in_docker else "http://localhost:8201"

        return es_url, (es_user, es_pass) if es_user and es_pass else None, False

    def get_workflow_executions(
            self,
            workflow_id: str,
            retries: int = 2,
            retry_delay: float = 1.0,
            execution_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
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
        import requests as _req
        from soar_lab.common.exceptions import IntegrationError
        # ES datastore keeps every execution; the Shuffle API truncates at 100.
        try:
            es_url, auth, verify = self._get_es_connection()
            search_url = f"{es_url}/workflowexecution-000001/_search"
            must = [{"term": {"workflow_id": workflow_id}}]
            if execution_ids:
                must.append({"terms": {"execution_id": execution_ids}})
            # Pulling the full "results" blob for many executions can return
            # multi-MB responses and hang the JSON decoder. Only fetch results
            # when we already narrowed the query to specific execution IDs.
            if execution_ids:
                source = ["execution_id", "status", "workflow_id", "results", "started_at", "completed_at"]
            else:
                source = ["execution_id", "status", "workflow_id", "started_at", "completed_at"]
            query = {
                "query": {"bool": {"must": must}},
                "sort": [{"started_at": {"order": "desc"}}],
                "size": len(execution_ids) if execution_ids else 1000,
                "_source": source,
            }
            resp = _req.get(search_url, json=query, auth=auth, timeout=10, verify=verify)
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            if hits:
                return [hit["_source"] for hit in hits]
        except Exception as exc:
            logger.debug("ES execution lookup failed: %s", exc)

        # Fallback to API if ES is unavailable
        url = self._url(f"/api/v1/workflows/{workflow_id}/executions?limit=1000")
        last_exc = None
        for attempt in range(retries + 1):
            try:
                resp = self._session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                result = resp.json() if resp.content else []
                return result if isinstance(result, list) else []
            except _req.RequestException as exc:
                if attempt < retries:
                    time.sleep(retry_delay)
                    last_exc = exc
                    continue
                raise IntegrationError(self.__class__.__name__, str(exc)) from exc
        if last_exc:
            raise IntegrationError(self.__class__.__name__, str(last_exc)) from last_exc
        return []

    def get_execution(
        self,
        workflow_id: str,
        execution_id: str,
        include_results: bool = True,
    ) -> Optional[Dict[str, Any]]:
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
        import requests as _req

        # Fast path: targeted ES query.  This avoids parsing the workflow
        # `results` blob, which can be multi-MB and hang the JSON decoder.
        try:
            es_url, auth, verify = self._get_es_connection()
            search_url = f"{es_url}/workflowexecution-000001/_search"
            source = ["execution_id", "status", "workflow_id", "started_at", "completed_at"]
            if include_results:
                source.append("results")
            query = {
                "query": {"terms": {"execution_id": [execution_id]}},
                "sort": [{"started_at": {"order": "desc"}}],
                "size": 1,
                "_source": source,
            }
            resp = _req.get(search_url, json=query, auth=auth, timeout=10, verify=verify)
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            if hits:
                return hits[0].get("_source", {})
        except Exception as exc:
            logger.debug("get_execution ES lookup failed: %s", exc)

        # API fallbacks.  These may return large `results`; only run them
        # when the caller explicitly asked for full execution data.
        if include_results:
            candidate: Optional[Dict[str, Any]] = None
            for path in (
                f"/api/v1/executions/{execution_id}",
                f"/api/v1/workflows/{workflow_id}/executions/{execution_id}",
            ):
                try:
                    resp = self._session.get(self._url(path), timeout=self.timeout)
                    if resp.status_code == 404:
                        continue
                    resp.raise_for_status()
                    data = resp.json() if resp.content else {}
                    if isinstance(data, dict):
                        if "data" in data and isinstance(data["data"], dict):
                            data = data["data"]
                        if data.get("execution_id") == execution_id or data.get("id") == execution_id:
                            if data.get("results") is not None:
                                return data
                            candidate = data
                except _req.HTTPError:
                    continue
                except Exception as exc:
                    logger.debug("get_execution API fallback failed for %s: %s", path, exc)
                    continue

            try:
                list_url = self._url(f"/api/v1/workflows/{workflow_id}/executions")
                resp = self._session.get(list_url, timeout=self.timeout)
                resp.raise_for_status()
                executions = resp.json() if resp.content else []
                if isinstance(executions, dict) and "data" in executions:
                    executions = executions["data"]
                if isinstance(executions, list):
                    for ex in executions:
                        if isinstance(ex, dict) and (ex.get("execution_id") == execution_id or ex.get("id") == execution_id):
                            if ex.get("results") is not None:
                                return ex
                            candidate = ex
            except Exception as exc:
                logger.debug("get_execution list fallback failed: %s", exc)

            return candidate

        return None

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

    def execute_workflow(self, workflow_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a workflow execution with the provided payload.

        Args:
            workflow_id: Workflow UUID to execute.
            data: Payload / arguments for the workflow execution.

        Returns:
            Shuffle API response for the execution request.
        """
        return self.post(f"/api/v1/workflows/{workflow_id}/execute", data=data)

    def health_check(self) -> bool:
        """Check if Shuffle API is reachable."""
        try:
            self.get("/api/v1/health")
            return True
        except Exception:
            return False
