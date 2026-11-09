# checkov:skip=CKV_DOCKER_2: healthcheck is defined in docker-compose.yml
# checkov:skip=CKV_DOCKER_3: DinD — needs root to reach mounted docker.sock
FROM thehiveproject/cortex:3.2.0-1

# Install Python dependencies for Cortex analyzers.
# Supply-chain (DK-P1-021): the pip bootstrap is fetched over HTTPS and
# verified against a pinned SHA-256 before execution — no unverified remote
# code runs during the build. cortexutils is pinned so two builds from the
# same commit resolve the same package set.
ARG GET_PIP_SHA256=93ac4b816cb62d2f1cd91c53adcc27ee4a2f33fe89cb9e84e2c90b6875a5475f
ARG CORTEXUTILS_VERSION=2.2.1
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN rm -f /etc/apt/sources.list.d/corretto.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-distutils curl && \
    curl -fsSL https://bootstrap.pypa.io/pip/3.9/get-pip.py -o /tmp/get-pip.py && \
    echo "${GET_PIP_SHA256}  /tmp/get-pip.py" | sha256sum -c - && \
    python3 /tmp/get-pip.py && \
    rm /tmp/get-pip.py && \
    pip3 install --no-cache-dir "cortexutils==${CORTEXUTILS_VERSION}" && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
