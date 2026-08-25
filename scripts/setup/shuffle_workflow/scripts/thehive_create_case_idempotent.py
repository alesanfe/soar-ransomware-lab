# Embedded script: thehive_create_case_idempotent
# Searches for an existing TheHive case with tag alert_id:<alert_id>.
# If found, returns the existing case (idempotency — prevents duplicates
# when Orborus re-executes stale workflows).
# If not found, creates a new case via POST /api/case.
import json
import logging

import requests

logger = logging.getLogger(__name__)

# TheHive configuration
_th_url = "__THEHIVE_INT__"
_th_key = "__THEHIVE_KEY__"

_case_json = r"""$build_case_json.message"""
try:
    case_data = json.loads(_case_json)
except Exception:
    case_data = {}

_alert_id = ""
try:
    _norm = json.loads(r"""$normalize_inputs.message""")
    _alert_id = _norm.get("alert_id", "")
except Exception:
    pass
if not _alert_id:
    _alert_id = """$exec.alert_id"""
if _alert_id.startswith("$"):
    _alert_id = ""

_headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {_th_key}",
}

# Step 1: Search for existing case with tag alert_id:<alert_id>
_existing_case = None
if _alert_id:
    try:
        _search = {
            "query": {
                "_and": [
                    {"_wildcard": {"tags": f"*alert_id:{_alert_id}*"}},
                ]
            },
            "range": "0-1",
        }
        _r = requests.post(
            f"{_th_url}/api/case/_search",
            headers=_headers,
            json=_search,
            timeout=30,
        )
        if _r.status_code == 200:
            _results = _r.json()
            if isinstance(_results, list) and len(_results) > 0:
                _existing_case = _results[0]
    except Exception as e:
        logger.warning(f"Search for existing case failed: {e}")

# Step 2: Return existing case or create new one
if _existing_case:
    # Return existing case — idempotent
    print(json.dumps({
        "status": 200,
        "body": _existing_case,
        "reused": True,
    }))
else:
    # Create new case
    try:
        _r = requests.post(
            f"{_th_url}/api/case",
            headers=_headers,
            json=case_data,
            timeout=120,
        )
        print(json.dumps({
            "status": _r.status_code,
            "body": _r.json() if _r.status_code < 400 else {},
            "reused": False,
        }))
    except Exception as e:
        print(json.dumps({
            "status": 500,
            "body": {"error": str(e)},
            "reused": False,
        }))
