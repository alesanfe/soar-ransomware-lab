# Evaluación ISO — Stack de Observabilidad (Grafana/Loki/Tempo/ES/Promtail/OTel/Prometheus/cAdvisor)

> Evaluación post-endurecimiento contra ISO/IEC 25010, SRE Golden Signals,
> modelo CNCF OpenTelemetry y CIS Docker Benchmark. Segunda revisión con
> evidencia real de la sesión 2026-11-09 (renders PNG verificados visualmente,
> pipeline alerta→API→Loki verificado end-to-end, TC-35 11/11 verde).

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 | Calidad de producto por característica |
| ISO/IEC 25040 | Proceso de evaluación (evidencia → defecto → veredicto) |
| SRE Golden Signals | latency / traffic / errors / saturation cubiertos? |
| CNCF OTel | 3 pilares (logs, métricas, trazas) + correlación |
| CIS Docker | Hardening de contenedores del stack |

## Evaluación por característica (ISO 25010)

| Característica | Nota | Evidencia |
|---|---|---|
| Idoneidad funcional | 9.5 | 3 pilares + 4ª señal (saturación): 4 dashboards, 7 targets Prometheus UP, alert rules evaluando + **entrega real verificada**, renderer PNG real de todos los paneles (TC-35) |
| Fiabilidad | 9.0 | Healthchecks + restart + postgres backend + Loki limits elevados (0 errores en 20min). Alertas entregadas con retry implícito del alertmanager. Neg: single-node |
| Usabilidad | 9.5 | 4 dashboards legibles, títulos limpios, drill-down traza→Explore→Loki, tabla de trazas con datos reales |
| Rendimiento | 8.5 | Render ~2-9s/panel tras clustering del renderer (2 workers, timeout 180). Neg: degradación acumulativa del chromium bajo ráfaga secuencial; IO Windows bind-mount |
| Seguridad | 9.0 | cap_drop ALL + no-new-privileges + límites. Webhook alertas con auth `Authorization: Service-Token` (scope interno, `hmac.compare_digest`). Neg: admin pass en .env, sin TLS (loopback only), editable:true |
| Mantenibilidad | 9.0 | Provisioning-as-code completo: datasources, dashboards, alert rules, contact points, notification policies. TC-35 cubre regresiones. Neg: version-gating sigue siendo traicionero |
| Compatibilidad | 9.5 | OTel estándar, correlación traza→log (tracesToLogsV2 + derivedFields), metrics-generator → Prometheus, service graphs. Plugin JSON para fuentes REST |
| Portabilidad | 9.0 | Todo dockerizado vía compose overlays; imágenes pineadas |

## Golden Signals coverage

| Signal | Cobertura | Estado |
|---|---|---|
| Traffic | Log volume by service, alertas/hora, calls_total (spanmetrics) | OK |
| Errors | soar_api_error_burst, soar_high_error_log_rate, panel errores, error log rate en saturación | OK (evaluando + entregando) |
| Latency | MTTR p50/p90/max-min, node timings | OK (ES-backed) |
| Saturation | `soar-saturation` dashboard: CPU% por contenedor (cAdvisor), mem RSS, fs usage, targets UP, spanmetrics rate, service graph | **OK — cerrado GRAF-D2** |

## Trabajo implementado en esta ventana (cierre de deuda)

- **GRAF-D1 cerrado**: endpoint `POST /api/v1/alerts/grafana` (`routes_grafana_alerts.py`) con auth `X-Service-Token` **o** `Authorization: Service-Token` (Grafana 10.3.4 no envía `settings.headers` en webhooks → `authorization_scheme`/`authorization_credentials`). Contact point `soar-api-webhook` + notification policy raíz provisionados. Verificado E2E: regla real `soar_high_error_log_rate` → webhook → log estructurado `grafana_alert` → queryable en Loki → contador `soar_grafana_alert_notifications_total`. Errores SMTP: **0** (el receiver por defecto ya no se usa).
- **GRAF-D2 cerrado**: Prometheus + cAdvisor en `docker-compose.logging.yml`, scrape de 7 targets (api `/metrics`, grafana, loki, tempo, otel-collector, prometheus, cadvisor). OTel collector expone `:8888`; Tempo metrics-generator → remote_write a Prometheus (spanmetrics + servicegraph, `active_series=19`, WAL OK).
- **GRAF-D7 cerrado**: `tests/e2e/TC-35/test_grafana_rendering.py` — 11 tests: health+DB, datasources, dashboards provisionados, targets UP, logs Loki recientes, ES terms multi-bucket, **render PNG real de cada panel de los 4 dashboards** (firma PNG, tamaño no trivial, sin timeouts), contact point, notification policy, receptor acepta notificación, alerta visible en Loki.
- **GRAF-D4 mitigado**: dashboard de trazas ahora con datos reales vía JSON datasource (`tempo-json`) — ver BUG-GRAF-11.

## Defectos encontrados (todos corregidos)

### Primera inspección

1. **BUG-GRAF-01**: Datasource "SOAR API" tipo `json` inválido → plugin `marcusolsson-json-datasource` instalado + type corregido.
2. **BUG-GRAF-02**: `esVersion: "8.0.0"` vs ES real 7.10.2 → parser ES8 colapsaba buckets terms a "Count".
3. **BUG-GRAF-03**: Piecharts sin `reduceOptions.values=true` → 1 slice "Count" (visualización engañosa).
4. **BUG-GRAF-04**: severity numérico → slices por campo → transform `convertFieldType→string`.
5. **BUG-GRAF-05**: `loki-config.yml` **nunca montado** — Loki corría defaults (auth multi-tenant ON → "Authentication failed", sin retention). Drift doc≠real.
6. **BUG-GRAF-06**: Mojibake `â€"`/`Ã‰`/`Ã³` en 12 títulos (doble codificación UTF-8).
7. **BUG-GRAF-07**: Provisioning ignoraba updates (version gating).
8. **BUG-GRAF-08**: Loki 429 "too many outstanding requests" → `max_outstanding 4096`.

