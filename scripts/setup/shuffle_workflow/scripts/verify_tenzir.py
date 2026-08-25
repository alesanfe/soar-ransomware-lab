# Embedded script: verify_tenzir
# Verifies the Tenzir analysis response (non-critical).
import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$tenzir_serve"""
try:
    obj = json.loads(raw)
    body = obj.get("body", obj)
    if isinstance(body, str):
        body = json.loads(body)
    events = body.get("events", [])
    print(f"OK: Tenzir found {len(events)} network events")
except Exception as e:
    logger.warning(f"WARN: Tenzir analysis failed (non-critical): {e}")
