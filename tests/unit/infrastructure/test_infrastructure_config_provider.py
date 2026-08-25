#!/usr/bin/env python3
"""Unit tests for infrastructure config_provider module."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider


class TestInfrastructureConfigProvider:
    """Tests for InfrastructureConfigProvider class."""

    def test_initialization(self):
        """Test successful initialization."""
        mock_settings = Mock()
        provider = InfrastructureConfigProvider(settings=mock_settings)

        assert provider._settings == mock_settings

    def test_initialization_no_settings(self):
        """Test initialization without settings raises ValueError."""
        with pytest.raises(ValueError, match="settings is required"):
            InfrastructureConfigProvider(settings=None)

    def test_get_from_attribute(self):
        """Test getting config value from Settings attribute."""
        mock_settings = Mock()
        mock_settings.test_key = "test_value"
        provider = InfrastructureConfigProvider(settings=mock_settings)

        result = provider.get("test_key")

        assert result == "test_value"

    def test_get_from_config_dict(self):
        """Test getting config value from Settings._config dict."""
        mock_settings = Mock(spec=[])
        mock_settings._config = {"test_key": "test_value"}
        provider = InfrastructureConfigProvider(settings=mock_settings)

        result = provider.get("test_key")

        assert result == "test_value"

    def test_get_with_default(self):
        """Test getting config value with default."""
        mock_settings = Mock(spec=[])
        mock_settings._config = {}
        provider = InfrastructureConfigProvider(settings=mock_settings)

        result = provider.get("nonexistent_key", default="default_value")

        assert result == "default_value"

    def test_get_nonexistent_key(self):
        """Test getting nonexistent key returns None."""
        mock_settings = Mock(spec=[])
        mock_settings._config = {}
        provider = InfrastructureConfigProvider(settings=mock_settings)

        result = provider.get("nonexistent_key")

        assert result is None

    def test_get_service_urls(self):
        """Test getting service URLs."""
        mock_settings = Mock()
        mock_settings.get_service_urls.return_value = {
            "shuffle": {"url": "http://localhost:8081", "container": "shuffle"}
        }
        provider = InfrastructureConfigProvider(settings=mock_settings)

        result = provider.get_service_urls()

        assert result == {"shuffle": {"url": "http://localhost:8081", "container": "shuffle"}}

    def test_get_service_urls_no_method(self):
        """Test getting service URLs when Settings doesn't have method."""
        mock_settings = Mock()
        del mock_settings.get_service_urls
        provider = InfrastructureConfigProvider(settings=mock_settings)

        result = provider.get_service_urls()

        assert result == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