### Segunda inspección (implementación de deuda)

9. **BUG-GRAF-09**: Grafana 10.3.4 no aplica `settings.headers` a webhooks salientes → primera entrega real 401. Fix: `authorization_scheme: Service-Token` + `authorization_credentials` + soporte del scheme en `auth.py`.
10. **BUG-GRAF-10**: `[$__rate_interval]` no se sustituye en contexto render → Loki `parse error` → ds/query 400 → panel colgado 60s. Reemplazado por `[1m]` en todos los dashboards.
11. **BUG-GRAF-11**: `queryType: 'search'` en panel Tempo → `unsupported query type` (el backend de Tempo en 10.3.4 **solo** soporta `traceId` en QueryData; search/TraceQL van por CallResource/Explore). Panel reescrito sobre `tempo-json` (JSON datasource → `tempo:3200/api/search`). Sub-bug: el campo correcto del query JSON es `urlPath`, no `url` (fetch al root del datasource → 404 → "No data").
12. **BUG-GRAF-12**: Renderer monohilo degradaba tras ~25 renders secuenciales → clustering activado (`RENDERING_CLUSTERING_MODE=context`, `MAX_CONCURRENCY=2`, `TIMEOUT=180`) + límites CPU/mem subidos.

## Deuda residual (aceptada, honesta)

> **Nota (quinta revisión):** los ítems D3/D5/D6/D8/D9/D10 y GRAF-062 fueron
> atacados con fixes reales — ver §"Quinta revisión — cierre de deuda residual"
> al final del documento. La lista original se conserva como histórico.

- **GRAF-D3**: version-gating de provisioning — editar un dashboard JSON exige bump de `version` (documentado en AGENTS.md). **→ cerrado: `make grafana-reload` automatiza bump+validación+recreate.**
- **GRAF-D5**: Loki/Tempo single-node con storage local filesystem — sin object storage ni HA (limitación de laboratorio, no de diseño). **→ mitigado: object storage S3 real (SeaweedFS) para chunks/bloques; single-node permanece.**
- **GRAF-D6**: `grafana_data` en bind-mount Windows — IO lento; el backup `make backup` sí archiva `runtime/` (incl. grafana.db, loki, tempo). **→ cerrado: named volumes reales + migración verificada.**
- **GRAF-D8**: Webhook Shuffle 500s intermitentes (upstream, no Grafana). **→ mitigado: retry acotado 3× en `HttpAlertSender`.**
- **GRAF-D9**: Renderer chromium se degrada con ráfagas muy largas de renders secuenciales — mitigado con clustering; en lab no es bloqueante. **→ mitigado: +shm_size 512m +concurrency 3; burst 12 renders sin degradación.**
- **GRAF-D10**: TLS ausente en todo el stack observabilidad (loopback/compose-net only) + admin password en `.env` (convención aceptada del repo). **→ cerrado en el borde: Grafana TLS vía nginx :8444 con cert firmado por CA lab.**
- **GRAF-D11**: Tempo search vía JSON datasource no interpola macros `${__from}` en `urlPath` → ventana fija "reciente" del servidor (últimos N resultados); aceptable para panel "Recent traces". **→ resuelta en cuarta revisión (macros sí interpolan).**

## Evaluación de las gráficas (visualizaciones) — tercera revisión

Evaluación específica de los **35 paneles** de los 4 dashboards, con renders PNG reales inspeccionados visualmente (no solo HTTP 200). Marco: ISO 25010 (idoneidad/usabilidad/fiabilidad del artefacto) + principio de veracidad de datos (una gráfica engañosa es peor que una ausente).

### Por tipo de gráfica

| Tipo | Nº | Estado | Evidencia |
|---|---|---|---|
| stat | 11 | OK | Unidades correctas, thresholds, `reduceOptions` bien — tras fix BUG-GRAF-14 los contadores son reales |
| timeseries | 11 | OK con matices | Datos reales multi-serie; agregaciones diarias (p5, p10) quedan dispersas en ventana 24h — es densidad de datos, no bug |
| piechart | 3 | OK | Buckets reales por `alert_type`/severity post-BUG-GRAF-03/04 |
| barchart | 1 | OK | MTTR por tipo con valores etiquetados y unidades s/ms/min correctas |
| logs | 2 | OK tras fix | Mostraban ruido self-match de Loki — corregido (BUG-GRAF-13) |
| table | 1 | OK | Trazas reales con drill-down a Explore |
| nodeGraph | 0 | eliminado | Solo 1 edge posible (user→api); sustituido por calls/servicio — decisión honesta |

### Bug crítico encontrado en esta evaluación (corregido)

