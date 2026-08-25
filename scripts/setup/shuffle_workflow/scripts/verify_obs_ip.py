# Embedded script: verify_obs_ip
# Verifies that TheHive IP observable was created.
import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$thehive_obs_ip"""
try:
    obj = json.loads(raw)
    body = obj.get("body", obj)
    obs_id = body.get("id", "")
    if not obs_id:
        raise Exception("IP observable creation failed")
    print(f"OK: IP observable_id={obs_id}")
except Exception as e:
    raise Exception(f"ERROR: IP observable verification failed: {e}") from e
