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
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request

from soar_lab.common.constants import (
    AUTH_BASIC_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)

logger = logging.getLogger(__name__)

ES_URL = os.environ.get("ELASTICSEARCH_URL", os.environ.get("ES_URL", "http://elasticsearch:9200"))
CORTEX_URL = os.environ.get("CORTEX_URL", "http://cortex:9001")
ES_INDEX = "cortex"
SUPERADMIN_USER = "admin"
ADMIN_PASS = os.environ.get("CORTEX_ADMIN_PASSWORD", "")
CORTEX_ORG = os.environ.get("CORTEX_ORG", "cortex")
WORK_ORG = "soar-lab"
ORG_ADMIN_USER = os.environ.get("CORTEX_ADMIN_USER", "soaradmin")
INIT_AUTH = base64.b64encode(b"init:init").decode()
ADMIN_AUTH = (
    base64.b64encode(f"{SUPERADMIN_USER}:{ADMIN_PASS}".encode()).decode() if ADMIN_PASS else ""
)
ORG_ADMIN_AUTH = (
    base64.b64encode(f"{ORG_ADMIN_USER}:{ADMIN_PASS}".encode()).decode() if ADMIN_PASS else ""
)
ES_USER = os.environ.get("ELASTIC_USERNAME", "elastic")
ES_PASS = os.environ.get("ELASTIC_PASSWORD", "")
ES_AUTH = base64.b64encode(f"{ES_USER}:{ES_PASS}".encode()).decode() if ES_PASS else ""
ENV_FILE = ".env.full"

if not ADMIN_PASS:
    # Just a sanity check; we will try to load from .env.full in main()
    pass

CORTEX_INDEX_TEMPLATE = {
    "index_patterns": ["cortex_*"],
    "settings": {"number_of_shards": 1, "number_of_replicas": 0},
    "mappings": {
        "dynamic_templates": [
            {
                "strings": {
                    "match_mapping_type": "string",
                    "mapping": {
                        "type": "text",
                        "fielddata": True,
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
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
                    "artifact": ["dummy-artifact"],
                },
            },
            "key": {"type": "keyword", "ignore_above": 256},
            "status": {"type": "keyword", "ignore_above": 256},
            "organization": {"type": "keyword", "ignore_above": 256},
            "createdBy": {"type": "keyword", "ignore_above": 256},
            "updatedBy": {"type": "keyword", "ignore_above": 256},
            "name": {"type": "keyword", "ignore_above": 256},
            "workerName": {"type": "keyword", "ignore_above": 256},
            "workerId": {"type": "keyword", "ignore_above": 256},
            "workerDefinitionId": {"type": "keyword", "ignore_above": 256},
            "dataType": {"type": "keyword", "ignore_above": 256},
            "type": {"type": "keyword", "ignore_above": 256},
        },
    },
}

CORTEX_INDEX_BODY = {
    "settings": CORTEX_INDEX_TEMPLATE["settings"],
    "mappings": CORTEX_INDEX_TEMPLATE["mappings"],
}


def es_request(method, path, body=None):
    url = f"{ES_URL}/{path}"
    data = json.dumps(body).encode() if body else None
    headers = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}
    if ES_AUTH:
        headers[HEADER_AUTHORIZATION] = f"{AUTH_BASIC_PREFIX} {ES_AUTH}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:  # nosec B310
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read())}
    except Exception as e:
        return {"error": str(e)}


def wait_for_es(timeout=120):
    logger.info("Waiting for Elasticsearch...")
    headers = {HEADER_AUTHORIZATION: f"{AUTH_BASIC_PREFIX} {ES_AUTH}"} if ES_AUTH else {}
    for _ in range(timeout):
        try:
            req = urllib.request.Request(f"{ES_URL}/_cluster/health", headers=headers)
            with urllib.request.urlopen(req, timeout=2) as r:  # nosec B310
                data = json.loads(r.read())
                if data.get("status") in ("green", "yellow", "red"):
                    logger.info(f" ready (status: {data.get('status')}).")
                    return True
        except Exception as _e:
            logging.debug("ES not ready: %s", _e)
        logger.debug(".")
        time.sleep(1)
    logger.warning(" TIMEOUT")
    return False


