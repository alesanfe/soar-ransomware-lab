#!/usr/bin/env python3
"""
Unit tests for health_service.py
"""

import pytest
from unittest.mock import Mock, AsyncMock

from soar_lab.services.health_service import HealthService


class TestHealthService:
    """Test HealthService with mocked dependencies"""

    def test_initialization_success(self):
        """Test successful initialization"""
        mock_health_checker = Mock()
        mock_metrics = Mock()

        service = HealthService(health_checker=mock_health_checker, system_metrics=mock_metrics)

        assert service.health_checker == mock_health_checker
        assert service.system_metrics == mock_metrics

    def test_get_system_metrics(self):
        """Test get_system_metrics delegates to system_metrics"""
        mock_health_checker = Mock()
        mock_metrics = Mock()
        mock_metrics.get_hardware_metrics.return_value = {
            'cpu': {'percent': 50},
            'memory': {'percent': 75}
        }

        service = HealthService(health_checker=mock_health_checker, system_metrics=mock_metrics)
        result = service.get_system_metrics()

        mock_metrics.get_hardware_metrics.assert_called_once()
        assert result['cpu']['percent'] == 50

    @pytest.mark.asyncio
    async def test_check_service_no_url(self):
        """Test service check with no URL configured"""
        mock_health_checker = Mock()
        mock_health_checker.check_service = AsyncMock(return_value=False)
        mock_metrics = Mock()
        service = HealthService(health_checker=mock_health_checker, system_metrics=mock_metrics)

        result = await service.check_service("test_service", {})

        assert result is False
        mock_health_checker.check_service.assert_called_once_with("test_service", None)

    @pytest.mark.asyncio
    async def test_check_service_with_url(self):
        """Test service check with URL"""
        mock_health_checker = Mock()
        mock_health_checker.check_service = AsyncMock(return_value=True)
        mock_metrics = Mock()
        service = HealthService(health_checker=mock_health_checker, system_metrics=mock_metrics)

        result = await service.check_service("test_service", {"url": "http://localhost:8080"})

        assert result is True
        mock_health_checker.check_service.assert_called_once_with("test_service", "http://localhost:8080")

    @pytest.mark.asyncio
    async def test_get_all_services_status(self):
        """Test getting all services status"""
        mock_health_checker = Mock()
        mock_health_checker.check_service = AsyncMock(side_effect=[True, False])
        mock_metrics = Mock()
        service = HealthService(health_checker=mock_health_checker, system_metrics=mock_metrics)

        services_config = {
            "service1": {"url": "http://localhost:8080"},
            "service2": {"url": "http://localhost:8081"}
        }

        result = await service.get_all_services_status(services_config)

        assert result["service1"] is True
        assert result["service2"] is False

    @pytest.mark.asyncio
    async def test_get_all_services_status_exception(self):
        """Test getting all services status with exception"""
        mock_health_checker = Mock()
        mock_health_checker.check_service = AsyncMock(side_effect=Exception("Check failed"))
        mock_metrics = Mock()
        service = HealthService(health_checker=mock_health_checker, system_metrics=mock_metrics)

        result = await service.get_all_services_status({"service1": {"url": "http://localhost:8080"}})

        assert result["service1"] is False

    @pytest.mark.asyncio
    async def test_get_all_services_status_with_soar_clients(self):
        """Test getting all services status with SOAR clients"""
        mock_health_checker = Mock()
        mock_health_checker.check_service = AsyncMock(return_value=True)
        mock_metrics = Mock()

        mock_client = Mock()
        mock_client.health_check.return_value = True

        service = HealthService(
            health_checker=mock_health_checker,
            system_metrics=mock_metrics,
            soar_clients={"thehive": mock_client}
        )

        result = await service.get_all_services_status({})

        assert result["thehive"] is True
        mock_client.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_services_status_with_soar_clients_exception(self):
        """Test getting all services status with SOAR clients that raise exception"""
        mock_health_checker = Mock()
        mock_health_checker.check_service = AsyncMock(return_value=True)
        mock_metrics = Mock()

        mock_client = Mock()
        mock_client.health_check.side_effect = Exception("Client check failed")

        service = HealthService(
            health_checker=mock_health_checker,
            system_metrics=mock_metrics,
            soar_clients={"thehive": mock_client}
        )

        result = await service.get_all_services_status({})

        assert result["thehive"] is False

    def test_get_system_metrics_exception(self):
        """Test get_system_metrics raises exception on error"""
        mock_health_checker = Mock()
        mock_metrics = Mock()
        mock_metrics.get_hardware_metrics.side_effect = Exception("Metrics error")

        service = HealthService(health_checker=mock_health_checker, system_metrics=mock_metrics)

        with pytest.raises(Exception, match="Metrics error"):
            service.get_system_metrics()
