#!/usr/bin/env python3
"""
reset_cortex.py - Resets Cortex index and recreates admin user/org.

Root cause of the elastic4play join field bug:
  elastic4play stores `relations` as a plain string for root entities
  (organization, user) and as an object {name, parent} for child entities
  (worker). ES 7.x cannot have a field that accepts both types. The fix is to
  pre-create an ES index template that declares `relations` as a proper join
  field with dummy children for each root type (accepted by ES 7.x for strings).
"""

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ES_URL = os.environ.get("ES_URL", "http://soar_elasticsearch:9200")
CORTEX_URL = os.environ.get("CORTEX_URL", "http://soar_cortex:9001")
ES_INDEX = "cortex_6"
SUPERADMIN_USER = "admin"
ADMIN_PASS = os.environ.get("CORTEX_ADMIN_PASSWORD", "")
CORTEX_ORG = os.environ.get("CORTEX_ORG", "cortex")
WORK_ORG = "soar-lab"
ORG_ADMIN_USER = os.environ.get("CORTEX_ADMIN_USER", "soaradmin")
INIT_AUTH = base64.b64encode(b"init:init").decode()
ADMIN_AUTH = base64.b64encode(f"{SUPERADMIN_USER}:{ADMIN_PASS}".encode()).decode() if ADMIN_PASS else ""
ORG_ADMIN_AUTH = base64.b64encode(f"{ORG_ADMIN_USER}:{ADMIN_PASS}".encode()).decode() if ADMIN_PASS else ""
ES_USER = os.environ.get("ELASTIC_USERNAME", "elastic")
ES_PASS = os.environ.get("ELASTIC_PASSWORD", "")
ES_AUTH = base64.b64encode(f"{ES_USER}:{ES_PASS}".encode()).decode() if ES_PASS else ""
ENV_FILE = ".env.full"

if not ADMIN_PASS:
    print("[ERROR] Falta CORTEX_ADMIN_PASSWORD", file=sys.stderr)
    sys.exit(1)

CORTEX_INDEX_TEMPLATE = {
    "index_patterns": ["cortex_*"],
    "settings": {
        "number_of_shards": 5,
        "number_of_replicas": 0
    },
    "mappings": {
        "dynamic_templates": [
            {
                "strings": {
                    "match_mapping_type": "string",
                    "mapping": {
                        "type": "text",
                        "fielddata": True,
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    }
                }
            }
        ],
        "properties": {
            "relations": {
                "type": "join",
                "relations": {
                    "organization": ["worker", "dummy-organization"],
                    "user": ["dummy-user"],
                    "worker": ["dummy-worker"],
                    "job": ["artifact", "dummy-job"],
                    "artifact": ["dummy-artifact"]
                }
            },
            "key": {
                "type": "keyword",
                "ignore_above": 256
            },
            "status": {
                "type": "keyword",
                "ignore_above": 256
            }
        }
    }
}


CORTEX_INDEX_BODY = {
    "settings": CORTEX_INDEX_TEMPLATE["settings"],
    "mappings": CORTEX_INDEX_TEMPLATE["mappings"],
}


def es_request(method, path, body=None):
    url = f"{ES_URL}/{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if ES_AUTH:
        headers["Authorization"] = f"Basic {ES_AUTH}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read())}
    except Exception as e:
        return {"error": str(e)}


def wait_for_es(timeout=120):
    print("Waiting for Elasticsearch...", end="", flush=True)
    headers = {"Authorization": f"Basic {ES_AUTH}"} if ES_AUTH else {}
    for _ in range(timeout):
        try:
            req = urllib.request.Request(f"{ES_URL}/_cluster/health", headers=headers)
            with urllib.request.urlopen(req, timeout=2) as r:
                data = json.loads(r.read())
                if data.get("status") in ("green", "yellow", "red"):
                    print(f" ready (status: {data.get('status')}).")
                    return True
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(1)
    print(" TIMEOUT")
    return False


def wait_for_cortex(timeout=120):
    print("Waiting for Cortex...", end="", flush=True)
    for _ in range(timeout):
        try:
            with urllib.request.urlopen(f"{CORTEX_URL}/api/status", timeout=2) as r:
                if r.status == 200:
                    print(" ready.")
                    return True
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(1)
    print(" TIMEOUT")
    return False


def delete_index():
    print(f"Deleting index {ES_INDEX}...")
    result = es_request("DELETE", ES_INDEX)
    if result.get("acknowledged"):
        print("  Deleted.")
    elif "index_not_found" in str(result):
        print("  Did not exist, skipping.")
    else:
        print(f"  Result: {result}")


