#!/usr/bin/env python3
"""Warmup Shuffle backend before sending a batch of alerts.

Sends a single test alert, waits for the workflow to finish, then
deletes the test execution from OpenSearch and the test case from
TheHive.  This ensures the backend is fully ready to accept a
burst of alerts without HTTP 500 errors.

Usage:
    python warmup_shuffle.py [--timeout 300] [--poll 5]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests


def _get_api_key() -> str:
    env_path = Path("/app/.env.full")
    if not env_path.exists():
        env_path = Path(".env.full")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("SHUFFLE_DEFAULT_APIKEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("SHUFFLE_DEFAULT_APIKEY not found in .env.full")


def _get_webhook_token() -> str:
    info_path = Path("/app/reports/validation/results/webhook_info.json")
    if not info_path.exists():
        raise RuntimeError("webhook_info.json not found")
    data = json.loads(info_path.read_text(encoding="utf-8"))
    url = data.get("webhook_url_internal", data.get("webhook_url", ""))
    token = url.rsplit("/", 1)[-1]
    if not token.startswith("webhook_"):
        raise RuntimeError(f"Invalid webhook token: {token}")
    return token


def _wait_for_opensearch(timeout: int = 60) -> bool:
    """Wait for OpenSearch to respond to write operations."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(
                "http://opensearch:9200/_cluster/health?wait_for_status=yellow&timeout=5s",
                timeout=10,
            )
            if r.status_code == 200:
                health = r.json()
                if health.get("status") in ("green", "yellow"):
                    return True
        except Exception:
            pass
        time.sleep(5)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Warmup Shuffle backend")
    parser.add_argument("--timeout", type=int, default=300, help="Max wait seconds")
    parser.add_argument("--poll", type=int, default=5, help="Poll interval seconds")
    parser.add_argument("--max-retries", type=int, default=20, help="Max webhook retries")
    args = parser.parse_args()

    api_key = _get_api_key()
    webhook_token = _get_webhook_token()
    headers = {"Authorization": f"Bearer {api_key}"}

    # Step 1: Wait for OpenSearch to be healthy
    print("[warmup] Waiting for OpenSearch to be healthy...", flush=True)
    if not _wait_for_opensearch(timeout=60):
        print("[warmup] ERROR: OpenSearch not healthy after 60s", flush=True)
        return 1
    print("[warmup] OpenSearch is healthy", flush=True)

    # Step 2: Send a test alert and retry until it succeeds
    test_alert = {
        "alert_id": "WARMUP-TEST",
        "alert_type": "ransomware",
        "event_type": "ransomware_detection",
        "severity": 3,
        "hostname": "warmup-host",
        "src_ip": "127.0.0.1",
        "hash": "warmup-hash",
        "source": "warmup",
        "detection_time": "2026-08-23T10:00:00Z",
        "mitre_techniques": ["T1486"],
        "mitre_tactics": ["Impact"],
    }

    webhook_url = f"http://shuffle-backend:5001/api/v1/hooks/{webhook_token}"
    execution_id = None

    print(f"[warmup] Sending test alert to {webhook_url}...", flush=True)
    for attempt in range(1, args.max_retries + 1):
        try:
            r = requests.post(webhook_url, json=test_alert, timeout=30)
            if r.status_code == 200:
                body = r.json()
                execution_id = body.get("execution_id")
                print(f"[warmup] Test alert accepted (execution_id={execution_id})", flush=True)
                break
            else:
                print(f"[warmup] Attempt {attempt}/{args.max_retries}: HTTP {r.status_code}, retrying in 15s...", flush=True)
        except requests.exceptions.Timeout:
            print(f"[warmup] Attempt {attempt}/{args.max_retries}: timeout, retrying in 15s...", flush=True)
        except Exception as exc:
            print(f"[warmup] Attempt {attempt}/{args.max_retries}: {exc}, retrying in 15s...", flush=True)
        time.sleep(15)
    else:
        print(f"[warmup] ERROR: Webhook not ready after {args.max_retries} attempts", flush=True)
        return 1

    if not execution_id:
        print("[warmup] ERROR: No execution_id returned", flush=True)
        return 1

    # Step 3: Wait for the test workflow to finish (this gives OpenSearch
    # time to warm up and create all necessary indices).  We don't abort
    # because aborting doesn't stop the underlying containers — the
    # workflow continues consuming OpenSearch resources in the background.
    print(f"[warmup] Waiting for test workflow {execution_id} to finish (max {args.timeout}s)...", flush=True)
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        try:
            r = requests.get(
                f"http://shuffle-backend:5001/api/v1/executions/{execution_id}",
                headers=headers,
                timeout=15,
            )
            if r.status_code == 200:
                body = r.json()
                if isinstance(body, dict):
                    body = body.get("data", body)
                status = body.get("status", "")
                if status in ("FINISHED", "ABORTED", "FAILURE"):
                    print(f"[warmup] Test workflow finished with status: {status}", flush=True)
                    break
            time.sleep(args.poll)
        except Exception:
            time.sleep(args.poll)
    else:
        print(f"[warmup] WARNING: Test workflow did not finish within {args.timeout}s, proceeding anyway", flush=True)
        # Abort the workflow since it's taking too long
        try:
            requests.delete(
                f"http://shuffle-backend:5001/api/v1/executions/{execution_id}",
                headers=headers,
                timeout=15,
            )
        except Exception:
            pass
        time.sleep(10)

    # Step 4: Clean up the test execution from OpenSearch
    print("[warmup] Cleaning up test execution from OpenSearch...", flush=True)
    try:
        requests.delete(
            f"http://shuffle-backend:5001/api/v1/executions/{execution_id}",
            headers=headers,
            timeout=15,
        )
    except Exception:
        pass
    try:
        requests.post(
            "http://opensearch:9200/workflowexecution-000001/_delete_by_query",
            json={"query": {"term": {"execution_id": execution_id}}},
            timeout=30,
        )
    except Exception:
        pass

    # Step 5: Clean up the test TheHive case (retry up to 3 times)
    print("[warmup] Cleaning up test TheHive case...", flush=True)
    try:
        thehive_key = ""
        for line in Path("/app/.env.full").read_text(encoding="utf-8").splitlines():
            if line.startswith("THEHIVE_API_KEY="):
                thehive_key = line.split("=", 1)[1].strip()
                break
        if thehive_key:
            for retry in range(3):
                r = requests.get(
                    "http://thehive:9000/api/case",
                    headers={"Authorization": f"Bearer {thehive_key}"},
                    params={"range": "all"},
                    timeout=15,
                )
                if r.status_code != 200:
                    time.sleep(5)
                    continue
                cases = r.json()
                found = False
                for case in cases:
                    title = case.get("title", "")
                    if "WARMUP-TEST" in title:
                        case_id = case.get("_id") or case.get("id")
                        try:
                            requests.delete(
                                f"http://thehive:9000/api/case/{case_id}",
                                headers={"Authorization": f"Bearer {thehive_key}"},
                                timeout=15,
                            )
                            print(f"[warmup] Deleted test TheHive case: {case_id}", flush=True)
                            found = True
                        except Exception as exc:
                            print(f"[warmup] WARNING: Delete failed for {case_id}: {exc}", flush=True)
                if not found:
                    break
                time.sleep(5)  # Wait and retry to verify deletion
    except Exception as exc:
        print(f"[warmup] WARNING: Could not clean TheHive case: {exc}", flush=True)

    # Step 6: Clean up test metrics and alerts from Elasticsearch
    print("[warmup] Cleaning up test alert/metrics from Elasticsearch...", flush=True)
    for idx in ["soar-alerts", "soar-metrics"]:
        for es_host in ["http://elasticsearch:9200", "http://opensearch:9200"]:
            try:
                requests.post(
                    f"{es_host}/{idx}/_delete_by_query",
                    json={"query": {"term": {"alert_id": "WARMUP-TEST"}}},
                    timeout=15,
                )
            except Exception:
                pass

    # Also clean up any Cortex jobs for the warmup alert
    try:
        requests.post(
            "http://elasticsearch:9200/cortex_6/_delete_by_query",
            json={"query": {"term": {"alert_id": "WARMUP-TEST"}}},
            timeout=15,
        )
    except Exception:
        pass

    print("[warmup] Backend is ready for batch simulation!", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
