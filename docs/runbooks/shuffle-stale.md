# Runbook: Ejecuciones stale de Shuffle saturan Orborus

## Síntomas

- Los workflows no arrancan: el Orborus está en `max 10 workers` con
  ejecuciones `EXECUTING` zombie (de tests fallidos o restarts).
- `make test-e2e` falla en timeouts de ejecución.
- Alertas llegan a Shuffle pero nada corre.

## Diagnóstico

```bash
# Contar ejecuciones stale en OpenSearch de Shuffle:
docker exec soar_api curl -s \
  "http://shuffle-opensearch:9200/workflowexecution*/_search?q=status:EXECUTING"
```

## Acción

**Automática (desde 2026-11-08):** la API corre `StaleExecutionGC`
(`infrastructure/monitoring/stale_execution_gc.py`) cada
`SHUFFLE_STALE_GC_INTERVAL_S` (300 s): todo `EXECUTING` más viejo que
`SHUFFLE_STALE_MINUTES` (30 min) se aborta vía API y se marca `ABORTED`
en OpenSearch — sin purgar el documento ni tocar workers sanos.
Desactivable con `SHUFFLE_STALE_GC_ENABLED=false`.

```bash
# Manual (nuclear — purga no-FINISHED y fuerza rm de workers):
make clean-shuffle   # → scripts/maintenance/clean_shuffle_executions.py
```

Marca las ejecuciones `EXECUTING` antiguas como `ABORTED`, liberando los
workers del Orborus. `make test-e2e` ya lo hace automáticamente — este
runbook es para ejecuciones manuales o cuando la GC automática no basta
(p.ej. workers Docker zombie acumulados).

## Verificación

- Orborus vuelve a tomar trabajos: `docker logs soar_orborus --tail 20`.
- Re-lanzar una alerta de prueba (`make simulate-malicious`) y confirmar
  que una ejecución nueva llega a `FINISHED`.

## Variante: ejecuciones `EXECUTING` con `results=0` eternamente

Si las ejecuciones (de **cualquier** workflow, no solo uno) se quedan en
`EXECUTING` con `results=0` >5 min y en el log del worker aparece
`Should run towards port XXXX for app <app>` seguido de un shutdown
silencioso, el **servicio swarm de la app** no existe —
`SHUFFLE_CONTAINER_AUTO_CLEANUP=true` (Orborus) o un `clean-shuffle`
pudieron haberlo eliminado.

```bash
# Comprobar qué app services existen (deben salir workers + una por app):
docker service ls

# Si falta p.ej. shuffle-tools_1-2-0, recrearlo (puerto ingress libre):
docker service create --name shuffle-tools_1-2-0 --replicas 4 \
  --network soar_swarm --publish published=33337,target=33337,mode=ingress \
  -e SHUFFLE_APP_EXPOSED_PORT=33337 -e SHUFFLE_SWARM_CONFIG=run \
  -e SHUFFLE_LOGS_DISABLED=true -e CALLBACK_URL=http://shuffle-backend:5001 \
  -e BASE_URL=http://shuffle-workers:33333 -e SHUFFLE_APP_SDK_TIMEOUT=300 \
  frikky/shuffle:shuffle-tools_1.2.0
```

El worker resuelve el servicio por **nombre** (`<app>_<version>` con `-`
en lugar de `.`); el puerto solo debe estar libre en el ingress.
Verificado 2026-11-08: tras recrear `shuffle-tools_1-2-0` la ejecución
pasó de `results=0` a `FINISHED 56/56` en ~3 min.

## Variante: warm-apps con callback erróneo (`:33333` connection refused)

Con `SHUFFLE_WARM_APPS=true`, si las ejecuciones quedan en
`EXECUTING res=0` y el log del contenedor `warmapp-*` muestra
`Sending result to http://<worker_ip>:33333 ... Connection refused`,
el worker corre una imagen **anterior** al hunk que inyecta
`SHUFFLE_WORKER_SERVER_URL=http://127.0.0.1:<worker_port>` en
`webserverSetup` (patch `images/worker/0004`). El app entonces cae al
default upstream `hostname:baseport(33333)` donde nadie escucha.

```bash
# El binario correcto contiene el string:
docker run --rm --entrypoint sh soar_shuffle-worker:2.2.1-patched \
  -c "strings /worker | grep 'http://127.0.0.1:%d'"

# Fix: rebuild de la imagen worker y dejar que Orborus relance workers
docker build -t soar_shuffle-worker:2.2.1-patched infra/docker/images/worker/
```

Los `EXECUTING res=0` generados los recoge el GC a los 30 min.
Verificado 2026-11-08: post-rebuild, cohorte warm P50 ≈ 36 s vs
250-332 s del cold path (ver `docs/20-perf-baseline.md`).

## Variante: frontend "Waiting for the Shuffle database" permanente

Síntoma: `localhost:8081` muestra la splash de espera aunque el backend
ejecuta workflows con normalidad. Logs del frontend:

```text
connect() failed (111: Connection refused) while connecting to upstream,
upstream: "http://172.18.0.12:5001/api/v1/checkusers"
```

Causa: el nginx interno del frontend resuelve `shuffle-backend` **al
arranque** y cachea la IP; si el backend se recrea/reinicia después
(`docker restart soar_shuffle_backend`), la IP cambia y el upstream
queda apuntando a una IP muerta.

```bash
# Confirmar: la IP cacheada no coincide con la actual del backend
docker inspect soar_shuffle_backend --format \
  "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}"

# Fix: reiniciar el frontend para re-resolver
docker restart soar_shuffle_frontend
```

Detectado 2026-11-08 por la suite de capturas UI (TC-28 screenshots).
Nota: cualquier nginx con `proxy_pass` a hostname resuelto al arranque
sufre el mismo modo de fallo tras restart del upstream.

## Notas

- Este runbook se menciona en `AGENTS.md` (common pitfalls) — es el
  fallo más frecuente tras E2E interrumpidos.
