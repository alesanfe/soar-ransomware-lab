#!/usr/bin/env python3
"""
Unit tests for config_provider.py
"""

import pytest
from unittest.mock import Mock

from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider


class TestInfrastructureConfigProvider:
    """Test InfrastructureConfigProvider infrastructure adapter"""

    def test_initialization_success(self):
        """Test successful initialization with settings"""
        mock_settings = Mock()
        
        provider = InfrastructureConfigProvider(settings=mock_settings)
        
        assert provider._settings == mock_settings

    def test_requires_settings(self):
        """Test that settings is required"""
        with pytest.raises(ValueError, match="settings is required"):
            InfrastructureConfigProvider(settings=None)

    def test_get_existing_key(self):
        """Test getting an existing configuration key"""
        mock_settings = Mock()
        mock_settings.test_key = "test_value"
        
        provider = InfrastructureConfigProvider(settings=mock_settings)
        
        value = provider.get("test_key")
        
        assert value == "test_value"

    def test_get_nonexistent_key_with_default(self):
        """Test getting a non-existent key with default value"""
        mock_settings = Mock()
        del mock_settings.nonexistent_key
        
        provider = InfrastructureConfigProvider(settings=mock_settings)
        
        value = provider.get("nonexistent_key", default="default_value")
        
        assert value == "default_value"

    def test_get_nonexistent_key_without_default(self):
        """Test getting a non-existent key without default value"""
        mock_settings = Mock()
        del mock_settings.nonexistent_key
        
        provider = InfrastructureConfigProvider(settings=mock_settings)
        
        value = provider.get("nonexistent_key")
        
        assert value is None

    def test_get_service_urls(self):
        """Test getting service URLs configuration"""
        mock_settings = Mock()
        mock_settings.SERVICES = {
            "service1": "http://service1.local",
            "service2": "http://service2.local"
        }
        
        provider = InfrastructureConfigProvider(settings=mock_settings)
        
        urls = provider.get_service_urls()
        
        assert urls == {
            "service1": "http://service1.local",
            "service2": "http://service2.local"
        }

    def test_get_service_urls_no_services(self):
        """Test getting service URLs when SERVICES attribute doesn't exist"""
        mock_settings = Mock()
        del mock_settings.SERVICES
        
        provider = InfrastructureConfigProvider(settings=mock_settings)
        
        urls = provider.get_service_urls()
        
        assert urls == {}
