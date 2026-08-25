# Embedded script: verify_es
# Verifies that Elasticsearch indexed the alert document.
import json
import logging

logger = logging.getLogger(__name__)
raw = r"""$es_index"""
try:
    obj = json.loads(raw)
    body = obj.get("body", obj)
    result = body.get("result", "")
    doc_id = body.get("_id", "")
    if result not in ("created", "updated"):
        raise Exception(f"ES indexing failed - result={result}")
    print(f"OK: ES indexed document_id={doc_id}")
except Exception as e:
    raise Exception(f"ERROR: ES indexing verification failed: {e}") from e
