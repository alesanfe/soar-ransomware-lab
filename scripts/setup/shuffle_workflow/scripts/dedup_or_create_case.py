# Embedded script: dedup_or_create_case
# Replaces the plain thehive_create_case HTTP node — same node name so
# downstream `$thehive_create_case.message.body._id` references keep resolving.
"""Shuffle node: create the TheHive case, deduplicated by alert_id.

A retried webhook send (client timeout while the server already queued the
execution) produces a second workflow execution for the same alert. Without
dedup each execution mints its own case — observed as duplicate TheHive cases
under storm/retry conditions. Before POSTing, this node scans recent cases
for the alert_id (``alert_id:{id}`` tag or description match) and returns the
existing case instead of creating a duplicate. The check-then-create window
is not atomic, so a hit is opportunistic — it covers the retry gap where the
first case is already indexed.
"""

import json
import urllib.error
import urllib.request

THEHIVE = "__THEHIVE_INT__"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer __THEHIVE_KEY__",
}

alert_id = r"""$exec.alert_id""".strip()


def _req(method, path, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(THEHIVE + path, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
    return json.loads(raw) if raw else {}


def _find_case(needle):
    """Return (existing_case, error). error is surfaced for diagnosis."""
    if not needle:
        return None, "empty alert_id"
    try:
        rows = _req(
            "POST",
            "/api/v1/query",
            {
                "query": [
                    {"_name": "listCase"},
                    # Newest first — an unsorted page returns the oldest
                    # cases and misses the one a retried send just created.
                    {"_name": "sort", "_fields": [{"number": "desc"}]},
                    {"_name": "page", "from": 0, "to": 100},
                ]
            },
            timeout=30,
        )
    except Exception as exc:
        return None, f"query failed: {exc}"
    if not isinstance(rows, list):
        return None, f"unexpected response type {type(rows).__name__}"
    tag = f"alert_id:{needle}"
    for case in rows:
        if not isinstance(case, dict):
            continue
        if tag in (case.get("tags") or []):
            return case, None
        if needle in (case.get("description") or ""):
            return case, None
    return None, f"scanned {len(rows)} cases, no match"


try:
    case_body = json.loads(r"""$normalize_inputs.message.case""")
except Exception:
    case_body = {}

existing, dedup_err = _find_case(alert_id)
if existing:
    print(json.dumps({"success": True, "deduped": True, "body": existing}))
else:
    try:
        created = _req("POST", "/api/v1/case", case_body, timeout=120)
        print(
            json.dumps(
                {
                    "success": True,
                    "deduped": False,
                    "dedup_note": dedup_err,
                    "body": created,
                }
            )
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:200].decode(errors="replace")
        print(
            json.dumps(
                {
                    "success": False,
                    "deduped": False,
                    # body._id must always exist — downstream nodes resolve
                    # `$thehive_create_case.message.body._id`; a missing key
                    # raises shuffle_variable_error BEFORE their code runs.
                    "body": {"_id": ""},
                    "error": f"HTTP {exc.code}: {detail}",
                }
            )
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "success": False,
                    "deduped": False,
                    "body": {"_id": ""},
                    "error": str(exc),
                }
            )
        )
