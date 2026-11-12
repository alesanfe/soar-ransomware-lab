# 20 — Runbooks de Observabilidad

> Runbooks operativos del stack Grafana/Loki/Tempo/Prometheus/Elasticsearch.
> Cada regla de `infra/docker/compose/logging/alert-rules.yml` referencia el
> runbook que le corresponde mediante la anotación `runbook`.

## 1. Resumen

### 1.1 Objetivo

Dar pasos de diagnóstico y remediación reproducibles para cada condición de
alerta del pipeline SOAR, de modo que una alerta accionable tenga siempre una
respuesta documentada.

### 1.2 Contexto

Entorno: laboratorio (`environment=lab`, ver §5.3). Las alertas notifican al
contact point `soar-api-webhook` (`POST /api/v1/alerts/grafana`), autenticado
con `Authorization: Service-Token`. El API las registra en logs (visibles en
Loki via `{compose_service="api"} |= "grafana_alert"`) y las contabiliza en
`soar_grafana_alert_notifications_total`.

## 2. Alcance

### 2.1 Qué cubre

Las 10 reglas provisionadas en `alert-rules.yml` (grupos `soar-pipeline` y
`soar-pipeline-and-infra`) más los dos fallos de observabilidad más comunes
(self-match en Loki, pipeline de render).

### 2.2 Estrategia de severidades (GRAF-049)

| Severidad | Semántica | Respuesta esperada | Reglas |
|-----------|-----------|--------------------|----------|
| `critical` | Pérdida de datos o servicio caído | Acción inmediata | `soar_dlq_not_empty`, `es_cluster_red`, `soar_api_error_burst` |
| `warning` | Degradación que puede escalar | Investigar en horario laboral | `soar_high_error_log_rate`, `soar_workflow_failure_rate`, `soar_loki_ingest_stalled`, `soar_stream_lag_high`, `es_unassigned_shards`, `grafana_rule_eval_error` |
| `info` | Señal operativa esperada en régimen | Revisar en la próxima revisión | `soar_admission_dead_rate` (dedup/idempotencia normal) |

Cada regla lleva `labels.team: soar-ops`, `labels.severity` y anotación
`runbook` apuntando a la sección RB-NN de este documento.

Owner de todas las reglas: `soar-ops` (label `team`). No existen on-call 24x7
en el laboratorio; las `critical` se tratan como "parar e investigar antes de
seguir usando el stack".

## 3. Runbooks

### RB-01 — `soar_dlq_not_empty` (critical)

**Condición**: `soar_queue_dlq_size > 0` durante 5m.

**Significado**: un mensaje de la cola de admisión agotó sus reintentos y fue a
la dead-letter queue. Ese evento NO se procesará automáticamente.

1. Inspeccionar: `docker exec soar_redis redis-cli XRANGE soar:dlq - + | head -40`
2. Identificar la causa en los logs: `{compose_service="api"} |= "dlq" |= <alert_id>`
3. Causas típicas: payload malformado del productor, TheHive/Shuffle caído más
   allá del presupuesto de reintentos, error de validación Pydantic.
4. Remediación: corregir la causa, reinyectar el mensaje al stream
   `soar:admission` (o descartarlo si es venenoso por diseño y documentarlo).
5. Verificar: panel "Redis Streams / DLQ" vuelve a 0; la alerta pasa a `normal`.

### RB-02 — `soar_stream_lag_high` / `soar_queue_backlog` (warning)

**Condición**: `soar_queue_consumer_lag` o `soar_queue_pending` crecen de forma
sostenida.

1. ¿El consumidor está vivo? `docker logs soar_api --since 10m | grep admission`
2. Lag creciente + consumidor vivo = throughput insuficiente: revisar
   `Container CPU Usage %` del api y `Span Latency p90` (¿dependencia lenta?).
3. Lag creciente + consumidor muerto = ver errores en
   `{compose_service="api"} |~ "(?i)admission|consumer"`.
