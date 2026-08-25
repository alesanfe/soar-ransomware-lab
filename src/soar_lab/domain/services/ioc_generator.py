"""IOC Generator - Domain logic for generating Indicators of Compromise."""

import hashlib
import random
from typing import Any

from soar_lab.domain.services._ioc_helpers import _CHARS, _TLDS, _URL_PATHS, gen_ip

__all__ = ["SimulatedIOCGenerator"]


class SimulatedIOCGenerator:
    """Domain implementation of IOCGenerator for simulated IOCs."""

    def __init__(self) -> None:
        """Initialize the SimulatedIOCGenerator with zeroed counters."""
        self._malicious_counter = 0
        self._benign_counter = 0

    def generate_malicious_hash(self, seed: Any = None) -> str:
        """Generate a simulated malicious SHA256 hash."""
        if seed is not None:
            return hashlib.sha256(str(seed).encode()).hexdigest()
        h = hashlib.sha256(f"malicious_{self._malicious_counter}".encode()).hexdigest()
        self._malicious_counter += 1
        return h

    def generate_benign_hash(self, seed: Any = None) -> str:
        """Generate a simulated benign SHA256 hash."""
        if seed is not None:
            return hashlib.sha256(str(seed).encode()).hexdigest()
        h = hashlib.sha256(f"benign_{self._benign_counter}".encode()).hexdigest()
        self._benign_counter += 1
        return h

    def generate_ip_addresses(self, count: int = 5) -> list[str]:
        """Generate random private IP addresses."""
        return [gen_ip() for _ in range(count)]

    def generate_domains(self, count: int = 5) -> list[str]:
        """Generate random domains."""
        return [
            f"{''.join(random.choices(_CHARS, k=random.randint(5, 12)))}.{random.choice(_TLDS)}"
            for _ in range(count)
        ]

    def generate_urls(self, count: int = 5) -> list[str]:
        """Generate random URLs."""
        domains = self.generate_domains(count)
        return [
            f"{random.choice(['http', 'https'])}://{domains[i]}/{random.choice(_URL_PATHS)}"
            for i in range(count)
        ]

    def generate_ioc(self, alert_id: str = "", is_malicious: bool = True) -> dict[str, Any]:
        """Generate a single IOC dict for an alert."""
        h = self.generate_malicious_hash() if is_malicious else self.generate_benign_hash()
        return {
            "hash": h,
            "ip": gen_ip(),
            "domain": self.generate_domains(1)[0],
            "url": self.generate_urls(1)[0],
        }

    def create_ioc_package(self, count: int = 5) -> dict[str, Any]:
        """Create a JSON package of simulated IOCs."""
        return {
            "malicious": {
                "hash": self.generate_malicious_hash(),
                "ips": self.generate_ip_addresses(count),
                "domains": self.generate_domains(count),
                "urls": self.generate_urls(count),
            },
            "benign": {
                "hash": self.generate_benign_hash(),
                "ips": self.generate_ip_addresses(count),
                "domains": self.generate_domains(count),
                "urls": self.generate_urls(count),
            },
        }
