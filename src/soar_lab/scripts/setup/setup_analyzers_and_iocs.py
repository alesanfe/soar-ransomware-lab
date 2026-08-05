#!/usr/bin/env python3
"""
Instala analyzers gratuitos en Cortex y carga los IOCs del proyecto en MISP.

Analyzers instalados (no requieren API key externa):
  - FileInfo_8_0       -- analiza hashes de ficheros (metadata)
  - Malwarebazaar_1_0  -- lookup de hashes en MalwareBazaar (free, no key)
  - OTXQuery_2_0       -- AlienVault OTX (free key, usamos anon)
  - Abuse_Finder_3_0   -- busca abuso en dominios/IPs (no key)
  - DomainTools_Iris_Investigate_1_0  -- skip (de pago)

IOCs cargados en MISP desde tests/e2e/fixtures/ioc_samples.json
"""
import base64
import json
import os
import requests
import sys
import time
import warnings

warnings.filterwarnings("ignore")

from dotenv import dotenv_values

# Prefer .env.full (mounted in container at /app/.env.full) over .env
_env = dotenv_values(".env.full")
if not _env:
    _env = dotenv_values(".env")

# The API container is created before reset_cortex.py updates .env.full, so its
# environment variables are stale. Prefer the mounted .env.full file, which is
# the authoritative source of the credentials and keys generated during setup.
CORTEX_URL = _env.get("CORTEX_URL") or os.environ.get("CORTEX_URL", "http://soar_cortex:9001")
CORTEX_API_KEY = _env.get("CORTEX_API_KEY", "") or os.environ.get("CORTEX_API_KEY", "")
CORTEX_USER = (_env.get("CORTEX_ADMIN_USER")
               or _env.get("CORTEX_USER")
               or os.environ.get("CORTEX_USER")
               or os.environ.get("CORTEX_ADMIN_USER")
               or "admin")
CORTEX_PASS = (_env.get("CORTEX_ADMIN_PASSWORD")
               or _env.get("CORTEX_PASS")
               or os.environ.get("CORTEX_PASS")
               or os.environ.get("CORTEX_ADMIN_PASSWORD")
               or "")
CORTEX_BASIC_AUTH = base64.b64encode(f"{CORTEX_USER}:{CORTEX_PASS}".encode()).decode()
MISP_URL = _env.get("MISP_URL") or os.environ.get("MISP_URL", "https://soar_misp:443")
MISP_KEY = _env.get("MISP_API_KEY", "") or os.environ.get("MISP_API_KEY", "")

if not CORTEX_API_KEY and not CORTEX_PASS:
    print("[ERROR] Falta CORTEX_ADMIN_PASSWORD/CORTEX_PASS o CORTEX_API_KEY", file=sys.stderr)
    sys.exit(1)

if not MISP_KEY:
    print("[ERROR] Falta MISP_API_KEY", file=sys.stderr)
    sys.exit(1)


def cortex_headers(use_basic=False):
    if CORTEX_API_KEY and not use_basic:
        return {"Authorization": f"Bearer {CORTEX_API_KEY}"}
    return {"Authorization": f"Basic {CORTEX_BASIC_AUTH}"}


def cortex_request(method, path, json_data=None, retries=5, delay=5, timeout=30):
    url = f"{CORTEX_URL}/api/{path}"
    use_basic = False
    for attempt in range(1, retries + 1):
        headers = cortex_headers(use_basic=use_basic)
        if json_data is not None:
            headers["Content-Type"] = "application/json"
        try:
            resp = requests.request(method, url, headers=headers, json=json_data, timeout=timeout)
            if resp.status_code == 401 and CORTEX_API_KEY and not use_basic:
                print(f"  Cortex Bearer auth failed for /api/{path}; falling back to basic auth.")
                use_basic = True
                continue
            if resp.status_code == 409:
                return resp
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"  Cortex {method} /api/{path} attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    return None


