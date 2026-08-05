import docker
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
TRIGGER_ID = info['trigger_id']

# Register webhook in Elasticsearch
requests.delete(f'{ES}/hooks', timeout=10)
requests.put(f'{ES}/hooks/_doc/{TRIGGER_ID}', json={
    'id': TRIGGER_ID,
    'start': WF_ID,
    'type': 'webhook',
    'owner': '',
    'status': 'running',
    'workflows': [WF_ID],
    'running': True,
    'org_id': 'b4fa04e8-6de3-45f1-920e-721b522a0eba',
    'environment': 'Shuffle',
    'info': {},
    'actions': []
}, timeout=10)
print('Webhook registered in ES')

# Send test alert
tr = requests.post(f'{SH}/api/v1/hooks/webhook_{TRIGGER_ID}', json={
    'alert_id': 'NET-TEST-001',
    'hostname': 'dc-001',
    'src_ip': '185.220.101.182',
    'severity': 3,
    'event_type': 'ransomware_detection',
    'description': 'Networking test - SHUFFLE_DEFAULT_NETWORK_ATTACH verification',
    'process_name': 'ransomware.exe',
    'hash': '44d88612fea8a8f36de82e1278abb02f',
    'mitre_techniques': ['T1486']
}, timeout=10)
print(f'Webhook sent: {tr.status_code}')
print(f'Execution ID: {tr.json().get("execution_id")}')

# Wait and check worker network
cli = docker.from_env()
for _ in range(30):
    time.sleep(1)
    workers = [c for c in cli.containers.list(all=True) if c.name.startswith('worker-')]
    if workers:
        w = workers[0]
        nets = list(w.attrs['NetworkSettings']['Networks'].keys())
        net_mode = w.attrs['HostConfig']['NetworkMode']
        print(f'Worker: {w.name}')
        print(f'  NetworkMode: {net_mode}')
        print(f'  Networks: {nets}')
        if 'soar_soar_net' in nets:
            print('  OK: Worker is on soar_soar_net - networking solution WORKS!')
        else:
            print('  FAIL: Worker is NOT on soar_soar_net')
        break
