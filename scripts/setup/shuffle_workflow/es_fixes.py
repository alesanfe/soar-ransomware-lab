"""Elasticsearch/OpenSearch index fixes for Shuffle.

Two idempotent fixes that run during setup:

1. ``fix_es_users_mapping`` — recreate the ``users`` / ``users_v2``
   indices with ``apikey`` mapped as ``text`` + ``keyword`` subfield
   (Shuffle uses ``apikey.keyword`` for term queries) and sync the
   ``apikey`` field inside ``organizations`` docs.

2. ``fix_workflow_execution_mapping`` — add ``started_at`` / ``completed_at``
   date fields to ``workflowexecution-*`` indices (required by Shuffle 1.2+).

3. ``sync_apikey`` — synchronize the admin user's apikey in OpenSearch
   with ``SHUFFLE_DEFAULT_APIKEY`` from ``.env.full``.  Needed because
   ``validate_api_key`` generates a new random key on every call,
   desynchronizing the DB from the environment used by Orborus and the
   ``soar_api`` keepalive loop.
"""

# NOTE: All ``requests`` calls in this module use ``verify=False`` because
# the lab uses self-signed certificates in the internal Docker network.
# This is safe in the lab context but must NOT be used in production.

from __future__ import annotations

import base64
import logging
import os
import time

import requests

from soar_lab.common.constants import (
    AUTH_BASIC_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)

from . import config

logger = logging.getLogger(__name__)


def _es_headers() -> dict[str, str]:
    h = {HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON}
    if config.SHUFFLE_DATA_USER and config.SHUFFLE_DATA_PASS:
        auth = base64.b64encode(
            f"{config.SHUFFLE_DATA_USER}:{config.SHUFFLE_DATA_PASS}".encode()
        ).decode()
        h[HEADER_AUTHORIZATION] = f"{AUTH_BASIC_PREFIX} {auth}"
    return h


def _es_auth_tuple():
    if config.SHUFFLE_DATA_USER and config.SHUFFLE_DATA_PASS:
        return (config.SHUFFLE_DATA_USER, config.SHUFFLE_DATA_PASS)
    return None