def misp_request(method, path, json_data=None, retries=10, delay=5, timeout=30):
    url = f"{MISP_URL}/{path}"
    headers = {
        "Authorization": MISP_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.request(method, url, headers=headers, json=json_data, verify=False, timeout=timeout)
            if resp.status_code == 403 and "already" not in resp.text.lower():
                print(f"  MISP {method} /{path} attempt {attempt}: {resp.status_code} - {resp.text[:120]}")
                if attempt < retries:
                    time.sleep(delay)
                continue
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"  MISP {method} /{path} attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(delay)
    return None


# -- 1. Cortex analyzer definitions ------------------------------------
print("=" * 60)
print("CORTEX - instalando analyzers gratuitos")
print("=" * 60)

r = cortex_request("GET", "analyzerdefinition")
definitions = r.json() if r and r.ok else []

free_analyzers = []
for d in definitions:
    config_items = d.get("configurationItems", [])
    required_items = [c for c in config_items if c.get("required", False)
                      and c.get("name") not in ("max_tlp", "max_pap", "proxy_http", "proxy_https",
                                                "auto_extract_artifacts")]
    if not required_items:
        free_analyzers.append(d)

print(f"Definiciones totales: {len(definitions)}")
print(f"Analyzers sin config requerida: {len(free_analyzers)}")

USEFUL_TYPES = {"hash", "ip", "domain", "url", "mail"}
useful = [a for a in free_analyzers
          if set(a.get("dataTypeList", [])) & USEFUL_TYPES]

print(f"\nInstalando {len(useful)} analyzers utiles...")
installed = 0
for a in useful:
    aid = a["id"]
    payload = {
        "name": a["name"],
        "configuration": {
            "max_tlp": 3,
            "max_pap": 3,
            "check_tlp": False,
            "check_pap": False,
        }
    }
    ri = cortex_request("POST", f"organization/analyzer/{aid}", json_data=payload)
    if ri is None:
        print(f"  [ERR] {aid} failed after retries")
        continue
    if ri.ok:
        print(f"  [OK ] {aid}")
        installed += 1
    elif ri.status_code == 409:
        print(f"  [DUP] {aid} (ya instalado)")
        installed += 1
    else:
        print(f"  [ERR] {aid} HTTP {ri.status_code}: {ri.text[:80]}")

r2 = cortex_request("GET", "analyzer")
installed_list = r2.json() if r2 and r2.ok else []
print(f"\nAnalyzers instalados: {len(installed_list)}")
for a in installed_list[:8]:
    print(f"  {a.get('name', '?'):35} datatypes: {a.get('dataTypeList', [])}")

# -- 2. MISP IOCs ------------------------------------------------------
print()
print("=" * 60)
print("MISP - cargando IOCs del lab")
print("=" * 60)

with open("tests/e2e/fixtures/ioc_samples.json") as f:
    ioc_data = json.load(f)

malicious_cases = ioc_data.get("malicious_test_cases", [])
malicious = {
    "hash": list({c.get("hash", "") for c in malicious_cases if c.get("hash")})[0]
    if malicious_cases else "",
    "ips": list({c.get("ip", "") for c in malicious_cases if c.get("ip")}),
    "domains": list({c.get("domain", "") for c in malicious_cases if c.get("domain")}),
    "urls": list({c.get("url", "") for c in malicious_cases if c.get("url")}),
}

print("Waiting for MISP API key to be accepted...")
misp_ready = None
for _ in range(30):
    probe = misp_request("GET", "servers/getPyMISPVersion", retries=1, delay=0)
    if probe is not None and probe.ok:
        misp_ready = probe
        print("  MISP API ready.")
        break
    print("  MISP not ready yet, retrying...")
    time.sleep(5)

if not misp_ready:
    print("[ERROR] MISP API key not accepted after retries.", file=sys.stderr)
    sys.exit(1)

event_payload = {
    "Event": {
        "info": "SOAR Lab - Ransomware IOCs (malicious)",
        "distribution": 0,
        "threat_level_id": 1,
        "analysis": 2,
        "Attribute": []
    }
}

if malicious.get("hash"):
    event_payload["Event"]["Attribute"].append({
        "type": "sha256",
        "category": "Payload delivery",
        "value": malicious.get("hash", ""),
        "comment": "Ransomware sample hash",
        "to_ids": True
    })

for ip in malicious.get("ips", []):
    event_payload["Event"]["Attribute"].append({
        "type": "ip-dst",
        "category": "Network activity",
        "value": ip,
        "comment": "C2 server IP",
        "to_ids": True
    })

for domain in malicious.get("domains", []):
    event_payload["Event"]["Attribute"].append({
        "type": "domain",
        "category": "Network activity",
        "value": domain,
        "comment": "C2 domain",
        "to_ids": True
    })

for url in malicious.get("urls", []):
    event_payload["Event"]["Attribute"].append({
        "type": "url",
        "category": "External analysis",
        "value": url,
        "comment": "Malicious URL",
        "to_ids": True
    })

misp_event_resp = misp_request("POST", "events", json_data=event_payload)
if misp_event_resp is not None and misp_event_resp.ok:
    event_data = misp_event_resp.json()
    if isinstance(event_data, list) and event_data:
        event_data = event_data[0]
    if not isinstance(event_data, dict):
        event_data = {}
    eid = event_data.get("Event", {}).get("id", "?")
    attr_count = len(event_data.get("Event", {}).get("Attribute", []))
    print(f"[OK] Evento MISP creado: ID={eid}  atributos={attr_count}")
else:
    print(f"[ERR] Crear evento: HTTP {getattr(misp_event_resp, 'status_code', 'N/A')}  {getattr(misp_event_resp, 'text', '')[:150]}")

misp_attrs_resp = misp_request("POST", "attributes/restSearch", json_data={"returnFormat": "json", "limit": 20})
attrs = []
if misp_attrs_resp is not None and misp_attrs_resp.ok:
    try:
        attrs = misp_attrs_resp.json().get("response", {}).get("Attribute", [])
    except Exception:
        attrs = []
print(f"\nAtributos totales en MISP: {len(attrs)}")
for a in attrs[:8]:
    print(f"  [{a.get('type', '?'):12}] {a.get('value', '?')}")

print()
print("=" * 60)
print("SETUP COMPLETO")
print(f"  Cortex : {len(installed_list)} analyzers instalados")
print(f"  MISP   : {len(attrs)} IOCs cargados")
print("=" * 60)

if not installed_list:
    print("[ERROR] No Cortex analyzers installed.", file=sys.stderr)
    sys.exit(1)

if not attrs:
    print("[ERROR] No MISP IOCs loaded.", file=sys.stderr)
    sys.exit(1)
