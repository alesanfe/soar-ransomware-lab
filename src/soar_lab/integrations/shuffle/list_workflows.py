import requests

ES = 'http://localhost:9201'
r = requests.get(f'{ES}/workflow-000001/_search?size=10', timeout=10)
for h in r.json()['hits']['hits']:
    src = h['_source']
    print(f"{src['name']} (status={src['status']}) - {len(src.get('actions', []))} actions")
