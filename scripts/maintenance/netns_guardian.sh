#!/bin/sh
# netns-guardian — re-anchor netns-sharing sidecars after backend recreates.
#
# Sidecars using `network_mode: "service:<x>"` are pinned at creation time to
# `container:<id>` in HostConfig. When <x> is recreated the sidecar keeps
# sleeping on the DEAD netns: rules/proxies installed there protect nothing
# and `docker restart` does NOT re-resolve the target (verified empirically).
#
# This watchdog inspects each (sidecar, target) pair and, on drift, clones the
# stale container via `inspect -> create` with a fresh `container:<name>`
# reference — same image/cmd/mounts/caps/healthcheck, current netns.
#
# Runs inside its own normal-networked container (immune to the trap itself),
# talking to the daemon over the mounted docker.sock via curl+jq.

SOCK=${DOCKER_SOCK:-/var/run/docker.sock}
INTERVAL=${GUARDIAN_INTERVAL:-10}

req() {
    # req METHOD PATH [data-file]
    method=$1; path=$2; data=$3
    if [ -n "$data" ]; then
        curl -sS --unix-socket "$SOCK" -X "$method" \
            -H 'Content-Type: application/json' \
            --data-binary "@$data" "http://localhost$path"
    else
        curl -sS --unix-socket "$SOCK" -X "$method" "http://localhost$path"
    fi
}

reanchor() {
    name=$1; target=$2
    tid=$(req GET "/containers/$target/json" | jq -r '.Id // empty' 2>/dev/null)
    [ -z "$tid" ] && return 0
    spec=$(req GET "/containers/$name/json")
    cur=$(echo "$spec" | jq -r '.HostConfig.NetworkMode // empty')
    [ -z "$cur" ] && return 0  # sidecar absent — compose up owns (re)creation
    [ "$cur" = "container:$tid" ] && return 0
    echo "$(date +%T) REANCHOR $name -> $target (was $cur)"
    # Clone the stale container's spec, re-pointing the shared netns at the
    # CURRENT target name (resolved to its fresh id at create time).
    # ExposedPorts/PortBindings are dropped: the daemon rejects them when
    # NetworkMode is container:* (ports belong to the shared netns owner).
    echo "$spec" | jq --arg t "container:$target" \
        '{Image: .Config.Image,
          Cmd: .Config.Cmd,
          Env: .Config.Env,
          Entrypoint: .Config.Entrypoint,
          WorkingDir: .Config.WorkingDir,
          Labels: .Config.Labels,
          Healthcheck: .Config.Healthcheck,
          HostConfig: (.HostConfig | .NetworkMode = $t | .PortBindings = null | .PublishAllPorts = false)}' \
        > /tmp/guardian_spec.json
    req DELETE "/containers/$name?force=true" >/dev/null
    new_id=$(req POST "/containers/create?name=$name" /tmp/guardian_spec.json | jq -r '.Id // empty')
    if [ -n "$new_id" ]; then
        req POST "/containers/$new_id/start" >/dev/null
        echo "$(date +%T) REANCHORED $name ($new_id)"
    else
        echo "$(date +%T) REANCHOR FAILED $name — recreate via compose up" >&2
    fi
}

P=${COMPOSE_PROJECT_NAME:-soar}
API_GUARD=${API_GUARD_NAME:-${P}_api_egress_guard}
API_TARGET=${API_TARGET_NAME:-${P}_api}
TLS_SIDECAR=${TLS_SIDECAR_NAME:-${P}_shuffle_backend_tls}
INGRESS_GUARD=${INGRESS_GUARD_NAME:-${P}_shuffle_backend_ingress_guard}
BACKEND=${BACKEND_NAME:-${P}_shuffle_backend}

echo "netns-guardian: watching $API_GUARD->$API_TARGET, $TLS_SIDECAR/$INGRESS_GUARD->$BACKEND every ${INTERVAL}s"
while true; do
    reanchor "$API_GUARD" "$API_TARGET"
    reanchor "$TLS_SIDECAR" "$BACKEND"
    reanchor "$INGRESS_GUARD" "$BACKEND"
    sleep "$INTERVAL"
done
