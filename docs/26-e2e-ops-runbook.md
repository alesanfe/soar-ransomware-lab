# 26. E2E Ops Runbook — Runner, Guard, Recuperación y Matriz de Configuración

> Documento operativo para las suites E2E estabilizadas (TC-11, TC-20, TC-36, TC-40).
> Complementa `docs/20-observability-runbooks.md` con la parte de ejecución de tests.

## 1. Resumen

### 1.1 Objetivo

Cerrar la trazabilidad operativa de los mecanismos introducidos en la ronda de
estabilización E2E: runner dedicado, egress-guard con anclaje de netns, preflight,
clasificación de fallos, métricas históricas de recuperación y gate de cierre.

### 1.2 Contexto

Docker Desktop/WSL2 reconcilia contenedores en oleadas bajo presión de disco.
Los tests que corren dentro de `soar_api` morían al recrearse el contenedor, y los
sidecars `network_mode: service:<target>` quedaban huérfanos al recrear el target.

## 2. Alcance

- Cubre: ejecución de E2E, ciclo de vida del runner, egress-guard, preflight,
  JUnit/metadata, métricas de recuperación, gate de cierre, matriz de variables.
- No cubre: hardening de servicios (ver `02-architecture.md`), dashboards
  (ver `20-observability-runbooks.md`).

## 3. Contenido

### 3.1 Egress-guard: arquitectura (E10-05)

```
soar_api (netns N)                       soar_api_egress_guard
┌─────────────────┐   network_mode:     ┌──────────────────────────┐
│  OUTPUT chain ──┼── service:api ─────▶│  aplica iptables EN N    │
│  (reglas viven  │                     │  (el contenedor solo es  │
│   en el netns)  │                     │   portador de binarios)  │
└─────────────────┘                     └──────────────────────────┘
```

Hechos verificados por TC-20 (`test_egress_after_recreate.py`):

- Las reglas iptables residen en el **netns del api**, no en el guard: borrar
  el guard NO abre egress (`test_egress_rules_outlive_guard_container`).
- Recrear `soar_api` crea un netns nuevo → el guard queda apuntando a un netns
  muerto (`network_mode: service:api` resuelve el ID en el momento de creación).
  Hay que re-anclar: recrear el guard contra el nuevo target.
- `docker restart soar_api` conserva el netns → el guard sigue válido
  (`test_egress_persists_across_api_restart`).
- Diagnóstico de sidecars huérfanos: `python scripts/debug/netns_orphan_report.py`
  — compara el target resuelto de cada `service:<x>` contra contenedores vivos.

Re-anclaje manual tras recreate del API:

```bash
docker rm -f soar_api_egress_guard
make up   # recrea el guard con network_mode: service:api → nuevo ID
python scripts/ci/e2e_host_preflight.py   # verifica anclaje al netns vivo
```

### 3.2 Runner dedicado `soar_test_runner` (E7-02/03/04)

- Creado con `scripts/debug/mk_test_runner.py`, eliminado con `rm_test_runner.py`.
- Misma imagen y mounts/env que `soar_api`, pero labels anti-adopción:
  `com.docker.compose.project=e2e-runner`, `oneoff=True`,
  `soar.runner.cfg-hash`, `soar.runner.image-id` — docker-compose no lo reconcilia.
- Ejecutar suites largas **detached** (un exec interactivo muere con la sesión):

```bash
docker exec -d soar_test_runner sh -c \
  "cd /app && python -m pytest tests/e2e/TC-36 -v \
   --junitxml=/app/reports/validation/results/junit/junit-tc-36-obspipe.xml \
   > /tmp/tc36.log 2>&1"
docker exec soar_test_runner tail -f /tmp/tc36.log
```

### 3.3 Runbook TC-11 — watcher precision (E10-02)

- Suite: `tests/e2e/TC-11` (13 tests; `test_watcher_precision.py` es el gate
  de precisión — ground truth vía `docker network inspect` real).
