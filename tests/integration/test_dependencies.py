#!/usr/bin/env python3
"""
Unit tests for api/dependencies.py
Tests FastAPI dependency injection functions
"""

import pytest
from unittest.mock import Mock

from soar_lab.api.dependencies import (
    get_composition_root,
    get_config_provider,
    get_redis,
    get_docker,
    get_analytics_service,
    get_backup_service,
    get_test_service,
    get_health_service,
    RedisDep,
    DockerDep,
    ConfigProviderDep,
    AnalyticsServiceDep,
    BackupServiceDep,
    TestServiceDep,
    HealthServiceDep
)


class TestGetCompositionRoot:
    """Test get_composition_root dependency"""

    def test_get_composition_root_with_instance(self):
        """Test get_composition_root with provided instance"""
        mock_root = Mock()
        result = get_composition_root(composition_root=mock_root)
        assert result == mock_root

    def test_get_composition_root_without_instance(self):
        """Test get_composition_root raises error without instance"""
        with pytest.raises(ValueError, match="composition_root must be provided"):
            get_composition_root(composition_root=None)


class TestGetConfigProvider:
    """Test get_config_provider dependency"""

    def test_get_config_provider(self):
        """Test get_config_provider returns config_provider from composition root"""
        mock_config = Mock()
        mock_root = Mock()
        mock_root.config_provider = mock_config
        
        result = get_config_provider(composition_root=mock_root)
        assert result == mock_config


class TestGetRedis:
    """Test get_redis dependency"""

    def test_get_redis(self):
        """Test get_redis returns redis_client from composition root"""
        mock_redis = Mock()
        mock_root = Mock()
        mock_root.redis_client = mock_redis
        
        result = get_redis(composition_root=mock_root)
        assert result == mock_redis


class TestGetDocker:
    """Test get_docker dependency"""

    def test_get_docker(self):
        """Test get_docker returns docker_client from composition root"""
        mock_docker = Mock()
        mock_root = Mock()
        mock_root.docker_client = mock_docker
        
        result = get_docker(composition_root=mock_root)
        assert result == mock_docker


class TestGetAnalyticsService:
    """Test get_analytics_service dependency"""

    def test_get_analytics_service(self):
        """Test get_analytics_service returns analytics_service from composition root"""
        mock_service = Mock()
        mock_root = Mock()
        mock_root.analytics_service = mock_service
        
        result = get_analytics_service(composition_root=mock_root)
        assert result == mock_service


class TestGetBackupService:
    """Test get_backup_service dependency"""

    def test_get_backup_service(self):
        """Test get_backup_service returns backup_service from composition root"""
        mock_service = Mock()
        mock_root = Mock()
        mock_root.backup_service = mock_service
        
        result = get_backup_service(composition_root=mock_root)
        assert result == mock_service


class TestGetTestService:
    """Test get_test_service dependency"""

    def test_get_test_service(self):
        """Test get_test_service returns test_service from composition root"""
        mock_service = Mock()
        mock_root = Mock()
        mock_root.test_service = mock_service
        
        result = get_test_service(composition_root=mock_root)
        assert result == mock_service


class TestGetHealthService:
    """Test get_health_service dependency"""

    def test_get_health_service(self):
        """Test get_health_service returns health_service from composition root"""
        mock_service = Mock()
        mock_root = Mock()
        mock_root.health_service = mock_service
        
        result = get_health_service(composition_root=mock_root)
        assert result == mock_service


class TestTypeAliases:
    """Test type aliases for dependency annotations"""

    def test_redis_dep_type(self):
        """Test RedisDep type alias exists"""
        assert RedisDep is not None

    def test_docker_dep_type(self):
        """Test DockerDep type alias exists"""
        assert DockerDep is not None

    def test_config_provider_dep_type(self):
        """Test ConfigProviderDep type alias exists"""
        assert ConfigProviderDep is not None

    def test_analytics_service_dep_type(self):
        """Test AnalyticsServiceDep type alias exists"""
        assert AnalyticsServiceDep is not None

    def test_backup_service_dep_type(self):
        """Test BackupServiceDep type alias exists"""
        assert BackupServiceDep is not None

    def test_test_service_dep_type(self):
        """Test TestServiceDep type alias exists"""
        assert TestServiceDep is not None

    def test_health_service_dep_type(self):
        """Test HealthServiceDep type alias exists"""
        assert HealthServiceDep is not None
