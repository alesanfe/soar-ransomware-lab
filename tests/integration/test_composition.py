#!/usr/bin/env python3
"""
Unit tests for api/composition.py
Tests composition root and dependency injection
"""

import pytest
from soar_lab.api.composition import create_app
from unittest.mock import Mock, patch


class TestCreateApp:
    """Test create_app factory function"""

    @patch('soar_lab.api.composition.CompositionRoot')
    def test_create_app_factory(self, mock_composition_root):
        """Test create_app factory function"""
        mock_app = Mock()
        mock_composition_instance = Mock()
        mock_composition_instance.create_fastapi_app.return_value = mock_app
        mock_composition_root.return_value = mock_composition_instance

        app = create_app()

        assert app == mock_app
        mock_composition_root.assert_called_once()
        mock_composition_instance.create_fastapi_app.assert_called_once()
