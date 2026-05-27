#!/usr/bin/env python3
"""
Inicializa Shuffle con un workflow SOAR completo que orquesta:
  1. Webhook  — recibe alertas del simulador SIEM
  2. TheHive  — crea caso de incidente
  3. Cortex   — analiza IOCs (hash, IP) del ransomware
  4. MISP     — busca indicadores en threat intelligence
  5. ES/HTTP  — indexa la alerta en Elasticsearch para Kibana

Uso:
  python src/soar_lab/infrastructure/setup/init_shuffle_webhook.py
  SHUFFLE_URL=http://192.168.56.10:5001 python src/soar_lab/infrastructure/setup/init_shuffle_webhook.py

Variables de entorno (requeridas):
  SHUFFLE_URL      URL de Shuffle
  ES_URL           URL de Elasticsearch
  THEHIVE_URL      URL de TheHive
  CORTEX_URL       URL de Cortex
  MISP_URL         URL de MISP
  SHUFFLE_USER     Usuario de Shuffle
  SHUFFLE_PASS     Contraseña de Shuffle
  SHUFFLE_APIKEY   API key de Shuffle
  THEHIVE_APIKEY   API key de TheHive
  CORTEX_APIKEY    API key de Cortex
  MISP_USER        Usuario de MISP
  MISP_PASS        Contraseña de MISP
"""
import json
import os
import requests
import subprocess
import sys
import time

# Validate required environment variables
required_vars = {
    'SHUFFLE_URL': 'URL de Shuffle',
    'ES_URL': 'URL de Elasticsearch',
    'THEHIVE_URL': 'URL de TheHive',
    'CORTEX_URL': 'URL de Cortex',
    'MISP_URL': 'URL de MISP',
    'SHUFFLE_USER': 'Usuario de Shuffle',
    'SHUFFLE_PASS': 'Contraseña de Shuffle',
    'SHUFFLE_APIKEY': 'API key de Shuffle',
    'THEHIVE_APIKEY': 'API key de TheHive',
    'CORTEX_APIKEY': 'API key de Cortex',
    'MISP_USER': 'Usuario de MISP',
    'MISP_PASS': 'Contraseña de MISP',
}

missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    print(f"[ERROR] Faltan variables de entorno requeridas:")
    for var in missing_vars:
        print(f"  - {var}: {required_vars[var]}")
    sys.exit(1)

SHUFFLE_URL = os.environ['SHUFFLE_URL']
ES_URL = os.environ['ES_URL']
THEHIVE_URL = os.environ['THEHIVE_URL']
CORTEX_URL = os.environ['CORTEX_URL']
MISP_URL = os.environ['MISP_URL']
SHUFFLE_USER = os.environ['SHUFFLE_USER']
SHUFFLE_PASS = os.environ['SHUFFLE_PASS']
SHUFFLE_KEY = os.environ['SHUFFLE_APIKEY']
THEHIVE_KEY = os.environ['THEHIVE_APIKEY']
CORTEX_KEY = os.environ['CORTEX_APIKEY']
MISP_USER = os.environ['MISP_USER']
MISP_PASS = os.environ['MISP_PASS']
WF_NAME = 'SOAR-Ransomware-Response'

print(f"[init_shuffle_webhook] Conectando a {SHUFFLE_URL} ...")


# ── helpers ───────────────────────────────────────────────────────────────────
def pos(x, y):
    return {"x": float(x), "y": float(y)}


def action(aid, name, app_name, app_version, action_name, params, position, environment="Shuffle"):
    return {
        "id": aid,
        "name": name,
        "app_name": app_name,
        "app_version": app_version,
        "action_name": action_name,
        "parameters": params,
        "position": position,
        "environment": environment,
        "is_valid": True,
        "errors": [],
        "authentication": [],
    }


def branch(bid, src, dst):
    return {"id": bid, "source_id": src, "destination_id": dst, "conditions": []}


def param(name, value, variant="STATIC_VALUE"):
    return {"name": name, "value": value, "variant": variant}


