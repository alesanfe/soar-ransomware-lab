# Embedded script: cortex_run_guarded
# Runs a Cortex analyzer ONLY when the observable is non-empty AND valid
# for its declared data type. Empty/malformed observables previously fired
# analyzer jobs that always failed (RDAP on domain="", FileInfo on a hash)
# — TC-KPI-06 / DT-01 / H-03.
# Prints the same envelope the http app produces ({status, body}) so
# downstream parsers keep working; the shuffle-tools result wrapper adds
# {"success","message"} around stdout, which consumers unwrap in _parse.
"""Shuffle node: guarded Cortex analyzer invocation (skip on empty/invalid input)."""

import json
import logging
import re
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

# Build-time substitutions (cortex_setup.py / workflow_actions.py):
ANALYZER_NAME = "__ANAME__"
ANALYZER_URL = "__ANALYZER_URL__"
AUTH_BASIC = "__AUTH__"
DATA_TYPE = "__DTYPE__"

_HASH_RE = re.compile(
    r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$|^[a-fA-F0-9]{128}$"
)
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)([a-zA-Z0-9](-?[a-zA-Z0-9])*\.)+[a-zA-Z]{2,63}$"
)
_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


def _is_ip(v: str) -> bool:
    parts = v.split(".")
    if len(parts) == 4:
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False
    return ":" in v  # crude IPv6 accept — analyzers validate further


def _valid(dtype: str, value: str) -> bool:
    """Per-type input validation mirroring analyzer_matrix.VALIDATORS."""
    if dtype == "hash":
        return bool(_HASH_RE.match(value))
    if dtype == "ip":
        return _is_ip(value)
    if dtype == "domain":
        return bool(_DOMAIN_RE.match(value)) and not _is_ip(value)
    if dtype == "url":
        return bool(_URL_RE.match(value))
    return True  # unknown types: non-empty check already applied


def _skip(reason: str) -> None:
    print(
        json.dumps(
            {
                "status": "skipped",
                "body": {
                    "skipped": reason,
                    "analyzer": ANALYZER_NAME,
                    "dataType": DATA_TYPE,
                },
            }
        )
    )


# Shuffle interpolates $exec.<field> before executing the script.
data = r"""__FIELD_TOKEN__"""
if not isinstance(data, str):
    data = str(data or "")
data = data.strip()

if not data or data.startswith("$"):
    _skip("empty observable")
elif not _valid(DATA_TYPE, data):
    _skip(f"invalid {DATA_TYPE}: {data[:60]}")
else:
    payload = json.dumps(
        {"data": data, "attributes": {"dataType": DATA_TYPE, "tlp": 2}}
    ).encode()
    req = urllib.request.Request(
        ANALYZER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Basic " + AUTH_BASIC,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body_txt = resp.read().decode()
            try:
                body_obj = json.loads(body_txt)
            except Exception:
                body_obj = {"raw": body_txt[:4000]}
            print(json.dumps({"status": resp.status, "body": body_obj}))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode()[:2000]
        except Exception:
            pass
        logger.warning("WARN: %s HTTP %s: %s", ANALYZER_NAME, exc.code, detail)
        print(
            json.dumps(
                {
                    "status": exc.code,
                    "body": {"error": detail, "analyzer": ANALYZER_NAME},
                }
            )
        )
    except Exception as exc:
        logger.warning("WARN: %s run failed: %s", ANALYZER_NAME, exc)
        print(
            json.dumps(
                {"status": "error", "body": {"error": str(exc), "analyzer": ANALYZER_NAME}}
            )
        )
