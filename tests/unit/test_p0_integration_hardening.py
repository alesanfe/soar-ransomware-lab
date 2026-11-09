#!/usr/bin/env python3
"""P0 integration-hardening regression tests.

Covers the defect list that took integrations from "works" to
"platform-grade": typed error taxonomy (P0.2), MISP breaker routing
(P0.1), ES latest sort (P0.3), severity contract (P0.4), Shuffle
session leak (P0.5) and credential-validator discovery (P0.6).
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from soar_lab.common.exceptions import (
    IntegrationAuthError,
    IntegrationAuthorizationError,
    IntegrationError,
    IntegrationPayloadError,
    IntegrationRateLimitError,
    IntegrationTimeoutError,
    IntegrationUnavailableError,
    RetryableError,
)
from soar_lab.domain.alert_generator import AlertGenerator
from soar_lab.infrastructure.integrations.base_client import BaseHTTPClient
from soar_lab.infrastructure.integrations.elasticsearch.client import (
    ElasticsearchClient,
)
from soar_lab.infrastructure.integrations.misp.client import MISPClient
from soar_lab.infrastructure.integrations.shuffle.client import ShuffleClient


def _http_error(status: int) -> requests.HTTPError:
    resp = Mock()
    resp.status_code = status
    return requests.HTTPError(f"status {status}", response=resp)


class TestTypedErrorHierarchy:
    """P0.2: domain-vs-infrastructure error distinction."""

    def test_all_integration_errors_carry_service(self):
        for cls in (
            IntegrationTimeoutError,
            IntegrationAuthError,
            IntegrationAuthorizationError,
            IntegrationUnavailableError,
            IntegrationRateLimitError,
            IntegrationPayloadError,
        ):
            exc = cls("svc", "boom")
            assert isinstance(exc, IntegrationError)
            assert exc.service == "svc"
            assert "[svc]" in str(exc)

    def test_retryable_marker(self):
        assert isinstance(IntegrationUnavailableError("s", "m"), RetryableError)
        assert isinstance(IntegrationRateLimitError("s", "m"), RetryableError)
        # auth/payload/timeout are NOT safe to retry blindly
        assert not isinstance(IntegrationAuthError("s", "m"), RetryableError)
        assert not isinstance(IntegrationPayloadError("s", "m"), RetryableError)
        assert not isinstance(IntegrationTimeoutError("s", "m"), RetryableError)


class TestBaseClientErrorTranslation:
    """P0.2: transport errors map to the typed hierarchy."""

    @pytest.fixture()
    def client(self):
        return BaseHTTPClient(base_url="http://x", api_key="k")

    def test_timeout_maps_to_timeout_error(self, client):
        exc = client._translate_error(requests.Timeout("slow"))
        assert isinstance(exc, IntegrationTimeoutError)

    def test_connection_maps_to_unavailable(self, client):
        exc = client._translate_error(requests.ConnectionError("refused"))
        assert isinstance(exc, IntegrationUnavailableError)

    def test_401_maps_to_auth(self, client):
        assert isinstance(client._translate_error(_http_error(401)), IntegrationAuthError)

    def test_403_maps_to_authorization(self, client):
        assert isinstance(
            client._translate_error(_http_error(403)),
            IntegrationAuthorizationError,
        )

    def test_429_maps_to_rate_limit(self, client):
        assert isinstance(client._translate_error(_http_error(429)), IntegrationRateLimitError)

    def test_5xx_maps_to_retryable_unavailable(self, client):
        """BL-ERR-004: a 5xx is transient infrastructure — the retry/breaker
        layer must see RetryableError, not a flattened permanent failure."""
        from soar_lab.common.exceptions import IntegrationUnavailableError

        for status in (500, 502, 503, 504):
            exc = client._translate_error(_http_error(status))
            assert isinstance(exc, IntegrationUnavailableError), status
            assert isinstance(exc, RetryableError), status

    def test_4xx_client_errors_map_to_payload_error(self, client):
        """BL-ERR-004: caller-side HTTP errors are IntegrationPayloadError —
        never retryable, never transient."""
        for status in (400, 404, 409, 422):
            exc = client._translate_error(_http_error(status))
            assert isinstance(exc, IntegrationPayloadError), status
            assert not isinstance(exc, RetryableError), status

    def test_unmapped_status_stays_plain_integration_error(self, client):
        exc = client._translate_error(_http_error(418))
        assert type(exc) is IntegrationError

    def test_get_raises_typed_error_through_breaker(self, client):
        client._session.get = Mock(side_effect=requests.Timeout("slow"))
        with pytest.raises(IntegrationTimeoutError):
            client.get("/path")


class TestMISPBreakerRouting:
    """P0.1: MISPClient.get must go through the shared breaker."""

    def test_get_uses_circuit_breaker(self):
        client = MISPClient(base_url="http://misp", api_key="k")
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.content = b"{}"
        resp.json = Mock(return_value={"ok": True})
        client._session.get = Mock(return_value=resp)

        with patch.object(client.circuit_breaker, "call", wraps=client.circuit_breaker.call) as spy:
            assert client.get("/events") == {"ok": True}
            spy.assert_called_once()

    def test_get_propagates_typed_timeout(self):
        client = MISPClient(base_url="http://misp", api_key="k")
        client._session.get = Mock(side_effect=requests.Timeout("slow"))
        with pytest.raises(IntegrationTimeoutError):
            client.get("/events")

    def test_get_preserves_json_accept_header(self):
        client = MISPClient(base_url="http://misp", api_key="k")
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.content = b"{}"
        resp.json = Mock(return_value={})
        client._session.get = Mock(return_value=resp)

        client.get("/events")
        headers = client._session.get.call_args.kwargs.get("headers", {})
        assert headers.get("Accept") == "application/json"

    def test_search_events_no_false_negative_on_outage(self):
        """If BOTH endpoints fail, an outage must not look like 'no IOCs'."""
        client = MISPClient(base_url="http://misp", api_key="k")
        client.post = Mock(side_effect=IntegrationUnavailableError("MISPClient", "down"))
        with pytest.raises(IntegrationUnavailableError):
            client.search_events(value="1.2.3.4")

    def test_search_events_fallback_still_works(self):
        """First endpoint down but second answers -> legitimate empty."""
        client = MISPClient(base_url="http://misp", api_key="k")
        calls = []

        def fake_post(path, data=None, **kw):
            calls.append(path)
            if "events/restSearch" in path:
                raise IntegrationUnavailableError("MISPClient", "down")
            return {"response": {"Attribute": []}}

        client.post = Mock(side_effect=fake_post)
        assert client.search_events(value="1.2.3.4") == []
        assert len(calls) == 2


class TestElasticsearchLatest:
    """P0.3: 'latest' must actually sort by @timestamp desc."""

    def test_latest_requests_timestamp_desc_sort(self):
        client = ElasticsearchClient(base_url="http://es")
        client.post = Mock(return_value={"hits": {"hits": [{"_source": {"a": 1}}]}})
        result = client.get_latest_documents(size=5)
        body = client.post.call_args.kwargs["data"]
        assert body["sort"] == [{"@timestamp": {"order": "desc", "unmapped_type": "date"}}]
        assert result == [{"a": 1}]

    def test_latest_empty_index(self):
        client = ElasticsearchClient(base_url="http://es")
        client.post = Mock(return_value={"hits": {"hits": []}})
        assert client.get_latest_documents(size=5) == []

    def test_latest_same_timestamp_returns_all(self):
        """Ties on @timestamp must not silently drop documents."""
        client = ElasticsearchClient(base_url="http://es")
        hits = [{"_source": {"n": i}} for i in range(3)]
        client.post = Mock(return_value={"hits": {"hits": hits}})
        result = client.get_latest_documents(size=10)
        assert [d["n"] for d in result] == [0, 1, 2]


class TestSeverityContract:
    """P0.4: severity=0 can never be emitted (schema min is 1)."""

    def test_benign_severity_within_schema(self):
        gen = AlertGenerator()
        for _ in range(50):
            alert = gen.generate_benign()
            assert alert["severity"] >= 1, "severity=0 violates ingest schema"
            assert alert["severity"] <= 5

    def test_malicious_severity_within_schema(self):
        gen = AlertGenerator()
        for _ in range(50):
            assert gen.generate_malicious()["severity"] >= 1


class TestShuffleSessionReuse:
    """P0.5: send_webhook_payload reuses _webhook_session, close() frees it."""

    def _client(self):
        with patch("soar_lab.infrastructure.integrations.shuffle.client.threading.Thread"):
            return ShuffleClient(base_url="http://sh", api_key="k")

    def test_webhook_uses_shared_session(self):
        client = self._client()
        resp = Mock()
        resp.raise_for_status = Mock()
        resp.content = b"{}"
        resp.json = Mock(return_value={"ok": 1})
        client._webhook_session.post = Mock(return_value=resp)

        client.send_webhook_payload("http://hook", {"a": 1})
        client.send_webhook_payload("http://hook", {"a": 2})
        # same underlying session both times — no per-call Session() leak
        assert client._webhook_session.post.call_count == 2

    def test_close_closes_webhook_session(self):
        client = self._client()
        with patch.object(client._webhook_session, "close") as spy:
            client.close()
            spy.assert_called_once()


class TestCredentialValidatorDiscovery:
    """P0.6: discovery via rglob, no stale hardcoded paths."""

    def test_discovers_real_files(self):
        from soar_lab.infrastructure.validate_credentials import _get_file_lists

        rr = next(p for p in Path(__file__).resolve().parents if (p / "infra/docker").is_dir())
        dc, py, cf = _get_file_lists(rr)

        assert dc, "no docker-compose files discovered"
        assert all(f.exists() for f in dc)
        assert py, "no python scripts discovered"
        assert all(f.exists() for f in py)
        # canonical scripts/ tree, not the obsolete src/soar_lab/scripts
        assert any("scripts" in f.parts for f in py)
        assert not any("soar_lab" in f.parts for f in py)

    def test_no_stale_paths_referenced(self):
        """Regression: the old list pointed at nonexistent locations."""
        from soar_lab.infrastructure.validate_credentials import _get_file_lists

        rr = next(p for p in Path(__file__).resolve().parents if (p / "infra/docker").is_dir())
        _, py, _ = _get_file_lists(rr)
        stale = [f for f in py if "src" in f.parts and "soar_lab" in f.parts]
        assert stale == []
