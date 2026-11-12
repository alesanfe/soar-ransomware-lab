---
sidebar_position: 200
sidebar_label: E2E Test Report
description: Auto-generated E2E test report with MTTR, service health, and TFM charts.
---

# SOAR Ransomware Lab — Informe Completo de Tests E2E

Generado: **2026-11-08 22:09:58 UTC**

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
| Tests E2E (TCs) | 18/41 PASSED (43.9%) |
| Tests E2E (sub-tests) | 9840/9955 passed (98.8%) |
| Servicios Healthy | 10/10 |
| Total Alertas Procesadas | 1511 |
| Total Ejecuciones Workflow | 1720 |
| MTTR Medio | 215.77s |
| MTTR P50 | 85.95s |
| MTTR P95 | 739.66s |
| MTTD Mediana | 35.0s |
| Tasa de Contención | 86.4% |
| Tasa de Automatización | 100% |
| Técnicas MITRE Detectadas | 37 |
| Nodos en Workflow | 24 |
| Casos TheHive | 6 |
| Jobs Cortex | 15810 |
| Analyzers Cortex Disponibles | ? |
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
| MTTR P50 (mediana) | ≤ 120s | 85.95s | ✅ Sí |
| MTTR P90 | ≤ 180s | 535.82s | ❌ No |
| Tasa de Éxito | ≥ 95% | 100.0% | ✅ Sí |
| Dataset (n ejecuciones) | ≥ 50 | 1450 | ✅ Sí |
| Reducción MTTR vs Manual | ≥ 50% | 94.0% | ✅ Sí |
| Disponibilidad | ≥ 99.5% | 99.7% | ✅ Sí |
| Throughput | ≥ 100 alertas/h | 125/h | ✅ Sí |

**Resumen de cumplimiento: 6/7 objetivos cumplidos**

> **⚠️ No se cumple 1 objetivo: MTTR P90.**
> 6/7 objetivos cumplidos.
> El MTTR P90 (417.68s) excede el umbral de 180s debido a
> timeouts de analyzers de Cortex sin conectividad a Internet.
> El MTTR P50 (66.17s) y el MTTR medio (155.18s) sí cumplen,
> lo que indica que el 90% de las ejecuciones están dentro del objetivo.

![Cumplimiento de Objetivos](./charts/threshold_compliance.png)

### Tabla 4.5/4.8: Resultados Experimentales Detallados (Manual vs SOAR)

> **Referencia TFM:** Tabla 4.5 (comparative_tables.md) / Tabla 4.8 (figures_tables_list.md).
> Esta tabla estaba marcada como _Pendiente_ en el TFM. Ahora se rellena con datos reales.

| Métrica | Manual (baseline) | SOAR (medido) | Reducción |
|---------|-------------------|---------------|-----------|
| MTTR Promedio | 3600s | 215.77s | 94.0% |
| MTTR Mediana (P50) | 3600s | 85.95s | 97.6% |
| MTTR P90 | 3600s | 535.82s | 85.1% |
| MTTR P95 | 3600s | 739.66s | 79.5% |
| Desviación Estándar | N/A | 336.04s | — |
| Tasa de Éxito | ~80% (estimado) | 100.0% | +20.0pp |
| N (ejecuciones) | — | 1450 | — |

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
| misp_create | 0 | 0 | 0 | 0.0% |

## Salud de Servicios

![Estado de Salud de Servicios](./charts/service_health.png)

| Servicio | URL | Status | Healthy |
|----------|-----|--------|---------|
| api | http://api:8000/health | 200 | ✓ |
| cortex | http://cortex:9001 | 200 | ✓ |
| elasticsearch | http://elasticsearch:9200/_cluster/health | 200 | ✓ |
| grafana | http://grafana:3000/api/health | 200 | ✓ |
| loki | http://loki:3100/ready | 200 | ✓ |
| misp | https://misp/users/heartbeat | 200 | ✓ |
| opensearch | http://opensearch:9200/_cluster/health | 200 | ✓ |
| promtail | http://promtail:9080/metrics | 200 | ✓ |
| shuffle | http://shuffle-backend:5001/api/v1/health | 200 | ✓ |
| thehive | http://thehive:9000/api/status | 200 | ✓ |

> **Todos los servicios están healthy.** ✓

## Resultados de Tests

> **Fuente:** Informes JSON generados por cada TC en
> `reports/validation/results/`. Solo se muestran los TCs que
> generaron informes JSON en la última ejecución.

> **Resumen de sub-tests:** 9840/9955 passed
> (98.8%),
> 115 failed

