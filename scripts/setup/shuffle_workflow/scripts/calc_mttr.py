# Embedded script: calc_mttr
# Calculate MTTR from workflow start to now.
import json
import logging
import time

logger = logging.getLogger(__name__)
# Calculate MTTR from workflow start to now
# Use the webhook timestamp if available, otherwise use current time
# Use normalize_inputs to avoid shuffle_variable_error on optional field
norm_raw = r"""$normalize_inputs.message"""
norm = {}
try:
    norm = json.loads(norm_raw) if norm_raw else {}
except Exception:
    pass
webhook_timestamp = norm.get("detection_time", "")
if not webhook_timestamp:
    webhook_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
try:
    from datetime import datetime

    if "T" in webhook_timestamp:
        dt = datetime.fromisoformat(webhook_timestamp.replace("Z", "+00:00"))
        start_time = dt.timestamp()
    else:
        start_time = float(webhook_timestamp)
    mttr_seconds = time.time() - start_time
except Exception:
    mttr_seconds = 0
print(json.dumps({"mttr_seconds": round(mttr_seconds, 2)}))
