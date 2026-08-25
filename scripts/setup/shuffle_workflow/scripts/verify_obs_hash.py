# Embedded script: verify_obs_hash
# Verifies that TheHive hash observable was created.
import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$thehive_obs_hash"""
try:
    obj = json.loads(raw)
    body = obj.get("body", obj)
    obs_id = body.get("id", "")
    if not obs_id:
        raise Exception("hash observable creation failed")
    print(f"OK: hash observable_id={obs_id}")
except Exception as e:
    raise Exception(f"ERROR: hash observable verification failed: {e}") from e
