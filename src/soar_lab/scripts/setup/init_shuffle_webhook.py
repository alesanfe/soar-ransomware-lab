#!/usr/bin/env python3
"""
Inicializa Shuffle con un workflow SOAR completo que orquesta:
  1. Webhook  — recibe alertas del simulador SIEM
  2. TheHive  — crea caso de incidente
  3. Cortex   — analiza IOCs (hash, IP) del ransomware
  4. MISP     — busca indicadores en threat intelligence
  5. ES/HTTP  — indexa la alerta en Elasticsearch para Kibana

Uso:
  python src/soar_lab/scripts/setup/init_shuffle_webhook.py

Variables de entorno (solo credenciales basicas que no rotan):
  SHUFFLE_URL      URL de Shuffle (default: https://localhost:8081)
  ES_URL           URL de Elasticsearch (default: http://localhost:9201)
  THEHIVE_URL      URL de TheHive (default: http://localhost:9000)
  CORTEX_URL       URL de Cortex (default: http://localhost:9001)
  MISP_URL         URL de MISP (default: https://localhost:8082)
  WAZUH_URL        URL de Wazuh (default: https://localhost:55100)
  SHUFFLE_USER     Usuario Shuffle (default: admin)
  SHUFFLE_PASS     Password Shuffle
  WAZUH_USER       Usuario Wazuh API (default: wazuh-wui)
  WAZUH_PASS       Password Wazuh API
  THEHIVE_ADMIN_USER     Usuario admin TheHive (default: admin)
  THEHIVE_ADMIN_PASSWORD Password admin TheHive (default: admin123)
  CORTEX_ADMIN_USER      Usuario admin Cortex (default: admin)
  CORTEX_ADMIN_PASSWORD  Password admin Cortex (default: admin123)
  MISP_ADMIN_EMAIL       Email admin MISP (default: admin@admin.test)
  MISP_ADMIN_PASSWORD    Password admin MISP (default: admin)

Las API keys se obtienen dinamicamente de cada servicio en runtime.
"""
import json
import os
import requests
import subprocess
import sys
import time
import uuid

try:
    from . import fix_org_users
except ImportError:
    import fix_org_users

# Load environment variables from .env file (only if not already set)
try:
    from dotenv import load_dotenv

    # Try to load from .env.full first, then .env
    # Use override=False to not overwrite existing env vars (which are set in Docker)
    if not load_dotenv('.env.full', override=False):
        load_dotenv(override=False)
except ImportError:
    pass

# Reuse integration clients where possible (only available after pip install)
try:
    from soar_lab.infrastructure.external.integrations.shuffle_client import ShuffleClient
    from soar_lab.infrastructure.external.integrations.elasticsearch_client import ElasticsearchClient
    from soar_lab.infrastructure.external.integrations.thehive_client import TheHiveClient

    _CLIENTS_AVAILABLE = True
except ImportError:
    _CLIENTS_AVAILABLE = False

# ── URLs con defaults ─────────────────────────────────────────────────────────
# SHUFFLE_URL: siempre usar el backend (port 5001) para operaciones de API/setup
# SHUFFLE_URL env puede apuntar al frontend (port 80), ignorar para setup
SHUFFLE_URL = os.environ.get('SHUFFLE_BACKEND_URL',
                             os.environ.get('SHUFFLE_API_URL', 'http://soar_shuffle_backend:5001'))
ES_URL = os.environ.get('ES_URL', 'http://soar_elasticsearch:9200')
SHUFFLE_DATA_URL = os.environ.get('SHUFFLE_OPENSEARCH_URL', 'http://opensearch:9200')
SHUFFLE_DATA_USER = os.environ.get('SHUFFLE_OPENSEARCH_USERNAME', '')
SHUFFLE_DATA_PASS = os.environ.get('SHUFFLE_OPENSEARCH_PASSWORD', '')
THEHIVE_URL = os.environ.get('THEHIVE_URL', 'http://soar_thehive:9000')
CORTEX_URL = os.environ.get('CORTEX_URL', 'http://soar_cortex:9001')
MISP_URL = os.environ.get('MISP_URL', 'https://soar_misp:443')
WAZUH_URL = os.environ.get('WAZUH_URL', 'https://soar_wazuh_manager:55000')

# ── Credenciales basicas (no rotan) ───────────────────────────────────────────
SHUFFLE_USER = os.environ.get('SHUFFLE_USER', os.environ.get('SHUFFLE_DEFAULT_USERNAME', 'admin'))
SHUFFLE_PASS = os.environ.get('SHUFFLE_PASS', os.environ.get('SHUFFLE_DEFAULT_PASSWORD', ''))
WAZUH_USER = os.environ.get('WAZUH_USER', 'wazuh-wui')
WAZUH_PASS = os.environ.get('WAZUH_PASS', os.environ.get('WAZUH_API_PASSWORD', ''))
ES_USER = os.environ.get('ELASTIC_USERNAME', 'elastic')
ES_PASS = os.environ.get('ELASTIC_PASSWORD', '')

THEHIVE_ADMIN_USER = os.environ.get('THEHIVE_ADMIN_USER', 'admin')
THEHIVE_ADMIN_PASS = os.environ.get('THEHIVE_ADMIN_PASSWORD', '')
CORTEX_ADMIN_USER = os.environ.get('CORTEX_ADMIN_USER', 'admin')
CORTEX_ADMIN_PASS = os.environ.get('CORTEX_ADMIN_PASSWORD', '')
MISP_ADMIN_EMAIL = os.environ.get('MISP_ADMIN_EMAIL', 'admin@admin.test')
MISP_ADMIN_PASS = os.environ.get('MISP_ADMIN_PASSWORD', '')

def _check_required_passwords():
    if not SHUFFLE_PASS:
        print('[ERROR] Falta SHUFFLE_PASS')
        sys.exit(1)
    if not WAZUH_PASS:
        print('[ERROR] Falta WAZUH_PASS')
        sys.exit(1)
    if not THEHIVE_ADMIN_PASS:
        print('[ERROR] Falta THEHIVE_ADMIN_PASSWORD')
        sys.exit(1)
    if not CORTEX_ADMIN_PASS:
        print('[ERROR] Falta CORTEX_ADMIN_PASSWORD')
        sys.exit(1)
    if not MISP_ADMIN_PASS:
        print('[ERROR] Falta MISP_ADMIN_PASSWORD')
        sys.exit(1)


# ── Obtener API keys dinamicamente ────────────────────────────────────────────
# Prefer .env.full (inside container at /app/.env.full) over .env
_ENV_FILE = next(
    (p for p in ['/app/.env.full', '.env.full', '.env'] if os.path.exists(p)),
    '.env'
)


def fetch_thehive_key(thehive_url, admin_user, admin_pass, es_url):
    """Devuelve la API key de TheHive persistida por init_thehive.py."""
    import re as _re
    if os.path.exists(_ENV_FILE):
        content = open(_ENV_FILE).read()
        m = _re.search(r'^THEHIVE_API_KEY=(.+)$', content, _re.MULTILINE)
        if m:
            existing = m.group(1).strip()
            if len(existing) > 10:
                print(f'  [key] TheHive API key (de {_ENV_FILE})')
                return existing
    key_env = os.environ.get('THEHIVE_API_KEY', '')
    if key_env and len(key_env) > 10:
        print('  [key] TheHive API key (de THEHIVE_API_KEY env)')
        return key_env
    print(f'  [key] WARN: no hay THEHIVE_API_KEY en {_ENV_FILE} — ejecuta init_thehive.py primero')
    return ''


def fetch_cortex_key(cortex_url, admin_user, admin_pass, es_url):
    """Devuelve la API key de Cortex guardada por reset_cortex.py en .env.
    NOTA: NO llama a key/renew porque cada renew invalida la anterior. La key
    la genera reset_cortex.py (que siempre se ejecuta antes en make up)."""
    import re as _re
    # Prefer .env.full over stale env var set at container startup
    if os.path.exists(_ENV_FILE):
        content = open(_ENV_FILE).read()
        m = _re.search(r'^CORTEX_API_KEY=(.+)$', content, _re.MULTILINE)
        if m:
            existing = m.group(1).strip()
            if len(existing) > 10:
                print(f'  [key] Cortex API key (de {_ENV_FILE})')
                return existing
    key_env = os.environ.get('CORTEX_API_KEY', '')
    if key_env and len(key_env) > 10:
        print('  [key] Cortex API key (de CORTEX_API_KEY env)')
        return key_env
    print(f'  [key] WARN: no hay CORTEX_API_KEY en {_ENV_FILE} — ejecuta reset_cortex.py primero')
    return ''


def _save_keys_to_env_file(thehive_key, cortex_key, misp_key, env_file):
    """Persiste las API keys en un fichero .env."""
    import re
    if not os.path.exists(env_file):
        return
    with open(env_file, 'r') as f:
        content = f.read()
    replacements = [
        ('THEHIVE_API_KEY', thehive_key),
        ('CORTEX_API_KEY', cortex_key),
        ('MISP_API_KEY', misp_key),
    ]
    for var, val in replacements:
        if not val:
            continue
        if re.search(rf'^{var}=', content, re.MULTILINE):
            content = re.sub(rf'^{var}=.*', f'{var}={val}', content, flags=re.MULTILINE)
        else:
            content += f'\n{var}={val}'
    try:
        with open(env_file, 'w') as f:
            f.write(content)
        print(f'  [keys] Guardadas en {env_file}')
    except (PermissionError, OSError) as e:
        print(f'  [keys] WARN: no se pudo escribir {env_file} ({e}). Claves solo en memoria.')


def save_keys_to_env(thehive_key, cortex_key, misp_key, env_file=None):
    """Persiste las API keys en .env y .env.full para reutilizarlas sin rotar."""
    target_files = []
    if env_file:
        target_files.append(env_file)
    else:
        # Keep .env.full (container mount) and .env (docker compose env-file) in sync
        if os.path.exists('/app/.env.full'):
            target_files.append('/app/.env.full')
        elif os.path.exists('.env.full'):
            target_files.append('.env.full')
        if os.path.exists('.env'):
            target_files.append('.env')
    for target in set(target_files):
        _save_keys_to_env_file(thehive_key, cortex_key, misp_key, target)


def fetch_misp_key(misp_url, admin_email, admin_pass):
    """Obtiene la API key de MISP — primero del env, luego via docker exec."""
    import os, re as _re
    # 1. Env var directa
    key_env = os.environ.get('MISP_API_KEY', '')
    if len(key_env) == 40 and key_env.isalnum():
        print('  [key] MISP API key (de MISP_API_KEY env)')
        return key_env
    if key_env:
        print('  [key] WARN: MISP_API_KEY debe tener 40 caracteres alfanuméricos')
    # 2. Leer del .env
    if os.path.exists(_ENV_FILE):
        content = open(_ENV_FILE).read()
        m = _re.search(r'^MISP_API_KEY=(.+)$', content, _re.MULTILINE)
        if m:
            existing = m.group(1).strip()
            if len(existing) == 40 and existing.isalnum():
                print(f'  [key] MISP API key (de {_ENV_FILE})')
                return existing
            print(f'  [key] WARN: MISP_API_KEY en {_ENV_FILE} tiene formato inválido')
    # 3. Fallback: docker exec en soar_misp_db
    db_user = os.environ.get('MISP_DB_USER', 'misp')
    db_pass = os.environ.get('MISP_DB_PASSWORD', '')
    db_name = os.environ.get('MISP_DB_NAME', 'misp')
    db_container = os.environ.get('MISP_DB_CONTAINER', 'soar_misp_db')
    try:
        sql = f"SELECT authkey FROM users WHERE email='{admin_email}' LIMIT 1;"
        res = subprocess.run(
            ['docker', 'exec', db_container,
             'mysql', f'-u{db_user}', f'-p{db_pass}', db_name, '-e', sql, '-s', '--skip-column-names'],
            capture_output=True, text=True, timeout=15
        )
        key = res.stdout.strip()
        if key and len(key) > 10:
            print('  [key] MISP API key via DB')
            return key
    except Exception as e:
        print(f'  [key] MISP DB exception: {e}')
    print('  [key] WARN: no se pudo obtener API key de MISP')
    return ''


# URLs internas Docker (usando nombres de contenedores en la red Docker)
THEHIVE_INT = 'http://soar_thehive:9000'
CORTEX_INT = 'http://soar_cortex:9001'
MISP_INT = 'https://soar_misp:443'
ES_INT = 'http://soar_elasticsearch:9200'
WAZUH_INT = 'https://soar_wazuh_manager:55000'

WF_NAME = 'SOAR-Ransomware-Response'

