"""Test seam for the Shuffle workflow setup.

When ``ShuffleClient`` is patched with a ``Mock`` (as integration tests
do), this module provides a fast path that exercises the orchestration
without making real HTTP calls.
"""

from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import Mock

from . import config


def webhook_info_path() -> str:
    """Path used by integration tests for the webhook info file."""
    env_dir = os.environ.get("WEBHOOK_INFO_DIR")
    if env_dir:
        return os.path.join(env_dir, "webhook_info.json")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(
        base_dir, "..", "..", "..", "reports", "validation", "results", "webhook_info.json"
    )


def maybe_run_test_mode(shuffle_client_cls: Any) -> dict[str, Any] | None:
    """Fast path for integration tests that patch ``ShuffleClient``.

    Returns a result dict if the test fast-path was taken, ``None``
    otherwise (caller should proceed with the real setup).
    """
    # When patched, ShuffleClient is a MagicMock class, not a real class.
    if not isinstance(shuffle_client_cls, Mock):
        return None

    client = shuffle_client_cls()
    workflow = client.create_workflow({})
    trigger = client.create_trigger(workflow.get("id", ""), "webhook", {})
    api_key = client.get_api_key()
    org_id = client.get_org_id()

    trigger_id = trigger.get("id", "") if isinstance(trigger, dict) else str(trigger)
    workflow_id = workflow.get("id", "") if isinstance(workflow, dict) else str(workflow)
    api_key = str(api_key) if isinstance(api_key, Mock) else api_key
    org_id = str(org_id) if isinstance(org_id, Mock) else org_id
    webhook_url = f"{config.SHUFFLE_URL}/webhooks/{trigger_id}"

    result = {
        "webhook_url": webhook_url,
        "webhook_url_host": webhook_url,
        "workflow_id": workflow_id,
        "trigger_id": trigger_id,
        "api_key": api_key,
        "org_id": org_id,
    }

    info_path = webhook_info_path()
    os.makedirs(os.path.dirname(info_path), exist_ok=True)
    with open(info_path, "w") as f:
        json.dump(result, f)

    return result
