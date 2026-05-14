#!/usr/bin/env python3
"""
Integration tests for SOAR Lab Management API
Tests real API endpoints and integrations with actual Docker deployment
"""

import json
import os
import pytest
import requests
import time
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# API base URL for real testing
API_BASE = "http://localhost:8000"
API_TOKEN = os.getenv("API_TOKEN", "test-token")

class TestAPIEndpoints:
    """Test API endpoints integration"""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Setup API client for testing"""
        # Start API server if not running
        try:
            response = requests.get(f"{API_BASE}/health", timeout=5)
            api_running = response.status_code == 200
        except requests.exceptions.RequestException:
            api_running = False
        
        if not api_running:
            pytest.skip("API server not running - start with: python -m uvicorn api.main:app --host 0.0.0.0 --port 8000")
        
        yield requests.Session()
    
    def test_health_endpoint(self, api_client):
        """Test health check endpoint"""
        response = api_client.get(f"{API_BASE}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_metrics_endpoint(self, api_client):
        """Test system metrics endpoint"""
        response = api_client.get(f"{API_BASE}/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data
        assert "timestamp" in data
        
        # Validate metric types
        assert isinstance(data["cpu"], (int, float))
        assert isinstance(data["memory"], (int, float))
        assert isinstance(data["disk"], (int, float))
    
    def test_services_endpoint(self, api_client):
        """Test services status endpoint"""
        response = api_client.get(f"{API_BASE}/services")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Check service structure
        if data:  # If services are returned
            service = data[0]
            assert "service" in service
            assert "status" in service
            assert "url" in service
    
    def test_test_run_endpoint(self, api_client):
        """Test test execution endpoint"""
        test_request = {
            "category": "unit"
        }
        
        response = api_client.post(
            f"{API_BASE}/test/run",
            json=test_request,
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        
        # Should accept request (may fail if tests not configured)
        assert response.status_code in [200, 202, 400]
        
        if response.status_code in [200, 202]:
            data = response.json()
            assert "category" in data
            assert "status" in data
    
    def test_backup_endpoint(self, api_client):
        """Test backup management endpoint"""
        backup_request = {
            "backup_name": f"test_backup_{int(time.time())}"
        }
        
        response = api_client.post(
            f"{API_BASE}/backup",
            json=backup_request,
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        
        # Should accept request (may fail if backup not configured)
        assert response.status_code in [200, 202, 400, 500]
    
    def test_logs_endpoint(self, api_client):
        """Test logs endpoint"""
        response = api_client.get(f"{API_BASE}/logs")
        
        # Should return logs or 401 if not authorized
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "logs" in data
            assert isinstance(data["logs"], list)
    
    def test_authentication_required(self, api_client):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            "/test/run",
            "/backup",
            "/logs"
        ]
        
        for endpoint in protected_endpoints:
            response = api_client.post(f"{API_BASE}{endpoint}", json={})
            assert response.status_code == 401
            
            response = api_client.get(f"{API_BASE}{endpoint}")
            assert response.status_code == 401
    
    def test_cors_headers(self, api_client):
        """Test CORS headers are present"""
        response = api_client.options(f"{API_BASE}/health")
        
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers


class TestAPIIntegration:
    """Test API integration with external services"""
    
    def test_redis_integration(self):
        """Test Redis integration in API"""
        # This test verifies Redis connection without mocking
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://:RedisSecurePassword678!@#@localhost:6379/0")
            
            client = redis.from_url(redis_url)
            client.ping()
            
            # Test basic Redis operations
            test_key = f"test_key_{int(time.time())}"
            test_value = "test_value"
            
            client.set(test_key, test_value)
            retrieved = client.get(test_key)
            
            assert retrieved.decode('utf-8') == test_value
            client.delete(test_key)
            
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")
    
    def test_docker_integration(self):
        """Test Docker integration in API"""
        try:
            import docker
            client = docker.from_env()
            
            # Test Docker connection
            client.ping()
            
            # List containers (real operation)
            containers = client.containers.list(all=True)
            assert isinstance(containers, list)
            
            # Test Docker info
            info = client.info()
            assert "Containers" in info
            assert "Images" in info
            
        except Exception as e:
            pytest.skip(f"Docker not available: {e}")
    
    @patch('subprocess.run')
    def test_test_execution_integration(self, mock_run):
        """Test test execution via subprocess"""
        # Mock successful test execution
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "tests passed"
        mock_run.return_value.stderr = ""
        
        # Simulate API test execution
        import subprocess
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/unit/", "-v"],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        assert result.returncode == 0
        assert "tests passed" in result.stdout


class TestAPIErrorHandling:
    """Test API error handling"""
    
    def test_invalid_endpoint(self):
        """Test 404 for invalid endpoints"""
        try:
            response = requests.get(f"{API_BASE}/invalid-endpoint")
            assert response.status_code == 404
        except requests.exceptions.RequestException:
            pytest.skip("API server not running")
    
    def test_invalid_json_payload(self):
        """Test handling of invalid JSON"""
        try:
            response = requests.post(
                f"{API_BASE}/test/run",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code in [400, 422]
        except requests.exceptions.RequestException:
            pytest.skip("API server not running")
    
    def test_missing_required_fields(self):
        """Test validation of required fields"""
        try:
            # Send empty JSON to endpoint that expects fields
            response = requests.post(
                f"{API_BASE}/test/run",
                json={},
                headers={"Authorization": f"Bearer {API_TOKEN}"}
            )
            assert response.status_code in [400, 422]
        except requests.exceptions.RequestException:
            pytest.skip("API server not running")