- Fallo típico 1 — **timeout de health**: sube `E2E_HEALTH_ATTEMPTS` /
  `E2E_HEALTH_PAUSE_S` durante oleadas de reconciliación (transient markers:
  connection refused/reset/timeout/DNS). Los fallos definitivos (401, cert)
  NO se reintentan — cortan al momento.
- Fallo típico 2 — **`soar_api` recreado mid-run**: mover la ejecución a
  `soar_test_runner` (§3.2); verificar guard tras el recreate (§3.1).
- Evidencia: `reports/validation/results/junit/junit-tc-11-precision.xml`.

### 3.4 Runbook TC-36 — observability outage recovery (E10-03)

- Suite: `tests/e2e/TC-36/test_obs_pipeline_outages.py` (5 tests).
- Matriz: Tempo stop/kill-9, OTel collector stop, Prometheus stop,
  Loki stop (replay vía positions de promtail).
- **Prometheus tras stop/start**: docker lo marca `healthy` mientras aún
  reemplaza el WAL — en este host ~5 min hasta `/-/ready` y repoblación de
  `up`. El test espera `/-/ready` explícitamente antes de consultar `up`;
  no recortar los timeouts (420s ready + 360s targets).
- **Loki/promtail**: los marcadores emitidos durante el outage deben aparecer
  todos tras el restart (0 pérdida vía positions file). Si faltan → revisar
  `/var/log/positions.yaml` en `soar_promtail`.
- No ejecutar dos veces la suite en paralelo: ambos compiten por los mismos
  contenedores.

### 3.5 Runbook general de recuperación/OPS (E10-04)

| Síntoma | Causa probable | Acción |
|---|---|---|
| E2E aborta con "container not found" | API recreada mid-run | usar `soar_test_runner` |
| egress abierto tras recreate | netns nuevo, guard huérfano | re-anclar guard (§3.1) |
| sidecars `warmapp-*shuffle-tools` DEAD | workers Orborus interrumpidos | `netns_orphan_report.py`, `make clean-shuffle` |
| health checks fallan en oleada | reconciliación Docker Desktop | esperar; health retries configurables |
| Prometheus tarda minutos en `up` | WAL replay + presión de disco | normal bajo host al 97%; no reducir timeouts |
| TheHive 401/connection refused cíclico | bootstrap/restart en curso | esperar a `healthy`; ver runbook TheHive en `AGENTS.md` |
| pytest ERROR `FileNotFoundError: git` | imagen runner sin git | metadata lo registra como `n/a` (no es bug del test) |

Correlación con tormentas de reconciliación (E11-05): cada registro de
`recovery-metrics.jsonl` puede cruzarse con
`docker events --since <Ts> --filter event=start` — ráfagas de starts
coincidiendo con recovery_s altos indican presión del host, no regresión
del producto. `recovery_metrics.docker_start_churn()` lo cuenta.

### 3.6 Matriz de configuración (E3-04)

| Variable | Default | Efecto |
|---|---|---|
| `E2E_API_URL` | `http://api:8000` | URL del API para tests portables (nunca hardcodear localhost) |
| `E2E_HEALTH_ATTEMPTS` | `10` | reintentos de health ante transient TCP |
| `E2E_HEALTH_PAUSE_S` | `8` | pausa entre reintentos |
| `E2E_SKIP_SERVICES` | `""` | servicios excluidos de checks; las suites hacen merge, nunca overwrite |
| `E2E_PREFLIGHT` | `warn` | `strict` hace FAIL cualquier WARN de preflight |
| `E2E_RECOVERY_METRICS` | `…/recovery-metrics.jsonl` | destino del histórico de recuperaciones |
| `E2E_SUITE_START` | `0` | offset de suites en `e2e_suites.py run` |
| `THEHIVE_HOST_PORT` | `8100` | puerto host→9443 TLS interno (renombrado de `THEHIVE_HTTP_PORT`) |
| `CORTEX_HOST_PORT` | `8101` | puerto host→9443 TLS interno (renombrado de `CORTEX_HTTP_PORT`) |
| `REQUESTS_CA_BUNDLE` | `/app/certs/ca-bundle.crt` | bundle CA para `requests` dentro de contenedores |
| `DOCKER_HOST` | `tcp://docker-socket-proxy:2375` | daemon vía proxy (CIS 5.31) |
| `CONTAINMENT_SERVICE_TOKEN` | — | token de servicio scoping containment (compose api) |
| `CACHE_SERVICE_TOKEN` | — | token de servicio scoping cache |
| `CALLBACK_SERVICE_TOKEN` | — | token de servicio scoping callbacks |

