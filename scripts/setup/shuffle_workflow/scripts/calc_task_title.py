# Embedded script: calc_task_title
# Calculates a conditional task title based on severity.
import json
import logging

logger = logging.getLogger(__name__)

norm_raw = r"""$normalize_inputs.message"""
try:
    _norm = json.loads(norm_raw)
except Exception:
    _norm = {}
severity_raw = str(_norm.get("severity", ""))
try:
    severity = int(float(severity_raw.strip()))
except Exception:
    severity = 2
if severity >= 3:
    title = "Isolate infected host, collect evidence and analyze IOCs"
else:
    title = "Investigate, collect and analyze IOCs, preserve evidence"
print(title)
