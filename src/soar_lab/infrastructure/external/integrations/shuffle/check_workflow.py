import json
import requests

ES = 'http://localhost:9201'
r = requests.get(f'{ES}/workflow-000001/_search?q=name:SOAR-Ransomware-Response&size=1', timeout=10)
h = r.json()['hits']['hits'][0]
src = h['_source']
wf_id = h['_id']
print(f"Workflow ID: {wf_id}")
print(f"Status: {src['status']}")
print(f"Actions: {len(src.get('actions', []))}")
for a in src.get('actions', []):
    print(
        f"  Action: {a['name']} | app: {a['app_name']} | action_name: {a.get('action_name')} | is_valid: {a.get('is_valid')}")
