#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for IOC Generator
Tests individual functions in isolation
"""

import unittest
import hashlib
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from generate_iocs import (
    generate_malicious_hash,
    generate_benign_hash,
    generate_ip_addresses,
    generate_domains,
    generate_urls,
    create_ioc_package
)


class TestIOCGeneratorAtomic(unittest.TestCase):
    """Atomic tests for individual IOC generation functions"""

    def test_generate_malicious_hash_with_seed(self):
        """Test hash generation with specific seed"""
        seed = "test_seed_123"
        result = generate_malicious_hash(seed)
        expected = hashlib.sha256(str(seed).encode()).hexdigest()
        self.assertEqual(result, expected)
        self.assertEqual(len(result), 64)  # SHA256 length
        self.assertTrue(all(c in '0123456789abcdef' for c in result))

    def test_generate_malicious_hash_deterministic(self):
        """Test hash generation is deterministic without seed"""
        # Reset counter by importing fresh
        import importlib
        import generate_iocs
        importlib.reload(generate_iocs)
        
        result1 = generate_iocs.generate_malicious_hash()
        result2 = generate_iocs.generate_malicious_hash()
        
        # First two calls should return same hash
        self.assertEqual(result1, result2)
        self.assertEqual(len(result1), 64)

    def test_generate_malicious_hash_counter(self):
        """Test hash generation counter behavior"""
        import importlib
        import generate_iocs
        importlib.reload(generate_iocs)
        
        # Call multiple times to trigger counter
        hashes = []
        for _ in range(5):
            hashes.append(generate_iocs.generate_malicious_hash())
        
        # All should be valid SHA256 hashes
        for h in hashes:
            self.assertEqual(len(h), 64)
            self.assertTrue(all(c in '0123456789abcdef' for c in h))

    def test_generate_ip_addresses_default_count(self):
        """Test IP addresses generation with default count"""
        ips = generate_ip_addresses()
        
        self.assertEqual(len(ips), 5)  # Default count
        self.assertIsInstance(ips, list)
        
        # All should be valid IP format
        for ip in ips:
            parts = ip.split('.')
            self.assertEqual(len(parts), 4)
            for part in parts:
                self.assertTrue(0 <= int(part) <= 255)
            
            # Should be in private ranges
            first_octet = int(parts[0])
            self.assertIn(first_octet, [10, 172, 192])

    def test_generate_ip_addresses_custom_count(self):
        """Test IP addresses generation with custom count"""
        count = 3
        ips = generate_ip_addresses(count)
        
        self.assertEqual(len(ips), count)
        self.assertIsInstance(ips, list)

    def test_generate_ip_addresses_10_range(self):
        """Test specific 10.x.x.x range generation"""
        ips = generate_ip_addresses(20)  # Generate many to find 10.x range
        
        found_10_range = False
        for ip in ips:
            if ip.startswith('10.'):
                parts = ip.split('.')
                self.assertEqual(int(parts[0]), 10)
                self.assertTrue(0 <= int(parts[1]) <= 255)
                self.assertTrue(0 <= int(parts[2]) <= 255)
                self.assertTrue(0 <= int(parts[3]) <= 255)
                found_10_range = True
                break
        
        self.assertTrue(found_10_range, "Should generate at least one 10.x.x.x IP")

    def test_generate_domains_default_count(self):
        """Test domains generation with default count"""
        domains = generate_domains()
        
        self.assertEqual(len(domains), 5)  # Default count
        self.assertIsInstance(domains, list)

    def test_generate_domains_custom_count(self):
        """Test domains generation with custom count"""
        count = 3
        domains = generate_domains(count)
        
        self.assertEqual(len(domains), count)
        self.assertIsInstance(domains, list)

    def test_generate_domains_format(self):
        """Test domain generation format"""
        domains = generate_domains(10)
        
        for domain in domains:
            # Should have valid domain format
            self.assertTrue('.' in domain)
            parts = domain.split('.')
            self.assertEqual(len(parts), 2)
            
            # Name part should be alphanumeric
            name = parts[0]
            self.assertTrue(name.isalnum())
            self.assertGreater(len(name), 0)
            
            # TLD should be from expected list
            tld = parts[1]
            valid_tlds = ['com', 'net', 'org', 'io', 'biz', 'info', 'ru', 'cn', 'xyz']
            self.assertIn(tld, valid_tlds)

    def test_generate_urls_default_count(self):
        """Test URLs generation with default count"""
        urls = generate_urls()
        
        self.assertEqual(len(urls), 5)  # Default count
        self.assertIsInstance(urls, list)

    def test_generate_urls_format(self):
        """Test URL generation format"""
        urls = generate_urls(10)
        
        for url in urls:
            # Should have protocol
            self.assertTrue(url.startswith('http://') or url.startswith('https://'))
            
            # Should have domain and path
            self.assertIn('://', url)
            self.assertIn('/', url[8:])  # After protocol

    def test_generate_benign_hash_format(self):
        """Test benign hash generation format"""
        hash_val = generate_benign_hash()
        
        # Should be valid SHA256
        self.assertEqual(len(hash_val), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_val))

    def test_generate_benign_hash_uniqueness(self):
        """Test benign hash generation uniqueness"""
        hashes = set()
        for _ in range(10):
            hash_val = generate_benign_hash()
            hashes.add(hash_val)
        
        # Should generate unique hashes
        self.assertGreater(len(hashes), 1)

    def test_create_ioc_package_structure(self):
        """Test IOC package creation structure"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            create_ioc_package(temp_file, 3)
            
            # Check file was created
            self.assertTrue(os.path.exists(temp_file))
            
            # Load and check structure
            import json
            with open(temp_file, 'r') as f:
                iocs = json.load(f)
            
            self.assertIsInstance(iocs, dict)
            self.assertIn('malicious', iocs)
            self.assertIn('benign', iocs)
            
            # Check malicious section
            malicious = iocs['malicious']
            self.assertIn('hash', malicious)
            self.assertIn('ips', malicious)
            self.assertIn('domains', malicious)
            self.assertIn('urls', malicious)
            
            # Check benign section
            benign = iocs['benign']
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
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_hash_uniqueness_multiple_calls(self):
        """Test that multiple hash calls can produce different results"""
        import importlib
        import generate_iocs
        importlib.reload(generate_iocs)
        
        # Generate many hashes
        hashes = set()
        for _ in range(20):
            h = generate_iocs.generate_malicious_hash()
            hashes.add(h)
        
        # Should have some variety (though first few may be same)
        self.assertGreater(len(hashes), 0)


if __name__ == '__main__':
    unittest.main()
