"""Simulated alert generator for ransomware detection testing."""

import hashlib
import random
import time
from datetime import UTC, datetime
from typing import Any

__all__ = ["AlertGenerator"]


class AlertGenerator:
    """Generates simulated malicious and benign security alerts."""

    MALICIOUS_IPS: list[str] = [
        "185.220.101.42",
        "198.51.100.15",
        "203.0.113.88",
        "192.0.2.50",
        "10.218.224.139",
    ]
    BENIGN_IPS: list[str] = [
        "10.0.0.1",
        "192.168.1.10",
        "172.16.0.5",
    ]

    def __init__(self, seq_offset: int | None = None) -> None:
        r"""Initialize the AlertGenerator.

        ``_counter`` stays 0-based (deterministic per-instance sequence);
        the emitted ID adds a random per-instance phase so two generators
        producing an ID inside the same second do not collide — the
        ``ALERT-\\d{10}-\\d{4}`` schema pattern leaves only 4 digits of
        sequence space. ``seq_offset`` pins the phase for tests.
        """
        self._counter = 0
        self._seq_offset = (
            seq_offset if seq_offset is not None else random.randrange(10_000)
        ) % 10_000

    def _id(self) -> str:
        """Generate a unique alert ID using a timestamp and counter.

        Returns:
            A string in the form ``ALERT-<timestamp>-<counter>``.
        """
        self._counter += 1
        seq = (self._seq_offset + self._counter) % 10_000
        return f"ALERT-{int(time.time())}-{seq:04d}"

    def _hash(self, data: str) -> str:
        """Compute a SHA256 hex digest of the given data.

        Args:
            data: String to hash.

        Returns:
            Hexadecimal SHA256 digest string.
        """
        return hashlib.sha256(data.encode()).hexdigest()

    def generate_malicious(self) -> dict[str, Any]:
        """Generate a simulated malicious ransomware detection alert.

        Returns:
            A dictionary representing a malicious alert.
        """
        return self._build(
            alert_type="ransomware",
            event_type="ransomware_detection",
            severity=random.choice([2, 3]),
            ips=self.MALICIOUS_IPS,
        )

    def generate_benign(self) -> dict[str, Any]:
        """Generate a simulated benign activity alert.

        Returns:
            A dictionary representing a benign alert.
        """
        return self._build(
            alert_type="benign",
            event_type="benign_activity",
            severity=1,
            ips=self.BENIGN_IPS,
        )

    def generate(self) -> dict[str, Any]:
        """Generate a default alert (alias for ``generate_malicious``).

        Returns:
            A dictionary representing a malicious alert.
        """
        return self.generate_malicious()

    def generate_test(self, alert_id: str = None) -> dict[str, Any]:
        """Generate a test alert with an optional custom alert ID.

        Args:
            alert_id: Optional alert ID to override the generated one.

        Returns:
            A dictionary representing a test alert.
        """
        alert = self._build(
            alert_type="test",
            event_type="test_alert",
            severity=1,
            ips=self.BENIGN_IPS,
        )
        if alert_id is not None:
            alert["alert_id"] = alert_id
        return alert

    def _build(
        self, alert_type: str, event_type: str, severity: int, ips: list[str]
    ) -> dict[str, Any]:
        """Build an alert dictionary from the given parameters.

        Args:
            alert_type: Type label for the alert (e.g. ``"ransomware"``).
            event_type: Event type label for the alert.
            severity: Severity level (1–3, matches AlertSeverity enum).
            ips: List of IP addresses to sample from.

        Returns:
            A dictionary representing the assembled alert.
        """
        ip = random.choice(ips)
        now = datetime.now(UTC).isoformat()
        alert_id = self._id()
        return {
            "alert_id": alert_id,
            "hostname": f"HOST-{self._counter:04d}",
            "src_ip": ip,
            "hash": self._hash(alert_id + ip),
            "severity": severity,
            "timestamp": now,
            "event_type": event_type,
            "alert_type": alert_type,
        }
