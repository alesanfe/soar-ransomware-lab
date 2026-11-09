#!/usr/bin/env python3
"""Coverage tests for base_client.py paths missed by the happy-path suite.

Covers: ``session`` property, ``post_raw``/``put``/``patch`` verbs,
``_translate_error`` fallthrough edges, the in-Docker URL rewrite
(``_resolve_docker_base_url``/``_load_env_key``) and the TTL DNS cache
(``_cached_getaddrinfo``). All unit-level — the Docker gate is faked by
patching the module ``Path`` symbol, no container needed.
"""

import os
import socket
from unittest.mock import Mock, patch

import pytest
import requests

import soar_lab.infrastructure.integrations.base_client as bc
from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.integrations.base_client import BaseHTTPClient


def _client() -> BaseHTTPClient:
    return BaseHTTPClient("http://example.com")


def _mock_response(payload: dict | None = None):
    resp = Mock()
    resp.content = b'{"ok": true}' if payload is not None else b""
    resp.json.return_value = payload if payload is not None else {}
    resp.raise_for_status.return_value = None
    return resp


class TestSessionProperty:
    def test_session_returns_underlying_requests_session(self):
        client = _client()
        assert client.session is client._session


class TestAdditionalVerbs:
    def test_post_raw_sends_body_and_parses_json(self):
        client = _client()
        resp = _mock_response({"id": 1})
        client._session = Mock(headers={}, post=Mock(return_value=resp))
        out = client.post_raw("bulk", body=b'{"docs":[]}', content_type="application/x-ndjson")
        assert out == {"id": 1}
        _, kwargs = client._session.post.call_args
        assert kwargs["data"] == b'{"docs":[]}'
        assert kwargs["headers"]["Content-Type"] == "application/x-ndjson"

    def test_post_raw_empty_body_returns_empty_dict(self):
        client = _client()
        client._session = Mock(headers={}, post=Mock(return_value=_mock_response(None)))
        assert client.post_raw("bulk", body=b"", content_type="text/plain") == {}

    def test_post_raw_http_error_translated(self):
        client = _client()
        err = requests.HTTPError("500")
        err.response = Mock(status_code=500)
        client._session = Mock(headers={}, post=Mock(side_effect=err))
        with pytest.raises(IntegrationError):
            client.post_raw("bulk", body=b"x", content_type="text/plain")

    def test_put_success_and_error(self):
        client = _client()
        resp = _mock_response({"updated": True})
        client._session = Mock(headers={}, put=Mock(return_value=resp))
        assert client.put("doc/1", data={"a": 1}) == {"updated": True}
        _, kwargs = client._session.put.call_args
        assert kwargs["json"] == {"a": 1}

        client._session.put.side_effect = requests.ConnectionError("down")
        with pytest.raises(IntegrationError):
            client.put("doc/1", data={})

    def test_patch_success_and_error(self):
        client = _client()
        resp = _mock_response({"patched": 3})
        client._session = Mock(headers={}, patch=Mock(return_value=resp))
        assert client.patch("doc/1", data={"b": 2}) == {"patched": 3}

        client._session.patch.side_effect = requests.Timeout("slow")
        with pytest.raises(IntegrationError):
            client.patch("doc/1", data={})


class TestTranslateErrorEdges:
    def test_generic_request_exception_maps_to_plain_integration_error(self):
        client = _client()
        exc = requests.RequestException("weird")
        mapped = client._translate_error(exc)
        assert type(mapped) is IntegrationError

    def test_http_error_without_status_maps_to_plain_integration_error(self):
        client = _client()
        exc = requests.HTTPError("no response attached")
        exc.response = None
        mapped = client._translate_error(exc)
        assert type(mapped) is IntegrationError

    def test_unmapped_4xx_maps_to_plain_integration_error(self):
        client = _client()
        exc = requests.HTTPError("418 teapot")
        exc.response = Mock(status_code=418)
        mapped = client._translate_error(exc)
        assert type(mapped) is IntegrationError

    def test_non_requests_exception_is_not_caught_by_caller_contract(self):
        client = _client()
        # contract: _translate_error only sees RequestException; a raw
        # ValueError still maps to the plain wrapper (no typed signal).
        mapped = client._translate_error(requests.RequestException("x"))
        assert type(mapped) is IntegrationError