### 3.7 Clasificación de fallos → JUnit (E6-03/E12-05)

`tests/e2e/helpers/failure_domain.py` etiqueta cada fallo con dominio primario
(`HOST_CAPACITY`, `NETWORK`, `TLS`, `AUTH`, `DOCKER`, `OBS_RECOVERY`,
`SECURITY_CONTROL`, `PRODUCT`, `TEST_CODE`, `RUNNER`, `CLEANUP`, `UNKNOWN`)
en `user_properties` + sección `failure domain` del XML. Nunca convierte un
fallo en éxito — solo enriquece diagnóstico.

### 3.8 Metadata de reproducibilidad en JUnit (E9-04)

Cada testcase lleva `<properties>` con `meta.git_commit`, `meta.docker_server`,
`meta.platform`, `meta.python`, `meta.e2e_api_url` (sanitizada),
`meta.e2e_skip_services`, `meta.health_attempts/pause_s`,
`meta.disk_free_mb_at_start`, `meta.ts_utc`. Lo no disponible se registra
como `n/a` — nunca se inventa.

### 3.9 Cleanup transaccional (E12-04)

`tests/e2e/helpers/cleanup_stack.py`: pila LIFO de acciones undo; `run()`
intenta TODAS aunque alguna falle y separa errores de cleanup del fallo
original del test. Usar en tests que mutan estado compartido.

### 3.10 Gate de cierre (E9-05)

```bash
python scripts/ci/e2e_close_gate.py --junit-dir reports/validation/results/junit --catalog-test
```

Verifica: JUnit TC-11/TC-36 frescos sin F/E, `e2e_suites.py validate` OK,
y (opcional) el contrato de catálogo. Exit 0 solo si todo cumple.

### 3.11 Rotación de artifacts (E11-03)

```bash
python scripts/maintenance/rotate_runtime.py          # dry-run
python scripts/maintenance/rotate_runtime.py --apply  # ejecuta
```

Archiva JUnit >14 días a zip, borra logs/artifacts >30 días, protege
`runtime/data`, `runtime/backups` y claves persistidas; conserva los 3
ficheros más nuevos por directorio.

## 4. Validación

- Preflight: `python scripts/ci/e2e_host_preflight.py` (daemon, disco, CA
  bundle, churn de reconciliación, guard anclado, reports escribibles).
- Close gate: §3.10 — PASS exige evidencia JUnit limpia.
- Orphans: `python scripts/debug/netns_orphan_report.py` sin DEAD targets.

## 5. Problemas y consideraciones

- **E11-01 (disco host ~97%)**: acción OPS del usuario — no ejecutable desde
  el repo sin aprobación explícita de destrucción. Ver
  `reports/ops/disk-audit-2026-11-11.md`: ~14.7 GiB recuperables
  (build cache 6.4 GiB + imágenes dangling 8.35 GiB).
- La discrepancia host-97% vs `/app`-libre es real (namespaces de mount
  distintos); el preflight la documenta, no la oculta.
- Ejecutar TC-36 en paralelo consigo mismo corrompe resultados (contenedores
  compartidos).

## 6. Referencias

- `tests/e2e/TC-20/test_egress_after_recreate.py` — semántica netns del guard
- `tests/e2e/TC-36/test_obs_pipeline_outages.py` — matriz de outages + kill-9
- `tests/e2e/conftest.py` — preflight autouse + metadata JUnit
- `scripts/debug/mk_test_runner.py`, `rm_test_runner.py`, `netns_orphan_report.py`
- `scripts/ci/e2e_host_preflight.py`, `e2e_close_gate.py`
- `scripts/maintenance/rotate_runtime.py`
- `reports/ops/disk-audit-2026-11-11.md`