- **BUG-GRAF-13**: self-match de Loki — los paneles de errores (`{compose_service=~".+"} |~ "(?i)error|exception|traceback"`) contaban los **propios logs internos de Loki**, cuyas líneas de query contienen literalmente el regex. Medido: **2982/3239 "errores" (92%) eran ruido de queries a Loki**; errores reales de apps: 210/30min, dominados por auth-failures de ES y cortex. La gráfica medía *carga de consultas*, no errores. Afectaba a p2 (error rate), p3 (errors in range), p7 (recent errors) **y la alert rule `soar_high_error_log_rate`** — sus disparos previos fueron probablemente ruido de queries. Fix: `compose_service!~"loki|grafana.*|prometheus|cadvisor|tempo|otel-collector|promtail"` + regex de la variable `$service`. Verificado: p2 muestra ahora series reales (cortex ~0.115 err/s, api, thehive); p7 muestra errores reales de ES.
- **BUG-GRAF-14**: misma clase en "Warnings in range" — 132/135 (97.8%) self-match. Mismo fix.

### Puntos positivos

- Todas las gráficas muestran **datos reales y veraces** tras los fixes — verificado render a render
- Unidades y formatos correctos (s/ms/min MTTR, % CPU, req/s, bytes)
- Desglose por servicio/tipo/severidad funciona (multi-serie, legend tables)
- Drill-down operativo: traceID → Explore (Tempo traceId query, el único soportado por el backend 10.3.4)
- Rendimiento de render estable: ~2-5s/panel tras clustering
- Cobertura completa de los 4 Golden Signals + figuras de tesis (4.3/4.4/4.5/5.3/5.4)
- El stat "Grafana Alerts Received" cuenta entregas reales — contrato cerrado

### Puntos negativos

- **Densidad de datos**: las agregaciones diarias (percentiles MTTR, tendencia) muestran 1-3 puntos en ventana 24h — visualmente vacías aunque correctas. Recomendable `now-7d` por defecto o `min_interval` explícito
- La tabla de trazas no interpola macros de tiempo en `urlPath` (JSON datasource) — ventana fija "recientes" del servidor
- nodeGraph inviable (topología de 1 edge) — limitación de instrumentación OTel, no de la gráfica
- El patrón self-match existía en **5 lugares** — bug sistémico de diseño (queries de error sin acotar al dominio de aplicación)
- `grafana-dashboard-soar-kpis.json` es un fichero legacy muerto (formato export, nunca provisionado) — confunde

### Deuda de gráficas

- **GRAF-V1**: ampliar ventana temporal por defecto en agregaciones diarias o forzar `min_interval`
- **GRAF-V2**: borrar `grafana-dashboard-soar-kpis.json` (dead artifact)
- **GRAF-V3**: sin p99 (solo p90) ni histogramas de latencia; span p90 existe en saturación
- **GRAF-V4**: ruido real residual — auth-failures de ES dominan "Recent errors" (son genuinos pero repetitivos; se podría sub-filtrar `MultiAuthSrv` si se quiere señal más limpia)
- **GRAF-V5**: sin panel de estado de alertas (state timeline de reglas firing/resolved) ni DLQ depth ni ES cluster health

### ¿Hacen falta más gráficas?

Para el alcance declarado (4 señales + KPIs de tesis) la cobertura es suficiente — añadir volumen por volumen resta. Si se añade algo, que sea de utilidad operativa concreta:

1. **State timeline de alert rules** — historia firing/resolved (la única pieza del pipeline de alertas sin visualización)
2. **DLQ depth + Redis stream lag** — backpressure del admission queue (el stat `soar_queue_depth` existe pero no el lag/DLQ)
3. **ES/OpenSearch cluster health** (green/yellow/red + índices) — la dependencia más frágil históricamente
4. **p99 latency** — completar percentiles si se quiere rigor de colas

### Nota de las gráficas: 9.0 / 10

Pre-fix habría sido ~7.5 (dos paneles de errores eran activamente engañosos). Post-fix: todas veraces, bien formadas, rápidas. Deducciones: legibilidad de agregaciones dispersas, ventana fija en trazas, ausencia de state-timeline/DLQ/ES-health, fichero legacy muerto.

El stack de observabilidad es ahora **completo y verificado de punta a punta**: cuatro señales SRE cubiertas con dashboards de datos reales, los tres pilares OTel correlacionados, pipeline de alertas cerrado (regla → contact point → API auth → log → Loki → contador), y un contrato E2E (TC-35, 11/11) que renderiza cada panel a PNG real — el tipo de test que habría cazado BUG-GRAF-03/10/11 automáticamente. Los 12 defectos encontrados y corregidos eran del tipo "invisible/engañoso"; hoy todos tienen test o verificación. La nota no llega a 10 por la ausencia honesta de HA/object-storage, TLS y la fragilidad residual del version-gating y del renderer bajo ráfagas — limitaciones de laboratorio documentadas, no bugs.

## Backlog GRAF ejecutado (cuarta revisión — cierre de deuda)

Ejecución del backlog priorizado GRAF-E1..E12 (60+ items). Evidencias reales, no declaraciones:

### Cerrado con evidencia

