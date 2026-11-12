#!/usr/bin/env bash
# backup_core_stack.sh — backup + restore drill for the CORE SOAR stack
# (TheHive/Cortex/Shuffle/Orborus/Tenzir/Redis) — CORE-REL-003/004.
#
#   backup_core_stack.sh backup  [outdir]
#   backup_core_stack.sh drill   [backupdir]
#
# backup: tar.gz every state-bearing volume into
#         runtime/backups/core/<ts>/ + manifest with image digests and
#         SHA-256 per archive. Crash-consistent (lab; documented).
#
#         DR-EVAL-006: archives are AES-256-CBC encrypted (PBKDF2, 600k
#         iterations) before hashing — TheHive/MISP/Redis volumes carry
#         credential-adjacent data. Requires BACKUP_PASSPHRASE (exported
#         or in .env.full/.env); fails closed if unset.
#
# drill:  restore into scratch volumes `<name>_drill`, verify content
#         markers, drop scratch volumes. Proves restorability WITHOUT
#         touching live data. Measures wall time → RTO evidence.
#         Archives are decrypted into a mktemp scratch dir (never
#         written back to the backup set).
#
# Tenzir's state lives in anonymous volumes — resolved live from the
# running container's mounts (skipped cleanly if absent).
#
# Exit non-zero on any failure.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT="${COMPOSE_PROJECT_NAME:-soar}"
OUT_ROOT="$ROOT/runtime/backups/core"
HELPER="alpine:3.20"

# Named volumes of the core stack (project-prefixed).
# MISP-EVAL-005: misp_db/files/configs carry the threat-intel corpus —
# they had zero backup coverage.
# DR-EVAL-001: es_data holds the soar-alerts SIEM corpus, opensearch_data
# the Shuffle environments/executions indexes — both had ZERO coverage.
# DR-EVAL-003: misp_logs carries forensic worker logs (was in MARKERS
# but never in NAMED_VOLUMES — dead config).
NAMED_VOLUMES=(
    thehive_data thehive_files cortex_data
    shuffle_apps shuffle_files redis_data
    misp_db misp_files misp_configs misp_logs
    es_data opensearch_data
)

# DR-EVAL-002: state living in HOST bind mounts (not named volumes).
# runtime/data/api holds soar_data.db — the SqliteAlertRepository.
# Map: logical name -> host dir relative to repo root.
declare -A HOST_DIRS=(
    [api_data]="runtime/data/api"
)

declare -A MARKERS=(
    [thehive_data]="db|index|berkeley"
    [thehive_files]=".|"
    [cortex_data]=".|"
    [shuffle_apps]=".|"
    [shuffle_files]=".|"
    [redis_data]=".|"
    [tenzir_lib]="catalog|meta|store|index|.|"
    [tenzir_cache]=".|"
    [misp_db]="mysql|misp|.|"
    [misp_files]=".|"
    [misp_configs]=".|"
    [misp_logs]=".|"
    [es_data]="nodes|indices|_state"
    [opensearch_data]="nodes|indices|_state"
    [api_data]="soar_data.db"
)

# DR-EVAL-004: retention — keep the N newest backup sets per stack.
KEEP="${BACKUP_KEEP:-5}"

# DR-EVAL-007: BACKUP_VOLUMES overrides the named-volume list — lets CI
# exercise the full encrypt→drill pipeline against a synthetic volume.
if [ -n "${BACKUP_VOLUMES:-}" ]; then
    read -ra NAMED_VOLUMES <<< "$BACKUP_VOLUMES"
fi

# DR-EVAL-006: resolve the encryption passphrase (exported env first,
# then the repo env files). Refuse to run without it.
if [ -z "${BACKUP_PASSPHRASE:-}" ]; then
    for envfile in "$ROOT/.env.full" "$ROOT/.env"; do
        [ -f "$envfile" ] || continue
        line="$(grep -E '^BACKUP_PASSPHRASE=' "$envfile" | tail -1 || true)"
        [ -n "$line" ] && BACKUP_PASSPHRASE="${line#BACKUP_PASSPHRASE=}"
        [ -n "${BACKUP_PASSPHRASE:-}" ] && break
    done
fi
BACKUP_PASSPHRASE="${BACKUP_PASSPHRASE:-}"
BACKUP_PASSPHRASE="${BACKUP_PASSPHRASE%$'\r'}"
export BACKUP_PASSPHRASE  # openssl -pass env: needs it in the process env
require_pass() {
    [ -n "${BACKUP_PASSPHRASE}" ] || {
        echo "FAIL: BACKUP_PASSPHRASE unset (see .env.example) — refusing"
        echo "      to run a plaintext-backup workflow"
        exit 1
    }
}

