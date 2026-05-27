"""IOC Generator - Domain logic for generating Indicators of Compromise."""

import hashlib
import random
from typing import List, Dict, Any


class SimulatedIOCGenerator:
    """Domain implementation of IOCGenerator for simulated IOCs."""

    def __init__(self):
        self._malicious_counter = 0
        self._benign_counter = 0

    def generate_malicious_hash(self, seed: Any = None) -> str:
        """Generate a simulated malicious SHA256 hash."""
        if seed is not None:
            return hashlib.sha256(str(seed).encode()).hexdigest()

        hash_input = f"malicious_{self._malicious_counter}"
        self._malicious_counter += 1
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def generate_benign_hash(self, seed: Any = None) -> str:
        """Generate a simulated benign SHA256 hash."""
        if seed is not None:
            return hashlib.sha256(str(seed).encode()).hexdigest()

        hash_input = f"benign_{self._benign_counter}"
        self._benign_counter += 1
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def generate_ip_addresses(self, count: int = 5) -> List[str]:
        """Generate random private IP addresses."""
        ips = []
        for _ in range(count):
            prefix = random.choice(['10', '172', '192'])
            if prefix == '10':
                ip = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            elif prefix == '172':
                ip = f"172.{random.randint(16, 31)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            else:
                ip = f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"
            ips.append(ip)
        return ips

    def generate_domains(self, count: int = 5) -> List[str]:
        """Generate random domains."""
        tlds = ['com', 'net', 'org', 'io', 'biz', 'info', 'ru', 'cn', 'xyz']
        domains = []
        for _ in range(count):
            name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=random.randint(5, 12)))
            tld = random.choice(tlds)
            domains.append(f"{name}.{tld}")
        return domains

    def generate_urls(self, count: int = 5) -> List[str]:
        """Generate random URLs."""
        urls = []
        domains = self.generate_domains(count)
        paths = ['download', 'api/v1', 'update', 'config', 'index.php', 'login', 'payload.exe', 'script.js']
        for i in range(count):
            protocol = random.choice(['http', 'https'])
            domain = domains[i]
            path = random.choice(paths)
            urls.append(f"{protocol}://{domain}/{path}")
        return urls

    def create_ioc_package(self, count: int = 5) -> Dict[str, Any]:
        """Create a JSON package of simulated IOCs."""
        return {
            'malicious': {
                'hash': self.generate_malicious_hash(),
                'ips': self.generate_ip_addresses(count),
                'domains': self.generate_domains(count),
                'urls': self.generate_urls(count)
            },
            'benign': {
                'hash': self.generate_benign_hash(),
                'ips': self.generate_ip_addresses(count),
                'domains': self.generate_domains(count),
                'urls': self.generate_urls(count)
            }
        }
