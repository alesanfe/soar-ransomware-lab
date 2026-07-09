#!/usr/bin/env python3
"""
Unit tests for cortex_client.py
"""

import pytest
from unittest.mock import Mock, patch

from soar_lab.integrations.cortex_client import CortexClient


class TestCortexClient:
    """Test CortexClient"""

    def test_initialization_with_base_url_and_api_key(self):
        """Test initialization with base_url and api_key"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        assert "Authorization" in client._session.headers

    def test_initialization_with_config_provider(self):
        """Test initialization with config_provider"""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default=None: {
            'cortex_url': 'http://localhost:9001',
            'cortex_api_key': 'test-key'
        }.get(key, default)

        client = CortexClient(base_url=None, api_key=None, config_provider=mock_config)
        assert "Authorization" in client._session.headers

    def test_initialization_without_url_raises(self):
        """Test initialization without url raises ValueError"""
        with pytest.raises(ValueError, match="cortex_url must be provided"):
            CortexClient(base_url=None, api_key="test-key")

    def test_initialization_without_api_key_raises(self):
        """Test initialization without api_key raises ValueError"""
        with pytest.raises(ValueError, match="cortex_api_key must be provided"):
            CortexClient(base_url="http://localhost:9001", api_key=None)

    def test_default_headers(self):
        """Test _default_headers returns correct headers"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        headers = client._default_headers("custom-key")
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    def test_list_analyzers(self):
        """Test listing analyzers"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.post = Mock(return_value=[{"id": "1", "name": "VirusTotal"}])

        result = client.list_analyzers()
        assert result == [{"id": "1", "name": "VirusTotal"}]

    def test_list_analyzers_returns_empty_on_invalid(self):
        """Test list_analyzers returns empty list on invalid response"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.post = Mock(return_value={"error": "not a list"})

        result = client.list_analyzers()
        assert result == []

    def test_run_analyzer(self):
        """Test running an analyzer"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.post = Mock(return_value={"id": "job-123", "status": "InProgress"})

        result = client.run_analyzer("VirusTotal_3_1", "hash", "abc123")
        assert result == {"id": "job-123", "status": "InProgress"}

    def test_get_job(self):
        """Test getting a job status"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.get = Mock(return_value={"id": "job-123", "status": "Success"})

        result = client.get_job("job-123")
        assert result == {"id": "job-123", "status": "Success"}

    def test_get_job_report(self):
        """Test getting a job report"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.get = Mock(return_value={"id": "job-123", "report": {"summary": "malicious"}})

        result = client.get_job_report("job-123")
        assert result == {"id": "job-123", "report": {"summary": "malicious"}}

    def test_list_jobs(self):
        """Test listing jobs"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.get = Mock(return_value=[{"id": "job-1"}, {"id": "job-2"}])

        result = client.list_jobs()
        assert result == [{"id": "job-1"}, {"id": "job-2"}]

    def test_list_jobs_with_params(self):
        """Test listing jobs with custom start and count"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.get = Mock(return_value=[{"id": "job-1"}])

        result = client.list_jobs(start=10, count=5)
        assert result == [{"id": "job-1"}]

    def test_list_jobs_returns_empty_on_invalid(self):
        """Test list_jobs returns empty list on invalid response"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.get = Mock(return_value={"error": "not a list"})

        result = client.list_jobs()
        assert result == []

    def test_list_analyzers_by_type(self):
        """Test listing analyzers by data type"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.list_analyzers = Mock(return_value=[
            {"id": "1", "name": "VirusTotal", "dataTypeList": ["hash", "ip"]},
            {"id": "2", "name": "Whois", "dataTypeList": ["domain"]}
        ])

        result = client.list_analyzers_by_type("hash")
        assert result == [{"id": "1", "name": "VirusTotal", "dataTypeList": ["hash", "ip"]}]

    def test_list_analyzers_by_type_empty(self):
        """Test list_analyzers_by_type returns empty when no match"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.list_analyzers = Mock(return_value=[
            {"id": "1", "name": "VirusTotal", "dataTypeList": ["hash", "ip"]}
        ])

        result = client.list_analyzers_by_type("domain")
        assert result == []

    def test_wait_for_job_success(self):
        """Test wait_for_job returns when job succeeds"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.get_job = Mock(return_value={"id": "job-123", "status": "Success"})

        result = client.wait_for_job("job-123", timeout=10, poll_interval=1)
        assert result == {"id": "job-123", "status": "Success"}

    def test_wait_for_job_failure(self):
        """Test wait_for_job returns when job fails"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.get_job = Mock(return_value={"id": "job-123", "status": "Failure"})

        result = client.wait_for_job("job-123", timeout=10, poll_interval=1)
        assert result == {"id": "job-123", "status": "Failure"}

    def test_wait_for_job_timeout(self):
        """Test wait_for_job returns current job on timeout"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.get_job = Mock(return_value={"id": "job-123", "status": "InProgress"})

        with patch('time.time', side_effect=[0, 100]):  # Simulate timeout
            result = client.wait_for_job("job-123", timeout=10, poll_interval=1)
            assert result == {"id": "job-123", "status": "InProgress"}

    def test_health_check(self):
        """Test health check returns True when successful"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.get = Mock(return_value={"status": "ok"})

        result = client.health_check()
        assert result is True

    def test_health_check_exception(self):
        """Test health check returns False on exception"""
        client = CortexClient(base_url="http://localhost:9001", api_key="test-key")
        client.get = Mock(side_effect=Exception("Error"))

        result = client.health_check()
        assert result is False