4. `XINFO GROUPS soar:admission soar` muestra `pending` por consumidor — un
   consumidor con pending alto y sin `delivered` reciente está atascado
   (claim/PEL en RB-05).

### RB-03 — `es_cluster_red` / `es_unassigned_shards` (critical/warning)

**Condición**: `elasticsearch_cluster_health_status{status="red"} == 1` o
`unassigned_shards > 0` durante 10m.

1. `docker exec soar_elasticsearch curl -s localhost:9200/_cat/shards?h=index,shard,prirep,state,unassigned.reason`
2. Causas típicas en este stack: índice corrupto tras kill a mitad de flush
   (`ALLOCATION_FAILED`), disco por encima de `flood_stage` watermark.
3. **Disco**: el panel "ES disk / heap pressure" muestra el % libre del
   filesystem de datos. En Docker Desktop el disco virtual comparte espacio
   con el host — <10% libre activa watermarks (85/90/95%). Liberar con
   `docker system prune` o purgar índices viejos.
4. Índice prescindible con shard irrecuperable → borrar índice
   (`DELETE /<index>`); el servicio lo recrea. Para índices con datos, usar
   `_cluster/reroute?retry_failed` tras resolver la causa.
5. `yellow` en single-node es normal (réplicas no asignables) — la alerta solo
   dispara en `red` o en unassigned persistente.

### RB-04 — `soar_high_error_log_rate` / `soar_api_error_burst` (warning/info)

**Condición**: rate de logs con `error|exception|traceback|fatal` por encima
del umbral, ya con el filtro de dominio aplicado (excluye el propio stack de
observabilidad).

1. Abrir el panel "Error rate by service" con el rango de la alerta.
2. Identificar el servicio dominante en la curva; drillar con
   `{compose_service="<svc>"} |~ "(?i)error"`.
3. **Ruido conocido — auth failures de Elasticsearch**: `security_exception`
   repetidos a intervalos regulares suelen ser un cliente con credenciales
   viejas, no un ataque. El panel "ES auth failures (infra noise)" los aísla.
   Si el origen es un contenedor del stack, revisar `SHUFFLE_*`/env vars
   stale (ver pitfall `SHUFFLE_DEFAULT_APIKEY` en AGENTS.md).
4. Si el "error rate" salta pero NINGÚN servicio de aplicación muestra errores
   → sospechar self-match (RB-06).

### RB-05 — `soar_admission_dead_rate` / `grafana_rule_eval_error` (info)

- `soar_admission_dead_rate`: mensajes marcados dead por idempotencia o
  backpressure. Rate bajo = sano; racha = revisar productor duplicado.
- `grafana_rule_eval_error`: la propia evaluación de una regla falla (datasource
  caído, query inválida tras un edit). Abrir el panel "Alert rules by state",
  localizar la regla en `error`/`nodata` y corregir su expresión.

### RB-06 — Self-match en consultas de logs (no es una alerta, es un bug de query)

**Síntoma**: "Error rate by service" muestra miles de hits con
`compose_service="loki"` o `grafana*`.

**Causa**: Loki/Promtail registran el *texto literal* de las queries LogQL, que
contienen el patrón `error|exception|traceback` → la query se matchea a sí
misma. En la medición original: 2982 hits de Loki vs 0 del API en 30m (92% ruido).

**Fix**: toda query de errores debe llevar el filtro de dominio canónico:

```logql
{compose_service=~".+", compose_service!~"loki|grafana.*|prometheus|cadvisor|tempo|otel-collector|promtail"}
```

(o la variable `$service` del dashboard logs, cuyos valores ya excluyen el
stack de observabilidad). El validador estático
`scripts/quality/validate_dashboards.py` y TC-35
`test_error_query_excludes_observability_stack` bloquean regresiones.

### RB-07 — Pipeline de render roto (TC-35 falla en `test_every_panel_renders_real_png`)

1. `docker logs soar_grafana_renderer --tail 50` — timeouts de Chromium vs
   errores de query.
2. Si solo falla el panel de trazas: Tempo search via JSON datasource necesita
   `urlPath` (no `url`) y la versión de Grafana 10.3.4 solo soporta
   `queryType: traceId` en el datasource Tempo nativo.
