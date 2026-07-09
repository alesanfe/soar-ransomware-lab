#!/usr/bin/env python3
"""
init_thehive.py - Initialises TheHive 3.x index and admin user.

Root cause of the elastic4play join field bug (same as Cortex):
  elastic4play stores `relations` as a plain string for root entities and as
  an object for child entities. ES 7.x cannot handle both types in one field.
  Fix: pre-create an ES index template that declares `relations` as a proper
  join field with dummy children for each root type.

  Additionally, TheHive 3.x auth-by-key requires `status`, `key`, `login`,
  and `password` to be mapped as `keyword` (not `text`) so that term queries
  work correctly during authentication.

Usage:
  python init_thehive.py           # idempotent — only creates what is missing
  python init_thehive.py --reset   # deletes the_hive_17 index and recreates all
"""

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ES_URL = os.environ.get("ES_URL", "http://elasticsearch:9200")
THEHIVE_URL = os.environ.get("THEHIVE_URL", "http://thehive:9000")
ES_INDEX = "the_hive_17"
ADMIN_USER = os.environ.get("THEHIVE_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("THEHIVE_ADMIN_PASSWORD", "X8k#2mP5$vR9@nQ3tW6!zY1&hF4sD7")
ADMIN_AUTH = base64.b64encode(f"{ADMIN_USER}:{ADMIN_PASS}".encode()).decode()
ENV_FILE = ".env.full"

THEHIVE_INDEX_TEMPLATE = {
    "index_patterns": ["the_hive_*"],
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
                    "case": ["case_task", "case_artifact", "dummy-case"],
                    "case_task": ["case_task_log", "dummy-case_task"],
                    "case_task_log": ["dummy-case_task_log"],
                    "case_artifact": ["dummy-case_artifact"],
                    "caseTemplate": ["dummy-caseTemplate"],
                    "alert": ["dummy-alert"],
                    "user": ["dummy-user"],
                    "dashboard": ["dummy-dashboard"],
                    "audit": ["dummy-audit"],
                    "sequence": ["dummy-sequence"],
                    "dblist": ["dblistitem"]
                }
            },
            "key": {"type": "keyword"},
            "password": {"type": "keyword"},
            "status": {"type": "keyword"},
            "login": {"type": "keyword"},
            "flag": {"type": "boolean"},
            "tlp": {"type": "integer"},
            "pap": {"type": "integer"},
            "severity": {"type": "integer"},
            "caseId": {"type": "integer"},
            "startDate": {"type": "date"},
            "endDate": {"type": "date"},
            "createdAt": {"type": "date"},
            "updatedAt": {"type": "date"},
            "date": {"type": "date"},
            "order": {"type": "integer"},
            "ioc": {"type": "boolean"},
            "sighted": {"type": "boolean"},
            "ignoreSimilarity": {"type": "boolean"},
            "dblist": {"type": "keyword"}
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


def thehive_request(method, path, body=None, auth=None):
    url = f"{THEHIVE_URL}/api/{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Basic {auth}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return {"error": json.loads(e.read())}
        except Exception:
            return {"error": e.reason}
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


def wait_for_thehive(timeout=180):
    print("Waiting for TheHive...", end="", flush=True)
    for _ in range(timeout):
        try:
            with urllib.request.urlopen(f"{THEHIVE_URL}/api/status", timeout=2) as r:
                if r.status == 200:
                    print(" ready.")
                    return True
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(1)
    print(" TIMEOUT")
    return False


def index_exists():
    result = es_request("GET", f"{ES_INDEX}/_count")
    return "error" not in result and "count" in result


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
    print("Creating ES index template for TheHive (join field + keyword fix)...")
    result = es_request("PUT", "_template/thehive_template", THEHIVE_INDEX_TEMPLATE)
    if result.get("acknowledged"):
        print("  Template created.")
    else:
        print(f"  Result: {result}")