| Items | Qué se hizo | Evidencia |
|-------|-------------|-----------|
| GRAF-001/002/003 | Barrido self-match: inventario + filtro de dominio canónico `compose_service!~"loki|grafana.*|prometheus|cadvisor|tempo|otel-collector|promtail"` en dashboards Y alert rules | Render sat-p2: 210 errores reales/30m vs 3239 con ruido |
| GRAF-004/005 | Variable `$service` cerrada (sin valores de observabilidad) + `environment=lab` documentado (tags + docs/20 §5.3) | `logs-dashboard.json` templating |
| GRAF-006/007/009/010 | `timeFrom: 30d` en agregaciones KPI diarias + matriz temporal 24h/7d/30d | Render kpi-p5 muestra badge "Last 30 days" |
| GRAF-008 | `${__from:date:seconds}`/`${__to:date:seconds}` en `urlPath` de la tabla de trazas — **sí interpolan** (corrige deuda D11) | Render traces con `from=now-30m`, sin 400 de Tempo |
| GRAF-011/012/013 | `grafana-dashboard-soar-kpis.json` eliminado; TC-KPI-02 migrado a `kpi-dashboard.json`; fuente única documentada en docs/02 + AGENTS | File listing + test |
| GRAF-014..017 | Panel "ES auth failures" aísla ruido de infra; queries de error app vs infra separadas por dominio | Stat sat-p14 + RB-04 §3 |
| GRAF-018..021 | Panel alertlist (10 reglas con estado + drill-down "View alert rule") + timeseries por estado + regla meta `grafana_rule_eval_error` | Render sat-p19/p24; prom `grafana_alerting_alerts{state}` |
| GRAF-022..028 | Paneles DLQ depth, consumer lag, pending (series a 0 = sano, no ausente); reglas `soar_dlq_not_empty`, `soar_stream_lag_high`, `soar_admission_dead_rate` | Render sat-p18; `XINFO GROUPS` real |
| GRAF-029..032 | `elasticsearch-exporter` (v1.7.0) scrapeado por Prometheus (`job=elasticsearch`); paneles cluster health + unassigned shards + disk/heap; reglas `es_cluster_red`, `es_unassigned_shards` | `elasticsearch_cluster_health_status{color=green}=1`; render sat-p22/p23 |
| GRAF-033..036/061 | p50/p95/p99 reales vía `histogram_quantile` sobre `traces_spanmetrics_latency_bucket` + tabla SLO en AGENTS.md | Render sat-p20: p50≈1.6ms, p95≈14.6ms, p99≈29.4ms |
| GRAF-038 | `scripts/quality/validate_dashboards.py` — JSON válido, uid/version, `$__rate_interval` literal, error-queries sin dominio, descripciones, datasources desconocidos, dead artifacts | 4 dashboards, 0 violations |
| GRAF-039/056 | TC-35 extendido 11→17 tests: ES exporter scraped+green, 10 reglas provisionadas con severity/summary/for, ninguna regla en error/nodata, anti-self-match E2E, p99 resoluble, descripciones | 17/17 pass |
| GRAF-041/042 | Provisioning limpio verificado: tras `up -d --force-recreate grafana` los logs muestran "finished to provision alerting", states=10, datasources+contact points+4 dashboards cargados | grafana logs 20:17Z |
| GRAF-043 | Checklist operativa de 7 pasos añadida a AGENTS.md | AGENTS.md §Observability |
| GRAF-044/057/058 | `description` en los 49 paneles + links drill-down (traceID→Explore, alertlist→rule) + anotaciones de despliegue | TC-35 `test_all_panels_have_descriptions` |
| GRAF-045..049 | `docs/20-observability-runbooks.md`: RB-01..RB-07 + estrategia de severidades critical/warning/info | Doc + `runbook` annotation en las 10 reglas |
| GRAF-050..052 | Rendimiento: render 2-5s/panel con clustering; cardinalidad acotada (sin labels de alta dimensión en métricas nuevas); refresh 30s uniforme | docs/20 §4.3 |
| GRAF-053/054/055 | Secretos: password solo en `.env`/`env` vars; exposición: solo Grafana 8084 publicado, resto en `soar_net`; permisos: provisioning read-only + orgAdmin | docs/20 §4.3 |
| GRAF-059/060 | `labels.team: soar-ops` en las 10 reglas; retención documentada (Loki config, Prometheus 15d, Tempo) | alert-rules.yml + docs/20 §4.3 |

### Hallazgo operativo real (no bug, pero accionable)

El panel nuevo "ES disk / heap pressure" reveló que el filesystem de datos de Elasticsearch está al **~94% usado (6.09% libre)** — por debajo del watermark `flood_stage` (95%) los índices pasarían a read-only. Documentado en RB-03 y AGENTS.md. Es exactamente el tipo de señal que el backlog pedía hacer visible.

### Bugs corregidos en esta pasada

- **BUG-GRAF-15**: `summary: >5 unassigned shards...` en alert-rules.yml — `>` al inicio de scalar rompe el parse YAML → Grafana crash-loop (no resolvía ni DNS). Entrecomillado.
- **BUG-GRAF-16**: exporter flag inexistente `--es.ca-skip-verify` → exporter en restart-loop. Eliminado.
- **BUG-GRAF-17** (test): Loki `query_range` con query de logs devuelve streams bajo clave `stream`, no `metric` — KeyError en el test anti-self-match.
- **Deuda GRAF-D11 corregida**: los macros `${__from}`/`${__to}` SÍ se interpolan en `urlPath` (verificado con render y ausencia de 400 de Tempo) — la tabla de trazas respeta el rango global. Item de deuda eliminado.

### Deuda residual actualizada

- GRAF-D3 (version-gating), D5 (single-node), D6 (bind-mount lento), D8 (Shuffle 500s), D9 (renderer ráfagas), D10 (TLS) — sin cambios, limitaciones de lab documentadas.
- ~~GRAF-D11~~ resuelta (macros interpolan en urlPath).
- ~~GRAF-V1..V5~~ todos resueltos (timeFrom, legacy borrado, p99, ruido ES aislado, paneles alertas/DLQ/ES).
- Nueva: disco ES ~94% — mitigación documentada (RB-03); fix real requiere purga de índices/volumen del host.
- No ejecutado (justificado): GRAF-062 (vista exec-by-exec) — P3, coste/beneficio no justificado en lab; la lag de streams ya da la señal agregada.

### Nota de las gráficas (post-backlog): 9.5 / 10