def fix_es_users_mapping() -> None:
    """Fix Shuffle authentication issues in Elasticsearch.

    Two separate issues cause 401 errors:

    1. 'users' index: 'apikey' field auto-mapped as 'text' → term queries
       return 0 hits.  Fix: recreate index with apikey as 'text' + keyword subfield.

    2. 'organizations' index: user entries inside org docs have apikey set
       to empty string (out-of-sync with 'users' index) → GetApikey falls
       through to org lookup, finds empty string, returns "no users found".
       Fix: sync apikey from 'users' into org user entries.

    Both fixes are idempotent.
    """
    _es = config.SHUFFLE_DATA_URL
    _h = _es_headers()

    # Wait up to 60 s for ES to be available
    for _attempt in range(12):
        try:
            _r = requests.get(f"{_es}/_cluster/health", headers=_h, timeout=5, verify=False)
            if _r.status_code < 300:
                break
        except Exception as _e:
            logging.debug("ES not ready: %s", _e)
        logger.info("[es-fix] Waiting for Elasticsearch... (%ds)", _attempt * 5)
        time.sleep(5)
    else:
        logger.warning("[es-fix] ES not available, skipping mapping fix")
        return

    _correct_mapping = {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {
            "dynamic": True,
            "properties": {
                "apikey": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "id": {"type": "keyword"},
                "username": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "session": {"type": "keyword"},
            },
        },
    }

    # Check if the mapping already has apikey.keyword subfield
    _has_kw_subfield = False
    try:
        _mr = requests.get(f"{_es}/users/_mapping", headers=_h, timeout=10, verify=False)
        if _mr.status_code == 200:
            _apikey_prop = (
                _mr.json()
                .get("users", {})
                .get("mappings", {})
                .get("properties", {})
                .get("apikey", {})
            )
            _has_kw_subfield = "keyword" in _apikey_prop.get("fields", {})
    except Exception as _e:
        logger.warning("[es-fix] Could not read mapping: %s", _e)

    def _reindex_users(idx_name):
        """Delete, recreate with correct mapping, and re-insert all user
        docs."""
        try:
            _sr = requests.get(
                f"{_es}/{idx_name}/_search?size=100", headers=_h, timeout=10, verify=False
            )
            _docs = _sr.json().get("hits", {}).get("hits", []) if _sr.status_code == 200 else []
        except Exception as _e:
            logger.warning("[es-fix] Error reading %s: %s", idx_name, _e)
            _docs = []
        requests.delete(f"{_es}/{idx_name}", headers=_h, timeout=10, verify=False)
        _cr = requests.put(
            f"{_es}/{idx_name}", headers=_h, json=_correct_mapping, timeout=10, verify=False
        )
        if _cr.status_code not in (200, 201):
            logger.error(
                "[es-fix] Error creating %s: %d %s", idx_name, _cr.status_code, _cr.text[:100]
            )
            return
        for _doc in _docs:
            _ir = requests.put(
                f"{_es}/{idx_name}/_doc/{_doc['_id']}",
                headers=_h,
                json=_doc["_source"],
                timeout=10,
                verify=False,
            )
            if _ir.status_code not in (200, 201):
                logger.warning("[es-fix] Error inserting into %s: %d", idx_name, _ir.status_code)
        requests.post(f"{_es}/{idx_name}/_refresh", headers=_h, timeout=5, verify=False)
        _sample_key = _docs[0]["_source"].get("apikey", "") if _docs else ""
        if _sample_key:
            _vr = requests.post(
                f"{_es}/{idx_name}/_search",
                headers=_h,
                timeout=10,
                verify=False,
                json={"query": {"term": {"apikey.keyword": _sample_key}}},
            )
            _hits = (
                _vr.json().get("hits", {}).get("total", {}).get("value", 0)
                if _vr.status_code == 200
                else -1
            )
            logger.info(
                "[es-fix] %s: reindexed OK — %d doc(s), apikey.keyword query hits=%d",
                idx_name,
                len(_docs),
                _hits,
            )
        else:
            logger.info("[es-fix] %s: reindexed OK — %d doc(s)", idx_name, len(_docs))

    if _has_kw_subfield:
        logger.info(
            "[es-fix] 'users.apikey' mapping already has keyword subfield — checking users_v2"
        )
    else:
        logger.info("[es-fix] Fixing 'users' mapping (adding apikey.keyword subfield) ...")
        _reindex_users("users")

    # Always ensure users_v2 exists with correct mapping and contains the user
    _v2_ok = False
    try:
        _v2r = requests.get(f"{_es}/users_v2/_mapping", headers=_h, timeout=10, verify=False)
        if _v2r.status_code == 200:
            _v2_apikey = (
                _v2r.json()
                .get("users_v2", {})
                .get("mappings", {})
                .get("properties", {})
                .get("apikey", {})
            )
            _v2_ok = "keyword" in _v2_apikey.get("fields", {})
    except Exception as _e:
        logging.debug("Could not read users_v2 mapping: %s", _e)
    if not _v2_ok:
        logger.info("[es-fix] Creating/fixing users_v2 with correct mapping ...")
        _reindex_users("users_v2")
    else:
        _u_r = requests.get(f"{_es}/users/_search?size=100", headers=_h, timeout=10, verify=False)
        _u2_r = requests.get(
            f"{_es}/users_v2/_search?size=100", headers=_h, timeout=10, verify=False
        )
        _u_docs = _u_r.json().get("hits", {}).get("hits", []) if _u_r.status_code == 200 else []
        _u2_count = (
            _u2_r.json().get("hits", {}).get("total", {}).get("value", 0)
            if _u2_r.status_code == 200
            else 0
        )
        if _u_docs and _u2_count == 0:
            logger.info("[es-fix] users_v2 empty — copying users ...")
            for _d in _u_docs:
                requests.put(
                    f"{_es}/users_v2/_doc/{_d['_id']}",
                    headers=_h,
                    json=_d["_source"],
                    timeout=10,
                    verify=False,
                )
            requests.post(f"{_es}/users_v2/_refresh", headers=_h, timeout=5, verify=False)
            logger.info("[es-fix] users_v2: %d user(s) copied", len(_u_docs))
        else:
            logger.info("[es-fix] users_v2: OK")

    # ── 2. Fix apikey in 'organizations' index ────────────────────────────────
    try:
        _usr_r = requests.get(f"{_es}/users/_search?size=100", headers=_h, timeout=10, verify=False)
        _usr_map = {}
        if _usr_r.status_code == 200:
            for _u in _usr_r.json().get("hits", {}).get("hits", []):
                _s = _u["_source"]
                if _s.get("apikey"):
                    _usr_map[_s.get("id", "")] = _s["apikey"]
                    _usr_map[_s.get("username", "")] = _s["apikey"]

        _org_r = requests.get(
            f"{_es}/organizations/_search?size=20", headers=_h, timeout=10, verify=False
        )
        if _org_r.status_code == 200:
            _org_fixed = 0
            for _org_hit in _org_r.json().get("hits", {}).get("hits", []):
                _org_id = _org_hit["_id"]
                _org_src = _org_hit["_source"]
                _changed = False
                for _u in _org_src.get("users", []):
                    _correct_key = _usr_map.get(_u.get("id", "")) or _usr_map.get(
                        _u.get("username", "")
                    )
                    if _correct_key and _u.get("apikey", "") != _correct_key:
                        _u["apikey"] = _correct_key
                        _changed = True
                if _changed:
                    _pr = requests.put(
                        f"{_es}/organizations/_doc/{_org_id}",
                        headers=_h,
                        json=_org_src,
                        timeout=10,
                        verify=False,
                    )
                    if _pr.status_code in (200, 201):
                        _org_fixed += 1
            if _org_fixed:
                logger.info(
                    "[es-fix] organizations: %d doc(s) with apikey synchronized", _org_fixed
                )
            else:
                logger.info("[es-fix] organizations: apikeys already synchronized")
    except Exception as _e:
        logger.error("[es-fix] Error fixing organizations: %s", _e)