def wait_for_cortex(timeout=180):
    logger.info("Waiting for Cortex...")
    for _ in range(timeout):
        try:
            # Check status and verify if it's actually initialized (not 5xx)
            with urllib.request.urlopen(f"{CORTEX_URL}/api/status", timeout=2) as r:  # nosec B310
                if r.status == 200:
                    # Additional check: can we reach the API?
                    logger.info(" ready.")
                    time.sleep(2)  # Grace period
                    return True
        except Exception as _e:
            logging.debug("Cortex not ready: %s", _e)
        logger.debug(".")
        time.sleep(2)
    logger.warning(" TIMEOUT")
    return False


def delete_index():
    logger.info(f"Deleting indices matching '{ES_INDEX}*'...")
    result = es_request("DELETE", f"{ES_INDEX}*")
    if result.get("acknowledged"):
        logger.info("  Deleted.")
    elif "index_not_found" in str(result):
        logger.info("  Did not exist, skipping.")
    else:
        logger.info(f"  Result: {result}")


def create_index_template():
    logger.info("Creating ES index template (join field fix for elastic4play)...")
    result = es_request("PUT", "_template/cortex_template", CORTEX_INDEX_TEMPLATE)
    if result.get("acknowledged"):
        logger.info("  Template created.")
    else:
        logger.info(f"  Result: {result}")


def ensure_cortex_index():
    """Pre-create the Cortex index with the join-field mapping if it is
    missing.

    On a fresh install Cortex may fail to auto-create cortex_6 because
    of elastic4play/ES 7.x incompatibilities. Creating it up-front lets
    user and organisation creation succeed.
    """
    logger.info(f"Ensuring Cortex index {ES_INDEX} exists...")
    result = es_request("GET", f"{ES_INDEX}/_count")
    if "count" in result:
        logger.info("  Index already exists.")
        return True
    result = es_request("PUT", ES_INDEX, CORTEX_INDEX_BODY)
    if result.get("acknowledged") or result.get("shards_acknowledged"):
        logger.info("  Index created.")
        return True
    if "resource_already_exists" in str(result):
        logger.info("  Index already exists.")
        return True
    logger.error(f"  ERROR creating index: {result}")
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
    headers = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}
    if auth:
        headers[HEADER_AUTHORIZATION] = f"{AUTH_BASIC_PREFIX} {auth}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
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
        # Distinguish timeouts from other errors so callers can retry/verify
        err_name = type(e).__name__
        if "timeout" in err_name.lower() or "timed out" in str(e).lower():
            return {"ok": False, "error": "timed out", "timeout": True}
        return {"ok": False, "error": str(e)}


def _error_str(result):
    err = result.get("error", {})
    return json.dumps(err) if isinstance(err, dict) else str(err)


def _cortex_api(method, path, body=None, auth=None, retries=5, delay=3, timeout=30):
    current_auth = auth
    for attempt in range(1, retries + 1):
        result = _cortex_request(method, path, body=body, auth=current_auth, timeout=timeout)
        if result["ok"]:
            return result
        err_str = _error_str(result)
        # Handle "already exist" silently
        if "already exist" in err_str or "AlreadyExist" in err_str or "Conflict" in err_str:
            return {"ok": True, "data": {"_id": "exists"}}

        if (
            (
                "AuthenticationError" in err_str
                or "AuthorizationError" in err_str
                or "forbidden" in err_str.lower()
            )
            and current_auth == INIT_AUTH
            and ADMIN_AUTH
        ):
            # Do not print warning yet, just retry silently
            current_auth = ADMIN_AUTH
            continue
        # Timeouts: Cortex may still be processing. Don't spam retries.
        if result.get("timeout"):
            logger.warning(
                f"  Cortex {method} /api/{path} attempt {attempt} timed out ({timeout}s)"
            )
        else:
            logger.warning(f"  Cortex {method} /api/{path} attempt {attempt} failed: {err_str}")
        if attempt < retries:
            time.sleep(delay)
    return result


