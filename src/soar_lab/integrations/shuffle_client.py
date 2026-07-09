#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Shuffle Client
Dedicated client for Shuffle SOAR orchestration.
"""

import threading
import time
from typing import Any, Dict, List, Optional

from soar_lab.config.logging import get_logger
from soar_lab.integrations.base_client import BaseHTTPClient

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

        super().__init__(base_url=url, api_key=key, verify_ssl=verify_ssl)
        self._session.headers["Connection"] = "close"
        import requests as _req
        self._webhook_session = _req.Session()
        self._webhook_session.verify = verify_ssl
        self._keepalive_stop = threading.Event()
        self._keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
        self._keepalive_thread.start()
        self._warm_cache()

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
            import os as _os, requests as _req2
            # Resolve ES connection — try env vars then .env.full
            es = _os.environ.get("ES_URL", "")
            eu = _os.environ.get("ES_USER", "elastic")
            ep = _os.environ.get("ES_PASS", "")
            if not es:
                try:
                    from pathlib import Path as _P
                    for _f in [_P(".env.full"), _P(__file__).parent.parent.parent.parent / ".env.full"]:
                        if _f.exists():
                            for _l in _f.read_text(errors="replace").splitlines():
                                if not _l.startswith("#") and "=" in _l:
                                    k, _, v = _l.partition("=")
                                    k, v = k.strip(), v.strip()
                                    if k == "ES_URL" and not es:
                                        es = v
                                    elif k == "ES_USER" and not eu:
                                        eu = v
                                    elif k == "ES_PASS" and not ep:
                                        ep = v
                except Exception:
                    pass
            if not es:
                es = "http://localhost:19200"
            er = _req2.get(
                f"{es}/users/_search",
                auth=(eu, ep) if eu and ep else None,
                timeout=5, verify=False,
            )
            if er.status_code == 200:
                hits = er.json().get("hits", {}).get("hits", [])
                if hits:
                    org_id = hits[0]["_source"].get("active_org", {}).get("id", "")
                    if org_id:
                        self._session.headers["Org-Id"] = org_id
                        logger.debug("Shuffle Org-Id header set from ES: %s", org_id)
        except Exception as _e:
            logger.debug("Could not set Org-Id header: %s", _e)

    def _fetch_real_apikey(self) -> str:
        """Return the real apikey from Elasticsearch (Shuffle API redacts it).

        Reads active user's apikey directly from the ES users index.
        Falls back gracefully if ES is not accessible.
        """
        import os as _os, requests as _req
        try:
            _es = _os.environ.get("ES_URL", "")
            _eu = _os.environ.get("ES_USER", "elastic")
            _ep = _os.environ.get("ES_PASS", "")
            if not _es:
                from pathlib import Path as _P
                for _f in [_P(".env.full"), _P(__file__).parent.parent.parent.parent / ".env.full"]:
                    if _f.exists():
                        for _l in _f.read_text(errors="replace").splitlines():
                            if not _l.startswith("#") and "=" in _l:
                                _k, _, _v = _l.partition("=")
                                _k, _v = _k.strip(), _v.strip()
                                if _k == "ES_URL" and not _es:
                                    _es = _v
                                elif _k == "ES_USER" and _eu == "elastic":
                                    _eu = _v
                                elif _k == "ES_PASS" and not _ep:
                                    _ep = _v
            if not _es:
                _es = "http://localhost:19200"
            _r = _req.get(f"{_es}/users/_search?size=1",
                          auth=(_eu, _ep) if _eu and _ep else None,
                          timeout=5, verify=False)
            if _r.status_code == 200:
                _hits = _r.json().get("hits", {}).get("hits", [])
                if _hits:
                    _key = _hits[0]["_source"].get("apikey", "")
                    if _key:
                        logger.debug("_fetch_real_apikey from ES: %s...", _key[:8])
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
        from soar_lab.exceptions import IntegrationError
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
        """Resolve ES URL and credentials for the internal Shuffle datastore."""
        import os as _os
        from pathlib import Path as _P
        es_url = _os.environ.get("ES_URL", "")
        es_user = _os.environ.get("ES_USER", "")
        es_pass = _os.environ.get("ES_PASS", "")
        if not es_url:
            for _f in [_P(".env.full"), _P(__file__).parent.parent.parent.parent / ".env.full"]:
                if _f.exists():
                    for _l in _f.read_text(errors="replace").splitlines():
                        if not _l.startswith("#") and "=" in _l:
                            k, _, v = _l.partition("=")
                            k, v = k.strip(), v.strip()
                            if k == "ES_URL" and not es_url:
                                es_url = v
                            elif k == "ES_USER" and not es_user:
                                es_user = v
                            elif k == "ES_PASS" and not es_pass:
                                es_pass = v
        if not es_url:
            es_url = "http://localhost:19200"
        return es_url, (es_user, es_pass) if es_user and es_pass else None, False

    def get_workflow_executions(self, workflow_id: str, retries: int = 2, retry_delay: float = 1.0) -> List[
        Dict[str, Any]]:
        """Return execution history for a workflow.

        The Shuffle API caps execution history at 100 entries. When an older
        execution is pruned from the API response, we fall back to the internal
        Elasticsearch datastore where every execution is stored.

        Args:
            workflow_id: Shuffle workflow UUID.
            retries: Number of retries on transient API errors (kept for API mode).
            retry_delay: Seconds to wait between retries.

        Returns:
            List of execution dicts (most recent first).
        """
        import requests as _req
        from soar_lab.exceptions import IntegrationError
        # ES datastore keeps every execution; the Shuffle API truncates at 100.
        try:
            es_url, auth, verify = self._get_es_connection()
            search_url = f"{es_url}/workflowexecution-000001/_search"
            query = {
                "query": {"term": {"workflow_id": workflow_id}},
                "sort": [{"started_at": {"order": "desc"}}],
                "size": 1000,
                "_source": ["execution_id", "status", "workflow_id", "results", "started_at", "completed_at"],
            }
            resp = _req.get(search_url, json=query, auth=auth, timeout=10, verify=verify)
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            if hits:
                return [hit["_source"] for hit in hits]
        except Exception as exc:
            logger.debug("ES execution lookup failed: %s", exc)

        # Fallback to API if ES is unavailable
        url = self._url(f"/api/v1/workflows/{workflow_id}/executions")
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

    def get_execution(self, workflow_id: str, execution_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific execution by ID from the workflow's history.

        Args:
            workflow_id: Shuffle workflow UUID.
            execution_id: Execution UUID returned by the webhook trigger.

        Returns:
            Execution dict or None if not found.
        """
        executions = self.get_workflow_executions(workflow_id)
        return next(
            (e for e in executions if e.get("execution_id") == execution_id),
            None,
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

    def health_check(self) -> bool:
        """Check if Shuffle API is reachable."""
        try:
            self.get("/api/v1/health")
            return True
        except Exception:
            return False