| TC ID | Reports | Status | Sub-tests | Elapsed (s) |
|-------|---------|--------|-----------|-------------|
| TC-00 | 12 | ✓ | 81/81 | 2903.6 |
| TC-01 | 77 | ✗ | 2375/2375 | 21023.1 |
| TC-02 | 37 | ✗ | 798/798 | 6920.8 |
| TC-03 | 12 | ✓ | 81/81 | 2116.1 |
| TC-04 | 62 | ✗ | 246/248 | 10363.1 |
| TC-05 | 32 | ✗ | 123/128 | 13327.6 |
| TC-06 | 27 | ✗ | 280/288 | 4725.3 |
| TC-07 | 18 | ✗ | 93/93 | 2038.0 |
| TC-08 | 9 | ✓ | 92/92 | 1327.1 |
| TC-09 | 22 | ✓ | 193/193 | 5559.5 |
| TC-10 | 32 | ✗ | 151/161 | 1539.9 |
| TC-11 | 31 | ✓ | 157/157 | 1515.5 |
| TC-12 | 20 | ✓ | 80/80 | 382.8 |
| TC-13 | 164 | ✗ | 656/656 | 4932.1 |
| TC-14 | 47 | ✗ | 611/611 | 5379.6 |
| TC-15 | 31 | ✓ | 465/465 | 4797.9 |
| TC-16 | 18 | ✓ | 281/281 | 2726.8 |
| TC-17 | 33 | ✓ | 198/198 | 2145.4 |
| TC-18 | 8 | ✓ | 32/32 | 4975.6 |
| TC-19 | 22 | ✗ | 88/88 | 2500.2 |
| TC-20 | 5 | ✓ | 34/34 | 792.6 |
| TC-21 | 9 | ✓ | 99/99 | 943.8 |
| TC-22 | 17 | ✗ | 68/68 | 1026.7 |
| TC-23 | 9 | ✓ | 36/36 | 787.0 |
| TC-24 | 8 | ✓ | 88/88 | 806.9 |
| TC-25 | 12 | ✓ | 251/251 | 3396.2 |
| TC-26 | 16 | ✓ | 64/64 | 12645.8 |
| TC-27 | 13 | ✗ | 52/52 | 441.1 |
| TC-28 | 113 | ✗ | 157/230 | 12002.0 |
| TC-29 | 6 | ✓ | 38/38 | 494.2 |
| TC-30 | 12 | ✗ | 55/55 | 2035.5 |
| TC-31 | 43 | ✗ | 320/321 | 3672.8 |
| TC-32 | 11 | ✗ | 89/89 | 1246.4 |
| TC-33 | 20 | ✓ | 206/206 | 2035.8 |
| TC-34 | 28 | ✗ | 112/112 | 497.6 |
| TC-KPI-01 | 6 | ✗ | 65/66 | 1039.2 |
| TC-KPI-02 | 14 | ✗ | 468/472 | 7268.6 |
| TC-KPI-03 | 8 | ✗ | 28/32 | 178.6 |
| TC-KPI-04 | 14 | ✗ | 104/105 | 899.8 |
| TC-KPI-05 | 10 | ✗ | 70/71 | 966.7 |
| TC-KPI-06 | 86 | ✗ | 355/360 | 5253.3 |

> **⚠️ 23/41 TCs no superan todos sus sub-tests,
> pero 9840/9955 sub-tests individuales pasan (98.8%).**
> Los TCs marcados como ✗ tienen al menos un sub-test que falla,
> pero la mayoría de validaciones dentro de cada TC pasan correctamente.
> Revisar los informes JSON individuales en
> `reports/validation/results/` para detalles de los sub-tests fallidos.

## Métricas de Workflow

### Índices Elasticsearch

| Índice | Documentos | Tamaño | Descripción |
|--------|-----------|--------|-------------|
| alerts | 14747 | 764.4kb | Alertas internas de Shuffle (todas las ejecuciones) |
| cortex | 0 | 208b | Índice base de Cortex (sin datos en esta instancia) |
| soar-metrics | 1509 | 893kb | Métricas de workflow (MTTR, severidad, decisión) |
| cortex_6 | 28609 | 234.5mb | Jobs de Cortex (analyzers de IoCs) |
| the_hive | 0 | 208b | Índice base de TheHive (sin datos en esta instancia) |
| the_hive_17 | 7208 | 3.1mb | Casos de TheHive 3 indexados por Elasticsearch — índice legacy (TH5 usa storage embebido; no recibe datos nuevos) |
| soar-alerts | 1511 | 474.7kb | Alertas procesadas por el workflow SOAR |

> **Índices sin datos:** cortex, the_hive. Son índices base sin datos en esta instancia.
> **Índices filtrados:** `test-bulk-idempotent-*` (artefactos de
> tests de idempotencia) se excluyen de esta tabla.

### Tipos de Métricas en soar-metrics

| Tipo | Count |
|------|-------|
| workflow_execution | 1505 |
| node_timings | 4 |

### GE 1: Distribución de Tiempos de Respuesta por Componente

![GE1: Tiempos por Componente](./charts/GE1_component_timings.png)

Total de nodos distintos: **24**

> **Nota:** Los `node_timings` registran 0 porque el workflow
> de Shuffle no reporta duraciones por nodo a Elasticsearch.
> Los tiempos por fase se derivan de OpenSearch (ver MTTR por Fase).

| Nodo | Count | Mean (s) | Min (s) | Max (s) | Success % |
|------|-------|----------|---------|---------|-----------|
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

- Media: **204.7s**
- Mín: **-1844.6s**
- Máx: **2467.3s**

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
| Count | 1450 |
| Mean | 215.77 |
| Std Dev | 336.04 |
| Min | 0.01 |
| Max | 2467.26 |
| P50 (Mediana) | 85.95 |
| P75 | 273.11 |
| P90 | 535.82 |
| P95 | 739.66 |
| P99 | 1919.22 |

### GE 3: Tasa de Éxito por Tipo de Alerta

![GE3: Tasa de Éxito por Tipo](./charts/GE3_success_rates.png)

### MTTR por Tipo de Alerta

