import hashlib
import random
import re
import time
from datetime import datetime, timezone
from typing import Dict, List


class AlertGenerator:
    MALICIOUS_IPS: List[str] = [
        "185.220.101.42",
        "198.51.100.15",
        "203.0.113.88",
        "192.0.2.50",
        "10.218.224.139",
    ]
    BENIGN_IPS: List[str] = [
        "10.0.0.1",
        "192.168.1.10",
        "172.16.0.5",
    ]

    def __init__(self) -> None:
        self._counter = 0

    def _id(self) -> str:
        self._counter += 1
        return f"ALERT-{int(time.time())}-{self._counter:04d}"

    def _hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    def generate_malicious(self) -> Dict[str, any]:
        return self._build(
            alert_type="ransomware",
            event_type="ransomware_detection",
            severity=random.choice([2, 3]),
            ips=self.MALICIOUS_IPS,
        )

    def generate_benign(self) -> Dict[str, any]:
        return self._build(
            alert_type="benign",
            event_type="benign_activity",
            severity=random.choice([0, 1]),
            ips=self.BENIGN_IPS,
        )

    def generate(self) -> Dict[str, any]:
        return self.generate_malicious()

    def generate_test(self, alert_id: str = None) -> Dict[str, any]:
        alert = self._build(
            alert_type="test",
            event_type="test_alert",
            severity=1,
            ips=self.BENIGN_IPS,
        )
        if alert_id is not None:
            alert["alert_id"] = alert_id
        return alert

    def _build(self, alert_type: str, event_type: str, severity: int, ips: List[str]) -> Dict[str, any]:
        ip = random.choice(ips)
        now = datetime.now(timezone.utc).isoformat()
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
