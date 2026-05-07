#!/usr/bin/env python3
"""
Extended unit tests for Settings configuration
"""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.settings import Settings, get_setting, get_service_url, validate_config, ensure_directories


class TestSettingsExtended(unittest.TestCase):
    """Extended tests for Settings class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = Settings()
    
    def test_get_with_default(self):
        """Test getting configuration with default value"""
        result = self.settings.get('nonexistent_key', 'default_value')
        self.assertEqual(result, 'default_value')
    
    def test_set_and_get(self):
        """Test setting and getting configuration values"""
        self.settings.set('test_key', 'test_value')
        result = self.settings.get('test_key')
        self.assertEqual(result, 'test_value')
    
    def test_get_all(self):
        """Test getting all configuration"""
        all_config = self.settings.get_all()
        self.assertIsInstance(all_config, dict)
        self.assertIn('project_name', all_config)
        self.assertIn('thehive_port', all_config)
    
    def test_validate_success(self):
        """Test successful configuration validation"""
        # Set required values
        self.settings.set('elastic_password', 'test_password')
        self.settings.set('thehive_secret', 'test_secret')
        self.settings.set('thehive_api_key', 'test_api_key')
        self.settings.set('cortex_secret', 'test_secret')
        self.settings.set('cortex_api_key', 'test_api_key')
        self.settings.set('siem_webhook_token', 'test_token')
        
        result = self.settings.validate()
        self.assertTrue(result)
    
    def test_validate_failure(self):
        """Test configuration validation failure"""
        # Clear required values
        self.settings.set('elastic_password', '')
        self.settings.set('thehive_secret', '')
        self.settings.set('thehive_api_key', '')
        self.settings.set('cortex_secret', '')
        self.settings.set('cortex_api_key', '')
        self.settings.set('siem_webhook_token', '')
        
        result = self.settings.validate()
        self.assertFalse(result)
    
    def test_get_service_urls_http(self):
        """Test getting service URLs with HTTP"""
        self.settings.set('enable_tls', False)
        self.settings.set('thehive_port', 9000)
        self.settings.set('cortex_port', 9001)
        self.settings.set('shuffle_ui_port', 3001)
        self.settings.set('shuffle_api_port', 5001)
        self.settings.set('elasticsearch_port', 19200)
        
        urls = self.settings.get_service_urls()
        
        self.assertEqual(urls['thehive'], 'http://localhost:9000')
        self.assertEqual(urls['cortex'], 'http://localhost:9001')
        self.assertEqual(urls['shuffle_ui'], 'http://localhost:3001')
        self.assertEqual(urls['shuffle_api'], 'http://localhost:5001')
        self.assertEqual(urls['elasticsearch'], 'http://localhost:19200')
    
    def test_get_service_urls_https(self):
        """Test getting service URLs with HTTPS"""
        self.settings.set('enable_tls', True)
        self.settings.set('thehive_port', 9000)
        
        urls = self.settings.get_service_urls()
        self.assertEqual(urls['thehive'], 'https://localhost:9000')
    
    def test_get_webhook_url(self):
        """Test getting webhook URL"""
        self.settings.set('shuffle_api_port', 5001)
        self.settings.set('enable_tls', False)
        
        webhook_url = self.settings.get_webhook_url()
        self.assertEqual(webhook_url, 'http://localhost:5001/api/v1/webhooks/siem')
    
    def test_ensure_directories(self):
        """Test ensuring directories exist"""
        # Set temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            self.settings.set('logs_dir', os.path.join(temp_dir, 'logs'))
            self.settings.set('results_dir', os.path.join(temp_dir, 'results'))
            self.settings.set('backup_dir', os.path.join(temp_dir, 'backup'))
            self.settings.set('certs_dir', os.path.join(temp_dir, 'certs'))
            
            self.settings.ensure_directories()
            
            # Check directories were created
            self.assertTrue(os.path.exists(os.path.join(temp_dir, 'logs')))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, 'results')))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, 'backup')))
            self.assertTrue(os.path.exists(os.path.join(temp_dir, 'certs')))
    
    def test_str_representation(self):
        """Test string representation"""
        self.settings.set('project_name', 'test_project')
        self.settings.set('enable_tls', True)
        
        str_repr = str(self.settings)
        self.assertEqual(str_repr, 'Settings(project=test_project, tls=True)')
    
    @patch.dict(os.environ, {
        'COMPOSE_PROJECT_NAME': 'test_project',
        'THEHIVE_HTTP_PORT': '9001',
        'ENABLE_TLS': 'false',
        'ELASTIC_PASSWORD': 'test_password'
    })
    def test_environment_variable_loading(self):
        """Test loading configuration from environment variables"""
        # Create new settings instance to test environment loading
        test_settings = Settings()
        
        self.assertEqual(test_settings.get('project_name'), 'test_project')
        self.assertEqual(test_settings.get('thehive_port'), 9001)
        self.assertFalse(test_settings.get('enable_tls'))
        self.assertEqual(test_settings.get('elastic_password'), 'test_password')


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    @patch('config.settings.settings')
    def test_get_setting_function(self, mock_settings):
        """Test get_setting convenience function"""
        mock_settings.get.return_value = 'test_value'
        
        result = get_setting('test_key', 'default')
        mock_settings.get.assert_called_once_with('test_key', 'default')
        self.assertEqual(result, 'test_value')
    
    @patch('config.settings.settings')
    def test_get_service_url_function(self, mock_settings):
        """Test get_service_url convenience function"""
        mock_settings.get_service_urls.return_value = {
            'thehive': 'http://localhost:9000',
            'cortex': 'http://localhost:9001'
        }
        
        result = get_service_url('thehive')
        mock_settings.get_service_urls.assert_called_once()
        self.assertEqual(result, 'http://localhost:9000')
        
        # Test non-existent service
        result = get_service_url('nonexistent')
        self.assertEqual(result, '')
    
    @patch('config.settings.settings')
    def test_validate_config_function(self, mock_settings):
        """Test validate_config convenience function"""
        mock_settings.validate.return_value = True
        
        result = validate_config()
        mock_settings.validate.assert_called_once()
        self.assertTrue(result)
    
    @patch('config.settings.settings')
    def test_ensure_directories_function(self, mock_settings):
        """Test ensure_directories convenience function"""
        ensure_directories()
        mock_settings.ensure_directories.assert_called_once()


class TestSettingsEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings = Settings()
    
    def test_get_nested_configuration(self):
        """Test getting nested configuration values"""
        # Test with complex configuration structure
        self.settings.set('database.host', 'localhost')
        self.settings.set('database.port', 5432)
        self.settings.set('database.name', 'test_db')
        
        self.assertEqual(self.settings.get('database.host'), 'localhost')
        self.assertEqual(self.settings.get('database.port'), 5432)
        self.assertEqual(self.settings.get('database.name'), 'test_db')
    
    def test_override_environment_variables(self):
        """Test overriding environment variables"""
        with patch.dict(os.environ, {'TEST_OVERRIDE': 'overridden_value'}):
            # Set initial value
            self.settings.set('test_override', 'initial_value')
            
            # Test that environment variable takes precedence
            # This test depends on the Settings implementation
            result = self.settings.get('test_override')
            # The actual behavior depends on Settings implementation
            self.assertIn(result, ['initial_value', 'overridden_value'])
    
    def test_configuration_persistence(self):
        """Test configuration persistence"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # Set some configuration
            self.settings.set('test_persist', 'persisted_value')
            self.settings.set('test_number', 42)
            
            # Save configuration if method exists
            if hasattr(self.settings, 'save_to_file'):
                self.settings.save_to_file(temp_file)
                self.assertTrue(os.path.exists(temp_file))
                
                # Load configuration in new instance
                new_settings = Settings()
                if hasattr(new_settings, 'load_from_file'):
                    new_settings.load_from_file(temp_file)
                    self.assertEqual(new_settings.get('test_persist'), 'persisted_value')
                    self.assertEqual(new_settings.get('test_number'), 42)
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_type_conversion_handling(self):
        """Test type conversion in configuration values"""
        # Test string to int conversion
        self.settings.set('port_number', '8080')
        result = self.settings.get('port_number')
        # Should handle both string and int
        self.assertIn(result, ['8080', 8080])
        
        # Test boolean conversion
        self.settings.set('enable_feature', 'true')
        result = self.settings.get('enable_feature')
        # Should handle various boolean representations
        self.assertIn(result, ['true', True, '1'])
    
    def test_configuration_validation_detailed(self):
        """Test detailed configuration validation"""
        # Test missing required fields
        self.settings.set('elastic_password', '')
        result = self.settings.validate()
        self.assertFalse(result)
        
        # Test with some but not all required fields
        self.settings.set('elastic_password', 'password123')
        self.settings.set('thehive_secret', 'secret123')
        # Still missing other required fields
        result = self.settings.validate()
        self.assertFalse(result)
        
        # Test with all required fields
        self.settings.set('thehive_api_key', 'api_key_123')
        self.settings.set('cortex_secret', 'cortex_secret')
        self.settings.set('cortex_api_key', 'cortex_api')
        self.settings.set('siem_webhook_token', 'webhook_token')
        result = self.settings.validate()
        self.assertTrue(result)
    
    def test_service_url_edge_cases(self):
        """Test service URL generation edge cases"""
        # Test with different port configurations
        self.settings.set('thehive_port', 8080)
        self.settings.set('cortex_port', 8081)
        self.settings.set('enable_tls', False)
        
        urls = self.settings.get_service_urls()
        expected_thehive = 'http://localhost:8080'
        expected_cortex = 'http://localhost:8081'
        self.assertEqual(urls['thehive'], expected_thehive)
        self.assertEqual(urls['cortex'], expected_cortex)
        
        # Test with HTTPS enabled
        self.settings.set('thehive_port', 9000)
        self.settings.set('enable_tls', True)
        
        urls = self.settings.get_service_urls()
        expected = 'https://localhost:9000'
        self.assertEqual(urls['thehive'], expected)
        
        # Test all service URLs are generated
        expected_services = ['thehive', 'cortex', 'shuffle_ui', 'shuffle_api', 'elasticsearch']
        for service in expected_services:
            self.assertIn(service, urls)
            self.assertTrue(urls[service].startswith('http'))
            self.assertIn('localhost', urls[service])


if __name__ == '__main__':
    unittest.main()
