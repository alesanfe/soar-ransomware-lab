import json
import os

import requests

s = requests.Session()
s.verify = "/app/certs/ca.crt"
s.auth = ("admin", os.environ["OPENSEARCH_PASSWORD"])
r = s.post(
    "https://opensearch:9200/workflow-000001/_search",
    json={"size": 5, "query": {"match_all": {}}},
).json()
for h in r["hits"]["hits"]:
    wf = h["_source"]
    if not wf.get("is_valid", True) and wf.get("name") != "SOAR-Ransomware-Response":
        continue
    print("workflow:", wf.get("name"), "| actions:", len(wf.get("actions", [])))
    found = {"cache": None, "verify_false": 0, "verify_true": 0, "plaintext": 0}
    for a in wf.get("actions", []):
        params = {p["name"]: str(p.get("value", "")) for p in a.get("parameters", [])}
        if "verify" in params:
            if params["verify"] == "true":
                found["verify_true"] += 1
            else:
                found["verify_false"] += 1
        if "cache/ioc" in params.get("url", ""):
            found["cache"] = "TOKEN" if "X-Service-Token:" in params.get("headers", "") else "NO-TOKEN"
        if "http://thehive" in str(params) or "http://cortex" in str(params):
            found["plaintext"] += 1
    print("cache node:", found["cache"], "| verify true/false:", found["verify_true"], "/", found["verify_false"], "| plaintext refs:", found["plaintext"])