3. Renderer a 500 con timeout interno: revisar `RENDERING_MODE`/
   `RENDERING_CLUSTERING_*`/`shm_size` en `docker-compose.logging.yml`
   (los nombres de env var importan — `RENDERING_CLUSTERED_*` no existe).

### RB-08 — Disco de datos (ES/Docker) saturado

**Señal**: panel "ES disk / heap pressure" <10% libre, o `df -h` del host
con C: >90%.

Desde la migración a named volumes, el exporter mide el **disco del VHDX
Docker**, no el host C:. Dos capas distintas:

1. **Disco Docker** (`elasticsearch_filesystem_data_*`): si baja de 10%,
   el watermark `flood_stage` pondría índices read-only. Recuperar espacio:
   `docker image prune -f` (dangling), `docker builder prune -f`,
   `docker image prune -a -f` (imágenes sin contenedor — recuperables vía
   pull/build; en la migración de 2026-11-09 liberó 8.57GB).
2. **Host C: / VHDX hinchado**: WSL2 no devuelve espacio liberado dentro del
   VHDX automáticamente. Script guardado:
   `powershell -ExecutionPolicy Bypass -File scripts\maintenance\compact_vhdx.ps1`
   — verifica que Docker/WSL están parados antes de compactar (rechaza si
   el VHDX está en uso) y con `-AutoStop` baja el stack + WSL, compacta y
   rearranca Docker Desktop. Equivale a `wsl --shutdown` +
   `Optimize-VHD -Mode Full` (o `diskpart compact vdisk` si no hay
   Hyper-V tools). Requiere PowerShell elevado y downtime del stack.
3. Los bind dirs pre-migración ya NO viven en `runtime/data/` — archivados
   a `runtime/backups/legacy/*.tar.gz` vía
   `python scripts/maintenance/archive_legacy_data.py` (verifica el tarball
   antes de borrar el origen; `--dry-run`/`--keep` disponibles). Borrar los
   tarballs tras validar los named volumes unas semanas.

### RB-09 — Object storage S3 (SeaweedFS) caído o corrupto

**Síntoma**: Loki/Tempo no arrancan o loguean `NoSuchBucket`/`connection
refused` a `s3:8333`.

1. Estado: `docker ps -f name=soar_s3`; salud: `wget -qO- http://<s3>:9333/cluster/status`.
2. Buckets esperados: `docker exec soar_s3 sh -c "echo 'fs.ls /buckets/' | weed shell -master=127.0.0.1:9333"`
   → `loki`, `tempo`. Si faltan: `echo 's3.bucket.create -name loki' | weed shell -master=127.0.0.1:9333`
   (o recrear el one-shot: `docker compose ... up -d s3-init`).
3. `autoCreateBucket` NO sustituye al init: Loki/Tempo LISTan el bucket
   antes del primer PUT y fallan con `NoSuchBucket`.
4. Credenciales: `iam.config.json` (`infra/docker/config/seaweedfs/`) debe
   coincidir con `S3_ACCESS_KEY`/`S3_SECRET_KEY` del `.env` — un rotate de
   secretos exige actualizar el file IAM.
5. Datos: `soar_s3_data` y `soar_s3_vol2_data` son named volumes —
   `make down` normal los conserva; `down -v` borra chunks/bloques
   (logs/trazas históricos).
6. Puerto S3 interno: `8333` (no publicado al host — intencional).
7. Réplica (RB-14): si `s3-vol2` cae, las escrituras nuevas **fallan** —
   placement `010` exige la otra réplica. Levantar `s3-vol2` primero;
   si hay volúmenes under-replicated:
   `echo "lock; volume.fix.replication -apply; unlock" | weed shell -master=127.0.0.1:9333`.

### RB-10 — Migración bind-mount → named volume (procedimiento)

Patrón usado en la migración GRAF-D6 (reversible):