# ── 1. Login y verificar usuario ──────────────────────────────────────────────
s = requests.Session()
lr = s.post(f'{SHUFFLE_URL}/api/v1/login',
            json={'username': SHUFFLE_USER, 'password': SHUFFLE_PASS}, timeout=15)
if not lr.ok:
    print(f"  ERROR login: HTTP {lr.status_code}")
    sys.exit(1)
print("  Login OK")

# Asegurar usuario verificado en ES
users_r = requests.get(f'{ES_URL}/users/_search', timeout=10)
for hit in users_r.json().get('hits', {}).get('hits', []):
    u = hit['_source']
    if u.get('username') == SHUFFLE_USER and not u.get('verified', False):
        requests.post(f'{ES_URL}/users/_update/{hit["_id"]}',
                      json={'doc': {'verified': True, 'first_setup': True}}, timeout=10)
        print("  Usuario verificado en ES")

# ── 2. Eliminar workflow anterior si existe ────────────────────────────────────
print(f"  Buscando workflow '{WF_NAME}'...")
wfs_r = s.get(f'{SHUFFLE_URL}/api/v1/workflows', timeout=15)
wfs = wfs_r.json() if isinstance(wfs_r.json(), list) else []
for old in [w for w in wfs if w.get('name') == WF_NAME]:
    s.delete(f'{SHUFFLE_URL}/api/v1/workflows/{old["id"]}', timeout=10)
    print(f"  Eliminado workflow anterior: {old['id']}")

# ── 3. Definir el workflow completo SOAR ──────────────────────────────────────
#
# Flujo:
#   [Webhook] ──> [1. TheHive: crear caso]
#               ──> [2. Cortex: analizar hash]
#               ──> [3. Cortex: analizar IP]
#               ──> [4. MISP: buscar IOC hash]
#               ──> [5. HTTP: indexar en ES]
#
TRIGGER_NODE = "webhook_trigger"

# Nodo 1 — TheHive: crear caso de incidente
ACT_THEHIVE = "act_thehive_create_case"
# Nodo 2 — Cortex: analizar hash del ransomware
ACT_CORTEX_HASH = "act_cortex_hash"
# Nodo 3 — Cortex: analizar IP origen
ACT_CORTEX_IP = "act_cortex_ip"
# Nodo 4 — MISP: buscar hash en threat intelligence
ACT_MISP = "act_misp_search"
# Nodo 5 — HTTP: indexar alerta en Elasticsearch
ACT_ES = "act_es_index"

