# syntax=docker/dockerfile:1
# checkov:skip=CKV_DOCKER_2: healthcheck is defined in docker-compose.yml
# checkov:skip=CKV_DOCKER_3: DinD — needs root to reach mounted docker.sock
# Patched Shuffle Worker for faster intra-execution dispatch.
#
# Why: upstream worker.go hardcodes `sleepTime = 5` in main(), making every
# stream/dependency poll cycle sleep 5s. With ~8 sequential dependency hops on
# our critical path this accounts for most of the measured scheduling_gap
# (P50 ~25-40s, >50% of workflow span). The patch makes the interval
# configurable via SHUFFLE_WORKER_POLL_TIME (seconds, >=1).
#
# Supply-chain (same hardening pattern as images/orborus):
#   * Source pinned to the exact commit that tag v2.2.1 resolves to; the build
#     FAILS on drift (retargeted tag cannot slip different code in).
#   * Builder image pinned by digest; go.mod requires go 1.25.0.
#   * Local modifications are unified-diff patches verified with
#     `git apply --check` — silent partial application fails the build.
#   * Known residual risk: upstream worker has NO go.sum (it runs
#     `go mod tidy` in its Dockerfile), so transitive Go modules resolve at
#     build time against the Go proxy. Same exposure as the upstream image;
#     documented in docs/17 (PERF-004).
FROM golang:1.25-alpine@sha256:1ae0735f00daffa3aaf1363a5184c0d2dc55c78e3db4ec70241cdac97bf84b59 AS builder

# Commit that refs/tags/v2.2.1 resolved to on 2026-11-07
# (git ls-remote https://github.com/Shuffle/Shuffle refs/tags/v2.2.1).
ARG SHUFFLE_VERSION=v2.2.1
ARG SHUFFLE_COMMIT=a106f27312bbb81791a33dfee585a6b8d0ad3289

RUN apk add --no-cache git ca-certificates

WORKDIR /src
RUN git init . && \
    git remote add origin https://github.com/Shuffle/Shuffle.git && \
    git fetch --depth 1 origin ${SHUFFLE_COMMIT} && \
    git checkout --detach FETCH_HEAD && \
    test "$(git rev-parse HEAD)" = "${SHUFFLE_COMMIT}" || { \
        echo "FATAL: tag ${SHUFFLE_VERSION} no longer resolves to ${SHUFFLE_COMMIT}"; \
        echo "Source drift detected — refusing to build unverified code."; \
        exit 1; \
    }

# Local patches (verified: git apply --check, then applied in order).
# 0001 sleepTime configurable via SHUFFLE_WORKER_POLL_TIME (default stays 5)
# 0002 async dispatch in the swarm branch of runWorkflowExecutionTransaction
# 0003 async handleExecutionResult inside setWorkflowExecution (all modes)
# 0004 SHUFFLE_WARM_APPS: per-image app servers sharing worker netns (docker)
# Build context is infra/docker (see Makefile.* worker-build target) so the
# lab CA can also be baked into the final image.
COPY images/worker/patches/ ./patches/
RUN for p in patches/*.patch; do \
        git apply --check "$p" && git apply "$p" || exit 1; \
    done && rm -rf patches

WORKDIR /src/functions/onprem/worker
RUN go mod download && go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o /worker .

FROM alpine:3.24@sha256:f59abe656b692d901e184be3445e084786602108599d2a51d229c0f5a48c71bf

# Same env defaults as the upstream worker image.
ENV SHUFFLE_BASE_IMAGE_REGISTRY=docker.io
ENV SHUFFLE_BASE_IMAGE_NAME=frikky/shuffle
ENV SHUFFLE_BASE_IMAGE_TAG_SUFFIX=0.8.70
ENV SHUFFLE_OPENSEARCH_URL=https://opensearch:9200
ENV SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY=false
# Poll interval override (seconds >=1); unset = upstream default 5.
ENV SHUFFLE_WORKER_POLL_TIME=

RUN apk add --no-cache bash tzdata ca-certificates
# Lab CA -> system trust store: workers talk to OpenSearch over TLS and
# must verify against the lab CA (was SKIPSSL_VERIFY=true debt).
COPY config/certs/ca.crt /usr/local/share/ca-certificates/lab-ca.crt
RUN update-ca-certificates
COPY --from=builder /worker /worker
CMD ["./worker"]
