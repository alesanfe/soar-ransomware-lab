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
import logging
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from soar_lab.common.constants import (
    AUTH_BASIC_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)

logger = logging.getLogger(__name__)

ES_URL = os.environ.get("ELASTICSEARCH_URL", os.environ.get("ES_URL", "http://elasticsearch:9200"))
THEHIVE_URL = os.environ.get("THEHIVE_URL", "http://thehive:9000")
CORTEX_URL = os.environ.get("CORTEX_URL", "http://cortex:9001")
ES_INDEX = "the_hive"
ADMIN_USER = os.environ.get("THEHIVE_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("THEHIVE_ADMIN_PASSWORD", "")
ADMIN_AUTH = base64.b64encode(f"{ADMIN_USER}:{ADMIN_PASS}".encode()).decode()
ES_USER = os.environ.get("ELASTIC_USERNAME", "elastic")
ES_PASS = os.environ.get("ELASTIC_PASSWORD", "")
ES_AUTH = base64.b64encode(f"{ES_USER}:{ES_PASS}".encode()).decode() if ES_PASS else ""
ENV_FILE = ".env.full"

if not ADMIN_PASS:
    # Just a sanity check; we will try to load from .env.full in main()
    pass

THEHIVE_INDEX_TEMPLATE = {
    "index_patterns": ["the_hive_*"],
    "settings": {"number_of_shards": 5, "number_of_replicas": 0},
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
                    "dblist": ["dblistitem"],
                },
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
            "dblist": {"type": "keyword"},
        },
    },
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


def thehive_request(method, path, body=None, auth=None):
    url = f"{THEHIVE_URL}/api/{path}"
    data = json.dumps(body).encode() if body else None
    headers = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}
    if auth:
        headers[HEADER_AUTHORIZATION] = f"{AUTH_BASIC_PREFIX} {auth}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:  # nosec B310
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return {"error": json.loads(e.read())}
        except Exception:
            return {"error": e.reason}
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
                # Accept any status (green, yellow, red) as long as ES is responding
                if data.get("status") in ("green", "yellow", "red"):
                    logger.info(f" ready (status: {data.get('status')}).")
                    return True
        except Exception as _e:
            logging.debug("ES not ready: %s", _e)
        logger.debug(".")
        time.sleep(1)
    logger.warning(" TIMEOUT")
    return False


def wait_for_thehive(timeout=180):
    logger.info("Waiting for TheHive...")
    for _ in range(timeout):
        try:
            with urllib.request.urlopen(f"{THEHIVE_URL}/api/status", timeout=2) as r:  # nosec B310
                if r.status == 200:
                    # Double check: sometimes status is 200 but backend is not ready
                    body = r.read().decode()
                    if "OK" in body.upper() or "version" in body.lower():
                        logger.info(" ready.")
                        time.sleep(2)  # Grace period
                        return True
        except Exception as _e:
            logging.debug("TheHive not ready: %s", _e)
        logger.debug(".")
        time.sleep(2)
    logger.warning(" TIMEOUT")
    return False


def index_exists():
    result = es_request("GET", f"{ES_INDEX}/_count")
    return "error" not in result and "count" in result


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
    logger.info("Creating ES index template for TheHive (join field + keyword fix)...")
    result = es_request("PUT", "_template/thehive_template", THEHIVE_INDEX_TEMPLATE)
    if result.get("acknowledged"):
        logger.info("  Template created.")
    else:
        logger.info(f"  Result: {result}")


def wait_for_admin_auth(timeout=120):
    logger.info("  Waiting for admin authentication")
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = thehive_request("GET", f"user/{ADMIN_USER}", auth=ADMIN_AUTH)
        if "error" not in result:
            logger.info(" ready.")
            return True
        logger.debug(".")
        time.sleep(2)
    logger.warning(" TIMEOUT")
    return False