class TestDockerUrlResolution:
    """_resolve_docker_base_url only activates inside a container — the
    ``/.dockerenv`` gate is faked by patching the module ``Path``."""

    @staticmethod
    def _in_docker():
        fake_path = Mock()
        fake_path.return_value.exists.return_value = True
        return patch.object(bc, "Path", fake_path)

    def test_outside_docker_returns_url_unchanged(self):
        client = _client()
        # Force the /.dockerenv gate OFF — this test also runs inside
        # containers (mutmut stats) where the file genuinely exists.
        fake_path = Mock()
        fake_path.return_value.exists.return_value = False
        with patch.object(bc, "Path", fake_path):
            url, key = client._resolve_docker_base_url("http://localhost:9000", None)
        assert url == "http://localhost:9000"
        assert key is None

    def test_misp_port80_rewritten_to_https_443(self):
        client = _client()
        with self._in_docker():
            url, _ = client._resolve_docker_base_url("http://misp:80", None)
        assert url == "https://misp:443"

    def test_non_localhost_passthrough(self):
        client = _client()
        with self._in_docker():
            url, _ = client._resolve_docker_base_url("http://thehive:9000/api", None)
        assert url == "http://thehive:9000/api"

    def test_localhost_without_port_passthrough(self):
        client = _client()
        with self._in_docker():
            url, _ = client._resolve_docker_base_url("http://localhost", None)
        assert url == "http://localhost"

    def test_localhost_unmapped_port_passthrough(self):
        client = _client()
        with self._in_docker():
            url, _ = client._resolve_docker_base_url("http://localhost:12345", None)
        assert url == "http://localhost:12345"

    def test_localhost_mapped_port_rewritten(self):
        client = _client()
        with self._in_docker():
            url, _ = client._resolve_docker_base_url("http://localhost:9200", None)
        assert url == "http://elasticsearch:9200"

    def test_mapped_port_loads_key_when_placeholder(self):
        client = _client()
        with self._in_docker():
            with patch.object(client, "_load_env_key", return_value="real-key") as load:
                url, key = client._resolve_docker_base_url("http://localhost:9000", "test-key")
        assert url == "http://thehive:9000"
        assert key == "real-key"
        load.assert_called_once_with("thehive_api_key")

    def test_mapped_port_keeps_real_key(self):
        client = _client()
        with self._in_docker():
            url, key = client._resolve_docker_base_url("http://localhost:9000", "real")
        assert url == "http://thehive:9000"
        assert key == "real"

    def test_resolution_exception_falls_back_to_input(self):
        client = _client()
        with self._in_docker():
            # ``parsed.port`` raises ValueError on a non-numeric port — the
            # guard must degrade to returning the input unchanged.
            url, key = client._resolve_docker_base_url("http://localhost:abc/", "k")
        assert url == "http://localhost:abc/"
        assert key == "k"


class TestLoadEnvKey:
    def test_settings_value_wins(self):
        client = _client()
        fake_settings = Mock()
        fake_settings.get.return_value = "from-settings"
        with patch.object(bc, "Settings", Mock(return_value=fake_settings)):
            assert client._load_env_key("some_key") == "from-settings"

    def test_env_var_fallback_when_settings_empty(self):
        client = _client()
        fake_settings = Mock()
        fake_settings.get.return_value = None
        with patch.object(bc, "Settings", Mock(return_value=fake_settings)):
            with patch.dict("os.environ", {"MY_KEY": "from-env"}):
                assert client._load_env_key("my_key") == "from-env"

    def test_settings_exception_falls_back_to_env(self):
        client = _client()
        with patch.object(bc, "Settings", Mock(side_effect=RuntimeError("no config"))):
            with patch.dict("os.environ", {"FALLBACK_KEY": "env-val"}):
                assert client._load_env_key("fallback_key") == "env-val"

    def test_nothing_configured_returns_none(self):
        client = _client()
        env = {k: v for k, v in os.environ.items() if k != "MISSING_KEY"}
        with patch.object(bc, "Settings", Mock(side_effect=RuntimeError("no config"))):
            with patch.dict("os.environ", env, clear=True):
                assert client._load_env_key("missing_key") is None


class TestCachedGetaddrinfo:
    def setup_method(self):
        bc._DNS_CACHE.clear()

    def teardown_method(self):
        bc._DNS_CACHE.clear()

    def test_miss_calls_real_resolver_and_caches(self):
        with patch.object(bc, "_ORIGINAL_GETADDRINFO", return_value=[("ip",)]) as real:
            out = bc._cached_getaddrinfo("host", 80)
            assert out == [("ip",)]
            assert ("host", 80, 0) in bc._DNS_CACHE
            real.assert_called_once()

    def test_hit_returns_cached_without_resolver(self):
        bc._DNS_CACHE[("host", 80, 0)] = (bc._time.time(), [("cached",)])
        with patch.object(bc, "_ORIGINAL_GETADDRINFO", side_effect=AssertionError("no call")):
            assert bc._cached_getaddrinfo("host", 80) == [("cached",)]

    def test_stale_entry_refreshes_via_resolver(self):
        bc._DNS_CACHE[("host", 80, 0)] = (bc._time.time() - 9999, [("old",)])
        with patch.object(bc, "_ORIGINAL_GETADDRINFO", return_value=[("new",)]):
            assert bc._cached_getaddrinfo("host", 80) == [("new",)]

    def test_dns_failure_serves_stale_cache(self):
        bc._DNS_CACHE[("host", 80, 0)] = (bc._time.time() - 9999, [("stale",)])
        with patch.object(bc, "_ORIGINAL_GETADDRINFO", side_effect=socket.gaierror("NXDOMAIN")):
            assert bc._cached_getaddrinfo("host", 80) == [("stale",)]

    def test_dns_failure_without_cache_raises(self):
        with patch.object(bc, "_ORIGINAL_GETADDRINFO", side_effect=socket.gaierror("NXDOMAIN")):
            with pytest.raises(socket.gaierror):
                bc._cached_getaddrinfo("host", 80)
