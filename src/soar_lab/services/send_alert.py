#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Alert Sender CLI
Generates and sends alert payloads to the SOAR webhook.

Usage:
    python3 -m soar_lab.services.send_alert
    python3 -m soar_lab.services.send_alert --type malicious --single
    python3 -m soar_lab.services.send_alert --type benign --num-alerts 10 --delay 5
"""

import argparse
import os
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Send SOAR alert payloads to webhook")
    parser.add_argument(
        "--type",
        choices=["malicious", "benign"],
        default="malicious",
        help="Alert type (malicious or benign)",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Send a single alert",
    )
    parser.add_argument(
        "--num-alerts",
        type=int,
        default=1,
        help="Number of alerts to send (default: 1)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=3,
        help="Delay between alerts in seconds (default: 3)",
    )
    parser.add_argument(
        "--webhook-url",
        default=os.environ.get("SHUFFLE_WEBHOOK_URL", "http://localhost:5001/api/v1/hooks/webhook"),
        help="Webhook URL (default: SHUFFLE_WEBHOOK_URL env var or localhost:5001)",
    )
    parser.add_argument(
        "--api-token",
        default=os.environ.get("SHUFFLE_API_TOKEN", "SiemToken123!@#"),
        help="API token (default: SHUFFLE_API_TOKEN env var or SiemToken123!@#)",
    )
    args = parser.parse_args()

    # Resolve BASE_DIR
    base_dir = Path(os.environ.get("BASE_DIR", Path(__file__).parent.parent.parent.parent))

    # ------------------------------------------------------------------ #
    # Bootstrap dependencies                                              #
    # ------------------------------------------------------------------ #
    sys.path.insert(0, str(base_dir / "src"))
    os.environ.setdefault("BASE_DIR", str(base_dir))
    os.environ.setdefault("SOAR_SKIP_EAGER_INIT", "1")

    from soar_lab.infrastructure.http_alert_sender import HTTPAlertSender
    from soar_lab.domain.alert_generator import AlertGenerator
    from soar_lab.config.logging import get_logger

    logger = get_logger(__name__)

    # ------------------------------------------------------------------ #
    # Initialize components                                               #
    # ------------------------------------------------------------------ #
    alert_generator = AlertGenerator()
    sender = HTTPAlertSender(webhook_url=args.webhook_url, api_token=args.api_token)

    # ------------------------------------------------------------------ #
    # Send alerts                                                        #
    # ------------------------------------------------------------------ #
    num_alerts = 1 if args.single else args.num_alerts
    alert_type = args.type

    logger.info(f"Sending {num_alerts} {alert_type} alert(s) to {args.webhook_url}")

    for i in range(num_alerts):
        if alert_type == "malicious":
            alert = alert_generator.generate_malicious_alert()
        else:
            alert = alert_generator.generate_benign_alert()

        result = sender.send(alert)

        if result.get("success"):
            print(f"[{i+1}/{num_alerts}] Alert sent successfully: {alert.get('alert_id')}")
        else:
            print(f"[{i+1}/{num_alerts}] Failed to send alert: {result.get('error', 'Unknown error')}")
            sys.exit(1)

        if i < num_alerts - 1 and args.delay > 0:
            time.sleep(args.delay)

    # ------------------------------------------------------------------ #
    # Summary                                                            #
    # ------------------------------------------------------------------ #
    metrics = sender.get_metrics()
    print(f"\nSummary: {metrics['alerts_sent']} sent, {metrics['alerts_failed']} failed")


if __name__ == "__main__":
    main()
