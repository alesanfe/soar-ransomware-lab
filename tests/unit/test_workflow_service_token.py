"""BUG-067 regression: the Shuffle workflow's containment action must carry
the service token *baked into* its embedded script.

Spawned Shuffle workers do NOT inherit ``INTERNAL_SERVICE_TOKEN`` — the
script's ``os.environ.get`` lookup inside the worker returns empty, so once
``API_REQUIRE_AUTH=true`` the ``/api/v1/contain`` call would answer 401 and
the malicious branch silently loses containment. The fix bakes the token
into the generated workflow, the same convention ``THEHIVE_KEY`` already
uses in ``mark_false_positive`` (``workflow_actions.py``).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.setup.shuffle_workflow import config, workflow_actions

SCRIPTS = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "setup"
    / "shuffle_workflow"
    / "scripts"
)


def _ctx() -> workflow_actions.WorkflowContext:
    return workflow_actions.WorkflowContext(
        thehive_key="hive",
        cortex_key="ctx",
        misp_key="misp",
        app_id_http="http",
        app_id_shuffle_tools="tools",
        cortex_basic="Y3R4",
        es_basic="ZXM=",
    )


def _containment_code(actions: list[dict]) -> str:
    for a in actions:
        if a.get("id") == workflow_actions.ACT_CONTAINMENT:
            return a["parameters"][0]["value"]
    raise AssertionError("act_containment action not found in workflow")


class TestServiceTokenPlaceholder:
    def test_template_declares_placeholder(self):
        src = (SCRIPTS / "containment.py").read_text(encoding="utf-8")
        assert "__SERVICE_TOKEN__" in src, (
            "containment.py has no __SERVICE_TOKEN__ placeholder — the "
            "workflow generator cannot bake the token in"
        )

    def test_placeholder_falls_back_to_env(self):
        """Old workflows (unbaked placeholder) must still work via env, and
        an unsubstituted placeholder must resolve to no-token, not a literal
        fake token that would 401."""
        src = (SCRIPTS / "containment.py").read_text(encoding="utf-8")
        assert '"__SERVICE_TOKEN__"' in src or "'__SERVICE_TOKEN__'" in src
        assert (
            'startswith("__")' in src
        ), "no guard against an unsubstituted placeholder leaking as the token"

    def test_build_actions_bakes_token(self):
        actions = workflow_actions.build_actions(_ctx())
        code = _containment_code(actions)
        assert (
            "__SERVICE_TOKEN__" not in code
        ), "containment script still contains the unsubstituted placeholder"
        assert (
            config.INTERNAL_SERVICE_TOKEN in code
        ), "INTERNAL_SERVICE_TOKEN was not baked into the containment script"

    def test_baked_token_reaches_header(self):
        actions = workflow_actions.build_actions(_ctx())
        code = _containment_code(actions)
        assert "X-Service-Token" in code
