# Embedded script: verify_cortex_ip
# Verifies the Cortex IP job response (non-critical).
import ast
import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$cortex_ip"""
try:
    raw = raw.strip()
    try:
        obj = json.loads(raw)
    except Exception:
        obj = ast.literal_eval(raw)
    if not isinstance(obj, dict):
        raise Exception("Cortex IP response is not a dict")
    body = obj.get("body", obj)
    job_id = body.get("id") or body.get("_id") or body.get("jobId")
    status = body.get("status") or obj.get("status", "unknown")
    if not job_id:
        logger.warning(f"WARN: Cortex IP job did not return a job id (status={status})")
    else:
        print(f"OK: cortex_ip_job_id={job_id}")
except Exception as e:
    logger.warning(f"WARN: Cortex IP verification failed (non-critical): {e}")