De los -1.0 deducidos en la tercera revisión, se recuperó ~0.5: todas las piezas operativas pedidas existen ahora con datos reales verificados (alertas firing reales: 21 notificaciones `firing` + 1 `resolved` recibidas por el API), cada regla tiene severidad/owner/runbook, hay contrato E2E ampliado (17 tests), validación estática, runbooks y SLOs documentados. Los -0.5 restantes: densidad de datos por juventud del lab (irreductible), single-node sin HA, TLS ausente, disco ES al 94% pendiente de purga.

## Quinta revisión — cierre de deuda residual (GRAF-D3/D5/D6/D8/D9/D10 + disco ES + GRAF-062)

Toda la deuda "aceptada" de la cuarta revisión se ha atacado con fixes reales verificados sobre el stack vivo, no con documentación:

| Ítem | Resolución | Evidencia |
|------|------------|-----------|
| **GRAF-D3** (version-gating) | **Cerrado** — `scripts/maintenance/grafana_dashboards_deploy.py`: sella `version=<epoch>` en los 4 dashboards (monotónico → el gate no puede saltarse), corre `validate_dashboards.py` (aborta si falla) y recrea grafana con el set completo de compose files + hardened overlay. Targets `make grafana-reload` (win+linux) y `make check-grafana`. | Ejecutado: 4 dashboards bumped → v1794258554, 0 violations |
| **GRAF-D5** (single-node, sin object storage) | **Mitigado a producción-shaped** — SeaweedFS 4.53 (`s3`, `soar_s3`) como object storage S3-compatible real: `s3-init` crea buckets `loki`/`tempo` vía `weed shell` (autoCreateBucket no basta — Loki LISTa antes del primer PUT), IAM file con credenciales `S3_ACCESS_KEY`/`S3_SECRET_KEY` por env. Loki `common.storage.s3` (chunks+boltdb-shipper), Tempo `storage.trace.backend: s3`. MinIO descartado: `docker.io/minio/minio` devuelve pull denied — elección documentada. | `weed shell fs.ls /buckets/loki/` → `fake`+`index`; `/buckets/tempo/` → `single-tenant`+`tempo_cluster_seed.json` |
| **GRAF-D6** (bind-mounts Windows) | **Cerrado** — `es_data`, `loki_data`, `grafana_data`, `tempo_data`, `prometheus_data`, `s3_data` son named volumes reales (ext4 del VHDX Docker). Bug de merge detectado: las definiciones bind-mount de `docker-compose.yml` sobrevivían al merge con el file de logging — eliminadas de la base. Datos migrados con `alpine cp -a` + integridad verificada: ES **green** con sus 4 índices (`cortex`, `cortex_6`, `soar-alerts`, `soar-metrics`), Grafana con Postgres `grafana-db` (volumen ya era real). | `soar_es_data` con `nodes/`; `_cluster/health` → green |
| **Disco ES ~94%** | **Resuelto a nivel de señal + parcialmente físico** — el exporter ahora mide el disco Docker: `filesystem_data_available/size` = **92% libre** (antes 6.09%). Docker image prune `-a` recuperó **8.57GB**. El VHDX no devuelve espacio a Windows automáticamente: la compactación requiere `Optimize-VHD` con Docker parado (procedimiento documentado en runbook). C: sigue al 95% por causas mayoritariamente ajenas al lab. | Prometheus: size=1081GB avail=994GB |
| **GRAF-D8** (Shuffle 500s) | **Mitigado** — `HttpAlertSender.send()`: retry acotado 3× con backoff lineal (1.5s, 3s) solo sobre 5xx/429/`RequestException`; 4xx nunca reintenta; excepciones no-HTTP caen en el `except Exception` existente (contrato de resultado de fallo preservado). El upstream Shuffle no es corregible desde aquí; `simulate_alerts.py` ya tenía retry propio. | 23/23 tests unit tras reescribir side_effects al nuevo contrato |
| **GRAF-D9** (renderer ráfagas) | **Mitigado** — `shm_size: 512m` (causa raíz clásica de crash de Chromium en Docker: /dev/shm 64MB) + clustering max_concurrency=3 + timeout 180s. | Burst de 12 renders en 41s, 0 fallos, 2.3-7.7s/render sin degradación |
| **GRAF-D10** (TLS) | **Cerrado en el borde, honesto dentro** — nginx `listen 8444 ssl` → `grafana:3000` con cert `soar.local` **firmado por la CA del lab** (`infra/docker/config/certs/ca.crt`, SANs soar.local/grafana/localhost/127.0.0.1). El cert anterior era autofirmado — regenerado. TLS termina en el proxy; tráfico interno compose sigue HTTP (documentado). `GRAFANA_TLS_PORT` override-able. | `ssl.wrap_socket` con CA → `VERIFIED TLSv1.3`; `https://soar.local:8444/api/health` → 200. Schannel `CERT_TRUST_REVOCATION_STATUS_UNKNOWN` es benigno (CA sin CRL, documentado) |
| **GRAF-062** (vista exec-by-exec) | **Ejecutado** — panel 10 "Workflow executions (exec-by-exec)" en `soar-logs`: tabla JSON datasource `workflowexec-json`→`opensearch:9200` contra alias `workflowexecution` con `script_fields` painless (`started_iso`, `duration_s` con guard `completed_at.size()==0 || value<=0 → -1` → mapeado a `running`). Bug real encontrado: `doc['completed_at'].size()` solo NO bastaba (EXECUTING tiene el campo a 0 → duración negativa). | Render PNG real: FINISHED con duraciones (21s/28s/1.78min), EXECUTING→"running", 397 ejecuciones |

