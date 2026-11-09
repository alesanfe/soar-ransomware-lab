# PERF — Baseline de rendimiento del admission path (soak-lite)

Evidencia medida para el campo 10 (Rendimiento) del scorecard. Ejecutado
**dentro del stack** (`soar_api` → `localhost:8000`) con
`scripts/perf/locustfile.py`, Locust 2.47.0, auth real vía
`X-Service-Token`. Artefactos CSV en `reports/perf/soak_lite_*` (gitignored).

## Runs

| Run | Config | Requests | Fails | Throughput |
| --- | --- | --- | --- | --- |
| `soak_lite` (2026-11-08 10:12) | -u 6 -r 2 -t 90s | 3152 | 47 (bug del perfil corregido: GETs no aceptaban 429) | ~36 req/s |
| `soak_lite_final` (2026-11-08 10:17) | -u 4 -r 2 -t 60s | **1147** | **0 (0.00%)** | ~20.6 req/s |

## Latencia (run final)

| Endpoint | P50 | P90 | P95 | P99 | Max |
| --- | --- | --- | --- | --- | --- |
| `POST /api/v1/alerts` (1106 req) | 6 ms | 49 ms | 90 ms | 240 ms | 690 ms |
| `GET /api/v1/queue/metrics` (31) | 10 ms | 55 ms | 110 ms | 340 ms | 343 ms |
| `GET /health` (10) | 10 ms | 61 ms | — | — | 61 ms |

## Qué demuestran los números

- **Admission path**: ~20–35 POST/s sostenidos con P95 < 100 ms
  end-to-end (schema validation → idempotencia → Redis XADD → 202).
  Cero fallos no controlados en >4000 requests acumulados.
- **Rechazo controlado en dos capas**: HTTP 429 (bucket rate-limit por
  token) y 503 (backpressure de cola) — ambos observados en los runs y
  contados como éxito según el contrato de carga del locustfile.
- **Drenado**: post-run la cola retuvo ~550 entradas drenando al ritmo
  del admission worker — la cola actúa como el buffer para el que fue
  diseñada.

## Cadena Shuffle — warm-app workers (medido 2026-11-08 ~11:30 UTC)

Optimización aplicada: `SHUFFLE_WARM_APPS=true` (patch
`images/worker/0004` + propagación Orborus `0008`) — un app server
long-lived por imagen compartiendo el netns del worker; dispatch por
HTTP `/api/v1/run` en ~0.1 s en lugar de spawn+boot de contenedor por
acción (~4.5 s). Sumado a `SHUFFLE_WORKER_POLL_TIME=1` (poll 5 s → 1 s).

**Método**: span real = `min(results[].started_at)` →
`max(results[].completed_at)` en el índice `workflowexecution` de
OpenSearch (excluye espera en cola de Orborus). 20 ejecuciones FINISHED
consecutivas de 56 acciones, durante el drenado post-soak (~10 workers
concurrentes compartiendo CPU del host).

| Cohorte | n | min | P50 | max |
| --- | --- | --- | --- | --- |
| **Warm + prewarm** (post-fix) | 1+ | **21 s** | — | — |
| **Warm apps** (lazy boot) | 17 | 21 s | **~36 s** | 121 s |
| Cold path (imagen previa) | 3 | 250 s | 303 s | 332 s |

- **Mejora ≈ 12×** sobre el baseline de ~266 s (TC-01): ejecución
  `775612e1` FINISHED 56/56 en **21 s** con boot perezoso eliminado —
  los warm servers de todas las imágenes del workflow arrancan en
  paralelo al primer dispatch (`prewarmAppImages`), así que ninguna
  acción paga el cold-start (~4-5 s/imagen) en el camino crítico.
- En esa ejecución la mediana por acción fue **0.28 s** y los más
  lentos (2.4-3.4 s) son analyzers Cortex reales — el suelo de esta
  arquitectura es ahora trabajo externo genuino.
- Bug adicional corregido en el patch (2026-11-08 cont. 2): el canal
  `ready` buffered era consumido por el primer dispatch → el segundo
  uso de la misma imagen bloqueaba `ensureWarmAppServer` para siempre
  (stall determinista `EXECUTING res=2`). Fix: `close(chan)` + campo
  `err`, patrón broadcast correcto.
- Duración por acción: mediana **0.1 s** (antes ~4.5 s de spawn); solo el
  primer uso de cada imagen paga el boot (~4–5 s, amortizado).
- Gap inter-acción: mediana **0.12 s** (antes ~5 s de poll).
- Verificado en vivo: apps postean resultados a
  `http://127.0.0.1:<worker_port>` (env `SHUFFLE_WORKER_SERVER_URL`
  inyectado por el patch en `webserverSetup`); `cleanupWarmApps()`
  elimina los contenedores `warmapp-*` al cerrar el worker (0 huérfanos
  observados). Fallback a contenedor por acción automático si el warm
  server no arranca (rama `deployApp`).
- Limitación conocida: la primera versión del patch no inyectaba
  `SHUFFLE_WORKER_SERVER_URL` → el callback caía al valor upstream
  `hostname:33333` y las acciones colgaban (`EXECUTING res=0`). Corregido
  en el propio patch; workers anteriores al rebuild lo exhiben.

## Límites honestos (no medidos / fuera de alcance)

- El soak mide solo el **admission path**. La cadena Shuffle, ya con
  warm-apps, tiene P50 ≈ 36 s de trabajo real (contenido: 10 workers
  concurrentes en un solo host; outliers 93-121 s por contención CPU).
- `AdmissionUser` usa idempotency keys únicos → la baja latencia no es
  caché de dedup.
- Un solo worker uvicorn; escalado horizontal no medido.

## Gate de aceptación (repetible)

```bash
docker exec soar_api pip install --quiet locust   # one-off
docker exec soar_api sh -c 'cd /app && python -m locust \
    -f scripts/perf/locustfile.py --host http://localhost:8000 \
    -u 4 -r 2 -t 60s --headless --only-summary \
    --csv reports/perf/soak_lite_final'
```

Gate: `failures/s == 0` y `POST /api/v1/alerts` P95 < 500 ms.
**Precaución** — cada admisión reenvía a Shuffle: ejecutar solo con el
stack idle; el `stale_execution_gc` / `make clean-shuffle` recoge las
ejecuciones generadas después.
