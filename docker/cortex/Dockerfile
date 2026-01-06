FROM thehiveproject/cortex:4

USER root
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends python3-venv ca-certificates; \
    python3 -m venv /opt/cortex-venv; \
    /opt/cortex-venv/bin/pip install --no-cache-dir cortexutils; \
    # Shims para que 'python3' y 'pip3' del sistema resuelvan al venv
    ln -sf /opt/cortex-venv/bin/python /usr/local/bin/python3; \
    ln -sf /opt/cortex-venv/bin/pip /usr/local/bin/pip3; \
    rm -rf /var/lib/apt/lists/*

ENV es_uri="http://opensearch:9200"
COPY application.conf /etc/cortex/application.conf
