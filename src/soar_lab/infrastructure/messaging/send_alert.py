# !/usr/bin/env python3
"""SOAR Ransomware Lab - Alert Sender CLI.

Generates and sends alert payloads to the SOAR webhook.

Usage:
python src/soar_lab/infrastructure/messaging/send_alert.py
python src/soar_lab/infrastructure/messaging/send_alert.py --type malicious --single
python src/soar_lab/infrastructure/messaging/send_alert.py --type benign \
--num-alerts 10 --delay 5
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from soar_lab.common.constants import (
    SHUFFLE_WEBHOOK_DEFAULT,
    WEBHOOK_INFO_PATHS,
)


def _default_webhook_url(base_dir: Path) -> str:
    """Return the host webhook URL from webhook_info.json if available."""
    env_url = os.environ.get("SHUFFLE_WEBHOOK_URL")
    if env_url:
        return env_url
    info_paths = [
        base_dir / "runtime" / "results" / "webhook_info.json",
        base_dir / "artifacts" / "results" / "webhook_info.json",  # legacy fallback
    ] + [Path(p) for p in WEBHOOK_INFO_PATHS]
    for p in info_paths:
        if p.exists():
            try:
                info = json.loads(p.read_text())
                return info.get("webhook_url_host", "") or info.get("webhook_url", "")
            except Exception:
                pass
    return SHUFFLE_WEBHOOK_DEFAULT


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
        default=None,
        help="Webhook URL (default: SHUFFLE_WEBHOOK_URL env var or webhook_info.json)",
    )
    parser.add_argument(
        "--api-token",
        default=os.environ.get("SIEM_WEBHOOK_TOKEN", os.environ.get("SHUFFLE_API_TOKEN", "")),
        help="API token (default: SIEM_WEBHOOK_TOKEN env var, then SHUFFLE_API_TOKEN)",
    )

    # Resolve BASE_DIR before parsing defaults that depend on it
    base_dir = Path(os.environ.get("BASE_DIR", Path(__file__).parent.parent.parent.parent.parent))

    if "--webhook-url" not in sys.argv:
        default_url = _default_webhook_url(base_dir)
    else:
        default_url = None
    parser.set_defaults(webhook_url=default_url)

    args = parser.parse_args()
    if args.webhook_url is None:
        args.webhook_url = _default_webhook_url(base_dir)

    # ------------------------------------------------------------------ #
    # Bootstrap dependencies                                              #
    # ------------------------------------------------------------------ #
    sys.path.insert(0, str(base_dir / "src"))
    os.environ.setdefault("BASE_DIR", str(base_dir))
    os.environ.setdefault("SOAR_SKIP_EAGER_INIT", "1")

    from soar_lab.config.logging import get_logger
    from soar_lab.domain.alert_generator import AlertGenerator
    from soar_lab.infrastructure.http_alert_sender import HTTPAlertSender

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
            alert = alert_generator.generate_malicious()
        else:
            alert = alert_generator.generate_benign()

        result = sender.send(alert)

        if result.get("success"):
            print(f"[{i + 1}/{num_alerts}] Alert sent successfully: {alert.get('alert_id')}")
        else:
            print(
                f"[{i + 1}/{num_alerts}] Failed to send alert: "
                f"{result.get('error', 'Unknown error')}"
            )
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
