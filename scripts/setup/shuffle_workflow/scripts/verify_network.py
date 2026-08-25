# Embedded script: verify_network
# Verifies the Network Watcher response (non-critical).
import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$network_watch"""
try:
    obj = json.loads(raw)
    connections = obj.get("connections", [])
    print(f"OK: Network Watcher found {len(connections)} connections")
except Exception as e:
    logger.warning(f"WARN: Network monitoring failed (non-critical): {e}")
