#!/usr/bin/env python3
"""Unit tests for infrastructure/auth_defaults.py default provider factories."""

from unittest.mock import MagicMock

import soar_lab.infrastructure.auth_defaults as ad


class TestCreateDefaultConfigProvider:
    def test_returns_none_when_settings_fail(self, monkeypatch):
        monkeypatch.setattr(
            ad, "create_settings", MagicMock(side_effect=RuntimeError("no env"))
        )
        assert ad.create_default_config_provider() is None

    def test_returns_provider_when_settings_load(self, monkeypatch):
        monkeypatch.setattr(ad, "create_settings", lambda: object())
        monkeypatch.setattr(ad, "InfrastructureConfigProvider", lambda s: "PROV")
        assert ad.create_default_config_provider() == "PROV"


class TestSimpleConfigProvider:
    def test_degraded_returns_caller_defaults(self, monkeypatch):
        monkeypatch.setattr(ad, "create_default_config_provider", lambda: None)
        p = ad._SimpleConfigProvider()
        assert p.available is False
        assert p.get("missing", "fallback") == "fallback"
        assert p.get_service_urls() == {}

    def test_delegates_when_backend_available(self, monkeypatch):
        backend = MagicMock()
        backend.get.return_value = "value"
        backend.get_service_urls.return_value = {"svc": "http://x"}
        monkeypatch.setattr(ad, "create_default_config_provider", lambda: backend)
        p = ad._SimpleConfigProvider()
        assert p.available is True
        assert p.get("key") == "value"
        assert p.get_service_urls() == {"svc": "http://x"}

    def test_wrapper_returns_simple_provider(self, monkeypatch):
        monkeypatch.setattr(ad, "create_default_config_provider", lambda: None)
        assert isinstance(
            ad.create_default_config_provider_wrapper(), ad._SimpleConfigProvider
        )


class TestSimpleTokenProvider:
    def test_init_builds_jwt_provider(self):
        p = ad._SimpleTokenProvider()
        assert isinstance(p._provider, ad.JWTTokenProvider)

    def test_delegates_create_and_verify(self):
        p = ad._SimpleTokenProvider()
        p._provider = MagicMock()
        p._provider.create_token.return_value = "tok"
        p._provider.verify_token.return_value = {"sub": "u"}
        assert p.create_token("u", "s", 5, "HS256", extra_claims={"r": 1}) == "tok"
        assert p.verify_token("t", "s", "HS256") == {"sub": "u"}

    def test_wrapper_returns_simple_token_provider(self):
        assert isinstance(
            ad.create_default_token_provider_wrapper(), ad._SimpleTokenProvider
        )
