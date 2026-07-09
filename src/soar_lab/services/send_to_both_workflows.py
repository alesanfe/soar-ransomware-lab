#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Send Alerts to Both Workflows
Sends alerts to both simulated and Wazuh workflows using execution endpoint.

Usage:
    python3 -m soar_lab.services.send_to_both_workflows --type malicious --single
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from soar_lab.integrations.shuffle_client import ShuffleClient

REPO_ROOT = Path(__file__).parent.parent.parent.parent
WEBHOOK_INFO = Path("/app/webhook_info.json") if Path(
    "/app/webhook_info.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info.json"
WEBHOOK_INFO_WAZUH = Path("/app/webhook_info_wazuh.json") if Path(
    "/app/webhook_info_wazuh.json").exists() else REPO_ROOT / "src" / "soar_lab" / "infrastructure" / "artifacts" / "webhook_info_wazuh.json"
ENV_FULL = Path("/app/.env.full") if Path("/app/.env.full").exists() else REPO_ROOT / ".env.full"


def _load_env() -> dict:
    if not ENV_FULL.exists():
        return {}
    result = {}
    for line in ENV_FULL.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    return result


def generate_malicious_alert(workflow_type: str) -> dict:
    """Generate a malicious alert payload."""
    timestamp = datetime.now(timezone.utc).isoformat()
    if workflow_type == "wazuh":
        return {
            "alert_id": f"WAZ-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-WAZ-001",
            "src_ip": "192.168.1.101",
            "severity": 2,
            "process_name": "malware.exe",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "mitre_techniques": ["T1486"],
            "detection_time": timestamp,
            "wazuh_agent_id": "001",
            "wazuh_agent_name": "simulated-agent",
            "wazuh_agent_ip": "192.168.1.101",
            "source": "wazuh-siem"
        }
    else:
        return {
            "alert_id": f"SIM-{int(time.time())}",
            "alert_type": "ransomware",
            "hostname": "WIN-SIM-001",
            "src_ip": "192.168.1.100",
            "severity": 2,
            "process_name": "malware.exe",
            "hash": "93e670becf64454b97b2efb7537fc1b7e09866f0dec001d8321467f74abc8dba",
            "mitre_techniques": ["T1486"],
            "detection_time": timestamp,
            "source": "simulated-siem"
        }


def generate_benign_alert(workflow_type: str) -> dict:
    """Generate a benign alert payload."""
    timestamp = datetime.now(timezone.utc).isoformat()
    if workflow_type == "wazuh":
        return {
            "alert_id": f"WAZ-BEN-{int(time.time())}",
            "alert_type": "file_access",
            "hostname": "WIN-WAZ-002",
            "src_ip": "192.168.1.102",
            "severity": 1,
            "process_name": "notepad.exe",
            "hash": "d41d8cd98f00b204e9800998ecf8427e",
            "mitre_techniques": [],
            "detection_time": timestamp,
            "wazuh_agent_id": "002",
            "wazuh_agent_name": "benign-agent",
            "wazuh_agent_ip": "192.168.1.102",
            "source": "wazuh-siem"
        }
    else:
        return {
            "alert_id": f"SIM-BEN-{int(time.time())}",
            "alert_type": "file_access",
            "hostname": "WIN-SIM-002",
            "src_ip": "192.168.1.102",
            "severity": 1,
            "process_name": "notepad.exe",
            "hash": "d41d8cd98f00b204e9800998ecf8427e",
            "mitre_techniques": [],
            "detection_time": timestamp,
            "source": "simulated-siem"
        }


def send_alert_to_workflow(webhook_id: str, payload: dict, shuffle_client: ShuffleClient) -> str:
    """Send alert to workflow using ShuffleClient."""
    result = shuffle_client.send_webhook(webhook_id, payload)
    if not result.get("success"):
        raise Exception(f"Shuffle did not accept alert: {result}")
    return result.get("execution_id", "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send alerts to both workflows")
    parser.add_argument(
        "--type",
        choices=["malicious", "benign"],
        default="malicious",
        help="Alert type (malicious or benign)",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Send a single alert to each workflow",
    )
    parser.add_argument(
        "--num-alerts",
        type=int,
        default=1,
        help="Number of alerts to send to each workflow (default: 1)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=3,
        help="Delay between alerts in seconds (default: 3)",
    )
    parser.add_argument(
        "--shuffle-url",
        default=os.environ.get("SHUFFLE_URL", "http://soar_shuffle_frontend:80"),
        help="Shuffle URL (default: SHUFFLE_URL env var or soar_shuffle_frontend:80)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("SHUFFLE_API_KEY", ""),
        help="Shuffle API key (default: SHUFFLE_API_KEY env var)",
    )
    args = parser.parse_args()

    # Load workflow configs
    simulated_info = json.loads(WEBHOOK_INFO.read_text()) if WEBHOOK_INFO.exists() else {}
    wazuh_info = json.loads(WEBHOOK_INFO_WAZUH.read_text()) if WEBHOOK_INFO_WAZUH.exists() else {}

    simulated_webhook_url = simulated_info.get("webhook_url", "")
    wazuh_webhook_url = wazuh_info.get("webhook_url", "")

    if not simulated_webhook_url:
        print("ERROR: Simulated webhook URL not found in webhook_info.json")
        sys.exit(1)
    if not wazuh_webhook_url:
        print("ERROR: Wazuh webhook URL not found in webhook_info_wazuh.json")
        sys.exit(1)

    # Extract webhook IDs from URLs
    simulated_webhook_id = simulated_webhook_url.split("webhook_")[-1] if "webhook_" in simulated_webhook_url else ""
    wazuh_webhook_id = wazuh_webhook_url.split("webhook_")[-1] if "webhook_" in wazuh_webhook_url else ""

    if not simulated_webhook_id:
        print("ERROR: Could not extract webhook ID from simulated webhook URL")
        sys.exit(1)
    if not wazuh_webhook_id:
        print("ERROR: Could not extract webhook ID from Wazuh webhook URL")
        sys.exit(1)

    # Initialize ShuffleClient
    shuffle_url = args.shuffle_url
    api_key = args.api_key
    if not api_key:
        print("WARNING: No API key provided, using placeholder")
        api_key = "placeholder"

    shuffle_client = ShuffleClient(base_url=shuffle_url, api_key=api_key, verify_ssl=False)

    print(f"Simulated Webhook ID: {simulated_webhook_id}")
    print(f"Wazuh Webhook ID: {wazuh_webhook_id}")
    print(f"Shuffle URL: {shuffle_url}")

    num_alerts = 1 if args.single else args.num_alerts
    alert_type = args.type

    print(f"\nSending {num_alerts} {alert_type} alert(s) to EACH workflow...\n")

    for i in range(num_alerts):
        print(f"=== Alert {i + 1}/{num_alerts} ===")

        # Generate alerts
        if alert_type == "malicious":
            sim_payload = generate_malicious_alert("simulated")
            wazuh_payload = generate_malicious_alert("wazuh")
        else:
            sim_payload = generate_benign_alert("simulated")
            wazuh_payload = generate_benign_alert("wazuh")

        # Send to simulated workflow
        try:
            sim_exec_id = send_alert_to_workflow(simulated_webhook_id, sim_payload, shuffle_client)
            print(f"[SIMULATED] Alert sent successfully: {sim_payload.get('alert_id')} (exec_id={sim_exec_id})")
        except Exception as e:
            print(f"[SIMULATED] Failed to send alert: {e}")

        # Send to Wazuh workflow
        try:
            wazuh_exec_id = send_alert_to_workflow(wazuh_webhook_id, wazuh_payload, shuffle_client)
            print(f"[WAZUH] Alert sent successfully: {wazuh_payload.get('alert_id')} (exec_id={wazuh_exec_id})")
        except Exception as e:
            print(f"[WAZUH] Failed to send alert: {e}")

        if i < num_alerts - 1 and args.delay > 0:
            time.sleep(args.delay)

    print(f"\nSummary: {num_alerts} alerts sent to each workflow")


if __name__ == "__main__":
    main()