def create_superadmin():
    global ADMIN_AUTH
    logger.info(f"Creating superadmin user '{SUPERADMIN_USER}' in '{CORTEX_ORG}'...")
    payload = {
        "login": SUPERADMIN_USER,
        "name": "Super Admin",
        "password": ADMIN_PASS,
        "roles": ["superAdmin"],
        "organization": CORTEX_ORG,
    }
    # Cortex's first user creation can take >30s on a fresh index.
    # Use a generous timeout and only 1 attempt — if it times out we verify
    # whether the user was actually created (Cortex often finishes server-side
    # even when the client gives up).
    result = _cortex_api("POST", "user", payload, auth=INIT_AUTH, retries=1, delay=5, timeout=120)
    if result["ok"]:
        logger.info(f"  Created: {result['data'].get('_id')}")
        return True

    # If it failed, maybe it's already there? Try with ADMIN_AUTH
    logger.info("  Failed to create with init auth, checking if superadmin already exists...")
    verify = _cortex_api(
        "GET", f"user/{SUPERADMIN_USER}", auth=ADMIN_AUTH, retries=5, delay=5, timeout=30
    )
    if verify["ok"]:
        logger.info("  Superadmin already exists and auth works.")
        return True

    # Timeout scenario: Cortex may have created the user but the client timed
    # out before reading the response.  Wait a few seconds for Cortex to settle,
    # then retry auth.  If auth still fails the user record is corrupt (known
    # bug when the POST is interrupted mid-write) and the caller must reset the
    # index.
    if result.get("timeout"):
        logger.warning("  POST timed out — waiting 10s for Cortex to settle, then retrying auth...")
        time.sleep(10)
        verify = _cortex_api(
            "GET", f"user/{SUPERADMIN_USER}", auth=ADMIN_AUTH, retries=3, delay=5, timeout=30
        )
        if verify["ok"]:
            logger.info("  Superadmin created (late) and auth works.")
            return True
        logger.warning("  Superadmin record appears corrupt (auth fails after timeout).")
        logger.warning("  Reset the cortex index and re-run with --reset to fix.")
    logger.error(f"  ERROR: {result.get('error')}")
    return False


def ensure_organization(org, auth):
    logger.info(f"Ensuring organization '{org}'...")
    # Increase retries and timeout for organization creation as Cortex might be
    # slow after index reset (first write on a fresh ES index).
    result = _cortex_api(
        "POST",
        "organization",
        {"name": org, "description": "SOAR Lab analyzers organization"},
        auth=auth,
        retries=5,
        delay=5,
        timeout=120,
    )
    if result["ok"]:
        logger.info(f"  Created: {result['data'].get('_id')}")
        return True
    err_str = _error_str(result)
    if "already exist" in err_str or "AlreadyExist" in err_str or "Conflict" in err_str:
        logger.info("  Organization already exists.")
        return True
    logger.error(f"  ERROR: {err_str}")
    return False


def create_orgadmin():
    logger.info(f"Creating orgadmin user '{ORG_ADMIN_USER}' in '{WORK_ORG}'...")
    payload = {
        "login": ORG_ADMIN_USER,
        "name": "SOAR Lab Org Admin",
        "password": ADMIN_PASS,
        "roles": ["read", "analyze", "orgAdmin"],
        "organization": WORK_ORG,
    }
    result = _cortex_api("POST", "user", payload, auth=ADMIN_AUTH, timeout=120)
    if result["ok"]:
        logger.info(f"  Created: {result['data'].get('_id')}")
        return True
    err_str = _error_str(result)
    if "already exist" in err_str or "AlreadyExist" in err_str or "Conflict" in err_str:
        verify = _cortex_api("GET", f"user/{ORG_ADMIN_USER}", auth=ORG_ADMIN_AUTH)
        if verify["ok"]:
            logger.info("  Orgadmin already exists and auth works.")
            return True
    logger.error(f"  ERROR: {err_str}")
    return False


def generate_orgadmin_api_key():
    logger.info(f"Generating API key for {ORG_ADMIN_USER}...")
    result = _cortex_api("POST", f"user/{ORG_ADMIN_USER}/key/renew", auth=ADMIN_AUTH, timeout=60)
    if not result["ok"]:
        result = _cortex_api(
            "POST", f"user/{ORG_ADMIN_USER}/key/renew", auth=ORG_ADMIN_AUTH, timeout=60
        )
    if result["ok"]:
        raw = result.get("data")
        if isinstance(raw, bytes):
            raw = raw.decode()
        if isinstance(raw, str):
            raw = raw.strip().strip('"')
        if raw and len(str(raw)) > 10:
            logger.info("  API key generated.")
            return str(raw)
    logger.error(f"  ERROR: {result}")
    return None


