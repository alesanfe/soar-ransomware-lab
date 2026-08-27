# Índice de Figuras

> Las páginas indicadas son orientativas y se confirmarán en el PDF final.
> Las figuras siguen enumeración propia y secuencial (Figura 1, 2, 3...) conforme aparecen en el documento,
> independientemente del capítulo o Anexo donde se encuentren (formato APA 7ª edición).

## Figuras del Capítulo 1: Introducción

| Figura  | Título                                            | Archivo |
|---------|---------------------------------------------------|---------|
| Figura 1 | Comparación MTTR Manual vs Automatizado          | `figures/Fig5_1_mttr_results.png` |

## Figuras del Capítulo 3: Objetivos y Metodología

| Figura  | Título                                            | Archivo |
|---------|---------------------------------------------------|---------|
| Figura 2 | Cronograma Gantt del Proyecto                    | Mermaid (inline) |

## Figuras del Capítulo 4: Desarrollo Específico

| Figura  | Título                                            | Archivo |
|---------|---------------------------------------------------|---------|
| Figura 3 | Arquitectura General del Laboratorio SOAR        | Anexo F (F.2) |
| Figura 4 | Diagrama de Despliegue Docker Compose            | Anexo F (F.3) |
| Figura 5 | Estado de Jobs de Cortex                         | `figures/cortex_job_status.png` |
| Figura 6 | Resultados de MTTR (manual vs automatizado)      | `figures/Fig5_1_mttr_results.png` |
| Figura 7a | Tiempos por Componente del Workflow              | `figures/mttr_by_phase.png` |
| Figura 7b | Tasas de Éxito por Tipo de Alerta                | `figures/GE3_success_rates.png` |
| Figura 8a | Análisis de Percentiles MTTR                     | `figures/GE2_percentiles.png` |
| Figura 8b | Cumplimiento de Umbrales                         | `figures/threshold_compliance.png` |
| Figura 9 | Distribución de Decisiones del Playbook          | `figures/decision_distribution.png` |
| Figura 10 | Distribución de Mejoras por Categoría           | `figures/Fig5_2_improvements_category.png` |

## Figuras del Capítulo 5: Conclusiones y Trabajo Futuro

| Figura  | Título                                            | Archivo |
|---------|---------------------------------------------------|---------|
| Figura 11 | Análisis Coste-Beneficio SOAR Open Source vs Comercial | `figures/Fig5_5_cost_benefit.png` |

## Figuras del Anexo C: Métricas y Visualizaciones Complementarias

| Figura  | Título                                            | Archivo |
|---------|---------------------------------------------------|---------|
| Figura 12 | Distribución de Alertas por Severidad            | `figures/severity_distribution.png` |
| Figura 13 | Distribución de Alertas por Tipo                 | `figures/alert_distribution.png` |
| Figura 14 | MTTR por Fase del Workflow                       | `figures/mttr_by_phase.png` |
| Figura 15 | MTTR por Severidad (boxplot)                     | `figures/mttr_severity_boxplot.png` |
| Figura 16 | Percentiles MTTR                                 | `figures/GE2_percentiles.png` |
| Figura 17 | Tasas de Éxito por Tipo de Alerta                | `figures/GE3_success_rates.png` |
| Figura 18 | Mejoras por Categoría                            | `figures/GE5_improvements.png` |
| Figura 19 | Distribución de Duraciones de Workflows          | `figures/workflow_durations.png` |
| Figura 20 | MTTR por Tipo de Alerta (Grafana)                | `figures/grafana_panel_13_MTTR_por_Tipo_de_Alerta.png` |
| Figura 21 | Resultados de MTTR (manual vs automatizado)      | `figures/Fig5_1_mttr_results.png` |
| Figura 22 | Estado de Casos en TheHive                       | `figures/thehive_case_status.png` |
| Figura 23 | Volumen de Logs en Loki                          | `figures/loki_log_volume.png` |
| Figura 24 | Cumplimiento de Umbrales                         | `figures/threshold_compliance.png` |
| Figura 25 | Análisis Coste-Beneficio                         | `figures/Fig5_5_cost_benefit.png` |
| Figura 26 | Distribución de Decisiones del Workflow          | `figures/decision_distribution.png` |
| Figura 27 | Correlación entre Métricas                       | `figures/correlation_heatmap.png` |
| Figura 28 | Evolución de Métricas durante el Proyecto        | `figures/GE4_metrics_evolution.png` |
| Figura 29 | Análisis Coste-Beneficio (versión extendida)     | `figures/GE6_cost_benefit.png` |

## Figuras del Anexo F (Diagramas Mermaid)

| Figura  | Título                                            |
|---------|---------------------------------------------------|
| Figura 30 | Arquitectura de Alto Nivel (flowchart LR)       |
| Figura 31 | Arquitectura de Despliegue Docker (graph TD)    |
| Figura 32 | Arquitectura Hexagonal (flowchart TD)           |
| Figura 33 | Diagrama de Contexto C4 (C4Context)             |
| Figura 34 | Flujo E2E de Alertas (sequenceDiagram)          |
| Figura 35 | Árbol de Decisión del Playbook (flowchart)      |
| Figura 36 | Respuesta Automatizada (sequenceDiagram)        |
| Figura 37 | Cronograma Objetivos SMART (gantt)              |
| Figura 38 | Roadmap por Semanas (gantt)                     |
| Figura 39 | Matriz de Priorización de Riesgos (graph)       |
| Figura 40 | GMinst4ll: Flujo de Infección (graph TD)        |
| Figura 41 | Pipeline SOAR para IoCs GMinst4ll (graph LR)    |

---

**Notas sobre las Figuras:**

1. **Formato de Imágenes**: Todas las figuras están en formato PNG o SVG con resolución mínima de 300 DPI para
   impresión.

2. **Enumeración APA**: Las figuras se numeran secuencialmente (Figura 1, 2, 3...) en orden de aparición en el
   documento, independientemente del capítulo o anexo.

3. **Colores en Diagramas**: Se utiliza una paleta consistente:
   - Azul: Componentes de datos
   - Verde: Componentes de aplicación
   - Naranja: Componentes de integración
   - Rojo: Componentes de seguridad

4. **Actualización**: Las figuras han sido actualizadas con los datos experimentales obtenidos durante la validación
   del sistema en agosto de 2026.

5. **Total**: 41 figuras (11 en capítulos + 18 en Anexo C + 12 en Anexo F).