def fix_workflow_execution_mapping() -> None:
    """Fix Shuffle workflow execution index mapping to include started_at
    field.

    Shuffle 1.2+ requires 'started_at' field for sorting workflow executions.
    Without this field, queries fail with: "No mapping found for [started_at]".

    This fix is idempotent - it only adds the mapping if the field doesn't exist.
    """
    _es = config.SHUFFLE_DATA_URL
    _h = _es_headers()

    try:
        _r = requests.get(
            f"{_es}/workflowexecution-*/_mapping", headers=_h, timeout=10, verify=False
        )
        if _r.status_code != 200:
            logger.info("[workflow-fix] No workflowexecution indices found, skipping")
            return

        _mappings = _r.json()
        _needs_fix = False

        for _idx_name, _idx_data in _mappings.items():
            if not _idx_name.startswith("workflowexecution-"):
                continue
            _props = _idx_data.get("mappings", {}).get("properties", {})
            if "started_at" not in _props:
                _needs_fix = True
                logger.info("[workflow-fix] Index %s lacks started_at field", _idx_name)
                break

        if not _needs_fix:
            logger.info("[workflow-fix] workflowexecution indices already have started_at field")
            return

        logger.info("[workflow-fix] Adding started_at field to workflowexecution indices...")
        for _idx_name, _idx_data in _mappings.items():
            if not _idx_name.startswith("workflowexecution-"):
                continue
            _put_r = requests.put(
                f"{_es}/{_idx_name}/_mapping",
                headers=_h,
                json={
                    "properties": {
                        "started_at": {"type": "date"},
                        "completed_at": {"type": "date"},
                    }
                },
                timeout=10,
                verify=False,
            )
            if _put_r.status_code in (200, 201):
                logger.info("[workflow-fix] Added started_at to %s", _idx_name)
            else:
                logger.warning(
                    "[workflow-fix] Failed to add started_at to %s: %d",
                    _idx_name,
                    _put_r.status_code,
                )

    except Exception as _e:
        logger.error("[workflow-fix] Error fixing workflow execution mapping: %s", _e)


