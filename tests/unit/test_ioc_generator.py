#!/usr/bin/env python3
"""
Unit tests for ioc_generator.py
"""

import pytest

from soar_lab.domain.ioc_generator import SimulatedIOCGenerator


class TestSimulatedIOCGenerator:
    """Test SimulatedIOCGenerator domain logic"""

    def test_initialization(self):
        """Test generator initialization"""
        generator = SimulatedIOCGenerator()
        assert generator._malicious_counter == 0
        assert generator._benign_counter == 0

    def test_generate_malicious_hash(self):
        """Test malicious hash generation"""
        generator = SimulatedIOCGenerator()
        hash1 = generator.generate_malicious_hash()
        hash2 = generator.generate_malicious_hash()
        
        assert hash1 != hash2
        assert len(hash1) == 64  # SHA256 hex length
        assert generator._malicious_counter == 2

    def test_generate_malicious_hash_with_seed(self):
        """Test malicious hash generation with seed"""
        generator = SimulatedIOCGenerator()
        hash1 = generator.generate_malicious_hash(seed="test")
        hash2 = generator.generate_malicious_hash(seed="test")
        
        assert hash1 == hash2  # Same seed should produce same hash
        assert generator._malicious_counter == 0  # Counter should not increment with seed

    def test_generate_benign_hash(self):
        """Test benign hash generation"""
        generator = SimulatedIOCGenerator()
        hash1 = generator.generate_benign_hash()
        hash2 = generator.generate_benign_hash()
        
        assert hash1 != hash2
        assert len(hash1) == 64
        assert generator._benign_counter == 2

    def test_generate_benign_hash_with_seed(self):
        """Test benign hash generation with seed"""
        generator = SimulatedIOCGenerator()
        hash1 = generator.generate_benign_hash(seed="test")
        hash2 = generator.generate_benign_hash(seed="test")
        
        assert hash1 == hash2
        assert generator._benign_counter == 0

    def test_generate_ip_addresses(self):
        """Test IP address generation"""
        generator = SimulatedIOCGenerator()
        ips = generator.generate_ip_addresses(count=5)
        
        assert len(ips) == 5
        for ip in ips:
            assert isinstance(ip, str)
            parts = ip.split('.')
            assert len(parts) == 4
            assert all(part.isdigit() for part in parts)

    def test_generate_ip_addresses_default_count(self):
        """Test IP address generation with default count"""
        generator = SimulatedIOCGenerator()
        ips = generator.generate_ip_addresses()
        
        assert len(ips) == 5

    def test_generate_domains(self):
        """Test domain generation"""
        generator = SimulatedIOCGenerator()
        domains = generator.generate_domains(count=3)
        
        assert len(domains) == 3
        for domain in domains:
            assert isinstance(domain, str)
            assert '.' in domain
            name, tld = domain.rsplit('.', 1)
            assert len(name) >= 5
            assert len(name) <= 12

    def test_generate_domains_default_count(self):
        """Test domain generation with default count"""
        generator = SimulatedIOCGenerator()
        domains = generator.generate_domains()
        
        assert len(domains) == 5

    def test_generate_urls(self):
        """Test URL generation"""
        generator = SimulatedIOCGenerator()
        urls = generator.generate_urls(count=3)
        
        assert len(urls) == 3
        for url in urls:
            assert isinstance(url, str)
            assert url.startswith('http://') or url.startswith('https://')
            assert '://' in url

    def test_generate_urls_default_count(self):
        """Test URL generation with default count"""
        generator = SimulatedIOCGenerator()
        urls = generator.generate_urls()
        
        assert len(urls) == 5

    def test_create_ioc_package(self):
        """Test IOC package creation"""
        generator = SimulatedIOCGenerator()
        package = generator.create_ioc_package(count=3)
        
        assert 'malicious' in package
        assert 'benign' in package
        assert 'hash' in package['malicious']
        assert 'ips' in package['malicious']
        assert 'domains' in package['malicious']
        assert 'urls' in package['malicious']
        assert len(package['malicious']['ips']) == 3
        assert len(package['malicious']['domains']) == 3
        assert len(package['malicious']['urls']) == 3

    def test_create_ioc_package_default_count(self):
        """Test IOC package creation with default count"""
        generator = SimulatedIOCGenerator()
        package = generator.create_ioc_package()
        
        assert len(package['malicious']['ips']) == 5
        assert len(package['benign']['ips']) == 5