def update_env_file(api_key):
    if not api_key or not os.path.exists(ENV_FILE):
        return
    logger.info(f"Updating {ENV_FILE}...")
    try:
        with open(ENV_FILE, encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r"CORTEX_ADMIN_USER=.*", f"CORTEX_ADMIN_USER={ORG_ADMIN_USER}", content)
        content = re.sub(
            r"CORTEX_ADMIN_PASSWORD=.*", f"CORTEX_ADMIN_PASSWORD={ADMIN_PASS}", content
        )
        content = re.sub(r"CORTEX_API_KEY=.*", f"CORTEX_API_KEY={api_key}", content)
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("  Done.")
    except OSError as e:
        logger.warning(f"  Warning: Could not update {ENV_FILE}: {e}")
        logger.warning("  API key generated but not saved to file.")


def index_exists():
    result = es_request("GET", f"{ES_INDEX}/_count")
    return "error" not in result and "count" in result


def main():
    global ADMIN_AUTH
    global ADMIN_PASS
    global ORG_ADMIN_AUTH
    force_reset = "--reset" in sys.argv

    # Try to load secrets from .env.full if not set
    if not os.environ.get("CORTEX_ADMIN_PASSWORD") and os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            content = f.read()
            m = re.search(r"^CORTEX_ADMIN_PASSWORD=(.+)$", content, re.MULTILINE)
            if m:
                ADMIN_PASS = m.group(1).strip().strip('"')
                ADMIN_AUTH = base64.b64encode(f"{SUPERADMIN_USER}:{ADMIN_PASS}".encode()).decode()
                ORG_ADMIN_AUTH = base64.b64encode(
                    f"{ORG_ADMIN_USER}:{ADMIN_PASS}".encode()
                ).decode()

    if not ADMIN_PASS:
        logger.error(
            "[ERROR] Missing CORTEX_ADMIN_PASSWORD. Set it in .env.full "
            "or as an environment variable and retry."
        )
        sys.exit(1)

    print("=" * 60)
    print("Cortex Init Script" if not force_reset else "Cortex Reset Script")
    print("=" * 60)

    if not wait_for_es():
        logger.error("ERROR: Elasticsearch is not running.")
        sys.exit(1)

    logger.info("Ensuring single-node template (0 replicas)...")
    sn_result = es_request(
        "PUT",
        "_template/single_node",
        {"index_patterns": ["*"], "order": -1, "settings": {"number_of_replicas": 0}},
    )
    if sn_result.get("acknowledged"):
        logger.info("  Template created.")
    else:
        logger.info(f"  Result: {sn_result}")

    create_index_template()

    if force_reset:
        delete_index()
        logger.info("Index deleted - full setup will run.")
    elif not index_exists():
        logger.info("Index does not exist - full setup will run.")
    else:
        logger.info(f"Index {ES_INDEX} already exists - will only ensure org/user exist.")

    if not ensure_cortex_index():
        logger.error("ERROR: Could not ensure Cortex index.")
        sys.exit(1)

    if not wait_for_cortex():
        logger.error("ERROR: Cortex is not running. Start containers first.")
        sys.exit(1)

    current_auth = INIT_AUTH
    if not ensure_organization(CORTEX_ORG, current_auth):
        logger.info(f"  [cortex] Org '{CORTEX_ORG}' setup check...")

    if not create_superadmin():
        # Last-resort recovery: the superadmin record may be corrupt (known
        # bug when the POST times out mid-write).  Delete the cortex index,
        # recreate it, restart Cortex internally, and try once more.
        if not force_reset:
            logger.warning("  Superadmin creation failed — attempting automatic index reset...")
            delete_index()
            if not ensure_cortex_index():
                logger.error("ERROR: Could not ensure Cortex index after reset.")
                sys.exit(1)
            # Give Cortex a moment to notice the index change
            time.sleep(5)
            if not ensure_organization(CORTEX_ORG, INIT_AUTH):
                logger.info(f"  [cortex] Org '{CORTEX_ORG}' setup check (post-reset)...")
            if not create_superadmin():
                logger.error("ERROR: Could not create/verify superadmin user after reset.")
                sys.exit(1)
        else:
            logger.error("ERROR: Could not create/verify superadmin user.")
            sys.exit(1)
    if not ensure_organization(WORK_ORG, ADMIN_AUTH):
        logger.error("ERROR: Could not create/verify work organization.")
        sys.exit(1)
    if not create_orgadmin():
        logger.error("ERROR: Could not create/verify orgadmin user.")
        sys.exit(1)

    # Re-verify admin auth before key generation
    ADMIN_AUTH = base64.b64encode(f"{SUPERADMIN_USER}:{ADMIN_PASS}".encode()).decode()

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
