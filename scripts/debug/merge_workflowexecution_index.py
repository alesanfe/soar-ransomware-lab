"""One-off: merge concrete `workflowexecution` index into `workflowexecution-000001`
so the ISM rollover alias can be created. Idempotent (op_type=create skips dupes)."""
import json
import os

import requests

OSU = "https://opensearch:9200"
AUTH = (os.environ.get("OPENSEARCH_USERNAME", "admin"), os.environ["OPENSEARCH_PASSWORD"])
CA = "/app/certs/ca.crt"

s = requests.Session()
s.verify = CA
s.auth = AUTH

r = s.post(
    f"{OSU}/workflowexecution/_search?scroll=2m",
    json={"size": 20, "query": {"match_all": {}}, "sort": ["_doc"]},
).json()
hits = r["hits"]["hits"]
sid = r["_scroll_id"]
total = r["hits"]["total"]["value"]
created = skipped = errs = batches = 0
while hits:
    lines = []
    for h in hits:
        lines.append(json.dumps({"create": {"_index": "workflowexecution-000001", "_id": h["_id"]}}))
        lines.append(json.dumps(h["_source"]))
    br = s.post(
        f"{OSU}/_bulk",
        data="\n".join(lines) + "\n",
        headers={"Content-Type": "application/x-ndjson"},
    ).json()
    for it in br["items"]:
        st = it["create"]["status"]
        if st in (200, 201):
            created += 1
        elif st == 409:
            skipped += 1
        else:
            errs += 1
            print("ERR", json.dumps(it)[:150])
    batches += 1
    r = s.post(f"{OSU}/_search/scroll", json={"scroll": "2m", "scroll_id": sid}).json()
    hits = r["hits"]["hits"]
    sid = r["_scroll_id"]

print(f"total_src={total} created={created} dupes_skipped={skipped} errs={errs} batches={batches}")
