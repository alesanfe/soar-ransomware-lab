#!/usr/bin/env python3
"""Replay an alert dataset through the SOAR pipeline (benchmark mode).

Reads a ``.jsonl``/``.ndjson``/``.json`` dataset and posts each alert to
the Shuffle webhook so repeated runs over the same dataset produce
comparable KPIs. Core logic lives in
``soar_lab.simulator.dataset_replay``.

Usage:
    python scripts/maintenance/replay_dataset.py dataset.jsonl \
        --webhook "$SHUFFLE_WEBHOOK_URL" --delay 0.5 --limit 100
    python scripts/maintenance/replay_dataset.py dataset.json --dry-run
"""

import argparse
import os
import sys

import requests as _req

from soar_lab.config.logging import get_logger
from soar_lab.simulator.dataset_replay import load_dataset, replay_dataset
from soar_lab.simulator.simulate_alerts import _get_default_webhook, send_alert

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dataset", help="Dataset file (.jsonl, .ndjson or .json)")
    parser.add_argument(
        "--webhook",
        default=os.environ.get("SHUFFLE_WEBHOOK_URL") or _get_default_webhook(),
        help="Webhook URL (default: SHUFFLE_WEBHOOK_URL or webhook_info.json)",
    )
    parser.add_argument("--delay", type=float, default=0.0, help="Seconds between alerts")
    parser.add_argument("--limit", type=int, default=None, help="Max alerts to replay")
    parser.add_argument(
        "--tag",
        default=None,
        help=(
            "Experiment variant label stamped on each alert "
            "(experiment_tag) — run the same dataset under two configs "
            "and compare with /analytics/experiment/compare (F1)."
        ),
    )
    parser.add_argument(
        "--via-api",
        action="store_true",
        help=(
            "Post through POST /api/v1/alerts instead of the Shuffle "
            "webhook — replays flow through the measured admission "
            "pipeline (queue, dedup, KPIs) rather than bypassing it (F3)."
        ),
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("SOAR_API_URL", "http://localhost:8000"),
        help="SOAR API base URL for --via-api (default: SOAR_API_URL)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset without sending")
    args = parser.parse_args()

    if not args.dry_run and not args.webhook and not args.via_api:
        logger.error("No webhook configured — set SHUFFLE_WEBHOOK_URL or run make init-webhook")
        return 1

    if args.via_api:
        api_url = args.api_url.rstrip("/")
        token = os.environ.get("INTERNAL_SERVICE_TOKEN", "")
        headers = {"X-Service-Token": token} if token else {}

        def _send(alert: dict) -> bool:
            try:
                resp = _req.post(
                    f"{api_url}/api/v1/alerts",
                    json=alert,
                    headers=headers,
                    timeout=10,
                )
                return resp.status_code in (200, 202)
            except Exception as exc:
                logger.warning("API replay post failed: %s", exc)
                return False

    else:

        def _send(alert: dict) -> bool:
            ok, _status = send_alert(alert, args.webhook)
            return ok

    try:
        alerts = load_dataset(args.dataset)
        summary = replay_dataset(
            alerts,
            send=(lambda _a: True) if args.dry_run else _send,
            delay=args.delay,
            limit=args.limit,
            tag=args.tag,
            on_result=lambda i, _a, ok: logger.info("[%s] %s", i, "OK" if ok else "FAIL"),
        )
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Dataset error: %s", exc)
        return 1

    logger.info(
        "Replay complete: %s/%s sent (%s%% success)",
        summary["sent"],
        summary["total"],
        summary["success_rate"],
    )
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
