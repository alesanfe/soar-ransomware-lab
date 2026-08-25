#!/usr/bin/env python3
"""Unit tests for config_provider.py."""

from unittest.mock import Mock

import pytest

from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider


class TestInfrastructureConfigProvider:
    """Test InfrastructureConfigProvider infrastructure adapter."""

    def test_initialization_success(self):
        """Test successful initialization with settings."""
        mock_settings = Mock()

        provider = InfrastructureConfigProvider(settings=mock_settings)

        assert provider._settings == mock_settings

    def test_requires_settings(self):
        """Test that settings is required."""
        with pytest.raises(ValueError, match="settings is required"):
            InfrastructureConfigProvider(settings=None)

    def test_get_existing_key(self):
        """Test getting an existing configuration key."""
        mock_settings = Mock()
        mock_settings.test_key = "test_value"

        provider = InfrastructureConfigProvider(settings=mock_settings)

        value = provider.get("test_key")

        assert value == "test_value"

    def test_get_nonexistent_key_with_default(self):
        """Test getting a non-existent key with default value."""
        mock_settings = Mock()
        del mock_settings.nonexistent_key

        provider = InfrastructureConfigProvider(settings=mock_settings)

        value = provider.get("nonexistent_key", default="default_value")

        assert value == "default_value"

    def test_get_nonexistent_key_without_default(self):
        """Test getting a non-existent key without default value."""
        mock_settings = Mock()
        del mock_settings.nonexistent_key

        provider = InfrastructureConfigProvider(settings=mock_settings)

        value = provider.get("nonexistent_key")

        assert value is None

    def test_get_key_from_config_dict_fallback(self):
        """Test getting a key that exists only in settings._config (lowercase
        keys like 'web_ui_user')"""
        mock_settings = Mock(spec=[])
        mock_settings._config = {"web_ui_user": "admin", "web_ui_password": "secret"}

        provider = InfrastructureConfigProvider(settings=mock_settings)

        assert provider.get("web_ui_user") == "admin"
        assert provider.get("web_ui_password") == "secret"
        assert provider.get("missing_key", "fallback") == "fallback"

    def test_get_service_urls(self):
        """Test getting service URLs configuration via get_service_urls()
        method."""
        expected = {
            "service1": {"url": "http://service1.local", "container": "c1"},
            "service2": {"url": "http://service2.local", "container": "c2"},
        }
        mock_settings = Mock()
        mock_settings.get_service_urls.return_value = expected

        provider = InfrastructureConfigProvider(settings=mock_settings)

        urls = provider.get_service_urls()

        assert urls == expected
        mock_settings.get_service_urls.assert_called_once()

    def test_get_service_urls_no_method(self):
        """Test getting service URLs when settings has no get_service_urls
        method."""
        mock_settings = Mock(spec=[])

        provider = InfrastructureConfigProvider(settings=mock_settings)

        urls = provider.get_service_urls()

        assert urls == {}