def create_index_template():
    print("Creating ES index template (join field fix for elastic4play)...")
    result = es_request("PUT", "_template/cortex_template", CORTEX_INDEX_TEMPLATE)
    if result.get("acknowledged"):
        print("  Template created.")
    else:
        print(f"  Result: {result}")


def ensure_cortex_index():
    """Pre-create the Cortex index with the join-field mapping if it is missing.

    On a fresh install Cortex may fail to auto-create cortex_6 because of
    elastic4play/ES 7.x incompatibilities. Creating it up-front lets user and
    organisation creation succeed.
    """
    print(f"Ensuring Cortex index {ES_INDEX} exists...")
    result = es_request("GET", f"{ES_INDEX}/_count")
    if "count" in result:
        print("  Index already exists.")
        return True
    result = es_request("PUT", ES_INDEX, CORTEX_INDEX_BODY)
    if result.get("acknowledged") or result.get("shards_acknowledged"):
        print("  Index created.")
        return True
    if "resource_already_exists" in str(result):
        print("  Index already exists.")
        return True
    print(f"  ERROR creating index: {result}")
    return False


def _parse_cortex_response(resp):
    try:
        text = resp.read().decode()
        if not text:
            return {"ok": True, "data": None}
        text = text.strip()
        try:
            return {"ok": True, "data": json.loads(text)}
        except json.JSONDecodeError:
            # Cortex /api/user/{login}/key/renew returns a plain API key string
            return {"ok": True, "data": text.strip().strip('"')}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _cortex_request(method, path, body=None, auth=None, timeout=30):
    url = f"{CORTEX_URL}/api/{path}"
    data = json.dumps(body).encode() if body is not None else None
    if data is None and method in ("POST", "PUT", "PATCH"):
        data = b""
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Basic {auth}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return _parse_cortex_response(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            payload = json.loads(body)
        except Exception:
            payload = {"message": body}
        if payload is None:
            payload = {"message": body}
        return {"ok": False, "status": e.code, "error": payload}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _error_str(result):
    err = result.get("error", {})
    return json.dumps(err) if isinstance(err, dict) else str(err)


def _cortex_api(method, path, body=None, auth=None, retries=5, delay=3):
    current_auth = auth
    for attempt in range(1, retries + 1):
        result = _cortex_request(method, path, body=body, auth=current_auth)
        if result["ok"]:
            return result
        err_str = _error_str(result)
        if "already exist" in err_str or "AlreadyExist" in err_str or "Conflict" in err_str:
            return {"ok": True, "data": {"_id": "exists"}}
        if ("AuthenticationError" in err_str or "AuthorizationError" in err_str) and current_auth == INIT_AUTH and ADMIN_AUTH:
            print(f"  Init auth failed, switching to admin auth...")
            current_auth = ADMIN_AUTH
            continue
        print(f"  Cortex {method} /api/{path} attempt {attempt} failed: {err_str}")
        if attempt < retries:
            time.sleep(delay)
    return result


def create_superadmin():
    print(f"Creating superadmin user '{SUPERADMIN_USER}' in '{CORTEX_ORG}'...")
    payload = {
        "login": SUPERADMIN_USER,
        "name": "Super Admin",
        "password": ADMIN_PASS,
        "roles": ["superAdmin"],
        "organization": CORTEX_ORG,
    }
    result = _cortex_api("POST", "user", payload, auth=INIT_AUTH)
    if result["ok"]:
        print(f"  Created: {result['data'].get('_id')}")
        return True
    err_str = _error_str(result)
    if "already exist" in err_str or "AlreadyExist" in err_str or "Conflict" in err_str:
        verify = _cortex_api("GET", f"user/{SUPERADMIN_USER}", auth=ADMIN_AUTH)
        if verify["ok"]:
            print("  Superadmin already exists and auth works.")
            return True
    print(f"  ERROR: {err_str}")
    return False


def ensure_organization(org, auth):
    print(f"Ensuring organization '{org}'...")
    result = _cortex_api("POST", "organization", {"name": org, "description": "SOAR Lab analyzers organization"}, auth=auth)
    if result["ok"]:
        print(f"  Created: {result['data'].get('_id')}")
        return True
    err_str = _error_str(result)
    if "already exist" in err_str or "AlreadyExist" in err_str or "Conflict" in err_str:
        print("  Organization already exists.")
        return True
    print(f"  ERROR: {err_str}")
    return False


def create_orgadmin():
    print(f"Creating orgadmin user '{ORG_ADMIN_USER}' in '{WORK_ORG}'...")
    payload = {
        "login": ORG_ADMIN_USER,
        "name": "SOAR Lab Org Admin",
        "password": ADMIN_PASS,
        "roles": ["read", "analyze", "orgAdmin"],
        "organization": WORK_ORG,
    }
    result = _cortex_api("POST", "user", payload, auth=ADMIN_AUTH)
    if result["ok"]:
        print(f"  Created: {result['data'].get('_id')}")
        return True
    err_str = _error_str(result)
    if "already exist" in err_str or "AlreadyExist" in err_str or "Conflict" in err_str:
        verify = _cortex_api("GET", f"user/{ORG_ADMIN_USER}", auth=ORG_ADMIN_AUTH)
        if verify["ok"]:
            print("  Orgadmin already exists and auth works.")
            return True
    print(f"  ERROR: {err_str}")
    return False


def generate_orgadmin_api_key():
    print(f"Generating API key for {ORG_ADMIN_USER}...")
    result = _cortex_api("POST", f"user/{ORG_ADMIN_USER}/key/renew", auth=ADMIN_AUTH)
    if not result["ok"]:
        result = _cortex_api("POST", f"user/{ORG_ADMIN_USER}/key/renew", auth=ORG_ADMIN_AUTH)
    if result["ok"]:
        raw = result.get("data")
        if isinstance(raw, bytes):
            raw = raw.decode()
        if isinstance(raw, str):
            raw = raw.strip().strip('"')
        if raw and len(str(raw)) > 10:
            print("  API key generated.")
            return str(raw)
    print(f"  ERROR: {result}")
    return None


def update_env_file(api_key):
    if not api_key or not os.path.exists(ENV_FILE):
        return
    print(f"Updating {ENV_FILE}...")
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"CORTEX_ADMIN_USER=.*", f"CORTEX_ADMIN_USER={ORG_ADMIN_USER}", content)
        content = re.sub(r"CORTEX_ADMIN_PASSWORD=.*", f"CORTEX_ADMIN_PASSWORD={ADMIN_PASS}", content)
        content = re.sub(r"CORTEX_API_KEY=.*", f"CORTEX_API_KEY={api_key}", content)
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print("  Done.")
    except OSError as e:
        print(f"  Warning: Could not update {ENV_FILE}: {e}")
        print("  API key generated but not saved to file.")


