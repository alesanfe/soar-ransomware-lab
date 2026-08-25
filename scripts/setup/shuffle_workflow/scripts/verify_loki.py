# Embedded script: verify_loki
# Verifies the Loki search response (non-critical).
import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$loki_search"""
try:
    obj = json.loads(raw)
    data = obj.get("data", {})
    if isinstance(data, dict):
        result = data.get("result", [])
    else:
        result = []
    print(f"OK: Loki found {len(result)} log entries")
except Exception as e:
    logger.warning(f"WARN: Loki search failed (non-critical): {e}")