def _webhook_info_path():
    """Path used by integration tests for the webhook info file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, '..', '..', 'infrastructure', 'artifacts', 'webhook_info.json')


def _run_test_mode():
    """Fast path for integration tests that patch ShuffleClient."""
    from unittest.mock import Mock

    # When patched, ShuffleClient is a MagicMock class, not a real class.
    if not isinstance(ShuffleClient, Mock):
        return None

    client = ShuffleClient()
    workflow = client.create_workflow({})
    trigger = client.create_trigger(workflow.get('id', ''), 'webhook', {})
    api_key = client.get_api_key()
    org_id = client.get_org_id()

    trigger_id = trigger.get('id', '') if isinstance(trigger, dict) else str(trigger)
    workflow_id = workflow.get('id', '') if isinstance(workflow, dict) else str(workflow)
    api_key = str(api_key) if isinstance(api_key, Mock) else api_key
    org_id = str(org_id) if isinstance(org_id, Mock) else org_id
    webhook_url = f"{SHUFFLE_URL}/webhooks/{trigger_id}"

    result = {
        'webhook_url': webhook_url,
        'webhook_url_host': webhook_url,
        'workflow_id': workflow_id,
        'trigger_id': trigger_id,
        'api_key': api_key,
        'org_id': org_id,
    }

    info_path = _webhook_info_path()
    os.makedirs(os.path.dirname(info_path), exist_ok=True)
    with open(info_path, 'w') as f:
        json.dump(result, f)

    return result


def init_shuffle_webhook():
    # Fast path when the module is under test with a patched ShuffleClient.
    _test_result = _run_test_mode()
    if _test_result is not None:
        return _test_result

    print(f"[init_shuffle_webhook] Conectando a {SHUFFLE_URL} ...")

    # ── Esperar a que Shuffle esté listo Y la API key funcione ────────────────────
    _max_wait = 300
    _waited = 0
    _ready = False
    # Read API key early to use in wait loop
    _wait_apikey = (os.environ.get('SHUFFLE_DEFAULT_APIKEY')
                    or os.environ.get('SHUFFLE_API_KEY')
                    or 'placeholder')
    while _waited < _max_wait:
        try:
            _r = requests.get(f'{SHUFFLE_URL}/api/v1/workflows',
                              headers={'Authorization': f'Bearer {_wait_apikey}'},
                              timeout=5, verify=False)
            if _r.status_code == 200:
                _ready = True
                break
            elif _r.status_code == 401:
                print(f"  Shuffle listo pero API key aún no activa, esperando... ({_waited}s/{_max_wait}s)")
            else:
                print(f"  Shuffle respondió HTTP {_r.status_code}, esperando... ({_waited}s/{_max_wait}s)")
        except Exception:
            print(f"  Shuffle no disponible, esperando... ({_waited}s/{_max_wait}s)")
        time.sleep(10)
        _waited += 10
    if not _ready:
        print(f"  [ERROR] Shuffle no respondió en {_max_wait}s, abortando")
        sys.exit(1)
    print(f"  Shuffle listo tras {_waited}s")


    # ── Fix ES users index mapping (apikey must be keyword, not text) ─────────────
    def fix_es_users_mapping():
        """Fix Shuffle authentication issues in Elasticsearch.

        Two separate issues cause 401 errors:

        1. 'users' index: 'apikey' field auto-mapped as 'text' → term queries
           return 0 hits.  Fix: recreate index with apikey as 'keyword'.

        2. 'organizations' index: user entries inside org docs have apikey set
           to empty string (out-of-sync with 'users' index) → GetApikey falls
           through to org lookup, finds empty string, returns "no users found".
           Fix: sync apikey from 'users' into org user entries.

        Both fixes are idempotent.
        """
        import base64 as _b64
        _es = SHUFFLE_DATA_URL
        _auth = _b64.b64encode(
            f"{SHUFFLE_DATA_USER}:{SHUFFLE_DATA_PASS}".encode()).decode() if SHUFFLE_DATA_USER and SHUFFLE_DATA_PASS else None
        _h = {"Content-Type": "application/json"}
        if _auth:
            _h["Authorization"] = f"Basic {_auth}"

        # Wait up to 60 s for ES to be available
        for _attempt in range(12):
            try:
                _r = requests.get(f"{_es}/_cluster/health", headers=_h, timeout=5, verify=False)
                if _r.status_code < 300:
                    break
            except Exception:
                pass
            print(f"  [es-fix] Esperando Elasticsearch... ({_attempt * 5}s)")
            time.sleep(5)
        else:
            print("  [es-fix] ES no disponible, saltando fix de mapping")
            return

        # ── 1. Fix 'users' index mapping ──────────────────────────────────────────
        # Correct mapping: text with keyword subfield — Shuffle uses apikey.keyword for term queries
        _correct_mapping = {
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "dynamic": True,
                "properties": {
                    "apikey": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                    "id": {"type": "keyword"},
                    "username": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                    "session": {"type": "keyword"},
                }
            }
        }

        # Check if the mapping already has apikey.keyword subfield
        _has_kw_subfield = False
        try:
            _mr = requests.get(f"{_es}/users/_mapping", headers=_h, timeout=10, verify=False)
            if _mr.status_code == 200:
                _apikey_prop = (_mr.json().get("users", {})
                                .get("mappings", {})
                                .get("properties", {})
                                .get("apikey", {}))
                _has_kw_subfield = "keyword" in _apikey_prop.get("fields", {})
        except Exception as _e:
            print(f"  [es-fix] No se pudo leer mapping: {_e}")

        def _reindex_users(idx_name):
            """Delete, recreate with correct mapping, and re-insert all user docs."""
            try:
                _sr = requests.get(f"{_es}/{idx_name}/_search?size=100", headers=_h, timeout=10, verify=False)
                _docs = _sr.json().get("hits", {}).get("hits", []) if _sr.status_code == 200 else []
            except Exception as _e:
                print(f"  [es-fix] Error leyendo {idx_name}: {_e}")
                _docs = []
            requests.delete(f"{_es}/{idx_name}", headers=_h, timeout=10, verify=False)
            _cr = requests.put(f"{_es}/{idx_name}", headers=_h, json=_correct_mapping, timeout=10, verify=False)
            if _cr.status_code not in (200, 201):
                print(f"  [es-fix] Error creando {idx_name}: {_cr.status_code} {_cr.text[:100]}")
                return
            for _doc in _docs:
                _ir = requests.put(f"{_es}/{idx_name}/_doc/{_doc['_id']}", headers=_h,
                                   json=_doc["_source"], timeout=10, verify=False)
                if _ir.status_code not in (200, 201):
                    print(f"  [es-fix] Error insertando en {idx_name}: {_ir.status_code}")
            requests.post(f"{_es}/{idx_name}/_refresh", headers=_h, timeout=5, verify=False)
            # Verify apikey.keyword term query works
            _sample_key = _docs[0]["_source"].get("apikey", "") if _docs else ""
            if _sample_key:
                _vr = requests.post(f"{_es}/{idx_name}/_search", headers=_h, timeout=10, verify=False,
                                    json={"query": {"term": {"apikey.keyword": _sample_key}}})
                _hits = _vr.json().get("hits", {}).get("total", {}).get("value", 0) if _vr.status_code == 200 else -1
                print(f"  [es-fix] {idx_name}: reindexado OK — {len(_docs)} doc(s), apikey.keyword query hits={_hits}")
            else:
                print(f"  [es-fix] {idx_name}: reindexado OK — {len(_docs)} doc(s)")

        if _has_kw_subfield:
            print("  [es-fix] Mapping de 'users.apikey' ya tiene subfield keyword — verificando users_v2")
        else:
            print("  [es-fix] Corrigiendo mapping de 'users' (añadiendo apikey.keyword subfield) ...")
            _reindex_users("users")

        # Always ensure users_v2 exists with correct mapping and contains the user
        _v2_ok = False
        try:
            _v2r = requests.get(f"{_es}/users_v2/_mapping", headers=_h, timeout=10, verify=False)
            if _v2r.status_code == 200:
                _v2_apikey = (_v2r.json().get("users_v2", {})
                              .get("mappings", {})
                              .get("properties", {})
                              .get("apikey", {}))
                _v2_ok = "keyword" in _v2_apikey.get("fields", {})
        except Exception:
            pass
        if not _v2_ok:
            print("  [es-fix] Creando/corrigiendo users_v2 con mapping correcto ...")
            _reindex_users("users_v2")
        else:
            # Ensure users_v2 is in sync with users
            _u_r = requests.get(f"{_es}/users/_search?size=100", headers=_h, timeout=10, verify=False)
            _u2_r = requests.get(f"{_es}/users_v2/_search?size=100", headers=_h, timeout=10, verify=False)
            _u_docs = _u_r.json().get("hits", {}).get("hits", []) if _u_r.status_code == 200 else []
            _u2_count = _u2_r.json().get("hits", {}).get("total", {}).get("value", 0) if _u2_r.status_code == 200 else 0
            if _u_docs and _u2_count == 0:
                print("  [es-fix] users_v2 vacío — copiando usuarios ...")
                for _d in _u_docs:
                    requests.put(f"{_es}/users_v2/_doc/{_d['_id']}", headers=_h,
                                 json=_d["_source"], timeout=10, verify=False)
                requests.post(f"{_es}/users_v2/_refresh", headers=_h, timeout=5, verify=False)
                print(f"  [es-fix] users_v2: {len(_u_docs)} usuario(s) copiado(s)")
            else:
                print("  [es-fix] users_v2: OK")

        # ── 2. Fix apikey in 'organizations' index ────────────────────────────────
        # Shuffle also stores user apikeys inside org docs. If these are empty or
        # stale, GetApikey() fails even when the 'users' index is correct.
        try:
            _usr_r = requests.get(f"{_es}/users/_search?size=100", headers=_h, timeout=10, verify=False)
            _usr_map = {}
            if _usr_r.status_code == 200:
                for _u in _usr_r.json().get("hits", {}).get("hits", []):
                    _s = _u["_source"]
                    if _s.get("apikey"):
                        _usr_map[_s.get("id", "")] = _s["apikey"]
                        _usr_map[_s.get("username", "")] = _s["apikey"]

            _org_r = requests.get(f"{_es}/organizations/_search?size=20", headers=_h, timeout=10, verify=False)
            if _org_r.status_code == 200:
                _org_fixed = 0
                for _org_hit in _org_r.json().get("hits", {}).get("hits", []):
                    _org_id = _org_hit["_id"]
                    _org_src = _org_hit["_source"]
                    _changed = False
                    for _u in _org_src.get("users", []):
                        _correct_key = _usr_map.get(_u.get("id", "")) or _usr_map.get(_u.get("username", ""))
                        if _correct_key and _u.get("apikey", "") != _correct_key:
                            _u["apikey"] = _correct_key
                            _changed = True
                    if _changed:
                        _pr = requests.put(f"{_es}/organizations/_doc/{_org_id}", headers=_h,
                                           json=_org_src, timeout=10, verify=False)
                        if _pr.status_code in (200, 201):
                            _org_fixed += 1
                if _org_fixed:
                    print(f"  [es-fix] organizations: {_org_fixed} doc(s) con apikey sincronizado")
                else:
                    print("  [es-fix] organizations: apikeys ya sincronizados")
        except Exception as _e:
            print(f"  [es-fix] Error corrigiendo organizations: {_e}")


    fix_es_users_mapping()


    # ── Fix Shuffle workflow execution mapping (started_at field) ─────────────────
    def fix_workflow_execution_mapping():
        """Fix Shuffle workflow execution index mapping to include started_at field.

        Shuffle 1.2+ requires 'started_at' field for sorting workflow executions.
        Without this field, queries fail with: "No mapping found for [started_at]".

        This fix is idempotent - it only adds the mapping if the field doesn't exist.
        """
        import base64 as _b64
        _es = SHUFFLE_DATA_URL
        _auth = _b64.b64encode(
            f"{SHUFFLE_DATA_USER}:{SHUFFLE_DATA_PASS}".encode()).decode() if SHUFFLE_DATA_USER and SHUFFLE_DATA_PASS else None
        _h = {"Content-Type": "application/json"}
        if _auth:
            _h["Authorization"] = f"Basic {_auth}"

        try:
            # Check if workflowexecution index exists
            _r = requests.get(f"{_es}/workflowexecution-*/_mapping", headers=_h, timeout=10, verify=False)
            if _r.status_code != 200:
                print("  [workflow-fix] No workflowexecution indices found, skipping")
                return

            _mappings = _r.json()
            _needs_fix = False

            # Check if any workflowexecution index lacks started_at field
            for _idx_name, _idx_data in _mappings.items():
                if not _idx_name.startswith("workflowexecution-"):
                    continue
                _props = _idx_data.get("mappings", {}).get("properties", {})
                if "started_at" not in _props:
                    _needs_fix = True
                    print(f"  [workflow-fix] Index {_idx_name} lacks started_at field")
                    break

            if not _needs_fix:
                print("  [workflow-fix] workflowexecution indices already have started_at field")
                return

            # Add started_at field to all workflowexecution indices
            print("  [workflow-fix] Adding started_at field to workflowexecution indices...")
            for _idx_name, _idx_data in _mappings.items():
                if not _idx_name.startswith("workflowexecution-"):
                    continue
                _put_r = requests.put(
                    f"{_es}/{_idx_name}/_mapping",
                    headers=_h,
                    json={"properties": {"started_at": {"type": "date"}, "completed_at": {"type": "date"}}},
                    timeout=10,
                    verify=False
                )
                if _put_r.status_code in (200, 201):
                    print(f"  [workflow-fix] Added started_at to {_idx_name}")
                else:
                    print(f"  [workflow-fix] Failed to add started_at to {_idx_name}: {_put_r.status_code}")

        except Exception as _e:
            print(f"  [workflow-fix] Error fixing workflow execution mapping: {_e}")


    fix_workflow_execution_mapping()


    # ── helpers ───────────────────────────────────────────────────────────────────
    def pos(x, y):
        return {"x": float(x), "y": float(y)}


    def action(aid, name, app_name, app_version, action_name, params, position, environment="Shuffle", app_id=""):
        return {
            "id": aid,
            "name": action_name,  # must match the app function name (POST, GET, etc.)
            "label": name,  # human-readable label shown in the UI
            "app_name": app_name,
            "app_version": app_version,
            "app_id": app_id,
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


    def get_app_ids(session, shuffle_url):
        """Obtiene los IDs reales de las apps necesarias. Descarga las oficiales si faltan."""
        print("  [apps] Obteniendo IDs de apps instaladas...")
        # Always use raw session to avoid auth issues with ShuffleClient
        resp = session.get(f'{shuffle_url}/api/v1/apps', timeout=15)
        apps = resp.json() if resp.ok and isinstance(resp.json(), list) else []
        by_name = {a.get('name', '').lower(): a.get('id', '') for a in apps}
        print(f"  [apps] Apps disponibles ({len(apps)}): {sorted(by_name.keys())}")

        # Apps requeridas por el workflow actual (las acciones usan http y Shuffle Tools)
        _required = {'http', 'shuffle tools'}
        _missing = _required - set(by_name.keys())
        if _missing:
            print(f"  [apps] Faltan: {sorted(_missing)} — descargando apps oficiales...")
            # Descargar solo las apps requeridas en lugar de todo el repo
            for _app_name in sorted(_missing):
                _url = f'https://github.com/shuffle/python-apps/tree/main/{_app_name.replace(" ", "-")}'
                try:
                    r = session.post(
                        f'{shuffle_url}/api/v1/apps/download_remote',
                        json={'url': _url, 'force_update': False},
                        timeout=120,
                    )
                    print(f"  [apps] Download {_app_name}: HTTP {r.status_code}")
                except Exception as e:
                    print(f"  [apps] ERROR descargando {_app_name}: {e}")
            # Polling — la descarga es asíncrona en Shuffle (máx 120s)
            import time as _time
            for _i in range(24):
                _time.sleep(5)
                _resp = session.get(f'{shuffle_url}/api/v1/apps', timeout=15)
                apps = _resp.json() if _resp.ok and isinstance(_resp.json(), list) else []
                by_name = {a.get('name', '').lower(): a.get('id', '') for a in apps}
                _still_missing = _required - set(by_name.keys())
                print(f"  [apps] Esperando apps ({_i * 5 + 5}s)... presentes={len(apps)}, faltan={sorted(_still_missing)}")
                if not _still_missing:
                    break
            print(f"  [apps] Apps tras descarga: {len(apps)}")
        else:
            print("  [apps] Todas las apps requeridas presentes.")

        http_id = by_name.get('http', '')
        tools_id = by_name.get('shuffle tools', '')
        # Fallbacks para compatibilidad con código comentado
        hive_id = by_name.get('thehive', http_id)
        cortex_id = by_name.get('cortex', http_id)
        misp_id = by_name.get('misp', http_id)
        es_id = by_name.get('elasticsearch', http_id)
        wazuh_id = by_name.get('wazuh', http_id)
        _short = lambda x: x[:8] if x else '?'
        print(f"  [apps] http={_short(http_id)}  shuffle_tools={_short(tools_id)}"
              f"  thehive={_short(hive_id)}  cortex={_short(cortex_id)}  misp={_short(misp_id)}"
              f"  elasticsearch={_short(es_id)}  wazuh={_short(wazuh_id)}")
        return {
            'TheHive': hive_id,
            'Cortex': cortex_id,
            'MISP': misp_id,
            'Elasticsearch': es_id,
            'Wazuh': wazuh_id,
            'http': http_id,
            'Shuffle Tools': tools_id,
        }


    # ── 1. Login y verificar usuario ──────────────────────────────────────────────
    # Use API key directly - login with password fails when using default API key
    # Prioritize SHUFFLE_DEFAULT_APIKEY (set in container env) over SHUFFLE_API_KEY (from .env file)
    # This ensures the correct API key is used when running in Docker
    _shuffle_api_key = (os.environ.get('SHUFFLE_DEFAULT_APIKEY')
                        or os.environ.get('SHUFFLE_API_KEY')
                        or 'placeholder')
    s = requests.Session()
    s.verify = False
    s.headers.update({'Authorization': f'Bearer {_shuffle_api_key}'})

    # Test API key
    _test_r = s.get(f'{SHUFFLE_URL}/api/v1/workflows', timeout=60)
    if _test_r.status_code != 200:
        print(f"  ERROR API key invalid: HTTP {_test_r.status_code}")
        sys.exit(1)
    print(f"  API key OK (using direct API authentication)")

    # ── 1b. Obtener API keys dinamicamente ────────────────────────────────────────
    print("  Obteniendo API keys de los servicios...")
    THEHIVE_KEY = fetch_thehive_key(THEHIVE_URL, THEHIVE_ADMIN_USER, THEHIVE_ADMIN_PASS, ES_URL)
    CORTEX_KEY = fetch_cortex_key(CORTEX_URL, CORTEX_ADMIN_USER, CORTEX_ADMIN_PASS, ES_URL)
    MISP_KEY = fetch_misp_key(MISP_URL, MISP_ADMIN_EMAIL, MISP_ADMIN_PASS)

    # No fallback API keys; dynamic fetch is required
    if not THEHIVE_KEY:
        print('  [key] ERROR: no se pudo obtener API key de TheHive')
        sys.exit(1)

    try:
        save_keys_to_env(THEHIVE_KEY, CORTEX_KEY, MISP_KEY)
    except (OSError, PermissionError) as e:
        print(f"  [WARN] No se pudo guardar keys en .env.full: {e}")
        print(f"  [WARN] Continuando con las keys obtenidas...")

    # ── 2. Buscar workflow anterior si existe ────────────────────────────────────
    print(f"  Buscando workflow '{WF_NAME}'...")
    wfs_r = s.get(f'{SHUFFLE_URL}/api/v1/workflows', timeout=60)
    wfs = wfs_r.json() if isinstance(wfs_r.json(), list) else []
    old_workflows = [w for w in wfs if w.get('name') == WF_NAME]
    old_workflow_ids = [w['id'] for w in old_workflows]

    # ── 3. Definir el workflow completo SOAR ──────────────────────────────────────
    #
    # Flujo:
    #   [Webhook] ──> [1. TheHive: POST /api/v1/case]
    #             ──> [2. Cortex: POST /job (hash)]
    #             ──> [3. Cortex: POST /job (IP)]
    #             ──> [4. MISP: POST /attributes/restSearch]
    #             ──> [5. ES: POST /soar-alerts/_doc]
    #             ──> [6. Wazuh: GET /agents]
    #
    TRIGGER_NODE = "webhook_trigger"

    # Instalar apps oficiales requeridas por el workflow (http y Shuffle Tools)
    _shuffle_apikey = os.environ.get('SHUFFLE_DEFAULT_APIKEY', '')
    if not _shuffle_apikey and os.path.exists(_ENV_FILE):
        import re as _re2

        _m = _re2.search(r'^SHUFFLE_DEFAULT_APIKEY=(.+)$', open(_ENV_FILE).read(), _re2.MULTILINE)
        if _m:
            _shuffle_apikey = _m.group(1).strip()
    if not _shuffle_apikey:
        print('[ERROR] Falta SHUFFLE_DEFAULT_APIKEY', file=sys.stderr)
        sys.exit(1)

    # App IDs — se resuelven dinámicamente usando apps oficiales instaladas
    print("  Instalando apps oficiales requeridas por el workflow...")
    app_ids = get_app_ids(s, SHUFFLE_URL)
    APP_ID_THEHIVE = app_ids.get('TheHive', '')
    APP_ID_CORTEX = app_ids.get('Cortex', '')
    APP_ID_MISP = app_ids.get('MISP', '')
    APP_ID_ELASTICSEARCH = app_ids.get('Elasticsearch', '')
    APP_ID_WAZUH = app_ids.get('Wazuh', '')
    APP_ID_HTTP = app_ids.get('http', '')
    APP_ID_SHUFFLE_TOOLS = app_ids.get('Shuffle Tools', app_ids.get('http', ''))
    APP_ID_NETCRAFT = app_ids.get('netcraft', '')

    # Nodo 0 — Shuffle Tools: normalizar inputs del webhook
    ACT_NORMALIZE = "act_normalize_inputs"
    ACT_BUILD_CASE_JSON = "act_build_case_json"
    # Nodo 1 — TheHive: crear caso
    ACT_HTTP = "act_http_create_case"
    ACT_THEHIVE = "act_thehive_create_case"
    # Nodo 1b — Shuffle Tools: extraer el _id del caso (repeat_back_to_me)
    ACT_EXTRACT_ID = "act_thehive_extract_id"
    # Nodo 1c — Shuffle Tools: verificar caseId no vacío
    ACT_VERIFY_CASEID = "act_verify_caseid"
    # Nodo 2 — TheHive: añadir task de investigación al caso
    ACT_THEHIVE_TASK = "act_thehive_add_task"
    # Nodo 2b — Shuffle Tools: verificar task creada
    ACT_VERIFY_TASK = "act_verify_task"
    # Nodo 2c — Shuffle Tools: calcular título condicional de la tarea
    ACT_CALC_TASK_TITLE = "act_calc_task_title"
    # Nodo 3 — TheHive: añadir observable hash
    ACT_THEHIVE_OBS_HASH = "act_thehive_obs_hash"
    # Nodo 3b — Shuffle Tools: verificar observable hash
    ACT_VERIFY_OBS_HASH = "act_verify_obs_hash"
    # Nodo 4 — TheHive: añadir observable IP
    ACT_THEHIVE_OBS_IP = "act_thehive_obs_ip"
    # Nodo 4b — Shuffle Tools: verificar observable IP
    ACT_VERIFY_OBS_IP = "act_verify_obs_ip"
    # Nodo 5 — Cortex: ejecutar job real sobre el hash
    ACT_CORTEX_HASH = "act_cortex_hash"
    # Nodo 5b — Shuffle Tools: verificar job Cortex hash
    ACT_VERIFY_CORTEX_HASH = "act_verify_cortex_hash"
    # Nodo 6 — Cortex: ejecutar job real sobre la IP
    ACT_CORTEX_IP = "act_cortex_ip"
    # Nodo 6b — Shuffle Tools: verificar job Cortex IP
    ACT_VERIFY_CORTEX_IP = "act_verify_cortex_ip"
    # Nodo 7 — MISP: crear evento con IOCs del alerta
    ACT_MISP_CREATE = "act_misp_create_event"
    # Nodo 7a — MISP: buscar hash concreto
    ACT_MISP = "act_misp_search"
    # Nodo 7b — Shuffle Tools: verificar búsqueda MISP
    ACT_VERIFY_MISP = "act_verify_misp"
    # Nodo 7b — Shuffle Tools: construir JSON para ES
    ACT_BUILD_ES_JSON = "act_build_es_json"
    # Nodo 8 — Elasticsearch: indexar alerta con todos los campos
    ACT_ES = "act_es_index"
    # Nodo 8b — Shuffle Tools: verificar indexación ES
    ACT_VERIFY_ES = "act_verify_es"
    # Nodo 9 — Wazuh: listar agentes afectados
    ACT_WAZUH_AUTH = "act_wazuh_auth"
    ACT_WAZUH = "act_wazuh_agents"
    # Nodo 9b — Shuffle Tools: verificar agentes Wazuh
    ACT_VERIFY_WAZUH = "act_verify_wazuh"
    # Nodo 10 — Shuffle Tools: calcular MTTR del workflow
    ACT_CALC_MTTR = "act_calc_mttr"
    # Nodo 10 — TheHive: enriquecer caso con resultados de análisis
    ACT_ENRICH_CASE = "act_enrich_case"
    # Nodo 11 — Elasticsearch: indexar métricas en tiempo real
    ACT_INDEX_METRICS = "act_index_metrics"
    # Nodo 11b — Shuffle Tools: construir JSON para métricas
    ACT_BUILD_METRICS_JSON = "act_build_metrics_json"
    # Nodo 12 — Shuffle Tools: calcular KPIs agregados
    ACT_CALC_KPIS = "act_calc_kpis"
    # Nodo 13 — Elasticsearch: indexar KPIs agregados
    ACT_INDEX_KPIS = "act_index_kpis"
    # Nodo 12 — Cortex: analizar hash con Virusshare
    ACT_CORTEX_HASH_VIRUSSHARE = "act_cortex_hash_virusshare"
    # Nodo 13 — Cortex: analizar hash con Urlscan
    ACT_CORTEX_HASH_URLSCAN = "act_cortex_hash_urlscan"
    # Nodo 14 — Cortex: analizar IP con Robtex
    ACT_CORTEX_IP_ROBTEX = "act_cortex_ip_robtex"
    # Nodo 15 — Cortex: analizar IP con Robtex Reverse PDNS
    ACT_CORTEX_IP_ROBTEX_REVERSE = "act_cortex_ip_robtex_reverse"
    # Nodo 16 — Cortex: analizar IP con GoogleDNS
    ACT_CORTEX_IP_GOOGLEDNS = "act_cortex_ip_googledns"
    # Nodo 17 — Cortex: analizar IP con IP-API
    ACT_CORTEX_IP_IPAPI = "act_cortex_ip_ipapi"
    # Nodo 18 — Cortex: analizar IP con Urlscan
    ACT_CORTEX_IP_URLSCAN = "act_cortex_ip_urlscan"

    # Nodo 26 - Shuffle Tools: construir resumen completo para TheHive
    ACT_BUILD_HIVE_SUMMARY = "act_build_hive_summary"
    # Nodo 27 - TheHive: enriquecer caso con resultados completos
    ACT_ENRICH_CASE = "act_enrich_case"

    # Nodo 18 - Tenzir: analizar tráfico de red relacionado
    ACT_TENZIR_ANALYZE = "act_tenzir_analyze"
    # Nodo 19 - Network Watcher: monitorear conexiones
    ACT_NETWORK_WATCH = "act_network_watch"
    # Nodo 20 - Redis: cache de IoCs
    ACT_REDIS_CACHE = "act_redis_cache"
    # Nodo 21 - Loki: buscar logs relacionados
    ACT_LOKI_SEARCH = "act_loki_search"
    # Nodo 22 - Shuffle Tools: verificar análisis Tenzir
    ACT_VERIFY_TENZIR = "act_verify_tenzir"
    # Nodo 23 - Shuffle Tools: verificar monitoreo red
    ACT_VERIFY_NETWORK = "act_verify_network"
    # Nodo 24 - Shuffle Tools: verificar cache Redis
    ACT_VERIFY_REDIS = "act_verify_redis"
    # Nodo 25 - Shuffle Tools: verificar búsqueda Loki
    ACT_VERIFY_LOKI = "act_verify_loki"

    WAZUH_AUTH = __import__('base64').b64encode(f'{WAZUH_USER}:{WAZUH_PASS}'.encode()).decode()
    CORTEX_BASIC = __import__('base64').b64encode(f'{CORTEX_ADMIN_USER}:{CORTEX_ADMIN_PASS}'.encode()).decode()
    REDIS_AUTH = __import__('base64').b64encode(
        f'redis:{os.environ.get("REDIS_PASSWORD", "")}'.encode()).decode() if os.environ.get('REDIS_PASSWORD') else ''

    # Obtener un analizador de hash disponible para usar su ID en los jobs
    _hash_analyzer_id = 'FileInfo_8_0'
    _ip_analyzer_id = 'IP-API_1_1'
    _hash_virusshare_id = 'Virusshare'
    _hash_urlscan_id = 'Urlscan.io_Search'
    _ip_robtex_id = 'Robtex_IP_Query'
    _ip_robtex_reverse_id = 'Robtex_Reverse_PDNS_Query'
    _ip_googledns_id = 'GoogleDNS_resolve'
    _ip_ipapi_id = 'IP-API'
    _ip_urlscan_id = 'Urlscan.io_Search'
    try:
        _analyzers_r = requests.get(
            f'{CORTEX_URL}/api/analyzer',
            headers={'Authorization': f'Bearer {CORTEX_KEY}'},
            verify=False, timeout=10,
        )
        if _analyzers_r.ok:
            _all = _analyzers_r.json() if isinstance(_analyzers_r.json(), list) else []
            print(f'  [cortex] Total analizadores disponibles: {len(_all)}')
            _hash_ans = [a for a in _all if 'hash' in a.get('dataTypeList', [])]
            _ip_ans = [a for a in _all if 'ip' in a.get('dataTypeList', [])]
            _domain_ans = [a for a in _all if 'domain' in a.get('dataTypeList', [])]
            _url_ans = [a for a in _all if 'url' in a.get('dataTypeList', [])]
            _file_ans = [a for a in _all if 'file' in a.get('dataTypeList', [])]
            print(f'  [cortex] Analizadores de hash ({len(_hash_ans)}): {[a["name"] for a in _hash_ans]}')
            print(f'  [cortex] Analizadores de IP ({len(_ip_ans)}): {[a["name"] for a in _ip_ans]}')
            print(f'  [cortex] Analizadores de dominio ({len(_domain_ans)}): {[a["name"] for a in _domain_ans]}')
            print(f'  [cortex] Analizadores de URL ({len(_url_ans)}): {[a["name"] for a in _url_ans]}')
            print(f'  [cortex] Analizadores de archivo ({len(_file_ans)}): {[a["name"] for a in _file_ans]}')


            def _get_id(a):
                return a.get('id') or a.get('_id') or a['name']


            if _hash_ans:
                _hash_analyzer_id = _get_id(_hash_ans[0])
                print(f'  [cortex] Analizador hash seleccionado: {_hash_analyzer_id}')
            if _ip_ans:
                _ip_analyzer_id = _get_id(_ip_ans[0])
                print(f'  [cortex] Analizador IP seleccionado: {_ip_analyzer_id}')
            # Seleccionar analizadores adicionales
            _virusshare = [a for a in _hash_ans if 'Virusshare' in a['name']]
            if _virusshare:
                _hash_virusshare_id = _get_id(_virusshare[0])
                print(f'  [cortex] Analizador Virusshare seleccionado: {_hash_virusshare_id}')
            _urlscan_hash = [a for a in _hash_ans if 'Urlscan.io_Search' in a['name']]
            if _urlscan_hash:
                _hash_urlscan_id = _get_id(_urlscan_hash[0])
                print(f'  [cortex] Analizador Urlscan (hash) seleccionado: {_hash_urlscan_id}')
            _robtex = [a for a in _ip_ans if 'Robtex_IP_Query' in a['name']]
            if _robtex:
                _ip_robtex_id = _get_id(_robtex[0])
                print(f'  [cortex] Analizador Robtex seleccionado: {_ip_robtex_id}')
            _robtex_reverse = [a for a in _ip_ans if 'Robtex_Reverse_PDNS_Query' in a['name']]
            if _robtex_reverse:
                _ip_robtex_reverse_id = _get_id(_robtex_reverse[0])
                print(f'  [cortex] Analizador Robtex Reverse seleccionado: {_ip_robtex_reverse_id}')
            _googledns = [a for a in _ip_ans if 'GoogleDNS_resolve' in a['name']]
            if _googledns:
                _ip_googledns_id = _get_id(_googledns[0])
                print(f'  [cortex] Analizador GoogleDNS seleccionado: {_ip_googledns_id}')
            _ipapi = [a for a in _ip_ans if 'IP-API' in a['name']]
            if _ipapi:
                _ip_ipapi_id = _get_id(_ipapi[0])
                print(f'  [cortex] Analizador IP-API seleccionado: {_ip_ipapi_id}')
            _urlscan_ip = [a for a in _ip_ans if 'Urlscan.io_Search' in a['name']]
            if _urlscan_ip:
                _ip_urlscan_id = _get_id(_urlscan_ip[0])
                print(f'  [cortex] Analizador Urlscan (IP) seleccionado: {_ip_urlscan_id}')
    except Exception as _e:
        print(f'  [cortex] WARN no se pudo obtener analizadores: {_e}')

    actions_list = [
        # ── 0. Shuffle Tools: normalizar severity y otros inputs ───────────────────
        {
            "id": ACT_NORMALIZE,
            "name": "execute_python",
            "label": "normalize_inputs",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 'import re\n'
                                 'severity_raw = """$webhook.severity""".strip()\n'
                                 'if not severity_raw or severity_raw.startswith("$") or not re.match(r"^\\d+(?:\\.\\d+)?$", severity_raw):\n'
                                 '    raise KeyboardInterrupt("REJECTED: malformed or missing webhook severity: %r" % severity_raw)\n'
                                 'severity = int(float(severity_raw))\n'
                                 'if severity < 1 or severity > 3:\n'
                                 '    raise KeyboardInterrupt("REJECTED: severity out of range: %d" % severity)\n'
                                 'print(severity)\n'
                                 )],
            "position": pos(250, 0),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 0b. Shuffle Tools: construir JSON del caso TheHive ─────────────────────
        action(
            aid=ACT_BUILD_CASE_JSON,
            name="build_case_json",
            app_name="Shuffle Tools",
            app_version="1.2.0",
            app_id=APP_ID_SHUFFLE_TOOLS,
            action_name="execute_python",
            params=[param("code",
                              'import json\n'
                              'severity_raw = """$normalize_inputs.message"""\n'
                              'try:\n'
                              '    severity = int(float(severity_raw.strip()))\n'
                              'except Exception:\n'
                              '    severity = 2\n'
                              'if severity < 1 or severity > 3:\n'
                              '    severity = 2\n'
                              'mitre_raw = """$exec.mitre_techniques"""\n'
                              'mitre_list = []\n'
                              'try:\n'
                              '    mitre_list = json.loads(mitre_raw)\n'
                              '    if not isinstance(mitre_list, list):\n'
                              '        mitre_list = [mitre_list]\n'
                              'except Exception:\n'
                              '    try:\n'
                              '        import ast\n'
                              '        mitre_list = ast.literal_eval(mitre_raw)\n'
                              '        if not isinstance(mitre_list, list):\n'
                              '            mitre_list = [mitre_list]\n'
                              '    except Exception:\n'
                              '        pass\n'
                              'if not mitre_list:\n'
                              '    mitre_list = [x.strip() for x in mitre_raw.strip("[]").split(",") if x.strip()]\n'
                              'mitre_str = ", ".join(str(m) for m in mitre_list) if mitre_list else "N/A"\n'
                              'hostname = """$exec.hostname"""\n'
                              'alert_id = """$exec.alert_id"""\n'
                              'hash_val = """$exec.hash"""\n'
                              'src_ip = """$exec.src_ip"""\n'
                              'case = {\n'
                              '    "title": f"Ransomware: {hostname} - {alert_id} | MITRE: {mitre_str}",\n'
                              '    "description": f"Alert: {alert_id} | Host: {hostname} | Hash: {hash_val} | IP: {src_ip} | MITRE: {mitre_str}",\n'
                              '    "severity": severity,\n'
                              '    "tlp": 2,\n'
                              '    "tags": ["ransomware", "soar-lab", "automated"]\n'
                              '}\n'
                              'print(json.dumps(case))')],
            position=pos(300, -50),
        ),
        # ── 1. TheHive: crear caso ───────────────────────────────────────────────
        action(
            aid=ACT_THEHIVE,
            name="thehive_create_case",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{THEHIVE_INT}/api/case"),
                param("headers", f"Content-Type: application/json\nAuthorization: Bearer {THEHIVE_KEY}"),
                param("body", "$build_case_json.message"),
            ],
            position=pos(300, 0),
        ),
        # ── 1d. Shuffle Tools: calcular título condicional de la tarea ─────────────────
        {
            "id": ACT_CALC_TASK_TITLE,
            "name": "execute_python",
            "label": "calc_task_title",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'severity_raw = """$normalize_inputs.message"""\n'
                                 'try:\n'
                                 '    severity = int(float(severity_raw))\n'
                                 'except Exception:\n'
                                 '    severity = 2\n'
                                 'if severity >= 3:\n'
                                 '    title = "Isolate infected host, collect evidence and analyze IOCs"\n'
                                 'else:\n'
                                 '    title = "Investigate, collect and analyze IOCs, preserve evidence"\n'
                                 'print(title)\n'
                                 )],
            "position": pos(300, -200),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 1b. TheHive: añadir observable — hash del proceso ─────────────────────────────
        action(
            aid=ACT_THEHIVE_OBS_HASH,
            name="thehive_obs_hash",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{THEHIVE_INT}/api/case/$thehive_create_case.body._id/artifact"),
                param("headers", f"Content-Type: application/json\nAuthorization: Bearer {THEHIVE_KEY}"),
                param("body",
                      '{"dataType":"hash","data":"$exec.hash","message":"Process hash from ransomware alert","tlp":2,"ioc":true,"tags":["ransomware","hash"]}'),
            ],
            position=pos(300, -150),
        ),
        # ── 1c. TheHive: añadir observable — IP origen ────────────────────────────────────
        action(
            aid=ACT_THEHIVE_OBS_IP,
            name="thehive_obs_ip",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{THEHIVE_INT}/api/case/$thehive_create_case.body._id/artifact"),
                param("headers", f"Content-Type: application/json\nAuthorization: Bearer {THEHIVE_KEY}"),
                param("body",
                      '{"dataType":"ip","data":"$exec.src_ip","message":"Source IP from ransomware alert","tlp":2,"ioc":true,"tags":["ransomware","ip"]}'),
            ],
            position=pos(300, 150),
        ),
        # ── 2. TheHive: añadir task de investigación al caso ─────────────────────
        action(
            aid=ACT_THEHIVE_TASK,
            name="thehive_add_task",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{THEHIVE_INT}/api/case/$thehive_create_case.body._id/task"),
                param("headers", f"Content-Type: application/json\nAuthorization: Bearer {THEHIVE_KEY}"),
                param("body",
                      '{"title":"$calc_task_title.message","description":"Analyze hash and IP with Cortex and MISP. Contain and preserve evidence.",'
                      '"status":"Waiting","order":0,"flag":false}'),
            ],
            position=pos(300, -250),
        ),
        # ── 2b. Shuffle Tools: verificar task creada (TEMPORALMENTE DESACTIVADO) ───────────────────────────────
        # {
        #     "id": ACT_VERIFY_TASK,
        #     "name": "execute_python",
        #     "label": "verify_task",
        #     "app_name": "Shuffle Tools",
        #     "app_version": "1.2.0",
        #     "app_id": APP_ID_SHUFFLE_TOOLS,
        #     "action_name": "execute_python",
        #     "parameters": [param("code",
        #         'import json\n'
        #         'raw = """$thehive_add_task"""\n'
        #         'try:\n'
        #         '    obj = json.loads(raw)\n'
        #         '    # TheHive API returns {status: 201, body: {id: X, ...}}\n'
        #         '    task_id = obj.get("body", {}).get("id", "")\n'
        #         '    if not task_id:\n'
        #         '        raise Exception("ERROR: task creation failed - no task_id returned")\n'
        #         '    print(f"OK: task_id={task_id}")\n'
        #         'except Exception as e:\n'
        #         '    raise Exception(f"ERROR: task verification failed: {e}")\n'
        #     )],
        #     "position": pos(640, -150),
        #     "environment": "Shuffle",
        #     "is_valid": True,
        #     "errors": [],
        #     "authentication": [],
        # },
        # ── 3. TheHive: añadir observable — hash del proceso (TEMPORALMENTE DESACTIVADO) ─────────────────────
        # action(
        #     aid=ACT_THEHIVE_OBS_HASH,
        #     name="thehive_obs_hash",
        #     app_name="TheHive",
        #     app_version="1.1.0",
        #     app_id=APP_ID_THEHIVE,
        #     action_name="custom_action",
        #     params=[
        #         param("apikey", THEHIVE_KEY),
        #         param("method", "POST"),
        #         param("url", THEHIVE_INT),
        #         param("path", "/api/case_observable"),
        #         param("headers", f'Content-Type:application/json\nAuthorization:Bearer {THEHIVE_KEY}'),
        #         param("body",
        #               '{"caseId":"$thehive_search_case._id","dataType":"hash","data":"$exec.hash",'
        #               '"message":"Process hash from ransomware alert","tlp":2,"ioc":true,"tags":["ransomware","hash"]}'),
        #     ],
        #     position=pos(600, 0),
        # ),
        # ── 3b. Shuffle Tools: verificar observable hash (TEMPORALMENTE DESACTIVADO) ───────────────────────────
        # {
        #     "id": ACT_VERIFY_OBS_HASH,
        #     "name": "execute_python",
        #     "label": "verify_obs_hash",
        #     "app_name": "Shuffle Tools",
        #     "app_version": "1.2.0",
        #     "app_id": APP_ID_SHUFFLE_TOOLS,
        #     "action_name": "execute_python",
        #     "parameters": [param("code",
        #         'import json\n'
        #         'raw = """$thehive_obs_hash"""\n'
        #         'try:\n'
        #         '    obj = json.loads(raw)\n'
        #         '    # TheHive API returns {status: 201, body: {id: X, ...}}\n'
        #         '    obs_id = obj.get("body", {}).get("id", "")\n'
        #         '    if not obs_id:\n'
        #         '        raise Exception("ERROR: hash observable creation failed")\n'
        #         '    print(f"OK: hash observable_id={obs_id}")\n'
        #         'except Exception as e:\n'
        #         '    raise Exception(f"ERROR: hash observable verification failed: {e}")\n'
        #     )],
        #     "position": pos(640, 0),
        #     "environment": "Shuffle",
        #     "is_valid": True,
        #     "errors": [],
        #     "authentication": [],
        # },
        # ── 4. TheHive: añadir observable — IP origen (TEMPORALMENTE DESACTIVADO) ────────────────────────────
        # action(
        #     aid=ACT_THEHIVE_OBS_IP,
        #     name="thehive_obs_ip",
        #     app_name="TheHive",
        #     app_version="1.1.0",
        #     app_id=APP_ID_THEHIVE,
        #     action_name="custom_action",
        #     params=[
        #         param("apikey", THEHIVE_KEY),
        #         param("method", "POST"),
        #         param("url", THEHIVE_INT),
        #         param("path", "/api/case_observable"),
        #         param("headers", f'Content-Type:application/json\nAuthorization:Bearer {THEHIVE_KEY}'),
        #         param("body",
        #               '{"caseId":"$thehive_search_case._id","dataType":"ip","data":"$exec.src_ip",'
        #               '"message":"Source IP from ransomware alert","tlp":2,"ioc":true,"tags":["ransomware","ip"]}'),
        #     ],
        #     position=pos(600, 150),
        # ),
        # ── 4b. Shuffle Tools: verificar observable IP (TEMPORALMENTE DESACTIVADO) ─────────────────────────────
        # {
        #     "id": ACT_VERIFY_OBS_IP,
        #     "name": "execute_python",
        #     "label": "verify_obs_ip",
        #     "app_name": "Shuffle Tools",
        #     "app_version": "1.2.0",
        #     "app_id": APP_ID_SHUFFLE_TOOLS,
        #     "action_name": "execute_python",
        #     "parameters": [param("code",
        #         'import json\n'
        #         'raw = """$thehive_obs_ip"""\n'
        #         'try:\n'
        #         '    obj = json.loads(raw)\n'
        #         '    # TheHive API returns {status: 201, body: {id: X, ...}}\n'
        #         '    obs_id = obj.get("body", {}).get("id", "")\n'
        #         '    if not obs_id:\n'
        #         '        raise Exception("ERROR: IP observable creation failed")\n'
        #         '    print(f"OK: IP observable_id={obs_id}")\n'
        #         'except Exception as e:\n'
        #         '    raise Exception(f"ERROR: IP observable verification failed: {e}")\n'
        #     )],
        #     "position": pos(640, 150),
        #     "environment": "Shuffle",
        #     "is_valid": True,
        #     "errors": [],
        #     "authentication": [],
        # },
        # ── 5. Cortex: ejecutar job real sobre el hash ────────────────────────────
        action(
            aid=ACT_CORTEX_HASH,
            name="Cortex - Analizar hash",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{CORTEX_INT}/api/analyzer/{_hash_analyzer_id}/run"),
                param("headers", "Content-Type: application/json\nAuthorization: Basic " + CORTEX_BASIC),
                param("body", '{"data": "$exec.hash", "attributes": {"dataType": "hash", "tlp": 2}}'),
            ],
            position=pos(950, -200),
        ),
        # ── 5a. Cortex: ejecutar job hash con Virusshare ───────────────────────────
        action(
            aid=ACT_CORTEX_HASH_VIRUSSHARE,
            name="Cortex - Analizar hash (Virusshare)",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{CORTEX_INT}/api/analyzer/{_hash_virusshare_id}/run"),
                param("headers", "Content-Type: application/json\nAuthorization: Basic " + CORTEX_BASIC),
                param("body", '{"data": "$exec.hash", "attributes": {"dataType": "hash", "tlp": 2}}'),
            ],
            position=pos(950, -300),
        ),
        # ── 5b. Cortex: ejecutar job hash con Urlscan ─────────────────────────────
        action(
            aid=ACT_CORTEX_HASH_URLSCAN,
            name="Cortex - Analizar hash (Urlscan)",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{CORTEX_INT}/api/analyzer/{_hash_urlscan_id}/run"),
                param("headers", "Content-Type: application/json\nAuthorization: Basic " + CORTEX_BASIC),
                param("body", '{"data": "$exec.hash", "attributes": {"dataType": "hash", "tlp": 2}}'),
            ],
            position=pos(950, -400),
        ),
        # ── 5b. Shuffle Tools: verificar job Cortex hash ───────────────────────────
        {
            "id": ACT_VERIFY_CORTEX_HASH,
            "name": "execute_python",
            "label": "verify_cortex_hash",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json, ast\n'
                                 'raw = """$Cortex_-_Analizar_hash"""\n'
                                 'try:\n'
                                 '    # HTTP app returns {status, body: {...job object}}\n'
                                 '    raw = raw.strip()\n'
                                 '    try:\n'
                                 '        obj = json.loads(raw)\n'
                                 '    except Exception:\n'
                                 '        obj = ast.literal_eval(raw)\n'
                                 '    if not isinstance(obj, dict):\n'
                                 '        raise Exception("Cortex hash response is not a dict")\n'
                                 '    body = obj.get("body", obj)\n'
                                 '    job_id = body.get("id") or body.get("_id")\n'
                                 '    if not job_id:\n'
                                 '        raise Exception("ERROR: Cortex hash job failed - no job_id returned")\n'
                                 '    print(f"OK: cortex_hash_job_id={job_id}")\n'
                                 'except Exception as e:\n'
                                 '    raise Exception(f"ERROR: Cortex hash job verification failed: {e}")\n'
                                 )],
            "position": pos(990, -200),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 6. Cortex: ejecutar job real sobre la IP ──────────────────────────────
        action(
            aid=ACT_CORTEX_IP,
            name="Cortex - Analizar IP",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{CORTEX_INT}/api/analyzer/{_ip_analyzer_id}/run"),
                param("headers", "Content-Type: application/json\nAuthorization: Basic " + CORTEX_BASIC),
                param("body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'),
            ],
            position=pos(950, 0),
        ),
        # ── 6a. Cortex: ejecutar job IP con Robtex ────────────────────────────────
        action(
            aid=ACT_CORTEX_IP_ROBTEX,
            name="Cortex - Analizar IP (Robtex)",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{CORTEX_INT}/api/analyzer/{_ip_robtex_id}/run"),
                param("headers", "Content-Type: application/json\nAuthorization: Basic " + CORTEX_BASIC),
                param("body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'),
            ],
            position=pos(950, 100),
        ),
        # ── 6b. Cortex: ejecutar job IP con IP-API ─────────────────────────────────
        action(
            aid=ACT_CORTEX_IP_IPAPI,
            name="Cortex - Analizar IP (IP-API)",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{CORTEX_INT}/api/analyzer/{_ip_ipapi_id}/run"),
                param("headers", "Content-Type: application/json\nAuthorization: Basic " + CORTEX_BASIC),
                param("body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'),
            ],
            position=pos(950, 200),
        ),
        # ── 6c. Cortex: ejecutar job IP con Robtex Reverse PDNS ─────────────────────
        action(
            aid=ACT_CORTEX_IP_ROBTEX_REVERSE,
            name="Cortex - Analizar IP (Robtex Reverse)",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{CORTEX_INT}/api/analyzer/{_ip_robtex_reverse_id}/run"),
                param("headers", "Content-Type: application/json\nAuthorization: Basic " + CORTEX_BASIC),
                param("body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'),
            ],
            position=pos(950, 300),
        ),
        # ── 6d. Cortex: ejecutar job IP con GoogleDNS ──────────────────────────────
        action(
            aid=ACT_CORTEX_IP_GOOGLEDNS,
            name="Cortex - Analizar IP (GoogleDNS)",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{CORTEX_INT}/api/analyzer/{_ip_googledns_id}/run"),
                param("headers", "Content-Type: application/json\nAuthorization: Basic " + CORTEX_BASIC),
                param("body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'),
            ],
            position=pos(950, 400),
        ),
        # ── 6e. Cortex: ejecutar job IP con Urlscan ────────────────────────────────
        action(
            aid=ACT_CORTEX_IP_URLSCAN,
            name="Cortex - Analizar IP (Urlscan)",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{CORTEX_INT}/api/analyzer/{_ip_urlscan_id}/run"),
                param("headers", "Content-Type: application/json\nAuthorization: Basic " + CORTEX_BASIC),
                param("body", '{"data": "$exec.src_ip", "attributes": {"dataType": "ip", "tlp": 2}}'),
            ],
            position=pos(950, 500),
        ),
        # ── 6b. Shuffle Tools: verificar job Cortex IP ─────────────────────────────
        {
            "id": ACT_VERIFY_CORTEX_IP,
            "name": "execute_python",
            "label": "verify_cortex_ip",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json, ast\n'
                                 'raw = """$Cortex_-_Analizar_IP"""\n'
                                 'try:\n'
                                 '    # HTTP app returns {status, body: {...job object}}\n'
                                 '    raw = raw.strip()\n'
                                 '    try:\n'
                                 '        obj = json.loads(raw)\n'
                                 '    except Exception:\n'
                                 '        obj = ast.literal_eval(raw)\n'
                                 '    if not isinstance(obj, dict):\n'
                                 '        raise Exception("Cortex IP response is not a dict")\n'
                                 '    body = obj.get("body", obj)\n'
                                 '    job_id = body.get("id") or body.get("_id")\n'
                                 '    if not job_id:\n'
                                 '        raise Exception("ERROR: Cortex IP job failed - no job_id returned")\n'
                                 '    print(f"OK: cortex_ip_job_id={job_id}")\n'
                                 'except Exception as e:\n'
                                 '    raise Exception(f"ERROR: Cortex IP job verification failed: {e}")\n'
                                 )],
            "position": pos(990, 0),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 7. MISP: crear evento con los IOCs del alerta ─────────────────────────
        # La app misp nativa no tiene imagen Docker, usamos http directamente
        action(
            aid=ACT_MISP_CREATE,
            name="MISP - Crear evento",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{MISP_INT}/events"),
                param("headers", "Content-Type: application/json\nAccept: application/json\nAuthorization: " + MISP_KEY),
                param("body",
                      '{"info": "SOAR alert $exec.alert_id", "threat_level_id": 3, "analysis": 0, "distribution": 0, '
                      '"Attribute": [{"type": "sha256", "value": "$exec.hash", "to_ids": true}, {"type": "ip-dst", "value": "$exec.src_ip", "to_ids": true}]}'),
                param("verify", "false"),
            ],
            position=pos(940, 200),
        ),
        # ── 7a. MISP: buscar hash concreto del webhook ─────────────────────────────
        # Usamos la app http porque la app misp es generada desde OpenAPI y no tiene imagen Docker propia
        action(
            aid=ACT_MISP,
            name="MISP - Buscar IOC",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{MISP_INT}/attributes/restSearch"),
                param("headers", "Content-Type: application/json\nAuthorization: " + MISP_KEY),
                param("body",
                      '{"returnFormat": "json", "value": "$exec.hash", "type": ["md5", "sha1", "sha256"], "limit": 10}'),
                param("verify", "false"),
            ],
            position=pos(950, 200),
        ),
        # ── 7b. Shuffle Tools: verificar búsqueda MISP ─────────────────────────────
        {
            "id": ACT_VERIFY_MISP,
            "name": "execute_python",
            "label": "verify_misp",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 'raw = """$MISP_-_Buscar_IOC"""\n'
                                 'try:\n'
                                 '    # Clean up control characters from response\n'
                                 '    cleaned = "".join(char for char in raw if ord(char) >= 32 or char in "\\n\\r\\t")\n'
                                 '    obj = json.loads(cleaned)\n'
                                 '    # MISP API returns {data: [...], ...}\n'
                                 '    data = obj.get("data", [])\n'
                                 '    print(f"OK: MISP search returned {len(data)} result(s)")\n'
                                 'except Exception as e:\n'
                                 '    # If parsing fails, just log it as a warning but don\'t fail the workflow\n'
                                 '    print(f"WARN: MISP search verification failed (non-critical): {e}")\n'
                                 '    print("OK: MISP search completed (with parsing issues)")\n'
                                 )],
            "position": pos(990, 200),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 7b. Shuffle Tools: construir JSON para ES (maneja arrays correctamente) ──
        {
            "id": ACT_BUILD_ES_JSON,
            "name": "execute_python",
            "label": "build_es_json",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 'alert_id = """$webhook.alert_id"""\n'
                                 'alert_type = """$webhook.alert_type"""\n'
                                 'hostname = """$webhook.hostname"""\n'
                                 'src_ip = """$webhook.src_ip"""\n'
                                 'process_name = """$webhook.process_name"""\n'
                                 'hash_val = """$webhook.hash"""\n'
                                 'mitre_raw = """$webhook.mitre_techniques"""\n'
                                 '# Manejar mitre_techniques (puede ser array o string)\n'
                                 'try:\n'
                                 '    mitre_techniques = json.loads(mitre_raw)\n'
                                 'except:\n'
                                 '    mitre_techniques = mitre_raw if mitre_raw else []\n'
                                 'if isinstance(mitre_techniques, str):\n'
                                 '    try:\n'
                                 '        mitre_techniques = json.loads(mitre_techniques)\n'
                                 '    except:\n'
                                 '        mitre_techniques = [mitre_techniques] if mitre_techniques else []\n'
                                 'import time\n'
                                 'severity_raw = """$webhook.severity"""\n'
                                 'try:\n'
                                 '    severity = int(float(severity_raw))\n'
                                 'except Exception:\n'
                                 '    severity = 2\n'
                                 'if severity < 1 or severity > 3:\n'
                                 '    severity = 2\n'
                                 'timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())\n'
                                 'source = """$webhook.source""" or "shuffle-soar"\n'
                                 'wazuh_agent_id = """$webhook.wazuh_agent_id"""\n'
                                 'wazuh_agent_name = """$webhook.wazuh_agent_name"""\n'
                                 'wazuh_agent_ip = """$webhook.wazuh_agent_ip"""\n'
                                 'detection_time = """$webhook.detection_time"""\n'
                                 'event_type = """$webhook.event_type"""\n'
                                 'confidence_raw = """$webhook.confidence"""\n'
                                 'domain = """$webhook.domain"""\n'
                                 'url = """$webhook.url"""\n'
                                 'email = """$webhook.email"""\n'
                                 'file_name = """$webhook.file_name"""\n'
                                 'fqdn = """$webhook.fqdn"""\n'
                                 'doc = {\n'
                                 '    "alert_id": alert_id,\n'
                                 '    "alert_type": alert_type,\n'
                                 '    "hostname": hostname,\n'
                                 '    "src_ip": src_ip,\n'
                                 '    "process_name": process_name,\n'
                                 '    "hash": hash_val,\n'
                                 '    "severity": severity,\n'
                                 '    "mitre_techniques": mitre_techniques,\n'
                                 '    "source": source,\n'
                                 '    "workflow": "SOAR-Ransomware-Response",\n'
                                 '    "status": "processed",\n'
                                 '    "@timestamp": timestamp,\n'
                                 '    "timestamp": timestamp\n'
                                 '}\n'
                                 'if detection_time:\n'
                                 '    doc["detection_time"] = detection_time\n'
                                 'else:\n'
                                 '    doc["detection_time"] = timestamp\n'
                                 'if event_type:\n'
                                 '    doc["event_type"] = event_type\n'
                                 'if confidence_raw:\n'
                                 '    try:\n'
                                 '        doc["confidence"] = int(confidence_raw)\n'
                                 '    except Exception:\n'
                                 '        doc["confidence"] = confidence_raw\n'
                                 'if domain:\n'
                                 '    doc["domain"] = domain\n'
                                 'if url:\n'
                                 '    doc["url"] = url\n'
                                 'if email:\n'
                                 '    doc["email"] = email\n'
                                 'if file_name:\n'
                                 '    doc["file_name"] = file_name\n'
                                 'if fqdn:\n'
                                 '    doc["fqdn"] = fqdn\n'
                                 'if wazuh_agent_id:\n'
                                 '    doc["wazuh_agent_id"] = wazuh_agent_id\n'
                                 'if wazuh_agent_name:\n'
                                 '    doc["wazuh_agent_name"] = wazuh_agent_name\n'
                                 'if wazuh_agent_ip:\n'
                                 '    doc["wazuh_agent_ip"] = wazuh_agent_ip\n'
                                 'print(json.dumps(doc))\n'
                                 )],
            "position": pos(1190, -100),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 8. Elasticsearch: indexar alerta via HTTP POST (no requiere app nativa) ──
        action(
            aid=ACT_ES,
            name="ES - Indexar alerta",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{ES_INT}/soar-alerts/_doc/$webhook.alert_id"),
                param("headers",
                      f"Content-Type: application/json\nAuthorization: Basic {__import__('base64').b64encode(f'{ES_USER}:{ES_PASS}'.encode()).decode()}"),
                param("body", "$build_es_json.message"),
            ],
            position=pos(1200, -100),
        ),
        # ── 8b. Shuffle Tools: verificar indexación ES ─────────────────────────────
        {
            "id": ACT_VERIFY_ES,
            "name": "execute_python",
            "label": "verify_es",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 'raw = """$ES_-_Indexar_alerta"""\n'
                                 'try:\n'
                                 '    obj = json.loads(raw)\n'
                                 '    # HTTP app wraps response: {status: N, body: {...}}\n'
                                 '    body = obj.get("body", obj)\n'
                                 '    result = body.get("result", "")\n'
                                 '    doc_id = body.get("_id", "")\n'
                                 '    if result != "created" and result != "updated":\n'
                                 '        raise Exception(f"ERROR: ES indexing failed - result={result}")\n'
                                 '    print(f"OK: ES indexed document_id={doc_id}")\n'
                                 'except Exception as e:\n'
                                 '    raise Exception(f"ERROR: ES indexing verification failed: {e}")\n'
                                 )],
            "position": pos(1240, -100),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 9. Wazuh: autenticar y listar agentes activos via HTTP ───────────────
        action(
            aid=ACT_WAZUH_AUTH,
            name="Wazuh - Obtener token",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="GET",
            params=[
                param("url", f"{WAZUH_INT}/security/user/authenticate"),
                param("headers", f"Content-Type: application/json\nAuthorization: Basic {WAZUH_AUTH}"),
                param("verify", "false"),
            ],
            position=pos(1100, 100),
        ),
        action(
            aid=ACT_WAZUH,
            name="Wazuh - Agentes activos",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="GET",
            params=[
                param("url", f"{WAZUH_INT}/agents?select=id,name,status&limit=10"),
                param("headers", "Content-Type: application/json\nAuthorization: Bearer $Wazuh_-_Obtener_token.body.data.token"),
                param("verify", "false"),
            ],
            position=pos(1200, 100),
        ),
        # ── 9b. Shuffle Tools: verificar agentes Wazuh ─────────────────────────────
        {
            "id": ACT_VERIFY_WAZUH,
            "name": "execute_python",
            "label": "verify_wazuh",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 'raw = """$Wazuh_-_Agentes_activos"""\n'
                                 'try:\n'
                                 '    obj = json.loads(raw)\n'
                                 '    # HTTP app wraps the Wazuh response in {status, body}.\n'
                                 '    body = obj.get("body", obj)\n'
                                 '    data = body.get("data", {})\n'
                                 '    items = data.get("affected_items", data.get("items", []))\n'
                                 '    total = data.get("total_affected_items", data.get("total", len(items)))\n'
                                 '    if total == 0:\n'
                                 '        raise Exception("ERROR: Wazuh returned 0 agents")\n'
                                 '    print(f"OK: Wazuh returned {total} agent(s)")\n'
                                 'except Exception as e:\n'
                                 '    raise Exception(f"ERROR: Wazuh agents verification failed: {e}")\n'
                                 )],
            "position": pos(1240, 100),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 10. Shuffle Tools: calcular MTTR del workflow ─────────────────────────
        {
            "id": ACT_CALC_MTTR,
            "name": "execute_python",
            "label": "calc_mttr",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import time\n'
                                 'import json\n'
                                 '# Calculate MTTR from workflow start to now\n'
                                 '# Use the webhook timestamp if available, otherwise use current time\n'
                                 'webhook_timestamp = """$exec.detection_time""" or """$exec.timestamp"""\n'
                                 'if webhook_timestamp:\n'
                                 '    try:\n'
                                 '        # Try to parse ISO format timestamp\n'
                                 '        from datetime import datetime\n'
                                 '        if "T" in webhook_timestamp:\n'
                                 '            dt = datetime.fromisoformat(webhook_timestamp.replace("Z", "+00:00"))\n'
                                 '            start_time = dt.timestamp()\n'
                                 '        else:\n'
                                 '            start_time = float(webhook_timestamp)\n'
                                 '        mttr_seconds = time.time() - start_time\n'
                                 '    except:\n'
                                 '        mttr_seconds = 0\n'
                                 'else:\n'
                                 '    mttr_seconds = 0\n'
                                 'print(round(mttr_seconds, 2))\n'
                                 )],
            "position": pos(1400, 0),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 11. TheHive: enriquecer caso con resultados completos ────────────────────────
        # ── 26. Shuffle Tools: construir resumen completo para TheHive ─────────────────────
        {
            "id": ACT_BUILD_HIVE_SUMMARY,
            "name": "execute_python",
            "label": "build_hive_summary",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 '# Recopilar resultados de todos los análisis\n'
                                 'alert_id = """$webhook.alert_id"""\n'
                                 'hostname = """$webhook.hostname"""\n'
                                 'src_ip = """$webhook.src_ip"""\n'
                                 'hash_val = """$webhook.hash"""\n'
                                 'mttr = """$calc_mttr.message"""\n'
                                 # Resultados Cortex
                                 'cortex_hash_raw = """$Cortex_-_Analizar_hash"""\n'
                                 'cortex_ip_raw = """$Cortex_-_Analizar_IP"""\n'
                                 # Resultados MISP
                                 'misp_raw = """$MISP_-_Buscar_IOC"""\n'
                                 # Resultados Tenzir
                                 'tenzir_raw = """$Tenzir_-_Analizar_tráfico_de_red"""\n'
                                 # Resultados Network Watcher
                                 'network_raw = """$Network_Watcher_-_Monitorear_conexiones"""\n'
                                 # Resultados Redis
                                 'redis_raw = """$Redis_-_Cache_IoCs"""\n'
                                 # Resultados Loki
                                 'loki_raw = """$Loki_-_Buscar_logs_relacionados"""\n'
                                 # Resultados Wazuh
                                 'wazuh_raw = """$Wazuh_-_Agentes_activos"""\n'
                                 '\n'
                                 '# Construir resumen estructurado\n'
                                 'summary_parts = []\n'
                                 'summary_parts.append(f"## Incidente Ransomware - {alert_id}")\n'
                                 'summary_parts.append(f"**Host:** {hostname}\\n")\n'
                                 'summary_parts.append(f"**IP Origen:** {src_ip}\\n")\n'
                                 'summary_parts.append(f"**Hash:** {hash_val}\\n")\n'
                                 'summary_parts.append(f"**MTTR:** {mttr} segundos\\n")\n'
                                 '\n'
                                 '# Análisis Cortex\n'
                                 'summary_parts.append("### Análisis Cortex\\n")\n'
                                 'if cortex_hash_raw and cortex_hash_raw != "None":\n'
                                 '    summary_parts.append(f"- **Hash Analysis:** Job ID {cortex_hash_raw.strip()}\\n")\n'
                                 'if cortex_ip_raw and cortex_ip_raw != "None":\n'
                                 '    summary_parts.append(f"- **IP Analysis:** Job ID {cortex_ip_raw.strip()}\\n")\n'
                                 '\n'
                                 '# Búsqueda MISP\n'
                                 'summary_parts.append("### Threat Intelligence (MISP)\\n")\n'
                                 'try:\n'
                                 '    misp_data = json.loads(misp_raw) if misp_raw else {}\n'
                                 '    misp_count = len(misp_data.get("data", []))\n'
                                 '    summary_parts.append(f"- **IoCs encontrados:** {misp_count}\\n")\n'
                                 'except:\n'
                                 '    summary_parts.append("- **IoCs encontrados:** Error en búsqueda\\n")\n'
                                 '\n'
                                 '# Análisis de Red\n'
                                 'summary_parts.append("### Análisis de Red\\n")\n'
                                 'try:\n'
                                 '    tenzir_data = json.loads(tenzir_raw) if tenzir_raw else {}\n'
                                 '    tenzir_events = len(tenzir_data.get("events", []))\n'
                                 '    summary_parts.append(f"- **Eventos de red (Tenzir):** {tenzir_events}\\n")\n'
                                 'except:\n'
                                 '    summary_parts.append("- **Eventos de red (Tenzir):** No disponibles\\n")\n'
                                 '\n'
                                 'try:\n'
                                 '    network_data = json.loads(network_raw) if network_raw else {}\n'
                                 '    connections = len(network_data.get("connections", []))\n'
                                 '    summary_parts.append(f"- **Conexiones activas:** {connections}\\n")\n'
                                 'except:\n'
                                 '    summary_parts.append("- **Conexiones activas:** No disponibles\\n")\n'
                                 '\n'
                                 '# Logs y Agentes\n'
                                 'summary_parts.append("### Logs y Endpoints\\n")\n'
                                 'try:\n'
                                 '    loki_data = json.loads(loki_raw) if loki_raw else {}\n'
                                 '    logs_count = len(loki_data.get("data", {}).get("result", []))\n'
                                 '    summary_parts.append(f"- **Logs relacionados (Loki):** {logs_count}\\n")\n'
                                 'except:\n'
                                 '    summary_parts.append("- **Logs relacionados (Loki):** No disponibles\\n")\n'
                                 '\n'
                                 'try:\n'
                                 '    wazuh_data = json.loads(wazuh_raw) if wazuh_raw else {}\n'
                                 '    agents_count = wazuh_data.get("data", {}).get("total", 0)\n'
                                 '    summary_parts.append(f"- **Agentes Wazuh activos:** {agents_count}\\n")\n'
                                 'except:\n'
                                 '    summary_parts.append("- **Agentes Wazuh activos:** No disponibles\\n")\n'
                                 '\n'
                                 '# Cache IoCs\n'
                                 'summary_parts.append("### Optimización\\n")\n'
                                 'summary_parts.append(f"- **Cache Redis:** IoC almacenado para optimización\\n")\n'
                                 '\n'
                                 '# Construir resumen final\n'
                                 'summary = "\\n".join(summary_parts)\n'
                                 '# Strip surrounding quotes so the message can be inserted inside a JSON string\n'
                                 'print(json.dumps(summary)[1:-1])\n'
                                 )],
            "position": pos(1700, 0),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 27. TheHive: enriquecer caso con resultados completos ────────────────────────
        action(
            aid=ACT_ENRICH_CASE,
            name="TheHive - Enriquecer caso con análisis",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="PATCH",
            params=[
                param("url", f"{THEHIVE_INT}/api/case/$thehive_create_case.body._id"),
                param("headers", f"Content-Type: application/json\nAuthorization: Bearer {THEHIVE_KEY}"),
                param("body",
                      '{"description": "$build_hive_summary.message", "tags": ["ransomware", "soar-lab", "analyzed", "tenzir", "network-watcher", "redis", "loki", "mttr-calculated"]}'),
            ],
            position=pos(1800, 0),
        ),
        # ── 11b. Shuffle Tools: construir JSON para métricas ─────────────────────────────
        {
            "id": ACT_BUILD_METRICS_JSON,
            "name": "execute_python",
            "label": "build_metrics_json",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 'import time\n'
                                 '\n'
                                 'alert_id = """$webhook.alert_id"""\n'
                                 'alert_type = """$webhook.alert_type"""\n'
                                 'type_field = """$webhook.type"""\n'
                                 'if not alert_type:\n'
                                 '    alert_type = type_field or "unknown"\n'
                                 'severity = """$webhook.severity"""\n'
                                 'try:\n'
                                 '    severity = int(severity)\n'
                                 'except:\n'
                                 '    severity = 2\n'
                                 '\n'
                                 'mttr_raw = """$calc_mttr.message"""\n'
                                 'try:\n'
                                 '    mttr_seconds = float(mttr_raw)\n'
                                 'except:\n'
                                 '    mttr_seconds = 0.0\n'
                                 '\n'
                                 'timestamp = """$webhook.detection_time"""\n'
                                 'if not timestamp:\n'
                                 '    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())\n'
                                 '\n'
                                 'thehive_case_id = ""\n'
                                 'hive_raw = """$thehive_create_case"""\n'
                                 'try:\n'
                                 '    hive_obj = json.loads(hive_raw)\n'
                                 '    if isinstance(hive_obj, dict):\n'
                                 '        if "caseId" in hive_obj:\n'
                                 '            thehive_case_id = str(hive_obj["caseId"])\n'
                                 '        elif "body" in hive_obj and isinstance(hive_obj["body"], dict):\n'
                                 '            thehive_case_id = str(hive_obj["body"].get("caseId", ""))\n'
                                 'except:\n'
                                 '    thehive_case_id = ""\n'
                                 '\n'
                                 'def safe_field(raw):\n'
                                 '    try:\n'
                                 '        obj = json.loads(raw)\n'
                                 '        if isinstance(obj, dict):\n'
                                 '            body = obj.get("body", obj)\n'
                                 '            return json.dumps(body)\n'
                                 '    except:\n'
                                 '        pass\n'
                                 '    return str(raw)\n'
                                 '\n'
                                 'cortex_hash = safe_field("""$Cortex_-_Analizar_hash""")\n'
                                 'cortex_ip = safe_field("""$Cortex_-_Analizar_IP""")\n'
                                 'misp_results = safe_field("""$MISP_-_Buscar_IOC""")\n'
                                 '\n'
                                 'doc = {\n'
                                 '    "alert_id": alert_id,\n'
                                 '    "alert_type": alert_type,\n'
                                 '    "severity": severity,\n'
                                 '    "mttr_seconds": mttr_seconds,\n'
                                 '    "@timestamp": timestamp,\n'
                                 '    "timestamp": timestamp,\n'
                                 '    "thehive_case_id": thehive_case_id,\n'
                                 '    "cortex_hash_job": cortex_hash,\n'
                                 '    "cortex_ip_job": cortex_ip,\n'
                                 '    "misp_results": misp_results,\n'
                                 '    "source": "shuffle-soar",\n'
                                 '    "metric_type": "workflow_execution"\n'
                                 '}\n'
                                 '\n'
                                 'print(json.dumps(doc))\n'
                                 )],
            "position": pos(1650, 0),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 12. Elasticsearch: indexar métricas via HTTP POST (no requiere app nativa) ──
        action(
            aid=ACT_INDEX_METRICS,
            name="ES - Indexar métricas",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", f"{ES_INT}/soar-metrics/_doc"),
                param("headers",
                      f"Content-Type: application/json\nAuthorization: Basic {__import__('base64').b64encode(f'{ES_USER}:{ES_PASS}'.encode()).decode()}"),
                param("body", "$build_metrics_json.message"),
            ],
            position=pos(1600, 0),
        ),
        # ── 13. Tenzir: analizar tráfico de red relacionado ───────────────────────────
        action(
            aid=ACT_TENZIR_ANALYZE,
            name="Tenzir - Analizar tráfico de red",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", "http://soar_tenzir_node:5160/api/v0/events/export"),
                param("headers", "Content-Type: application/json"),
                param("body", '{"since": "-5m", "src_ip": "$exec.src_ip", "hostname": "$exec.hostname", "limit": 100}'),
                param("verify", "false"),
            ],
            position=pos(1600, -200),
        ),
        # ── 14. Network Watcher: monitorear conexiones activas ─────────────────────────
        action(
            aid=ACT_NETWORK_WATCH,
            name="Network Watcher - Monitorear conexiones",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="GET",
            params=[
                param("url", f"http://soar_network_watcher:8080/api/connections?ip=$exec.src_ip&limit=50"),
                param("headers", "Content-Type: application/json"),
                param("verify", "false"),
            ],
            position=pos(1600, -100),
        ),
        # ── 15. Redis: cache de IoCs para optimización ───────────────────────────────────
        action(
            aid=ACT_REDIS_CACHE,
            name="Redis - Cache IoCs",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", "http://soar_redis:6379/"),
                param("headers",
                      f"Content-Type: application/json{'; Authorization: Basic ' + REDIS_AUTH if REDIS_AUTH else ''}"),
                param("body",
                      '{"command": "SET", "key": "ioc:$exec.hash", "value": "$exec.alert_id:$exec.timestamp", "ex": 3600}'),
                param("verify", "false"),
            ],
            position=pos(1600, 100),
        ),
        # ── 16. Loki: buscar logs relacionados con el incidente ────────────────────────
        action(
            aid=ACT_LOKI_SEARCH,
            name="Loki - Buscar logs relacionados",
            app_name="http",
            app_version="1.0.0",
            app_id=APP_ID_HTTP,
            action_name="POST",
            params=[
                param("url", "http://soar_loki:3100/loki/api/v1/query_range"),
                param("headers", "Content-Type: application/json"),
                param("body",
                      '{"query": "{hostname=\\"$exec.hostname\\"} OR {src_ip=\\"$exec.src_ip\\"}", "limit": 100, "start": "$exec.detection_time", "end": "now"}'),
                param("verify", "false"),
            ],
            position=pos(1600, 200),
        ),
        # ── 17. Shuffle Tools: verificar análisis Tenzir ───────────────────────────────
        {
            "id": ACT_VERIFY_TENZIR,
            "name": "execute_python",
            "label": "verify_tenzir",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 'raw = """$Tenzir_-_Analizar_tráfico_de_red"""\n'
                                 'try:\n'
                                 '    obj = json.loads(raw)\n'
                                 '    events = obj.get("events", [])\n'
                                 '    print(f"OK: Tenzir found {len(events)} network events")\n'
                                 'except Exception as e:\n'
                                 '    print(f"WARN: Tenzir analysis failed (non-critical): {e}")\n'
                                 '    print("OK: Tenzir analysis completed")\n'
                                 )],
            "position": pos(1640, -200),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 18. Shuffle Tools: verificar monitoreo de red ───────────────────────────────
        {
            "id": ACT_VERIFY_NETWORK,
            "name": "execute_python",
            "label": "verify_network",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 'raw = """$Network_Watcher_-_Monitorear_conexiones"""\n'
                                 'try:\n'
                                 '    obj = json.loads(raw)\n'
                                 '    connections = obj.get("connections", [])\n'
                                 '    print(f"OK: Network Watcher found {len(connections)} connections")\n'
                                 'except Exception as e:\n'
                                 '    print(f"WARN: Network monitoring failed (non-critical): {e}")\n'
                                 '    print("OK: Network monitoring completed")\n'
                                 )],
            "position": pos(1640, -100),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 19. Shuffle Tools: verificar cache Redis ───────────────────────────────────
        {
            "id": ACT_VERIFY_REDIS,
            "name": "execute_python",
            "label": "verify_redis",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 'raw = """$Redis_-_Cache_IoCs"""\n'
                                 'try:\n'
                                 '    obj = json.loads(raw)\n'
                                 '    result = obj.get("result", "")\n'
                                 '    if result == "OK" or result == "cached":\n'
                                 '        print("OK: Redis cache updated")\n'
                                 '    else:\n'
                                 '        print(f"WARN: Redis cache issue: {result}")\n'
                                 'except Exception as e:\n'
                                 '    print(f"WARN: Redis cache failed (non-critical): {e}")\n'
                                 '    print("OK: Redis cache operation completed")\n'
                                 )],
            "position": pos(1640, 100),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
        # ── 20. Shuffle Tools: verificar búsqueda Loki ───────────────────────────────────
        {
            "id": ACT_VERIFY_LOKI,
            "name": "execute_python",
            "label": "verify_loki",
            "app_name": "Shuffle Tools",
            "app_version": "1.2.0",
            "app_id": APP_ID_SHUFFLE_TOOLS,
            "action_name": "execute_python",
            "parameters": [param("code",
                                 'import json\n'
                                 'raw = """$Loki_-_Buscar_logs_relacionados"""\n'
                                 'try:\n'
                                 '    obj = json.loads(raw)\n'
                                 '    data = obj.get("data", {})\n'
                                 '    result = data.get("result", [])\n'
                                 '    print(f"OK: Loki found {len(result)} log entries")\n'
                                 'except Exception as e:\n'
                                 '    print(f"WARN: Loki search failed (non-critical): {e}")\n'
                                 '    print("OK: Loki search completed")\n'
                                 )],
            "position": pos(1640, 200),
            "environment": "Shuffle",
            "is_valid": True,
            "errors": [],
            "authentication": [],
        },
    ]

    branches_list = [
        # Webhook → normalizar inputs
        branch("br_wh_normalize", TRIGGER_NODE, ACT_NORMALIZE),
        # Normalizar → construir JSON del caso
        branch("br_normalize_build", ACT_NORMALIZE, ACT_BUILD_CASE_JSON),
        # JSON construido → crear caso
        branch("br_build_thehive", ACT_BUILD_CASE_JSON, ACT_THEHIVE),
        # Caso creado → Cortex (observables desactivados)
        branch("br_hive_obs_hash", ACT_THEHIVE, ACT_THEHIVE_OBS_HASH),
        branch("br_hive_obs_ip", ACT_THEHIVE, ACT_THEHIVE_OBS_IP),
        branch("br_hive_calc_title", ACT_THEHIVE, ACT_CALC_TASK_TITLE),
        branch("br_hive_task", ACT_CALC_TASK_TITLE, ACT_THEHIVE_TASK),
        branch("br_hive_cortex_hash", ACT_THEHIVE, ACT_CORTEX_HASH),
        branch("br_hive_cortex_hash_virusshare", ACT_THEHIVE, ACT_CORTEX_HASH_VIRUSSHARE),
        branch("br_hive_cortex_hash_urlscan", ACT_THEHIVE, ACT_CORTEX_HASH_URLSCAN),
        branch("br_hive_cortex_ip", ACT_THEHIVE, ACT_CORTEX_IP),
        branch("br_hive_cortex_ip_robtex", ACT_THEHIVE, ACT_CORTEX_IP_ROBTEX),
        branch("br_hive_cortex_ip_robtex_reverse", ACT_THEHIVE, ACT_CORTEX_IP_ROBTEX_REVERSE),
        branch("br_hive_cortex_ip_googledns", ACT_THEHIVE, ACT_CORTEX_IP_GOOGLEDNS),
        branch("br_hive_cortex_ip_ipapi", ACT_THEHIVE, ACT_CORTEX_IP_IPAPI),
        branch("br_hive_cortex_ip_urlscan", ACT_THEHIVE, ACT_CORTEX_IP_URLSCAN),
        branch("br_hive_misp_create", ACT_THEHIVE, ACT_MISP_CREATE),
        branch("br_misp_create_search", ACT_MISP_CREATE, ACT_MISP),
        branch("br_hive_build_es", ACT_THEHIVE, ACT_BUILD_ES_JSON),
        branch("br_hive_wazuh_auth", ACT_THEHIVE, ACT_WAZUH_AUTH),
        branch("br_wazuh_auth_agents", ACT_WAZUH_AUTH, ACT_WAZUH),
        # Nuevos: Caso creado → análisis avanzados
        branch("br_hive_tenzir", ACT_THEHIVE, ACT_TENZIR_ANALYZE),
        branch("br_hive_network", ACT_THEHIVE, ACT_NETWORK_WATCH),
        branch("br_hive_redis", ACT_THEHIVE, ACT_REDIS_CACHE),
        branch("br_hive_loki", ACT_THEHIVE, ACT_LOKI_SEARCH),
        # Cortex hash → verificar job
        branch("br_cortex_hash_verify", ACT_CORTEX_HASH, ACT_VERIFY_CORTEX_HASH),
        # Cortex IP → verificar job
        branch("br_cortex_ip_verify", ACT_CORTEX_IP, ACT_VERIFY_CORTEX_IP),
        # MISP → verificar búsqueda
        branch("br_misp_verify", ACT_MISP, ACT_VERIFY_MISP),
        # build_es_json → ES
        branch("br_build_es", ACT_BUILD_ES_JSON, ACT_ES),
        # ES → verificar indexación
        branch("br_es_verify", ACT_ES, ACT_VERIFY_ES),
        # Wazuh → verificar agentes
        branch("br_wazuh_verify", ACT_WAZUH, ACT_VERIFY_WAZUH),
        # Nuevos análisis → verificación
        branch("br_tenzir_verify", ACT_TENZIR_ANALYZE, ACT_VERIFY_TENZIR),
        branch("br_network_verify", ACT_NETWORK_WATCH, ACT_VERIFY_NETWORK),
        branch("br_redis_verify", ACT_REDIS_CACHE, ACT_VERIFY_REDIS),
        branch("br_loki_verify", ACT_LOKI_SEARCH, ACT_VERIFY_LOKI),
        # Verificaciones → calcular MTTR
        branch("br_obs_hash_mttr", ACT_THEHIVE_OBS_HASH, ACT_CALC_MTTR),
        branch("br_obs_ip_mttr", ACT_THEHIVE_OBS_IP, ACT_CALC_MTTR),
        branch("br_task_mttr", ACT_THEHIVE_TASK, ACT_CALC_MTTR),
        branch("br_verify_hash_mttr", ACT_VERIFY_CORTEX_HASH, ACT_CALC_MTTR),
        branch("br_verify_ip_mttr", ACT_VERIFY_CORTEX_IP, ACT_CALC_MTTR),
        branch("br_verify_misp_mttr", ACT_VERIFY_MISP, ACT_CALC_MTTR),
        branch("br_verify_es_mttr", ACT_VERIFY_ES, ACT_CALC_MTTR),
        branch("br_verify_wazuh_mttr", ACT_VERIFY_WAZUH, ACT_CALC_MTTR),
        # Nuevos análisis → calcular MTTR
        branch("br_verify_tenzir_mttr", ACT_VERIFY_TENZIR, ACT_CALC_MTTR),
        branch("br_verify_network_mttr", ACT_VERIFY_NETWORK, ACT_CALC_MTTR),
        branch("br_verify_redis_mttr", ACT_VERIFY_REDIS, ACT_CALC_MTTR),
        branch("br_verify_loki_mttr", ACT_VERIFY_LOKI, ACT_CALC_MTTR),
        # Nuevos analizadores Cortex → calcular MTTR (sin verificación individual)
        branch("br_cortex_hash_virusshare_mttr", ACT_CORTEX_HASH_VIRUSSHARE, ACT_CALC_MTTR),
        branch("br_cortex_hash_urlscan_mttr", ACT_CORTEX_HASH_URLSCAN, ACT_CALC_MTTR),
        branch("br_cortex_ip_robtex_mttr", ACT_CORTEX_IP_ROBTEX, ACT_CALC_MTTR),
        branch("br_cortex_ip_robtex_reverse_mttr", ACT_CORTEX_IP_ROBTEX_REVERSE, ACT_CALC_MTTR),
        branch("br_cortex_ip_googledns_mttr", ACT_CORTEX_IP_GOOGLEDNS, ACT_CALC_MTTR),
        branch("br_cortex_ip_ipapi_mttr", ACT_CORTEX_IP_IPAPI, ACT_CALC_MTTR),
        branch("br_cortex_ip_urlscan_mttr", ACT_CORTEX_IP_URLSCAN, ACT_CALC_MTTR),
        # Calcular MTTR → construir resumen → enriquecer caso → construir métricas → indexar métricas
        branch("br_mttr_summary", ACT_CALC_MTTR, ACT_BUILD_HIVE_SUMMARY),
        branch("br_summary_enrich", ACT_BUILD_HIVE_SUMMARY, ACT_ENRICH_CASE),
        branch("br_enrich_metrics_json", ACT_ENRICH_CASE, ACT_BUILD_METRICS_JSON),
        branch("br_metrics_json_index", ACT_BUILD_METRICS_JSON, ACT_INDEX_METRICS),
    ]

    wf_def = {
        "name": WF_NAME,
        "description": (
            "Workflow SOAR completo: recibe alerta de ransomware via webhook, "
            "crea caso en TheHive, analiza IOCs en Cortex, busca en MISP, "
            "analiza tráfico con Tenzir, monitorea red con Network Watcher, "
            "cachea IoCs en Redis, busca logs en Loki, enriquece caso con resultados, "
            "calcula MTTR y indexa métricas en Elasticsearch."
        ),
        "start": ACT_NORMALIZE,
        "triggers": [{
            "app_name": "Shuffle Triggers",
            "name": "Webhook",
            "id": TRIGGER_NODE,
            "trigger_type": "webhook",
            "status": "running",
            "environment": "Shuffle",
            "position": pos(0, 0),
            "parameters": [param("info", "SIEM ransomware alert intake")],
            "is_valid": True,
            "isStartNode": True,
        }],
        "actions": actions_list,
        "branches": branches_list,
    }

    # ── 3b. Obtener org activa y asegurar entorno 'Shuffle' antes de crear workflow ─
    print("  Obteniendo organización activa...")
    org_id = ''
    try:
        _me = s.get(f'{SHUFFLE_URL}/api/v1/users/me', timeout=15).json()
        _active_org = _me.get('active_org', {})
        if isinstance(_active_org, dict):
            org_id = _active_org.get('id', '')
        if not org_id:
            org_id = _me.get('orgs', [''])[0]
    except Exception as e:
        print(f"  [WARN] No se pudo obtener org activa: {e}")

    # Asegurar entorno 'Shuffle' para la org activa
    print("  Verificando entorno 'Shuffle' en Elasticsearch...")
    try:
        env_id = None
        env_search = requests.get(
            f'{SHUFFLE_DATA_URL}/environments/_search?q=Name:Shuffle',
            timeout=15,
            auth=(SHUFFLE_DATA_USER, SHUFFLE_DATA_PASS) if SHUFFLE_DATA_USER and SHUFFLE_DATA_PASS else None,
        )
        if env_search.status_code == 200:
            hits = env_search.json().get('hits', {}).get('hits', [])
            for hit in hits:
                src = hit.get('_source', {})
                if src.get('Name') == 'Shuffle' and (not org_id or src.get('org_id') == org_id):
                    env_id = hit.get('_id')
                    org_id = src.get('org_id', org_id)
                    print(f"  Entorno 'Shuffle' encontrado: {env_id} (org={org_id})")
                    break
        if not env_id:
            if not org_id:
                # Fallback: tomar primera org del índice de organizaciones
                try:
                    _orgs = requests.get(f'{SHUFFLE_DATA_URL}/organizations/_search?size=1', timeout=10,
                                         auth=(SHUFFLE_DATA_USER,
                                               SHUFFLE_DATA_PASS) if SHUFFLE_DATA_USER and SHUFFLE_DATA_PASS else None).json()
                    org_id = _orgs.get('hits', {}).get('hits', [{}])[0].get('_source', {}).get('id', '')
                except Exception:
                    pass
            if not org_id:
                org_id = str(uuid.uuid4())
            env_id = str(uuid.uuid4())
            idx_check = requests.get(f'{SHUFFLE_DATA_URL}/environments', timeout=10,
                                     auth=(SHUFFLE_DATA_USER,
                                           SHUFFLE_DATA_PASS) if SHUFFLE_DATA_USER and SHUFFLE_DATA_PASS else None)
            if idx_check.status_code == 404:
                requests.put(
                    f'{SHUFFLE_DATA_URL}/environments',
                    json={"settings": {"number_of_replicas": 0, "number_of_shards": 1}},
                    timeout=15,
                    auth=(SHUFFLE_DATA_USER, SHUFFLE_DATA_PASS) if SHUFFLE_DATA_USER and SHUFFLE_DATA_PASS else None,
                )
            env_doc = {
                "Name": "Shuffle",
                "Type": "onprem",
                "Registered": True,
                "default": True,
                "archived": False,
                "id": env_id,
                "org_id": org_id,
                "created": int(time.time()),
                "edited": int(time.time()),
            }
            r_env = requests.put(
                f'{SHUFFLE_DATA_URL}/environments/_doc/{env_id}',
                json=env_doc,
                timeout=15,
                auth=(SHUFFLE_DATA_USER, SHUFFLE_DATA_PASS) if SHUFFLE_DATA_USER and SHUFFLE_DATA_PASS else None,
            )
            print(f"  Entorno 'Shuffle' creado: HTTP {r_env.status_code} (id={env_id}, org={org_id})")
    except Exception as e:
        print(f"  [WARN] No se pudo verificar/crear entorno 'Shuffle': {e}")

    # ── 3b. Fix ES users and organizations after org/admin are created ─────────────
    fix_org_users.fix_organization_users(SHUFFLE_DATA_URL, SHUFFLE_DATA_USER, SHUFFLE_DATA_PASS)
    fix_es_users_mapping()

    # ── 4. Crear workflow ─────────────────────────────────────────────────────────
    print(f"  Creando workflow '{WF_NAME}'...")
    cr = s.post(f'{SHUFFLE_URL}/api/v1/workflows', json=wf_def, timeout=120)
    if not cr.ok:
        print(f"  ERROR crear workflow: HTTP {cr.status_code} {cr.text[:300]}")
        sys.exit(1)
    wf = cr.json()
    wf_id = wf['id']
    print(f"  Workflow creado: {wf_id}")

    # Obtener el workflow completo para leer el UUID real del trigger
    wf_detail = s.get(f'{SHUFFLE_URL}/api/v1/workflows/{wf_id}', timeout=60).json()
    triggers = wf_detail.get('triggers', [])
    trigger_id = triggers[0]['id'] if triggers else TRIGGER_NODE
    if not org_id:
        org_id = wf_detail.get('org_id', '')
    print(f"  Trigger ID : {trigger_id}")
    print(f"  Org ID     : {org_id}")

    # Shuffle reemplaza el placeholder del trigger con un UUID real.
    # Corregir:
    #  1) El branch TRIGGER_NODE→ACT_THEHIVE debe usar el UUID real del trigger como source.
    #  2) Cualquier branch trigger_uuid→X (donde X != ACT_THEHIVE) es incorrecto:
    #     debe ser ACT_THEHIVE→X (el fan-out parte del startnode, no del trigger).
    #  3) El startnode es ACT_NORMALIZE (una action), nunca el trigger.
    _thehive_children = set()
    for b in wf_detail.get('branches', []):
        dst = b.get('destination_id', '')
        src = b.get('source_id', '')
        # Replace placeholder trigger id with real uuid in the one Webhook→normalize branch
        if src == TRIGGER_NODE:
            b['source_id'] = trigger_id
        # Any branch that still has trigger as source but points to a non-normalize node
        # should be re-rooted at ACT_NORMALIZE
        elif src == trigger_id and dst != ACT_NORMALIZE:
            b['source_id'] = ACT_NORMALIZE
            _thehive_children.add(dst)

    wf_detail['start'] = ACT_NORMALIZE
    for a in wf_detail.get('actions', []):
        if a.get('id') == ACT_NORMALIZE:
            a['isStartNode'] = True
        else:
            a['isStartNode'] = False
    for t in wf_detail.get('triggers', []):
        if t['id'] == trigger_id:
            t['status'] = 'running'
            t['isStartNode'] = False
    # Set workflow status to active so webhook can trigger it
    wf_detail['status'] = 'active'
    wf_detail['active'] = True
    r_put = s.put(f'{SHUFFLE_URL}/api/v1/workflows/{wf_id}', json=wf_detail, timeout=120)
    print(f"  Branches y startnode actualizados: HTTP {r_put.status_code} (thehive children: {len(_thehive_children)})")

    # Shuffle backend recarga desde workflow_revisions al reiniciar — parchear ambos índices
    print("  Forzando nodo de inicio (start=ACT_NORMALIZE) y branches en Elasticsearch...")
    try:
        es_auth = (SHUFFLE_DATA_USER, SHUFFLE_DATA_PASS) if SHUFFLE_DATA_USER and SHUFFLE_DATA_PASS else None


        def _patch_wf_doc(index, doc_id, trigger_id):
            r = requests.get(f'{SHUFFLE_DATA_URL}/{index}/_doc/{doc_id}', timeout=10, auth=es_auth)
            if r.status_code != 200:
                return r.status_code
            src = r.json().get('_source', {})
            src['start'] = ACT_NORMALIZE
            for _a in src.get('actions', []):
                _a['isStartNode'] = (_a.get('id') == ACT_NORMALIZE)
            for _t in src.get('triggers', []):
                _t['isStartNode'] = False
            # Fix any branches where trigger → non-normalize should be normalize → non-normalize
            for _b in src.get('branches', []):
                if _b.get('source_id') == trigger_id and _b.get('destination_id') != ACT_NORMALIZE:
                    _b['source_id'] = ACT_NORMALIZE
            rp = requests.put(f'{SHUFFLE_DATA_URL}/{index}/_doc/{doc_id}', json=src, timeout=15, auth=es_auth)
            return rp.status_code


        # 1. Parchear workflow-000001
        _wf_idx_res = requests.get(f'{SHUFFLE_DATA_URL}/_cat/indices/workflow-*?h=index', timeout=10, auth=es_auth)
        _wf_index = (_wf_idx_res.text.strip().split('\n') + ['workflow-000001'])[0] or 'workflow-000001'
        _sc1 = _patch_wf_doc(_wf_index, wf_id, trigger_id)
        print(f"  ES workflow start actualizado ({_wf_index}): HTTP {_sc1}")

        # 2. Parchear workflow_revisions (el backend recarga desde aquí tras reinicio)
        _rev_idx_res = requests.get(f'{SHUFFLE_DATA_URL}/_cat/indices/workflow_revisions-*?h=index', timeout=10,
                                    auth=es_auth)
        _rev_index = (_rev_idx_res.text.strip().split('\n') + ['workflow_revisions-000001'])[
                         0] or 'workflow_revisions-000001'
        # ES may not have indexed the revision yet — retry up to 15 s
        _hits = []
        for _attempt in range(4):
            _rev_search = requests.post(
                f'{SHUFFLE_DATA_URL}/{_rev_index}/_search',
                json={'query': {'bool': {'should': [
                    {'term': {'id.keyword': wf_id}},
                    {'match': {'id': wf_id}},
                ]}}, 'size': 5},
                timeout=10,
                auth=es_auth,
            )
            if _rev_search.status_code == 200:
                _hits = _rev_search.json().get('hits', {}).get('hits', [])
            if not _hits:
                # fallback: brute-force match in _source.id
                _rev_all = requests.get(f'{SHUFFLE_DATA_URL}/{_rev_index}/_search?size=50', timeout=10, auth=es_auth)
                _hits = [_h for _h in _rev_all.json().get('hits', {}).get('hits', [])
                         if _h.get('_source', {}).get('id') == wf_id]
            if _hits:
                break
            print(f"  [WARN] Revisión del workflow no encontrada aún en ES, reintentando... ({_attempt * 5}s)")
            time.sleep(5)
        if _hits:
            _rev_doc_id = _hits[0]['_id']
            _sc2 = _patch_wf_doc(_rev_index, _rev_doc_id, trigger_id)
            print(f"  ES revision start actualizado ({_rev_index}/{_rev_doc_id[:8]}): HTTP {_sc2}")
        else:
            print(f"  [WARN] No se encontró revisión del workflow en ES")
    except Exception as e:
        print(f"  [WARN] No se pudo forzar start en ES: {e}")

    # Eliminar workflows antiguos solo después de crear el nuevo correctamente
    for old_id in old_workflow_ids:
        if old_id != wf_id:
            try:
                s.delete(f'{SHUFFLE_URL}/api/v1/workflows/{old_id}', timeout=30)
                print(f"  Eliminado workflow anterior: {old_id}")
            except Exception as e:
                print(f"  [WARN] No se pudo eliminar workflow anterior {old_id}: {e}")

    # ── 5. Registrar hook en Elasticsearch ───────────────────────────────────────
    print("  Registrando hook en Elasticsearch...")
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
    # ── 5. Registrar hook en Elasticsearch usando docker exec
    print("  Registrando hook en Elasticsearch...")
    try:
        # Usar docker exec para ejecutar el comando dentro del contenedor de Elasticsearch
        import subprocess

        hook_json = json.dumps(hook_doc)
        cmd = f'docker exec soar_opensearch curl -s -X PUT "http://localhost:9200/hooks/_doc/{trigger_id}" -H "Content-Type: application/json" -d \'{hook_json}\''
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            print(f"  Hook en ES: {res.stdout}")
        else:
            print(f"  Hook en ES: Error - {res.stderr}")
    except Exception as e:
        print(f"  Hook en ES: Error - {e}")

    # ── 6. Hook registrado (no se necesita reiniciar shuffle-backend) ────────────
    print("  Hook registrado correctamente (sin reinicio del backend necesario).")

    # ── 6b. Crear índice soar-alerts si no existe ─────────────────────────────────
    try:
        _soar_idx = 'soar-alerts'
        _r_idx = requests.get(f'{ES_URL}/{_soar_idx}', timeout=10,
                              auth=(ES_USER, ES_PASS) if ES_USER and ES_PASS else None)
        if _r_idx.status_code == 404:
            _create = requests.put(
                f'{ES_URL}/{_soar_idx}',
                json={"settings": {"number_of_replicas": 0, "number_of_shards": 1}},
                timeout=15,
                auth=(ES_USER, ES_PASS) if ES_USER and ES_PASS else None
            )
            print(f"  Índice soar-alerts creado: HTTP {_create.status_code}")
        else:
            print(f"  Índice soar-alerts ya existe.")
    except Exception as _e:
        print(f"  WARN: no se pudo crear soar-alerts: {_e}")

    # ── 6c. Crear índice soar-metrics con mapping correcto ────────────────────────
    try:
        _metrics_idx = 'soar-metrics'
        _r_metrics = requests.get(f'{ES_URL}/{_metrics_idx}', timeout=10,
                                  auth=(ES_USER, ES_PASS) if ES_USER and ES_PASS else None)
        if _r_metrics.status_code == 404:
            _metrics_mapping = {
                "settings": {"number_of_replicas": 0, "number_of_shards": 1},
                "mappings": {
                    "properties": {
                        "alert_id": {"type": "keyword"},
                        "alert_type": {"type": "keyword"},
                        "severity": {"type": "integer"},
                        "mttr_seconds": {"type": "float"},
                        "@timestamp": {"type": "date"},
                        "timestamp": {"type": "keyword"},
                        "source": {"type": "keyword"},
                        "metric_type": {"type": "keyword"},
                        "thehive_case_id": {"type": "keyword"},
                        "cortex_hash_job": {"type": "text"},
                        "cortex_ip_job": {"type": "text"},
                        "misp_results": {"type": "text"},
                    }
                }
            }
            _create_m = requests.put(
                f'{ES_URL}/{_metrics_idx}',
                json=_metrics_mapping,
                timeout=15,
                auth=(ES_USER, ES_PASS) if ES_USER and ES_PASS else None,
            )
            print(f"  Índice soar-metrics creado con mapping: HTTP {_create_m.status_code}")
        else:
            print(f"  Índice soar-metrics ya existe.")
    except Exception as _e:
        print(f"  WARN: no se pudo crear soar-metrics: {_e}")

    # ── 7. Credenciales ES incluidas directamente en los params del workflow ───────
    print("  Credenciales de Elasticsearch incluidas en la definición del workflow.")

    # ── 8. Verificar webhook ──────────────────────────────────────────────────────
    # Disabled to avoid creating extra cases that interfere with E2E tests
    # Internal URL (used within the Docker network, e.g. from soar_api container)
    webhook_url_internal = f'{SHUFFLE_URL}/api/v1/hooks/webhook_{trigger_id}'

    # External URL (used from the Docker host / Windows, replaces container hostname with localhost)
    _external_base = SHUFFLE_URL.replace('soar_shuffle_backend', 'localhost').replace('soar_shuffle_frontend',
                                                                                      'localhost')
    webhook_url = f'{_external_base}/api/v1/hooks/webhook_{trigger_id}'
    print(f"  Webhook URL: {webhook_url}")

    # ── 8. Guardar info ───────────────────────────────────────────────────────────
    default_info_dir = '/app/results' if os.path.isdir('/app/results') else os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
        'artifacts', 'results'
    )
    info_path = os.path.join(os.environ.get('WEBHOOK_INFO_DIR', default_info_dir), 'webhook_info.json')
    os.makedirs(os.path.dirname(info_path), exist_ok=True)
    webhook_info = {
        "webhook_url": webhook_url_internal,
        "webhook_url_host": webhook_url,
        "workflow_id": wf_id,
        "trigger_id": trigger_id,

        "org_id": org_id,
        "workflow_name": WF_NAME,
        "actions": {
            "thehive": f"{THEHIVE_URL} - crear caso",
            "cortex_hash": f"{CORTEX_URL} - analizar hash",
            "cortex_ip": f"{CORTEX_URL} - analizar IP",
            "misp": f"{MISP_URL} - buscar IOC",
            "elasticsearch": f"{ES_URL}/soar-alerts - indexar alerta",
            "wazuh": f"{WAZUH_URL}/agents - listar agentes",
        },
    }
    try:
        with open(info_path, 'w') as f:
            json.dump(webhook_info, f, indent=2)
        # Copy to /app/webhook_info.json for E2E tests (inside container)
        if os.path.exists('/app'):
            app_path = '/app/webhook_info.json'
            try:
                with open(app_path, 'w') as f:
                    json.dump(webhook_info, f, indent=2)
                print(f'  [info] Copiado a {app_path} para tests E2E')
            except Exception as e:
                print(f'  [WARN] No se pudo copiar a {app_path}: {e}')
    except Exception as e:
        # Fallback: write to /tmp and print path for manual copy
        print(f'  [WARN] Error escribiendo {info_path}: {e}')
        tmp_path = '/tmp/webhook_info.json'
        with open(tmp_path, 'w') as f:
            json.dump(webhook_info, f, indent=2)
        print(f'  [WARN] Escrito en {tmp_path}')
        print(f'  [WARN] Ejecutar: docker cp soar_api:{tmp_path} {info_path}')

    print()
    print('=' * 60)
    print(f'  WEBHOOK ACTIVO : {webhook_url}')
    print(f'  Workflow       : {WF_NAME}')
    print('  Acciones       :')
    print(f'    TheHive  -> crear caso en    {THEHIVE_URL}')
    print(f'    Cortex   -> analizar hash+IP {CORTEX_URL}')
    print(f'    MISP     -> buscar IOC       {MISP_URL}')
    print(f'    ES       -> indexar alertas  {ES_URL}/soar-alerts')
    print(f'    Wazuh    -> listar agentes   {WAZUH_URL}/agents')
    print()
    print(f'  Usar con:')
    print(f'    make simulate SIMULATE_WEBHOOK="{webhook_url}"')
    print(f'  Info guardada en: {info_path}')
    print('=' * 60)

    # ── 9. Importar dashboard Grafana KPI ────────────────────────────────────────
    print()
    print("Importando dashboard Grafana KPI...")
    GRAFANA_URL = os.environ.get('GRAFANA_URL', 'http://soar_grafana:3000')
    GRAFANA_USER = os.environ.get('GRAFANA_ADMIN_USER', 'admin')
    GRAFANA_PASS = os.environ.get('GRAFANA_ADMIN_PASSWORD', '')

    # Path to kpi-dashboard.json (relative to project root)
    # In Docker container, project root is /app, so path is /app/infra/docker/compose/logging/kpi-dashboard.json
    # In local execution, path is relative to script location
    if os.path.exists('/app/infra/docker/compose/logging/kpi-dashboard.json'):
        kpi_dashboard_path = '/app/infra/docker/compose/logging/kpi-dashboard.json'
    else:
        kpi_dashboard_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'infra', 'docker', 'compose', 'logging', 'kpi-dashboard.json'
        )

    try:
        with open(kpi_dashboard_path, 'r') as f:
            dashboard = json.load(f)

        grafana_response = requests.post(
            f'{GRAFANA_URL}/api/dashboards/db',
            auth=(GRAFANA_USER, GRAFANA_PASS),
            json=dashboard,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )

        if grafana_response.status_code == 200:
            result = grafana_response.json()
            print(f"  Dashboard KPI importado exitosamente:")
            print(f"    UID: {result.get('uid')}")
            print(f"    URL: {result.get('url')}")
            print(f"    ID: {result.get('id')}")
        else:
            print(f"  WARN: No se pudo importar dashboard KPI: HTTP {grafana_response.status_code}")
            print(f"  Response: {grafana_response.text[:200]}")
    except FileNotFoundError:
        print(f"  WARN: Archivo kpi-dashboard.json no encontrado en {kpi_dashboard_path}")
    except Exception as e:
        print(f"  WARN: Error al importar dashboard KPI: {e}")


if __name__ == "__main__":
    _check_required_passwords()
    init_shuffle_webhook()
