#!/usr/bin/env python3
"""Unit tests for ioc_generator.py."""

from soar_lab.domain.services._ioc_helpers import _TLDS, _URL_PATHS
from soar_lab.domain.services.ioc_generator import SimulatedIOCGenerator


class TestSimulatedIOCGenerator:
    """Test SimulatedIOCGenerator domain logic."""

    def test_initialization(self):
        """Test generator initialization."""
        generator = SimulatedIOCGenerator()
        assert generator._malicious_counter == 0
        assert generator._benign_counter == 0

    def test_generate_malicious_hash(self):
        """Test malicious hash generation."""
        generator = SimulatedIOCGenerator()
        hash1 = generator.generate_malicious_hash()
        hash2 = generator.generate_malicious_hash()

        assert hash1 != hash2
        assert len(hash1) == 64  # SHA256 hex length
        assert generator._malicious_counter == 2

    def test_generate_malicious_hash_with_seed(self):
        """Test malicious hash generation with seed."""
        generator = SimulatedIOCGenerator()
        hash1 = generator.generate_malicious_hash(seed="test")
        hash2 = generator.generate_malicious_hash(seed="test")

        assert hash1 == hash2  # Same seed should produce same hash
        assert generator._malicious_counter == 0  # Counter should not increment with seed

    def test_generate_benign_hash(self):
        """Test benign hash generation."""
        generator = SimulatedIOCGenerator()
        hash1 = generator.generate_benign_hash()
        hash2 = generator.generate_benign_hash()

        assert hash1 != hash2
        assert len(hash1) == 64
        assert generator._benign_counter == 2

    def test_generate_benign_hash_with_seed(self):
        """Test benign hash generation with seed."""
        generator = SimulatedIOCGenerator()
        hash1 = generator.generate_benign_hash(seed="test")
        hash2 = generator.generate_benign_hash(seed="test")

        assert hash1 == hash2
        assert generator._benign_counter == 0

    def test_generate_ip_addresses(self):
        """Test IP address generation."""
        generator = SimulatedIOCGenerator()
        ips = generator.generate_ip_addresses(count=5)

        assert len(ips) == 5
        for ip in ips:
            assert isinstance(ip, str)
            parts = ip.split(".")
            assert len(parts) == 4
            assert all(part.isdigit() for part in parts)

    def test_generate_ip_addresses_default_count(self):
        """Test IP address generation with default count."""
        generator = SimulatedIOCGenerator()
        ips = generator.generate_ip_addresses()

        assert len(ips) == 5
        for ip in ips:
            parts = ip.split(".")
            assert len(parts) == 4
            for part in parts:
                assert 0 <= int(part) <= 255

    def test_generate_domains(self):
        """Test domain generation."""
        generator = SimulatedIOCGenerator()
        domains = generator.generate_domains(count=3)

        assert len(domains) == 3
        for domain in domains:
            assert isinstance(domain, str)
            assert "." in domain
            name, tld = domain.rsplit(".", 1)
            assert len(name) >= 5
            assert len(name) <= 12

    def test_generate_domains_default_count(self):
        """Test domain generation with default count."""
        generator = SimulatedIOCGenerator()
        domains = generator.generate_domains()

        assert len(domains) == 5
        for domain in domains:
            assert "." in domain
            assert len(domain) > 5
            assert all(c.isalnum() or c == "." or c == "-" for c in domain)

    def test_generate_urls(self):
        """Test URL generation."""
        generator = SimulatedIOCGenerator()
        urls = generator.generate_urls(count=3)

        assert len(urls) == 3
        for url in urls:
            assert isinstance(url, str)
            assert url.startswith("http://") or url.startswith("https://")
            assert "://" in url

    def test_generate_urls_default_count(self):
        """Test URL generation with default count."""
        generator = SimulatedIOCGenerator()
        urls = generator.generate_urls()

        assert len(urls) == 5
        for url in urls:
            assert url.startswith(("http://", "https://"))
            assert "." in url

    def test_create_ioc_package(self):
        """Test IOC package creation."""
        generator = SimulatedIOCGenerator()
        package = generator.create_ioc_package(count=3)

        assert "malicious" in package
        assert "benign" in package
        assert "hash" in package["malicious"]
        assert "ips" in package["malicious"]
        assert "domains" in package["malicious"]
        assert "urls" in package["malicious"]
        assert len(package["malicious"]["ips"]) == 3
        assert len(package["malicious"]["domains"]) == 3
        assert len(package["malicious"]["urls"]) == 3

    def test_create_ioc_package_default_count(self):
        """Test IOC package creation with default count."""
        generator = SimulatedIOCGenerator()
        package = generator.create_ioc_package()

        assert len(package["malicious"]["ips"]) == 5
        assert len(package["benign"]["ips"]) == 5


