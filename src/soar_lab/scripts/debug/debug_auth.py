import json
import requests
import sys
import urllib3

urllib3.disable_warnings()
try:
    with open('/app/results/webhook_info.json') as f:
        info = json.load(f)
    print(f'webhook_info: {json.dumps(info, indent=2)}', file=sys.stderr)
    api_key = info.get('shuffle_api_key')
    print('API Key: <redacted>', file=sys.stderr)
    url = f"http://soar_shuffle_backend:5001/api/v1/workflows/{info.get('workflow_id')}"
    print(f'URL: {url}', file=sys.stderr)
    r = requests.get(url, headers={'Authorization': f'Bearer {api_key}'}, verify=False)
    print(f'Status: {r.status_code}', file=sys.stderr)
    print(f'Response: {r.text[:500]}', file=sys.stderr)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
