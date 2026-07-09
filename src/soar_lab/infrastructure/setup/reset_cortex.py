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
ADMIN_USER = os.environ.get("CORTEX_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("CORTEX_ADMIN_PASSWORD", "J5x#8mP3$vR2@nQ7tW4!zY9&hF1sD6")
CORTEX_ORG = os.environ.get("CORTEX_ORG", "cortex")
INIT_AUTH = base64.b64encode(b"init:init").decode()
ADMIN_AUTH = base64.b64encode(f"{ADMIN_USER}:{ADMIN_PASS}".encode()).decode()
ENV_FILE = ".env.full"

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
            }
        }
    }
}


def es_request(method, path, body=None):
    url = f"{ES_URL}/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read())}
    except Exception as e:
        return {"error": str(e)}


def cortex_request(method, path, body=None, auth=None):
    url = f"{CORTEX_URL}/api/{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Basic {auth}"
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
    for _ in range(timeout):
        try:
            with urllib.request.urlopen(f"{ES_URL}/_cluster/health", timeout=2) as r:
                data = json.loads(r.read())
                # Accept any status (green, yellow, red) as long as ES is responding
                if data.get("status") in ("green", "yellow", "red"):
                    print(f" ready (status: {data.get('status')}).")
                    return True
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(1)
    print(" TIMEOUT")
    return False


def wait_for_cortex(timeout=60):
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


def create_organization():
    print(f"Creating organization '{CORTEX_ORG}'...")
    result = cortex_request("POST", "organization",
                            {"name": CORTEX_ORG, "description": "Default organization"},
                            auth=INIT_AUTH)
    if "error" in result:
        err = str(result)
        if "already exist" in err or "AlreadyExist" in err or "Conflict" in err:
            print(f"  Already exists, skipping.")
        elif "AuthenticationError" in err:
            print(f"  Init user unavailable — org likely already exists, skipping.")
        else:
            print(f"  ERROR: {result}")
    else:
        print(f"  Created: {result.get('_id')}")


def create_admin_user():
    print(f"Creating admin user ({ADMIN_USER}/{ADMIN_PASS})...")
    result = cortex_request("POST", "user",
                            {"login": ADMIN_USER, "name": "Admin User",
                             "password": ADMIN_PASS,
                             "roles": ["read", "analyze", "orgadmin"],
                             "organization": CORTEX_ORG},
                            auth=INIT_AUTH)
    if "error" in result:
        err = str(result)
        if "already exist" in err or "AlreadyExist" in err or "Conflict" in err:
            print(f"  Already exists, skipping.")
        elif "AuthenticationError" in err:
            verify = cortex_request("GET", f"user/{ADMIN_USER}", auth=ADMIN_AUTH)
            if "error" not in verify:
                print(f"  Already exists (verified with admin auth), skipping.")
            else:
                print(f"  ERROR: init user unavailable and admin not found: {verify}")
        else:
            print(f"  ERROR: {result}")
    else:
        print(f"  Created: {result.get('_id')}")


def generate_api_key():
    print(f"Generating API key for {ADMIN_USER}...")
    url = f"{CORTEX_URL}/api/user/{ADMIN_USER}/key/renew"
    req = urllib.request.Request(url, data=b"", method="POST",
                                 headers={"Authorization": f"Basic {ADMIN_AUTH}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode().strip().strip('"')
            if len(raw) > 10:
                print(f"  API key: {raw}")
                return raw
    except Exception as e:
        print(f"  ERROR: {e}")
    return None


def update_env_file(api_key):
    if not api_key or not os.path.exists(ENV_FILE):
        return
    print(f"Updating {ENV_FILE}...")
    try:
        with open(ENV_FILE, "r") as f:
            content = f.read()
        content = re.sub(r"CORTEX_API_KEY=.*", f"CORTEX_API_KEY={api_key}", content)
        with open(ENV_FILE, "w") as f:
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

    # Ensure single-node ES stays green (0 replicas for all indices)
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
        print("Index deleted — full setup will run.")
    elif not index_exists():
        print("Index does not exist — full setup will run.")
    else:
        print(f"Index {ES_INDEX} already exists — will only ensure org/user exist.")

    if not wait_for_cortex():
        print("ERROR: Cortex is not running. Start containers first.", file=sys.stderr)
        sys.exit(1)

    create_organization()
    create_admin_user()
    api_key = generate_api_key()
    update_env_file(api_key)

    print("\n" + "=" * 60)
    print("Done!")
    print(f"  URL:     {CORTEX_URL}")
    print(f"  Login:   {ADMIN_USER} / {ADMIN_PASS}")
    if api_key:
        print(f"  API key: {api_key}")
    print("=" * 60)


if __name__ == "__main__":
    main()
