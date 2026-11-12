#!/usr/bin/env python3
"""Wait for all workflow executions to reach a terminal state (FINISHED/ABORTED).

Usage: python wait_for_workflows.py [--expected N] [--timeout 600] [--poll 10]
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import requests

from soar_lab.common.constants import DEFAULT_ELASTICSEARCH_URL, DEFAULT_OPENSEARCH_URL
from soar_lab.security.tls_config import ca_verify

OS_URL = os.environ.get("SHUFFLE_OPENSEARCH_URL", DEFAULT_OPENSEARCH_URL)
ES_URL = os.environ.get("ES_URL", DEFAULT_ELASTICSEARCH_URL)
OS_AUTH = (
    os.environ.get("SHUFFLE_OPENSEARCH_USERNAME", os.environ.get("OPENSEARCH_USERNAME", "admin")),
    os.environ.get("SHUFFLE_OPENSEARCH_PASSWORD", os.environ.get("OPENSEARCH_PASSWORD", "")),
)
ES_AUTH = (
    os.environ.get("ELASTIC_USERNAME", "elastic"),
    os.environ.get("ELASTIC_PASSWORD", ""),
)
_VERIFY = ca_verify()


def count_finished() -> tuple[int, int]:
    """Return (finished_count, total_count) from OpenSearch workflowexecution index."""
    try:
        r = requests.post(
            f"{OS_URL}/workflowexecution/_count",
            json={"query": {"terms": {"status": ["FINISHED", "ABORTED", "FAILED"]}}},
            auth=OS_AUTH,
            verify=_VERIFY,
            timeout=15,
        )
        if r.status_code != 200:
            return (0, 0)
        finished = r.json().get("count", 0)
    except Exception:
        finished = 0

    try:
        r2 = requests.get(
            f"{OS_URL}/workflowexecution/_count",
            auth=OS_AUTH,
            verify=_VERIFY,
            timeout=15,
        )
        if r2.status_code != 200:
            return (finished, 0)
        total = r2.json().get("count", 0)
    except Exception:
        total = 0

    return (finished, total)


def count_metrics() -> int:
    """Return number of documents in soar-metrics (ES)."""
    try:
        r = requests.get(f"{ES_URL}/soar-metrics/_count", auth=ES_AUTH, verify=_VERIFY, timeout=15)
        if r.status_code == 200:
            return r.json().get("count", 0)
    except Exception:
        pass
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Wait for workflows to finish")
    parser.add_argument("--expected", type=int, default=0, help="Expected number of workflows")
    parser.add_argument("--timeout", type=int, default=600, help="Max wait in seconds")
    parser.add_argument("--poll", type=int, default=10, help="Poll interval in seconds")
    args = parser.parse_args()

    expected = args.expected
    deadline = time.time() + args.timeout
    last_metrics = 0

    while time.time() < deadline:
        finished, total = count_finished()
        metrics = count_metrics()

        if expected > 0:
            print(f"  Workflows: {finished}/{expected} finished (total in OS: {total}), metrics: {metrics}")
            if finished >= expected and metrics >= expected:
                print(f"  All {expected} workflows finished with metrics.")
                return 0
        else:
            print(f"  Workflows: {finished} finished (total: {total}), metrics: {metrics}")
            if total > 0 and finished >= total and metrics == last_metrics and metrics > 0:
                print(f"  All {finished} workflows finished. Metrics stable at {metrics}.")
                return 0
            last_metrics = metrics

        time.sleep(args.poll)

    print(f"  TIMEOUT: only {finished}/{expected or total} workflows finished.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
