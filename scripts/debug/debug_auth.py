import json
import logging
import os

import requests
import urllib3

urllib3.disable_warnings()

logger = logging.getLogger(__name__)
try:
    with open("/app/runtime/results/webhook_info.json") as f:
        info = json.load(f)
    logger.info(f"webhook_info: {json.dumps(info, indent=2)}")
    api_key = info.get("shuffle_api_key")
    logger.info("API Key: <redacted>")
    shuffle_url = os.environ.get("SHUFFLE_BACKEND_URL", "http://shuffle-backend:5001")
    url = f"{shuffle_url}/api/v1/workflows/{info.get('workflow_id')}"
    logger.info(f"URL: {url}")
    r = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, verify=False)
    logger.info(f"Status: {r.status_code}")
    logger.info(f"Response: {r.text[:500]}")
except Exception as e:
    logger.error(f"{e}")
