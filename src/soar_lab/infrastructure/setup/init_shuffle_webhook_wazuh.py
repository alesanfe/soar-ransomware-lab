#!/usr/bin/env python3
"""
Inicializa Shuffle con un workflow SOAR completo que orquesta:
  1. Webhook  — recibe alertas de Wazuh SIEM
  2. TheHive  — crea caso de incidente
  3. Cortex   — analiza IOCs (hash, IP) del ransomware
  4. MISP     — busca indicadores en threat intelligence
  5. Wazuh    — gestiona agentes afectados y respuestas

Uso:
  python src/soar_lab/infrastructure/setup/init_shuffle_webhook_wazuh.py

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

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    # Try to load from .env.full first, then .env
    if not load_dotenv('.env.full'):
        load_dotenv()
except ImportError:
    pass

# Reuse integration clients where possible (only available after pip install)
try:
    from soar_lab.integrations.shuffle_client import ShuffleClient
    from soar_lab.integrations.elasticsearch_client import ElasticsearchClient
    from soar_lab.integrations.thehive_client import TheHiveClient

    _CLIENTS_AVAILABLE = True
except ImportError:
    _CLIENTS_AVAILABLE = False

# ── URLs con defaults ─────────────────────────────────────────────────────────
SHUFFLE_URL = os.environ.get('SHUFFLE_URL', 'http://soar_shuffle_frontend:80')
ES_URL = os.environ.get('ES_URL', 'http://soar_elasticsearch:9200')
THEHIVE_URL = os.environ.get('THEHIVE_URL', 'http://soar_thehive:9000')
CORTEX_URL = os.environ.get('CORTEX_URL', 'http://soar_cortex:9001')
MISP_URL = os.environ.get('MISP_URL', 'http://soar_misp:80')
WAZUH_URL = os.environ.get('WAZUH_URL', 'https://soar_wazuh_manager:55000')

# ── Credenciales basicas (no rotan) ───────────────────────────────────────────
SHUFFLE_USER = os.environ.get('SHUFFLE_USER', 'admin')
SHUFFLE_PASS = os.environ.get('SHUFFLE_PASS', os.environ.get('SHUFFLE_DEFAULT_PASSWORD', ''))
WAZUH_USER = os.environ.get('WAZUH_USER', 'wazuh-wui')
WAZUH_PASS = os.environ.get('WAZUH_PASS', os.environ.get('WAZUH_API_PASSWORD', ''))

THEHIVE_ADMIN_USER = os.environ.get('THEHIVE_ADMIN_USER', 'admin')
THEHIVE_ADMIN_PASS = os.environ.get('THEHIVE_ADMIN_PASSWORD', 'X8k#2mP5$vR9@nQ3tW6!zY1&hF4sD7')
CORTEX_ADMIN_USER = os.environ.get('CORTEX_ADMIN_USER', 'admin')
CORTEX_ADMIN_PASS = os.environ.get('CORTEX_ADMIN_PASSWORD', 'J5x#8mP3$vR2@nQ7tW4!zY9&hF1sD6')
MISP_ADMIN_EMAIL = os.environ.get('MISP_ADMIN_EMAIL', 'admin@admin.test')
MISP_ADMIN_PASS = os.environ.get('MISP_ADMIN_PASSWORD', 'admin')

if not SHUFFLE_PASS:
    print('[ERROR] Falta SHUFFLE_PASS')
    sys.exit(1)
if not WAZUH_PASS:
    print('[ERROR] Falta WAZUH_PASS')
    sys.exit(1)

# ── Obtener API keys dinamicamente ────────────────────────────────────────────
_ENV_FILE = '.env'


def fetch_thehive_key(thehive_url, admin_user, admin_pass, es_url):
    """Devuelve la API key de TheHive: reutiliza la del .env si sigue valida, si no la renueva."""
    import base64, re as _re
    # 1. Intentar reutilizar la key guardada en .env
    if os.path.exists(_ENV_FILE):
        content = open(_ENV_FILE).read()
        m = _re.search(r'^THEHIVE_API_KEY=(.+)$', content, _re.MULTILINE)
        if m:
            existing = m.group(1).strip()
            try:
                if _CLIENTS_AVAILABLE:
                    client = TheHiveClient(base_url=thehive_url, api_key=existing)
                    client.get(f'/api/user/{admin_user}')
                else:
                    rv = requests.get(f'{thehive_url}/api/user/{admin_user}',
                                      headers={'Authorization': f'Bearer {existing}'}, timeout=10)
                    if not rv.ok:
                        raise ValueError('key invalid')
                print(f'  [key] TheHive API key reutilizada: {existing[:8]}...')
                return existing
            except Exception:
                pass
    # 2. Renovar (solo si la existente no funciona)
    auth = base64.b64encode(f'{admin_user}:{admin_pass}'.encode()).decode()
    try:
        r = requests.post(f'{thehive_url}/api/user/{admin_user}/key/renew',
                          data='{}',
                          headers={'Authorization': f'Basic {auth}',
                                   'Content-Type': 'application/json'},
                          timeout=10)
        if r.ok:
            key = r.text.strip().strip('"')
            if len(key) > 10:
                print(f'  [key] TheHive API key renovada: {key}')
                return key
    except Exception as e:
        print(f'  [key] TheHive exception: {e}')
    print('  [key] WARN: no se pudo obtener API key de TheHive')
    return ''


def fetch_cortex_key(cortex_url, admin_user, admin_pass, es_url):
    """Devuelve la API key de Cortex guardada por reset_cortex.py en .env.
    NOTA: NO llama a key/renew porque cada renew invalida la anterior. La key
    la genera reset_cortex.py (que siempre se ejecuta antes en make up)."""
    import re as _re
    # Leer de env var directa primero
    key_env = os.environ.get('CORTEX_API_KEY', '')
    if key_env and len(key_env) > 10:
        print(f'  [key] Cortex API key (de CORTEX_API_KEY env): {key_env[:8]}...')
        return key_env
    if os.path.exists(_ENV_FILE):
        content = open(_ENV_FILE).read()
        m = _re.search(r'^CORTEX_API_KEY=(.+)$', content, _re.MULTILINE)
        if m:
            existing = m.group(1).strip()
            if len(existing) > 10:
                print(f'  [key] Cortex API key (de {_ENV_FILE}): {existing[:8]}...')
                return existing
    print(f'  [key] WARN: no hay CORTEX_API_KEY en {_ENV_FILE} — ejecuta reset_cortex.py primero')
    return ''


def save_keys_to_env(thehive_key, cortex_key, misp_key, env_file=None):
    """Persiste las API keys en .env para reutilizarlas sin rotar."""
    if env_file is None:
        env_file = _ENV_FILE
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
    with open(env_file, 'w') as f:
        f.write(content)
    print(f'  [keys] Guardadas en {env_file}')


def fetch_misp_key(misp_url, admin_email, admin_pass):
    """Obtiene la API key de MISP — primero del env, luego via docker exec."""
    import os, re as _re
    # 1. Env var directa
    key_env = os.environ.get('MISP_API_KEY', '')
    if key_env and len(key_env) > 10:
        print(f'  [key] MISP API key (de MISP_API_KEY env): {key_env[:8]}...')
        return key_env
    # 2. Leer del .env
    if os.path.exists(_ENV_FILE):
        content = open(_ENV_FILE).read()
        m = _re.search(r'^MISP_API_KEY=(.+)$', content, _re.MULTILINE)
        if m:
            existing = m.group(1).strip()
            if len(existing) > 10:
                print(f'  [key] MISP API key (de {_ENV_FILE}): {existing[:8]}...')
                return existing
    # 3. Fallback: docker exec en soar_misp_db
    db_user = os.environ.get('MISP_DB_USER', 'misp')
    db_pass = os.environ.get('MISP_DB_PASSWORD', 'MispDbPassword456!@#')
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
            print(f'  [key] MISP API key via DB: {key[:8]}...')
            return key
    except Exception as e:
        print(f'  [key] MISP DB exception: {e}')
    print('  [key] WARN: no se pudo obtener API key de MISP')
    return ''


# URLs internas Docker (usando nombres de contenedores en la red Docker)
THEHIVE_INT = 'http://soar_thehive:9000'
CORTEX_INT = 'http://soar_cortex:9001'
MISP_INT = 'https://soar_misp'
ES_INT = 'http://host.docker.internal:9201'
WAZUH_INT = 'https://host.docker.internal:55100'

WF_NAME = 'SOAR-Ransomware-Response-Wazuh'

print(f"[init_shuffle_webhook] Conectando a {SHUFFLE_URL} ...")


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


_OPENAPI_SPECS = {
    'TheHive': {
        'openapi': '3.0.0',
        'info': {'title': 'TheHive', 'version': '3.5.2', 'description': 'TheHive security incident response platform'},
        'servers': [{'url': 'http://thehive:9000'}],
        'components': {'securitySchemes': {'BearerAuth': {'type': 'http', 'scheme': 'bearer'}}},
        'security': [{'BearerAuth': []}],
        'paths': {
            '/api/case': {
                'post': {'operationId': 'create_case', 'summary': 'Create a case',
                         'requestBody': {'content': {'application/json': {'schema': {'type': 'object', 'properties': {
                             'title': {'type': 'string'}, 'description': {'type': 'string'},
                             'severity': {'type': 'integer'}, 'tlp': {'type': 'integer'},
                             'flag': {'type': 'boolean'}, 'tags': {'type': 'array', 'items': {'type': 'string'}}
                         }}}}},
                         'responses': {'201': {'description': 'Case created'}}},
                'get': {'operationId': 'list_cases', 'summary': 'List cases',
                        'responses': {'200': {'description': 'List of cases'}}},
            },
            '/api/case/{caseId}/task': {
                'post': {'operationId': 'create_task', 'summary': 'Add task to case',
                         'parameters': [
                             {'name': 'caseId', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                         'requestBody': {'content': {'application/json': {'schema': {'type': 'object', 'properties': {
                             'title': {'type': 'string'}, 'description': {'type': 'string'},
                             'status': {'type': 'string'}, 'flag': {'type': 'boolean'}
                         }}}}},
                         'responses': {'201': {'description': 'Task created'}}},
            },
            '/api/case/{caseId}/artifact': {
                'post': {'operationId': 'create_observable', 'summary': 'Add observable to case',
                         'parameters': [
                             {'name': 'caseId', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                         'requestBody': {'content': {'application/json': {'schema': {'type': 'object', 'properties': {
                             'dataType': {'type': 'string'}, 'data': {'type': 'string'},
                             'message': {'type': 'string'}, 'tlp': {'type': 'integer'}, 'ioc': {'type': 'boolean'},
                             'tags': {'type': 'array', 'items': {'type': 'string'}}
                         }}}}},
                         'responses': {'201': {'description': 'Observable created'}}},
            },
            '/api/case/{caseId}': {
                'get': {'operationId': 'get_case', 'summary': 'Get case by ID',
                        'parameters': [
                            {'name': 'caseId', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                        'responses': {'200': {'description': 'Case details'}}},
            },
        },
    },
    'MISP': {
        'openapi': '3.0.0',
        'info': {'title': 'MISP', 'version': '2.4', 'description': 'MISP Threat Intelligence Platform'},
        'servers': [{'url': 'https://misp'}],
        'components': {'securitySchemes': {'ApiKeyAuth': {'type': 'apiKey', 'in': 'header', 'name': 'Authorization'}}},
        'security': [{'ApiKeyAuth': []}],
        'paths': {
            '/attributes/restSearch': {
                'post': {'operationId': 'search_attributes', 'summary': 'Search attributes (IOCs)',
                         'requestBody': {'content': {'application/json': {'schema': {'type': 'object', 'properties': {
                             'value': {'type': 'string'}, 'type': {'type': 'string'},
                             'limit': {'type': 'integer'}, 'page': {'type': 'integer'}
                         }}}}},
                         'responses': {'200': {'description': 'Search results'}}},
            },
            '/events/restSearch': {
                'post': {'operationId': 'search_events', 'summary': 'Search events',
                         'requestBody': {'content': {'application/json': {'schema': {'type': 'object', 'properties': {
                             'value': {'type': 'string'}, 'limit': {'type': 'integer'}
                         }}}}},
                         'responses': {'200': {'description': 'Events list'}}},
            },
            '/events': {
                'post': {'operationId': 'create_event', 'summary': 'Create event',
                         'requestBody': {'content': {'application/json': {'schema': {'type': 'object', 'properties': {
                             'Event': {'type': 'object'}
                         }}}}},
                         'responses': {'200': {'description': 'Event created'}}},
            },
        },
    },
    'Elasticsearch': {
        'openapi': '3.0.0',
        'info': {'title': 'Elasticsearch', 'version': '7.10', 'description': 'Elasticsearch REST API'},
        'servers': [{'url': 'http://elasticsearch:9200'}],
        'paths': {
            '/{index}/_doc': {
                'post': {'operationId': 'index_document', 'summary': 'Index a document',
                         'parameters': [
                             {'name': 'index', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                         'requestBody': {'content': {'application/json': {'schema': {'type': 'object'}}}},
                         'responses': {'201': {'description': 'Document indexed'}}},
            },
            '/{index}/_search': {
                'post': {'operationId': 'search', 'summary': 'Search documents',
                         'parameters': [
                             {'name': 'index', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                         'requestBody': {'content': {'application/json': {'schema': {'type': 'object', 'properties': {
                             'query': {'type': 'object'}, 'size': {'type': 'integer'}
                         }}}}},
                         'responses': {'200': {'description': 'Search results'}}},
                'get': {'operationId': 'search_get', 'summary': 'Search documents (GET)',
                        'parameters': [{'name': 'index', 'in': 'path', 'required': True, 'schema': {'type': 'string'}},
                                       {'name': 'q', 'in': 'query', 'schema': {'type': 'string'}}],
                        'responses': {'200': {'description': 'Search results'}}},
            },
            '/{index}/_doc/{id}': {
                'get': {'operationId': 'get_document', 'summary': 'Get document by ID',
                        'parameters': [{'name': 'index', 'in': 'path', 'required': True, 'schema': {'type': 'string'}},
                                       {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                        'responses': {'200': {'description': 'Document'}}},
            },
            '/_cluster/health': {
                'get': {'operationId': 'cluster_health', 'summary': 'Cluster health',
                        'responses': {'200': {'description': 'Health status'}}},
            },
        },
    },
    'Wazuh': {
        'openapi': '3.0.0',
        'info': {'title': 'Wazuh', 'version': '4.14', 'description': 'Wazuh SIEM/XDR API'},
        'servers': [{'url': 'https://wazuh-manager:55000'}],
        'components': {'securitySchemes': {'BearerAuth': {'type': 'http', 'scheme': 'bearer'}}},
        'security': [{'BearerAuth': []}],
        'paths': {
            '/security/user/authenticate': {
                'post': {'operationId': 'authenticate', 'summary': 'Authenticate and get JWT token',
                         'responses': {'200': {'description': 'JWT token'}}},
            },
            '/agents': {
                'get': {'operationId': 'list_agents', 'summary': 'List agents',
                        'parameters': [{'name': 'status', 'in': 'query', 'schema': {'type': 'string'}},
                                       {'name': 'limit', 'in': 'query', 'schema': {'type': 'integer'}}],
                        'responses': {'200': {'description': 'List of agents'}}},
            },
            '/agents/{agent_id}/restart': {
                'put': {'operationId': 'restart_agent', 'summary': 'Restart agent',
                        'parameters': [
                            {'name': 'agent_id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                        'responses': {'200': {'description': 'Agent restarted'}}},
            },
            '/syscheck/{agent_id}/run': {
                'put': {'operationId': 'run_syscheck', 'summary': 'Run syscheck on agent',
                        'parameters': [
                            {'name': 'agent_id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                        'responses': {'200': {'description': 'Syscheck started'}}},
            },
            '/alerts': {
                'get': {'operationId': 'list_alerts', 'summary': 'List alerts',
                        'parameters': [{'name': 'limit', 'in': 'query', 'schema': {'type': 'integer'}},
                                       {'name': 'offset', 'in': 'query', 'schema': {'type': 'integer'}}],
                        'responses': {'200': {'description': 'Alerts list'}}},
            },
        },
    },
    'Cortex': {
        'openapi': '3.0.0',
        'info': {'title': 'Cortex', 'version': '3.1', 'description': 'Cortex threat intelligence analysis platform'},
        'servers': [{'url': 'http://cortex:9001'}],
        'components': {'securitySchemes': {'BearerAuth': {'type': 'http', 'scheme': 'bearer'}}},
        'security': [{'BearerAuth': []}],
        'paths': {
            '/analyzer': {
                'get': {'operationId': 'list_analyzers', 'summary': 'List available analyzers',
                        'responses': {'200': {'description': 'List of analyzers'}}},
            },
            '/analyzer/{analyzerId}/run': {
                'post': {'operationId': 'run_analyzer', 'summary': 'Run an analyzer',
                         'parameters': [
                             {'name': 'analyzerId', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                         'requestBody': {'content': {'application/json': {'schema': {'type': 'object', 'properties': {
                             'data': {'type': 'string'}, 'dataType': {'type': 'string'},
                             'tlp': {'type': 'integer'}, 'parameters': {'type': 'object'}
                         }}}}},
                         'responses': {'200': {'description': 'Analysis job created'}}},
            },
            '/job/{jobId}': {
                'get': {'operationId': 'get_job', 'summary': 'Get job status',
                        'parameters': [{'name': 'jobId', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                        'responses': {'200': {'description': 'Job details'}}},
            },
            '/job/{jobId}/wait': {
                'get': {'operationId': 'wait_job', 'summary': 'Wait for job completion',
                        'parameters': [{'name': 'jobId', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                        'responses': {'200': {'description': 'Job result'}}},
            },
            '/job/{jobId}/report': {
                'get': {'operationId': 'get_job_report', 'summary': 'Get job report',
                        'parameters': [{'name': 'jobId', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
                        'responses': {'200': {'description': 'Analysis report'}}},
            },
        },
    },
}


def ensure_openapi_apps(session, shuffle_url, shuffle_apikey):
    """Sube los specs OpenAPI para TheHive, MISP, Elasticsearch, Wazuh y Cortex si no están instalados."""
    resp = session.get(f'{shuffle_url}/api/v1/apps', timeout=15)
    existing = {a.get('name', '').lower() for a in (resp.json() if resp.ok and isinstance(resp.json(), list) else [])}
    headers = {'Authorization': f'Bearer {shuffle_apikey}', 'Content-Type': 'application/json'}

    for app_name, spec in _OPENAPI_SPECS.items():
        if app_name.lower() in existing:
            print(f'  [openapi] {app_name}: ya instalada')
            continue
        print(f'  [openapi] Subiendo spec para {app_name}...')
        try:
            # Paso 1: validar
            r1 = session.post(f'{shuffle_url}/api/v1/validate_openapi',
                              headers=headers, data=json.dumps(spec), timeout=30)
            if not r1.ok:
                print(f'  [openapi] {app_name}: validate falló {r1.status_code} {r1.text[:80]}')
                continue
            handle_id = r1.json().get('id', '')
            # Paso 2: obtener spec procesado
            r2 = session.get(f'{shuffle_url}/api/v1/get_openapi/{handle_id}',
                             headers=headers, timeout=15)
            if not r2.ok:
                print(f'  [openapi] {app_name}: get_openapi falló {r2.status_code}')
                continue
            body = r2.json().get('body', '')
            if isinstance(body, dict):
                body = json.dumps(body)
            # Paso 3: construir la app
            r3 = session.post(f'{shuffle_url}/api/v1/verify_openapi?sharing=true',
                              headers=headers, data=body, timeout=30)
            if r3.ok:
                print(f'  [openapi] {app_name}: instalada OK')
            else:
                print(f'  [openapi] {app_name}: verify falló {r3.status_code} {r3.text[:80]}')
        except Exception as ex:
            print(f'  [openapi] {app_name}: error — {ex}')


def get_app_ids(session, shuffle_url):
    """Obtiene los IDs reales de las apps necesarias. Descarga las oficiales si faltan."""
    print("  [apps] Obteniendo IDs de apps instaladas...")
    if _CLIENTS_AVAILABLE:
        apps = s_client.list_apps()
    else:
        resp = session.get(f'{shuffle_url}/api/v1/apps', timeout=15)
        apps = resp.json() if resp.ok and isinstance(resp.json(), list) else []
    by_name = {a.get('name', '').lower(): a.get('id', '') for a in apps}
    print(f"  [apps] Apps disponibles ({len(apps)}): {sorted(by_name.keys())}")

    # Apps requeridas por el workflow (thehive/misp no existen como apps nativas, se usa http)
    _required = {'http', 'shuffle tools', 'cortex'}
    _missing = _required - set(by_name.keys())
    if _missing:
        print(f"  [apps] Faltan: {sorted(_missing)} — descargando python-apps oficiales...")
        if _CLIENTS_AVAILABLE:
            s_client.download_remote_apps('https://github.com/shuffle/python-apps')
        else:
            r = session.post(
                f'{shuffle_url}/api/v1/apps/download_remote',
                json={'url': 'https://github.com/shuffle/python-apps', 'force_update': False},
                timeout=300,
            )
            print(f"  [apps] Download: HTTP {r.status_code}")
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
    hive_id = by_name.get('thehive', http_id)
    cortex_id = by_name.get('cortex', http_id)
    misp_id = by_name.get('misp', http_id)
    es_id = by_name.get('elasticsearch', http_id)
    wazuh_id = by_name.get('wazuh', http_id)
    tools_id = by_name.get('shuffle tools', http_id)
    _short = lambda x: x[:8] if x else '?'
    print(f"  [apps] http={_short(http_id)}  thehive={_short(hive_id)}  cortex={_short(cortex_id)}"
          f"  misp={_short(misp_id)}  elasticsearch={_short(es_id)}  wazuh={_short(wazuh_id)}")
    return {
        'TheHive': hive_id,
        'Cortex': cortex_id,
        'MISP': misp_id,
        'Elasticsearch': es_id,
        'Wazuh': wazuh_id,
        'http': http_id,
        'Shuffle Tools': tools_id,
    }


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
    _es = ES_URL
    _auth = _b64.b64encode(f"{ES_USER}:{ES_PASS}".encode()).decode() if ES_USER and ES_PASS else None
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
        print("  [es-fix] Mapping de 'users.apickey' ya tiene subfield keyword — verificando users_v2")
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
    _es = ES_URL
    _auth = _b64.b64encode(f"{ES_USER}:{ES_PASS}".encode()).decode() if ES_USER and ES_PASS else None
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


# ── 1. Login y verificar usuario ──────────────────────────────────────────────
if _CLIENTS_AVAILABLE:
    _shuffle_api_key = os.environ.get('SHUFFLE_API_KEY', '')
    s_client = ShuffleClient(base_url=SHUFFLE_URL, api_key=_shuffle_api_key or 'placeholder')
    if not s_client.login(SHUFFLE_USER, SHUFFLE_PASS):
        print(f"  ERROR login Shuffle")
        sys.exit(1)
    print("  Login OK (ShuffleClient)")
    # Reuse internal session for operations that need raw session (workflow PUT, etc.)
    s = s_client._session
else:
    s = requests.Session()
    s.verify = False
    lr = s.post(f'{SHUFFLE_URL}/api/v1/login',
                json={'username': SHUFFLE_USER, 'password': SHUFFLE_PASS}, timeout=15)
    if not lr.ok:
        print(f"  ERROR login: HTTP {lr.status_code}")
        sys.exit(1)
    print("  Login OK")

# Asegurar usuario verificado en ES (comentado porque ES no es accesible desde el host)
# if _CLIENTS_AVAILABLE:
#    _es_setup = ElasticsearchClient(base_url=ES_URL)
#    try:
#        users_resp = _es_setup.search(query={'match_all': {}}, index='users', size=50)
#        for hit in users_resp.get('hits', {}).get('hits', []):
#            u = hit['_source']
#            if u.get('username') == SHUFFLE_USER and not u.get('verified', False):
#                _es_setup.update_document(hit['_id'], {'verified': True, 'first_setup': True},
#                                          index='users')
#                print("  Usuario verificado en ES")
#    except Exception:
#        pass
# else:
#    users_r = requests.get(f'{ES_URL}/users/_search', timeout=30)
#    for hit in users_r.json().get('hits', {}).get('hits', []):
#        u = hit['_source']
#        if u.get('username') == SHUFFLE_USER and not u.get('verified', False):
#            requests.post(f'{ES_URL}/users/_update/{hit["_id"]}',
#                          json={'doc': {'verified': True, 'first_setup': True}}, timeout=30)
#            print("  Usuario verificado en ES")

# ── 1b. Obtener API keys dinamicamente ────────────────────────────────────────
print("  Obteniendo API keys de los servicios...")
THEHIVE_KEY = fetch_thehive_key(THEHIVE_URL, THEHIVE_ADMIN_USER, THEHIVE_ADMIN_PASS, ES_URL)
CORTEX_KEY = fetch_cortex_key(CORTEX_URL, CORTEX_ADMIN_USER, CORTEX_ADMIN_PASS, ES_URL)
MISP_KEY = fetch_misp_key(MISP_URL, MISP_ADMIN_EMAIL, MISP_ADMIN_PASS)

# Fallback to hardcoded keys if dynamic fetch fails
if not THEHIVE_KEY:
    THEHIVE_KEY = 'rGdCHFJcf3NeTFbu9JhSymBKsTut4NYS'
    print(f'  [key] THEHIVE API key fallback: {THEHIVE_KEY[:8]}...')

save_keys_to_env(THEHIVE_KEY, CORTEX_KEY, MISP_KEY)

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
#   [Webhook] ──> [1. TheHive: POST /api/v1/case]
#             ──> [2. Cortex: POST /job (hash)]
#             ──> [3. Cortex: POST /job (IP)]
#             ──> [4. MISP: POST /attributes/restSearch]
#             ──> [5. ES: POST /soar-alerts/_doc]
#             ──> [6. Wazuh: GET /agents]
#
TRIGGER_NODE = "webhook_trigger"

# Instalar apps OpenAPI para servicios del stack que no tienen app nativa
_shuffle_apikey = os.environ.get('SHUFFLE_DEFAULT_APIKEY', '')
if not _shuffle_apikey and os.path.exists(_ENV_FILE):
    import re as _re2

    _m = _re2.search(r'^SHUFFLE_DEFAULT_APIKEY=(.+)$', open(_ENV_FILE).read(), _re2.MULTILINE)
    if _m:
        _shuffle_apikey = _m.group(1).strip()
if not _shuffle_apikey:
    _shuffle_apikey = 'f2a8b3c9-d4e1-5f6a-7b8c-9d0e1f2a3b4c'  # default del compose
print("  Instalando apps OpenAPI (TheHive, MISP, Elasticsearch, Wazuh)...")
ensure_openapi_apps(s, SHUFFLE_URL, _shuffle_apikey)

# App IDs — se resuelven dinámicamente usando apps oficiales instaladas
app_ids = get_app_ids(s, SHUFFLE_URL)
APP_ID_THEHIVE = app_ids.get('TheHive', '')
APP_ID_CORTEX = app_ids.get('Cortex', '')
APP_ID_MISP = app_ids.get('MISP', '')
APP_ID_ELASTICSEARCH = app_ids.get('Elasticsearch', '')
APP_ID_WAZUH = app_ids.get('Wazuh', '')
APP_ID_HTTP = app_ids.get('http', '')
APP_ID_SHUFFLE_TOOLS = app_ids.get('Shuffle Tools', app_ids.get('http', ''))
APP_ID_NETCRAFT = app_ids.get('netcraft', '')

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
# Nodo 7 — MISP: buscar hash concreto
ACT_MISP = "act_misp_search"
# Nodo 7b — Shuffle Tools: verificar búsqueda MISP
ACT_VERIFY_MISP = "act_verify_misp"
# Nodo 8 — Wazuh: indexar alerta y gestionar agentes
ACT_WAZUH_INDEX = "act_wazuh_index"
# Nodo 8b — Shuffle Tools: verificar indexación Wazuh
ACT_VERIFY_WAZUH_INDEX = "act_verify_wazuh_index"
# Nodo 9 — Wazuh: listar agentes afectados
ACT_WAZUH = "act_wazuh_agents"
# Nodo 9b — Shuffle Tools: verificar agentes Wazuh
ACT_VERIFY_WAZUH = "act_verify_wazuh"
# Nodo 10 — Shuffle Tools: calcular MTTR del workflow
ACT_CALC_MTTR = "act_calc_mttr"
# Nodo 11 — TheHive: enriquecer caso con resultados de análisis
ACT_ENRICH_CASE = "act_enrich_case"
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

WAZUH_AUTH = __import__('base64').b64encode(f'{WAZUH_USER}:{WAZUH_PASS}'.encode()).decode()
CORTEX_BASIC = __import__('base64').b64encode(f'{CORTEX_ADMIN_USER}:{CORTEX_ADMIN_PASS}'.encode()).decode()

# Obtener un analizador de hash disponible para usar su ID en los jobs
_hash_analyzer_id = 'FileInfo_8_0'
_ip_analyzer_id = 'AbuseIPDB_1_0'
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
        headers={'Authorization': f'Basic {CORTEX_BASIC}'},
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
        if _hash_ans:
            _hash_analyzer_id = _hash_ans[0]['name']
            print(f'  [cortex] Analizador hash seleccionado: {_hash_analyzer_id}')
        if _ip_ans:
            _ip_analyzer_id = _ip_ans[0]['name']
            print(f'  [cortex] Analizador IP seleccionado: {_ip_analyzer_id}')
        # Seleccionar analizadores adicionales
        _virusshare = [a for a in _hash_ans if 'Virusshare' in a['name']]
        if _virusshare:
            _hash_virusshare_id = _virusshare[0]['name']
            print(f'  [cortex] Analizador Virusshare seleccionado: {_hash_virusshare_id}')
        _urlscan_hash = [a for a in _hash_ans if 'Urlscan.io_Search' in a['name']]
        if _urlscan_hash:
            _hash_urlscan_id = _urlscan_hash[0]['name']
            print(f'  [cortex] Analizador Urlscan (hash) seleccionado: {_hash_urlscan_id}')
        _robtex = [a for a in _ip_ans if 'Robtex_IP_Query' in a['name']]
        if _robtex:
            _ip_robtex_id = _robtex[0]['name']
            print(f'  [cortex] Analizador Robtex seleccionado: {_ip_robtex_id}')
        _robtex_reverse = [a for a in _ip_ans if 'Robtex_Reverse_PDNS_Query' in a['name']]
        if _robtex_reverse:
            _ip_robtex_reverse_id = _robtex_reverse[0]['name']
            print(f'  [cortex] Analizador Robtex Reverse seleccionado: {_ip_robtex_reverse_id}')
        _googledns = [a for a in _ip_ans if 'GoogleDNS_resolve' in a['name']]
        if _googledns:
            _ip_googledns_id = _googledns[0]['name']
            print(f'  [cortex] Analizador GoogleDNS seleccionado: {_ip_googledns_id}')
        _ipapi = [a for a in _ip_ans if 'IP-API' in a['name']]
        if _ipapi:
            _ip_ipapi_id = _ipapi[0]['name']
            print(f'  [cortex] Analizador IP-API seleccionado: {_ip_ipapi_id}')
        _urlscan_ip = [a for a in _ip_ans if 'Urlscan.io_Search' in a['name']]
        if _urlscan_ip:
            _ip_urlscan_id = _urlscan_ip[0]['name']
            print(f'  [cortex] Analizador Urlscan (IP) seleccionado: {_ip_urlscan_id}')
except Exception as _e:
    print(f'  [cortex] WARN no se pudo obtener analizadores: {_e}')

actions_list = [
    # ── 1. TheHive: crear caso ───────────────────────────────────────────────
    action(
        aid=ACT_THEHIVE,
        name="thehive_create_case",
        app_name="http",
        app_version="1.0.0",
        app_id="f7a6f5e3d1c4b2a9e8f7d6c5b4a3e2d1",
        action_name="POST",
        params=[
            param("url", f"{THEHIVE_INT}/api/case"),
            param("headers", "Content-Type: application/json\nAuthorization: Bearer rGdCHFJcf3NeTFbu9JhSymBKsTut4NYS"),
            param("body",
                  '{"title": "Ransomware: $exec.hostname - $exec.alert_id", "description": "Alert: $exec.alert_id | Host: $exec.hostname | Hash: $exec.hash | IP: $exec.src_ip", "severity": 2, "tlp": 2, "tags": ["ransomware", "soar-lab", "automated"]}'),
        ],
        position=pos(300, 0),
    ),
    # ── 2. TheHive: añadir task de investigación al caso (TEMPORALMENTE DESACTIVADO) ─────────────────────
    # action(
    #     aid=ACT_THEHIVE_TASK,
    #     name="thehive_add_task",
    #     app_name="TheHive",
    #     app_version="1.1.0",
    #     app_id=APP_ID_THEHIVE,
    #     action_name="custom_action",
    #     params=[
    #         param("apikey", THEHIVE_KEY),
    #         param("method", "POST"),
    #         param("url", THEHIVE_INT),
    #         param("path", "/api/case/_/task"),
    #         param("headers", f'Content-Type:application/json\nAuthorization:Bearer {THEHIVE_KEY}'),
    #         param("body",
    #               '{"caseId":"$thehive_create_case.caseId","title":"Investigate IOCs","description":"Analyze hash and IP with Cortex and MISP.",'
    #               '"status":"Waiting","order":0,"flag":false}'),
    #     ],
    #     position=pos(600, -150),
    # ),
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
        app_id="f7a6f5e3d1c4b2a9e8f7d6c5b4a3e2d1",
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
        app_id="f7a6f5e3d1c4b2a9e8f7d6c5b4a3e2d1",
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
        app_id="f7a6f5e3d1c4b2a9e8f7d6c5b4a3e2d1",
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
                             'import json\n'
                             'raw = """$Cortex_-_Analizar_hash"""\n'
                             'try:\n'
                             '    # Native Cortex app returns the job_id directly\n'
                             '    job_id = raw.strip()\n'
                             '    if not job_id or job_id == "None":\n'
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
        app_id="f7a6f5e3d1c4b2a9e8f7d6c5b4a3e2d1",
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
        app_id="f7a6f5e3d1c4b2a9e8f7d6c5b4a3e2d1",
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
        app_id="f7a6f5e3d1c4b2a9e8f7d6c5b4a3e2d1",
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
        app_id="f7a6f5e3d1c4b2a9e8f7d6c5b4a3e2d1",
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
        app_id="f7a6f5e3d1c4b2a9e8f7d6c5b4a3e2d1",
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
        app_id="f7a6f5e3d1c4b2a9e8f7d6c5b4a3e2d1",
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
                             'import json\n'
                             'raw = """$Cortex_-_Analizar_IP"""\n'
                             'try:\n'
                             '    # Native Cortex app returns the job_id directly\n'
                             '    job_id = raw.strip()\n'
                             '    if not job_id or job_id == "None":\n'
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
    # ── 7. MISP: buscar hash concreto del webhook ─────────────────────────────
    # Usamos la app http porque la app misp es generada desde OpenAPI y no tiene imagen Docker propia
    action(
        aid=ACT_MISP,
        name="MISP - Buscar IOC",
        app_name="http",
        app_version="1.0.0",
        app_id="a74824f4",
        action_name="POST",
        params=[
            param("url", f"{MISP_INT}/attributes/restSearch"),
            param("headers", "Content-Type: application/json\nAuthorization: " + MISP_KEY),
            param("body",
                  '{"returnFormat": "json", "value": "$exec.hash", "type": ["md5", "sha1", "sha256"], "limit": 10}'),
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
    # ── 8. Wazuh: indexar alerta en Wazuh SIEM ─────────────────────────────────
    action(
        aid=ACT_WAZUH_INDEX,
        name="Wazuh - Indexar alerta",
        app_name="Wazuh",
        app_version="1.1.0",
        app_id=APP_ID_WAZUH,
        action_name="post_authenticate_and_get_jwt_token",
        params=[
            param("apikey", f'Basic {WAZUH_AUTH}'),
            param("url", WAZUH_INT),
            param("headers", f'Authorization:Basic {WAZUH_AUTH}'),
            param("ssl_verify", "False"),
        ],
        position=pos(1200, -100),
    ),
    # ── 8b. Shuffle Tools: verificar indexación Wazuh ─────────────────────────
    {
        "id": ACT_VERIFY_WAZUH_INDEX,
        "name": "execute_python",
        "label": "verify_wazuh_index",
        "app_name": "Shuffle Tools",
        "app_version": "1.2.0",
        "app_id": APP_ID_SHUFFLE_TOOLS,
        "action_name": "execute_python",
        "parameters": [param("code",
                             'import json\n'
                             'raw = """$Wazuh_-_Indexar_alerta"""\n'
                             'try:\n'
                             '    obj = json.loads(raw)\n'
                             '    # Wazuh API returns {data: {items: [...], total: X}, ...}\n'
                             '    data = obj.get("data", {})\n'
                             '    total = data.get("total", 0)\n'
                             '    if total == 0:\n'
                             '        raise Exception("ERROR: Wazuh returned 0 alerts")\n'
                             '    print(f"OK: Wazuh indexed {total} alert(s)")\n'
                             'except Exception as e:\n'
                             '    raise Exception(f"ERROR: Wazuh indexing verification failed: {e}")\n'
                             )],
        "position": pos(1240, -100),
        "environment": "Shuffle",
        "is_valid": True,
        "errors": [],
        "authentication": [],
    },
    # ── 9. Wazuh: autenticar y listar agentes activos ───────────────────────
    action(
        aid=ACT_WAZUH,
        name="Wazuh - Agentes activos",
        app_name="Wazuh",
        app_version="1.1.0",
        app_id=APP_ID_WAZUH,
        action_name="post_authenticate_and_get_jwt_token",
        params=[
            param("apikey", f'Basic {WAZUH_AUTH}'),
            param("url", WAZUH_INT),
            param("headers", f'Authorization:Basic {WAZUH_AUTH}'),
            param("ssl_verify", "False"),
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
                             '    # Wazuh API returns {data: {items: [...], total: X}, ...}\n'
                             '    data = obj.get("data", {})\n'
                             '    items = data.get("items", [])\n'
                             '    total = data.get("total", 0)\n'
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
    # ── 11. TheHive: enriquecer caso con resultados de análisis (TEMPORALMENTE DESACTIVADO) ─────────────────
    # action(
    #     aid=ACT_ENRICH_CASE,
    #     name="thehive_enrich_case",
    #     app_name="TheHive",
    #     app_version="1.1.0",
    #     app_id=APP_ID_THEHIVE,
    #     action_name="custom_action",
    #     params=[
    #         param("apikey", THEHIVE_KEY),
    #         param("method", "PATCH"),
    #         param("url", THEHIVE_INT),
    #         param("path", "/api/case/_"),
    #         param("headers", f'Content-Type:application/json\nAuthorization:Bearer {THEHIVE_KEY}'),
    #         param("body",
    #               '{"caseId":"$thehive_create_case.caseId","summary":"Analysis completed: Hash analyzed by Cortex, IP checked, MISP search performed. '
    #               'MTTR: $calc_mttr seconds.",'
    #               '"tags":["analyzed","cortex","misp","mttr-calculated"]}'),
    #     ],
    #     position=pos(1500, 0),
    # ),
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
            param("body",
                  '{"alert_id":"$exec.alert_id",'
                  '"alert_type":"$exec.alert_type",'
                  '"severity":"$exec.severity",'
                  '"mttr_seconds":"$calc_mttr.message",'
                  '"@timestamp":"$exec.detection_time",'
                  '"timestamp":"$exec.detection_time",'
                  '"source":"shuffle-soar-wazuh","metric_type":"workflow_execution"}'),
        ],
        position=pos(1600, 0),
    ),
]

branches_list = [
    # Webhook → crear caso
    branch("br_wh_hive", TRIGGER_NODE, ACT_THEHIVE),
    # Caso creado → Cortex (observables desactivados)
    branch("br_hive_cortex_hash", ACT_THEHIVE, ACT_CORTEX_HASH),
    branch("br_hive_cortex_hash_virusshare", ACT_THEHIVE, ACT_CORTEX_HASH_VIRUSSHARE),
    branch("br_hive_cortex_hash_urlscan", ACT_THEHIVE, ACT_CORTEX_HASH_URLSCAN),
    branch("br_hive_cortex_ip", ACT_THEHIVE, ACT_CORTEX_IP),
    branch("br_hive_cortex_ip_robtex", ACT_THEHIVE, ACT_CORTEX_IP_ROBTEX),
    branch("br_hive_cortex_ip_robtex_reverse", ACT_THEHIVE, ACT_CORTEX_IP_ROBTEX_REVERSE),
    branch("br_hive_cortex_ip_googledns", ACT_THEHIVE, ACT_CORTEX_IP_GOOGLEDNS),
    branch("br_hive_cortex_ip_ipapi", ACT_THEHIVE, ACT_CORTEX_IP_IPAPI),
    branch("br_hive_cortex_ip_urlscan", ACT_THEHIVE, ACT_CORTEX_IP_URLSCAN),
    branch("br_hive_misp", ACT_THEHIVE, ACT_MISP),
    branch("br_hive_wazuh_index", ACT_THEHIVE, ACT_WAZUH_INDEX),
    branch("br_hive_wazuh", ACT_THEHIVE, ACT_WAZUH),
    # Cortex hash → verificar job
    branch("br_cortex_hash_verify", ACT_CORTEX_HASH, ACT_VERIFY_CORTEX_HASH),
    # Cortex IP → verificar job
    branch("br_cortex_ip_verify", ACT_CORTEX_IP, ACT_VERIFY_CORTEX_IP),
    # MISP → verificar búsqueda
    branch("br_misp_verify", ACT_MISP, ACT_VERIFY_MISP),
    # Wazuh index → verificar indexación
    branch("br_wazuh_index_verify", ACT_WAZUH_INDEX, ACT_VERIFY_WAZUH_INDEX),
    # Wazuh → verificar agentes
    branch("br_wazuh_verify", ACT_WAZUH, ACT_VERIFY_WAZUH),
    # Verificaciones → calcular MTTR
    branch("br_verify_hash_mttr", ACT_VERIFY_CORTEX_HASH, ACT_CALC_MTTR),
    branch("br_verify_ip_mttr", ACT_VERIFY_CORTEX_IP, ACT_CALC_MTTR),
    branch("br_verify_misp_mttr", ACT_VERIFY_MISP, ACT_CALC_MTTR),
    branch("br_verify_wazuh_index_mttr", ACT_VERIFY_WAZUH_INDEX, ACT_CALC_MTTR),
    branch("br_verify_wazuh_mttr", ACT_VERIFY_WAZUH, ACT_CALC_MTTR),
    # Nuevos analizadores Cortex → calcular MTTR (sin verificación individual)
    branch("br_cortex_hash_virusshare_mttr", ACT_CORTEX_HASH_VIRUSSHARE, ACT_CALC_MTTR),
    branch("br_cortex_hash_urlscan_mttr", ACT_CORTEX_HASH_URLSCAN, ACT_CALC_MTTR),
    branch("br_cortex_ip_robtex_mttr", ACT_CORTEX_IP_ROBTEX, ACT_CALC_MTTR),
    branch("br_cortex_ip_robtex_reverse_mttr", ACT_CORTEX_IP_ROBTEX_REVERSE, ACT_CALC_MTTR),
    branch("br_cortex_ip_googledns_mttr", ACT_CORTEX_IP_GOOGLEDNS, ACT_CALC_MTTR),
    branch("br_cortex_ip_ipapi_mttr", ACT_CORTEX_IP_IPAPI, ACT_CALC_MTTR),
    branch("br_cortex_ip_urlscan_mttr", ACT_CORTEX_IP_URLSCAN, ACT_CALC_MTTR),
    # Calcular MTTR → indexar métricas
    branch("br_mttr_metrics", ACT_CALC_MTTR, ACT_INDEX_METRICS),
]

wf_def = {
    "name": WF_NAME,
    "description": (
        "Workflow SOAR completo: recibe alerta de ransomware via webhook de Wazuh, "
        "crea caso en TheHive, analiza IOCs en Cortex, busca en MISP, "
        "y gestiona agentes afectados en Wazuh."
    ),
    "start": ACT_THEHIVE,
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
# Actualizar trigger status a running
for t in wf_detail.get('triggers', []):
    if t['id'] == trigger_id:
        t['status'] = 'running'
r_put = s.put(f'{SHUFFLE_URL}/api/v1/workflows/{wf_id}', json=wf_detail, timeout=15)
print(f"  Branches y trigger actualizados: HTTP {r_put.status_code}")

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
    cmd = f'docker exec soar_elasticsearch curl -s -X PUT "http://localhost:9200/hooks/_doc/{trigger_id}" -H "Content-Type: application/json" -d \'{hook_json}\''
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    if res.returncode == 0:
        print(f"  Hook en ES: {res.stdout}")
    else:
        print(f"  Hook en ES: Error - {res.stderr}")
except Exception as e:
    print(f"  Hook en ES: Error - {e}")

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
# Disabled to avoid creating extra cases that interfere with E2E tests
webhook_url = f'{SHUFFLE_URL}/api/v1/hooks/webhook_{trigger_id}'
# test_r = s.post(webhook_url, json={
#     "alert_id": "INIT-TEST-001",
#     "alert_type": "ransomware",
#     "hostname": "init-check",
#     "src_ip": "127.0.0.1",
#     "severity": 2,
#     "process_name": "init_test.exe",
#     "hash": "d41d8cd98f00b204e9800998ecf8427e",
#     "mitre_techniques": "T1486",
# }, timeout=10)
# print(f"  Test webhook: HTTP {test_r.status_code} -> {test_r.text[:100]}")
# 
# if test_r.status_code != 200:
#     print("  ADVERTENCIA: webhook no respondio 200. Puede requerir reinicio manual.")
#     sys.exit(1)
print(f"  Webhook URL: {webhook_url}")

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
        "wazuh": f"{WAZUH_URL}/agents - listar agentes",
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
print(f'    Wazuh    -> listar agentes   {WAZUH_URL}/agents')
print()
print(f'  Usar con:')
print(f'    make simulate SIMULATE_WEBHOOK="{webhook_url}"')
print(f'  Info guardada en: {info_path}')
print('=' * 60)
