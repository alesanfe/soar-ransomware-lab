# syntax=docker/dockerfile:1
# Patched Shuffle Orborus for docker mode concurrency.
# Clones the upstream v2.2.1 tag and applies a small patch so that
# /api/v1/workflows/queue is polled with ?amount=<maxConcurrency> even in
# docker mode. This lets Orborus fetch multiple pending executions in one
# poll and start worker containers concurrently.
FROM golang:1.24-alpine AS builder

ARG ORBORUS_VERSION=v2.2.1
ENV GOTOOLCHAIN=auto

RUN apk add --no-cache git ca-certificates

WORKDIR /src
RUN git clone --depth 1 --branch ${ORBORUS_VERSION} https://github.com/Shuffle/orborus.git .

# Patch 1: request up to maxConcurrency executions per queue poll in any mode.
RUN sed -i 's/if maxConcurrency < 50 && (swarmConfig == "run" || swarmConfig == "swarm") {/if maxConcurrency < 50 {/' orborus.go && \
    sed -i 's/fullUrl += "?amount=50"/fullUrl += fmt.Sprintf("?amount=%d", maxConcurrency)/' orborus.go

# Patch 2: ensure getRunningWorkers counts the ghcr.io shuffle-worker image,
# not only the legacy docker.io frikky/shuffle name.
RUN sed -i 's/if !strings.Contains(container.Image, baseimagename) {/if !strings.Contains(container.Image, baseimagename) \&\& !strings.Contains(container.Image, "shuffle-worker") {/' orborus.go

# Patch 3: force worker containers to use the Docker Hub app image base
# (frikky/shuffle:<app>_<version>) regardless of the base image name used by
# orborus for cleanup/counting.
RUN sed -i 's|fmt.Sprintf("SHUFFLE_BASE_IMAGE_NAME=%s", os.Getenv("SHUFFLE_BASE_IMAGE_NAME"))|"SHUFFLE_BASE_IMAGE_NAME=frikky/shuffle"|g' orborus.go && \
    sed -i 's|fmt.Sprintf("SHUFFLE_BASE_IMAGE_NAME=%s", baseimagename)|"SHUFFLE_BASE_IMAGE_NAME=frikky/shuffle"|g' orborus.go

# Patch 4: prevent zombiecheck from treating app containers (python app.py)
# as worker containers to clean up.
RUN sed -i 's|baseString := `python app.py`|baseString := `__NO_MATCH__`|' orborus.go

# Patch 5: attach worker containers to the configured Docker app network
# (SHUFFLE_APP_NETWORK, e.g. soar_net) instead of sharing the orborus
# container's network namespace. This gives each worker its own network
# stack/DNS resolver and prevents NameResolutionError storms under load.
RUN sed -i 's|hostConfig.NetworkMode = container.NetworkMode(fmt.Sprintf("container:%s", containerId))|networkMode := os.Getenv("SHUFFLE_APP_NETWORK"); if len(networkMode) == 0 { networkMode = fmt.Sprintf("container:%s", containerId) }; hostConfig.NetworkMode = container.NetworkMode(networkMode)|' orborus.go

RUN go mod download
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o /orborus .

FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY --from=builder /orborus /orborus
ENTRYPOINT ["/orborus"]
