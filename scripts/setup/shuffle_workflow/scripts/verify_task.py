# Embedded script: verify_task
# Verifies that TheHive task was created.
import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$thehive_add_task"""
try:
    obj = json.loads(raw)
    body = obj.get("body", obj)
    task_id = body.get("id", "")
    if not task_id:
        raise Exception("task creation failed - no task_id returned")
    print(f"OK: task_id={task_id}")
except Exception as e:
    raise Exception(f"ERROR: task verification failed: {e}") from e
