import json
import requests

ES = 'http://localhost:9201'
WF_ID = '21d7822d-aad1-41e4-9c26-f2122e4857d9'

# Get workflow
r = requests.get(f'{ES}/workflow-000001/_doc/{WF_ID}', timeout=10)
src = r.json()['_source']

# Fix actions to use TheHive app instead of HTTP
for a in src.get('actions', []):
    if a.get('app_name') == 'HTTP':
        # Change app_name to TheHive
        a['app_name'] = 'TheHive'
        # Use standard TheHive API action names
        if 'TheHive - Crear Caso' in a.get('name', ''):
            a['action_name'] = 'create_case'
        elif 'MISP - Buscar IOC' in a.get('name', ''):
            a['action_name'] = 'create_alert'
        elif 'Elasticsearch - Indexar Alerta' in a.get('name', ''):
            a['app_name'] = 'Elasticsearch'
            a['action_name'] = 'create_index'
        a['is_valid'] = True

# Update workflow
r = requests.put(f'{ES}/workflow-000001/_doc/{WF_ID}', json=src, timeout=10)
print(f'Fixed workflow to use TheHive app: {r.status_code}')

# Show fixed actions
for a in src.get('actions', []):
    print(f"  {a['name']}: app={a.get('app_name')}, action_name={a.get('action_name')}, is_valid={a.get('is_valid')}")
