import json
import os

import requests

s = requests.Session()
s.verify = "/app/certs/ca.crt"
s.auth = ("admin", os.environ["OPENSEARCH_PASSWORD"])
r = s.post(
    "https://opensearch:9200/workflowexecution/_search",
    json={
        "size": 1,
        "sort": [{"started_at": {"order": "desc"}}],
        "query": {"match_all": {}},
    },
).json()
h = r["hits"]["hits"][0]["_source"]
print("status:", h.get("status"), "| started:", h.get("started_at"))
for res in h.get("results", []):
    a = res.get("action", {})
    print("-", a.get("name"), "|", res.get("status"), "|", str(res.get("result"))[:300])
