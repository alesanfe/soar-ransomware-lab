# Embedded script: verify_obs_ip
# Verifies that TheHive IP observable was created.
"""Shuffle node: confirm the IP observable registered."""

import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$thehive_obs_ip"""
try:
    obj = json.loads(raw)
    body = obj.get("body", obj)
    # TH5 observable POST returns a list of created observables.
    if isinstance(body, list) and body:
        body = body[0]
    obs_id = body.get("_id") or body.get("id", "")
    if not obs_id:
        raise Exception("IP observable creation failed")
    print(f"OK: IP observable_id={obs_id}")
except Exception as e:
    raise Exception(f"ERROR: IP observable verification failed: {e}") from e