1. Parar el servicio afectado (`docker compose ... stop <svc>`).
2. Crear el volumen si no existe: `docker volume create soar_<name>_data`.
3. Copiar: `docker run --rm -v soar_<name>_data:/dst -v <ruta-bind>:/src:ro alpine sh -c "cp -a /src/. /dst/"`.
4. Ajustar la definición del volumen en compose a `driver: local` **sin**
   `driver_opts` — OJO: si otra `-f` file también define el volumen con
   `driver_opts` (bind), el merge las mantiene y el volumen sigue siendo
   bind-mount. Verificar con `docker compose ... config | grep -A4 <name>`.
5. Levantar + verificar (para ES: `_cluster/health` green, `_cat/indices`).
6. El bind dir antiguo queda como rollback — no borrar hasta estabilizar.

### RB-11 — Diagnóstico de 5xx upstream en Shuffle

**Síntoma**: `HttpAlertSender` loguea "Transient failure ... retrying" o
devuelve `success=false` con `status_code` 5xx.

1. Mirar el upstream, no el sender: `docker logs soar_shuffle_backend --tail 100 | grep -iE "500|error"`.
2. El sender reintenta 3× (1.5s+3s) solo en 5xx/429/red — un 4xx sale al
   primer intento. `error="network error after retries"` = 3 fallos
   consecutivos de transporte.
3. Si los 5xx persisten tras retries: el bug está en Shuffle backend
   (upstream, fuera del repo) — escalar, no aumentar el retry budget.
4. Métricas: `alerts_failed` sube solo tras agotar los reintentos —
   un pico sugiere upstream sostenido caído, no flaky.

### RB-12 — Acceso TLS a Grafana (:8444)

- Endpoint: `https://soar.local:8444` (nginx → grafana:3000). Cert firmado
  por `infra/docker/config/certs/ca.crt` (SANs soar.local/grafana/localhost).
- Verificación: `curl --cacert infra/docker/config/certs/ca.crt --resolve soar.local:8444:127.0.0.1 https://soar.local:8444/api/health`.
- Windows Schannel puede mostrar `CERT_TRUST_REVOCATION_STATUS_UNKNOWN`
  con CAs internas sin CRL — benigno; verificar con OpenSSL/Python.
- Renovar el cert: firmar un nuevo `soar.local.csr` con `ca.key` (mismo
  procedimiento que `gen_certs.sh` server cert) — **no** regenerar la CA
  (invalidaría los certs desplegados, p.ej. MISP en `soar_api`).

### RB-13 — TLS interno del stack de observabilidad (GRAF-D10)

Desde 2026-11-10, **toda la superficie HTTP de observabilidad es TLS** con
certs firmados por la CA del lab (`infra/docker/config/certs/`):

| Servicio | Listener TLS | Verifican contra CA |
|----------|-------------|---------------------|
| loki:3100 | `server.http_tls_config` (loki-config.yml) | promtail (`tls_config.ca_file`), grafana ds (`secureJsonData.tlsCACert`), prometheus scrape, API health |
| tempo:3200 | `server.http_tls_config` (tempo.yaml) | grafana ds tempo + tempo-json |
| prometheus:9090 | `--web.config.file` → `prometheus-web.yml` | tempo remote_write (`tls_config.ca_file`), grafana ds, self-scrape |
| grafana:3000 | `GF_SERVER_PROTOCOL=https` | nginx edge (`proxy_ssl_verify on`), prometheus scrape |

- Certs: `infra/docker/config/certs/{loki,tempo,prometheus,grafana}.{crt,key}`,
  CN=<servicio> + SANs `<svc>`, `soar_<svc>`, `localhost`, `127.0.0.1`
  (730 días). Regenerar con la misma receta SAN contra `ca.{crt,key}`.
- El CA PEM va **embebido** en `grafana-datasources.yml.template`
  (`secureJsonData.tlsCACert`) — es material público (solo `ca.key` es
  secreto). Tras regenerar la CA hay que actualizar el PEM en el template.
- Healthchecks de container: `wget --no-check-certificate` (busybox no puede
  pinar CA) — ejercitan handshake TLS; la verificación real la hacen los
  consumidores.
