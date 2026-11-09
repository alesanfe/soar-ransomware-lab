# Embedded script: verify_task
# Verifies that TheHive task was created.
"""Shuffle node: confirm the investigation task was created."""

import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$thehive_add_task"""
try:
    obj = json.loads(raw)
    body = obj.get("body", obj)
    # TheHive 5 returns _id (TheHive 3 used id)
    task_id = body.get("_id") or body.get("id", "")
    if not task_id:
        raise Exception("task creation failed - no task_id returned")
    print(f"OK: task_id={task_id}")
except Exception as e:
    raise Exception(f"ERROR: task verification failed: {e}") from e
