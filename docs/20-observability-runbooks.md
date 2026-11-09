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
3. Renderer a 500 con timeout interno: revisar `CLUSTERING`/`maxConcurrency`
   en `docker-compose.logging.yml` (los nombres de env var importan).

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

- Disco del filesystem de datos de ES al ~94% (6% libre observado): vigilar el
  panel "ES disk / heap pressure"; si se cruza el watermark `flood_stage`,
  Elasticsearch bloquea escrituras y los índices pasan a read-only.
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
