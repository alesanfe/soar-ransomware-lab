"""Unit tests for api.composition module."""

import pytest
from pathlib import Path
from soar_lab.api.composition import CompositionRoot, create_app
from unittest.mock import Mock, patch


class TestCompositionRoot:
    """Tests for CompositionRoot class."""

    def test_composition_root_init_missing_base_dir(self):
        """Test CompositionRoot raises ValueError when base_dir is not provided."""
        with patch('soar_lab.interfaces.api.composition.create_settings') as mock_settings:
            mock_settings.return_value = {}
            with patch('soar_lab.interfaces.api.composition.InfrastructureConfigProvider') as mock_config_provider:
                mock_config = Mock()
                mock_config.get.return_value = None  # base_dir is None
                mock_config_provider.return_value = mock_config

                with pytest.raises(ValueError):
                    CompositionRoot()


class TestCreateApp:
    """Tests for create_app factory function."""

    @pytest.mark.skip(reason="Requires complex mocking of composition root - revisit")
    def test_create_app_returns_fastapi(self):
        """Test create_app returns FastAPI instance."""
        with patch('soar_lab.interfaces.api.composition.CompositionRoot') as mock_composition_root:
            mock_composition = Mock()
            mock_app = Mock()
            mock_composition.create_fastapi_app.return_value = mock_app
            mock_composition_root.return_value = mock_composition

            app = create_app()

            assert app == mock_app
