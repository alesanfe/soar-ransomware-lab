FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

# medallion 3.0.0 — OASIS reference TAXII 2.1 server (memory backend).
# Pinned: a lab must be reproducible, never float on latest.
RUN pip install --no-cache-dir "medallion==3.0.0" "gunicorn==23.0.0" \
    && useradd -r -u 10001 -m taxii

WORKDIR /srv
COPY config.json /srv/config.template.json
COPY data.json /srv/data.json
COPY tls_app.py /srv/tls_app.py
COPY entrypoint.sh /srv/entrypoint.sh
RUN chmod 755 /srv/entrypoint.sh

# read_only rootfs: python must not try to write __pycache__.
ENV PYTHONDONTWRITEBYTECODE=1

USER taxii
EXPOSE 5000
ENTRYPOINT ["/srv/entrypoint.sh"]
