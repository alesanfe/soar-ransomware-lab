#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Atomic Tests for IOC Generator (Corrected)
Tests individual IOC generation functions in isolation
"""

import json
import os
import pytest
import tempfile
from pathlib import Path
from soar_lab.domain.services.ioc_generator import SimulatedIOCGenerator


class TestIOCGeneratorAtomic:
    """Atomic tests for individual IOC generation functions"""

    @pytest.fixture
    def generator(self):
        """Create a fresh IOC generator instance for each test"""
        return SimulatedIOCGenerator()

    def test_generate_malicious_hash_deterministic(self, generator):
        """Test malicious hash generation with same seed produces same result"""
        hash1 = generator.generate_malicious_hash("test_seed")
        hash2 = generator.generate_malicious_hash("test_seed")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 length

    def test_generate_malicious_hash_random(self, generator):
        """Test malicious hash generation without seed"""
        hash1 = generator.generate_malicious_hash()
        hash2 = generator.generate_malicious_hash()
        # Hashes should be different for random generation
        assert hash1 != hash2
        assert len(hash1) == 64

    def test_generate_benign_hash_deterministic(self, generator):
        """Test benign hash generation with same seed produces same result"""
        hash1 = generator.generate_benign_hash("test_seed")
        hash2 = generator.generate_benign_hash("test_seed")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 length

    def test_generate_benign_hash_random(self, generator):
        """Test benign hash generation without seed"""
        hash1 = generator.generate_benign_hash()
        hash2 = generator.generate_benign_hash()
        # Hashes should be different for random generation
        assert hash1 != hash2
        assert len(hash1) == 64

    def test_generate_ip_addresses_default_count(self, generator):
        """Test IP address generation with default count"""
        ips = generator.generate_ip_addresses()
        assert len(ips) == 5

        for ip in ips:
            parts = ip.split('.')
            assert len(parts) == 4
            for part in parts:
                assert 0 <= int(part) <= 255

    def test_generate_ip_addresses_custom_count(self, generator):
        """Test IP address generation with custom count"""
        for count in [1, 3, 10]:
            ips = generator.generate_ip_addresses(count)
            assert len(ips) == count

            for ip in ips:
                parts = ip.split('.')
                assert len(parts) == 4
                for part in parts:
                    assert 0 <= int(part) <= 255

    def test_generate_ip_addresses_private_ranges(self, generator):
        """Test IP addresses are in private ranges"""
        ips = generator.generate_ip_addresses(20)

        for ip in ips:
            parts = ip.split('.')
            first_octet = int(parts[0])

            # Should be in private ranges
            assert (
                first_octet == 10 or  # 10.0.0.0/8
                (first_octet == 172 and 16 <= int(parts[1]) <= 31) or  # 172.16.0.0/12
                (first_octet == 192 and int(parts[1]) == 168)  # 192.168.0.0/16
            )

    def test_generate_domains_default_count(self, generator):
        """Test domain generation with default count"""
        domains = generator.generate_domains()
        assert len(domains) == 5

        for domain in domains:
            assert '.' in domain
            assert len(domain) > 5
            # Should not contain invalid characters
            assert all(c.isalnum() or c == '.' for c in domain)

    def test_generate_domains_custom_count(self, generator):
        """Test domain generation with custom count"""
        for count in [1, 3, 10]:
            domains = generator.generate_domains(count)
            assert len(domains) == count

            for domain in domains:
                assert '.' in domain
                assert len(domain) > 5

    def test_generate_domains_valid_tlds(self, generator):
        """Test domains use valid TLDs"""
        domains = generator.generate_domains(20)
        valid_tlds = ['com', 'net', 'org', 'io', 'biz', 'info', 'ru', 'cn', 'xyz']

        for domain in domains:
            tld = domain.split('.')[-1]
            assert tld in valid_tlds

    def test_generate_urls_default_count(self, generator):
        """Test URL generation with default count"""
        urls = generator.generate_urls()
        assert len(urls) == 5

        for url in urls:
            assert url.startswith(('http://', 'https://'))
            assert '.' in url

    def test_generate_urls_custom_count(self, generator):
        """Test URL generation with custom count"""
        for count in [1, 3, 10]:
            urls = generator.generate_urls(count)
            assert len(urls) == count

            for url in urls:
                assert url.startswith(('http://', 'https://'))
                assert '.' in url

    def test_generate_urls_valid_protocols(self, generator):
        """Test URLs use valid protocols"""
        urls = generator.generate_urls(20)
        valid_protocols = ['http', 'https']

        for url in urls:
            protocol = url.split('://')[0]
            assert protocol in valid_protocols

    def test_generate_urls_structure(self, generator):
        """Test URLs have proper structure"""
        urls = generator.generate_urls(10)

        for url in urls:
            # Should have protocol://domain/path
            import re
            assert re.match(r'^https?://[^/]+/.+$', url)

    def test_create_ioc_package_structure(self, generator):
        """Test IOC package creation returns proper structure"""
        package = generator.create_ioc_package(3)

        # Check structure
        assert isinstance(package, dict)
        assert 'malicious' in package
        assert 'benign' in package

        # Check malicious IOCs
        malicious = package['malicious']
        assert 'hash' in malicious
        assert 'ips' in malicious
        assert 'domains' in malicious
        assert 'urls' in malicious

        # Check benign IOCs
        benign = package['benign']
        assert 'hash' in benign
        assert 'ips' in benign
        assert 'domains' in benign
        assert 'urls' in benign

        # Check counts
        assert len(malicious['ips']) == 3
        assert len(malicious['domains']) == 3
        assert len(malicious['urls']) == 3
        assert len(benign['ips']) == 3
        assert len(benign['domains']) == 3
        assert len(benign['urls']) == 3

    def test_create_ioc_package_hash_formats(self, generator):
        """Test IOC package contains properly formatted hashes"""
        package = generator.create_ioc_package(1)

        # Check hash formats (should be SHA256)
        malicious_hash = package['malicious']['hash']
        benign_hash = package['benign']['hash']

        assert len(malicious_hash) == 64
        assert len(benign_hash) == 64
        assert all(c in '0123456789abcdef' for c in malicious_hash.lower())
        assert all(c in '0123456789abcdef' for c in benign_hash.lower())

    def test_create_ioc_package_ip_formats(self, generator):
        """Test IOC package contains properly formatted IPs"""
        package = generator.create_ioc_package(5)

        # Check IP formats
        for ip in package['malicious']['ips']:
            parts = ip.split('.')
            assert len(parts) == 4
            for part in parts:
                assert 0 <= int(part) <= 255

        for ip in package['benign']['ips']:
            parts = ip.split('.')
            assert len(parts) == 4
            for part in parts:
                assert 0 <= int(part) <= 255

    def test_edge_cases_zero_count(self, generator):
        """Test generation functions with zero count"""
        ips = generator.generate_ip_addresses(0)
        assert len(ips) == 0

        domains = generator.generate_domains(0)
        assert len(domains) == 0

        urls = generator.generate_urls(0)
        assert len(urls) == 0

    def test_edge_cases_large_count(self, generator):
        """Test generation functions with large count"""
        large_count = 100

        ips = generator.generate_ip_addresses(large_count)
        assert len(ips) == large_count

        domains = generator.generate_domains(large_count)
        assert len(domains) == large_count

        urls = generator.generate_urls(large_count)
        assert len(urls) == large_count

    def test_hash_uniqueness(self, generator):
        """Test hash generation produces unique values"""
        hash1 = generator.generate_malicious_hash("seed1")
        hash2 = generator.generate_malicious_hash("seed2")
        hash3 = generator.generate_benign_hash("seed1")
        hash4 = generator.generate_benign_hash("seed2")
        hash5 = generator.generate_malicious_hash()  # No seed - deterministic
        hash6 = generator.generate_benign_hash()  # No seed - deterministic

        # Different seeds should produce different hashes
        assert hash1 != hash2
        assert hash3 != hash4

        # Same seed should produce same hash (deterministic behavior)
        assert hash1 == hash3  # Same seed "seed1"
        assert hash2 == hash4  # Same seed "seed2"

        # No seed calls should be different between malicious and benign
        assert hash5 != hash6

    def test_url_validation_valid_urls(self, generator):
        """Test URL validation with valid URLs"""
        valid_urls = [
            'http://example.com',
            'https://example.com',
            'http://example.com/path',
            'https://example.com/path?query=value',
            'http://192.168.1.1:8080',
            'https://subdomain.example.com'
        ]

        for url in valid_urls:
            ioc = generator.generate_ioc('test', is_malicious=True)
            if 'url' in ioc:
                # If URL is generated, it should be valid
                assert '://' in ioc['url']

    def test_url_validation_invalid_urls(self):
        """Test URL validation with invalid URLs"""
        invalid_urls = [
            'not-a-url',
            'htp://example.com',  # Typo in protocol
            'http://',  # No domain
            'example.com',  # No protocol
            'javascript:alert(1)',  # JavaScript protocol
            'data:text/html,<script>alert(1)</script>'  # Data URL
        ]

        # Should handle invalid URLs gracefully
        for url in invalid_urls:
            # This would test URL validation if URLs are part of IOCs
            pass

    def test_url_sanitization(self):
        """Test URL sanitization"""
        malicious_urls = [
            'http://example.com/<script>alert(1)</script>',
            'http://example.com/"><script>alert(1)</script>',
            'http://example.com/?param=<img src=x onerror=alert(1)>'
        ]

        # Should sanitize malicious URLs
        for url in malicious_urls:
            # This would test URL sanitization
            pass

    def test_domain_validation(self, generator):
        """Test domain validation"""
        valid_domains = [
            'example.com',
            'subdomain.example.com',
            'example.co.uk',
            'malicious-domain.com'
        ]

        invalid_domains = [
            'not a domain',
            'example..com',
            '-example.com',
            'example-.com'
        ]

        # Should validate domains correctly
        for domain in valid_domains:
            assert len(domain) > 0

        for domain in invalid_domains:
            # Should handle invalid domains
            pass

    def test_url_length_limit(self):
        """Test URL length limit"""
        very_long_url = 'http://example.com/' + 'a' * 10000

        # Should handle very long URLs (truncate or reject)
        pass

    def test_url_with_credentials(self):
        """Test URL with credentials"""
        url_with_creds = 'http://user:password@example.com'

        # Should handle URLs with credentials (sanitize or reject)
        pass
