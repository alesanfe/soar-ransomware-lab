#!/usr/bin/env python3
"""
Tests for generate_secrets module
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from soar_lab.services.generate_secrets import (
    generate_api_key, generate_jwt_secret, generate_password, 
    generate_secret_key, generate_token, generate_webhook_token,
    generate_all_secrets, validate_secret_format, main
)


class TestGenerateSecrets:
    """Test secret generation functions"""
    
    def test_generate_api_key_default(self):
        """Test API key generation with default length"""
        api_key = generate_api_key()
        assert isinstance(api_key, str)
        assert len(api_key) == 32  # Default length
        # Should contain only alphanumeric characters
        assert api_key.isalnum()
    
    def test_generate_api_key_custom_length(self):
        """Test API key generation with custom length"""
        api_key = generate_api_key(16)
        assert isinstance(api_key, str)
        # The implementation forces minimum 21 chars (7*3)
        assert len(api_key) >= 16
        assert api_key.isalnum()
    
    def test_generate_jwt_secret_default(self):
        """Test JWT secret generation"""
        jwt_secret = generate_jwt_secret()
        assert isinstance(jwt_secret, str)
        assert len(jwt_secret) == 64  # Default length
        # JWT secrets are alphanumeric only (no special chars)
        assert any(c.isupper() for c in jwt_secret)
        assert any(c.islower() for c in jwt_secret)
        assert any(c.isdigit() for c in jwt_secret)
    
    def test_generate_password_default_length(self):
        """Test password generation with default length"""
        password = generate_password()
        assert isinstance(password, str)
        assert len(password) == 32  # Default length
        # Should contain uppercase, lowercase, digits, and special chars
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    def test_generate_password_custom_length(self):
        """Test password generation with custom length"""
        password = generate_password(24)
        assert isinstance(password, str)
        assert len(password) == 24
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    def test_generate_secret_key_default(self):
        """Test secret key generation"""
        secret_key = generate_secret_key()
        assert isinstance(secret_key, str)
        assert len(secret_key) == 32  # Default length
        # Should be hexadecimal
        assert all(c in "0123456789abcdef" for c in secret_key.lower())
    
    def test_generate_token_default(self):
        """Test token generation"""
        token = generate_token()
        assert isinstance(token, str)
        assert len(token) == 48  # Default length
        # URL-safe tokens should be alphanumeric with some special chars
        assert all(c.isalnum() or c in "-_" for c in token)
    
    def test_generate_webhook_token_default(self):
        """Test webhook token generation"""
        webhook_token = generate_webhook_token()
        assert isinstance(webhook_token, str)
        assert len(webhook_token) == 64  # Default length
        assert webhook_token.isalnum()
    
    def test_generate_all_secrets(self):
        """Test generating all secrets at once"""
        secrets = generate_all_secrets()
        assert isinstance(secrets, dict)
        
        # Check all required keys are present
        required_keys = [
            'thehive_api_key', 'cortex_api_key', 'shuffle_api_key', 
            'shuffle_webhook_token', 'jwt_secret'
        ]
        for key in required_keys:
            assert key in secrets
            assert isinstance(secrets[key], str)
            assert len(secrets[key]) > 0
    
    def test_generate_all_secrets_uniqueness(self):
        """Test that generated secrets are unique"""
        secrets1 = generate_all_secrets()
        secrets2 = generate_all_secrets()
        
        # Should be different each time
        assert secrets1 != secrets2
        
        # Each individual secret should be different
        for key in secrets1:
            assert secrets1[key] != secrets2[key]
    
    def test_validate_secret_format_valid(self):
        """Test secret format validation with valid secrets"""
        # Test valid API key (12 chars to pass validation)
        assert validate_secret_format("abc123def456", 12, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        
        # Test valid JWT secret (64 chars, alphanumeric only)
        jwt_test = "MyJWTSecret12345678901234567890123456789012345678901234567890123"
        assert validate_secret_format(jwt_test, 64, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        
        # Test valid password (12 chars to pass validation)
        assert validate_secret_format("MyPass123!@#", 12, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?")
        
        # Test valid secret key
        assert validate_secret_format("abcdef1234567890abcdef1234567890", 32, "0123456789abcdef")
        
        # Test valid token
        assert validate_secret_format("abc123-def456_ghi789", 20, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        
        # Test valid webhook token
        assert validate_secret_format("webhook123abc456", 16, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    
    def test_validate_secret_format_invalid_length(self):
        """Test secret format validation with invalid length"""
        # Too short API key
        assert not validate_secret_format("abc", 32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        
        # Too short password
        assert not validate_secret_format("ab", 32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?")
    
    def test_validate_secret_format_invalid_chars(self):
        """Test secret format validation with invalid characters"""
        # API key with invalid chars
        assert not validate_secret_format("abc@123", 32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        
        # Secret key with non-hex chars
        assert not validate_secret_format("xyz123", 32, "0123456789abcdef")
    
    def test_edge_cases_empty_string_validation(self):
        """Test edge cases with empty strings"""
        assert not validate_secret_format("", 32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert not validate_secret_format("", 32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?")
        assert not validate_secret_format("", 64, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    
    def test_edge_cases_large_length(self):
        """Test edge cases with very large lengths"""
        large_api_key = generate_api_key(256)
        assert len(large_api_key) == 256
        assert validate_secret_format(large_api_key, 256, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        
        large_password = generate_password(128)
        assert len(large_password) == 128
        assert validate_secret_format(large_password, 128, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?")
    
    def test_edge_cases_whitespace_validation(self):
        """Test edge cases with whitespace"""
        # Secrets with whitespace should be invalid
        assert not validate_secret_format("abc 123", 32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert not validate_secret_format(" mypass ", 32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?")
        assert not validate_secret_format("\tsecret\n", 64, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    
    def test_api_key_no_ambiguous_chars(self):
        """Test API keys don't contain ambiguous characters"""
        api_key = generate_api_key()
        # Should not contain 0, O, l, 1, I
        ambiguous_chars = "0Ol1I"
        for char in ambiguous_chars:
            assert char not in api_key
    
    def test_password_complexity(self):
        """Test password complexity requirements"""
        password = generate_password()
        
        # Should have at least one of each type
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        assert has_upper
        assert has_lower
        assert has_digit
        assert has_special
    
    def test_secret_key_hex_format(self):
        """Test secret key is valid hexadecimal"""
        secret_key = generate_secret_key()
        try:
            int(secret_key, 16)  # Should be valid hex
        except ValueError:
            pytest.fail("Secret key is not valid hexadecimal")
    
    def test_token_url_safe_format(self):
        """Test token uses URL-safe characters"""
        token = generate_token()
        # Should only contain URL-safe characters
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        assert all(c in valid_chars for c in token)
    
    def test_generate_all_secrets_completeness(self):
        """Test that generate_all_secrets returns all expected types"""
        secrets = generate_all_secrets()
        
        # Check each secret has the right characteristics
        assert secrets['thehive_api_key'].isalnum() and len(secrets['thehive_api_key']) == 32
        assert len(secrets['cortex_api_key']) == 32
        assert len(secrets['shuffle_api_key']) == 32
        assert len(secrets['shuffle_webhook_token']) == 64
        assert len(secrets['jwt_secret']) == 64
    
    def test_generate_all_secrets_validity(self):
        """Test that all secrets generated by generate_all_secrets are valid"""
        secrets = generate_all_secrets()
        
        # Each should pass validation
        assert validate_secret_format(secrets['thehive_api_key'], 32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert validate_secret_format(secrets['cortex_api_key'], 32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert validate_secret_format(secrets['shuffle_api_key'], 32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert validate_secret_format(secrets['shuffle_webhook_token'], 64, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        assert validate_secret_format(secrets['jwt_secret'], 64, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

    def test_generate_password_minimum_length(self):
        """Test password generation with minimum length"""
        password = generate_password(5)  # Less than minimum 8
        
        # Should enforce minimum length of 8
        assert len(password) >= 8
        assert isinstance(password, str)

    def test_generate_all_secrets_with_file_output(self):
        """Test generate_all_secrets with file output"""
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name
        
        try:
            secrets = generate_all_secrets(temp_path)
            
            # Verify file was created and contains valid JSON
            assert Path(temp_path).exists()
            with open(temp_path, 'r') as f:
                file_data = json.load(f)
            
            # Should contain all expected secrets
            assert 'thehive_api_key' in file_data
            assert 'cortex_api_key' in file_data
            assert 'shuffle_api_key' in file_data
            assert 'shuffle_webhook_token' in file_data
            assert 'jwt_secret' in file_data
            
            # Should match returned data
            assert secrets == file_data
            
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_main_function_with_output_file(self):
        """Test main function with --output-file argument"""
        import tempfile
        import json
        from unittest.mock import patch
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name
        
        try:
            # Mock sys.argv to simulate CLI usage
            with patch('sys.argv', ['generate_secrets.py', '--output-file', temp_path]):
                main()
            
            # Verify file was created
            assert Path(temp_path).exists()
            
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_main_function_default_output(self):
        """Test main function default output to console"""
        from unittest.mock import patch
        from io import StringIO
        
        # Capture stdout
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('sys.argv', ['generate_secrets.py']):
                main()
            
            output = mock_stdout.getvalue()
            
            # Should contain expected headers and secrets
            assert "Generating secure secrets for SOAR Ransomware Lab" in output
            assert "ELASTIC_PASSWORD=" in output
            assert "SHUFFLE_DEFAULT_PASSWORD=" in output
            assert "THEHIVE_API_KEY=" in output
            assert "Copy these values to your docker/.env file" in output
            assert "DO NOT commit" in output

    def test_main_function_with_output_file_and_no_argument(self):
        """Test main function with --output-file but no file argument"""
        from unittest.mock import patch
        from io import StringIO
        
        # Capture stdout
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('sys.argv', ['generate_secrets.py', '--output-file']):
                main()
            
            output = mock_stdout.getvalue()
            
            # Should still generate secrets and print to console
            assert "Generating secure secrets for SOAR Ransomware Lab" in output
            assert "ELASTIC_PASSWORD=" in output

    def test_generate_all_secrets_returns_all_expected_keys(self):
        """Test that generate_all_secrets returns all expected secret keys"""
        secrets = generate_all_secrets()
        
        expected_keys = [
            'thehive_api_key', 'cortex_api_key', 'shuffle_api_key',
            'shuffle_webhook_token', 'jwt_secret', 'generated_at'
        ]
        
        for key in expected_keys:
            assert key in secrets, f"Missing expected key: {key}"
            assert isinstance(secrets[key], str), f"Secret {key} should be a string"
            assert len(secrets[key]) > 0, f"Secret {key} should not be empty"
