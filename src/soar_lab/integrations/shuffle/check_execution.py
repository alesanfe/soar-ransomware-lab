import json
import os
import requests
import time

SH = 'http://localhost:5001'
ES = 'http://localhost:9201'

# Get artifacts directory (absolute path)
script_dir = os.path.dirname(os.path.abspath(__file__))
artifacts_dir = os.path.join(script_dir, '../../../../artifacts')
artifacts_dir = os.path.abspath(artifacts_dir)

# Load workflow info
with open(os.path.join(artifacts_dir, 'workflow_info.json')) as f:
    info = json.load(f)
WF_ID = info['workflow_id']

# Login
s = requests.Session()
s.post(f'{SH}/api/v1/users/login', json={'username': 'admin', 'password': 'R3x#7mP9$vK4@nQ2tW8!zY5&hF1sD3'}, timeout=10)

# Wait for execution to complete
time.sleep(30)

# Get executions
execs = s.get(f'{SH}/api/v1/workflows/{WF_ID}/executions', timeout=10).json()
execs = execs if isinstance(execs, list) else []
if execs:
    ex = execs[0]
    print(f'Status: {ex["status"]}')
    for res in ex.get('results', []):
        n = res.get('action', {}).get('name', '?')
        st = res.get('status', '?')
        rv = str(res.get('result', ''))[:200]
        print(f'  [{st}] {n}: {rv}')
