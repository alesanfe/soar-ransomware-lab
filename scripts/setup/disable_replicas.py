#!/usr/bin/env python3
"""Disable replicas on all OpenSearch indices (single-node optimization).

Retries up to 5 times with 10s delay to handle indices that are still
being created by the Shuffle backend.
"""
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from soar_lab.security.tls_config import ca_verify  # noqa: E402


def main():
    os_url = os.environ.get("OPENSEARCH_URL", "https://localhost:19201")
    auth = (
        os.environ.get("OPENSEARCH_USERNAME", "admin"),
        os.environ.get("OPENSEARCH_PASSWORD", ""),
    )
    max_retries = 5

    for attempt in range(1, max_retries + 1):
        try:
            # Get all indices
            r = requests.get(
                os_url + "/_cat/indices?h=index", auth=auth, verify=ca_verify(), timeout=15
            )
            r.raise_for_status()
            indices = r.text.split()

            if not indices:
                print("No indices found yet, retrying...")
                time.sleep(10)
                continue

            # Disable replicas on all indices
            r = requests.put(
                os_url + "/_all/_settings",
                json={"index.number_of_replicas": 0},
                auth=auth,
                verify=ca_verify(),
                timeout=30,
            )
            r.raise_for_status()
            print("Replicas disabled for " + str(len(indices)) + " indices: " + r.text[:80])
            return 0
        except Exception as exc:
            print("Attempt " + str(attempt) + "/" + str(max_retries) + ": " + str(exc))
            if attempt < max_retries:
                time.sleep(10)

    print(
        "ERROR: Could not disable replicas after " + str(max_retries) + " attempts", file=sys.stderr
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
