#!/usr/bin/env python3
"""
Unit tests for path_service.py
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from soar_lab.infrastructure.path_service import PathService


class TestPathService:
    """Test PathService infrastructure adapter"""

    def test_initialization_with_base_dir(self):
        """Test initialization with base_dir parameter"""
        base_dir = Path("/test/base")
        service = PathService(base_dir=base_dir)
        
        assert service.base_dir == base_dir

    @patch.dict('os.environ', {'BASE_DIR': '/env/base'})
    def test_initialization_with_env_var(self):
        """Test initialization with BASE_DIR environment variable"""
        service = PathService()
        
        assert service.base_dir == Path("/env/base")

    @patch.dict('os.environ', {}, clear=True)
    def test_initialization_without_base_dir_raises_error(self):
        """Test initialization without base_dir raises ValueError"""
        with pytest.raises(ValueError, match="base_dir must be provided"):
            PathService()

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider"""
        mock_config = Mock()
        mock_config.get.return_value = "/config/base"
        service = PathService(config_provider=mock_config)
        
        assert service.base_dir == Path("/config/base")

    @patch.dict('os.environ', {'BASE_DIR': '/env/base'})
    def test_initialization_config_provider_fallback_to_env(self):
        """Test initialization with config_provider that returns None falls back to env"""
        mock_config = Mock()
        mock_config.get.return_value = None
        service = PathService(config_provider=mock_config)
        
        assert service.base_dir == Path("/env/base")

    def test_artifacts_dir_property(self):
        """Test artifacts_dir property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default  # Return default value
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.artifacts_dir == base_dir / "artifacts"

    def test_artifacts_dir_property_with_config(self):
        """Test artifacts_dir property with config override"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: "/custom/artifacts" if key == "artifacts_dir" else default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.artifacts_dir == Path("/custom/artifacts")

    def test_logs_dir_property(self):
        """Test logs_dir property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.logs_dir == base_dir / "artifacts" / "logs"

    def test_results_dir_property(self):
        """Test results_dir property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.results_dir == base_dir / "artifacts" / "results"

    def test_coverage_dir_property(self):
        """Test coverage_dir property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.coverage_dir == base_dir / "artifacts" / "coverage"

    def test_coverage_file_property(self):
        """Test coverage_file property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.coverage_file == base_dir / "artifacts" / "coverage" / "coverage.json"

    def test_backup_dir_property(self):
        """Test backup_dir property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.backup_dir == base_dir / "artifacts" / "backups"

    def test_schemas_dir_property(self):
        """Test schemas_dir property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.schemas_dir == base_dir / "schemas"

    def test_scripts_dir_property(self):
        """Test scripts_dir property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.scripts_dir == base_dir / "scripts"

    def test_docker_dir_property(self):
        """Test docker_dir property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.docker_dir == base_dir / "infra" / "docker"

    def test_notify_log_file_property(self):
        """Test notify_log_file property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.notify_log_file == base_dir / "artifacts" / "logs" / "notify.log"

    def test_kpi_file_property(self):
        """Test kpi_file property"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        assert service.kpi_file == base_dir / "artifacts" / "results" / "kpis.csv"

    @patch('pathlib.Path.mkdir')
    def test_ensure_directories(self, mock_mkdir):
        """Test ensure_directories creates all directories"""
        base_dir = Path("/test/base")
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: default
        service = PathService(base_dir=base_dir, config_provider=mock_config)
        
        service.ensure_directories()
        
        # Should call mkdir for each directory
        assert mock_mkdir.call_count == 5