- **Superficie residual en claro** (decisión documentada): OTLP gRPC
  otel-collector→tempo:4317, ES/OpenSearch (xpack security off en lab),
  api:8000, grafana-renderer callback (el renderer usa
  `IGNORE_HTTPS_ERRORS=true` porque Chromium NSS no conoce la CA — el
  tráfico va cifrado igualmente).
- API health checks: `health_check_ssl_config` en settings pinna
  `/app/certs/ca.crt` para loki/grafana/misp — `requests.verify` acepta
  path de bundle (http_client `VerifySSL = bool | str`).
- Verificación: `docker exec soar_api curl --cacert /app/certs/ca.crt https://loki:3100/ready` (200). El curl del **host** falla con Schannel
  (la CA no está en el store de Windows) — es esperado, no un bug.

### RB-14 — Replicación S3 (SeaweedFS 2 racks, placement 010)

Topología: `s3` (master+volume+rack1+filer+S3 gw) + `s3-vol2` (volume,
rack2). `-master.defaultReplication=010` → cada fichero nuevo se escribe
en **dos racks**. Backfill histórico ya ejecutado
(`volume.configure.replication -collectionPattern="*" -replication=010` +
`volume.fix.replication -apply`).

- Estado: `docker exec soar_s3 sh -c 'echo "volume.list" | weed shell -master=127.0.0.1:9333'` — cada volumen debe existir en rack1 **y** rack2.
- `volume.fix.replication` (sin -apply) reporta under-replicated — debe
  salir vacío.
- **Límite honesto**: protege contra caída de un volumen-contenedor, NO
  contra caída del host/WSL ni del filer/S3-gateway (single-instance).
  HA real = despliegue multi-host o S3 gestionado externo — fuera del
  alcance del lab.
- `s3-vol2 -max=64` limita slots; `free:0` rompería escrituras nuevas —
  subir `-max` si el uso crece (los volúmenes lab son <1MB).

### RB-15 — Datos legacy y compactación VHDX

- Bind dirs antiguos: archivados en `runtime/backups/legacy/*.tar.gz`
  por `scripts/maintenance/archive_legacy_data.py` (tar→verify→remove).
- VHDX: `scripts/maintenance/compact_vhdx.ps1 [-AutoStop]` — compactación
  segura con guardas (rechaza si Docker/WSL sigue activo).

### RB-16 — `obs_probe_down` (blackbox probe failing)

`probe_success == 0` durante 2 scrapes. El endpoint objetivo no responde
HTTPS correctamente o el exporter no lo alcanza.

1. `docker logs soar_blackbox_exporter --tail 30` — errores de probe
   (TLS handshake, timeout, DNS).
2. Probar a mano desde la red: `docker exec soar_prometheus wget -qO-
   https://<target>/ready --ca-certificate=/etc/prometheus/tls/ca.crt`.
3. Si es `probe_ssl_verify` — cert caducado o SAN incorrecto: ver RB-18.
4. Si el servicio está healthy pero el probe falla: el nombre/PUERTO del
   target en `prometheus.yml` (job `blackbox-*`) puede estar desactualizado.

### RB-17 — `obs_prometheus_target_down`

`up == 0` más de 2 min. Un scrape target dejó de contestar.

1. `https://grafana:3000` → Prometheus `/targets` — última causa (`dial tcp`,
   `server returned 401`, `context deadline exceeded`).
2. DNS: `docker exec soar_prometheus nslookup <job>` — el servicio y
   Prometheus deben compartir `logging_net` (cadvisor sólo estaba en una
   red una vez y el target daba `lookup cadvisor: no such host`).
3. Scrape timeout: cadvisor enumera todos los contenedores — su job corre a
   `scrape_interval: 60s` + `scrape_timeout: 30s`; promtool exige
   `timeout <= interval` (gate: `validate_observability_configs.sh`).
4. Si el contenedor está en crash-loop → RB-19.

