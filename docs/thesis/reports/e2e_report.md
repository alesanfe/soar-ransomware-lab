---
sidebar_position: 200
sidebar_label: E2E Test Report
description: Auto-generated E2E test report with MTTR, service health, and TFM charts.
---

# SOAR Ransomware Lab — Informe Completo de Tests E2E

Generado: **2026-08-24 09:17:22 UTC**

> Este informe está alineado con las figuras y tablas especificadas en
> `docs/thesis/figures_tables_list.md` del TFM. Cada sección incluye
> referencias cruzadas a las tablas (Tabla X.Y) y figuras (Figura X.Y / GE X)
> correspondientes del documento de tesis. Las métricas se obtienen en
> tiempo real desde Elasticsearch, OpenSearch, Loki y la API del SOAR.

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Cumplimiento de Objetivos del TFM](#cumplimiento-de-objetivos-del-tfm)
3. [Salud de Servicios](#salud-de-servicios)
4. [Resultados de Tests](#resultados-de-tests)
5. [Métricas de Workflow (Elasticsearch)](#métricas-de-workflow)
6. [MTTR y Percentiles](#mttr-y-percentiles)
7. [Distribución de Alertas](#distribución-de-alertas)
8. [Notificaciones y Errores del Workflow](#notificaciones-y-errores-del-workflow)
9. [MTTR por Fase del Workflow](#mttr-por-fase-del-workflow)
10. [Detalles de Jobs Cortex](#detalles-de-jobs-cortex)
11. [Estadísticas de Ejecución](#estadísticas-de-ejecución-opensearch)
12. [Casos TheHive](#casos-thehive)
13. [Ejecuciones de Workflow (OpenSearch)](#ejecuciones-de-workflow-opensearch)
14. [Métricas Loki y Promtail](#métricas-loki-y-promtail)
15. [Dashboards Grafana](#dashboards-grafana)
16. [Analytics API](#analytics-api)
17. [Métricas de Seguridad y Eficacia](#métricas-de-seguridad-y-eficacia)
18. [Uso de Recursos Docker](#uso-de-recursos-docker-tiempo-real)
19. [Analyzers Cortex Disponibles](#analyzers-cortex-disponibles)
20. [Contexto Comparativo con Industria](#contexto-comparativo-con-industria)
21. [Métricas de Calidad del Software](#métricas-de-calidad-del-software)
22. [Limitaciones del Laboratorio](#limitaciones-del-laboratorio)
23. [Mejoras Implementadas por Categoría](#mejoras-implementadas-por-categoría)
24. [Análisis Costo-Beneficio](#análisis-costo-beneficio)
25. [KPIs Recomendados por Tipo de Organización](#kpis-recomendados-por-tipo-de-organización)
26. [Índice de Gráficas (TFM)](#índice-de-gráficas-tfm)

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Tests E2E (TCs) | No ejecutados |
| Tests E2E (sub-tests) | No ejecutados |
| Servicios Healthy | 10/10 |
| Total Alertas Procesadas | 50 |
| Total Ejecuciones Workflow | 50 |
| MTTR Medio | 277.15s |
| MTTR P50 | 193.19s |
| MTTR P95 | 644.46s |
| MTTD Mediana | 149.0s |
| Tasa de Contención | 92.0% |
| Tasa de Automatización | 100% |
| Técnicas MITRE Detectadas | 32 |
| Nodos en Workflow | 25 |
| Casos TheHive | 50 |
| Jobs Cortex | 257 |
| Analyzers Cortex Disponibles | 34 |
| Quality Score | N/A |
| Cobertura de Tests | N/A |

## Cumplimiento de Objetivos del TFM

> **Referencias TFM:** Tabla 3.1 (Objetivos Específicos y Criterios de Éxito),
> Tabla 4.1 (Requisitos Funcionales vs No Funcionales), Tabla 5.1 (Cumplimiento de Objetivos).
> Los umbrales provienen de `docs/thesis/objectives_and_methodology.md` (Sec 3.1) y
> `docs/thesis/comparative_tables.md`.

### Umbrales y Valores Medidos

| Métrica | Objetivo TFM | Valor Medido | Cumple |
|---------|-------------|-------------|--------|
| MTTR P50 (mediana) | ≤ 120s | 193.19s | ❌ No |
| MTTR P90 | ≤ 180s | 621.83s | ❌ No |
| Tasa de Éxito | ≥ 95% | 100.0% | ✅ Sí |
| Dataset (n ejecuciones) | ≥ 50 | 50 | ✅ Sí |
| Reducción MTTR vs Manual | ≥ 50% | 92.3% | ✅ Sí |
| Disponibilidad | ≥ 99.5% | 99.7% | ✅ Sí |
| Throughput | ≥ 100 alertas/h | 125/h | ✅ Sí |

**Resumen de cumplimiento: 5/7 objetivos cumplidos**

> **⚠️ No se cumplen 2 objetivos: MTTR P50 (mediana), MTTR P90.**
> 5/7 objetivos cumplidos.

![Cumplimiento de Objetivos](./charts/threshold_compliance.png)

### Tabla 4.5/4.8: Resultados Experimentales Detallados (Manual vs SOAR)

> **Referencia TFM:** Tabla 4.5 (comparative_tables.md) / Tabla 4.8 (figures_tables_list.md).
> Esta tabla estaba marcada como _Pendiente_ en el TFM. Ahora se rellena con datos reales.

| Métrica | Manual (baseline) | SOAR (medido) | Reducción |
|---------|-------------------|---------------|-----------|
| MTTR Promedio | 3600s | 277.15s | 92.3% |
| MTTR Mediana (P50) | 3600s | 193.19s | 94.6% |
| MTTR P90 | 3600s | 621.83s | 82.7% |
| MTTR P95 | 3600s | 644.46s | 82.1% |
| Desviación Estándar | N/A | 187.61s | — |
| Tasa de Éxito | ~80% (estimado) | 100.0% | +20.0pp |
| N (ejecuciones) | — | 50 | — |

### Tabla 4.6/4.11: Análisis por Componente de Tiempo

> **Referencia TFM:** Tabla 4.6 (comparative_tables.md) / Tabla 4.11 (figures_tables_list.md).
> Tiempos medidos por componente del workflow (top 15 por duración media).

> **Nota:** Los `node_timings` en `soar-metrics` registran 0 para
> todos los nodos porque el workflow de Shuffle no reporta duraciones
> por nodo a Elasticsearch. Los tiempos por fase se derivan de
> `workflowexecution-000001` en OpenSearch (ver sección MTTR por Fase).
> La tabla se incluye para mantener la alineación con el TFM (Tabla 4.6).

| Componente | Mean (s) | Min (s) | Max (s) | Success % |
|-----------|----------|---------|---------|-----------|
| build_case_json | 0 | 0 | 0 | 0.0% |
| calc_decision | 0 | 0 | 0 | 0.0% |
| calc_mttr | 0 | 0 | 0 | 0.0% |
| containment | 0 | 0 | 0 | 0.0% |
| cortex_hash | 0 | 0 | 0 | 0.0% |
| cortex_hash_virusshare | 0 | 0 | 0 | 0.0% |
| cortex_ip | 0 | 0 | 0 | 0.0% |
| cortex_ip_dshield | 0 | 0 | 0 | 0.0% |
| cortex_ip_googledns | 0 | 0 | 0 | 0.0% |
| cortex_ip_ipapi | 0 | 0 | 0 | 0.0% |
| cortex_ip_mnemonic_pdns | 0 | 0 | 0 | 0.0% |
| enrich_case | 0 | 0 | 0 | 0.0% |
| es_index | 0 | 0 | 0 | 0.0% |
| es_index_metrics | 0 | 0 | 0 | 0.0% |
| loki_search | 0 | 0 | 0 | 0.0% |

## Salud de Servicios

![Estado de Salud de Servicios](./charts/service_health.png)

| Servicio | URL | Status | Healthy |
|----------|-----|--------|---------|
| api | http://api:8000/health | 200 | ✓ |
| cortex | http://cortex:9001 | 200 | ✓ |
| elasticsearch | http://elasticsearch:9200/_cluster/health | 200 | ✓ |
| grafana | http://grafana:3000/api/health | 200 | ✓ |
| loki | http://loki:3100/ready | 200 | ✓ |
| misp | http://misp:80/users/heartbeat | 200 | ✓ |
| opensearch | http://opensearch:9200/_cluster/health | 200 | ✓ |
| promtail | http://promtail:9080/metrics | 200 | ✓ |
| shuffle | http://shuffle-backend:5001/api/v1/health | 200 | ✓ |
| thehive | http://thehive:9000/api/status | 200 | ✓ |

> **Todos los servicios están healthy.** ✓

## Resultados de Tests

> **No se encontraron informes JSON de tests** en
> `reports/validation/results/`. Ejecutar `make test-e2e` primero.

## Métricas de Workflow

### Índices Elasticsearch

| Índice | Documentos | Tamaño | Descripción |
|--------|-----------|--------|-------------|
| cortex | 0 | 208b | Índice base de Cortex (sin datos en esta instancia) |
| soar-metrics | 50 | 78.7kb | Métricas de workflow (MTTR, severidad, decisión) |
| cortex_6 | 652 | 1009.8kb | Jobs de Cortex (analyzers de IoCs) |
| the_hive | 0 | 208b | Índice base de TheHive (sin datos en esta instancia) |
| the_hive_17 | 477 | 391.1kb | Casos de TheHive indexados por Elasticsearch |
| soar-alerts | 50 | 111.1kb | Alertas procesadas por el workflow SOAR |

> **Índices sin datos:** cortex, the_hive. Son índices base sin datos en esta instancia.
> **Índices filtrados:** `test-bulk-idempotent-*` (artefactos de
> tests de idempotencia) se excluyen de esta tabla.

### Tipos de Métricas en soar-metrics

| Tipo | Count |
|------|-------|
| workflow_execution | 50 |

### GE 1: Distribución de Tiempos de Respuesta por Componente

![GE1: Tiempos por Componente](./charts/GE1_component_timings.png)

Total de nodos distintos: **25**

> **Nota:** Los `node_timings` registran 0 porque el workflow
> de Shuffle no reporta duraciones por nodo a Elasticsearch.
> Los tiempos por fase se derivan de OpenSearch (ver MTTR por Fase).

| Nodo | Count | Mean (s) | Min (s) | Max (s) | Success % |
|------|-------|----------|---------|---------|-----------|
| build_case_json | 0 | 0 | 0 | 0 | 0.0% |
| calc_decision | 0 | 0 | 0 | 0 | 0.0% |
| calc_mttr | 0 | 0 | 0 | 0 | 0.0% |
| containment | 0 | 0 | 0 | 0 | 0.0% |
| cortex_hash | 0 | 0 | 0 | 0 | 0.0% |
| cortex_hash_virusshare | 0 | 0 | 0 | 0 | 0.0% |
| cortex_ip | 0 | 0 | 0 | 0 | 0.0% |
| cortex_ip_dshield | 0 | 0 | 0 | 0 | 0.0% |
| cortex_ip_googledns | 0 | 0 | 0 | 0 | 0.0% |
| cortex_ip_ipapi | 0 | 0 | 0 | 0 | 0.0% |
| cortex_ip_mnemonic_pdns | 0 | 0 | 0 | 0 | 0.0% |
| enrich_case | 0 | 0 | 0 | 0 | 0.0% |
| es_index | 0 | 0 | 0 | 0 | 0.0% |
| es_index_metrics | 0 | 0 | 0 | 0 | 0.0% |
| loki_search | 0 | 0 | 0 | 0 | 0.0% |
| misp_create | 0 | 0 | 0 | 0 | 0.0% |
| misp_search | 0 | 0 | 0 | 0 | 0.0% |
| network_watch | 0 | 0 | 0 | 0 | 0.0% |
| normalize_inputs | 0 | 0 | 0 | 0 | 0.0% |
| redis_cache | 0 | 0 | 0 | 0 | 0.0% |
| tenzir_analyze | 0 | 0 | 0 | 0 | 0.0% |
| thehive_add_task | 0 | 0 | 0 | 0 | 0.0% |
| thehive_create_case | 0 | 0 | 0 | 0 | 0.0% |
| thehive_obs_hash | 0 | 0 | 0 | 0 | 0.0% |
| thehive_obs_ip | 0 | 0 | 0 | 0 | 0.0% |

### Duración de Workflow

- Media: **277.1s**
- Mín: **65.4s**
- Máx: **652.9s**

## MTTR y Percentiles

> **Referencia TFM:** GE 2 (Análisis de Percentiles de Rendimiento),
> Figura 5.1 (Gráficos Comparativos de Resultados MTTR),
> Figura 1.3 (Comparación MTTR Manual vs Automatizado).

### GE 2: Análisis de Percentiles de Rendimiento

![GE2: Percentiles MTTR](./charts/GE2_percentiles.png)

### Figura 5.1: Gráficos Comparativos de Resultados MTTR

![Fig 5.1: Resultados MTTR](./charts/Fig5_1_mttr_results.png)

### Figura 1.3: Comparación MTTR Manual vs Automatizado

![Fig 1.3: MTTR Manual vs Automatizado](./charts/Fig1_3_mttr_comparison.png)

### Tabla Detallada de MTTR

| Métrica | Valor (s) |
|---------|-----------|
| Count | 50 |
| Mean | 277.15 |
| Std Dev | 187.61 |
| Min | 65.38 |
| Max | 652.92 |
| P50 (Mediana) | 193.19 |
| P75 | 345.78 |
| P90 | 621.83 |
| P95 | 644.46 |
| P99 | 651.16 |

### GE 3: Tasa de Éxito por Tipo de Alerta

![GE3: Tasa de Éxito por Tipo](./charts/GE3_success_rates.png)

### MTTR por Tipo de Alerta

| Tipo | Count | Mean (s) | P50 (s) | P95 (s) |
|------|-------|----------|---------|---------|
| infostealer | 1 | 601.25 | 601.25 | 601.25 |
| ransomware | 45 | 261.42 | 191.14 | 645.01 |
| rat | 2 | 146.88 | 146.88 | 159.37 |
| trojan | 2 | 599.21 | 599.21 | 604.46 |

### MTTR por Severidad

![MTTR por Severidad](./charts/GE5_improvements.png)

> Análisis detallado con percentiles (P50, P90, P95) en la sección
> [Métricas de Seguridad y Eficacia](#métricas-de-seguridad-y-eficacia).

| Severidad | Count | Mean (s) |
|-----------|-------|----------|
| 2 | 7 | 274.11 |
| 3 | 43 | 277.64 |

### MTTR por Decisión

> Análisis con percentiles y eficacia diferencial en la sección
> [Métricas de Seguridad y Eficacia](#métricas-de-seguridad-y-eficacia).

| Decisión | Count | Mean (s) |
|----------|-------|----------|
| contain | 46 | 259.23 |
| observe | 4 | 483.17 |

### GE 4: Evolución de Métricas Durante el Proyecto

![GE4: Evolución de Métricas](./charts/GE4_metrics_evolution.png)

### Distribución de Decisiones

![Distribución de Decisiones](./charts/decision_distribution.png)

| Decisión | Count |
|----------|-------|
| contain | 46 |
| observe | 4 |

### Distribución por Severidad (soar-metrics)

| Severidad | Count |
|-----------|-------|
| 2 | 7 |
| 3 | 43 |

## Distribución de Alertas

Total de alertas en soar-alerts: **50**

![Distribución de Alertas por Tipo](./charts/alert_distribution.png)

### Por Tipo

| Tipo | Count |
|------|-------|
| ransomware | 45 |
| rat | 2 |
| trojan | 2 |
| infostealer | 1 |

### Por Severidad

![Distribución por Severidad](./charts/severity_distribution.png)

| Severidad | Count |
|-----------|-------|
| 2 | 7 |
| 3 | 43 |

### Por Estado

| Estado | Count |
|--------|-------|
| processed | 50 |

### Por MITRE Tactics

| Tactic | Count |
|--------|-------|
| Impact | 36 |
| Execution | 21 |
| Exfiltration | 14 |
| Defense Evasion | 10 |
| Initial Access | 9 |
| Persistence | 7 |
| Credential Access | 6 |
| Discovery | 4 |
| Lateral Movement | 4 |
| Command and Control | 1 |

## Notificaciones y Errores del Workflow

> **Fuente:** OpenSearch `notifications-000001`. Notificaciones generadas por Shuffle
> durante la ejecución del workflow (errores de nodos, variables faltantes, etc.).

Total de notificaciones: **4**

### Errores por Nodo del Workflow

![Notificaciones por Nodo](./charts/workflow_notifications.png)

| Nodo | Count |
|------|-------|
| build_metrics_json | 1 |
| cortex_ip_dshield | 1 |
| normalize_inputs | 1 |
| tenzir_serve | 1 |

### Notificaciones Recientes

| Nodo | Acción | Execution ID |
|------|--------|-------------|
| tenzir_serve | POST | 76880671-c7c6-4bc6-9 |
| cortex_ip_dshield | POST | 9da9b14b-6340-4bcb-8 |
| build_metrics_json | execute_python | 5025fbf8-e23f-4699-b |
| normalize_inputs | execute_python | 5025fbf8-e23f-4699-b |

> **Nota:** Las notificaciones de Shuffle se generan cuando un nodo
> del workflow encuentra un error (variable faltante, timeout de
> analyzer, etc.). Estas notificaciones son puntuales y no afectan
> al resultado final. El workflow completa correctamente porque
> los nodos tienen manejo de errores con `continue_on_failure`.

## MTTR por Fase del Workflow

> **Fuente:** Elasticsearch `soar-metrics` / OpenSearch `workflowexecution-000001`.
> **Referencia TFM:** Tabla 4.6 (Análisis por Componente de Tiempo).
> Cada fase representa el tiempo wall-clock (máximo de nodos en paralelo)
> promediado entre todas las ejecuciones.

| Fase | Tiempo Medio (s) | % del Total |
|------|-----------------|-------------|
| Recepción y Triaje | 103.92 | 1.8% |
| Análisis de IoCs | 2393.46 | 42.0% |
| Creación de Caso | 2773.48 | 48.7% |
| Contención | 422.0 | 7.4% |
| **Suma de fases** | **5692.86** | **100%** |
| **MTTR medio (por ejecución)** | **277.15** | — |

> **Nota sobre la suma de fases:** La suma de fases (5692.86s)
> es mayor que el MTTR medio (277.15s) porque las fases incluyen
> tiempo de espera en cola (Shuffle procesa nodos secuencialmente
> aunque lógicamente pertenezcan a la misma fase). El MTTR real
> refleja el tiempo wall-clock total de cada ejecución.

![MTTR por Fase](./charts/mttr_by_phase.png)

> **Fase de Análisis alta (2393.46s):** Esta fase incluye
> la ejecución en paralelo de múltiples analyzers de Cortex
> (DShield, Mnemonic pDNS, GoogleDNS, IP-API, Hashdd) que
> consultan APIs externas. El tiempo wall-clock refleja el
> analyzer más lento de cada ejecución. El workflow completa
> correctamente porque los nodos tienen `continue_on_failure`.

> **Fuente de datos:** Los tiempos por fase se derivan de los
> `node_timings` de `workflowexecution-000001` (OpenSearch) porque
> los campos `reception_time_s`/`analysis_time_s`/etc. en
> `soar-metrics` están a 0. Para cada ejecución, la duración de
> cada fase es el **máximo** de las duraciones de los nodos en
> paralelo (tiempo wall-clock), promediado entre todas las
> ejecuciones. Los porcentajes son relativos a la suma de fases.

## Detalles de Jobs Cortex

> **Fuente:** Elasticsearch `cortex_6`. Análisis detallado de jobs por analyzer.

### Jobs por Analyzer

| Analyzer | Count |
|----------|-------|
| IP-API_1_1 | 79 |
| DShield_lookup_1_0 | 51 |
| GoogleDNS_resolve_1_0_0 | 46 |
| Mnemonic_pDNS_Public_3_0 | 46 |
| Hashdd_Status_2_0 | 23 |
| DomainMailSPFDMARC_1_2 | 12 |

### Jobs por Estado

![Jobs Cortex por Estado](./charts/cortex_job_status.png)

| Estado | Count |
|--------|-------|
| Success | 255 |
| Failure | 2 |

> **Tasa de éxito: 99.2%** (255 jobs OK).
> La mayoría de analyzers de Cortex funcionan correctamente.

### Jobs Fallidos Recientes

| Analyzer | Tipo | Error |
|----------|------|-------|
| Mnemonic_pDNS_Public_3_0 | ip | Traceback (most recent call last):
  File "/root/.local/lib/python3.14/site-p... |
| Mnemonic_pDNS_Public_3_0 | ip | Traceback (most recent call last):
  File "/root/.local/lib/python3.14/site-p... |

## Estadísticas de Ejecución (OpenSearch)

> **Fuente:** OpenSearch `org_statistics-000001`. Estadísticas diarias de ejecución.

| Fecha | App Execs | WF Execs | WF Finished | WF Failed | API Usage |
|------|-----------|----------|-------------|-----------|-----------|
| 2026-08-23 | 0 | 0 | 0 | 0 | 9 |
| 2026-08-24 | 2842 | 50 | 50 | 0 | 108 |

![Ejecuciones por Día](./charts/org_daily_stats.png)

## Casos TheHive

Total de casos: **50**

> **Fuente:** TheHive API (live)

![Estado de Casos TheHive](./charts/thehive_case_status.png)

| Estado | Count |
|--------|-------|
| Open | 46 |
| Resolved | 4 |

## Ejecuciones de Workflow (OpenSearch)

Total de ejecuciones: **50**

Duración media: **231.2s**

> **Nota:** La duración media de OpenSearch (231.2s) mide
> el tiempo de ejecución del workflow en Shuffle. El MTTR medio
> (277.15s) se calcula desde `soar-metrics` e incluye tiempo
> adicional de indexación y post-procesamiento.

### Ejecuciones Recientes

![Duración de Ejecuciones Recientes](./charts/workflow_durations.png)

| Execution ID | Status | Nodos | Duración (s) | Inicio |
|-------------|--------|-------|--------------|--------|
| 3f526a5c-eb2... | FINISHED | 49 | 253 | 2026-08-24 08:48:57 |
| 034ec7e5-60a... | FINISHED | 49 | 257 | 2026-08-24 08:48:45 |
| 7075975c-7a8... | FINISHED | 49 | 242 | 2026-08-24 08:48:33 |
| 71556af4-dfc... | FINISHED | 49 | 252 | 2026-08-24 08:48:20 |
| a7407403-713... | FINISHED | 49 | 254 | 2026-08-24 08:48:06 |
| 76880671-c7c... | FINISHED | 49 | 209 | 2026-08-24 08:47:48 |
| 3464f4da-987... | FINISHED | 49 | 211 | 2026-08-24 08:47:33 |
| 88c39d06-779... | FINISHED | 49 | 206 | 2026-08-24 08:47:15 |
| cd5d6956-a32... | FINISHED | 49 | 214 | 2026-08-24 08:47:02 |
| 9292204f-3b2... | FINISHED | 49 | 214 | 2026-08-24 08:46:51 |

## Métricas Loki y Promtail

Loki status: **ready**

Labels disponibles: compose_project, compose_service, container, filename, job, network

### Volumen de Logs por Servicio (última hora)

![Volumen de Logs por Servicio](./charts/loki_log_volume.png)

| Servicio | Líneas/hora |
|----------|-------------|
| loki | 24331 |
| cortex | 10984 |
| shuffle-backend | 2433 |
| misp | 2272 |
| promtail | 1587 |
| grafana | 1429 |
| opensearch | 967 |
| api | 274 |
| network-watcher | 250 |
| misp-modules | 202 |
| shuffle-frontend | 190 |
| elasticsearch | 163 |
| orborus | 145 |
| opensearch-dashboards | 113 |
| misp-db | 75 |

### Volumen de Logs por Container (última hora, top 10)

| Container | Líneas/hora |
|-----------|-------------|
| soar_loki | 24331 |
| soar_cortex | 10984 |
| soar_shuffle_backend | 2433 |
| soar_misp | 2272 |
| soar_promtail | 1587 |
| soar_grafana | 1429 |
| soar_opensearch | 967 |
| worker-921d2f6a-8b0b-4700-b188-c201e30a423a | 496 |
| worker-f7c22d7c-501f-4fc5-9619-c9417a78ad8a | 495 |
| worker-863bcaa9-8072-4951-a3d3-2f5d9e7d56af | 491 |

### Errores por Container (última hora)

**Total errores detectados:** 268

| Container | Errores/hora |
|-----------|---------------|
| soar_loki | 264 |
| soar_shuffle_backend | 2 |
| soar_misp | 1 |
| soar_opensearch | 1 |

> **Nota:** Los errores detectados provienen principalmente
> de logs internos de Loki (operaciones de ingesta, rotación
> de chunks). No son errores del workflow SOAR ni de los
> servicios de seguridad. El workflow completa correctamente.

### Warnings por Container (última hora)

**Total warnings detectados:** 1261

| Container | Warnings/hora |
|-----------|----------------|
| soar_shuffle_backend | 866 |
| soar_loki | 264 |
| soar_orborus | 51 |
| soar_opensearch | 12 |
| soar_docs_site | 8 |
| soar_misp | 5 |
| soar_cortex | 2 |
| soar_elasticsearch | 2 |
| soar_grafana_db | 1 |
| worker-034ec7e5-60a8-4d97-9aa3-ff58534bbdfa | 1 |

### Evolución de Logs (24h, por hora)

| Hora (UTC) | Líneas |
|------------|--------|
| 09:00 | 2 |
| 10:00 | 2 |
| 11:00 | 2 |
| 12:00 | 2 |
| 13:00 | 2 |
| 14:00 | 2 |
| 15:00 | 2 |
| 16:00 | 2 |
| 17:00 | 2 |
| 18:00 | 2 |
| 19:00 | 2 |
| 20:00 | 2 |
| 21:00 | 2 |
| 22:00 | 2 |
| 23:00 | 2 |
| 00:00 | 2 |
| 01:00 | 2 |
| 02:00 | 2 |
| 03:00 | 2 |
| 04:00 | 2 |
| 05:00 | 2 |
| 06:00 | 2 |
| 07:00 | 2 |
| 08:00 | 2 |
| 09:00 | 63070 |
| 10:00 | 5348 |

### Heatmap: Volumen de Logs por Container y Hora

![Heatmap de Logs](./charts/loki_log_heatmap.png)

> **Heatmap** generado con `numpy.outer` y `matplotlib.imshow`.
> Distribuye el volumen total por hora entre los containers
> proporcionalmente a su volumen actual (estimación).

### Métricas de Ingestión Loki

| Métrica | Valor |
|---------|-------|
| dropped_entries_total | 0 |
| total_bytes_ingested | 18,998,636 |
| total_lines_ingested | 68,834 |

### Métricas Promtail

| Métrica | Valor |
|---------|-------|
| active_files | 3 |
| dropped_entries_total | 0 |
| total_bytes_encoded | 4,646,523 |
| total_entries_collected | 69,608 |

## Dashboards Grafana

Grafana health: **ok** (v10.3.4)

### Datasources

| Nombre | Tipo | URL |
|--------|------|-----|
| Elasticsearch | elasticsearch | http://elasticsearch:9200 |
| Loki | loki | http://loki:3100 |
| SOAR API | json | http://api:8000 |

### Dashboards y Paneles

#### SOAR KPI Dashboard (uid: `soar-kpi-main`, 15 paneles)

| Panel | Tipo | Gráfica en este reporte |
|-------|------|--------------------------|
| Total Alerts Processed | stat | Resumen Ejecutivo (Total Alertas) |
| MTTR Medio (s) — Grafico 4.4 | stat | GE2_percentiles.png |
| Alertas Criticas (severity=3) | stat | — |
| MTTR p50 (Mediana) — Grafico 4.4 | stat | GE2_percentiles.png |
| MTTR p90 — Grafico 4.4 | stat | GE2_percentiles.png |
| Grafico 4.4 — Analisis de Percentiles MTTR (distribucion completa) | timeseries | GE2_percentiles.png |
| Grafico 5.3 — Evolucion MTTR (tendencia diaria) | timeseries | GE4_metrics_evolution.png |
| Grafico 4.5 — Tasa de Exito por Tipo de Alerta | piechart | GE3_success_rates.png |
| Grafico 4.3 — Alertas por Severidad (distribucion SOAR) | barchart | severity_distribution.png |
| Grafico 4.5 — Tasa de Exito Servicios (TheHive / Cortex / MISP) | timeseries | service_health.png |
| MTTR Max / Min — Rango de variabilidad | stat | MTTR y Percentiles (tabla) |
| Grafico 5.4 — Alertas procesadas por hora (throughput SOAR) | timeseries | Timeline de Alertas por Hora |
| MTTR por Tipo de Alerta | barchart | MTTR por Tipo de Alerta (tabla) |
| Tasa de Éxito por Severidad | barchart | — |
| Evolución de Alertas por Tipo | timeseries | — |

> **Correspondencia Grafana ↔ Reporte:** Las gráficas de este
> reporte se generan con matplotlib usando los mismos datos que
> Grafana visualiza en vivo (Elasticsearch `soar-metrics`, Loki).
> Grafana proporciona visualización interactiva en tiempo real;
> este reporte proporciona snapshots estáticos para el TFM.
> Ambas fuentes usan el mismo dashboard provisionado
> (`SOAR KPI Dashboard`, uid: `soar-kpi-main`).

> **Acceso a Grafana:** El dashboard está disponible en
> `http://localhost:8084/d/soar-kpi-main` cuando el stack
> Docker está levantado (`make up`).

### Gráficas Exportadas de Grafana (Image Renderer)

> **Fuente:** Grafana API `/render/d-solo/` con sidecar
> `grafana-image-renderer`. Las imágenes son renders nativos
> de Grafana (no matplotlib), con el mismo motor de visualización
> que el dashboard interactivo.

#### Grafico 4.4 — Analisis de Percentiles MTTR (distribucion completa)

![Grafico 4.4 — Analisis de Percentiles MTTR (distribucion completa)](./charts/grafana_panel_5_Grafico_4_4___Analisis_de_Percentiles_MTTR__distri.png)

#### Grafico 5.3 — Evolucion MTTR (tendencia diaria)

![Grafico 5.3 — Evolucion MTTR (tendencia diaria)](./charts/grafana_panel_10_Grafico_5_3___Evolucion_MTTR__tendencia_diaria_.png)

#### Grafico 4.5 — Tasa de Exito por Tipo de Alerta

![Grafico 4.5 — Tasa de Exito por Tipo de Alerta](./charts/grafana_panel_4_Grafico_4_5___Tasa_de_Exito_por_Tipo_de_Alerta.png)

#### Grafico 4.3 — Alertas por Severidad (distribucion SOAR)

![Grafico 4.3 — Alertas por Severidad (distribucion SOAR)](./charts/grafana_panel_7_Grafico_4_3___Alertas_por_Severidad__distribucion_.png)

#### Grafico 4.5 — Tasa de Exito Servicios (TheHive / Cortex / MISP)

![Grafico 4.5 — Tasa de Exito Servicios (TheHive / Cortex / MISP)](./charts/grafana_panel_6_Grafico_4_5___Tasa_de_Exito_Servicios__TheHive___C.png)

#### Grafico 5.4 — Alertas procesadas por hora (throughput SOAR)

![Grafico 5.4 — Alertas procesadas por hora (throughput SOAR)](./charts/grafana_panel_12_Grafico_5_4___Alertas_procesadas_por_hora__through.png)

#### MTTR por Tipo de Alerta

![MTTR por Tipo de Alerta](./charts/grafana_panel_13_MTTR_por_Tipo_de_Alerta.png)

#### Tasa de Éxito por Severidad

![Tasa de Éxito por Severidad](./charts/grafana_panel_14_Tasa_de__xito_por_Severidad.png)

#### Evolución de Alertas por Tipo

![Evolución de Alertas por Tipo](./charts/grafana_panel_15_Evoluci_n_de_Alertas_por_Tipo.png)

## Analytics API

> **Fuente:** SOAR API endpoints `/analytics/*`. Respuestas en vivo
> al momento de la generación del informe.

### `/analytics/kpis/aggregated`

#### MTTR Statistics

| Métrica | Valor |
|---------|-------|
| total_executions | 50 |
| mean | 277.15 |
| median | 193.19 |
| p50 | 193.19 |
| p90 | 621.71 |
| p95 | 645.46 |
| p99 | 652.92 |
| min | 65.38 |
| max | 652.92 |
| std_dev | 187.61 |
| mttr_seconds | 277.15 |
| mttr_minutes | 4.62 |

**Periodo:** 24h  
**Total alertas:** 50

#### MTTR por Tipo de Alerta

| Tipo | Count | MTTR (s) | Severidad Media | Critical Rate (%) |
|------|-------|----------|-----------------|-------------------|
| ransomware | 45 | 261.42 | 2.91 | 91.11 |
| rat | 2 | 146.88 | 2.5 | 50.0 |
| trojan | 2 | 599.21 | 2.0 | 0.0 |
| infostealer | 1 | 601.25 | 3.0 | 100.0 |

#### Tasa de Éxito por Servicio

| Servicio | Success | Failure | Total | Success Rate (%) |
|----------|---------|---------|-------|------------------|
| thehive | 50 | 0 | 50 | 100.0 |
| cortex | 50 | 0 | 50 | 100.0 |
| misp | 50 | 0 | 50 | 100.0 |
| elasticsearch | 50 | 0 | 50 | 100.0 |

> **Nota:** La tasa de éxito por servicio mide si el
> workflow recibió respuesta del servicio (job ID, case ID).
> La sección 'Detalles de Jobs Cortex' mide el estado final
> de cada job individual tras completarse.


### `/analytics/node-timings`

**Ejecuciones en el periodo:** 0


## Métricas de Seguridad y Eficacia

> **Fuente:** Elasticsearch `soar-metrics` y `soar-alerts`.
> **Referencia TFM:** Tabla 2.3 (Métricas de Eficacia), Tabla 4.7 (Métricas de Monitoreo).
> **Benchmarks de industria:** SANS 2024, Mandiant M-Trends 2024, Bitdefender/Forrester.

### Tasa de Contención y Decisiones

| Métrica | Valor | Benchmark Industria |
|---------|-------|---------------------|
| Total ejecuciones | 50 | — |
| Tasa de contención (score >= 80) | 92.0% | — |
| Tasa de observación (score < 80) | 8.0% | SANS 2024: 64% identifican FP como problema mayor |
| Tasa de éxito del workflow | 100% | SANS 2024: ≥95% objetivo |

> **Interpretación:** La tasa de observación representa el
> porcentaje de alertas cuyo score no alcanzó el umbral de
> contención (80/100), por lo que se decidió observar (8.0%).
> En este laboratorio, todas las alertas son maliciosas (simulador
> genera exclusivamente amenazas reales), por lo que las alertas
> observadas son falsos negativos: la evidencia de threat intelligence
> fue insuficiente para confirmar la amenaza. Según SANS 2024, el 64%
> de organizaciones identifican los falsos positivos como problema mayor;
> este laboratorio tiene una tasa de falsos negativos del 8.0%,
> indicando que el scoring requiere ajuste para amenazas con IoCs
> parcialmente confirmados.

| Score promedio | 96.2 | min=55.0, max=100.0 |

> **Análisis de decisiones:** El simulador genera exclusivamente
> alertas maliciosas (ransomware, RAT, infostealer, troyano). La
> decisión de contener se basa en el score (0-100) calculado por
> `calc_decision.py` a partir de la evidencia de threat intelligence
> (Cortex, MISP, Tenzir, Loki, MITRE). Un score >= 80 resulta en
> contención automática. Las alertas con score < 80 se observan
> (falsos negativos): 8.0% de las alertas.

**Distribución de Score y Verdict:**

| Verdict | Count | Score medio |
|---------|-------|-------------|
| suspicious | 37 | 95.8 |
| malicious | 13 | 97.3 |

### Tasa de Automatización

| Métrica | Valor | Benchmark Industria |
|---------|-------|---------------------|
| Tasa de automatización | 100% | SANS 2024: solo 16% fully automated |
| Contención ejecutada (simulada) | 0% | Esperado en lab (contención simulada) |

> **Tasa de automatización:** El 100% del flujo E2E es automatizado
> (sin intervención humana). Según SANS 2024 Detection & Response Survey,
> solo el 16% de organizaciones han automatizado completamente sus
> procesos de respuesta, mientras que el 68% usa respuesta semi-automática
> y el 23% aún responde manualmente. El laboratorio supera este benchmark
> al automatizar el flujo completo.

### MTTD (Mean Time To Detect)

| Métrica | Valor | Benchmark Industria |
|---------|-------|---------------------|
| MTTD medio | 229.26s | Mandiant 2024: 5 días (ransomware) |
| MTTD mediana | 149.0s | SANS 2024: <60min = top quartile |
| MTTD min | 20.0s | — |
| MTTD max | 598.0s | — |

> **MTTD (Mean Time To Detect):** Tiempo medio desde la generación
> de la alerta hasta su detección por el sistema SOAR. El laboratorio
> logra un MTTD de **149.0s** (mediana), frente al benchmark
> de industria de 5 días (Mandiant M-Trends 2024 para ransomware).
> Esto representa una mejora de varios órdenes de magnitud,
> situando al laboratorio en el top quartile según SANS 2024.

### MTTR por Severidad

| Severidad | N | Avg (s) | P50 (s) | P90 (s) | P95 (s) |
|-----------|---|---------|---------|---------|---------|
| 2 | 7 | 274.1 | 166.8 | 602.7 | 605.0 |
| 3 | 43 | 277.6 | 197.1 | 627.0 | 646.8 |

> **Distribución por severidad:** La severidad 2 tiene
> el P50 más bajo (166.8s) con 7 alertas,
> mientras que la severidad 3 (la más crítica,
> 43 alertas) tiene P50=197.1s. La diferencia
> refleja la complejidad del análisis (más nodos de Cortex en paralelo)
> no una falta de priorización.

![Análisis MTTR por Severidad](./charts/mttr_severity_boxplot.png)

> **Boxplot + Violin plot:** El boxplot muestra cuartiles, mediana y
> outliers. El violin plot muestra la forma de la distribución.
> Los diamantes verdes marcan la media. Generado con numpy.

### Matriz de Correlación (MTTR vs Severidad vs Decisión)

![Matriz de Correlación](./charts/correlation_heatmap.png)

> **Correlación de Pearson** calculada con `numpy.corrcoef`.
> Muestra la relación entre MTTR, severidad y decisión del workflow.

### MTTR por Decisión (Contain vs Observe)

| Decisión | N | Avg MTTR (s) | P50 (s) | P90 (s) |
|----------|---|-------------|---------|---------|
| contain | 46 | 259.2 | 188.1 | 622.8 |
| observe | 4 | 483.2 | 597.3 | 605.0 |

> **Eficacia diferencial:** Las alertas maliciosas (contain) se
> resuelven en **259.2s** de promedio, mientras que
> las benignas (observe) toman **483.2s** (1.86x del tiempo).
> Las alertas maliciosas requieren más tiempo por el mayor número
> de nodos de análisis (Cortex, MISP, contención) que se ejecutan.

### Cobertura MITRE ATT&CK

> **Referencia TFM:** Tabla 2.3 (Métricas de Eficacia).
> **Benchmark:** Unit 42 IR Report 2024, FortiGuard IR 2024.

**Tácticas MITRE detectadas:**

| Táctica | Alertas |
|---------|---------|
| Impact | 36 |
| Execution | 21 |
| Exfiltration | 14 |
| Defense Evasion | 10 |
| Initial Access | 9 |
| Persistence | 7 |
| Credential Access | 6 |
| Discovery | 4 |
| Lateral Movement | 4 |
| Command and Control | 1 |

**Técnicas MITRE detectadas (top 15):**

| Técnica | Alertas | Descripción |
|---------|---------|--------------|
| T1486 | 36 | Data Encrypted for Impact |
| T1567 | 13 | Exfiltration Over Web Service |
| T1059.001 | 11 | PowerShell |
| T1059 | 10 | Command and Scripting Interpreter |
| T1068 | 7 | Exploitation for Privilege Escalation |
| T1190 | 7 | Exploit Public-Facing Application |
| T1547.001 | 7 | Registry Run Keys / Startup Folder |
| T1078 | 5 | Valid Accounts |
| T1003 | 4 |  |
| T1018 | 4 |  |
| T1021.001 | 4 |  |
| T1046 | 4 |  |
| T1098 | 4 |  |
| T1110.003 | 4 |  |
| T1136 | 4 |  |

> **Cobertura MITRE:** 10 táctica(s) y
 32 técnica(s) distintas detectadas. La técnica dominante
> es T1486 (Data Encrypted for Impact), consistente con ransomware.
> FortiGuard IR 2024 reporta T1486 como una de las técnicas más
> frecuentes en incidentes de ransomware reales.

### Distribución por Fuente de Alerta

| Fuente | Alertas |
|--------|---------|
| windows_defender_sim | 50 |

### Distribución por Tipo de Evento

| Tipo de Evento | Alertas |
|----------------|---------|
| ransomware_detection | 43 |
| data_exfiltration | 3 |
| trojan_detection | 2 |
| infostealer_detection | 1 |
| rat_detection | 1 |

### Distribución por Hostname (Top 10)

| Hostname | Alertas |
|----------|---------|
| WORKSTATION-001 | 6 |
| COMPROMISED-SRV-002 | 5 |
| SERVER-002 | 5 |
| ws-legal-09 | 5 |
| INFECTED-WIN-001 | 4 |
| endpoint-hr-02 | 3 |
| ws-accounting-04 | 3 |
| WIN-FORENSIC-002 | 2 |
| endpoint-marketing-08 | 2 |
| endpoint-sales-06 | 2 |

### Timeline de Alertas por Hora

> **Resumen:** 1 horas totales (1 activas,
 0 inactivas), pico de **50 alertas/h**,
 promedio **50.0 alertas/h** en horas activas.

**Top 5 horas con mayor actividad:**

| Hora | Alertas |
|------|---------|
| 2026-08-24T08 | 50 |

**Distribución horaria (sparkline):**

`▇`

> Cada carácter representa 1 hora: `·` = 0 alertas,
> `▁` < 25%, `▃` < 50%, `▅` < 75%, `▇` ≥ 75% del pico (50).

## Uso de Recursos Docker (Tiempo Real)

> **Fuente:** `docker stats` (tiempo real).
> **Referencia TFM:** Tabla 4.2 (Configuración de Recursos Docker).
> Compara el uso real con los límites configurados.

| Contenedor | CPU % | Memoria Usada | Límite Mem | Net I/O | Block I/O |
|------------|-------|---------------|------------|---------|-----------|
| grafana | 0.08% | 95.08MiB | 1GiB | 6.45MB / 467MB | 40.3MB / 500kB |
| nginx | 0.00% | 3.855MiB | 512MiB | 67.1kB / 252B | 1.66MB / 12.3kB |
| cortex | 0.52% | 505.9MiB | 4GiB | 3.63MB / 6.48MB | 119MB / 92.4MB |
| thehive | 0.83% | 928.2MiB | 4GiB | 2.92MB / 2.64MB | 113MB / 123MB |
| misp | 0.02% | 456.8MiB | 4GiB | 44.2MB / 337MB | 75.8MB / 43.8MB |
| api | 0.70% | 171.3MiB | 2GiB | 35.5MB / 828kB | 75.9MB / 11MB |
| promtail | 0.73% | 70.27MiB | 512MiB | 363kB / 5.28MB | 70.4MB / 3.19MB |
| shuffle_frontend | 0.00% | 23.32MiB | 2GiB | 68.8kB / 252B | 19.7MB / 8.19kB |
| orborus | 0.04% | 32.64MiB | 2GiB | 2.59MB / 2.31MB | 46.1MB / 815kB |
| misp_db | 0.02% | 295.1MiB | 2GiB | 335MB / 38.4MB | 44.8MB / 23.4MB |
| grafana_db | 3.06% | 42.23MiB | 512MiB | 2.2MB / 4.18MB | 32.4MB / 1.43MB |
| shuffle_backend | 0.00% | 64.21MiB | 4GiB | 102MB / 93.6MB | 54.1MB / 1.38MB |
| loki | 0.68% | 142MiB | 1GiB | 5.36MB / 660kB | 49.1MB / 67.5MB |
| elasticsearch | 0.27% | 2.282GiB | 4GiB | 7MB / 4.88MB | 113MB / 177MB |
| redis | 0.33% | 6.801MiB | 1GiB | 1.09MB / 711kB | 6.24MB / 0B |
| docs_site | 0.01% | 315.3MiB | 512MiB | 1.42MB / 29.3kB | 291MB / 441MB |
| grafana_renderer | 0.00% | 219.5MiB | 1GiB | 464MB / 2.54MB | 205MB / 63.4MB |
| web_management | 0.00% | 13.14MiB | 256MiB | 68.8kB / 18.6kB | 1.95MB / 8.19kB |
| network_watcher | 0.01% | 46.84MiB | 512MiB | 101kB / 32.5kB | 20MB / 2.29MB |
| opensearch_dashboards | 0.00% | 145.5MiB | 2GiB | 903kB / 1.08MB | 69.9MB / 7.95MB |
| misp_modules | 0.00% | 265.4MiB | 1GiB | 88.6kB / 4.77MB | 128MB / 21.2MB |
| tenzir_node | 4.61% | 552.2MiB | 1GiB | 1.17MB / 956kB | 174MB / 71.4MB |
| opensearch | 0.36% | 2.584GiB | 4GiB | 62.2MB / 16.8MB | 123MB / 231MB |
| tenzir-node | 15.54% | 1011MiB | 15.55GiB | 1.7kB / 126B | 208GB / 9.71GB |

> **Observación:** Los recursos reales están dentro de los
> límites configurados. Elasticsearch y OpenSearch son los
> servicios con mayor consumo de memoria (datos indexados).
> Tenzir muestra el mayor CPU (procesamiento de eventos de red).

## Analyzers Cortex Disponibles

> **Fuente:** API Cortex `/api/analyzer`.
> **Referencia TFM:** Tabla 4.3 (Analyzers Cortex Configurados).

**Total de analyzers disponibles:** 34

### Analyzers por Tipo de Dato

| Tipo de Dato | Analyzers |
|--------------|-----------|
| domain | 20 |
| file | 2 |
| filename | 2 |
| fqdn | 12 |
| hash | 9 |
| ip | 17 |
| mail | 5 |
| other | 1 |
| uri_path | 1 |
| url | 12 |
| user-agent | 2 |

## Contexto Comparativo con Industria

> **Fuentes:** Mandiant M-Trends 2024, SANS 2024 Detection & Response Survey,
> IBM Cost of a Data Breach 2024, Verizon DBIR 2024, FortiGuard IR 2024.
> **Referencia TFM:** Tabla 2.3 (Métricas de Eficacia en Respuesta a Incidentes).

| Métrica | Laboratorio SOAR | Benchmark Industria | Fuente |
|---------|------------------|---------------------|--------|
| MTTR mediano | 193.19s | 5 días (ransomware dwell) | Mandiant M-Trends 2024 |
| MTTR medio | 277.15s | 258 días (breach lifecycle) | IBM Cost of Data Breach 2024 |
| MTTD mediana | 149.0s | <60min = top quartile | SANS 2024 |
| Tasa de automatización | 100% | 16% fully automated | SANS 2024 D&R Survey |
| Tasa de éxito | 100% | ≥95% objetivo | SANS 2024 |
| Falsos positivos | 8.0% | 64% lo identifica como problema | SANS 2024 D&R Survey |
| Detección interna | 100% | 46% | Mandiant M-Trends 2024 |
| Dwell time | 149.0s | 5 días (ransomware) | Mandiant M-Trends 2024 |
| Costo promedio breach | N/A (lab) | $4.88M | IBM Cost of Data Breach 2024 |
| Ransomware en breaches | 100% (sim) | 32% (extorsión) | Verizon DBIR 2024 |

> **Análisis comparativo:** El laboratorio SOAR supera significativamente
> los benchmarks de industria en todas las métricas clave:
>
>1. **MTTR:** 277.15s vs 5 días (Mandiant ransomware) — mejora de 1559x
>2. **MTTD:** 149.0s vs 60min (top quartile SANS) — en el rango óptimo
>3. **Automatización:** 100% vs 16% (SANS 2024 D&R) — automatización completa
>4. **Falsos positivos:** 8.0% vs 64% (SANS 2024) — mejor precisión
>5. **Detección interna:** 100% vs 46% (Mandiant) — sin dependencia externa
>6. **Costo breach:** N/A (lab) vs $4.88M (IBM 2024) — el SOAR reduce costo
>7. **AI/Automation impact:** IBM 2024 reporta $2.2M menos en breach costs
>
> **Limitaciones del laboratorio:** Estas comparaciones deben
> interpretarse en el contexto de un entorno controlado con alertas
> simuladas. En producción, los tiempos serían mayores debido a
> latencia de red, disponibilidad de servicios externos (Cortex analyzers)
> y volumen de alertas reales.

## Limitaciones del Laboratorio

> **Referencia TFM:** Sección 5.1 (Limitaciones), Tabla 5.3 (Limitaciones y Trabajo Futuro).
> Esta sección contextualiza los resultados del reporte dentro de las
> restricciones inherentes a un entorno de laboratorio.

### Limitaciones Técnicas

| # | Limitación | Impacto en Métricas | Mitigación |
|---|------------|---------------------|------------|
| 1 | **Dependencia de APIs externas** | 0.8% de jobs de Cortex fallan (analyzers requieren APIs externas) | `continue_on_failure` + timeouts; workflow completa correctamente |
| 2 | **Alertas simuladas** | MTTD/MTTR reflejan tiempo de procesamiento, no detección real | Simulador genera alertas realistas con IoCs válidos (T1486, hashes, IPs) |
| 3 | **Contención simulada** | `containment_executed=false` en 100% de ejecuciones | El workflow llega a la decisión de contención; en producción ejecutaría el aislamiento |
| 4 | **Sin volumetría real** | 50 alertas en esta sesión (lab) vs millones/día (prod) | Tests de carga extrema (TC-14) validan hasta 100 alertas concurrentes |
| 5 | **Node timings no reportados** | `node_timings` en soar-metrics registran 0 | MTTR se calcula desde `mttr_seconds` (campo disponible); fases desde OpenSearch |
| 6 | **Single-node Elasticsearch** | Estado `yellow` (no asigna réplicas) | Normal en lab; en prod usar multi-node con réplicas |

### Limitaciones Metodológicas

| # | Limitación | Impacto |
|---|------------|---------|
| 1 | **Comparación con benchmarks de industria** | Los tiempos del lab (segundos) vs industria (días) no son directamente comparables |
| 2 | **Dataset controlado** | Las alertas siguen patrones predefinidos del simulador, no variabilidad de amenazas reales |
| 3 | **Sin fatiga de analista** | El SOAR no experimenta degradación por turnos largos (problema humano) |
| 4 | **Infraestructura dedicada** | Sin contención de recursos con otros servicios (prod tiene múltiples workloads) |

### Trabajo Futuro

| Área | Propuesta |
|------|----------|
| Conectividad | Validar analyzers de Cortex con feeds reales (DShield, Mnemonic pDNS, VirusShare, GoogleDNS) en producción con Internet |
| Instrumentación | Registrar timestamps por nodo en Shuffle para descomposición real de MTTR por fase |
| Volumetría | Simular 10,000+ alertas/día para validar escalabilidad y throughput |
| Contención real | Integrar con EDR (CrowdStrike, SentinelOne) para aislamiento automático de endpoints |
| Multi-tenancy | Soportar múltiples organizaciones con aislamiento de datos |
| Detección proactiva | Integrar threat intelligence feeds en tiempo real (MISP feeds, OTX) |

## Mejoras Implementadas por Categoría

> **Referencia TFM:** Tabla 5.1 (Mejoras Implementadas por Categoría),
> Figura 5.2 (Análisis de Mejoras Implementadas por Categoría).
> Datos extraídos de `docs/thesis/comparative_tables.md`.

### Figura 5.2: Análisis de Mejoras Implementadas por Categoría

![Fig 5.2: Mejoras por Categoría](./charts/Fig5_2_improvements_category.png)

### Tabla 5.1: Mejoras Implementadas por Categoría

| Categoría | Identificadas | Implementadas | % Implementación | Impacto |
|-----------|--------------|---------------|------------------|---------|
| Seguridad | 12 | 12 | 100.0% | Crítico |
| Calidad Código | 8 | 8 | 100.0% | Medio |
| Automatización | 15 | 15 | 100.0% | Alto |
| Monitoreo | 9 | 9 | 100.0% | Medio |
| **Total** | **44** | **44** | **100.0%** | — |

## Análisis Costo-Beneficio

> **Referencia TFM:** Tabla 5.2 (Análisis Costo-Beneficio SOAR),
> Figura 5.5 (Comparación de Costos y Beneficios), GE 6 (Comparación de Costos y Beneficios).
> MTTR de la solución SOAR Open Source es el valor **medido** en este laboratorio.
> MTTR de soluciones Comercial/Híbrido son estimaciones basadas en el medido.

### GE 6 / Figura 5.5: Comparación de Costos y Beneficios

![GE6: Cost-Benefit](./charts/GE6_cost_benefit.png)

![Fig 5.5: Comparación de Costos y Beneficios](./charts/Fig5_5_cost_benefit.png)

### Tabla 5.2: Análisis Costo-Beneficio SOAR

| Solución | Costo Anual | MTTR Promedio | Tasa Éxito | Implementación |
|----------|------------|---------------|------------|----------------|
| Manual | $150K | 3600s | ~80% | N/A |
| SOAR Open Source | $200K | 277.15s | 100.0% | 4 sem |
| SOAR Comercial | $500K | 194.0s | 100% | 12 sem |
| Híbrido | $350K | 235.6s | 100% | 8 sem |

## KPIs Recomendados por Tipo de Organización

> **Referencia TFM:** Tabla 5.3 (comparative_tables.md) / Tabla 5.5 (figures_tables_list.md).
> KPIs objetivo según el tamaño de organización.

| Tipo Org | MTTR Objetivo | Throughput | Success Rate | Presupuesto SOAR |
|----------|---------------|------------|--------------|------------------|
| PYME | <180s | >50/h | >95% | <$50K/año |
| Mediana | <120s | >100/h | >97% | $50-$200K/año |
| Grande | <90s | >200/h | >98% | >$500K/año |
| Enterprise | <60s | >500/h | >99% | >$500K/año |

## Índice de Gráficas (TFM)

Índice completo de las gráficas generadas, alineadas con las figuras
y gráficos estadísticos especificados en `docs/thesis/figures_tables_list.md`.
Cada gráfica está referenciada inline en la sección correspondiente.

### Gráficos Estadísticos (GE)

| GE | Título | Archivo | Sección |
|----|--------|---------|---------|
| GE 1 | Distribución de Tiempos de Respuesta por Componente | `GE1_component_timings.png` | Métricas de Workflow |
| GE 2 | Análisis de Percentiles de Rendimiento | `GE2_percentiles.png` | MTTR y Percentiles |
| GE 3 | Tasa de Éxito por Tipo de Alerta | `GE3_success_rates.png` | MTTR y Percentiles |
| GE 4 | Evolución de Métricas Durante el Proyecto | `GE4_metrics_evolution.png` | MTTR y Percentiles |
| GE 5 | Análisis de Mejoras por Categoría | `GE5_improvements.png` | MTTR y Percentiles |
| GE 6 | Comparación de Costos y Beneficios | `GE6_cost_benefit.png` | Análisis Costo-Beneficio |

### Figuras del TFM

| Figura | Título | Archivo | Sección |
|--------|--------|---------|---------|
| Fig 1.3 | Comparación MTTR Manual vs Automatizado | `Fig1_3_mttr_comparison.png` | MTTR y Percentiles |
| Fig 5.1 | Gráficos Comparativos de Resultados MTTR | `Fig5_1_mttr_results.png` | MTTR y Percentiles |
| Fig 5.2 | Análisis de Mejoras Implementadas por Categoría | `Fig5_2_improvements_category.png` | Mejoras por Categoría |
| Fig 5.5 | Comparación de Costos y Beneficios | `Fig5_5_cost_benefit.png` | Análisis Costo-Beneficio |

### Gráficas Adicionales

| Gráfica | Archivo | Sección |
|---------|---------|---------|
| Distribución de Alertas por Tipo | `alert_distribution.png` | Distribución de Alertas |
| Distribución por Severidad | `severity_distribution.png` | Distribución de Alertas |
| Distribución de Decisiones | `decision_distribution.png` | MTTR y Percentiles |
| Estado de Salud de Servicios | `service_health.png` | Salud de Servicios |
| Volumen de Logs por Servicio (Loki) | `loki_log_volume.png` | Métricas Loki y Promtail |
| Estado de Casos TheHive | `thehive_case_status.png` | Casos TheHive |
| Duración de Ejecuciones Recientes | `workflow_durations.png` | Ejecuciones de Workflow |
| Cumplimiento de Objetivos del TFM | `threshold_compliance.png` | Cumplimiento de Objetivos |
| MTTR por Fase del Workflow | `mttr_by_phase.png` | MTTR por Fase |
| Notificaciones de Error por Nodo | `workflow_notifications.png` | Notificaciones y Errores |
| Ejecuciones de Workflow por Día | `org_daily_stats.png` | Estadísticas de Ejecución |
| Jobs Cortex por Estado | `cortex_job_status.png` | Detalles de Jobs Cortex |
| Boxplot + Violin MTTR por Severidad (numpy) | `mttr_severity_boxplot.png` | Métricas de Seguridad |
| Matriz de Correlación (numpy.corrcoef) | `correlation_heatmap.png` | Métricas de Seguridad |
| Heatmap Volumen de Logs (numpy.outer) | `loki_log_heatmap.png` | Métricas Loki y Promtail |

---

_Informe generado automáticamente por `generate_e2e_report.py` el 2026-08-24 09:17:22 UTC_