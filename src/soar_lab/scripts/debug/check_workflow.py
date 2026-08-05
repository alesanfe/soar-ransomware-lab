import json
import requests
import urllib3

urllib3.disable_warnings()
with open('/app/results/webhook_info.json') as f:
    info = json.load(f)
api_key = info.get('shuffle_api_key')
url = f"http://soar_shuffle_backend:5001/api/v1/workflows/{info.get('workflow_id')}"
r = requests.get(url, headers={'Authorization': f'Bearer {api_key}'}, verify=False)
if r.status_code == 200:
    data = r.json()
    actions = data.get('actions', [])
    print(f'Total actions: {len(actions)}')
    for a in actions:
        label = a.get('label', '')
        if 'network' in label.lower() or 'watcher' in label.lower():
            print(f'Label: {label}')
