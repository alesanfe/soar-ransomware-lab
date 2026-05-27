#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Alert Generator (Domain)
Generates realistic simulated ransomware / benign alert payloads.
Responsibility: data creation only (no HTTP, no I/O).
This is domain logic - pure business rules without infrastructure dependencies.
"""

import random
from datetime import datetime, timezone
from typing import Any, Dict, List

_ALERT_SEQ_MAX = 9999


class AlertGenerator:
    """Generates simulated SIEM alert payloads."""

    MALICIOUS_HASHES = [
        "44d88612fea8a8f36de82e1278abb02f44d88612fea8a8f36de82e1278abb02f",
        "d41d8cd98f00b204e9800998ecf8427ed41d8cd98f00b204e9800998ecf8427e",
        "098f6bcd4621d373cade4e832627b4f6098f6bcd4621d373cade4e832627b4f6",
        "5d41402abc4b2a76b9719d911017c5925d41402abc4b2a76b9719d911017c592",
    ]
    BENIGN_HASHES = [
        "e3b0c44298fc1c149afbf4c8996fb924e3b0c44298fc1c149afbf4c8996fb924",
        "a665a45920422f9d417e4867efdc4fb8a665a45920422f9d417e4867efdc4fb8",
        "7c222fb2927d828af22f592134e893247c222fb2927d828af22f592134e89324",
    ]
    SAMPLE_IPS = [
        "192.168.1.100", "10.0.0.50", "172.16.0.25",
        "192.168.2.75", "10.1.1.200", "172.20.0.10",
    ]
    MALICIOUS_IPS = ["185.220.101.182", "198.54.131.67", "94.102.52.10"]
    HOSTNAMES = ["WIN-001", "WIN-002", "WIN-003", "SRV-001", "LAPTOP-001", "DC-001"]

    def generate(self, alert_type: str = "malicious") -> Dict[str, Any]:
        """Generate an alert payload.

        Args:
            alert_type: "malicious" or "benign".

        Returns:
            Alert dict payload.
        """
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat().replace("+00:00", "Z")
        unix_ts = int(now.timestamp())
        seq = random.randint(1000, _ALERT_SEQ_MAX)
        alert_id = f"ALERT-{unix_ts:010d}-{seq:04d}"
        is_malicious = alert_type == "malicious"

        hash_value = random.choice(
            self.MALICIOUS_HASHES if is_malicious else self.BENIGN_HASHES
        )
        src_ip = random.choice(self.MALICIOUS_IPS if is_malicious else self.SAMPLE_IPS)
        severity = random.choice([2, 3]) if is_malicious else random.choice([0, 1])
        hostname = random.choice(self.HOSTNAMES)

        return {
            "alert_id": alert_id,
            "hostname": hostname,
            "src_ip": src_ip,
            "ip_address": src_ip,
            "hash": hash_value,
            "severity": severity,
            "source": "siem-ransomware-detection" if is_malicious else "siem-file-monitoring",
            "timestamp": timestamp,
            "detection_time": timestamp,
            "event_type": "ransomware_detection",
            "description": (
                f"Ransomware activity detected on {hostname}"
                if is_malicious
                else f"Suspicious activity detected on {hostname}"
            ),
            "affected_files": (
                [
                    "C:\\Users\\Documents\\important.docx",
                    "C:\\Data\\financial.xlsx",
                    "C:\\Backup\\database.sql",
                ]
                if is_malicious
                else []
            ),
            "mitre_tactics": ["TA0040"] if is_malicious else [],
            "mitre_techniques": ["T1486"] if is_malicious else [],
            "mitre_attack": (
                {"tactics": ["Impact"], "techniques": ["Data Encrypted for Impact"]}
                if is_malicious
                else {"tactics": [], "techniques": []}
            ),
            "user_account": "johndoe",
            "process_name": "ransomware.exe" if is_malicious else "setup.exe",
            "command_line": (
                "C:\\Users\\johndoe\\ransomware.exe"
                if is_malicious
                else "C:\\Users\\johndoe\\setup.exe"
            ),
            "parent_process": "explorer.exe",
            "file_size": 1024576,
            "file_path": (
                "C:\\Users\\johndoe\\ransomware.exe"
                if is_malicious
                else "C:\\Users\\johndoe\\setup.exe"
            ),
            "network_connections": [
                {
                    "dst_ip": "1.1.1.1",
                    "destination_ip": "1.1.1.1",
                    "dst_port": 443,
                    "destination_port": 443,
                    "protocol": "tcp",
                }
            ],
            "registry_changes": [],
            "detection_rules": ["Suspicious File Execution"],
            "confidence": 95 if is_malicious else 25,
            "impact_assessment": {
                "data_affected": "High" if is_malicious else "Low",
                "systems_affected": 1 if is_malicious else 0,
                "affected_hosts": [hostname] if is_malicious else [],
                "business_impact": "High" if is_malicious else "Low",
                "recovery_time_estimate": "4-8 hours" if is_malicious else "< 1 hour",
                "files_encrypted": 100 if is_malicious else 0,
            },
            "false_positive_indicators": [] if is_malicious else ["Known process"],
            "whitelist_status": "not_whitelisted",
        }

    def generate_malicious(self) -> Dict[str, Any]:
        return self.generate("malicious")

    def generate_benign(self) -> Dict[str, Any]:
        return self.generate("benign")

    def generate_test(self, alert_id: str = None) -> Dict[str, Any]:
        alert = self.generate()
        if alert_id:
            alert["alert_id"] = alert_id
        alert["event_type"] = "test_alert"
        return alert
