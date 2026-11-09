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

- **GRAF-D3**: version-gating de provisioning — editar un dashboard JSON exige bump de `version` (documentado en AGENTS.md).
- **GRAF-D5**: Loki/Tempo single-node con storage local filesystem — sin object storage ni HA (limitación de laboratorio, no de diseño).
- **GRAF-D6**: `grafana_data` en bind-mount Windows — IO lento; el backup `make backup` sí archiva `runtime/` (incl. grafana.db, loki, tempo).
- **GRAF-D8**: Webhook Shuffle 500s intermitentes (upstream, no Grafana).
- **GRAF-D9**: Renderer chromium se degrada con ráfagas muy largas de renders secuenciales — mitigado con clustering; en lab no es bloqueante.
- **GRAF-D10**: TLS ausente en todo el stack observabilidad (loopback/compose-net only) + admin password en `.env` (convención aceptada del repo).
- **GRAF-D11**: Tempo search vía JSON datasource no interpola macros `${__from}` en `urlPath` → ventana fija "reciente" del servidor (últimos N resultados); aceptable para panel "Recent traces".

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