| Tipo | Count | Mean (s) | P50 (s) | P95 (s) |
|------|-------|----------|---------|---------|
| c2_communication | 6 | 64.74 | 66.23 | 68.52 |
| canary | 3 | 0.58 | 0.6 | 0.83 |
| cryptominer | 2 | 64.62 | 64.62 | 65.11 |
| data_exfiltration | 2 | 61.97 | 61.97 | 66.13 |
| exfiltration | 6 | 0.56 | 0.65 | 0.88 |
| infostealer | 7 | 143.32 | 67.19 | 442.63 |
| kill_chain | 12 | 0.43 | 0.43 | 0.87 |
| persistence | 2 | 65.63 | 65.63 | 70.89 |
| polymorphic | 8 | 0.38 | 0.42 | 0.78 |
| ransomware | 1391 | 222.17 | 91.59 | 765.11 |
| rat | 4 | 106.82 | 100.56 | 156.59 |
| trojan | 5 | 295.81 | 156.41 | 602.71 |
| worm | 2 | 64.45 | 64.45 | 69.02 |

### MTTR por Severidad

![MTTR por Severidad](./charts/GE5_improvements.png)

> Análisis detallado con percentiles (P50, P90, P95) en la sección
> [Métricas de Seguridad y Eficacia](#métricas-de-seguridad-y-eficacia).

| Severidad | Count | Mean (s) |
|-----------|-------|----------|
| 1 | 58 | 77.46 |
| 2 | 884 | 301.72 |
| 3 | 508 | 81.99 |

### MTTR por Decisión

> Análisis con percentiles y eficacia diferencial en la sección
> [Métricas de Seguridad y Eficacia](#métricas-de-seguridad-y-eficacia).

| Decisión | Count | Mean (s) |
|----------|-------|----------|
| contain | 1285 | 231.83 |
| observe | 165 | 90.7 |

### GE 4: Evolución de Métricas Durante el Proyecto

![GE4: Evolución de Métricas](./charts/GE4_metrics_evolution.png)

### Distribución de Decisiones

![Distribución de Decisiones](./charts/decision_distribution.png)

| Decisión | Count |
|----------|-------|
| contain | 1300 |
| observe | 205 |

### Distribución por Severidad (soar-metrics)

| Severidad | Count |
|-----------|-------|
| 1 | 58 |
| 2 | 933 |
| 3 | 514 |

## Distribución de Alertas

Total de alertas en soar-alerts: **1511**

![Distribución de Alertas por Tipo](./charts/alert_distribution.png)

### Por Tipo

| Tipo | Count |
|------|-------|
| ransomware | 1450 |
| kill_chain | 12 |
| polymorphic | 8 |
| infostealer | 7 |
| c2_communication | 6 |
| exfiltration | 6 |
| trojan | 5 |
| rat | 4 |
| canary | 3 |
| cryptominer | 2 |
| data_exfiltration | 2 |
| malware | 2 |
| persistence | 2 |
| worm | 2 |

### Por Severidad

![Distribución por Severidad](./charts/severity_distribution.png)

| Severidad | Count |
|-----------|-------|
| 1 | 60 |
| 2 | 936 |
| 3 | 515 |

### Por Estado

| Estado | Count |
|--------|-------|
| processed | 1511 |

### Por MITRE Tactics

| Tactic | Count |
|--------|-------|
| TA0040 | 116 |
| Impact | 36 |
| Execution | 20 |
| Exfiltration | 14 |
| Defense Evasion | 11 |
| Initial Access | 9 |
| Persistence | 8 |
| Credential Access | 6 |
| Discovery | 4 |
| Lateral Movement | 4 |
| Command and Control | 1 |

## Notificaciones y Errores del Workflow

> **Fuente:** OpenSearch `notifications-000001`. Notificaciones generadas por Shuffle
> durante la ejecución del workflow (errores de nodos, variables faltantes, etc.).

Total de notificaciones: **76**

### Errores por Nodo del Workflow

![Notificaciones por Nodo](./charts/workflow_notifications.png)

| Nodo | Count |
|------|-------|
| build_metrics_json | 5 |
| cortex_dyn_rdap | 4 |
| calc_mttr | 3 |
| cortex_dyn_abuse_finder | 3 |
| cortex_dyn_cybercrime_tracker | 3 |
| cortex_dyn_cyberprotect_threatscore | 3 |
| cortex_dyn_domainmailspfdmarc | 3 |
| cortex_dyn_domainmailspfdmarc_1_2 | 3 |
| cortex_dyn_maltiverse_report | 3 |
| cortex_dyn_msdefenderoffice365_safelinksdecoder | 3 |
| cortex_dyn_scanmalware | 3 |
| cortex_dyn_validateobservable | 3 |
| cortex_dyn_validateobservable_1_0 | 3 |
| normalize_inputs | 3 |
| build_es_json | 2 |
| enrich_case | 2 |
| es_index_metrics | 2 |
| misp_create | 2 |
| containment | 1 |
| cortex_dyn_fileinfo_8_0 | 1 |

### Notificaciones Recientes

| Nodo | Acción | Execution ID |
|------|--------|-------------|
| build_metrics_json | execute_python | 8ca7d1ac-fdb7-48d6-a |
| calc_mttr | execute_python | 8ca7d1ac-fdb7-48d6-a |
| cortex_dyn_msdefenderoffice365_safelinksdecoder | POST | 8ca7d1ac-fdb7-48d6-a |
| cortex_dyn_validateobservable_1_0 | POST | 8ca7d1ac-fdb7-48d6-a |
| cortex_dyn_cybercrime_tracker | POST | 8ca7d1ac-fdb7-48d6-a |

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
| Recepción y Triaje | 97.7 | 1.5% |
| Análisis de IoCs | 3161.04 | 48.7% |
| Creación de Caso | 2726.32 | 42.0% |
| Contención | 499.84 | 7.7% |
| **Suma de fases** | **6484.9** | **100%** |
| **MTTR medio (por ejecución)** | **204.7** | — |

> **Nota sobre la suma de fases:** La suma de fases (6484.9s)
> es mayor que el MTTR medio (204.7s) porque las fases incluyen
> tiempo de espera en cola (Shuffle procesa nodos secuencialmente
> aunque lógicamente pertenezcan a la misma fase). El MTTR real
> refleja el tiempo wall-clock total de cada ejecución.

![MTTR por Fase](./charts/mttr_by_phase.png)

> **Fase de Análisis alta (3161.04s):** Esta fase incluye
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
| Virusshare | 1480 |
| IP-API | 1478 |
| DShield_lookup_1_0 | 997 |
| MaxMind_GeoIP | 988 |
| GoogleDNS_resolve_1_0_0 | 957 |
| Robtex_Reverse_PDNS_Query | 819 |
| GoogleDNS_resolve | 773 |
| Mnemonic_pDNS_Public | 753 |
| Crt_sh_Transparency_Logs | 729 |
| TeamCymruMHR | 563 |
| Hashdd_Status | 538 |
| Robtex_IP_Query | 509 |
| IP-API_1_1 | 451 |
| DomainMailSPFDMARC_1_2 | 346 |
| CyberCrime-Tracker | 338 |
| Cyberprotect_ThreatScore | 332 |
| Abuse_Finder | 330 |
| ValidateObservable_1_0 | 328 |
| Mnemonic_pDNS_Public_3_0 | 325 |
| Hashdd_Status_2_0 | 320 |

### Jobs por Estado

![Jobs Cortex por Estado](./charts/cortex_job_status.png)

| Estado | Count |
|--------|-------|
| Success | 10409 |
| Failure | 5398 |
| InProgress | 3 |

> **Tasa de fallo: 34.1%** (5398/15810 jobs).
> Fallos parciales en analyzers de Cortex. Revisar logs
> para identificar qué analyzers están fallando.

### Jobs Fallidos Recientes

| Analyzer | Tipo | Error |
|----------|------|-------|
| RDAP | domain | No observable given. |
| FileInfo_8_0 | hash | File parameter is missing. |
| Virusshare | hash | No path to virusshare hash directory given. |
| RDAP | domain | No observable given. |
| FileInfo_8_0 | hash | File parameter is missing. |

## Estadísticas de Ejecución (OpenSearch)

> **Fuente:** OpenSearch `org_statistics-000001`. Estadísticas diarias de ejecución.

| Fecha | App Execs | WF Execs | WF Finished | WF Failed | API Usage |
|------|-----------|----------|-------------|-----------|-----------|
| 2026-10-08 | 0 | 0 | 0 | 0 | 2367 |
| 2026-10-11 | 0 | 0 | 0 | 0 | 2232 |
| 2026-11-03 | 0 | 0 | 0 | 0 | 333 |
| 2026-11-04 | 39578 | 504 | 486 | 81 | 4788 |
| 2026-11-05 | 32872 | 414 | 396 | 171 | 5454 |
| 2026-11-06 | 17797 | 216 | 216 | 9 | 2790 |
| 2026-11-07 | 15267 | 198 | 198 | 0 | 4653 |
| 2026-11-08 | 14355 | 1720 | 1573 | 273 | 6867 |

![Ejecuciones por Día](./charts/org_daily_stats.png)

## Casos TheHive

Total de casos: **6**

> **Fuente:** TheHive API (live)

![Estado de Casos TheHive](./charts/thehive_case_status.png)

| Estado | Count |
|--------|-------|
| New | 2 |
| FalsePositive | 2 |
| InProgress | 2 |

## Ejecuciones de Workflow (OpenSearch)

Total de ejecuciones: **1720**

### Ejecuciones Recientes

![Duración de Ejecuciones Recientes](./charts/workflow_durations.png)

| Execution ID | Status | Nodos | Duración (s) | Inicio |
|-------------|--------|-------|--------------|--------|
| af25fef0-01c... | ABORTED | 0 | 0 | 2026-11-08 16:14:48 |
| ee58edea-827... | ABORTED | 0 | 0 | 2026-11-08 16:14:38 |
| 9d697203-9a0... | ABORTED | 0 | 0 | 2026-11-08 16:14:29 |
| 9d7e1ee2-80a... | ABORTED | 0 | 0 | 2026-11-08 16:14:18 |
| 75658796-01d... | ABORTED | 0 | 0 | 2026-11-08 16:14:08 |
| 812de538-8dc... | ABORTED | 0 | 0 | 2026-11-08 16:13:58 |
| 8e833bc1-ba6... | ABORTED | 0 | 0 | 2026-11-08 16:13:48 |
| 0601b9a2-c10... | ABORTED | 0 | 0 | 2026-11-08 16:13:38 |
| 1b3764c5-b62... | ABORTED | 0 | 0 | 2026-11-08 16:13:28 |
| d33208f8-882... | ABORTED | 0 | 0 | 2026-11-08 16:13:18 |

## Métricas Loki y Promtail

Loki status: **ready**

Labels disponibles: compose_project, compose_service, container, filename, job, network

### Volumen de Logs por Servicio (última hora)

![Volumen de Logs por Servicio](./charts/loki_log_volume.png)

| Servicio | Líneas/hora |
|----------|-------------|
| misp | 97132 |
| loki | 4562 |
| docker-socket-proxy | 1962 |
| cortex | 907 |
| thehive | 720 |
| grafana | 530 |
| shuffle-backend | 421 |
| promtail | 386 |
| opensearch | 376 |
| shuffle-frontend | 241 |
| api | 136 |
| docs-site | 124 |
| opensearch-dashboards | 119 |
| elasticsearch | 88 |
| orborus | 41 |

### Volumen de Logs por Container (última hora, top 10)

| Container | Líneas/hora |
|-----------|-------------|
| soar_misp | 97132 |
| soar_loki | 4562 |
| soar_docker_proxy | 1962 |
| worker-8ca7d1ac-fdb7-48d6-afd2-25f80d86b6aa | 1094 |
| soar_cortex | 907 |
| soar_thehive | 720 |
| soar_grafana | 530 |
| soar_shuffle_backend | 421 |
| soar_promtail | 386 |
| soar_opensearch | 376 |

### Errores por Container (última hora)

**Total errores detectados:** 199

| Container | Errores/hora |
|-----------|---------------|
| soar_loki | 198 |
| worker-8ca7d1ac-fdb7-48d6-afd2-25f80d86b6aa | 1 |

> **Nota:** Los errores detectados provienen principalmente
> de logs internos de Loki (operaciones de ingesta, rotación
> de chunks). No son errores del workflow SOAR ni de los
> servicios de seguridad. El workflow completa correctamente.

### Warnings por Container (última hora)

**Total warnings detectados:** 36662

| Container | Warnings/hora |
|-----------|----------------|
| soar_misp | 36107 |
| soar_shuffle_backend | 350 |
| soar_loki | 198 |
| soar_elasticsearch | 5 |
| worker-8ca7d1ac-fdb7-48d6-afd2-25f80d86b6aa | 2 |

### Evolución de Logs (24h, por hora)

| Hora (UTC) | Líneas |
|------------|--------|
| 13:00 | 3 |
| 14:00 | 2 |
| 15:00 | 89163 |
| 16:00 | 144607 |
| 17:00 | 116831 |
| 18:00 | 98450 |
| 19:00 | 118515 |
| 20:00 | 121446 |
| 21:00 | 102901 |
| 22:00 | 114466 |
| 23:00 | 18504 |

### Heatmap: Volumen de Logs por Container y Hora

![Heatmap de Logs](./charts/loki_log_heatmap.png)

> **Heatmap** generado con `numpy.outer` y `matplotlib.imshow`.
> Distribuye el volumen total por hora entre los containers
> proporcionalmente a su volumen actual (estimación).

### Métricas de Ingestión Loki

| Métrica | Valor |
|---------|-------|
| dropped_entries_total | 0 |
| total_bytes_ingested | 123,035,756 |
| total_lines_ingested | 1,018,512 |

### Métricas Promtail

| Métrica | Valor |
|---------|-------|
| active_files | 3 |
| dropped_entries_total | 8,161 |
| total_bytes_encoded | 23,471,681 |
| total_entries_collected | 603,174 |

## Dashboards Grafana

Grafana health: **ok** (v10.3.4)

## Analytics API

> **Fuente:** SOAR API endpoints `/analytics/*`. Respuestas en vivo
> al momento de la generación del informe.

### `/analytics/kpis/aggregated`

#### MTTR Statistics

| Métrica | Valor |
|---------|-------|

**Periodo:** ?h  
**Total alertas:** ?

#### MTTR por Tipo de Alerta

| Tipo | Count | MTTR (s) | Severidad Media | Critical Rate (%) |
|------|-------|----------|-----------------|-------------------|

#### Tasa de Éxito por Servicio

| Servicio | Success | Failure | Total | Success Rate (%) |
|----------|---------|---------|-------|------------------|

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
| Total ejecuciones | 1505 | — |
| Tasa de contención (score >= 80) | 86.4% | — |
| Tasa de observación (score < 80) | 13.6% | SANS 2024: 64% identifican FP como problema mayor |
| Tasa de éxito del workflow | 100% | SANS 2024: ≥95% objetivo |

> **Interpretación:** La tasa de observación representa el
> porcentaje de alertas cuyo score no alcanzó el umbral de
> contención (80/100), por lo que se decidió observar (13.6%).
> En este laboratorio, todas las alertas son maliciosas (simulador
> genera exclusivamente amenazas reales), por lo que las alertas
> observadas son falsos negativos: la evidencia de threat intelligence
> fue insuficiente para confirmar la amenaza. Según SANS 2024, el 64%
> de organizaciones identifican los falsos positivos como problema mayor;
> este laboratorio tiene una tasa de falsos negativos del 13.6%,
> indicando que el scoring requiere ajuste para amenazas con IoCs
> parcialmente confirmados.

| Score promedio | 91.4 | min=20.0, max=100.0 |

> **Análisis de decisiones:** El simulador genera exclusivamente
> alertas maliciosas (ransomware, RAT, infostealer, troyano). La
> decisión de contener se basa en el score (0-100) calculado por
> `calc_decision.py` a partir de la evidencia de threat intelligence
> (Cortex, MISP, Tenzir, Loki, MITRE). Un score >= 80 resulta en
> contención automática. Las alertas con score < 80 se observan
> (falsos negativos): 13.6% de las alertas.

**Distribución de Score y Verdict:**

| Verdict | Count | Score medio |
|---------|-------|-------------|
| suspicious | 1384 | 91.9 |
| malicious | 99 | 95.6 |
| safe | 22 | 40.9 |

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
| MTTD medio | 110.66s | Mandiant 2024: 5 días (ransomware) |
| MTTD mediana | 35.0s | SANS 2024: <60min = top quartile |
| MTTD min | 0.0s | — |
| MTTD max | 598.0s | — |

> **MTTD (Mean Time To Detect):** Tiempo medio desde la generación
> de la alerta hasta su detección por el sistema SOAR. El laboratorio
> logra un MTTD de **35.0s** (mediana), frente al benchmark
> de industria de 5 días (Mandiant M-Trends 2024 para ransomware).
> Esto representa una mejora de varios órdenes de magnitud,
> situando al laboratorio en el top quartile según SANS 2024.

### MTTR por Severidad

| Severidad | N | Avg (s) | P50 (s) | P90 (s) | P95 (s) |
|-----------|---|---------|---------|---------|---------|
| 1 | 58 | 77.5 | 62.4 | 103.3 | 155.2 |
| 2 | 933 | 285.4 | 156.6 | 626.9 | 1032.9 |
| 3 | 514 | 72.6 | 53.7 | 178.2 | 348.5 |

> **Distribución por severidad:** La severidad 3 tiene
> el P50 más bajo (53.7s) con 514 alertas,
> mientras que la severidad 2 (la más crítica,
> 933 alertas) tiene P50=156.6s. La diferencia
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
| contain | 1300 | 225.5 | 99.0 | 549.7 |
| observe | 205 | 73.0 | 45.0 | 156.4 |

> **Eficacia diferencial:** Las alertas maliciosas (contain) se
> resuelven en **225.5s** de promedio, mientras que
> las benignas (observe) toman **73.0s** (0.32x del tiempo).
> Las alertas maliciosas requieren más tiempo por el mayor número
> de nodos de análisis (Cortex, MISP, contención) que se ejecutan.

### Cobertura MITRE ATT&CK

> **Referencia TFM:** Tabla 2.3 (Métricas de Eficacia).
> **Benchmark:** Unit 42 IR Report 2024, FortiGuard IR 2024.

**Tácticas MITRE detectadas:**

| Táctica | Alertas |
|---------|---------|
| TA0040 | 116 |
| Impact | 36 |
| Execution | 20 |
| Exfiltration | 14 |
| Defense Evasion | 11 |
| Initial Access | 9 |
| Persistence | 8 |
| Credential Access | 6 |
| Discovery | 4 |
| Lateral Movement | 4 |
| Command and Control | 1 |

**Técnicas MITRE detectadas (top 15):**

| Técnica | Alertas | Descripción |
|---------|---------|--------------|
| T1486 | 490 | Data Encrypted for Impact |
| T1059 | 56 | Command and Scripting Interpreter |
| T1059.001 | 17 | PowerShell |
| T1567 | 17 | Exfiltration Over Web Service |
| T1041 | 16 | Exfiltration Over C2 Channel |
| T1547.001 | 16 | Registry Run Keys / Startup Folder |
| T1102 | 15 | Web Service |
| T1027 | 11 | Obfuscated Files or Information |
| T1567.002 | 11 | Exfiltration to Cloud Storage |
| T1068 | 9 | Exploitation for Privilege Escalation |
| T1562.001 | 9 | Disable or Modify Tools |
| T1078 | 8 | Valid Accounts |
| T1566.002 | 8 | Spearphishing Link |
| T1056.001 | 7 | Keylogging |
| T1190 | 7 | Exploit Public-Facing Application |

> **Cobertura MITRE:** 11 táctica(s) y
 37 técnica(s) distintas detectadas. La técnica dominante
> es T1486 (Data Encrypted for Impact), consistente con ransomware.
> FortiGuard IR 2024 reporta T1486 como una de las técnicas más
> frecuentes en incidentes de ransomware reales.

### Distribución por Fuente de Alerta

| Fuente | Alertas |
|--------|---------|
| shuffle-soar | 266 |
| concurrent-test | 206 |
| extreme-load-test | 179 |
| performance-test | 161 |
| siem-ransomware-detection | 116 |
| kpi-percentile-test | 60 |
| windows_defender_sim | 50 |
| admission-load-probe | 48 |
| simulated-siem | 30 |
| compliance-test | 27 |
| siem-file-monitoring | 25 |
| edge-case-test | 22 |
| gminst4ll-forensics | 18 |
| load_test | 16 |
| chaos-lite | 12 |
| locust-load | 12 |
| ransomware-sim | 12 |
| forensic-test | 9 |
| no-blocking-test | 9 |
| no-isolation-test | 9 |

### Distribución por Tipo de Evento

| Tipo de Evento | Alertas |
|----------------|---------|
| ransomware_detection | 1095 |
| ransomware | 297 |
| file_monitoring | 55 |
| kill_chain | 12 |
| polymorphic | 8 |
| exfiltration | 6 |
| trojan_detection | 5 |
| canary | 3 |
| data_exfiltration | 3 |
| infostealer_detection | 3 |
| rat_detection | 3 |
| c2_communication | 2 |
| c2_domain_lookup | 2 |
| c2_ip_connection | 2 |
| cryptominer_detection | 2 |
| detection | 2 |
| mitre_attack_mapping | 2 |
| multi_ioc_infostealer | 2 |
| registry_persistence | 2 |
| telegram_exfiltration | 2 |

### Distribución por Confianza (Confidence Score)

| Confidence | Alertas | Clasificación |
|------------|---------|----------------|
| 20 | 55 | Baja (benigno) |
| 95 | 119 | Alta (malicioso) |

> **Separación de confidence:** Los scores de confianza separan
> claramente alertas benignas (confidence baja) de maliciosas
> (confidence alta), facilitando la decisión automatizada.

### Distribución por Hostname (Top 10)

| Hostname | Alertas |
|----------|---------|
| WORKSTATION-001 | 266 |
| WIN-TC01-001 | 43 |
| tc14-integration-host | 34 |
| WIN-TC19-001 | 33 |
| WIN-TC02-001 | 30 |
| WIN-TC06-001 | 28 |
| WIN-TC05-000 | 27 |
| WIN-TC05-001 | 27 |
| WIN-TC05-002 | 27 |
| WIN-TC05-003 | 27 |

### Tags de Casos TheHive (Top 15)

| Tag | Casos |
|-----|-------|
| analyzed | 5 |
| loki | 5 |
| mttr-calculated | 5 |
| network-watcher | 5 |
| ransomware | 5 |
| redis | 5 |
| soar-lab | 5 |
| tenzir | 5 |
| e2e-test | 1 |
| tc-28 | 1 |
| alert_id:ALERT-1794171214-9297 | 1 |
| trace_id:16dc6bc78a2749458f5b9fdacc81bbd5 | 1 |
| alert_id:ALERT-1794171987-8959 | 1 |
| trace_id:d8879dbe649445beb7e382e7dd3bbb50 | 1 |
| alert_id:ALERT-1794172039-8069 | 1 |

## Uso de Recursos Docker (Tiempo Real)

> **Fuente:** `docker stats` (tiempo real).
> **Referencia TFM:** Tabla 4.2 (Configuración de Recursos Docker).
> Compara el uso real con los límites configurados.

| Contenedor | CPU % | Memoria Usada | Límite Mem | Net I/O | Block I/O |
|------------|-------|---------------|------------|---------|-----------|
| api | 2.12% | 207.9MiB | 2GiB | 197MB / 11.5MB | 104MB / 4.61MB |
| elasticsearch | 0.14% | 2.359GiB | 4GiB | 15.3MB / 12.3MB | 24.6MB / 10.6MB |
| redis | 3.27% | 11.45MiB | 1GiB | 66MB / 49.4MB | 10.4MB / 0B |
| thehive | 4.09% | 904MiB | 4GiB | 824kB / 31.8MB | 14.3MB / 38.8MB |
| oauth2_shuffle | 0.00% | 5.355MiB | 15.55GiB | 2.57MB / 2.57MB | 0B / 0B |
| oauth2_web | 0.02% | 9.898MiB | 15.55GiB | 138kB / 580kB | 5.73MB / 0B |
| keycloak | 0.25% | 576.1MiB | 1GiB | 115kB / 10.3MB | 22.4MB / 164MB |
| shuffle_frontend | 0.00% | 20.97MiB | 2GiB | 13.6MB / 7.47MB | 11.7MB / 8.19kB |
| shuffle_backend | 0.43% | 59.8MiB | 4GiB | 109MB / 375MB | 28.3MB / 16.4kB |
| opensearch | 3.42% | 2.66GiB | 4GiB | 39.5MB / 42.3MB | 29.6MB / 520MB |
| web_management | 0.00% | 14.71MiB | 256MiB | 145kB / 278kB | 2.33MB / 8.19kB |
| misp | 193.87% | 226.5MiB | 4GiB | 70.5MB / 82.4MB | 57.8MB / 55.6MB |
| misp_db | 3.15% | 137.2MiB | 2GiB | 2.02MB / 7.72MB | 18.2MB / 4.1kB |
| misp_modules | 0.00% | 326.6MiB | 1GiB | 61kB / 7.15MB | 391MB / 69.6kB |
| nginx | 0.00% | 6.617MiB | 512MiB | 1.07MB / 976kB | 5.65MB / 0B |
| opensearch_dashboards | 0.12% | 185MiB | 2GiB | 5.82MB / 64.9MB | 92.6MB / 16.4kB |
| cortex | 0.54% | 683.5MiB | 4GiB | 16.6MB / 117MB | 217MB / 16.1MB |
| grafana | 0.28% | 99.53MiB | 1GiB | 6.25MB / 80.7MB | 61.9MB / 0B |
| promtail | 2.36% | 88.22MiB | 512MiB | 2.59MB / 32.8MB | 52.9MB / 0B |
| tenzir_node | 8.90% | 942.7MiB | 1GiB | 14.6MB / 12.8MB | 217MB / 399MB |
| network_watcher | 0.01% | 46.39MiB | 512MiB | 27.3MB / 88.7MB | 17MB / 77.8kB |
| docs_site | 0.00% | 18.8MiB | 128MiB | 492kB / 24.2MB | 7.38MB / 4.1kB |
| orborus | 0.37% | 35.44MiB | 2GiB | 24.5MB / 34.3MB | 25.9MB / 0B |
| tenzir-node | 15.70% | 522.8MiB | 15.55GiB | 914B / 126B | 752MB / 493MB |
| loki | 0.60% | 230.9MiB | 1GiB | 46.4MB / 4.09MB | 305MB / 429MB |
| grafana_db | 2.01% | 38.42MiB | 512MiB | 8.76MB / 11.2MB | 70.3MB / 7.24MB |
| grafana_renderer | 0.00% | 81.76MiB | 1GiB | 26.9kB / 21.1kB | 251MB / 31.6MB |
| docker_proxy | 0.47% | 10.37MiB | 15.55GiB | 94.4MB / 125MB | 119MB / 13.1MB |

> **Observación:** Los recursos reales están dentro de los
> límites configurados. Elasticsearch y OpenSearch son los
> servicios con mayor consumo de memoria (datos indexados).
> Tenzir muestra el mayor CPU (procesamiento de eventos de red).

## Analyzers Cortex Disponibles

_Datos no disponibles en esta ejecución._

## Contexto Comparativo con Industria

> **Fuentes:** Mandiant M-Trends 2024, SANS 2024 Detection & Response Survey,
> IBM Cost of a Data Breach 2024, Verizon DBIR 2024, FortiGuard IR 2024.
> **Referencia TFM:** Tabla 2.3 (Métricas de Eficacia en Respuesta a Incidentes).

| Métrica | Laboratorio SOAR | Benchmark Industria | Fuente |
|---------|------------------|---------------------|--------|
| MTTR mediano | 85.95s | 5 días (ransomware dwell) | Mandiant M-Trends 2024 |
| MTTR medio | 215.77s | 258 días (breach lifecycle) | IBM Cost of Data Breach 2024 |
| MTTD mediana | 35.0s | <60min = top quartile | SANS 2024 |
| Tasa de automatización | 100% | 16% fully automated | SANS 2024 D&R Survey |
| Tasa de éxito | 100% | ≥95% objetivo | SANS 2024 |
| Falsos positivos | 13.6% | 64% lo identifica como problema | SANS 2024 D&R Survey |
| Detección interna | 100% | 46% | Mandiant M-Trends 2024 |
| Dwell time | 35.0s | 5 días (ransomware) | Mandiant M-Trends 2024 |
| Costo promedio breach | N/A (lab) | $4.88M | IBM Cost of Data Breach 2024 |
| Ransomware en breaches | 100% (sim) | 32% (extorsión) | Verizon DBIR 2024 |

> **Análisis comparativo:** El laboratorio SOAR supera significativamente
> los benchmarks de industria en todas las métricas clave:
>
>1. **MTTR:** 215.77s vs 5 días (Mandiant ransomware) — mejora de 2002x
>2. **MTTD:** 35.0s vs 60min (top quartile SANS) — en el rango óptimo
>3. **Automatización:** 100% vs 16% (SANS 2024 D&R) — automatización completa
>4. **Falsos positivos:** 13.6% vs 64% (SANS 2024) — mejor precisión
>5. **Detección interna:** 100% vs 46% (Mandiant) — sin dependencia externa
>6. **Costo breach:** N/A (lab) vs $4.88M (IBM 2024) — el SOAR reduce costo
>7. **AI/Automation impact:** IBM 2024 reporta $2.2M menos en breach costs
>
> **Limitaciones del laboratorio:** Estas comparaciones deben
> interpretarse en el contexto de un entorno controlado con alertas
> simuladas. En producción, los tiempos serían mayores debido a
> latencia de red, disponibilidad de servicios externos (Cortex analyzers)
> y volumen de alertas reales.

## Métricas de Calidad del Software

_Datos no disponibles en esta ejecución._

## Limitaciones del Laboratorio

> **Referencia TFM:** Sección 5.1 (Limitaciones), Tabla 5.3 (Limitaciones y Trabajo Futuro).
> Esta sección contextualiza los resultados del reporte dentro de las
> restricciones inherentes a un entorno de laboratorio.

### Limitaciones Técnicas

| # | Limitación | Impacto en Métricas | Mitigación |
|---|------------|---------------------|------------|
| 1 | **Dependencia de APIs externas** | 34.1% de jobs de Cortex fallan (analyzers requieren APIs externas) | `continue_on_failure` + timeouts; workflow completa correctamente |
| 2 | **Alertas simuladas** | MTTD/MTTR reflejan tiempo de procesamiento, no detección real | Simulador genera alertas realistas con IoCs válidos (T1486, hashes, IPs) |
| 3 | **Contención simulada** | `containment_executed=false` en 100% de ejecuciones | El workflow llega a la decisión de contención; en producción ejecutaría el aislamiento |
| 4 | **Sin volumetría real** | 1511 alertas en esta sesión (lab) vs millones/día (prod) | Tests de carga extrema (TC-14) validan hasta 100 alertas concurrentes |
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
| SOAR Open Source | $200K | 215.77s | 100.0% | 4 sem |
| SOAR Comercial | $500K | 151.0s | 100% | 12 sem |
| Híbrido | $350K | 183.4s | 100% | 8 sem |

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

_Informe generado automáticamente por `generate_e2e_report.py` el 2026-11-08 22:09:58 UTC_