#!/usr/bin/env python3
"""
Unit tests for generate_iocs.py
"""

import unittest
import tempfile
import os
import json
import hashlib
from unittest.mock import patch, mock_open
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scripts.generate_iocs import (
    generate_malicious_hash,
    generate_benign_hash,
    generate_ip_addresses,
    generate_domains,
    generate_urls,
    create_ioc_package
)


class TestIOCGenerator(unittest.TestCase):
    """Test cases for IOC generation"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.test_output_file = os.path.join(self.test_dir, 'test_iocs.json')

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_generate_malicious_hash(self):
        """Test malicious hash generation"""
        hash_value = generate_malicious_hash()
        
        # Should be a valid SHA256 hash
        self.assertEqual(len(hash_value), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_value))
        
        # Should be consistent (deterministic)
        hash_value2 = generate_malicious_hash()
        self.assertEqual(hash_value, hash_value2)

    def test_generate_benign_hash(self):
        """Test benign hash generation"""
        hash_value = generate_benign_hash()
        
        # Should be a valid SHA256 hash
        self.assertEqual(len(hash_value), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_value))
        
        # Should be different from malicious
        malicious_hash = generate_malicious_hash()
        self.assertNotEqual(hash_value, malicious_hash)

    def test_generate_ip_addresses(self):
        """Test IP address generation"""
        ips = generate_ip_addresses(5)
        
        self.assertEqual(len(ips), 5)
        
        for ip in ips:
            # Should be valid private IP addresses
            self.assertTrue(ip.startswith('192.168.') or 
                          ip.startswith('10.') or 
                          ip.startswith('172.'))
            
            # Should be valid IP format
            parts = ip.split('.')
            self.assertEqual(len(parts), 4)
            for part in parts:
                self.assertTrue(0 <= int(part) <= 255)

    def test_generate_domains(self):
        """Test domain generation"""
        domains = generate_domains(3)
        
        self.assertEqual(len(domains), 3)
        
        for domain in domains:
            # Should have valid domain format
            self.assertTrue('.' in domain)
            # Should not have invalid characters
            self.assertTrue(domain.replace('.', '').replace('-', '').isalnum())

    def test_generate_urls(self):
        """Test URL generation"""
        urls = generate_urls(3)
        
        self.assertEqual(len(urls), 3)
        
        for url in urls:
            # Should start with http:// or https://
            self.assertTrue(url.startswith('http://') or url.startswith('https://'))
            # Should have domain
            self.assertTrue('.' in url)

    @patch('builtins.open', new_callable=mock_open)
    @patch('scripts.generate_iocs.generate_malicious_hash')
    @patch('scripts.generate_iocs.generate_benign_hash')
    @patch('scripts.generate_iocs.generate_ip_addresses')
    @patch('scripts.generate_iocs.generate_domains')
    @patch('scripts.generate_iocs.generate_urls')
    def test_create_ioc_package(self, mock_urls, mock_domains, mock_ips, 
                               mock_benign, mock_malicious, mock_file):
        """Test IOC package creation"""
        # Setup mocks
        mock_malicious.return_value = "malicious_hash"
        mock_benign.return_value = "benign_hash"
        mock_ips.return_value = ["192.168.1.100", "192.168.1.101"]
        mock_domains.return_value = ["malicious.com", "benign.com"]
        mock_urls.return_value = ["http://malicious.com/bad", "http://benign.com/good"]
        
        # Mock file operations
        mock_file.return_value.write.return_value = None
        
        # Create IOC package
        create_ioc_package(self.test_output_file, 2)
        
        # Verify all generation functions were called
        mock_malicious.assert_called()
        mock_benign.assert_called()
        mock_ips.assert_called_with(2)
        mock_domains.assert_called_with(2)
        mock_urls.assert_called_with(2)
        
        # Verify file was opened for writing
        mock_file.assert_called_once_with(self.test_output_file, 'w')

    def test_ioc_output_format(self):
        """Test IOC output format is valid JSON"""
        # Create actual IOC file
        create_ioc_package(self.test_output_file, 1)
        
        # Read and validate JSON
        with open(self.test_output_file, 'r') as f:
            ioc_data = json.load(f)
        
        # Check structure
        self.assertIn('malicious', ioc_data)
        self.assertIn('benign', ioc_data)
        
        # Check malicious IOCs
        malicious = ioc_data['malicious']
        self.assertIn('hash', malicious)
        self.assertIn('ips', malicious)
        self.assertIn('domains', malicious)
        self.assertIn('urls', malicious)
        
        # Check benign IOCs
        benign = ioc_data['benign']
        self.assertIn('hash', benign)
        self.assertIn('ips', benign)
        self.assertIn('domains', benign)
        self.assertIn('urls', benign)

    def test_hash_uniqueness(self):
        """Test that generated hashes are unique"""
        hashes = []
        for _ in range(100):
            hash_val = generate_malicious_hash()
            self.assertNotIn(hash_val, hashes)
            hashes.append(hash_val)

    def test_ip_range_validation(self):
        """Test IP addresses are in valid ranges"""
        for _ in range(50):
            ips = generate_ip_addresses(10)
            for ip in ips:
                parts = list(map(int, ip.split('.')))
                
                # Check private IP ranges
                is_private = (
                    (parts[0] == 10) or  # 10.0.0.0/8
                    (parts[0] == 172 and 16 <= parts[1] <= 31) or  # 172.16.0.0/12
                    (parts[0] == 192 and parts[1] == 168)  # 192.168.0.0/16
                )
                self.assertTrue(is_private, f"IP {ip} is not in private range")

    def test_domain_tld_variety(self):
        """Test domains have variety in TLDs"""
        domains = generate_domains(20)
        tlds = set()
        
        for domain in domains:
            tld = domain.split('.')[-1]
            tlds.add(tld)
        
        # Should have multiple different TLDs
        self.assertGreater(len(tlds), 1)


class TestIOCSecurity(unittest.TestCase):
    """Test security aspects of IOC generation"""

    def test_no_real_malicious_hashes(self):
        """Test we don't generate real malicious hashes"""
        # Generate multiple hashes
        hashes = [generate_malicious_hash() for _ in range(10)]
        
        # Check against known malicious hashes (sample)
        known_malicious = [
            "44d88612fea8a8f36de82e1278abb02f",  # EICAR
            "d41d8cd98f00b204e9800998ecf8427e",  # Empty file
            "5d41402abc4b2a76b9719d911017c592",  # "hello"
        ]
        
        for hash_val in hashes:
            self.assertNotIn(hash_val[:32], known_malicious)  # Check first 32 chars

    def test_no_real_malicious_domains(self):
        """Test we don't generate real malicious domains"""
        domains = generate_domains(20)
        
        # Check against known malicious domains (sample)
        known_malicious = [
            "malware.com",
            "evil.com", 
            "badstuff.net"
        ]
        
        for domain in domains:
            self.assertNotIn(domain.lower(), known_malicious)

    def test_no_localhost_in_generated_ips(self):
        """Test we don't generate localhost IPs"""
        ips = generate_ip_addresses(50)
        
        for ip in ips:
            self.assertNotEqual(ip, "127.0.0.1")
            self.assertNotEqual(ip, "0.0.0.0")


if __name__ == '__main__':
    unittest.main()
