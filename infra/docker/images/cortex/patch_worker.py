#!/usr/bin/env python3
"""Patch cortexutils/worker.py to fall back to /job/input/input.json when stdin fails.

Also patches Robtex analyzer (if present) to use a browser User-Agent
instead of the default python-requests UA, which Cloudflare blocks with
HTTP 403.
"""
import os
import cortexutils.worker

wf = cortexutils.worker.__file__
with open(wf) as f:
    src = f.read()

# The original code (16 spaces indent):
#             if not sys.stdin.isatty():
#                 self._input = json.load(sys.stdin)
#
# Replace with try/except that falls back to /job/input/input.json

old = "self._input = json.load(sys.stdin)"
new = (
    "try:\n"
    "                    self._input = json.load(sys.stdin)\n"
    "                except Exception:\n"
    "                    import os as _os\n"
    "                    if _os.path.exists('/job/input/input.json'):\n"
    "                        with open('/job/input/input.json') as _f:\n"
    "                            self._input = json.load(_f)\n"
    "                    else:\n"
    "                        self.error('Input file does not exist')"
)

if old in src:
    src = src.replace(old, new, 1)
    with open(wf, "w") as f:
        f.write(src)
    print("Patched %s" % wf)
else:
    print("WARNING: pattern not found in %s" % wf)

# --- Patch Robtex analyzer to use a browser User-Agent ---
# Cloudflare blocks the default python-requests User-Agent with HTTP 403.
# This patch replaces bare requests.get() calls with ones that include
# a browser User-Agent header.
robtex_paths = [
    "/worker/Robtex/robtex.py",
]
robtex_ua_patch = '''
# --- BEGIN User-Agent patch (Cloudflare blocks python-requests UA) ---
import requests as _req
_orig_get = _req.get
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
def _patched_get(url, **kwargs):
    headers = kwargs.pop("headers", {})
    if "User-Agent" not in headers:
        headers["User-Agent"] = _BROWSER_UA
    if "Accept" not in headers:
        headers["Accept"] = "application/json, text/plain, */*"
    kwargs["headers"] = headers
    if "timeout" not in kwargs:
        kwargs["timeout"] = 30
    return _orig_get(url, **kwargs)
_req.get = _patched_get
# --- END User-Agent patch ---
'''

for rp in robtex_paths:
    if os.path.exists(rp):
        with open(rp) as f:
            rsrc = f.read()
        if "BEGIN User-Agent patch" not in rsrc:
            rsrc = robtex_ua_patch + "\n" + rsrc
            with open(rp, "w") as f:
                f.write(rsrc)
            print("Patched Robtex UA in %s" % rp)
        else:
            print("Robtex UA already patched in %s" % rp)
    else:
        print("No Robtex analyzer at %s (skipping)" % rp)
