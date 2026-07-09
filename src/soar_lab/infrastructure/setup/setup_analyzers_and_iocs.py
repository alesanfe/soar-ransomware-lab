#!/usr/bin/env python3
"""
Instala analyzers gratuitos en Cortex y carga los IOCs del proyecto en MISP.

Analyzers instalados (no requieren API key externa):
  - FileInfo_8_0       — analiza hashes de ficheros (metadata)
  - Malwarebazaar_1_0  — lookup de hashes en MalwareBazaar (free, no key)
  - OTXQuery_2_0       — AlienVault OTX (free key, usamos anon)
  - Abuse_Finder_3_0   — busca abuso en dominios/IPs (no key)
  - DomainTools_Iris_Investigate_1_0  — skip (de pago)

IOCs cargados en MISP desde tests/fixtures/malicious_iocs.json
"""
import base64
import json
import requests
import time
import warnings

warnings.filterwarnings("ignore")

from dotenv import dotenv_values

v = dotenv_values(".env")

CORTEX_URL = "http://localhost:9001"
MISP_URL = "http://localhost:8083"
CORTEX_AUTH = base64.b64encode(b"admin:J5x#8mP3$vR2@nQ7tW4!zY9&hF1sD6").decode()
MISP_KEY = v.get("MISP_API_KEY", "")

# ── 1. Ver definiciones disponibles sin config requerida ──────────────────────
print("=" * 60)
print("CORTEX — instalando analyzers gratuitos")
print("=" * 60)

r = requests.get(f"{CORTEX_URL}/api/analyzerdefinition",
                 headers={"Authorization": f"Basic {CORTEX_AUTH}"}, timeout=15)
definitions = r.json() if r.ok else []

# Filtrar los que NO tienen items requeridos (required=True) o solo tienen items opcionales
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
for a in free_analyzers[:10]:
    print(f"  - {a['id']:40} datatypes: {a.get('dataTypeList', [])}")

# ── 2. Instalar los analyzers gratuitos utiles ────────────────────────────────
# Seleccionar los mas utiles para el lab (hash, ip, domain)
USEFUL_TYPES = {"hash", "ip", "domain", "url", "mail"}
useful = [a for a in free_analyzers
          if set(a.get("dataTypeList", [])) & USEFUL_TYPES]

print(f"\nInstalando {len(useful)} analyzers utiles...")
installed = 0
for a in useful:
    aid = a["id"]
    base_config = a.get("baseConfig", aid)
    payload = {
        "name": a["name"],
        "configuration": {
            "max_tlp": 3,
            "max_pap": 3,
            "check_tlp": False,
            "check_pap": False,
        }
    }
    ri = requests.post(
        f"{CORTEX_URL}/api/organization/analyzer/{aid}",
        headers={"Authorization": f"Basic {CORTEX_AUTH}",
                 "Content-Type": "application/json"},
        json=payload, timeout=15
    )
    if ri.ok:
        print(f"  [OK ] {aid}")
        installed += 1
    elif ri.status_code == 409:
        print(f"  [DUP] {aid} (ya instalado)")
        installed += 1
    else:
        print(f"  [ERR] {aid} HTTP {ri.status_code}: {ri.text[:80]}")

# Verificar cuantos quedaron instalados
r2 = requests.get(f"{CORTEX_URL}/api/analyzer",
                  headers={"Authorization": f"Basic {CORTEX_AUTH}"}, timeout=15)
installed_list = r2.json() if r2.ok else []
print(f"\nAnalyzers instalados: {len(installed_list)}")
for a in installed_list[:8]:
    print(f"  {a.get('name', '?'):35} datatypes: {a.get('dataTypeList', [])}")

# ── 3. Cargar IOCs en MISP ────────────────────────────────────────────────────
print()
print("=" * 60)
print("MISP — cargando IOCs del lab")
print("=" * 60)

with open("tests/fixtures/malicious_iocs.json") as f:
    ioc_data = json.load(f)

malicious = ioc_data.get("malicious", {})
misp_headers = {
    "Authorization": MISP_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Crear evento MISP para los IOCs maliciosos
event_payload = {
    "Event": {
        "info": "SOAR Lab — Ransomware IOCs (malicious)",
        "distribution": 0,
        "threat_level_id": 1,
        "analysis": 2,
        "Attribute": []
    }
}

# Hash SHA256
event_payload["Event"]["Attribute"].append({
    "type": "sha256",
    "category": "Payload delivery",
    "value": malicious.get("hash", ""),
    "comment": "Ransomware sample hash",
    "to_ids": True
})

# IPs
for ip in malicious.get("ips", []):
    event_payload["Event"]["Attribute"].append({
        "type": "ip-dst",
        "category": "Network activity",
        "value": ip,
        "comment": "C2 server IP",
        "to_ids": True
    })

# Dominios
for domain in malicious.get("domains", []):
    event_payload["Event"]["Attribute"].append({
        "type": "domain",
        "category": "Network activity",
        "value": domain,
        "comment": "C2 domain",
        "to_ids": True
    })

# URLs
for url in malicious.get("urls", []):
    event_payload["Event"]["Attribute"].append({
        "type": "url",
        "category": "External analysis",
        "value": url,
        "comment": "Malicious URL",
        "to_ids": True
    })

re = requests.post(f"{MISP_URL}/events",
                   headers=misp_headers, json=event_payload,
                   verify=False, timeout=30)

if re.ok:
    eid = re.json().get("Event", {}).get("id", "?")
    attr_count = len(re.json().get("Event", {}).get("Attribute", []))
    print(f"[OK] Evento MISP creado: ID={eid}  atributos={attr_count}")
else:
    print(f"[ERR] Crear evento: HTTP {re.status_code}  {re.text[:150]}")

# Verificar
r3 = requests.post(f"{MISP_URL}/attributes/restSearch",
                   headers=misp_headers,
                   json={"returnFormat": "json", "limit": 20},
                   verify=False, timeout=15)
attrs = r3.json().get("response", {}).get("Attribute", []) if r3.ok else []
print(f"\nAtributos totales en MISP: {len(attrs)}")
for a in attrs[:8]:
    print(f"  [{a.get('type', '?'):12}] {a.get('value', '?')}")

print()
print("=" * 60)
print("SETUP COMPLETO")
print(f"  Cortex : {len(installed_list)} analyzers instalados")
print(f"  MISP   : {len(attrs)} IOCs cargados")
print("=" * 60)