### RB-18 — `obs_cert_expiry_30d` / `obs_cert_expiry_14d`

`probe_ssl_earliest_cert_expiry - time() < 30d/14d`. Un cert del stack va a
expirar.

1. Identificar el endpoint: label `instance` del alert (probe_xxx).
2. Regenerar: `scripts/setup/gen_certs.sh` (o `make certs`) — regenera CA +
   certs de servicio en `infra/docker/config/certs/`.
3. Re-emitir el PEM embebido en el datasource template de Grafana
   (`secureJsonData.tlsCACert` lleva el PEM inline) y recrear:
   `docker compose up -d grafana prometheus loki tempo`.
4. Validar: `curl --cacert infra/docker/config/certs/ca.crt
   https://<svc>/ready` sin `-k`.

### RB-19 — `obs_container_restart_loop`

`increase(container_start_time_seconds[15m]) > 3` — un servicio reinicia en
bucle.

1. `docker ps --filter status=restarting` y `docker logs <svc> --tail 50`.
2. Causas frecuentes ya vistas:
   - `s3-vol2`: `su-exec: setgroups` — el `cap_drop: ALL` rompía el
     entrypoint; el servicio conserva `cap_add` justificada (ver ADR-0014).
   - `tempo`: `ListObjects AccessDenied` — IAM S3 sin permiso en el bucket
     (ver RB-20 / iam.config.json `policyNames`).
   - Scripts shell con CRLF → `set: illegal option -` (`.gitattributes`
     fija `*.sh eol=lf`; gate CI lo detecta con `od`).
3. Tras corregir la causa: `docker compose up -d <svc>` y confirmar
   `restart_count` estable.

### RB-20 — `obs_s3_objectstore_errors`

Errores `NoSuchBucket`/`AccessDenied` en logs de loki/tempo hacia SeaweedFS.

1. `docker logs soar_s3 --tail 50` y `docker logs soar_loki|soar_tempo |
   grep -i denied`.
2. IAM: `infra/docker/config/seaweedfs/iam.config.json` — cada componente
   usa credenciales propias con `policyNames` → policy con `Resource`
   ARN-scoped (`arn:aws:s3:::loki/*`). Verificación SigV4 en vivo:
   `tests/integration/test_observability_live.py::TestTLSAndS3`.
3. Buckets ausentes: `s3-init` los crea con probe write/read/delete —
   `docker logs soar_s3_init`.
4. Credenciales: rotadas en `.env` (`LOKI_S3_*`, `TEMPO_S3_*`); el par por
   defecto `soar-s3/soar-s3-secret-change-me` está REVOCADO (403).

### RB-21 — `obs_otel_spans_dropped`

`otelcol_processor_dropped_spans` o `otelcol_exporter_enqueue_failed_*` > 0.

1. `docker logs soar_otel_collector --tail 50` — `memory_limiter` activo?
   (soft limit ~82% del cgroup de 512m).
2. Cola saturada → Tempo no absorbe: check `https://tempo:3200/ready` y
   `soar_tempo` healthy; la sending_queue tiene retry con backoff.
3. Burst persistente: subir `memory_limiter.limit_mib` o el batch
   `send_batch_max_size` en `infra/docker/config/otel-collector-config.yaml`
   y recrear. Gate CI: `otelcol validate`.

### RB-22 — `obs_iscm_watchdog` (siempre firing — NIST 800-137 ISCM)

Heartbeat deliberado (`expr: vector(1)`, `noDataState: Alerting`, repite
cada 4h). Debe estar **firing permanentemente** — es la prueba de vida del
bucle eval→notify→API.

1. Si NO está firing: el pipeline de eval está roto → revisar Grafana logs
   (`Unified Alerting`), datasource Grafana-Prometheus, y que el ruleset
   provisionado carga (`/api/v1/provisioning/alert-rules` → 22 reglas).
2. Cada firing genera una notificación al contact point `soar-api-webhook`
   → la API incrementa su contador de alertas — es la señal que consume
   RB-23.

### RB-23 — `obs_alert_channel_silent`