def create_admin_user():
    print(f"Creating admin user ({ADMIN_USER}/{ADMIN_PASS})...")
    # Retry logic for creating admin user
    max_retries = 5
    retry_delay = 5
    for attempt in range(max_retries):
        result = thehive_request("POST", "user", {
            "login": ADMIN_USER,
            "name": "Admin",
            "password": ADMIN_PASS,
            "roles": ["read", "write", "admin"]
        })
        if "error" in result:
            err = str(result)
            if "already exist" in err or "AlreadyExist" in err or "Conflict" in err:
                print("  Already exists, attempting to reset password...")
                # Try to reset password for existing user
                reset_result = thehive_request("POST", f"user/{ADMIN_USER}/password", {
                    "password": ADMIN_PASS
                })
                if "error" in reset_result:
                    print(f"  Password reset failed: {reset_result}")
                    # Try with auth if initial reset fails
                    reset_result = thehive_request("POST", f"user/{ADMIN_USER}/password", {
                        "password": ADMIN_PASS
                    }, auth=ADMIN_AUTH)
                    if "error" in reset_result:
                        print(f"  Password reset with auth also failed: {reset_result}")
                    else:
                        print("  Password reset successfully with auth.")
                        return
                else:
                    print("  Password reset successfully.")
                    return
            elif "AuthenticationError" in err or "forbidden" in err.lower():
                verify = thehive_request("GET", f"user/{ADMIN_USER}", auth=ADMIN_AUTH)
                if "error" not in verify:
                    print("  Already exists (verified with admin auth), skipping.")
                    return
                else:
                    print(f"  ERROR: init user unavailable and admin not found: {verify}")
            else:
                print(f"  ERROR: {result}")
                if attempt < max_retries - 1:
                    print(f"  Retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
        else:
            print(f"  Created: {result.get('_id')}")
            return
    print("  Failed to create admin user after multiple retries.")


def generate_api_key():
    print(f"Generating API key for {ADMIN_USER}...")
    # Retry logic for generating API key
    max_retries = 5
    retry_delay = 5
    for attempt in range(max_retries):
        url = f"{THEHIVE_URL}/api/user/{ADMIN_USER}/key/renew"
        req = urllib.request.Request(url, data=b"{}", method="POST",
                                     headers={"Authorization": f"Basic {ADMIN_AUTH}",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode().strip().strip('"')
                if len(raw) > 10:
                    print(f"  API key: {raw}")
                    return raw
        except Exception as e:
            print(f"  ERROR: {e}")
            if attempt < max_retries - 1:
                print(f"  Retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                continue
    print("  Failed to generate API key after multiple retries.")
    return None


def populate_observable_types(auth):
    print("Populating observable data types...")
    types = [
        "domain", "file", "filename", "fqdn", "hash", "ip",
        "mail", "mail_subject", "other", "regexp", "registry",
        "uri_path", "url", "user-agent",
    ]
    added = 0
    for t in types:
        url = f"{THEHIVE_URL}/api/list/list_artifactDataType"
        data = json.dumps({"value": t}).encode()
        req = urllib.request.Request(url, data=data, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Basic {auth}"})
        try:
            with urllib.request.urlopen(req) as resp:
                added += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if "AlreadyExist" in body or "ConflictError" in body:
                added += 1
            else:
                print(f"  WARN {t}: {e.code} {body[:80]}")
        except Exception as ex:
            print(f"  WARN {t}: {ex}")
    print(f"  Observable types registered: {added}/{len(types)}")


def update_env_file(api_key):
    if not api_key or not os.path.exists(ENV_FILE):
        return
    print(f"Updating {ENV_FILE}...")
    try:
        with open(ENV_FILE, "r") as f:
            content = f.read()
        content = re.sub(r"THEHIVE_API_KEY=.*", f"THEHIVE_API_KEY={api_key}", content)
        with open(ENV_FILE, "w") as f:
            f.write(content)
        print("  Done.")
    except OSError as e:
        print(f"  Warning: Could not update {ENV_FILE}: {e}")
        print("  API key generated but not saved to file.")


def main():
    force_reset = "--reset" in sys.argv

    print("=" * 60)
    print("TheHive Init Script" if not force_reset else "TheHive Reset Script")
    print("=" * 60)

    if not wait_for_es():
        print("ERROR: Elasticsearch is not running.", file=sys.stderr)
        sys.exit(1)

    create_index_template()

    if force_reset:
        delete_index()
        print("Index deleted — full setup will run.")
    elif not index_exists():
        print("Index does not exist — full setup will run.")
    else:
        print(f"Index {ES_INDEX} already exists — will only ensure user exists.")

    if not wait_for_thehive():
        print("ERROR: TheHive is not running. Start containers first.", file=sys.stderr)
        sys.exit(1)

    create_admin_user()
    api_key = generate_api_key()
    update_env_file(api_key)
    populate_observable_types(ADMIN_AUTH)

    print("\n" + "=" * 60)
    print("Done!")
    print(f"  URL:        {THEHIVE_URL}")
    print(f"  Login:      {ADMIN_USER} / {ADMIN_PASS}")
    print(f"  Bearer key: Authorization: Bearer {api_key}" if api_key else "")
    print("=" * 60)


if __name__ == "__main__":
    main()
