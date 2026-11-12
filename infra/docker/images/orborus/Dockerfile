# syntax=docker/dockerfile:1
# checkov:skip=CKV_DOCKER_2: healthcheck is defined in docker-compose.yml
# checkov:skip=CKV_DOCKER_3: DinD — needs root to reach mounted docker.sock
# Patched Shuffle Orborus for docker mode concurrency.
#
# Supply-chain (DK-P0-023 / DK-P1-022 / DK-P1-024):
#   * Source pinned to the exact commit that tag v2.2.1 resolves to, and the
#     build FAILS if the checkout is not that commit — a retargeted tag can no
#     longer slip different code into the image.
#   * Builder image pinned by digest; go.mod requires go 1.25.0, so the pinned
#     golang:1.25-alpine satisfies it WITHOUT GOTOOLCHAIN=auto (no undeclared
#     toolchain downloads during the build).
#   * The five local modifications are formal unified-diff patches applied
#     with `git apply --check` — a silent partial application or an upstream
#     drift in the patched regions now fails the build instead of producing a
#     differently-behaving binary.
FROM golang:1.25-alpine@sha256:1ae0735f00daffa3aaf1363a5184c0d2dc55c78e3db4ec70241cdac97bf84b59 AS builder

# Commit that refs/tags/v2.2.1 resolved to on 2026-11-06
# (git ls-remote https://github.com/Shuffle/orborus refs/tags/v2.2.1).
ARG ORBORUS_VERSION=v2.2.1
ARG ORBORUS_COMMIT=da2e2c42d7f8dba64b94cc4b7d94d2664dc19366

RUN apk add --no-cache git ca-certificates

WORKDIR /src
RUN git init . && \
    git remote add origin https://github.com/Shuffle/orborus.git && \
    git fetch --depth 1 origin ${ORBORUS_COMMIT} && \
    git checkout --detach FETCH_HEAD && \
    test "$(git rev-parse HEAD)" = "${ORBORUS_COMMIT}" || { \
        echo "FATAL: tag ${ORBORUS_VERSION} no longer resolves to ${ORBORUS_COMMIT}"; \
        echo "Source drift detected — refusing to build unverified code."; \
        exit 1; \
    }

# Local patches (verified: git apply --check, then applied in order).
# 0001 poll ?amount=<maxConcurrency> in every mode, not only swarm run modes
# 0002 count ghcr.io shuffle-worker containers as workers (not only frikky/*)
# 0003 force worker base image frikky/shuffle:<app>_<version>
# 0004 zombiecheck must not treat app containers (python app.py) as workers
# 0005 attach workers to SHUFFLE_APP_NETWORK instead of container netns
# 0006 pass SHUFFLE_WORKER_POLL_TIME through to docker-mode worker env
# 0007 pass SHUFFLE_WORKER_POLL_TIME + SHUFFLE_WORKER_SERVER_URL through to
#      swarm-mode worker service env (upstream hardcodes the env list)
# 0008 pass SHUFFLE_WARM_APPS through to spawned workers
# 0009 zombiecheck also reaps orphaned warmapp-* containers whose sibling
#      worker-<execid> is gone (they have no labels and leak unbounded)
# 0010 zombiecheck reaps EXITED ghcr.io/thehive-project/* analyzer
#      containers — Cortex DinD leaves one residue per analysis forever
#      (the "Orborus analyzer leak" `make clean-containers` worked around)
COPY patches/ ./patches/
RUN for p in patches/*.patch; do \
        git apply --check "$p" && git apply "$p" || exit 1; \
    done && rm -rf patches

RUN go mod download
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o /orborus .

FROM alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf
RUN apk add --no-cache ca-certificates
COPY --from=builder /orborus /orborus
ENTRYPOINT ["/orborus"]
