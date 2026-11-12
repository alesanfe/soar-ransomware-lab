# syntax=docker/dockerfile:1
# checkov:skip=CKV_DOCKER_2: app images are spawned by the Shuffle worker — they
# inherit no compose healthcheck; liveness is the execution result itself.
# Lab CA shim for upstream Shuffle app images.
#
# Why: upstream python app images (shuffle-tools, http, subflow) only trust the
# public CA bundle — calls to thehive:9443 / cortex:9443 / shuffle-backend:5443
# fail CERTIFICATE_VERIFY_FAILED. This shim appends the lab CA to the system
# store AND certifi, and exports the *CA_BUNDLE envs so urllib/requests/curl all
# verify correctly. The image is retagged with the upstream name so the app
# definitions stored in OpenSearch keep working unchanged.
#
# Build context must be infra/docker (config/certs/ca.crt is copied from there):
#   docker build -f images/app-ca/Dockerfile --build-arg BASE_IMAGE=frikky/shuffle:http_1.4.0 -t frikky/shuffle:http_1.4.0 infra/docker
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER root
COPY config/certs/ca.crt /usr/local/share/ca-certificates/lab-ca.crt
RUN (command -v update-ca-certificates >/dev/null && update-ca-certificates) || \
    (mkdir -p /etc/ssl/certs && cat /usr/local/share/ca-certificates/lab-ca.crt >> /etc/ssl/certs/ca-certificates.crt) || true
# certifi does NOT read the system store — append the lab CA there too.
RUN python -c "import certifi; open(certifi.where(), 'a').write(open('/usr/local/share/ca-certificates/lab-ca.crt').read())" 2>/dev/null || \
    python3 -c "import certifi; open(certifi.where(), 'a').write(open('/usr/local/share/ca-certificates/lab-ca.crt').read())" 2>/dev/null || true
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
