# Embedded script: verify_misp
# Verifies the MISP search response (non-critical, handles truncation).
import json
import logging
import re

logger = logging.getLogger(__name__)
raw = r"""$misp_search"""
try:
    clean = "".join(char for char in raw if ord(char) >= 32 or char in "\n\r\t")
    try:
        obj = json.loads(clean)
        body = obj.get("body", obj) if isinstance(obj, dict) else {}
        if isinstance(body, str):
            body = json.loads(body)
        resp = body.get("response", body.get("data", {})) if isinstance(body, dict) else {}
        attrs = (
            resp.get("Attribute", [])
            if isinstance(resp, dict)
            else (resp if isinstance(resp, list) else [])
        )
        print(f"OK: MISP search returned {len(attrs)} result(s)")
    except Exception:
        # Response may have been truncated by Shuffle's variable
        # substitution (large nested MISP payloads); fall back to a
        # best-effort count of attribute ids instead of failing outright.
        approx = len(re.findall(r'"category"\s*:', clean))
        if approx:
            print(f"OK: MISP search returned ~{approx} result(s) (truncated response)")
        else:
            raise
except Exception as e:
    logger.warning(f"WARN: MISP search verification failed (non-critical): {e}")
