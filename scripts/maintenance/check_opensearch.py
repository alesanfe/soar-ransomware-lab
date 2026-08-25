import json
import logging
import os
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

BASE = os.environ.get("OPENSEARCH_URL", "http://localhost:19201")
OPENSEARCH_USERNAME = os.environ.get("OPENSEARCH_USERNAME", "admin")
OPENSEARCH_PASSWORD = os.environ.get("OPENSEARCH_PASSWORD")

if not OPENSEARCH_PASSWORD:
    raise RuntimeError(
        "OPENSEARCH_PASSWORD no está definida. "
        "Carga las variables de .env.full o define OPENSEARCH_PASSWORD en el entorno."
    )

AUTH = (OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD)


def get(path):
    r = requests.get(urljoin(BASE, path), auth=AUTH)
    return r.status_code, r.json()


def get_cat(path):
    r = requests.get(urljoin(BASE, path), auth=AUTH)
    return r.text


# 1. list indices matching workflow
cat = get_cat("/_cat/indices/workflow*")
print("=== workflow indices ===")
print(cat)

# 2. mapping for workflow-000001
status, mapping = get("/workflow-000001/_mapping")
print("\n=== workflow-000001 mapping status ===", status)
print(json.dumps(mapping, indent=2))

# 3. template status
status, tmpl = get("/_index_template/shuffle-workflow")
print("\n=== template status ===", status)
print(json.dumps(tmpl, indent=2))

# 4. health endpoint
shuffle_api_url = os.environ.get("SHUFFLE_API_URL", "http://localhost:15001")
r = requests.get(f"{shuffle_api_url}/api/v1/health")
print("\n=== shuffle health ===", r.status_code)
print(json.dumps(r.json(), indent=2))
