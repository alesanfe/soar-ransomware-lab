import json
import os
import requests
import uuid
from pathlib import Path

SH = 'http://localhost:5001'
ES = 'http://localhost:9201'
SHUFFLE_PASSWORD = os.environ.get('SHUFFLE_DEFAULT_PASSWORD') or os.environ.get('SHUFFLE_PASS', '')
if not SHUFFLE_PASSWORD:
    print('Error: SHUFFLE_DEFAULT_PASSWORD not set')
    exit(1)

# Login
s = requests.Session()
r = s.post(f'{SH}/api/v1/users/login', json={'username': 'admin', 'password': SHUFFLE_PASSWORD},
           timeout=10)
print('Login:', r.status_code)

# Get org
r = s.get(f'{SH}/api/v1/orgs', timeout=10)
org_id = r.json()[0]['id']
print('Org ID:', org_id)

# Create simple workflow with HTTP app using POST action
wf_id = str(uuid.uuid4())
trigger_id = str(uuid.uuid4())
action_id = str(uuid.uuid4())

wf = {
    'id': wf_id,
    'name': 'Simple HTTP Test',
    'description': 'Simple workflow to test HTTP app with POST action',
    'org_id': org_id,
    'environment': 'Shuffle',
    'status': 'active',
    'actions': [
        {
            'id': action_id,
            'name': 'HTTP POST Test',
            'app_name': 'HTTP',
            'app_version': '1.0.0',
            'action_name': 'POST',
            'environment': 'Shuffle',
            'is_valid': True,
            'errors': [],
            'authentication': [],
            'position': {'x': 300, 'y': 0},
            'parameters': [
                {'name': 'url', 'value': 'http://httpbin.org/post'},
                {'name': 'headers', 'value': json.dumps({'Content-Type': 'application/json'})},
                {'name': 'body', 'value': json.dumps({'test': 'data'})},
            ],
        }
    ],
    'triggers': [
        {
            'id': trigger_id,
            'name': 'Webhook',
            'app_name': 'Shuffle',
            'app_version': '1.0.0',
            'action_name': 'webhook',
            'environment': 'Shuffle',
            'is_valid': True,
            'position': {'x': 100, 'y': 0},
        }
    ],
    'branches': [
        {
            'id': str(uuid.uuid4()),
            'source_id': trigger_id,
            'destination_id': action_id,
            'condition': {},
        }
    ],
}
r = s.post(f'{SH}/api/v1/workflows', json=wf, timeout=10)
print('Create workflow:', r.status_code)
if r.status_code != 200:
    print('Error:', r.text)
    exit(1)
print('Workflow created:', r.json())

# Get webhook URL
r = s.get(f'{SH}/api/v1/workflows/{wf_id}/triggers', timeout=10)
print('Triggers response status:', r.status_code)
print('Triggers response text:', r.text[:500])
triggers = r.json() if r.status_code == 200 else []
webhook_url = None
for t in triggers:
    if t.get('app_name') == 'Shuffle' and t.get('action_name') == 'webhook':
        webhook_url = t.get('webhook_url')
        print('Webhook URL:', webhook_url)
        break

# Save info - use Path to resolve artifacts directory
script_dir = Path(__file__).parent
artifacts_dir = script_dir.parent.parent.parent.parent / 'artifacts'
artifacts_dir.mkdir(parents=True, exist_ok=True)
output_file = artifacts_dir / 'simple_workflow_info.json'

with open(output_file, 'w') as f:
    json.dump({'workflow_id': wf_id, 'webhook_url': webhook_url, 'trigger_id': trigger_id}, f, indent=2)
print(f'Saved workflow info to: {output_file}')
