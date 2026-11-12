#!/usr/bin/env python3
"""Refresh MISP taxonomies, galaxies and warninglists from upstream.

MISP-EVAL-014: taxonomies/galaxies ship pinned to the image version;
this job pulls the upstream updates exposed by the MISP REST API
(``/taxonomies/update``, ``/galaxies/update``, ``/warninglists/update``)
so the lab's CTI classification data does not silently go stale.

Requires the **admin** key — these are admin-scoped endpoints, so the
script uses ``MISP_API_KEY`` (not the Publisher automation key).

Usage (inside ``soar_api`` or any host with reachability to MISP):

    python scripts/maintenance/misp_update_taxonomies.py

Environment:
    MISP_URL      - base URL (default https://misp)
    MISP_API_KEY  - admin authkey
    MISP_CA       - CA bundle path (default /app/certs/ca.crt, falls back
                    to infra/docker/config/certs/ca.crt for host runs)
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

MISP_URL = os.environ.get("MISP_URL", "https://misp").rstrip("/")
KEY = os.environ.get("MISP_API_KEY", "")
_CA_CANDIDATES = [
    os.environ.get("MISP_CA", ""),
    "/app/certs/ca.crt",
    str(Path(__file__).resolve().parents[2] / "infra" / "docker" / "config" / "certs" / "ca.crt"),
]

ENDPOINTS = (
    ("taxonomies", "/taxonomies/update"),
    ("galaxies", "/galaxies/update"),
    ("warninglists", "/warninglists/update"),
)


def _ca() -> str | None:
    return next((c for c in _CA_CANDIDATES if c and Path(c).is_file()), None)


def main() -> int:
    if not KEY:
        print("MISP_API_KEY is required (admin authkey)", file=sys.stderr)
        return 2
    ctx = ssl.create_default_context(cafile=_ca())
    headers = {
        "Authorization": KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    failed = False
    for name, path in ENDPOINTS:
        req = urllib.request.Request(MISP_URL + path, data=b"{}", method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
                body = json.loads(resp.read() or b"{}")
                print(f"{name}: HTTP {resp.status} — {body.get('message', body)}")
        except urllib.error.HTTPError as exc:
            print(f"{name}: HTTP {exc.code} — {exc.read()[:200]!r}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
