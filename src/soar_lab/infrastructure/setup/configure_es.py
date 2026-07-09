#!/usr/bin/env python3
"""
Configure Elasticsearch index templates for single-node deployment.
Sets number_of_replicas=0 for all SOAR-related indices.
"""

import requests
import sys
import time

def main():
    es_url = "http://elasticsearch:9200"
    
    # Wait for Elasticsearch to be ready
    print("Waiting for Elasticsearch to be ready...")
    for i in range(24):
        try:
            r = requests.get(f"{es_url}/_cluster/health", timeout=4)
            if r.status_code == 200:
                print(f"Elasticsearch ready after {i * 5}s")
                break
        except Exception:
            pass
        time.sleep(5)
    else:
        print("ERROR: Elasticsearch not ready after 120s")
        sys.exit(1)
    
    # Create index template for replicas=0
    print("Creating index template for replicas=0...")
    tpl = {
        "index_patterns": ["shuffle*", "the_hive*", "cortex*", "soar*"],
        "settings": {"number_of_replicas": 0}
    }
    r = requests.put(f"{es_url}/_template/soar_no_replicas", json=tpl)
    print(f"[ES template] {r.status_code} {r.text[:80]}")
    
    # Update existing indices
    print("Updating existing indices to replicas=0...")
    indices = requests.get(f"{es_url}/_cat/indices?h=index").text.split()
    for idx in indices:
        if idx:
            try:
                requests.put(f"{es_url}/{idx}/_settings", json={"index": {"number_of_replicas": 0}})
                print(f"  Updated {idx}")
            except Exception as e:
                print(f"  Failed to update {idx}: {e}")
    
    print("Elasticsearch configuration complete")

if __name__ == "__main__":
    main()
