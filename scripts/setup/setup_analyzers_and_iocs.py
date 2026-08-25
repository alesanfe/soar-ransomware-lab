#!/usr/bin/env python3
"""Installs free analyzers in Cortex and loads the project IOCs into MISP.

Installed analyzers (no external API key required):
  - FileInfo_8_0       -- analyzes file hashes (metadata)
  - Malwarebazaar_1_0  -- hash lookup in MalwareBazaar (free, no key)
  - OTXQuery_2_0       -- AlienVault OTX (free key, we use anon)
  - Abuse_Finder_3_0   -- abuse lookup in domains/IPs (no key)
  - DomainTools_Iris_Investigate_1_0  -- skip (paid)

IOCs loaded into MISP from tests/e2e/fixtures/ioc_samples.json
"""

import base64
import json
import logging
import os
import sys
import time
import warnings

import requests
from dotenv import dotenv_values

from soar_lab.common.constants import (
    AUTH_BASIC_PREFIX,
    AUTH_BEARER_PREFIX,
    CONTENT_TYPE_JSON,
    HEADER_ACCEPT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
)

logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore")

# Prefer .env.full (mounted in container at /app/.env.full) over .env
_env = dotenv_values(".env.full")
if not _env:
    _env = dotenv_values(".env")

# The API container is created before reset_cortex.py updates .env.full, so its
# environment variables are stale. Prefer the mounted .env.full file, which is
# the authoritative source of the credentials and keys generated during setup.
CORTEX_URL = _env.get("CORTEX_URL") or os.environ.get("CORTEX_URL", "http://cortex:9001")
CORTEX_API_KEY = _env.get("CORTEX_API_KEY", "") or os.environ.get("CORTEX_API_KEY", "")
CORTEX_USER = (
    _env.get("CORTEX_ADMIN_USER")
    or _env.get("CORTEX_USER")
    or os.environ.get("CORTEX_USER")
    or os.environ.get("CORTEX_ADMIN_USER")
    or "admin"
)
CORTEX_PASS = (
    _env.get("CORTEX_ADMIN_PASSWORD")
    or _env.get("CORTEX_PASS")
    or os.environ.get("CORTEX_PASS")
    or os.environ.get("CORTEX_ADMIN_PASSWORD")
    or ""
)
CORTEX_BASIC_AUTH = base64.b64encode(f"{CORTEX_USER}:{CORTEX_PASS}".encode()).decode()
MISP_URL = _env.get("MISP_URL") or os.environ.get("MISP_URL", "http://misp:80")
MISP_KEY = _env.get("MISP_API_KEY", "") or os.environ.get("MISP_API_KEY", "")

if not CORTEX_API_KEY and not CORTEX_PASS:
    logger.error("[ERROR] Missing CORTEX_ADMIN_PASSWORD/CORTEX_PASS or CORTEX_API_KEY")
    sys.exit(1)

if not MISP_KEY:
    logger.error("[ERROR] Missing MISP_API_KEY")
    sys.exit(1)


def cortex_headers(use_basic=False):
    if CORTEX_API_KEY and not use_basic:
        return {HEADER_AUTHORIZATION: f"{AUTH_BEARER_PREFIX} {CORTEX_API_KEY}"}
    return {HEADER_AUTHORIZATION: f"{AUTH_BASIC_PREFIX} {CORTEX_BASIC_AUTH}"}


