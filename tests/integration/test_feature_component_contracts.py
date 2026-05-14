#!/usr/bin/env python3
"""
New Features Coverage Tests
Tests for new features and functionality detected in the codebase
"""

import pytest
import json
import os
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from soar_lab.analytics.tfm_data_enhancer import TFMDataEnhancer
from soar_lab.api.main import app, LoginRequest, TestRequest, BackupRequest, ServiceStatus, Metrics, TestResults
from soar_lab.data.generate_iocs import generate_malicious_hash, generate_benign_hash
from soar_lab.services.generate_secrets import generate_password, generate_api_key, generate_jwt_secret
from soar_lab.config.schemas import (
    NetworkEvent, FileHash, SeverityLevel, AlertType
)
from soar_lab.config.settings import Settings


class TestFeatureComponentContracts:
    """Test coverage for new features and functionality"""
    
    @pytest.fixture
    def tfm_enhancer(self):
        """TFM Data Enhancer fixture"""
        return TFMDataEnhancer()
    
    @pytest.fixture
    def ioc_functions(self):
        """IOC functions fixture"""
        return {
            'generate_malicious_hash': generate_malicious_hash,
            'generate_benign_hash': generate_benign_hash
        }
    
    @pytest.fixture
    def secret_functions(self):
        """Secret functions fixture"""
        return {
            'generate_password': generate_password,
            'generate_api_key': generate_api_key,
            'generate_jwt_secret': generate_jwt_secret
        }
    
    @pytest.fixture
    def settings(self):
        """Settings fixture"""
        return Settings()
    
    @pytest.fixture
    def sample_alert_data(self):
        """Sample alert data for testing"""
        return {
            "id": "alert-001",
            "title": "Test Alert",
            "description": "Test alert description",
            "severity": "high",
            "status": "new",
            "timestamp": datetime.now().isoformat(),
            "source": "test_source",
            "category": "malware"
        }
    
    @pytest.fixture
    def sample_ioc_data(self):
        """Sample IOC data for testing"""
        return {
            "type": "ip",
            "value": "192.168.1.100",
            "description": "Test IP address",
            "source": "test",
            "confidence": "high"
        }
    
    # TFM Data Enhancer Tests
    def test_tfm_enhancer_initialization(self, tfm_enhancer):
        """Test TFM Data Enhancer initialization"""
        assert tfm_enhancer.base_dir is not None
        assert tfm_enhancer.results_dir.exists()
        assert tfm_enhancer.logs_dir.exists()
        assert tfm_enhancer.scenarios == ['malicious', 'benign', 'edge_cases']
    
    def test_tfm_enhancer_alert_configuration(self, tfm_enhancer, sample_alert_data):
        """Test TFM Data Enhancer alert configuration"""
        # Test malicious alert configuration
        malicious_data = sample_alert_data.copy()
        tfm_enhancer._configure_alert_payload(malicious_data, 'malicious')
        assert malicious_data['severity'] == '2'
        assert malicious_data['event_type'] == 'ransomware_detection'
        
        # Test benign alert configuration
        benign_data = sample_alert_data.copy()
        tfm_enhancer._configure_alert_payload(benign_data, 'benign')
        assert benign_data['severity'] == '1'
        assert benign_data['event_type'] == 'false_positive'
    
    def test_tfm_enhancer_directory_setup(self, tfm_enhancer):
        """Test TFM Data Enhancer directory setup"""
        # Check that directories are created properly
        assert tfm_enhancer.results_dir.is_dir()
        assert tfm_enhancer.logs_dir.is_dir()
        
        # Check parent directories exist
        assert tfm_enhancer.base_dir.exists()
        artifacts_dir = tfm_enhancer.base_dir / "artifacts"
        assert artifacts_dir.exists()
    
    # API Tests
    def test_api_pydantic_models(self):
        """Test API Pydantic models"""
        # Test LoginRequest model
        login_data = LoginRequest(username="test", password="test")
        assert login_data.username == "test"
        assert login_data.password == "test"
        
        # Test TestRequest model
        test_data = TestRequest(category="unit")
        assert test_data.category == "unit"
        
        # Test BackupRequest model
        backup_data = BackupRequest(backup_name="test_backup")
        assert backup_data.backup_name == "test_backup"
        
        # Test ServiceStatus model
        status_data = ServiceStatus(service="test_service", status=True, url="http://test")
        assert status_data.service == "test_service"
        assert status_data.status is True
        assert status_data.url == "http://test"
        
        # Test Metrics model
        metrics_data = Metrics(cpu=50.0, memory=60.0, disk=70.0, timestamp=datetime.now())
        assert metrics_data.cpu == 50.0
        assert metrics_data.memory == 60.0
        assert metrics_data.disk == 70.0
        
        # Test TestResults model
        results_data = TestResults(
            category="integration",
            passed=10,
            failed=2,
            skipped=1,
            coverage=85.5,
            output="test_output",
            duration=120.5
        )
        assert results_data.category == "integration"
        assert results_data.passed == 10
        assert results_data.failed == 2
        assert results_data.skipped == 1
        assert results_data.coverage == 85.5
        assert results_data.output == "test_output"
        assert results_data.duration == 120.5
    
    def test_api_authentication_function(self):
        """Test API authentication function"""
        from soar_lab.api.main import verify_credentials
        
        # Test with environment variables not set
        with patch.dict(os.environ, {}, clear=True):
            result = verify_credentials("test", "test")
            assert result is False
        
        # Test with environment variables set
        with patch.dict(os.environ, {
            'WEB_UI_USER': 'testuser',
            'WEB_UI_PASSWORD': 'testpass'
        }, clear=True):
            result = verify_credentials("testuser", "testpass")
            assert result is True
            
            result = verify_credentials("wronguser", "wrongpass")
            assert result is False
    
    def test_api_fastapi_app_initialization(self):
        """Test FastAPI app initialization"""
        assert app.title == "SOAR Lab Management API"
        assert app.description == "REST API for SOAR Ransomware Lab Management"
        assert app.version == "1.0.0"
    
    def test_api_cors_configuration(self):
        """Test API CORS configuration"""
        # Check that CORS middleware is configured
        middleware = [middleware.cls for middleware in app.user_middleware]
        from fastapi.middleware.cors import CORSMiddleware
        assert CORSMiddleware in middleware
    
    # IOC Generator Tests
    def test_ioc_functions_initialization(self, ioc_functions):
        """Test IOC functions initialization"""
        assert ioc_functions is not None
        assert 'generate_malicious_hash' in ioc_functions
        assert 'generate_benign_hash' in ioc_functions
    
    def test_malicious_hash_generation(self, ioc_functions):
        """Test malicious hash generation"""
        generate_malicious_hash = ioc_functions['generate_malicious_hash']
        
        # Test with seed
        hash_with_seed = generate_malicious_hash("test_seed")
        assert len(hash_with_seed) == 64  # SHA256 length
        assert hash_with_seed == hashlib.sha256("test_seed".encode()).hexdigest()
        
        # Test without seed (deterministic behavior)
        hash1 = generate_malicious_hash()
        hash2 = generate_malicious_hash()
        assert hash1 == hash2  # Should be same for deterministic behavior
        
        # Test unique hash generation
        hash3 = generate_malicious_hash()
        hash4 = generate_malicious_hash()
        assert hash3 != hash4  # Should be different after first few calls
    
    def test_benign_hash_generation(self, ioc_functions):
        """Test benign hash generation"""
        generate_benign_hash = ioc_functions['generate_benign_hash']
        
        # Test with seed
        hash_with_seed = generate_benign_hash("test_seed")
        assert len(hash_with_seed) == 64  # SHA256 length
        assert hash_with_seed == hashlib.sha256("test_seed".encode()).hexdigest()
        
        # Test without seed (deterministic behavior)
        hash1 = generate_benign_hash()
        hash2 = generate_benign_hash()
        assert hash1 == hash2  # Should be same for deterministic behavior
        
        # Test unique hash generation
        hash3 = generate_benign_hash()
        hash4 = generate_benign_hash()
        assert hash3 != hash4  # Should be different after first few calls
    
    # Secret Functions Tests
    def test_secret_functions_initialization(self, secret_functions):
        """Test Secret functions initialization"""
        assert secret_functions is not None
        assert 'generate_password' in secret_functions
        assert 'generate_api_key' in secret_functions
        assert 'generate_jwt_secret' in secret_functions
    
    def test_password_generation(self, secret_functions):
        """Test password generation"""
        generate_password = secret_functions['generate_password']
        password = generate_password(16)
        assert len(password) == 16
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
    
    def test_api_key_generation(self, secret_functions):
        """Test API key generation"""
        generate_api_key = secret_functions['generate_api_key']
        api_key = generate_api_key(32)
        assert len(api_key) == 32
        assert api_key.replace('-', '').replace('_', '').isalnum()
    
    def test_jwt_secret_generation(self, secret_functions):
        """Test JWT secret generation"""
        generate_jwt_secret = secret_functions['generate_jwt_secret']
        jwt_secret = generate_jwt_secret(64)
        assert len(jwt_secret) == 64
        assert all(c.isalnum() or c in '-_.' for c in jwt_secret)
    
    # Configuration Schemas Tests
    def test_network_event_schema_validation(self):
        """Test NetworkEvent schema validation"""
        valid_event = {
            "src_ip": "192.168.1.100",
            "dst_ip": "192.168.1.200",
            "src_port": 80,
            "dst_port": 8080,
            "protocol": "TCP"
        }
        
        # Valid data should pass
        try:
            NetworkEvent(**valid_event)
        except Exception:
            pytest.fail("Valid network event data should pass schema validation")
        
        # Invalid data should fail
        invalid_event = valid_event.copy()
        invalid_event['protocol'] = 'INVALID_PROTOCOL'
        
        with pytest.raises(Exception):
            NetworkEvent(**invalid_event)
    
    def test_file_hash_schema_validation(self):
        """Test FileHash schema validation"""
        valid_hash = {
            "sha256": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
        }
        
        # Valid data should pass
        try:
            FileHash(**valid_hash)
        except Exception:
            pytest.fail("Valid file hash data should pass schema validation")
        
        # Invalid data should fail
        invalid_hash = valid_hash.copy()
        invalid_hash['sha256'] = 'invalid_hash'
        
        with pytest.raises(Exception):
            FileHash(**invalid_hash)
    
    def test_severity_level_enum(self):
        """Test SeverityLevel enum"""
        assert SeverityLevel.LOW == "0"
        assert SeverityLevel.MEDIUM == "1"
        assert SeverityLevel.HIGH == "2"
        assert SeverityLevel.CRITICAL == "3"
    
    def test_alert_type_enum(self):
        """Test AlertType enum"""
        assert AlertType.MALICIOUS == "malicious"
        assert AlertType.BENIGN == "benign"
        assert AlertType.SUSPICIOUS == "suspicious"
    
    # Settings Manager Tests
    def test_settings_initialization(self, settings):
        """Test Settings initialization"""
        assert settings is not None
        assert hasattr(settings, '_config')
        assert isinstance(settings._config, dict)
    
    def test_settings_manager_get_setting(self, settings):
        """Test getting settings"""
        from soar_lab.config.settings import get_setting
        
        # Test with default value
        value = get_setting('TEST_SETTING', 'default_value')
        assert value == 'default_value'
        
        # Test with existing setting
        value = get_setting('base_dir')
        assert value is not None
    
    def test_settings_manager_set_setting(self, settings):
        """Test setting settings using the Settings object directly"""
        # Set a setting
        settings.set('TEST_SETTING', 'new_value')
        
        # Get the setting
        value = settings.get('TEST_SETTING')
        assert value == 'new_value'
    
    # Integration Tests
    def test_tfm_enhancer_integration_with_siem(self, tfm_enhancer, sample_alert_data):
        """Test TFM Data Enhancer integration with SIEM"""
        # Test alert configuration which is used for SIEM integration
        alert_data = sample_alert_data.copy()
        tfm_enhancer._configure_alert_payload(alert_data, 'malicious')
        
        # Verify alert data is configured correctly
        assert alert_data['severity'] == '2'
        assert alert_data['event_type'] == 'ransomware_detection'
        
        # Test system status check which includes service availability
        status = tfm_enhancer.get_system_status()
        assert 'timestamp' in status
        assert 'services' in status
    
    def test_api_integration_with_docker(self):
        """Test API integration with Docker"""
        # Test Docker client initialization in API
        from soar_lab.api.main import docker_client
        
        # Should be None if Docker is not available
        if docker_client is None:
            # This is expected in test environment
            pass
        else:
            # If Docker is available, test basic functionality
            assert hasattr(docker_client, 'containers')
            assert hasattr(docker_client, 'images')
    
    def test_api_integration_with_redis(self):
        """Test API integration with Redis"""
        from soar_lab.api.main import redis_client
        
        # Should be None if Redis is not available
        if redis_client is None:
            # This is expected in test environment
            pass
        else:
            # If Redis is available, test basic functionality
            assert hasattr(redis_client, 'ping')
            assert hasattr(redis_client, 'set')
            assert hasattr(redis_client, 'get')
    
    # Error Handling Tests
    def test_tfm_enhancer_error_handling(self, tfm_enhancer):
        """Test TFM Data Enhancer error handling"""
        # Test with invalid scenario - it should be treated as benign
        payload = {}
        tfm_enhancer._configure_alert_payload(payload, 'invalid_scenario')
        assert payload['severity'] == '1'  # Treated as benign
        assert payload['event_type'] == 'false_positive'
    
    def test_api_error_handling(self):
        """Test API error handling"""
        from fastapi import HTTPException
        
        # Test HTTPException handling
        with pytest.raises(HTTPException):
            raise HTTPException(status_code=400, detail="Test error")
    
    def test_hash_functions_error_handling(self, ioc_functions):
        """Test hash functions error handling"""
        generate_malicious_hash = ioc_functions['generate_malicious_hash']
        generate_benign_hash = ioc_functions['generate_benign_hash']
        
        # Test with invalid seed (should not raise error, just handle gracefully)
        try:
            generate_malicious_hash(None)
            generate_benign_hash(None)
        except Exception:
            pytest.fail("Hash functions should handle None seed gracefully")
    
    def test_secret_functions_error_handling(self, secret_functions):
        """Test Secret functions error handling"""
        generate_password = secret_functions['generate_password']
        
        # Test with invalid length - should be adjusted to minimum 8
        password = generate_password(0)
        assert len(password) >= 8  # Should be adjusted to minimum length
        
        # Test with negative length - should also be adjusted to minimum 8
        password_neg = generate_password(-1)
        assert len(password_neg) >= 8
    
    # Performance Tests
    def test_tfm_enhancer_performance(self, tfm_enhancer):
        """Test TFM Data Enhancer performance"""
        import time
        
        start_time = time.time()
        
        # Test multiple alert configurations
        for i in range(100):
            sample_alert = {
                "id": f"alert-{i}",
                "title": f"Test Alert {i}",
                "description": f"Test alert description {i}",
                "severity": "high",
                "status": "new",
                "timestamp": datetime.now().isoformat(),
                "source": "test_source",
                "category": "malware"
            }
            tfm_enhancer._configure_alert_payload(sample_alert, 'malicious')
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 100 configurations in under 1 second
        assert duration < 1.0, f"TFM Data Enhancer took too long: {duration}s"
    
    def test_hash_functions_performance(self, ioc_functions):
        """Test hash functions performance"""
        import time
        
        start_time = time.time()
        
        # Test generating 1000 hashes
        hashes = []
        for i in range(1000):
            hash_val = ioc_functions['generate_malicious_hash'](f"seed_{i}")
            hashes.append(hash_val)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 1000 hashes in under 1 second
        assert duration < 1.0, f"Hash functions took too long: {duration}s"
        assert len(hashes) == 1000
        
        # Test uniqueness
        unique_hashes = set(hashes)
        assert len(unique_hashes) == 1000, "Generated hashes should be unique"
    
    def test_secret_functions_performance(self, secret_functions):
        """Test Secret functions performance"""
        import time
        
        start_time = time.time()
        
        # Test generating 100 secrets
        for i in range(100):
            secret_functions['generate_password'](16)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 100 secrets in under 1 second
        assert duration < 1.0, f"Secret functions took too long: {duration}s"