def create_admin_user():
    logger.info(f"Ensuring admin user '{ADMIN_USER}' exists...")
    for attempt in range(1, 6):
        result = thehive_request(
            "POST",
            "user",
            {
                "login": ADMIN_USER,
                "name": "Admin",
                "password": ADMIN_PASS,
                "roles": ["read", "write", "admin"],
            },
        )
        if "error" not in result:
            logger.info(f"  Created: {result.get('_id')}")
            return wait_for_admin_auth()

        err = str(result)
        # Check if already exists or auth works
        if wait_for_admin_auth(timeout=5):
            logger.info("  Admin user already exists and credentials are valid.")
            return True

        logger.warning(f"  Attempt {attempt}/5 failed: {err[:100]}...")
        if attempt < 5:
            time.sleep(5)

    logger.warning("  Warning: Admin user creation might have failed, but continuing setup...")
    return True  # Allow other steps to proceed


def generate_api_key():
    logger.info(f"Generating API key for {ADMIN_USER}...")
    # Retry logic for generating API key
    max_retries = 5
    retry_delay = 5
    for attempt in range(max_retries):
        url = f"{THEHIVE_URL}/api/user/{ADMIN_USER}/key/renew"
        req = urllib.request.Request(
            url,
            data=b"{}",
            method="POST",
            headers={
                HEADER_AUTHORIZATION: f"{AUTH_BASIC_PREFIX} {ADMIN_AUTH}",
                HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # nosec B310
                raw = resp.read().decode().strip().strip('"')
                if len(raw) > 10:
                    logger.info("  API key generated")
                    return raw
        except Exception as e:
            logger.error(f"  ERROR: {e}")
            if attempt < max_retries - 1:
                logger.info(
                    f"  Retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(retry_delay)
                continue
    logger.error("  Failed to generate API key after multiple retries.")
    return None


def populate_observable_types(auth):
    logger.info("Populating observable data types...")
    types = [
        "domain",
        "file",
        "filename",
        "fqdn",
        "hash",
        "ip",
        "mail",
        "mail_subject",
        "other",
        "regexp",
        "registry",
        "uri_path",
        "url",
        "user-agent",
    ]
    added = 0
    for t in types:
        url = f"{THEHIVE_URL}/api/list/list_artifactDataType"
        data = json.dumps({"value": t}).encode()
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={
                HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
                HEADER_AUTHORIZATION: f"{AUTH_BASIC_PREFIX} {auth}",
            },
        )
        try:
            with urllib.request.urlopen(req):  # nosec B310
                added += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if "AlreadyExist" in body or "ConflictError" in body:
                added += 1
            else:
                logger.warning(f"  WARN {t}: {e.code} {body[:80]}")
        except Exception as ex:
            logger.warning(f"  WARN {t}: {ex}")
    logger.info(f"  Observable types registered: {added}/{len(types)}")


def update_env_file(api_key):
    if not api_key or not os.path.exists(ENV_FILE):
        return
    logger.info(f"Updating {ENV_FILE}...")
    try:
        with open(ENV_FILE) as f:
            content = f.read()
        content = re.sub(r"THEHIVE_API_KEY=.*", f"THEHIVE_API_KEY={api_key}", content)
        with open(ENV_FILE, "w") as f:
            f.write(content)
        logger.info("  Done.")
    except OSError as e:
        logger.warning(f"  Warning: Could not update {ENV_FILE}: {e}")
        logger.warning("  API key generated but not saved to file.")


def configure_cortex():
    """Write the Cortex API key into thehive.conf and restart thehive to load
    it."""
    cortex_key = ""
    if os.path.exists(ENV_FILE):
        m = re.search(r"^CORTEX_API_KEY=(.+)$", open(ENV_FILE).read(), re.MULTILINE)
        if m:
            cortex_key = m.group(1).strip()
    if not cortex_key:
        cortex_key = os.environ.get("CORTEX_API_KEY", "")
    if not cortex_key:
        logger.info("  [cortex] No CORTEX_API_KEY available; skipping Cortex configuration.")
        return

    conf_path = Path("/app/infra/docker/config/thehive.application.conf/thehive.conf")
    if not conf_path.exists():
        logger.info(f"  [cortex] {conf_path} not mounted; skipping Cortex configuration.")
        return

    try:
        config = json.loads(conf_path.read_text(encoding="utf-8"))
        # TheHive 3.5.2 entrypoint generates cortex.cortex1.url/key from TH_CORTEX_* env vars.
        # The included application.conf is loaded after, so we must override the same
        # HOCON path to ensure host, port and key are correct.
        config["cortex"] = {"cortex1": {"url": CORTEX_URL, "key": cortex_key}}
        conf_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("  [cortex] Updated thehive.conf with Cortex key.")
    except Exception as e:
        logger.error(f"  [cortex] ERROR updating thehive.conf: {e}")
        return

    thehive_container = os.environ.get("THEHIVE_CONTAINER", "soar_thehive")
    try:
        logger.info(f"  [cortex] Restarting {thehive_container} to load Cortex config...")
        subprocess.run(["docker", "restart", thehive_container], check=True, timeout=60)  # nosec B603 B607
        logger.info("  [cortex] Restart command issued.")
    except Exception as e:
        logger.error(f"  [cortex] ERROR restarting {thehive_container}: {e}")
        return

    if not wait_for_thehive():
        logger.warning("  [cortex] WARN: TheHive did not become ready after restart.")
        return

    try:
        with urllib.request.urlopen(f"{THEHIVE_URL}/api/status", timeout=10) as r:  # nosec B310
            status = json.loads(r.read())
        cortex = status.get("connectors", {}).get("cortex", {})
        logger.info(f"  [cortex] TheHive connector status: {cortex.get('status', 'unknown')}")
    except Exception as e:
        logger.warning(f"  [cortex] Could not verify TheHive status: {e}")


def ensure_thehive_index():
    logger.info(f"Ensuring TheHive index {ES_INDEX} exists...")
    result = es_request("GET", f"{ES_INDEX}/_count")
    if "count" in result:
        logger.info("  Index already exists.")
        return True
    # TheHive 3.x uses specific mappings, but creating the index shell is often enough
    # for it to start its own migrations without 520 errors.
    result = es_request("PUT", ES_INDEX, {})
    if result.get("acknowledged"):
        logger.info("  Index created.")
        return True
    if "resource_already_exists" in str(result):
        return True
    logger.warning(f"  Warning: Could not create index: {result}")
    return False


def main():
    global ADMIN_PASS
    global ADMIN_AUTH
    force_reset = "--reset" in sys.argv

    # Try to load secrets from .env.full if not set
    if not os.environ.get("THEHIVE_ADMIN_PASSWORD") and os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            content = f.read()
            m = re.search(r"^THEHIVE_ADMIN_PASSWORD=(.+)$", content, re.MULTILINE)
            if m:
                ADMIN_PASS = m.group(1).strip().strip('"')
                ADMIN_AUTH = base64.b64encode(f"{ADMIN_USER}:{ADMIN_PASS}".encode()).decode()

    if not ADMIN_PASS:
        logger.error(
            "[ERROR] Missing THEHIVE_ADMIN_PASSWORD. Set it in .env.full "
            "or as an environment variable and retry."
        )
        sys.exit(1)

    print("=" * 60)
    print("TheHive Init Script" if not force_reset else "TheHive Reset Script")
    print("=" * 60)

    if not wait_for_es():
        logger.error("ERROR: Elasticsearch is not running.")
        sys.exit(1)

    create_index_template()

    if force_reset:
        delete_index()
        logger.info("Index deleted — full setup will run.")
    elif not index_exists():
        logger.info("Index does not exist — full setup will run.")
    else:
        logger.info(f"Index {ES_INDEX} already exists — will only ensure user exists.")

    ensure_thehive_index()

    if not wait_for_thehive():
        logger.error("ERROR: TheHive is not running. Start containers first.")
        sys.exit(1)

    if not create_admin_user():
        logger.error("ERROR: TheHive admin initialization failed.")
        sys.exit(1)
    api_key = generate_api_key()
    if not api_key:
        logger.error("ERROR: TheHive API key generation failed.")
        sys.exit(1)
    update_env_file(api_key)
    populate_observable_types(ADMIN_AUTH)
    configure_cortex()

    print("\n" + "=" * 60)
    print("Done!")
    print(f"  URL:        {THEHIVE_URL}")
    print(f"  Login:      {ADMIN_USER} / <redacted>")
    print("  Bearer key: configured" if api_key else "")
    print("=" * 60)


if __name__ == "__main__":
    main()