actions_list = [
    # ── TheHive: crear caso ───────────────────────────────────────────────────
    action(
        aid=ACT_THEHIVE,
        name="TheHive - Crear Caso",
        app_name="TheHive",
        app_version="1.0.0",
        action_name="create_case",
        params=[
            param("url", THEHIVE_URL),
            param("apikey", THEHIVE_KEY),
            param("title", "Ransomware Alert: $exec.alert_id", "EXECUTION_ARGUMENT"),
            param("description",
                  "Host: $exec.hostname | IP: $exec.src_ip | Process: $exec.process_name | "
                  "Hash: $exec.hash | Severity: $exec.severity | MITRE: $exec.mitre_techniques",
                  "EXECUTION_ARGUMENT"),
            param("severity", "$exec.severity", "EXECUTION_ARGUMENT"),
            param("tags", '["ransomware","soar-lab","auto-created"]'),
            param("tlp", "2"),
        ],
        position=pos(400, 0),
    ),
    # ── Cortex: analizar hash ─────────────────────────────────────────────────
    action(
        aid=ACT_CORTEX_HASH,
        name="Cortex - Analizar Hash",
        app_name="Cortex",
        app_version="1.0.0",
        action_name="run_analyzer",
        params=[
            param("url", CORTEX_URL),
            param("apikey", CORTEX_KEY),
            param("analyzer_id", "FileInfo_8_0"),
            param("data_type", "hash"),
            param("data", "$exec.hash", "EXECUTION_ARGUMENT"),
        ],
        position=pos(700, -150),
    ),
    # ── Cortex: analizar IP ───────────────────────────────────────────────────
    action(
        aid=ACT_CORTEX_IP,
        name="Cortex - Analizar IP",
        app_name="Cortex",
        app_version="1.0.0",
        action_name="run_analyzer",
        params=[
            param("url", CORTEX_URL),
            param("apikey", CORTEX_KEY),
            param("analyzer_id", "AbuseIPDB_1_0"),
            param("data_type", "ip"),
            param("data", "$exec.src_ip", "EXECUTION_ARGUMENT"),
        ],
        position=pos(700, 150),
    ),
    # ── MISP: buscar IOC ─────────────────────────────────────────────────────
    action(
        aid=ACT_MISP,
        name="MISP - Buscar IOC",
        app_name="MISP",
        app_version="1.0.0",
        action_name="search_iocs",
        params=[
            param("url", MISP_URL),
            param("apikey", ""),
            param("username", MISP_USER),
            param("password", MISP_PASS),
            param("value", "$exec.hash", "EXECUTION_ARGUMENT"),
            param("type", "md5"),
        ],
        position=pos(1000, -150),
    ),
    # ── HTTP: indexar en Elasticsearch ───────────────────────────────────────
    action(
        aid=ACT_ES,
        name="Elasticsearch - Indexar Alerta",
        app_name="HTTP",
        app_version="1.0.0",
        action_name="post",
        params=[
            param("url", f"{ES_URL}/soar-alerts/_doc"),
            param("headers", '{"Content-Type":"application/json"}'),
            param("body", '$exec', "EXECUTION_ARGUMENT"),
        ],
        position=pos(1000, 150),
    ),
]

branches_list = [
    branch("br_wh_hive", TRIGGER_NODE, ACT_THEHIVE),
    branch("br_wh_cortex_hash", TRIGGER_NODE, ACT_CORTEX_HASH),
    branch("br_wh_cortex_ip", TRIGGER_NODE, ACT_CORTEX_IP),
    branch("br_wh_misp", TRIGGER_NODE, ACT_MISP),
    branch("br_wh_es", TRIGGER_NODE, ACT_ES),
]

wf_def = {
    "name": WF_NAME,
    "description": (
        "Workflow SOAR completo: recibe alerta de ransomware via webhook, "
        "crea caso en TheHive, analiza IOCs en Cortex, busca en MISP, "
        "e indexa en Elasticsearch para visualización en Kibana."
    ),
    "start": TRIGGER_NODE,
    "triggers": [{
        "app_name": "Shuffle Triggers",
        "name": "Webhook",
        "id": TRIGGER_NODE,
        "type": "webhook",
        "status": "running",
        "environment": "Shuffle",
        "position": pos(0, 0),
        "parameters": [param("info", "SIEM ransomware alert intake")],
    }],
    "actions": actions_list,
    "branches": branches_list,
}

# ── 4. Crear workflow ─────────────────────────────────────────────────────────
print(f"  Creando workflow '{WF_NAME}'...")
cr = s.post(f'{SHUFFLE_URL}/api/v1/workflows', json=wf_def, timeout=15)
if not cr.ok:
    print(f"  ERROR crear workflow: HTTP {cr.status_code} {cr.text[:300]}")
    sys.exit(1)
wf = cr.json()
wf_id = wf['id']
print(f"  Workflow creado: {wf_id}")

# Obtener el workflow completo para leer el UUID real del trigger
wf_detail = s.get(f'{SHUFFLE_URL}/api/v1/workflows/{wf_id}', timeout=15).json()
triggers = wf_detail.get('triggers', [])
trigger_id = triggers[0]['id'] if triggers else TRIGGER_NODE
org_id = wf_detail.get('org_id', '')
print(f"  Trigger ID : {trigger_id}")
print(f"  Org ID     : {org_id}")

