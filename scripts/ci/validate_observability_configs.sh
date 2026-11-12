#!/usr/bin/env bash
# validate_observability_configs.sh — CI gate for the observability stack.
#
# Runs every config through its image-native validator so a bad config can
# never reach `docker compose up` (OBS-076/088/089/097/098/109/147):
#
#   docker compose config -q          full merged model interpolates
#   promtool check config             prometheus.yml scrape/probe jobs
#   promtool check web-config         prometheus-web.yml TLS/basic-auth
#   loki -verify-config               loki-config.yml schema
#   tempo -config.verify              tempo.yml schema
#   promtail -check-syntax            promtail-config.yml pipeline stages
#   otelcol validate                  otel-collector-config.yaml pipeline
#   blackbox_exporter --config.check  blackbox.yml probe modules
#   image pinning                     no :latest / untagged observability images
#   gitleaks (if installed)           secrets regression scan
#
# Image references are parsed from the compose file so the validator always
# matches the deployed version. Exit non-zero on any failure.

set -euo pipefail

# Git-Bash/MSYS rewrites container-side absolute args (/cfg/foo -> C:/Program
# Files/Git/cfg/foo) — disable path conversion for the whole script.
export MSYS_NO_PATHCONV=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_DIR="$ROOT/infra/docker/compose"
LOGGING_COMPOSE="$COMPOSE_DIR/logging/docker-compose.logging.yml"
# Service configs live in infra/docker/config (NOT compose/config — a stray
# dir there once fooled docker into creating empty dirs over the mounts).
CONFIG_DIR="$ROOT/infra/docker/config"
SEAWEED_DIR="$CONFIG_DIR/seaweedfs"
# Git-Bash -> native path for the windows docker binary's --env-file.
# .env is gitignored — CI checks out only .env.example, which is enough for
# `compose config` (the compose files define no `:?` required vars).
if [ -f "$ROOT/.env" ]; then ENV_SRC="$ROOT/.env"; else ENV_SRC="$ROOT/.env.example"; fi
ENV_FILE="$(cygpath -m "$ENV_SRC" 2>/dev/null || echo "$ENV_SRC")"

COMPOSE_FILES=()
for f in \
    docker-compose.yml \
    docker-compose.core.yml \
    docker-compose.misp.yml \
    docker-compose.opensearch.yml \
    docker-compose.api.yml \
    logging/docker-compose.logging.yml \
    docker-compose.hardened.yml
do
    # cygpath: the windows docker binary can't parse MSYS /c/... paths
    COMPOSE_FILES+=(-f "$(cygpath -m "$COMPOSE_DIR/$f" 2>/dev/null || echo "$COMPOSE_DIR/$f")")
done

PASS=0
FAIL=0

ok()  { PASS=$((PASS + 1)); echo "PASS  $1"; }
bad() { FAIL=$((FAIL + 1)); echo "FAIL  $1"; }

run_check() {
    # run_check <label> <cmd...>
    local label="$1"; shift
    if "$@" > /tmp/obs-val.out 2>&1; then
        ok "$label"
    else
        bad "$label"
        sed 's/^/       /' /tmp/obs-val.out | head -15
    fi
}

