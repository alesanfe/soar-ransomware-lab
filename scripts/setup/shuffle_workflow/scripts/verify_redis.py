# Embedded script: verify_redis
# Verifies the Redis cache response (non-critical).
import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$redis_cache"""
try:
    obj = json.loads(raw)
    body = obj.get("body", obj)
    if isinstance(body, str):
        body = json.loads(body)
    if body.get("success"):
        print("OK: Redis cache updated")
    else:
        logger.warning(f"WARN: Redis cache issue: {body.get('message', body)}")
except Exception as e:
    logger.warning(f"WARN: Redis cache failed (non-critical): {e}")