La API no registró notificaciones de Grafana en >4.5h mientras el watchdog
debiera repetir cada 4h — el canal alerta→webhook está muerto aunque las
reglas evalúen.

1. `https://grafana:3000/alerting/notifications` — últimas entregas y
   errores del contact point `soar-api-webhook`.
2. `docker logs soar_grafana | grep -i notif` — TLS fallando contra
   `api:8000`? (el contact point usa HTTPS + lab CA).
3. Endpoint receptor: `POST /api/v1/alerts/grafana` con
   `Authorization: Service-Token $INTERNAL_SERVICE_TOKEN` — test vivo:
   `test_webhook_endpoint_accepts_synthetic_alert`.
4. Si el token rotó: actualizar `grafana-contact-points.yml` + `.env`.

## 4. Validación

### 4.1 Verificación

- `python scripts/quality/validate_dashboards.py` — contrato estático (0 violations).
- `pytest tests/e2e/TC-35` — 17 tests: render de cada panel, datasources,
  targets Prometheus, ES exporter green, reglas provisionadas con
  severity+summary, ninguna regla en `error|nodata`, anti-self-match, p99
  resoluble, descripciones presentes.

### 4.2 Matriz temporal (GRAF-010)

| Ventana | Qué validar | Resultado |
|---------|-------------|-----------|
| 24h | Todos los paneles renderizan con datos | verificado TC-35 |
| 7d | Agregaciones diarias legibles (interval auto) | `date_histogram` adapta buckets |
| 30d | KPI panels 4.x/5.x con `timeFrom:30d` muestran serie completa y badge "Last 30 days" | verificado render p5 |

### 4.3 Ownership, retención y seguridad (GRAF-059/060/053..055)

- **Owner**: equipo `soar-ops` (label `team` en cada regla; contact point al API).
- **Retención**: Loki según `loki-config.yml`; Prometheus local 15d por
  defecto; Tempo conforme a su config — suficiente para la matriz 30d.
- **Secretos**: password de Grafana solo en `.env`/`.env.full` (gitignored);
  el webhook usa `Service-Token` provisionado por env, nunca embebido en JSON.
- **Exposición**: Grafana publica 3000→8084 solo en el host; renderer, Loki,
  Tempo, exporter y Prometheus solo en la red interna `soar_net`.
- **Cardinalidad**: métricas nuevas (`soar_queue_*`, `soar_grafana_alert_*`)
  son gauges/contadores sin labels de alta cardinalidad; spanmetrics lleva
  `span_name`/`service`/`status_code` — acotado por el OTel collector.

## 5. Problemas y consideraciones

### 5.1 Limitaciones

- El entorno es single-host Docker Desktop: la "correlación host↔contenedor"
  se limita a cAdvisor + exporter; no hay node-exporter.
- `soar-kpi-main` p4.x/5.x usan `timeFrom: 30d` — en un lab de días de vida se
  verán series cortas al principio (es correcto, no datos ausentes).

### 5.2 Riesgos

- Disco: tras la migración a named volumes (2026-11-09) el exporter mide el
  VHDX Docker (~92% libre). El host C: sigue al ~95% — vigilar el panel "ES
  disk / heap pressure" (disco Docker) y `df -h` del host (RB-08).
- Una regla en `nodata` puede significar "sin datos" legítimo o "query rota" —
  `grafana_rule_eval_error` y el panel de estados los distinguen.

### 5.3 Entorno

`environment=lab` está documentado en el dashboard (`tags: [lab, soar]` y
descripciones). No hay selección multi-entorno: las variables de dominio
(`$service` en logs) están cerradas a valores conocidos para impedir mezclar
dominios (GRAF-004/005).

## 6. Referencias

- `infra/docker/compose/logging/alert-rules.yml` — reglas y anotaciones
- `scripts/quality/validate_dashboards.py` — validación estática (GRAF-038)
- `tests/e2e/TC-35/test_grafana_rendering.py` — contrato E2E
- `docs/19-eval-observability-stack.md` — evaluación ISO 25010 del stack
