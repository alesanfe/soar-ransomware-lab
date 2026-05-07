#!/usr/bin/env python3
"""
Unit tests for generate_secrets.py
"""

import unittest
import tempfile
import os
import json
import secrets
import string
from unittest.mock import patch, mock_open
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scripts.generate_secrets import (
    generate_api_key,
    generate_password,
    generate_webhook_token,
    generate_jwt_secret,
    generate_secret_key,
    generate_token,
    generate_all_secrets,
    validate_secret_format
)


class TestSecretGenerator(unittest.TestCase):
    """Test cases for secret generation"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.test_output_file = os.path.join(self.test_dir, 'test_secrets.json')

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_generate_api_key(self):
        """Test API key generation"""
        api_key = generate_api_key()
        
        # Should be 32 characters long
        self.assertEqual(len(api_key), 32)
        
        # Should contain only valid characters
        valid_chars = string.ascii_letters + string.digits
        self.assertTrue(all(c in valid_chars for c in api_key))
        
        # Should be different each time
        api_key2 = generate_api_key()
        self.assertNotEqual(api_key, api_key2)

    def test_generate_password(self):
        """Test password generation"""
        password = generate_password(length=16)
        
        # Should be specified length
        self.assertEqual(len(password), 16)
        
        # Should contain at least one uppercase letter
        self.assertTrue(any(c.isupper() for c in password))
        
        # Should contain at least one lowercase letter
        self.assertTrue(any(c.islower() for c in password))
        
        # Should contain at least one digit
        self.assertTrue(any(c.isdigit() for c in password))
        
        # Should contain at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        self.assertTrue(any(c in special_chars for c in password))

    def test_generate_webhook_token(self):
        """Test webhook token generation"""
        token = generate_webhook_token()
        
        # Should be 64 characters long
        self.assertEqual(len(token), 64)
        
        # Should contain only valid characters
        valid_chars = string.ascii_letters + string.digits
        self.assertTrue(all(c in valid_chars for c in token))

    def test_generate_jwt_secret(self):
        """Test JWT secret generation"""
        secret = generate_jwt_secret()
        
        # Should be 64 characters long
        self.assertEqual(len(secret), 64)
        
        # Should contain only valid characters
        valid_chars = string.ascii_letters + string.digits
        self.assertTrue(all(c in valid_chars for c in secret))

    def test_password_entropy(self):
        """Test password has sufficient entropy"""
        passwords = [generate_password() for _ in range(100)]
        
        # All passwords should be unique
        unique_passwords = set(passwords)
        self.assertEqual(len(unique_passwords), 100)

    def test_api_key_format(self):
        """Test API key format consistency"""
        for _ in range(10):
            api_key = generate_api_key()
            
            # Should not contain ambiguous characters
            ambiguous_chars = '0Ol1I'
            self.assertTrue(all(c not in ambiguous_chars for c in api_key))

    @patch('builtins.open', new_callable=mock_open)
    @patch('scripts.generate_secrets.generate_api_key')
    @patch('scripts.generate_secrets.generate_password')
    @patch('scripts.generate_secrets.generate_webhook_token')
    @patch('scripts.generate_secrets.generate_jwt_secret')
    def test_generate_all_secrets(self, mock_jwt, mock_webhook, mock_password, 
                                 mock_api_key, mock_file):
        """Test generating all secrets"""
        # Setup mocks
        mock_api_key.return_value = "test_api_key_32_chars_long"
        mock_password.return_value = "TestPass123!"
        mock_webhook.return_value = "test_webhook_token_64_chars_long"
        mock_jwt.return_value = "test_jwt_secret_64_chars_long"
        
        # Mock file operations
        mock_file.return_value.write.return_value = None
        
        # Generate all secrets
        generate_all_secrets(self.test_output_file)
        
        # Verify all generation functions were called
        # generate_api_key is called 3 times in generate_all_secrets
        self.assertEqual(mock_api_key.call_count, 3)
        mock_password.assert_not_called() # Not called in generate_all_secrets
        mock_webhook.assert_called_once()
        mock_jwt.assert_called_once()
        
        # Verify file was opened for writing
        mock_file.assert_called_once_with(self.test_output_file, 'w')

    def test_secrets_output_format(self):
        """Test secrets output format is valid JSON"""
        # Create actual secrets file
        generate_all_secrets(self.test_output_file)
        
        # Read and validate JSON
        with open(self.test_output_file, 'r') as f:
            secrets_data = json.load(f)
        
        # Check structure
        expected_keys = ['thehive_api_key', 'cortex_api_key', 'shuffle_api_key',
                       'shuffle_webhook_token', 'jwt_secret', 'generated_at']
        
        for key in expected_keys:
            self.assertIn(key, secrets_data)
        
        # Check timestamp format
        from datetime import datetime
        timestamp = secrets_data['generated_at']
        try:
            # ISO format with Z
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            try:
                datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                self.fail(f"Generated timestamp {timestamp} is not in expected format")

    def test_validate_secret_format(self):
        """Test secret format validation"""
        # Valid formats
        self.assertTrue(validate_secret_format("abc123", 6, string.ascii_letters + string.digits))
        self.assertTrue(validate_secret_format("ABCdef123", 9, string.ascii_letters + string.digits))
        
        # Invalid formats
        self.assertFalse(validate_secret_format("abc123", 5, string.ascii_letters + string.digits))  # Wrong length
        self.assertFalse(validate_secret_format("abc@123", 6, string.ascii_letters + string.digits))  # Invalid chars
        self.assertFalse(validate_secret_format("", 6, string.ascii_letters + string.digits))  # Empty

    def test_secrets_uniqueness(self):
        """Test secrets are unique across generations"""
        secrets_sets = []
        
        for _ in range(5):
            generate_all_secrets(self.test_output_file)
            
            with open(self.test_output_file, 'r') as f:
                secrets_data = json.load(f)
            
            current_secrets = {
                secrets_data['thehive_api_key'],
                secrets_data['cortex_api_key'],
                secrets_data['shuffle_api_key'],
                secrets_data['shuffle_webhook_token'],
                secrets_data['jwt_secret']
            }
            
            secrets_sets.append(current_secrets)
        
        # Check all generated secrets are unique
        all_secrets = []
        for secrets in secrets_sets:
            all_secrets.extend(secrets)
        
        unique_secrets = set(all_secrets)
        self.assertEqual(len(unique_secrets), len(all_secrets))

    def test_password_length_variations(self):
        """Test password generation with different lengths"""
        for length in [8, 12, 16, 20, 32]:
            password = generate_password(length=length)
            self.assertEqual(len(password), length)

    def test_no_weak_passwords(self):
        """Test generated passwords are not weak"""
        weak_passwords = [
            "password",
            "12345678",
            "abcdefgh",
            "Password1",
            "qwertyui"
        ]
        
        for _ in range(100):
            password = generate_password()
            self.assertNotIn(password.lower(), weak_passwords)

    def test_secret_character_distribution(self):
        """Test secrets have good character distribution"""
        api_keys = [generate_api_key() for _ in range(100)]
        
        # Count character types
        upper_count = sum(1 for key in api_keys for c in key if c.isupper())
        lower_count = sum(1 for key in api_keys for c in key if c.islower())
        digit_count = sum(1 for key in api_keys for c in key if c.isdigit())
        
        # Should have reasonable distribution (not all one type)
        total_chars = len(api_keys) * 32
        self.assertGreater(upper_count, total_chars * 0.2)  # At least 20% uppercase
        self.assertGreater(lower_count, total_chars * 0.2)  # At least 20% lowercase
        self.assertGreater(digit_count, total_chars * 0.2)  # At least 20% digits

    def test_generate_secret_key(self):
        """Test secret key generation"""
        secret_key = generate_secret_key()
        
        # Should be 32 characters long (16 bytes * 2 for hex)
        self.assertEqual(len(secret_key), 32)
        
        # Should contain only hexadecimal characters
        valid_chars = string.hexdigits.lower()
        self.assertTrue(all(c in valid_chars for c in secret_key))
        
        # Should be different each time
        secret_key2 = generate_secret_key()
        self.assertNotEqual(secret_key, secret_key2)

    def test_generate_token(self):
        """Test token generation"""
        token = generate_token()
        
        # Should be 48 characters long
        self.assertEqual(len(token), 48)
        
        # Should contain only URL-safe characters
        valid_chars = string.ascii_letters + string.digits + '-_'
        self.assertTrue(all(c in valid_chars for c in token))
        
        # Should be different each time
        token2 = generate_token()
        self.assertNotEqual(token, token2)

    def test_generate_token_custom_length(self):
        """Test token generation with custom length"""
        for length in [16, 24, 32, 48, 64]:
            token = generate_token(length=length)
            self.assertEqual(len(token), length)

    def test_generate_secret_key_custom_length(self):
        """Test secret key generation with custom length"""
        # Test even length
        secret_key = generate_secret_key(64)
        self.assertEqual(len(secret_key), 64)
        
        # Test odd length (should be floor(length/2) * 2 for hex)
        secret_key_odd = generate_secret_key(33)
        self.assertEqual(len(secret_key_odd), 32)  # 33//2 = 16, *2 = 32

    def test_generate_all_secrets_without_file(self):
        """Test generating all secrets without saving to file"""
        secrets_data = generate_all_secrets()
        
        # Should return dictionary with expected keys
        expected_keys = ['thehive_api_key', 'cortex_api_key', 'shuffle_api_key',
                       'shuffle_webhook_token', 'jwt_secret', 'generated_at']
        
        for key in expected_keys:
            self.assertIn(key, secrets_data)
        
        # Should not create any files
        self.assertFalse(os.path.exists(self.test_output_file))


class TestSecretMainFunction(unittest.TestCase):
    """Test main function and CLI interface"""

    @patch('sys.argv', ['generate_secrets.py'])
    @patch('builtins.print')
    def test_main_default_output(self, mock_print):
        """Test main function with default output"""
        from scripts.generate_secrets import main
        
        main()
        
        # Should have called print multiple times
        self.assertGreater(mock_print.call_count, 10)
        
        # Check that key messages were printed
        print_calls = [str(call) for call in mock_print.call_args_list]
        output_text = ' '.join(print_calls)
        
        self.assertIn('Generating secure secrets', output_text)
        self.assertIn('ELASTIC_PASSWORD=', output_text)
        self.assertIn('Copy these values', output_text)

    @patch('sys.argv', ['generate_secrets.py', '--output-file', 'test.json'])
    @patch('scripts.generate_secrets.generate_all_secrets')
    @patch('builtins.print')
    def test_main_with_output_file(self, mock_print, mock_generate):
        """Test main function with output file argument"""
        from scripts.generate_secrets import main
        
        main()
        
        # Should call generate_all_secrets with the file path
        mock_generate.assert_called_once_with('test.json')
        
        # Should print success message
        mock_print.assert_any_call('Secrets generated in test.json')

    @patch('sys.argv', ['generate_secrets.py', '--output-file'])
    @patch('builtins.print')
    def test_main_with_output_file_missing_argument(self, mock_print):
        """Test main function with output file but missing argument"""
        from scripts.generate_secrets import main
        
        main()
        
        # Should generate secrets normally (no file specified)
        self.assertGreater(mock_print.call_count, 10)

    @patch('sys.argv', ['generate_secrets.py', '--unknown-arg'])
    @patch('builtins.print')
    def test_main_with_unknown_argument(self, mock_print):
        """Test main function with unknown argument"""
        from scripts.generate_secrets import main
        
        main()
        
        # Should generate secrets normally (ignore unknown arg)
        self.assertGreater(mock_print.call_count, 10)


class TestSecretSecurity(unittest.TestCase):
    """Test security aspects of secret generation"""

    def test_no_predictable_patterns(self):
        """Test secrets don't have predictable patterns"""
        secrets = [generate_api_key() for _ in range(50)]
        
        # Check for sequential patterns
        for i in range(len(secrets) - 1):
            # Should not be sequential (like abc123, abc124)
            self.assertNotEqual(
                int(secrets[i+1][-3:], 36) - int(secrets[i][-3:], 36),
                1
            )

    def test_no_dictionary_words(self):
        """Test passwords don't contain common dictionary words"""
        common_words = [
            "password", "admin", "user", "login", "welcome",
            "qwerty", "asdf", "zxcv", "123456", "letmein"
        ]
        
        for _ in range(100):
            password = generate_password()
            password_lower = password.lower()
            
            for word in common_words:
                self.assertNotIn(word, password_lower)

    def test_sufficient_entropy(self):
        """Test secrets have sufficient entropy"""
        import math
        
        # Calculate entropy for API key (62 possible characters)
        api_key = generate_api_key()
        entropy = len(api_key) * math.log2(62)  # 62 possible characters
        
        # Should have at least 180 bits of entropy
        self.assertGreater(entropy, 180)

    def test_no_reuse_across_types(self):
        """Test secrets of different types don't collide"""
        for _ in range(20):
            api_key = generate_api_key()
            password = generate_password()
            webhook_token = generate_webhook_token()
            jwt_secret = generate_jwt_secret()
            
            # All should be different
            secrets = [api_key, password, webhook_token, jwt_secret]
            unique_secrets = set(secrets)
            self.assertEqual(len(unique_secrets), 4)


if __name__ == '__main__':
    unittest.main()
