# Reportes experimentales — Índice

Esta carpeta contiene los reportes generados automáticamente por el laboratorio SOAR
tras la ejecución experimental (n=50 alertas). Estos reportes respaldan los datos
presentados en la tesis.

## Reporte principal

| Archivo | Descripción |
|---------|-------------|
| `e2e_report.md` | Reporte E2E completo: salud de servicios, MTTR, workflows, Cortex, TheHive, MITRE, decisiones, benchmarks |
| `e2e_report.json` | Datos estructurados del reporte E2E (para procesamiento programático) |

## Reportes de calidad

| Archivo | Descripción |
|---------|-------------|
| `quality_summary.md` | Resumen de calidad: complejidad, seguridad (bandit), mantenibilidad, dependencias |
| `quality_summary.json` | Datos estructurados del reporte de calidad |
| `test_review_report.md` | Revisión de tests en 7 dimensiones |
| `test_review_summary.json` | Datos estructurados de la revisión de tests |
| `holistic_review_report.md` | Holistic Project Radar (5 capas, 15 dimensiones) |
| `holistic_review_summary.json` | Datos estructurados del holistic review |
| `mutation_report.md` | Mutation testing con mutmut |
| `mutation_summary.json` | Datos estructurados del mutation testing |

## Figures

Los gráficos (PNG) están en `docs/thesis/figures/` (34 archivos). Incluyen:

- MTTR: percentiles, evolución, por fase, por severidad, comparación manual vs SOAR
- Workflows: duraciones, notificaciones, tasa de éxito
- Cortex: jobs por estado, analyzers
- TheHive: casos por estado
- Alertas: distribución por tipo/severidad
- Servicios: salud
- Loki: volumen de logs, heatmap
- Cumplimiento de objetivos TFM
- Grafana: paneles exportados (MTTR, throughput, éxito por tipo/severidad)

## Datos clave (n=50)

| Métrica | Valor |
|---------|-------|
| Workflows completados | 50/50 (100%) |
| MTTR medio | 277.15s |
| MTTR P50 | 193.19s |
| MTTR P90 | 621.83s |
| MTTR P95 | 644.46s |
| Reducción MTTR vs manual | 92.3% (3600s → 277.15s) |
| Tasa de contención | 92.0% (46/50, score >= 80) |
| Tasa de falsos negativos | 8.0% (4/50, score < 80) |
| Score promedio | 96.2/100 (min=55, max=100) |
| Jobs Cortex | 255/257 (99.2% éxito) |
| Casos TheHive | 50/50 (100%) |
| Servicios healthy | 10/10 |
| Técnicas MITRE detectadas | 32 |
| Tasa de automatización | 100% |

## Objetivos TFM

| Objetivo | Umbral | Valor | Cumple |
|----------|--------|-------|--------|
| MTTR P50 | ≤ 120s | 193.19s | ❌ |
| MTTR P90 | ≤ 180s | 621.83s | ❌ |
| Tasa de éxito | ≥ 95% | 100% | ✅ |
| Dataset | ≥ 50 | 50 | ✅ |
| Reducción MTTR | ≥ 50% | 92.3% | ✅ |
| Disponibilidad | ≥ 99.5% | 99.7% | ✅ |
| Throughput | ≥ 100/h | 125/h | ✅ |

**Cumplimiento: 5/7 objetivos**