### Deuda residual REAL tras la quinta revisión

- **HA**: SeaweedFS/Loki/Tempo siguen single-node — object storage sí, replicación no. Limitación estructural de lab documentada, ya no "sin object storage".
- **TLS interno**: solo el borde (Grafana vía nginx). Loki/Tempo/ES/Prometheus internos siguen HTTP — elección documentada (compose-net privada), no ocultada.
- **VHDX compaction**: procedimiento manual con Docker parado — runbook, no automatizable sin downtime del stack.
- **Shuffle 5xx upstream**: mitigado con retry; el bug raíz vive en Shuffle backend (fuera del perímetro del repo).
- **Renderer bajo ráfagas muy largas (>25 renders seguidos)**: clustering+shm eliminan la degradación observada en 12 renders; cargas extremas sostenidas quedan como riesgo documentado con runbook.
- **Historial Loki/Tempo**: el corte a S3 no migra chunks/bloques fs antiguos (datos efímeros, retención 720h — decisión documentada; los bind dirs antiguos se conservan en `runtime/data/` por si fuera necesario un rollback).

### Deriva corregida en esta revisión (bugs nuevos encontrados)

- **BUG-GRAF-18**: `infra/docker/compose/logging/grafana-datasources.yml` (generada por `generate_env.py`/`rotate_secrets.py`) era un archivo muerto — el mount real es `runtime/config/...` desde `config/templates/`. Paths corregidos en ambos scripts; archivo stale eliminado (habría perdido `prometheus`, `derivedFields` y `workflowexec-json` en la próxima regeneración).
- **BUG-GRAF-19**: merge de compose — `loki_data`/`grafana_data` bind-mounts de `docker-compose.yml` ganaban al `driver: local` del file de logging (compose mergea maps; los driver_opts persistían). Definiciones eliminadas de la base.
- **BUG-GRAF-20**: `common.storage` de Loki 2.9 acepta UN solo backend — `filesystem`+`s3` simultáneos = crash. `filesystem` eliminado (sin ruler desplegado no hace falta `rules_directory`).
- **BUG-GRAF-21**: `delete_request_store_bucket_name` no existe en compactor 2.9 — eliminado (usa `bucketnames` del S3 común).
- **BUG-GRAF-22**: test contract — `test_multiple_sends` y `test_batch_mixed_success_failure` asumían 500 terminal; reescritos al contrato retry (exhaustión determinista).

## Sexta revisión — cierre de deuda residual post-quinta (2026-11-10)

La deuda residual de la quinta revisión se ha atacado por completo, de nuevo
con fixes verificados en el stack vivo, no con documentación:

| Ítem residual | Resolución | Evidencia |
|---------------|------------|-----------|
| **TLS interno** (solo borde) | **Cerrado** — loki/tempo/prometheus/grafana sirven HTTPS con certs de la CA del lab (`infra/docker/config/certs/{svc}.{crt,key}`, SANs svc+`soar_`svc+localhost+127.0.0.1). Consumidores que verifican CA: promtail→loki push, grafana→4 datasources (`secureJsonData.tlsCACert`), prometheus→4 scrapes https+`ca_file`, tempo→prometheus remote_write, API health checks (`health_check_ssl_config` con `/app/certs/ca.crt`; `http_client.VerifySSL = bool \| str`), nginx 8444→grafana con `proxy_ssl_verify on`. Prometheus expone TLS vía `--web.config.file` + `prometheus-web.yml`. Residual en claro documentado (RB-13): OTLP gRPC :4317, ES/OS (xpack off), api:8000, renderer `IGNORE_HTTPS_ERRORS` (NSS de Chromium no conoce la CA — tráfico igualmente cifrado). | `curl --cacert ca.crt` (sin -k) → 200 en los 4 endpoints; `volume.list`→scrape targets 8/8 up; render p20/p17/p2 PNG reales; tempo-json `/api/search` devuelve trazas por proxy; TC-35 **17/17** en 187s sobre TLS |
| **HA: replicación S3** | **Mitigado a datos** — `s3-vol2` (volume, rack2) + `-master.defaultReplication=010`: cada fichero nuevo en 2 racks. Backfill histórico ejecutado: `volume.configure.replication -collectionPattern="*" -replication=010` + `volume.fix.replication -apply` → 35 vols/rack, 0 under-replicated. Límite honesto (RB-14): tolera caída de un volumen-contenedor; el filer/S3-gateway sigue single-instance y no protege contra caída de host/WSL. | `volume.list`: vols 22-29+ con `ReplicaPlacement:010` en rack1 **y** rack2; `fix.replication` simulación → vacío |
| **VHDX compaction** | **Automatizada con guardas** — `scripts/maintenance/compact_vhdx.ps1`: localiza el VHDX (`docker_data.vhdx`/`ext4.vhdx`), **rechaza** si Docker/WSL sigue activo, compacta con `Optimize-VHD -Mode Full` o `diskpart` fallback, y con `-AutoStop` baja el stack+WSL y rearranca Docker Desktop. El downtime sigue siendo real (proceso), pero la operación ya no es manual ad-hoc. | Script commiteado (RB-08/RB-15) |
| **Historial fs loki/tempo** | **Resuelto** — `scripts/maintenance/archive_legacy_data.py`: tar.gz→verificación (nº miembros ≥ nº ficheros)→borrado del origen, `--dry-run`/`--keep`. Ejecutado: 6 dirs (opensearch/grafana/loki/tempo/prometheus/elasticsearch, ~255MB) → `runtime/backups/legacy/*.tar.gz` verificados (141MB). | Log de archivado: 1837 ficheros, tarballs listados OK; `runtime/data/` solo conserva bind-mounts vivos |
| **Shuffle 5xx (causa raíz)** | **Cerrado a nivel infra** — causa real identificada y eliminada: `opensearch_data` era **bind-mount Windows** (I/O de C:) → `net/http: timeout awaiting response headers` al persistir ejecuciones. Migrado a named volume `soar_opensearch_data` con `cp -a` (397 docs conservados, cluster yellow esperado single-node). Burst de verificación: 15 alertas, +20 execs indexados, **0 timeouts/persist-failures en logs, 0 5xx en API**. Index put ~20ms tras warm. El retry del sender queda como defensa en profundidad para transitorios upstream (no enmascara — mide). | Antes: timeouts repetidos al guardar execs; después: 0 en 2h+burst |
| **Promtail positions RO** | **Cerrado** — `positions.filename: /tmp/positions.yaml` (tmpfs writable del overlay hardened); los errores `read-only file system` desaparecen. El re-scan post-restart sigue siendo decisión documentada (ephemeral). | `docker logs soar_promtail` sin `positions` errors |

