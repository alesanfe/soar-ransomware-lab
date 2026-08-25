#!/usr/bin/env python3
"""Rebuild all analyzer images with the stdin patch."""
import subprocess
import os
import sys

images = [
    "ghcr.io/thehive-project/abuse_finder:3",
    "ghcr.io/thehive-project/validateobservable:1",
    "ghcr.io/thehive-project/robtex_ip_query:1",
    "ghcr.io/thehive-project/robtex_reverse_pdns_query:1",
    "ghcr.io/thehive-project/hashdd_status:2",
    "ghcr.io/thehive-project/googledns_resolve:1",
    "ghcr.io/thehive-project/dns_lookingglass:1",
    "ghcr.io/thehive-project/crt_sh_transparency_logs:1",
    "ghcr.io/thehive-project/stopforumspam:1",
    "ghcr.io/thehive-project/lookyloo_screenshot:1",
    "ghcr.io/thehive-project/unshortenlink:1",
    "ghcr.io/thehive-project/virusshare:2",
]

patch_dir = os.path.dirname(os.path.abspath(__file__))
dockerfile = os.path.join(patch_dir, "analyzer-patch.Dockerfile")

for img in images:
    # Build directly with the original tag
    r = subprocess.run(
        ["docker", "build", "--no-cache", "--build-arg", f"ANALYZER_IMAGE={img}",
         "-f", dockerfile, "-t", img, patch_dir],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"FAIL: {img}: {r.stderr[:200]}")
        continue

    # Verify the patch is installed
    r2 = subprocess.run(
        ["docker", "run", "--rm", "--entrypoint", "python", img, "-c",
         "import cortexutils.worker; f=cortexutils.worker.__file__; print('OK' if '/job/input/input.json' in open(f).read() else 'MISSING')"],
        capture_output=True, text=True
    )
    if "OK" in r2.stdout:
        print(f"OK: {img}")
    else:
        print(f"PATCH MISSING: {img}: {r2.stdout} {r2.stderr[:100]}")