class TestGenIPMutationHardening:
    """Deterministic kills via captured random call args."""

    def _capture(self, monkeypatch, prefix):
        import soar_lab.domain.services._ioc_helpers as h

        ints = []
        monkeypatch.setattr(h.random, "choice", lambda seq: prefix)
        monkeypatch.setattr(h.random, "randint", lambda a, b: ints.append((a, b)) or a)
        return h, ints

    def test_prefix_10_octets(self, monkeypatch):
        h, ints = self._capture(monkeypatch, "10")
        ip = h.gen_ip()
        assert ip == "10.0.0.1"
        assert ints == [(0, 255), (0, 255), (1, 254)]

    def test_prefix_172_octets(self, monkeypatch):
        h, ints = self._capture(monkeypatch, "172")
        ip = h.gen_ip()
        assert ip == "172.16.0.1"
        assert ints == [(16, 31), (0, 255), (1, 254)]

    def test_prefix_192_octets(self, monkeypatch):
        h, ints = self._capture(monkeypatch, "192")
        ip = h.gen_ip()
        assert ip == "192.168.0.1"
        assert ints == [(0, 255), (1, 254)]

    def test_prefix_candidates(self, monkeypatch):
        import soar_lab.domain.services._ioc_helpers as h

        seen = []
        monkeypatch.setattr(h.random, "choice", lambda seq: seen.append(seq) or seq[0])
        h.gen_ip()
        assert seen == [["10", "172", "192"]]


class TestIOCGeneratorMutationHardening:
    def test_counters_start_zero_and_increment(self):
        g = SimulatedIOCGenerator()
        assert g._malicious_counter == 0 and g._benign_counter == 0
        g.generate_malicious_hash()
        assert g._malicious_counter == 1 and g._benign_counter == 0
        g.generate_benign_hash()
        assert g._benign_counter == 1

    def test_hash_matches_counter_seed(self):
        import hashlib

        g = SimulatedIOCGenerator()
        g.generate_malicious_hash()
        h = g.generate_malicious_hash()
        assert h == hashlib.sha256(b"malicious_1").hexdigest()

    def test_seeded_hash_uses_str_seed(self):
        import hashlib

        g = SimulatedIOCGenerator()
        assert g.generate_malicious_hash(seed=42) == hashlib.sha256(b"42").hexdigest()
        # seeded call must not consume the counter
        assert g._malicious_counter == 0

    def test_domain_length_bounds(self, monkeypatch):
        import soar_lab.domain.services.ioc_generator as m

        captured = []
        real_randint = m.random.randint
        monkeypatch.setattr(
            m.random, "randint", lambda a, b: captured.append((a, b)) or real_randint(a, b)
        )
        g = SimulatedIOCGenerator()
        g.generate_domains(1)
        assert captured == [(5, 12)]

    def test_ioc_dict_keys_exact(self):
        g = SimulatedIOCGenerator()
        ioc = g.generate_ioc(alert_id="a1")
        assert set(ioc) == {"hash", "ip", "domain", "url"}
        assert len(ioc["hash"]) == 64
        assert ioc["domain"].split(".")[-1] in _TLDS

    def test_ioc_package_structure_exact(self):
        g = SimulatedIOCGenerator()
        pkg = g.create_ioc_package(3)
        assert set(pkg) == {"malicious", "benign"}
        for side in ("malicious", "benign"):
            assert set(pkg[side]) == {"hash", "ips", "domains", "urls"}
            assert len(pkg[side]["ips"]) == 3
            assert len(pkg[side]["domains"]) == 3
            assert len(pkg[side]["urls"]) == 3
            for u in pkg[side]["urls"]:
                scheme, rest = u.split("://")
                assert scheme in ("http", "https")
                path = rest.split("/", 1)[1]
                assert path in _URL_PATHS

    def test_ip_addresses_count(self):
        g = SimulatedIOCGenerator()
        assert len(g.generate_ip_addresses(4)) == 4

    def test_generate_ioc_default_is_malicious(self):
        import hashlib

        g = SimulatedIOCGenerator()
        ioc = g.generate_ioc()
        assert ioc["hash"] == hashlib.sha256(b"malicious_0").hexdigest()

    def test_generate_ioc_false_is_benign(self):
        import hashlib

        g = SimulatedIOCGenerator()
        ioc = g.generate_ioc(is_malicious=False)
        assert ioc["hash"] == hashlib.sha256(b"benign_0").hexdigest()

    def test_generate_ioc_single_domain_url(self, monkeypatch):

        from unittest.mock import MagicMock

        g = SimulatedIOCGenerator()
        d = MagicMock(return_value=["d.com"])
        u = MagicMock(return_value=["http://d.com/x"])
        monkeypatch.setattr(g, "generate_domains", d)
        monkeypatch.setattr(g, "generate_urls", u)
        g.generate_ioc()
        d.assert_called_once_with(1)
        u.assert_called_once_with(1)

    def test_benign_hash_explicit_seed(self):
        import hashlib

        g = SimulatedIOCGenerator()
        assert g.generate_benign_hash("x") == hashlib.sha256(b"x").hexdigest()