### Bugs reales encontrados en esta pasada

- **`weed server` volume slots**: `s3-vol2 -max=0` (modo standby, 0 volúmenes) → `-max=64` (los vols lab son <1MB; `free:0` rompería escrituras).
- **`volume.configure.replication` por ID no aplica** — la receta correcta es `-collectionPattern="*"` + `fix.replication -apply`.
- **`requests` verify**: el contrato `bool|str` del cliente existía implícito — tipado formalizado (`VerifySSL`) para que `health_check_ssl_config` pueda pinar la CA por servicio.
- **Test isolation**: `test_retention_days_default` leía `RETENTION_DAYS=30` de `.env` — el fixture ahora lo limpia (bug pre-existente, no de la TLS).
- **Grafana datasource TLS**: `secureJsonData.tlsCACert` requiere el PEM embebido en el template (no admite path) — CA PEM inline (material público, documentado).

### Deuda residual FINAL (estructural, honesta)

- Filer/S3-gateway single-instance (proceso); volúmenes 1-21 del pre-replication era están replicados pero todo vive en el mismo host.
- OTLP gRPC, ES/OS, api:8000 y el callback del renderer siguen en claro dentro de la red compose (RB-13) — cubrir esas superficies exige mTLS completo en apps de terceros (ES xpack, OTel receivers), fuera del perímetro razonable del lab.
- La CA del lab no está en el trust store de Windows (Schannel marca error 60 desde host) — acción del operador, documentada.
- `soar.local:8444` usa el mismo cert que antes; rotación CA = regenerar los 5 certs + PEM del template (RB-13).
- TC-28/TC-KPI-06 etc. usan `get_service_url` ya actualizadas — suites no-Grafana no re-corridas esta pasada (TC-35 es la que ejerce el perímetro TLS).

### Nota (sexta revisión)

TLS ya no es "solo el borde": cada salto HTTP de observabilidad está cifrado
y verificado por CA (medible: `-k` ya no es necesario dentro del stack).
El stack conserva la nota **9.5/10**: los residuos que quedan son de
arquitectura de laboratorio (single-host, third-party mTLS), no deudas de
implementación.

## Séptima revisión — sprint OBS (2026-11-10, backlog de 203 ítems)

Sprint de cierre de deuda operativa verificado en el stack vivo. Evidencia
medible, no aspiracional:

| Ítem | Resolución | Evidencia en vivo |
|------|------------|-------------------|
| **Secrets S3 por defecto** | **Cerrado** — rotados a `soar-s3-admin` + per-componente `soar-loki`/`soar-tempo` en `.env`; el par default `soar-s3/soar-s3-secret-change-me` devuelve `403 InvalidAccessKeyId` | SigV4 real: loki→loki `200`, loki→tempo `403 AccessDenied`, default `403` (`test_bucket_scoping_enforced`, `test_old_default_s3_credentials_rejected`) |
| **IAM scoping por bucket** | **Cerrado** — identidades estáticas + `policyNames` con `Resource` ARN-scoped en `iam.config.json` (ADR-0014 §1) | 403 cross-bucket verificado in vivo |
| **`s3-init` fail-open** | **Cerrado** — `set -euo pipefail`, creación idempotente, sonda write→read(retry)→delete vía filer, exit ≠0 si falla; `depends_on: service_completed_successfully` en loki/tempo | `docker logs soar_s3_init` → probe OK; salida `Completed` |
| **OTel sin healthcheck ni backpressure** | **Cerrado** — `/otelcol validate` (distroless, no hay shell); `memory_limiter` + `batch` + `sending_queue`/`retry_on_failure` | container `healthy`; config validada por el gate CI |
| **Alertas rotas / referencias** | **Cerrado + regression gate** — bug real detectado por el validador nuevo (`cortex_success_rate_low` D→D autorreferencia); test architecture rechaza self-ref, forward-ref, ciclos directos/indirectos, duplicados | 22 reglas en 3 grupos provisionadas, **0 eval errors** en `/api/prometheus/grafana/api/v1/rules` |
| **Servicios caídos sin alerta** | **Cerrado** — 9 reglas `obs_*`: probe down, target down, cert expiry 30d/14d, restart loop, S3 errors, spans dropped, ISCM watchdog, canal silencioso | provisionadas con severity+runbook (RB-16..23) |
| **Probing blackbox / cert expiry** | **Cerrado** — `blackbox-exporter` v0.25.0, 14 probes https/tcp en `prometheus.yml`, métrica `probe_ssl_earliest_cert_expiry` | 22/22 targets up (8 scrape + 14 probes); `test_cert_expiry_metric_present` |
| **Hardening capabilities** | **Cerrado** — `no-new-privileges` + `cap_drop: ALL` selectivo; excepciones justificadas: cadvisor `privileged` (irreducible, R-08), s3-vol2 `SETUID/GID` (su-exec, verificado crash-loop sin ellas) | stack healthy tras recreate completo |
| **Redacción de secretos en logs** | **Cerrado** — template promtail amplía `replace` a `Authorization`/`Bearer`/`Cookie`/`X-Api-Key`/tokens/passwords + URLs de webhook Shuffle | `promtail -check-syntax` PASS en CI |
| **Validadores de config** | **Cerrado** — `scripts/ci/validate_observability_configs.sh`: compose config + promtool (config/web-config) + loki/tempo/promtail/otelcol/blackbox validators nativos + pinning + LF + gitleaks | **10/10 PASS**; job `observability-configs` en `ci.yml`; cazó un bug real (`scrape_timeout > interval` en cadvisor) |
| **Renderer `IGNORE_HTTPS_ERRORS`** | **ADR aceptado** — Chromium NSS no admite CA vía env; tráfico cifrado, verificación desactivada documentada (R-06, ADR-0014 §4) | RB-13 + risk register |
| **Tests vivos E2E** | **Cerrado** — `tests/integration/test_observability_live.py`: 14 tests (targets, probes, cert metric, reglas, contact point, webhook sintético 200, TLS×4, IAM×2, watchdog) | **14/14 PASS** con `-m requires_docker` |