# Shuffle asigna un UUID nuevo al trigger — actualizar branches con UUID real
for b in wf_detail.get('branches', []):
    if b['source_id'] == TRIGGER_NODE:
        b['source_id'] = trigger_id
r_put = s.put(f'{SHUFFLE_URL}/api/v1/workflows/{wf_id}', json=wf_detail, timeout=15)
print(f"  Branches actualizados: HTTP {r_put.status_code}")

# ── 5. Registrar hook en Elasticsearch ───────────────────────────────────────
print("  Registrando hook en Elasticsearch...")
hooks_r = requests.get(f'{ES_URL}/hooks', timeout=10)
if hooks_r.ok:
    requests.delete(f'{ES_URL}/hooks', timeout=10)

hook_doc = {
    "id": trigger_id,
    "start": wf_id,
    "type": "webhook",
    "owner": "",
    "status": "running",
    "workflows": [wf_id],
    "running": True,
    "org_id": org_id,
    "environment": "Shuffle",
    "info": {},
    "actions": [],
}
hr = requests.put(f'{ES_URL}/hooks/_doc/{trigger_id}', json=hook_doc, timeout=10)
print(f"  Hook en ES: HTTP {hr.status_code}")

# ── 6. Reiniciar shuffle-backend para cargar el hook ─────────────────────────
print("  Reiniciando shuffle-backend...")
for container in ('soar_shuffle_backend', 'shuffle_backend', 'soar-lab_shuffle_backend'):
    res = subprocess.run(['docker', 'restart', container],
                         capture_output=True, text=True, timeout=60)
    if res.returncode == 0:
        print(f"  Reiniciado: {container}")
        break
print("  Esperando 15s...")
time.sleep(15)

# ── 7. Verificar webhook ──────────────────────────────────────────────────────
webhook_url = f'{SHUFFLE_URL}/api/v1/hooks/webhook_{trigger_id}'
test_r = requests.post(webhook_url, json={
    "alert_id": "INIT-TEST-001",
    "hostname": "init-check",
    "src_ip": "127.0.0.1",
    "severity": 1,
    "event_type": "test",
    "description": "Webhook initialization test",
    "process_name": "init",
    "hash": "d41d8cd98f00b204e9800998ecf8427e",
    "mitre_techniques": [],
}, timeout=10)
print(f"  Test webhook: HTTP {test_r.status_code} -> {test_r.text[:100]}")

if test_r.status_code != 200:
    print("  ADVERTENCIA: webhook no respondio 200. Puede requerir reinicio manual.")
    sys.exit(1)

# ── 8. Guardar info ───────────────────────────────────────────────────────────
info_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'artifacts', 'webhook_info.json'
)
os.makedirs(os.path.dirname(info_path), exist_ok=True)
webhook_info = {
    "webhook_url": webhook_url,
    "workflow_id": wf_id,
    "trigger_id": trigger_id,
    "workflow_name": WF_NAME,
    "actions": {
        "thehive": f"{THEHIVE_URL} - crear caso",
        "cortex_hash": f"{CORTEX_URL} - analizar hash",
        "cortex_ip": f"{CORTEX_URL} - analizar IP",
        "misp": f"{MISP_URL} - buscar IOC",
        "elasticsearch": f"{ES_URL}/soar-alerts - indexar alerta",
    },
}
with open(info_path, 'w') as f:
    json.dump(webhook_info, f, indent=2)

print()
print('=' * 60)
print(f'  WEBHOOK ACTIVO : {webhook_url}')
print(f'  Workflow       : {WF_NAME}')
print('  Acciones       :')
print(f'    TheHive  -> crear caso en    {THEHIVE_URL}')
print(f'    Cortex   -> analizar hash+IP {CORTEX_URL}')
print(f'    MISP     -> buscar IOC       {MISP_URL}')
print(f'    ES       -> indexar alertas  {ES_URL}/soar-alerts')
print()
print(f'  Usar con:')
print(f'    make simulate SIMULATE_WEBHOOK="{webhook_url}"')
print(f'  Info guardada en: {info_path}')
print('=' * 60)
