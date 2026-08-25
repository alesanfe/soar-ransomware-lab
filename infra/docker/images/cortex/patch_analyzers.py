#!/usr/bin/env python3
"""
Patch analyzer Docker images to fix stdin issue on Docker Desktop (WSL2).

Uses docker build with a Dockerfile that extends each analyzer image and
adds a PYTHONSTARTUP patch.
"""

import subprocess
import sys
import os

ANALYZER_IMAGES = [
    "ghcr.io/thehive-project/abuse_finder:3",
    "ghcr.io/thehive-project/validateobservable:1",
    "ghcr.io/thehive-project/robtex_ip_query:1",
    "ghcr.io/thehive-project/robtex_reverse_pdns_query:1",
    "ghcr.io/thehive-project/robtex_forward_pdns_query:1",
    "ghcr.io/thehive-project/hashdd_status:2",
    "ghcr.io/thehive-project/googledns_resolve:1",
    "ghcr.io/thehive-project/dns_lookingglass:1",
    "ghcr.io/thehive-project/crt_sh_transparency_logs:1",
    "ghcr.io/thehive-project/stopforumspam:1",
    "ghcr.io/thehive-project/lookyloo_screenshot:1",
    "ghcr.io/thehive-project/unshortenlink:1",
    "ghcr.io/thehive-project/virusshare:2",
]

PATCH_DIR = os.path.dirname(os.path.abspath(__file__))
DOCKERFILE = os.path.join(PATCH_DIR, "analyzer-patch.Dockerfile")
PATCH_FILE = os.path.join(PATCH_DIR, "stdin_patch.py")

def run(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"  ERROR: {' '.join(cmd)}")
        if result.stderr:
            print(f"  stderr: {result.stderr[:300]}")
        return None
    return result

def patch_image(image):
    print(f"\n=== Patching {image} ===")
    
    # Build a patched image using the Dockerfile
    # Use a temporary tag first, then retag to overwrite the original
    tmp_tag = f"patched-{image.replace('/', '-').replace(':', '-')}"
    
    result = run([
        "docker", "build",
        "--build-arg", f"ANALYZER_IMAGE={image}",
        "-f", DOCKERFILE,
        "-t", tmp_tag,
        PATCH_DIR,
    ], check=False)
    
    if not result or result.returncode != 0:
        print(f"  Failed to build patched image")
        return False
    
    # Retag to overwrite the original image
    result = run(["docker", "tag", tmp_tag, image], check=False)
    if not result or result.returncode != 0:
        print(f"  Failed to retag")
        return False
    
    # Remove the temporary tag
    run(["docker", "rmi", tmp_tag], check=False)
    
    print(f"  OK - Patched successfully")
    return True

def main():
    if not os.path.exists(PATCH_FILE):
        print(f"ERROR: Patch file not found: {PATCH_FILE}")
        sys.exit(1)
    
    if not os.path.exists(DOCKERFILE):
        print(f"ERROR: Dockerfile not found: {DOCKERFILE}")
        sys.exit(1)
    
    print(f"Patch dir: {PATCH_DIR}")
    print(f"Images to patch: {len(ANALYZER_IMAGES)}")
    
    success = 0
    failed = 0
    for image in ANALYZER_IMAGES:
        if patch_image(image):
            success += 1
        else:
            failed += 1
    
    print(f"\n=== Results ===")
    print(f"Patched: {success}/{len(ANALYZER_IMAGES)}")
    print(f"Failed: {failed}/{len(ANALYZER_IMAGES)}")
    
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
