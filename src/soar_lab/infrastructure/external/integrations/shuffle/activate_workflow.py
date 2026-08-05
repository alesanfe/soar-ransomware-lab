import json
import os
import requests

ES = 'http://localhost:9201'
WF_ID = '21d7822d-aad1-41e4-9c26-f2122e4857d9'

# Get artifacts directory (absolute path)
script_dir = os.path.dirname(os.path.abspath(__file__))
artifacts_dir = os.path.join(script_dir, '../../../../artifacts')
artifacts_dir = os.path.abspath(artifacts_dir)

# Get workflow
r = requests.get(f'{ES}/workflow-000001/_doc/{WF_ID}', timeout=10)
src = r.json()['_source']

# Change status to active
src['status'] = 'active'

# Update workflow
r = requests.put(f'{ES}/workflow-000001/_doc/{WF_ID}', json=src, timeout=10)
print(f'Updated workflow status to active: {r.status_code}')

# Get triggers
triggers = src.get('triggers', [])
print(f'Triggers: {len(triggers)}')
for t in triggers:
    if t.get('app_name') == 'Shuffle' and t.get('action_name') == 'webhook':
        print(f"Webhook trigger ID: {t['id']}")

# Save info
with open(os.path.join(artifacts_dir, 'workflow_info.json'), 'w') as f:
    json.dump({'workflow_id': WF_ID, 'trigger_id': triggers[0]['id'] if triggers else None}, f, indent=2)
print('Saved workflow info')