encrypt_one() {  # $1=tgz path — AES-256-CBC/PBKDF2, then drop the plaintext
    openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt \
        -pass env:BACKUP_PASSPHRASE -in "$1" -out "$1.enc" \
        || { echo "FAIL  encrypt $1"; return 1; }
    rm -f "$1"
}

decrypt_one() {  # $1=enc path  $2=dest tgz
    openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
        -pass env:BACKUP_PASSPHRASE -in "$1" -out "$2" \
        || { echo "FAIL  decrypt $1"; return 1; }
}

cmd="${1:-}"; arg="${2:-}"

# Resolve tenzir anonymous volumes live (var/lib = state, var/cache = cache).
tenzir_vols() {
    docker inspect soar_tenzir_node --format \
        '{{range .Mounts}}{{if eq .Destination "/var/lib/tenzir"}}tenzir_lib:{{.Name}}{{"\n"}}{{end}}{{if eq .Destination "/var/cache/tenzir"}}tenzir_cache:{{.Name}}{{"\n"}}{{end}}{{end}}' \
        2>/dev/null || true
}

backup_one() {  # $1=logical name  $2=docker volume name  $3=outdir
    local v="$1" vol="$2" out="$3" dout tgz="$3/$1.tar.gz" members size
    dout="$(cygpath -m "$out" 2>/dev/null || echo "$out")"
    docker run --rm -v "$vol:/data:ro" -v "$dout:/backup" "$HELPER" \
        sh -c "cd /data && tar czf /backup/$1.tar.gz ." \
        || { echo "FAIL  $vol tar"; return 1; }
    members=$(docker run --rm -v "$dout:/backup:ro" "$HELPER" \
        sh -c "gzip -t /backup/$1.tar.gz && tar tzf /backup/$1.tar.gz | wc -l")
    size=$(stat -c%s "$tgz" 2>/dev/null || stat -f%z "$tgz")
    echo "OK    $vol → ${size}B, ${members} members"
    [ "$members" -gt 0 ] || { echo "FAIL  $vol empty archive"; return 1; }
    encrypt_one "$tgz" || return 1
    sha256sum "$tgz.enc" | awk -v n="$1" '{print $1"  "n".tar.gz.enc"}' >> "$out/SHA256SUMS"
}

backup_host_dir() {  # $1=logical name  $2=host dir  $3=outdir
    local v="$1" src="$2" out="$3" dout tgz="$3/$1.tar.gz" members size
    dout="$(cygpath -m "$out" 2>/dev/null || echo "$out")"
    local dsrc; dsrc="$(cygpath -m "$src" 2>/dev/null || echo "$src")"
    docker run --rm -v "$dsrc:/data:ro" -v "$dout:/backup" "$HELPER" \
        sh -c "cd /data && tar czf /backup/$1.tar.gz ." \
        || { echo "FAIL  $v tar"; return 1; }
    members=$(docker run --rm -v "$dout:/backup:ro" "$HELPER" \
        sh -c "gzip -t /backup/$1.tar.gz && tar tzf /backup/$1.tar.gz | wc -l")
    size=$(stat -c%s "$tgz" 2>/dev/null || stat -f%z "$tgz")
    echo "OK    $v → ${size}B, ${members} members"
    [ "$members" -gt 0 ] || { echo "FAIL  $v empty archive"; return 1; }
    encrypt_one "$tgz" || return 1
    sha256sum "$tgz.enc" | awk -v n="$1" '{print $1"  "n".tar.gz.enc"}' >> "$out/SHA256SUMS"
}

