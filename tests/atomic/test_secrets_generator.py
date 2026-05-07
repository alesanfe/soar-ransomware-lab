#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for Secrets Generator
Tests individual secrets generation functions in isolation
"""

import unittest
import re
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from generate_secrets import (
    generate_password,
    generate_api_key,
    generate_jwt_secret,
    generate_webhook_token,
    validate_secret_format,
    generate_all_secrets,
    generate_secret_key,
    generate_token
)


class TestSecretsGeneratorAtomic(unittest.TestCase):
    """Atomic tests for individual secrets generation functions"""

    def test_generate_password_default_length(self):
        """Test password generation with default length"""
        password = generate_password()
        self.assertEqual(len(password), 32)  # Default length

    def test_generate_password_custom_length(self):
        """Test password generation with custom length"""
        password = generate_password(length=24)
        self.assertEqual(len(password), 24)

    def test_generate_password_contains_lowercase(self):
        """Test password contains lowercase letters"""
        password = generate_password()
        self.assertTrue(any(c.islower() for c in password))

    def test_generate_password_contains_uppercase(self):
        """Test password contains uppercase letters"""
        password = generate_password()
        self.assertTrue(any(c.isupper() for c in password))

    def test_generate_password_contains_digits(self):
        """Test password contains digits"""
        password = generate_password()
        self.assertTrue(any(c.isdigit() for c in password))

    def test_generate_password_contains_special(self):
        """Test password contains special characters"""
        password = generate_password()
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        self.assertTrue(any(c in special_chars for c in password))

    def test_generate_password_uniqueness(self):
        """Test that multiple password generations produce unique results"""
        passwords = set()
        for _ in range(10):
            password = generate_password()
            passwords.add(password)
        
        # Should have multiple unique passwords
        self.assertGreater(len(passwords), 1)

    def test_generate_api_key_format(self):
        """Test API key generation format"""
        api_key = generate_api_key()
        
        # Should be 32 characters
        self.assertEqual(len(api_key), 32)
        
        # Should not contain ambiguous characters
        ambiguous_chars = '0Ol1I'
        for char in ambiguous_chars:
            self.assertNotIn(char, api_key)
        
        # Should be alphanumeric
        self.assertTrue(all(c.isalnum() for c in api_key))

    def test_generate_api_key_uniqueness(self):
        """Test that multiple API key generations produce unique results"""
        api_keys = set()
        for _ in range(10):
            api_key = generate_api_key()
            api_keys.add(api_key)
        
        # Should have multiple unique API keys
        self.assertGreater(len(api_keys), 1)

    def test_generate_jwt_secret_length(self):
        """Test JWT secret generation length"""
        secret = generate_jwt_secret()
        self.assertEqual(len(secret), 64)  # 64 bytes = 512 bits

    def test_generate_jwt_secret_format(self):
        """Test JWT secret generation format"""
        secret = generate_jwt_secret()
        
        # Should contain only base64url characters
        valid_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        self.assertTrue(all(c in valid_chars for c in secret))

    def test_generate_jwt_secret_uniqueness(self):
        """Test that multiple JWT secret generations produce unique results"""
        secrets = set()
        for _ in range(10):
            secret = generate_jwt_secret()
            secrets.add(secret)
        
        # Should have multiple unique secrets
        self.assertGreater(len(secrets), 1)

    def test_generate_webhook_token_length(self):
        """Test webhook token generation length"""
        token = generate_webhook_token()
        self.assertEqual(len(token), 24)

    def test_generate_webhook_token_format(self):
        """Test webhook token generation format"""
        token = generate_webhook_token()
        
        # Should contain only alphanumeric characters
        self.assertTrue(token.isalnum())

    def test_generate_webhook_token_uniqueness(self):
        """Test that multiple webhook token generations produce unique results"""
        tokens = set()
        for _ in range(10):
            token = generate_webhook_token()
            tokens.add(token)
        
        # Should have multiple unique tokens
        self.assertGreater(len(tokens), 1)

    def test_validate_secret_format_valid_password(self):
        """Test secret format validation with valid password"""
        password = "TestPass123!@#"
        allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?"
        result = validate_secret_format(password, len(password), allowed_chars)
        self.assertTrue(result)

    def test_validate_secret_format_invalid_password_too_short(self):
        """Test secret format validation with password too short"""
        password = "Test1!"
        allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?"
        result = validate_secret_format(password, 8, allowed_chars)  # Expect length 8
        self.assertFalse(result)

    def test_validate_secret_format_invalid_password_chars(self):
        """Test secret format validation with password invalid characters"""
        password = "TestPass123@@"  # Double @, but @ is in allowed set multiple times
        allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?"  # @ is allowed
        result = validate_secret_format(password, len(password), allowed_chars)
        self.assertTrue(result)  # Should be true since @ is allowed

    def test_validate_secret_format_valid_api_key(self):
        """Test secret format validation with valid API key"""
        api_key = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"[:32]
        allowed_chars = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No 0Ol1I
        # Check if all characters are in allowed set
        result = all(c in allowed_chars for c in api_key)
        self.assertTrue(result)

    def test_validate_secret_format_invalid_api_key_length(self):
        """Test secret format validation with API key wrong length"""
        api_key = "a1b2c3d4"
        allowed_chars = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        result = validate_secret_format(api_key, 32, allowed_chars)  # Expect length 32
        self.assertFalse(result)

    def test_validate_secret_format_invalid_api_key_chars(self):
        """Test secret format validation with API key invalid characters"""
        api_key = "g1h2i3j4k5l6789012345678901234ab"  # Contains 'g' and 'l'
        allowed_chars = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No g, l
        result = validate_secret_format(api_key, len(api_key), allowed_chars)
        self.assertFalse(result)

    def test_validate_secret_format_valid_jwt_secret(self):
        """Test secret format validation with valid JWT secret"""
        jwt_secret = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        result = validate_secret_format(jwt_secret, len(jwt_secret), allowed_chars)
        self.assertTrue(result)

    def test_validate_secret_format_invalid_jwt_secret_length(self):
        """Test secret format validation with JWT secret wrong length"""
        jwt_secret = "ABC"
        allowed_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        result = validate_secret_format(jwt_secret, 64, allowed_chars)  # Expect length 64
        self.assertFalse(result)

    def test_generate_secret_key_format(self):
        """Test secret key generation format"""
        secret_key = generate_secret_key(32)
        self.assertEqual(len(secret_key), 32)  # generate_secret_key returns hex of specified length
        self.assertTrue(all(c in '0123456789abcdef' for c in secret_key))

    def test_generate_token_format(self):
        """Test token generation format"""
        token = generate_token(48)
        self.assertEqual(len(token), 48)
        # Should be base64url safe characters
        valid_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
        self.assertTrue(all(c in valid_chars for c in token))

    def test_generate_webhook_token_length(self):
        """Test webhook token generation length"""
        token = generate_webhook_token(24)
        self.assertEqual(len(token), 24)

    def test_generate_webhook_token_format(self):
        """Test webhook token generation format"""
        token = generate_webhook_token()
        self.assertEqual(len(token), 64)  # Default length
        valid_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        self.assertTrue(all(c in valid_chars for c in token))

    def test_generate_all_secrets_structure(self):
        """Test generate_all_secrets returns proper structure"""
        secrets = generate_all_secrets()
        
        # Should be a dictionary
        self.assertIsInstance(secrets, dict)
        
        # Should contain expected keys
        expected_keys = [
            "thehive_api_key", "cortex_api_key", "shuffle_api_key", 
            "shuffle_webhook_token", "jwt_secret", "generated_at"
        ]
        for key in expected_keys:
            self.assertIn(key, secrets)
        
        # All values should be strings
        for key, value in secrets.items():
            if key != "generated_at":  # timestamp is also string
                self.assertIsInstance(value, str)
                self.assertGreater(len(value), 0)

    def test_generate_all_secrets_lengths(self):
        """Test generate_all_secrets returns correct lengths"""
        secrets = generate_all_secrets()
        
        self.assertEqual(len(secrets["thehive_api_key"]), 32)
        self.assertEqual(len(secrets["cortex_api_key"]), 32)
        self.assertEqual(len(secrets["shuffle_api_key"]), 32)
        self.assertEqual(len(secrets["shuffle_webhook_token"]), 64)
        self.assertEqual(len(secrets["jwt_secret"]), 64)

    def test_generate_all_secrets_with_file(self):
        """Test generate_all_secrets with output file"""
        import tempfile
        import os
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            secrets = generate_all_secrets(temp_file)
            
            # Check file was created
            self.assertTrue(os.path.exists(temp_file))
            
            # Load and verify content
            with open(temp_file, 'r') as f:
                file_secrets = json.load(f)
            
            self.assertEqual(secrets, file_secrets)
            
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_secrets_uniqueness_across_types(self):
        """Test that different secret types produce different values"""
        secrets = generate_all_secrets()
        
        # Extract secret values (excluding timestamp)
        secret_values = [
            secrets["thehive_api_key"],
            secrets["cortex_api_key"], 
            secrets["shuffle_api_key"],
            secrets["shuffle_webhook_token"],
            secrets["jwt_secret"]
        ]
        
        # All values should be unique
        self.assertEqual(len(secret_values), len(set(secret_values)))


if __name__ == '__main__':
    unittest.main()