def index_exists():
    result = es_request("GET", f"{ES_INDEX}/_count")
    return "error" not in result and "count" in result


def main():
    force_reset = "--reset" in sys.argv

    print("=" * 60)
    print("Cortex Init Script" if not force_reset else "Cortex Reset Script")
    print("=" * 60)

    if not wait_for_es():
        print("ERROR: Elasticsearch is not running.", file=sys.stderr)
        sys.exit(1)

    print("Ensuring single-node template (0 replicas)...")
    sn_result = es_request("PUT", "_template/single_node", {
        "index_patterns": ["*"],
        "order": -1,
        "settings": {"number_of_replicas": 0}
    })
    if sn_result.get("acknowledged"):
        print("  Template created.")
    else:
        print(f"  Result: {sn_result}")

    create_index_template()

    if force_reset:
        delete_index()
        print("Index deleted - full setup will run.")
    elif not index_exists():
        print("Index does not exist - full setup will run.")
    else:
        print(f"Index {ES_INDEX} already exists - will only ensure org/user exist.")

    if not ensure_cortex_index():
        print("ERROR: Could not ensure Cortex index.", file=sys.stderr)
        sys.exit(1)

    if not wait_for_cortex():
        print("ERROR: Cortex is not running. Start containers first.", file=sys.stderr)
        sys.exit(1)

    if not ensure_organization(CORTEX_ORG, INIT_AUTH):
        print(f"ERROR: Could not create/verify default '{CORTEX_ORG}' organization.", file=sys.stderr)
        sys.exit(1)

    if not create_superadmin():
        print("ERROR: Could not create/verify superadmin user.", file=sys.stderr)
        sys.exit(1)
    if not ensure_organization(WORK_ORG, ADMIN_AUTH):
        print("ERROR: Could not create/verify work organization.", file=sys.stderr)
        sys.exit(1)
    if not create_orgadmin():
        print("ERROR: Could not create/verify orgadmin user.", file=sys.stderr)
        sys.exit(1)

    api_key = generate_orgadmin_api_key()
    update_env_file(api_key)

    print("\n" + "=" * 60)
    print("Done!")
    print(f"  URL:        {CORTEX_URL}")
    print(f"  Superadmin: {SUPERADMIN_USER} / <redacted>")
    print(f"  Org admin:  {ORG_ADMIN_USER} / <redacted>")
    if api_key:
        print("  API key:    configured")
    print("=" * 60)


if __name__ == "__main__":
    main()
