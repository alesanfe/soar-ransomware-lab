#!/bin/sh
# Render /srv/config.template.json -> /tmp/config.json injecting the
# TAXII_*_PASS env vars, then exec gunicorn serving the medallion Flask
# app over TLS. Credentials never live in the image: the template
# carries placeholders and compose fails closed when env vars are unset.
set -eu

python3 - <<'PY'
import json
import os
import sys

required = ("TAXII_READER_PASS", "TAXII_WRITER_PASS")
missing = [v for v in required if not os.environ.get(v)]
if missing:
    sys.exit(f"entrypoint: missing required env vars: {', '.join(missing)}")

with open("/srv/config.template.json", encoding="utf-8") as fh:
    cfg = json.load(fh)
cfg["users"]["taxii_reader"] = os.environ["TAXII_READER_PASS"]
cfg["users"]["taxii_writer"] = os.environ["TAXII_WRITER_PASS"]
with open("/tmp/config.json", "w", encoding="utf-8") as fh:
    json.dump(cfg, fh)
PY

# TLS-only: medallion's own runner is HTTP-only, so the Flask app is
# served by gunicorn with the lab CA-signed certificate.
exec gunicorn --bind 0.0.0.0:5000 \
    --workers 2 \
    --certfile /etc/taxii/tls/taxii.crt \
    --keyfile /etc/taxii/tls/taxii.key \
    --chdir /srv \
    tls_app:app
