#!/usr/bin/env bash
# init_tenzir_token.sh — CORE-SEC-003: provision a X-Tenzir-Token for the
# Tenzir web server running in "upstream" mode (HTTP + token auth on the
# internal net).
#
#   init_tenzir_token.sh [--force]
#
# Idempotent: if TENZIR_TOKEN in .env already authenticates, it is kept.
# Otherwise a fresh token is minted via `tenzir-ctl web generate-token`
# (persisted in the node state volume) and written to .env.
#
# After running this, re-run `make init-webhook` so the Shuffle workflow
# picks the token up in its Tenzir actions' headers.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT/.env"
CURL_IMG="curlimages/curl:8.10.1"

die() { echo "ERROR: $*" >&2; exit 1; }

[ -f "$ENV_FILE" ] || die "$ENV_FILE not found"

token_valid() {
    [ -n "${1:-}" ] || return 1
    # POST pipeline/create is the cheapest endpoint that exercises the
    # token check (no GET route exists); the probe pipeline is hidden and
    # self-destructs via ttl=5s.
    docker run --rm --network soar_net "$CURL_IMG" \
        -sk -o /dev/null -w '%{http_code}' -X POST \
        -H "X-Tenzir-Token: $1" -H 'Content-Type: application/json' \
        -d '{"definition":"export | head 1 | discard","name":"_token_probe","hidden":true,"ttl":"5s"}' \
        'https://tenzir-node:5160/api/v0/pipeline/create' 2>/dev/null \
        | grep -q '^2'
}

current="$(grep -E '^TENZIR_TOKEN=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '"'"'"' ' || true)"
if [ "${1:-}" != "--force" ] && token_valid "$current"; then
    echo "OK: existing TENZIR_TOKEN still valid — nothing to do"
    exit 0
fi

echo "minting fresh token via tenzir-ctl..."
token="$(MSYS_NO_PATHCONV=1 docker exec soar_tenzir_node tenzir-ctl web generate-token 2>/dev/null | tail -1 | tr -d '[:space:]')"
[ -n "$token" ] || die "tenzir-ctl returned no token (is soar_tenzir_node up?)"

if grep -qE '^TENZIR_TOKEN=' "$ENV_FILE"; then
    sed -i.bak "s|^TENZIR_TOKEN=.*|TENZIR_TOKEN=$token|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
else
    echo "TENZIR_TOKEN=$token" >> "$ENV_FILE"
fi
for extra in "$ROOT/.env.full" "$ROOT/.env.container"; do
    if [ -f "$extra" ]; then
        if grep -qE '^TENZIR_TOKEN=' "$extra"; then
            sed -i.bak "s|^TENZIR_TOKEN=.*|TENZIR_TOKEN=$token|" "$extra" && rm -f "$extra.bak"
        else
            echo "TENZIR_TOKEN=$token" >> "$extra"
        fi
    fi
done

token_valid "$token" || die "fresh token failed validation against the API"
echo "OK: TENZIR_TOKEN written to .env (+ .env.full/.env.container if present)"
echo "next: make init-webhook  # re-render the workflow with the token header"
