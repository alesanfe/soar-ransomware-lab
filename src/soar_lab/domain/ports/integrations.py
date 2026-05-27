"""Domain ports - Integration interfaces.

These protocols define the contracts for external system integrations
like IOC generation and alert transport.
The domain depends only on these abstract interfaces, not on concrete
implementations like HTTP clients or external APIs.
"""

from typing import Protocol, List, Dict, Any


class IOCGenerator(Protocol):
    """Generator for Indicators of Compromise (IOCs).

    Encapsulates the knowledge of IOC generation,
    allowing the application to generate IOCs without knowing generation logic.
    """

    def generate_malicious_hash(self, seed: Any = None) -> str:
        """Generate a simulated malicious SHA256 hash."""
        ...

    def generate_benign_hash(self, seed: Any = None) -> str:
        """Generate a simulated benign SHA256 hash."""
        ...

    def generate_ip_addresses(self, count: int = 5) -> List[str]:
        """Generate random private IP addresses."""
        ...

    def generate_domains(self, count: int = 5) -> List[str]:
        """Generate random domains."""
        ...

    def generate_urls(self, count: int = 5) -> List[str]:
        """Generate random URLs."""
        ...

    def create_ioc_package(self, count: int = 5) -> Dict[str, Any]:
        """Create a JSON package of simulated IOCs."""
        ...


class AlertTransporter(Protocol):
    """Transport for sending alerts to external systems.

    Encapsulates the knowledge of HTTP/webhook transport,
    allowing the application to send alerts without knowing about requests.
    """

    def send(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Send an alert payload and return result."""
        ...
