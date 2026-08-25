#!/usr/bin/env python3
"""Unit tests for calc_kpis module."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.data.calc_kpis import _fetch_mttr_from_es


class TestFetchMTTRFromES:
    """Tests for _fetch_mttr_from_es function."""

    @patch("requests.get")
    def test_fetch_mttr_from_es_success(self, mock_get):
        """Test successful fetch of MTTR values from Elasticsearch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"mttr_seconds": 120.5}},
                    {"_source": {"mttr_seconds": 90.0}},
                    {"_source": {"mttr_seconds": 150.0}},
                ]
            }
        }
        mock_get.return_value = mock_response

        result = _fetch_mttr_from_es("http://localhost:9200", "elastic", "password")

        assert result == [120.5, 90.0, 150.0]
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_fetch_mttr_from_es_filters_invalid_values(self, mock_get):
        """Test that invalid MTTR values are filtered out."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"mttr_seconds": 120.5}},
                    {"_source": {"mttr_seconds": 0}},  # Invalid: 0
                    {"_source": {"mttr_seconds": 4000}},  # Invalid: > 3600
                    {"_source": {"mttr_seconds": "invalid"}},  # Invalid: string
                    {"_source": {"mttr_seconds": 90.0}},
                ]
            }
        }
        mock_get.return_value = mock_response

        result = _fetch_mttr_from_es("http://localhost:9200", "elastic", "password")

        assert result == [120.5, 90.0]

    @patch("requests.get")
    def test_fetch_mttr_from_es_empty_response(self, mock_get):
        """Test handling of empty Elasticsearch response."""
        mock_response = Mock()
        mock_response.json.return_value = {"hits": {"hits": []}}
        mock_get.return_value = mock_response

        result = _fetch_mttr_from_es("http://localhost:9200", "elastic", "password")

        assert result == []

    @patch("requests.get")
    def test_fetch_mttr_from_es_request_error(self, mock_get):
        """Test handling of request errors."""
        mock_get.side_effect = Exception("Connection error")

        result = _fetch_mttr_from_es("http://localhost:9200", "elastic", "password")

        assert result == []

    @patch("requests.get")
    def test_fetch_mttr_from_es_no_auth(self, mock_get):
        """Test fetch without authentication."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {"_source": {"mttr_seconds": 120.5}},
                ]
            }
        }
        mock_get.return_value = mock_response

        result = _fetch_mttr_from_es("http://localhost:9200", None, None)

        assert result == [120.5]
        # Verify no auth was passed
        call_args = mock_get.call_args
        assert call_args[1]["auth"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
