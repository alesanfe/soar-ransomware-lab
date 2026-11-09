#!/usr/bin/env python3
"""Export the live FastAPI OpenAPI spec to the repo snapshots.

Keeps docs/api/openapi.json, docs/assets/references/openapi.json and
tests/baseline/openapi.json byte-identical (docs_quality.py gate #1).

Run inside the API container (composition imports need app settings):
    docker exec soar_api python /app/scripts/ci/export_openapi.py
or on the host with the package installed:
    python scripts/ci/export_openapi.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    ROOT / "docs" / "api" / "openapi.json",
    ROOT / "docs" / "assets" / "references" / "openapi.json",
    ROOT / "tests" / "baseline" / "openapi.json",
]


def main() -> int:
    from soar_lab.interfaces.api.composition import create_app

    spec = create_app().openapi()
    payload = json.dumps(spec, indent=2, sort_keys=True) + "\n"
    for target in TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
        print(f"wrote {target} ({len(spec['paths'])} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