def cortex_request(method, path, json_data=None, retries=3, delay=3, timeout=60):
    url = f"{CORTEX_URL}/api/{path}"
    use_basic = False
    for attempt in range(1, retries + 1):
        headers = cortex_headers(use_basic=use_basic)
        if json_data is not None:
            headers[HEADER_CONTENT_TYPE] = CONTENT_TYPE_JSON
        try:
            resp = requests.request(method, url, headers=headers, json=json_data, timeout=timeout)
            if resp.status_code == 401 and CORTEX_API_KEY and not use_basic:
                logger.warning(
                    f"  Cortex Bearer auth failed for /api/{path}; falling back to basic auth."
                )
                use_basic = True
                continue
            if resp.status_code in (200, 201, 204, 409):
                return resp
            # 4xx/5xx other than 409 should not block make up; return the response
            return resp
        except Exception as e:
            logger.warning(f"  Cortex {method} /api/{path} attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    return None


def misp_request(method, path, json_data=None, retries=10, delay=5, timeout=30):
    url = f"{MISP_URL}/{path}"
    headers = {
        HEADER_AUTHORIZATION: MISP_KEY,
        HEADER_CONTENT_TYPE: CONTENT_TYPE_JSON,
        HEADER_ACCEPT: CONTENT_TYPE_JSON,
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.request(
                method, url, headers=headers, json=json_data, verify=False, timeout=timeout
            )
            if resp.status_code == 403 and "already" not in resp.text.lower():
                logger.warning(
                    f"  MISP {method} /{path} attempt {attempt}: {resp.status_code} -"
                    f" {resp.text[:120]}"
                )
                if attempt < retries:
                    time.sleep(delay)
                continue
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.warning(f"  MISP {method} /{path} attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    return None


# -- 1. Cortex analyzer definitions ------------------------------------
print("=" * 60)
print("CORTEX - installing free analyzers")
print("=" * 60)

r = cortex_request("GET", "analyzerdefinition")
definitions = r.json() if r and r.ok else []

# Load currently installed analyzers to avoid duplicate/conflicting POSTs
r_installed = cortex_request("GET", "analyzer")
installed_map = {}
if r_installed and r_installed.ok:
    for a in r_installed.json():
        installed_map[
            a.get("workerDefinitionId") or a.get("analyzerDefinitionId") or a.get("name")
        ] = a

free_analyzers = []
for d in definitions:
    config_items = d.get("configurationItems", [])
    # Avoid analyzers that require external API keys or credentials
    excluded_names = {"api_key", "key", "username", "password", "token", "secret"}
    # Filter required items, excluding common global options
    required_items = [
        c
        for c in config_items
        if c.get("required", False)
        and c.get("name")
        not in ("max_tlp", "max_pap", "proxy_http", "proxy_https", "auto_extract_artifacts")
    ]

    # If any remaining required item looks like a credential, skip it
    if required_items and any(c.get("name", "").lower() in excluded_names for c in required_items):
        continue

    # De-duplicate: If we have multiple analyzers for the same function,
    # we could filter them here, but the instruction is to only remove
    # if it's already covered by another. However, Cortex workers are
    # unique by ID, so we keep the existing logic of not re-installing
    # if the ID matches.

    if not required_items:
        free_analyzers.append(d)

logger.info(f"Total definitions: {len(definitions)}")
logger.info(f"Analyzers without required config: {len(free_analyzers)}")

USEFUL_TYPES = {"hash", "ip", "domain", "url", "mail"}
useful = [a for a in free_analyzers if set(a.get("dataTypeList", [])) & USEFUL_TYPES]

logger.info(f"\nInstalling {len(useful)} useful analyzers...")
installed = len(installed_map)
for a in useful:
    aid = a["id"]
    if aid in installed_map:
        logger.info(f"  [DUP] {aid} (already installed)")
        continue
    payload = {
        "name": a["name"],
        "configuration": {
            "max_tlp": 3,
            "max_pap": 3,
            "check_tlp": False,
            "check_pap": False,
            "auto_extract_artifacts": False,
        },
    }
    ri = cortex_request(
        "POST", f"organization/analyzer/{aid}", json_data=payload, retries=1, delay=0
    )
    if ri is None:
        logger.error(f"  [ERR] {aid} failed after retries")
        continue
    if ri.ok:
        logger.info(f"  [OK ] {aid}")
        installed += 1
        installed_map[aid] = {"id": aid}
    elif ri.status_code == 409:
        logger.info(f"  [DUP] {aid} (already installed)")
        installed_map[aid] = {"id": aid}
    else:
        logger.error(f"  [ERR] {aid} HTTP {ri.status_code}: {ri.text[:80]}")

r2 = cortex_request("GET", "analyzer")
installed_list = r2.json() if r2 and r2.ok else []
logger.info(f"\nAnalyzers installed: {len(installed_list)}")
for a in installed_list[:8]:
    logger.info(f"  {a.get('name', '?'):35} datatypes: {a.get('dataTypeList', [])}")

# -- 2. MISP IOCs ------------------------------------------------------
print()
print("=" * 60)
print("MISP - loading lab IOCs")
print("=" * 60)

with open("tests/e2e/fixtures/ioc_samples.json") as f:
    ioc_data = json.load(f)

malicious_cases = ioc_data.get("malicious_test_cases", [])
malicious = {
    "hash": (
        list({c.get("hash", "") for c in malicious_cases if c.get("hash")})[0]
        if malicious_cases
        else ""
    ),
    "ips": list({c.get("ip", "") for c in malicious_cases if c.get("ip")}),
    "domains": list({c.get("domain", "") for c in malicious_cases if c.get("domain")}),
    "urls": list({c.get("url", "") for c in malicious_cases if c.get("url")}),
}

logger.info("Waiting for MISP API key to be accepted...")
misp_ready = None
for _ in range(30):
    probe = misp_request("GET", "servers/getPyMISPVersion", retries=1, delay=0)
    if probe is not None and probe.ok:
        misp_ready = probe
        logger.info("  MISP API ready.")
        break
    logger.info("  MISP not ready yet, retrying...")
    time.sleep(5)

if not misp_ready:
    logger.error("[ERROR] MISP API key not accepted after retries.")
    sys.exit(1)

event_payload = {
    "Event": {
        "info": "SOAR Lab - Ransomware IOCs (malicious)",
        "distribution": 0,
        "threat_level_id": 1,
        "analysis": 2,
        "Attribute": [],
    }
}

if malicious.get("hash"):
    event_payload["Event"]["Attribute"].append(
        {
            "type": "sha256",
            "category": "Payload delivery",
            "value": malicious.get("hash", ""),
            "comment": "Ransomware sample hash",
            "to_ids": True,
        }
    )

for ip in malicious.get("ips", []):
    event_payload["Event"]["Attribute"].append(
        {
            "type": "ip-dst",
            "category": "Network activity",
            "value": ip,
            "comment": "C2 server IP",
            "to_ids": True,
        }
    )

for domain in malicious.get("domains", []):
    event_payload["Event"]["Attribute"].append(
        {
            "type": "domain",
            "category": "Network activity",
            "value": domain,
            "comment": "C2 domain",
            "to_ids": True,
        }
    )

for url in malicious.get("urls", []):
    event_payload["Event"]["Attribute"].append(
        {
            "type": "url",
            "category": "External analysis",
            "value": url,
            "comment": "Malicious URL",
            "to_ids": True,
        }
    )

misp_event_resp = misp_request("POST", "events", json_data=event_payload)
if misp_event_resp is not None and misp_event_resp.ok:
    event_data = misp_event_resp.json()
    if isinstance(event_data, list) and event_data:
        event_data = event_data[0]
    if not isinstance(event_data, dict):
        event_data = {}
    eid = event_data.get("Event", {}).get("id", "?")
    attr_count = len(event_data.get("Event", {}).get("Attribute", []))
    logger.info(f"[OK] MISP event created: ID={eid}  attributes={attr_count}")
else:
    logger.error(
        f"[ERR] Create event: HTTP {getattr(misp_event_resp, 'status_code', 'N/A')}"
        f"  {getattr(misp_event_resp, 'text', '')[:150]}"
    )

misp_attrs_resp = misp_request(
    "POST", "attributes/restSearch", json_data={"returnFormat": "json", "limit": 20}
)
attrs = []
if misp_attrs_resp is not None and misp_attrs_resp.ok:
    try:
        attrs = misp_attrs_resp.json().get("response", {}).get("Attribute", [])
    except Exception:
        attrs = []
logger.info(f"\nTotal attributes in MISP: {len(attrs)}")
for a in attrs[:8]:
    logger.info(f"  [{a.get('type', '?'):12}] {a.get('value', '?')}")

print()
print("=" * 60)
print("SETUP COMPLETE")
print(f"  Cortex : {len(installed_list)} analyzers installed")
print(f"  MISP   : {len(attrs)} IOCs loaded")
print("=" * 60)

if not installed_list:
    logger.warning(
        "[WARN] No Cortex analyzers installed; continuing. The workflow will no longer depend on"
        " Cortex."
    )

if not attrs:
    logger.warning("[WARN] No MISP IOCs loaded; continuing.")
