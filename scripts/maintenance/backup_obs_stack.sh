#!/usr/bin/env bash
# backup_obs_stack.sh — backup + restore drill for the observability stack.
#
#   backup_obs_stack.sh backup  [outdir]
#   backup_obs_stack.sh drill   [backupdir]
#
# backup: tar.gz every named volume of the logging stack into
#         runtime/backups/obs/<ts>/ + manifest with image digests and
#         SHA-256 per archive (DR-EVAL-005: parity with the core script —
#         it previously had neither, so a silently corrupted archive could
#         pass a drill). Volumes are snapshotted live — crash-consistent
#         (acceptable for the lab; documented in doc-24).
#
#         DR-EVAL-006: archives are AES-256-CBC encrypted (PBKDF2, 600k
#         iterations) before hashing — they carry grafana.db, loki chunks
#         and other credential-adjacent data. Requires BACKUP_PASSPHRASE
#         (exported or in .env.full/.env); fails closed if unset.
#
# drill:  restore the latest (or given) backup set into scratch volumes
#         `<name>_drill`, verify sha256 integrity + restored file counts
#         + expected content markers, then drop the scratch volumes.
#         Proves the backup is restorable WITHOUT touching live data.
#         Measures wall time → RTO evidence. Archives are decrypted into
#         a mktemp scratch dir (never written back to the backup set).
#
# Coverage: grafana_data, grafana_db_data, loki_data, tempo_data,
#           prometheus_data, s3_data, s3_vol2_data (project prefix `soar_`).
#
# Retention: keeps the $BACKUP_KEEP newest sets (default 5) — DR-EVAL-004.
#
# Exit non-zero on any failure. Requires docker + a running stack for
# `backup` (reads live volumes); `drill` only needs the daemon.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROJECT="${COMPOSE_PROJECT_NAME:-soar}"
OUT_ROOT="$ROOT/runtime/backups/obs"
HELPER="alpine:3.20"
KEEP="${BACKUP_KEEP:-5}"

VOLUMES=(
    grafana_data
    grafana_db_data
    loki_data
    tempo_data
    prometheus_data
    s3_data
    s3_vol2_data
)

# DR-EVAL-007: BACKUP_VOLUMES overrides the list — lets CI exercise the
# full encrypt→drill pipeline against a synthetic scratch volume.
if [ -n "${BACKUP_VOLUMES:-}" ]; then
    read -ra VOLUMES <<< "$BACKUP_VOLUMES"
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

# Content marker each restored volume must contain to count as
# "real data restored" (not an empty tarball).
declare -A MARKERS=(
    [grafana_data]="grafana.db|png|alerting"
    [grafana_db_data]="base|PG_VERSION"
    [loki_data]="chunks|index|wal"
    [tempo_data]="blocks|wal|traces"
    [prometheus_data]="tsdb|wal"
    [s3_data]=".|"      # any non-empty content
    [s3_vol2_data]=".|"
)

cmd="${1:-}"; arg="${2:-}"

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
    echo "== obs-stack backup → $out =="
    rc=0
    for v in "${VOLUMES[@]}"; do
        vol="${PROJECT}_${v}"
        if ! docker volume inspect "$vol" >/dev/null 2>&1; then
            echo "SKIP  $vol (volume missing)"; continue
        fi
        backup_one "$v" "$vol" "$out" || rc=1
    done
    # manifest: image digests inventory (parity with core script)
    {
        echo "# obs-stack backup manifest — $(date -u +%FT%TZ)"
        for c in soar_grafana soar_grafana_db soar_grafana_renderer soar_loki \
                 soar_tempo soar_prometheus soar_promtail soar_otel_collector \
                 soar_cadvisor soar_blackbox soar_es_exporter soar_s3 soar_s3_vol2; do
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
