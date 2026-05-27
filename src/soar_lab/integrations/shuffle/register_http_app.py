import json
import requests
import uuid

ES = 'http://localhost:9201'

# Create HTTP app with correct actions
http_app = {
    'id': str(uuid.uuid4()),
    'name': 'HTTP',
    'app_version': '1.0.0',
    'description': 'HTTP app for REST calls',
    'is_valid': True,
    'generated': False,
    'actions': [
        {'name': 'GET', 'description': 'HTTP GET request', 'parameters': []},
        {'name': 'POST', 'description': 'HTTP POST request', 'parameters': []},
        {'name': 'PUT', 'description': 'HTTP PUT request', 'parameters': []},
        {'name': 'DELETE', 'description': 'HTTP DELETE request', 'parameters': []},
    ],
}

# Delete existing HTTP apps
r = requests.post(f'{ES}/workflowapp-000001/_delete_by_query', json={'query': {'match': {'name': 'HTTP'}}}, timeout=10)
print(f'Deleted existing HTTP apps: {r.json().get("deleted", 0)}')

# Register HTTP app
r = requests.post(f'{ES}/workflowapp-000001/_doc', json=http_app, timeout=10)
print(f'Registered HTTP app: {r.status_code}')
