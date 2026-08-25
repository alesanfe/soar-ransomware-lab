#!/usr/bin/env python3
"""Disable replicas on all OpenSearch indices (single-node optimization).

Retries up to 5 times with 10s delay to handle indices that are still
being created by the Shuffle backend.
"""
import urllib.request
import json
import sys
import time

def main():
    os_url = "http://localhost:9200"
    max_retries = 5
    
    for attempt in range(1, max_retries + 1):
        try:
            # Get all indices
            r = urllib.request.urlopen(os_url + "/_cat/indices?h=index", timeout=15)
            indices = r.read().decode().split()
            
            if not indices:
                print("No indices found yet, retrying...")
                time.sleep(10)
                continue
            
            # Disable replicas on all indices
            data = json.dumps({"index.number_of_replicas": 0}).encode()
            req = urllib.request.Request(
                os_url + "/_all/_settings", data=data, method="PUT",
                headers={"Content-Type": "application/json"},
            )
            r = urllib.request.urlopen(req, timeout=30)
            print("Replicas disabled for " + str(len(indices)) + " indices: " + r.read().decode()[:80])
            return 0
        except Exception as exc:
            print("Attempt " + str(attempt) + "/" + str(max_retries) + ": " + str(exc))
            if attempt < max_retries:
                time.sleep(10)
    
    print("ERROR: Could not disable replicas after " + str(max_retries) + " attempts", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
