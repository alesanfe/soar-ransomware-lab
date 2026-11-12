"""Gunicorn entrypoint for the medallion TAXII server over TLS.

medallion's CLI only supports plain HTTP (``application_instance.run``).
The lab PKI requires TLS on every service, so the Flask application is
configured exactly as ``medallion.scripts.run.main`` does and then
served by gunicorn with the CA-signed certificate mounted under
``/etc/taxii/tls/``.
"""

import json

from medallion import application_instance
from medallion.scripts.run import register_blueprints, set_config

with open("/tmp/config.json", encoding="utf-8") as fh:
    configuration = json.load(fh)

set_config(application_instance, "users", configuration)
set_config(application_instance, "taxii", configuration)
set_config(application_instance, "backend", configuration)
register_blueprints(application_instance)

app = application_instance
