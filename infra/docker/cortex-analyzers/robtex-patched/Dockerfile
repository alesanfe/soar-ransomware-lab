# Patches the official Robtex analyzer to use a browser User-Agent
# instead of the default python-requests UA, which Cloudflare blocks
# with HTTP 403.
FROM ghcr.io/thehive-project/robtex_ip_query:1
COPY robtex.py /worker/Robtex/robtex.py