def sync_apikey() -> None:
    """Synchronize the admin user's apikey in OpenSearch with ``SHUFFLE_DEFAULT_APIKEY``.

    The Shuffle backend's ``validate_api_key`` calls
    ``GET /api/v1/users/generateapikey`` which **generates a new random
    apikey** on every invocation.  This overwrites the key stored in the
    ``users`` / ``users_v2`` indices but does NOT update
    ``SHUFFLE_DEFAULT_APIKEY`` in ``.env.full``.

    As a result, the Orborus and the ``soar_api`` keepalive loop (both of
    which read the apikey from the environment at container start) keep
    using the stale key and produce a flood of::

        WARNING  Api authentication failed in getworkflows: No users found for this apikey

    This function restores consistency by writing the ``.env.full`` apikey
    back into the ``users``, ``users_v2`` and ``organizations`` indices.
    It is idempotent and safe to call at any time.
    """
    _es = config.SHUFFLE_DATA_URL
    _h = _es_headers()

    # Read the expected apikey from .env.full (or environment)
    _expected_key = os.environ.get("SHUFFLE_DEFAULT_APIKEY", "")
    if not _expected_key and os.path.exists(config.ENV_FILE):
        import re as _re

        with open(config.ENV_FILE) as _f:
            _m = _re.search(r"^SHUFFLE_DEFAULT_APIKEY=(.+)$", _f.read(), _re.MULTILINE)
        if _m:
            _expected_key = _m.group(1).strip()
    if not _expected_key:
        logger.warning("[apikey-sync] SHUFFLE_DEFAULT_APIKEY not set — skipping")
        return

    # Find the admin user in users_v2
    try:
        _sr = requests.get(
            f"{_es}/users_v2/_search?size=100", headers=_h, timeout=10, verify=False
        )
        _hits = _sr.json().get("hits", {}).get("hits", []) if _sr.status_code == 200 else []
    except Exception as _e:
        logger.warning("[apikey-sync] Could not read users_v2: %s", _e)
        return

    _fixed = 0
    for _hit in _hits:
        _uid = _hit["_id"]
        _current = _hit["_source"].get("apikey", "")
        if _current == _expected_key:
            continue
        # Update users_v2
        requests.post(
            f"{_es}/users_v2/_update/{_uid}",
            headers=_h,
            json={"doc": {"apikey": _expected_key}},
            timeout=10,
            verify=False,
        )
        # Update users (old index) if it exists
        requests.post(
            f"{_es}/users/_update/{_uid}",
            headers=_h,
            json={"doc": {"apikey": _expected_key}},
            timeout=10,
            verify=False,
        )
        _fixed += 1
        logger.info("[apikey-sync] Updated user %s apikey in users/users_v2", _uid)

    # Sync organizations index
    try:
        _org_r = requests.get(
            f"{_es}/organizations/_search?size=20", headers=_h, timeout=10, verify=False
        )
        if _org_r.status_code == 200:
            for _org_hit in _org_r.json().get("hits", {}).get("hits", []):
                _org_src = _org_hit["_source"]
                _changed = False
                for _u in _org_src.get("users", []):
                    if _u.get("apikey", "") != _expected_key:
                        _u["apikey"] = _expected_key
                        _changed = True
                if _changed:
                    requests.put(
                        f"{_es}/organizations/_doc/{_org_hit['_id']}",
                        headers=_h,
                        json=_org_src,
                        timeout=10,
                        verify=False,
                    )
                    logger.info(
                        "[apikey-sync] Synced apikey in organization %s", _org_hit["_id"]
                    )
    except Exception as _e:
        logger.warning("[apikey-sync] Error syncing organizations: %s", _e)

    requests.post(
        f"{_es}/users_v2,users,organizations/_refresh",
        headers=_h, timeout=5, verify=False,
    )
    if _fixed:
        logger.info("[apikey-sync] %d user(s) updated — DB now matches .env.full", _fixed)
    else:
        logger.info("[apikey-sync] apikey already in sync")


def update_env_file(key: str, value: str) -> None:
    """Update or append a key=value line in ``.env.full``.

    Used when ``validate_api_key`` generates a new Shuffle API key that
    must be persisted back to the environment file so that Orborus and
    the ``soar_api`` keepalive loop use the same key.
    """
    import re

    env_path = config.ENV_FILE
    if not os.path.exists(env_path):
        logger.warning("[env-update] %s not found — skipping", env_path)
        return

    with open(env_path, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(content):
        new_content = pattern.sub(f"{key}={value}", content)
    else:
        new_content = content.rstrip("\n") + f"\n{key}={value}\n"

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    logger.info("[env-update] %s updated in %s", key, env_path)
