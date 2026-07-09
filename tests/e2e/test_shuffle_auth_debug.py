"""Minimal debug test to isolate Shuffle Bearer auth failure inside pytest."""
import json
import os
import requests
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Use container path when running inside Docker, otherwise use host path
_info_path_container = Path('/app/src/soar_lab/infrastructure/artifacts/webhook_info.json')
_info_path_host = Path(
    __file__).resolve().parent.parent.parent / 'src' / 'soar_lab' / 'infrastructure' / 'artifacts' / 'webhook_info.json'
_info_path = _info_path_container if _info_path_container.exists() else _info_path_host
_info = json.loads(_info_path.read_text()) if _info_path.exists() else {}

WF = os.environ.get('SHUFFLE_WORKFLOW_ID', _info.get('workflow_id', ''))
KEY = os.environ.get('SHUFFLE_DEFAULT_APIKEY', 'f2a8b3c9-d4e1-5f6a-7b8c-9d0e1f2a3b4c')
ORG = os.environ.get('SHUFFLE_ORG_ID', _info.get('org_id', ''))
BASE = os.environ.get('SHUFFLE_URL', 'http://shuffle-backend:5001')


class TestShuffleAuthDebug(unittest.TestCase):

    def test_bearer_direct_fresh_session(self):
        """Fresh requests.Session with Bearer token — should be 200."""
        s = requests.Session()
        s.headers.update({
            'Authorization': f'Bearer {KEY}',
            'Connection': 'close',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Org-Id': ORG,
        })
        r = s.get(f'{BASE}/api/v1/workflows/{WF}/executions', timeout=15)
        self.assertEqual(r.status_code, 200, f"Bearer direct failed: {r.text[:80]}")

    def test_bearer_via_shuffle_client(self):
        """ShuffleClient.get_workflow_executions — should be 200."""
        from soar_lab.integrations.shuffle_client import ShuffleClient
        c = ShuffleClient(base_url=BASE, api_key=KEY, verify_ssl=False)
        print(f"\nOrg-Id header: {c._session.headers.get('Org-Id', 'NOT SET')}")
        execs = c.get_workflow_executions(WF)
        self.assertIsInstance(execs, list)
        print(f"Executions returned: {len(execs)}")

    def test_session_headers_check(self):
        """Verify what headers ShuffleClient session has after init."""
        from soar_lab.integrations.shuffle_client import ShuffleClient
        c = ShuffleClient(base_url=BASE, api_key=KEY, verify_ssl=False)
        headers = dict(c._session.headers)
        print(f"\nSession headers: {headers}")
        self.assertIn('Authorization', headers)
        self.assertIn('Bearer', headers['Authorization'])
