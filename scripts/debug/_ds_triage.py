"""Debug helper: triage dataset/defect samples (dev-only)."""

import json
import subprocess

out = subprocess.run(
    ["python3", "-m", "detect_secrets", "scan", "src/"],
    capture_output=True, text=True,
).stdout
d = json.loads(out)
for fn, items in d["results"].items():
    for it in items:
        src = open(fn, encoding="utf8").read().split("\n")[it["line_number"] - 1].strip()
        print(f'{it["type"]:28} {fn}:{it["line_number"]}')
        print(f'    {src[:110]}')
