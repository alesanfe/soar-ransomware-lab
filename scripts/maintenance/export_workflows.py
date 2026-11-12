#!/usr/bin/env python3
"""Export Shuffle workflows to versioned JSON playbooks (IR2).

The SOAR playbooks currently live only inside Shuffle — a reset wipes
them and changes are unreviewable. This script pulls every workflow
definition through the Shuffle API and writes one deterministic JSON
file per workflow under ``playbooks/``, making the playbooks
GitOps-able: diffs in review, restore via re-import, audit trail in git.

Usage:
    python scripts/maintenance/export_workflows.py [--out playbooks]
    python scripts/maintenance/export_workflows.py --dry-run
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from soar_lab.config.logging import get_logger
from soar_lab.config.settings import create_settings
from soar_lab.infrastructure.integrations.shuffle.client import ShuffleClient

logger = get_logger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_SECRET_NAME_RE = re.compile(r"(TOKEN|SECRET|PASSWORD|PASSWD|PASS|API_?KEY|SIGNING_KEY)")


def _slug(name: str) -> str:
    return _SLUG_RE.sub("-", str(name).lower()).strip("-") or "unnamed"


def _secret_placeholders() -> dict[str, str]:
    """Map live secret values -> ``__VAR__`` placeholders.

    Workflows carry real credentials in action headers (``X-Service-Token``,
    ``Authorization`` …).  Exported playbooks are Git-tracked, so the live
    values must never be written — replace each env-provided secret with a
    deterministic placeholder that a re-import substitutes back.
    """
    out: dict[str, str] = {}
    for key, val in os.environ.items():
        if _SECRET_NAME_RE.search(key) and isinstance(val, str) and len(val) >= 16:
            out[val] = f"__{key}__"
    return out


def _scrub(text: str, secrets: dict[str, str]) -> str:
    for val, placeholder in sorted(secrets.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(val, placeholder)
    return text


def export_workflows(client: ShuffleClient, out_dir: Path, dry_run: bool = False) -> dict:
    """Dump each Shuffle workflow to ``<slug>-<id8>.json`` in out_dir."""
    workflows = client.list_workflows()
    secrets = _secret_placeholders()
    written: list[str] = []
    skipped: list[str] = []
    for wf in workflows:
        if not isinstance(wf, dict):
            continue
        wf_id = wf.get("id") or wf.get("workflow_id")
        name = wf.get("name") or "unnamed"
        if not wf_id:
            skipped.append(str(name))
            continue
        detail = client.get_workflow(str(wf_id))
        filename = f"{_slug(name)}-{str(wf_id)[:8]}.json"
        if dry_run:
            logger.info("[dry-run] would write playbooks/%s", filename)
            written.append(filename)
            continue
        payload = _scrub(
            json.dumps(detail, indent=2, sort_keys=True, default=str) + "\n",
            secrets,
        )
        (out_dir / filename).write_text(payload, encoding="utf-8")
        written.append(filename)
    return {"exported": len(written), "skipped": skipped, "files": written}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="playbooks", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="List without writing")
    args = parser.parse_args()

    settings = create_settings()
    client = ShuffleClient(
        base_url=settings.get("shuffle_url"),
        api_key=settings.get("shuffle_api_key"),
        config_provider=settings,
    )
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = export_workflows(client, out_dir, dry_run=args.dry_run)
    except Exception as e:
        logger.error("Workflow export failed: %s", e)
        return 1
    logger.info(
        "Exported %s workflow(s) to %s (%s skipped)",
        result["exported"],
        out_dir,
        len(result["skipped"]),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