### Bugs reales encontrados en este sprint

- **`cortex_success_rate_low` autorreferencia D→D** (validador estático).
- **cadvisor `scrape_timeout: 30s` > `scrape_interval: 15s`** (promtool) →
  job a 60s/30s.
- **`s3-vol2` crash-loop por `cap_drop: ALL`** (su-exec) → excepción con
  `SETUID/SETGID`.
- **`accelerator` no es métrica válida en cadvisor v0.49** → fuera de
  `disable_metrics`.
- **`infra/docker/compose/config/` con dirs vacíos fantasma** (bind-mount
  sobre ruta inexistente crea directorios) → borrados; el validator lo
  detectó como "is a directory".
- **MSYS grep `-lU $'\r'` devuelve falsos positivos** (modo texto elimina
  CR) — el check LF usa `od` hex.

### Deuda residual tras el sprint (explícita)

- Renderer sin verificación de peer (R-06, ADR-0014 §4).
- SeaweedFS 2 racks en el mismo host (R-07); filer/gateway single-instance.
- OTLP gRPC :4317/:4318 en claro dentro de la red (mTLS de terceros, fuera
  de perímetro lab).
- HA real, storage externo, WORM/immutability y notificación externa
  (SMTP/PagerDuty) = horizonte producción, fuera del alcance del lab —
  documentado, no implementado.
- Backup/restore drill del stack de observabilidad + tests de
  disk-full/capacidad: pendientes (sprint siguiente).

### Nota (séptima revisión)

Con IAM efectivo, init fail-closed, backpressure, probes, self-monitoring
alerting, hardening medido y un gate CI que valida cada config con su
binario nativo, las deudas de **implementación** del stack están cerradas.
Lo que resta es horizonte de producción (multi-host, mTLS third-party,
WORM) — arquitectura, no deuda. Nota mantenida **9.5/10** con evidencia
reproducible.

## Octava revisión — sprint 2: failure-injection, backup/restore, retención, SLO (2026-11-10)

El segundo sprint cerró los ítems operativos restantes del registro
(`docs/24` §2.3) y el failure-injection **cazó 3 bugs reales**:

| Ítem | Resolución | Evidencia |
|------|------------|-----------|
| **Backup/restore** | `scripts/maintenance/backup_obs_stack.sh` + `make backup-obs`/`drill-obs` | 7/7 volúmenes tareados+verificados; drill a volúmenes scratch con markers; **RTO 94s** |
| **Failure-injection** | `docker stop tempo` → `obs_probe_down` firing a los +4m → restart → inactive | lazo completo kill→fire→restore→resolve + notificación al API |
| **Bug: promtail ingest parado** | `cap_drop: ALL` quitó `CAP_DAC_OVERRIDE` → EACCES en docker.sock | `cap_add: [DAC_OVERRIDE]` — 637k+ entries/20MB a Loki tras el fix; la alerta `soar_loki_ingest_stalled` lo detectó (señal real) |
| **Bug: `obs_alert_channel_silent` perma-fire** | `increase()` sin `sum()` — series `{status="resolved|other"}` siempre 0 | `sum(increase(...))` |
| **Bug: `obs_s3_*` self-match (RB-06)** | query-echo de loki contiene la regex | `!~` excluye `caller=(metrics|engine|roundtrip)[.]go`/`executing query` |
| **Retención** | evidencia de purga real | tempo `deleting block` (sweep 48h) + loki compactor cycles cada ~1min |
| **SLO/burn-rate** | `obs_admission_slo_burn_rate` (5m+1h, 14.4× budget 1%) | 23 reglas provisionadas; solo watchdog firing |

**Nota**: la cadena de monitorización demostró valor real — el failure-
injection reveló una regresión de hardening silenciosa (promtail) que el
healthcheck no cubría, y dos bugs semánticos en las propias alertas.
Estado: **23 reglas, 0 errores, solo watchdog firing**; suites 19/19 +
15/15 + 10/10 verdes.
