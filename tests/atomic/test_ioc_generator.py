#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for IOC Generator (Corrected)
Tests individual IOC generation functions in isolation
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from soar_lab.data.generate_iocs import (
    generate_malicious_hash,
    generate_benign_hash,
    generate_ip_addresses,
    generate_domains,
    generate_urls,
    create_ioc_package
)


class TestIOCGeneratorAtomic(unittest.TestCase):
    """Atomic tests for individual IOC generation functions"""

    def test_generate_malicious_hash_deterministic(self):
        """Test malicious hash generation with same seed produces same result"""
        hash1 = generate_malicious_hash("test_seed")
        hash2 = generate_malicious_hash("test_seed")
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA256 length

    def test_generate_malicious_hash_random(self):
        """Test malicious hash generation without seed"""
        hash1 = generate_malicious_hash()
        hash2 = generate_malicious_hash()
        # Hashes should be different for random generation
        self.assertNotEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)

    def test_generate_benign_hash_deterministic(self):
        """Test benign hash generation with same seed produces same result"""
        hash1 = generate_benign_hash("test_seed")
        hash2 = generate_benign_hash("test_seed")
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA256 length

    def test_generate_benign_hash_random(self):
        """Test benign hash generation without seed"""
        hash1 = generate_benign_hash()
        hash2 = generate_benign_hash()
        # Hashes should be different for random generation
        self.assertNotEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)

    def test_generate_ip_addresses_default_count(self):
        """Test IP address generation with default count"""
        ips = generate_ip_addresses()
        self.assertEqual(len(ips), 5)
        
        for ip in ips:
            parts = ip.split('.')
            self.assertEqual(len(parts), 4)
            for part in parts:
                self.assertTrue(0 <= int(part) <= 255)

    def test_generate_ip_addresses_custom_count(self):
        """Test IP address generation with custom count"""
        for count in [1, 3, 10]:
            ips = generate_ip_addresses(count)
            self.assertEqual(len(ips), count)
            
            for ip in ips:
                parts = ip.split('.')
                self.assertEqual(len(parts), 4)
                for part in parts:
                    self.assertTrue(0 <= int(part) <= 255)

    def test_generate_ip_addresses_private_ranges(self):
        """Test IP addresses are in private ranges"""
        ips = generate_ip_addresses(20)
        
        for ip in ips:
            parts = ip.split('.')
            first_octet = int(parts[0])
            
            # Should be in private ranges
            self.assertTrue(
                first_octet == 10 or  # 10.0.0.0/8
                (first_octet == 172 and 16 <= int(parts[1]) <= 31) or  # 172.16.0.0/12
                (first_octet == 192 and int(parts[1]) == 168)  # 192.168.0.0/16
            )

    def test_generate_domains_default_count(self):
        """Test domain generation with default count"""
        domains = generate_domains()
        self.assertEqual(len(domains), 5)
        
        for domain in domains:
            self.assertIn('.', domain)
            self.assertGreater(len(domain), 5)
            # Should not contain invalid characters
            self.assertTrue(all(c.isalnum() or c == '.' for c in domain))

    def test_generate_domains_custom_count(self):
        """Test domain generation with custom count"""
        for count in [1, 3, 10]:
            domains = generate_domains(count)
            self.assertEqual(len(domains), count)
            
            for domain in domains:
                self.assertIn('.', domain)
                self.assertGreater(len(domain), 5)

    def test_generate_domains_valid_tlds(self):
        """Test domains use valid TLDs"""
        domains = generate_domains(20)
        valid_tlds = ['com', 'net', 'org', 'io', 'biz', 'info', 'ru', 'cn', 'xyz']
        
        for domain in domains:
            tld = domain.split('.')[-1]
            self.assertIn(tld, valid_tlds)

    def test_generate_urls_default_count(self):
        """Test URL generation with default count"""
        urls = generate_urls()
        self.assertEqual(len(urls), 5)
        
        for url in urls:
            self.assertTrue(url.startswith(('http://', 'https://')))
            self.assertIn('.', url)

    def test_generate_urls_custom_count(self):
        """Test URL generation with custom count"""
        for count in [1, 3, 10]:
            urls = generate_urls(count)
            self.assertEqual(len(urls), count)
            
            for url in urls:
                self.assertTrue(url.startswith(('http://', 'https://')))
                self.assertIn('.', url)

    def test_generate_urls_valid_protocols(self):
        """Test URLs use valid protocols"""
        urls = generate_urls(20)
        valid_protocols = ['http', 'https']
        
        for url in urls:
            protocol = url.split('://')[0]
            self.assertIn(protocol, valid_protocols)

    def test_generate_urls_structure(self):
        """Test URLs have proper structure"""
        urls = generate_urls(10)
        
        for url in urls:
            # Should have protocol://domain/path
            self.assertRegex(url, r'^https?://[^/]+/.+$')

    def test_create_ioc_package_structure(self):
        """Test IOC package creation returns proper structure"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            package = create_ioc_package(temp_path, 3)
            
            # Check structure
            self.assertIsInstance(package, dict)
            self.assertIn('malicious', package)
            self.assertIn('benign', package)
            
            # Check malicious IOCs
            malicious = package['malicious']
            self.assertIn('hash', malicious)
            self.assertIn('ips', malicious)
            self.assertIn('domains', malicious)
            self.assertIn('urls', malicious)
            
            # Check benign IOCs
            benign = package['benign']
            self.assertIn('hash', benign)
            self.assertIn('ips', benign)
            self.assertIn('domains', benign)
            self.assertIn('urls', benign)
            
            # Check counts
            self.assertEqual(len(malicious['ips']), 3)
            self.assertEqual(len(malicious['domains']), 3)
            self.assertEqual(len(malicious['urls']), 3)
            self.assertEqual(len(benign['ips']), 3)
            self.assertEqual(len(benign['domains']), 3)
            self.assertEqual(len(benign['urls']), 3)
            
        finally:
            # Clean up
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_create_ioc_package_file_creation(self):
        """Test IOC package creates file correctly"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            package = create_ioc_package(temp_path, 2)
            
            # Check file was created
            self.assertTrue(Path(temp_path).exists())
            
            # Check file content
            with open(temp_path, 'r') as f:
                saved_package = json.load(f)
            
            self.assertEqual(saved_package, package)
            
        finally:
            # Clean up
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_create_ioc_package_hash_formats(self):
        """Test IOC package contains properly formatted hashes"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            package = create_ioc_package(temp_path, 1)
            
            # Check hash formats (should be SHA256)
            malicious_hash = package['malicious']['hash']
            benign_hash = package['benign']['hash']
            
            self.assertEqual(len(malicious_hash), 64)
            self.assertEqual(len(benign_hash), 64)
            self.assertTrue(all(c in '0123456789abcdef' for c in malicious_hash.lower()))
            self.assertTrue(all(c in '0123456789abcdef' for c in benign_hash.lower()))
            
        finally:
            # Clean up
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_create_ioc_package_ip_formats(self):
        """Test IOC package contains properly formatted IPs"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            package = create_ioc_package(temp_path, 5)
            
            # Check IP formats
            for ip in package['malicious']['ips']:
                parts = ip.split('.')
                self.assertEqual(len(parts), 4)
                for part in parts:
                    self.assertTrue(0 <= int(part) <= 255)
            
            for ip in package['benign']['ips']:
                parts = ip.split('.')
                self.assertEqual(len(parts), 4)
                for part in parts:
                    self.assertTrue(0 <= int(part) <= 255)
            
        finally:
            # Clean up
            import os
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_edge_cases_zero_count(self):
        """Test generation functions with zero count"""
        ips = generate_ip_addresses(0)
        self.assertEqual(len(ips), 0)
        
        domains = generate_domains(0)
        self.assertEqual(len(domains), 0)
        
        urls = generate_urls(0)
        self.assertEqual(len(urls), 0)

    def test_edge_cases_large_count(self):
        """Test generation functions with large count"""
        large_count = 100
        
        ips = generate_ip_addresses(large_count)
        self.assertEqual(len(ips), large_count)
        
        domains = generate_domains(large_count)
        self.assertEqual(len(domains), large_count)
        
        urls = generate_urls(large_count)
        self.assertEqual(len(urls), large_count)

    def test_hash_uniqueness(self):
        """Test hash generation produces unique values"""
        hash1 = generate_malicious_hash("seed1")
        hash2 = generate_malicious_hash("seed2")
        hash3 = generate_benign_hash("seed1")
        hash4 = generate_benign_hash("seed2")
        hash5 = generate_malicious_hash()  # No seed - deterministic
        hash6 = generate_benign_hash()    # No seed - deterministic
        
        # Different seeds should produce different hashes
        self.assertNotEqual(hash1, hash2)
        self.assertNotEqual(hash3, hash4)
        
        # Same seed should produce same hash (deterministic behavior)
        self.assertEqual(hash1, hash3)  # Same seed "seed1"
        self.assertEqual(hash2, hash4)  # Same seed "seed2"
        
        # No seed calls should be different between malicious and benign
        self.assertNotEqual(hash5, hash6)


if __name__ == '__main__':
    unittest.main()
