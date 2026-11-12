#!/usr/bin/env bash
# obs_capacity_report.sh — capacity/headroom report for the obs stack.
#
# Two views, both verifiable without touching live data:
#   1. Per-volume sizes (docker system df -v) for the 7 obs volumes
#   2. Real filesystem headroom — `df` on /var/lib/docker inside
#      soar_cadvisor (it already mounts it :ro), i.e. the Docker-data FS
#      that backs every named volume AND container layer.
#
# Thresholds: warn >75% used, fail >90% used (exit 1 on fail).
# The full disk-fill drill (inject writes into a scratch volume until the
# FS saturates and confirm obs_s3_objectstore_errors fires) stays a manual
# procedure — it is destructive-by-design on the shared data FS.

set -euo pipefail

PROJECT="${COMPOSE_PROJECT_NAME:-soar}"
WARN_PCT=75
FAIL_PCT=90

VOLUMES=(
    grafana_data grafana_db_data loki_data tempo_data
    prometheus_data s3_data s3_vol2_data
)

echo "== Observability capacity report =="
echo

echo "-- Per-volume sizes --"
docker system df -v | awk -v proj="${PROJECT}_" -v re="(${VOLUMES[*]// /|})" '
    BEGIN { gsub(/ /, "|", re); pat = "^" proj "(" re ")$" }
    $1 ~ pat { printf "%-32s links=%-4s size=%s\n", $1, $(NF-1), $NF }'

echo
echo "-- Docker data filesystem (named-volume mount, same FS as all docker data) --"
# Named volumes live under /var/lib/docker/volumes → `df` on any volume mount
# reports the real data FS (cadvisor is distroless: no df binary).
df_line=""
for probe in "soar_loki:/loki" "soar_tempo:/var/tempo" "soar_api:/"; do
    c="${probe%%:*}"; m="${probe#*:}"
    if df_line=$(MSYS_NO_PATHCONV=1 docker exec "$c" df -P "$m" 2>/dev/null | tail -1) \
        && [ -n "$df_line" ]; then
        echo "      probe=$c mount=$m"
        break
    fi
    df_line=""
done
if [ -z "$df_line" ]; then
    echo "FAIL  no container reachable for df probe"
    exit 1
fi
echo "      $df_line"
used_pct=$(echo "$df_line" | awk '{gsub("%","",$5); print $5}')
avail=$(echo "$df_line" | awk '{print $4}')
echo "      used=${used_pct}% avail=${avail}KB"

echo
rc=0
if [ "$used_pct" -ge "$FAIL_PCT" ]; then
    echo "RESULT: FAIL — data FS at ${used_pct}% (>= ${FAIL_PCT}%)"
    rc=1
elif [ "$used_pct" -ge "$WARN_PCT" ]; then
    echo "RESULT: WARN — data FS at ${used_pct}% (>= ${WARN_PCT}%)"
else
    echo "RESULT: OK — data FS at ${used_pct}%"
fi
exit "$rc"