prune_old() {  # keep the $KEEP newest sets in $OUT_ROOT
    local sets n
    mapfile -t sets < <(ls -1d "$OUT_ROOT"/*/ 2>/dev/null | sort)
    n=${#sets[@]}
    [ "$n" -le "$KEEP" ] && return 0
    for old in "${sets[@]:0:$((n - KEEP))}"; do
        echo "PRUNE ${old%/}"
        rm -rf "${old%/}"
    done
}

case "$cmd" in

backup)
    require_pass
    out="${arg:-$OUT_ROOT/$(date +%Y%m%d-%H%M%S)}"
    mkdir -p "$out"
    : > "$out/SHA256SUMS"
    echo "== core-stack backup → $out =="
    rc=0
    for v in "${NAMED_VOLUMES[@]}"; do
        vol="${PROJECT}_${v}"
        if ! docker volume inspect "$vol" >/dev/null 2>&1; then
            echo "SKIP  $vol (volume missing)"; continue
        fi
        backup_one "$v" "$vol" "$out" || rc=1
    done
    # tenzir anonymous volumes
    for entry in $(tenzir_vols); do
        name="${entry%%:*}"; vol="${entry#*:}"
        backup_one "$name" "$vol" "$out" || rc=1
    done
    # host bind mounts (DR-EVAL-002)
    for v in "${!HOST_DIRS[@]}"; do
        src="$ROOT/${HOST_DIRS[$v]}"
        [ -d "$src" ] || { echo "SKIP  $v ($src missing)"; continue; }
        backup_host_dir "$v" "$src" "$out" || rc=1
    done
    # manifest: image digests + versions inventory (CORE-REL-003)
    {
        echo "# core-stack backup manifest — $(date -u +%FT%TZ)"
        for c in soar_thehive soar_cortex soar_shuffle_backend soar_shuffle_frontend \
                 soar_orborus soar_tenzir_node soar_redis soar_network_watcher \
                 soar_misp soar_misp_db soar_misp_modules \
                 soar_elasticsearch soar_opensearch soar_api; do
            docker inspect "$c" --format '{{.Name}} image={{.Config.Image}} id={{.Image}}' 2>/dev/null || true
        done
    } > "$out/MANIFEST.txt"
    echo "== backup done (rc=$rc) =="
    prune_old
    exit "$rc"
    ;;

drill)
    require_pass
    bdir="${arg:-$(ls -1d "$OUT_ROOT"/*/ 2>/dev/null | sort | tail -1)}"
    [ -n "$bdir" ] || { echo "no backup set found in $OUT_ROOT"; exit 1; }
    bdir="${bdir%/}"
    echo "== restore drill from $bdir =="
    # integrity check against SHA256SUMS first (names are the real .enc files)
    if [ -f "$bdir/SHA256SUMS" ]; then
        (cd "$bdir" && sha256sum -c SHA256SUMS >/dev/null) \
            || { echo "FAIL  sha256 integrity"; exit 1; }
        echo "OK    sha256 integrity verified"
    fi
    # DR-EVAL-006: decrypt into a scratch dir — the backup set stays
    # encrypted at rest and is never written back to.
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    dtmp="$(cygpath -m "$tmp" 2>/dev/null || echo "$tmp")"
    t0=$SECONDS
    rc=0
    for enc in "$bdir"/*.tar.gz.enc; do
        v="$(basename "$enc" .tar.gz.enc)"
        decrypt_one "$enc" "$tmp/${v}.tar.gz" || { rc=1; continue; }
        dv="${PROJECT}_${v}_drill"
        docker volume create "$dv" >/dev/null
        docker run --rm -v "$dv:/data" -v "$dtmp:/backup:ro" "$HELPER" \
            sh -c "cd /data && tar xzf /backup/${v}.tar.gz" \
            || { echo "FAIL  $v extract"; rc=1; docker volume rm "$dv" >/dev/null; continue; }
        expected=$(docker run --rm -v "$dtmp:/backup:ro" "$HELPER" \
            sh -c "tar tzf /backup/${v}.tar.gz | grep -cv '/$' || true")
        found=$(docker run --rm -v "$dv:/data:ro" "$HELPER" \
            sh -c "find /data -type f | grep -cE '${MARKERS[$v]:-.|}' || true")
        total=$(docker run --rm -v "$dv:/data:ro" "$HELPER" \
            sh -c "find /data -type f | wc -l")
        if [ "$total" -ne "$expected" ]; then
            echo "FAIL  $v file count $total != archive $expected"
            rc=1
        elif [ "$total" -eq 0 ]; then
            echo "OK    $v restored (empty volume, as archived)"
        elif [ "$found" -gt 0 ]; then
            echo "OK    $v restored ($total files, $found markers)"
        else
            echo "FAIL  $v restored ($total files) but no marker files"
            rc=1
        fi
        rm -f "$tmp/${v}.tar.gz"
        docker volume rm "$dv" >/dev/null
    done
    echo "== drill done in $((SECONDS - t0))s (rc=$rc) — RTO evidence =="
    exit "$rc"
    ;;

*)
    echo "usage: $0 {backup [outdir] | drill [backupdir]}" >&2
    exit 2
    ;;
esac