# --- image refs straight from the compose file (single source of truth) ----
# Compose images use ${VAR:-image:tag} indirection; resolve to the default.
image_of() {
    local raw
    raw=$(awk -v svc="$1" '
        $0 ~ "^  " svc ":" { in_svc=1; next }
        in_svc && /^  [a-z]/ { in_svc=0 }
        in_svc && /image:/ { gsub(/[ "'"'"']/, "", $2); print $2; exit }
    ' "$LOGGING_COMPOSE")
    # ${VAR:-default} → default ; plain ref passes through unchanged
    echo "$raw" | sed -E 's/^\$\{[A-Z0-9_]+:-([^}]+)\}$/\1/'
}

echo "== Observability config validation =="

# 1) Merged compose model must interpolate (catches undefined ${VARS}, bad
#    depends_on conditions, mount typos).
run_check "docker compose config -q" \
    docker compose --env-file "$ENV_FILE" -p soar-ci \
        "${COMPOSE_FILES[@]}" config -q

# 2) Prometheus main + web config.
run_check "promtool check config prometheus.yml" \
    docker run --rm \
        -v "$CONFIG_DIR:/cfg:ro" \
        -v "$CONFIG_DIR/certs:/etc/prometheus/tls:ro" \
        --entrypoint promtool \
        "$(image_of prometheus)" check config /cfg/prometheus.yml

run_check "promtool check web-config prometheus-web.yml" \
    docker run --rm \
        -v "$CONFIG_DIR:/cfg:ro" \
        -v "$CONFIG_DIR/certs:/etc/prometheus/tls:ro" \
        --entrypoint promtool \
        "$(image_of prometheus)" check web-config /cfg/prometheus-web.yml

# 3) Loki.
run_check "loki -verify-config loki-config.yml" \
    docker run --rm -v "$COMPOSE_DIR/logging:/cfg:ro" \
        "$(image_of loki)" -config.file=/cfg/loki-config.yml -verify-config

# 4) Tempo (config lives in infra/docker/config as tempo.yaml).
run_check "tempo -config.verify tempo.yaml" \
    docker run --rm -v "$CONFIG_DIR:/cfg:ro" \
        "$(image_of tempo)" -config.file=/cfg/tempo.yaml -config.verify=true

# 5) Promtail — validate the rendered runtime config AND the template's
#    redaction rules by rendering the template first.
PROMTAIL_RUNTIME="$ROOT/runtime/config/promtail-config.yml"
PROMTAIL_TEMPLATE="$CONFIG_DIR/templates/promtail-config.yml.template"
# /tmp isn't visible to the Windows docker daemon — render inside runtime/.
RENDERED="$ROOT/runtime/promtail-ci-rendered.yml"
if [ -f "$PROMTAIL_TEMPLATE" ]; then
    mkdir -p "$ROOT/runtime"
    # Render the template with dummy values purely for syntax checking.
    sed -e 's/\${[^}]*}/X/g' "$PROMTAIL_TEMPLATE" > "$RENDERED"
    run_check "promtail -check-syntax (rendered template)" \
        docker run --rm -v "$RENDERED:/cfg/promtail.yml:ro" \
            "$(image_of promtail)" -config.file=/cfg/promtail.yml -check-syntax
    rm -f "$RENDERED"
elif [ -f "$PROMTAIL_RUNTIME" ]; then
    run_check "promtail -check-syntax (runtime config)" \
        docker run --rm -v "$PROMTAIL_RUNTIME:/cfg/promtail.yml:ro" \
            "$(image_of promtail)" -config.file=/cfg/promtail.yml -check-syntax
else
    bad "promtail config not found (template or runtime)"
fi

# 6) OpenTelemetry Collector.
run_check "otelcol validate otel-collector-config.yaml" \
    docker run --rm -v "$CONFIG_DIR:/cfg:ro" \
        "$(image_of otel-collector)" validate --config=/cfg/otel-collector-config.yaml

# 7) Blackbox exporter modules.
run_check "blackbox_exporter --config.check blackbox.yml" \
    docker run --rm -v "$CONFIG_DIR:/cfg:ro" \
        "$(image_of blackbox-exporter)" --config.check --config.file=/cfg/blackbox.yml

# 8) Image pinning — observability images must carry an explicit immutable
#    tag (no :latest, no bare name). ${VAR:-ref} resolves to ref for the
#    check; a bare ${VAR} (no default) is a violation since CI can't prove
#    the tag. Digest pinning is accepted too.
pinning_violations=$(
    grep -hE "^\s+image:" "$LOGGING_COMPOSE" \
        | sed -E 's/.*image:[[:space:]]*//; s/["'"'"']//g' \
        | sed -E 's/^\$\{[A-Z0-9_]+:-([^}]+)\}$/\1/' \
        | awk '{
            # violation: no digest/tag at all, or the mutable :latest tag
            if ($0 ~ /:latest$/ || $0 !~ /(@sha256:|:[a-zA-Z0-9._-]+$)/) print
          }' \
        | sort -u || true
)
if [ -z "$pinning_violations" ]; then
    ok "image pinning (no :latest/untagged in logging compose)"
else
    bad "image pinning"
    echo "$pinning_violations" | sed 's/^/       /'
fi

# 9) SeaweedFS scripts are LF (CRLF breaks `set -e` shebang parsing — a bug
#    we already hit once).
# MSYS grep silently strips CR in text mode, so grep-based checks are
# unreliable here — compare od hex output for byte 0d instead.
crlf=""
for f in "$SEAWEED_DIR"/*.sh; do
    if od -An -tx1 "$f" | grep -qw "0d"; then
        crlf="$crlf$f\n"
    fi
done
crlf=$(printf "%b" "$crlf" | sed '/^$/d')
if [ -z "$crlf" ]; then
    ok "seaweedfs scripts use LF endings"
else
    bad "seaweedfs scripts use LF endings"
    echo "$crlf" | sed 's/^/       /'
fi

# 10) Secrets regression scan when gitleaks is available (optional locally,
#     always present in CI).
if command -v gitleaks >/dev/null 2>&1; then
    run_check "gitleaks detect" gitleaks detect --source "$ROOT" --no-git
else
    echo "SKIP  gitleaks detect (gitleaks not installed)"
fi

echo
echo "== Result: $PASS passed, $FAIL failed =="
[ "$FAIL" -eq 0 ]
