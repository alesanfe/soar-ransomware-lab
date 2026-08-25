import json
import logging
import os

import requests
import urllib3

urllib3.disable_warnings()

logger = logging.getLogger(__name__)
with open("/app/runtime/results/webhook_info.json") as f:
    info = json.load(f)
api_key = info.get("shuffle_api_key")
shuffle_url = os.environ.get("SHUFFLE_BACKEND_URL", "http://shuffle-backend:5001")
url = f"{shuffle_url}/api/v1/workflows/{info.get('workflow_id')}"
r = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, verify=False)
if r.status_code == 200:
    data = r.json()
    actions = data.get("actions", [])
    logger.info(f"Total actions: {len(actions)}")
    for a in actions:
        label = a.get("label", "")
        logger.info(f"Label: {label}")
