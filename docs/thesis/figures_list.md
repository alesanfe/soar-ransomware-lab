# Índice de Figuras

> Las páginas indicadas son orientativas y se confirmarán en el PDF final.
> Las figuras siguen enumeración independiente por capítulo: Figura [Capítulo].[Número].

## Figuras del Capítulo 1: Introducción

| Figura     | Título                                            | Archivo |
|------------|---------------------------------------------------|---------|
| Figura 1.1 | Comparación MTTR Manual vs Automatizado           | `figures/Fig1_3_mttr_comparison.png` |

## Figuras del Capítulo 3: Objetivos y Metodología

| Figura     | Título                                             | Archivo |
|------------|----------------------------------------------------|---------|
| Figura 3.1 | Cronograma Gantt del Proyecto                      | Mermaid (inline) |

## Figuras del Capítulo 4: Desarrollo Específico

| Figura     | Título                                             | Archivo |
|------------|----------------------------------------------------|---------|
| Figura 4.1 | Arquitectura General del Laboratorio SOAR          | Anexo J (J.2) |
| Figura 4.2 | Diagrama de Despliegue Docker Compose              | Anexo J (J.3) |
| Figura 4.5 | Estado de Jobs de Cortex                           | `figures/cortex_job_status.png` |
| Figura 4.6 | Resultados de MTTR (manual vs automatizado)        | `figures/Fig5_1_mttr_results.png` |
| Figura 4.7 | Tiempos por Componente del Workflow                | `figures/GE1_component_timings.png` |
| Figura 4.8 | Análisis de Percentiles MTTR (Grafana)             | `figures/grafana_panel_5_Grafico_4_4___Analisis_de_Percentiles_MTTR__distri.png` |
| Figura 4.9 | Distribución de Decisiones del Playbook            | `figures/decision_distribution.png` |
| Figura 4.10 | Distribución de Mejoras por Categoría             | `figures/Fig5_2_improvements_category.png` |

## Figuras del Capítulo 5: Conclusiones y Trabajo Futuro

| Figura     | Título                                             | Archivo |
|------------|----------------------------------------------------|---------|
| Figura 5.1 | Análisis Coste-Beneficio SOAR Open Source vs Comercial | `figures/Fig5_5_cost_benefit.png` |

## Figuras del Anexo E: Métricas y Visualizaciones Complementarias

| Figura     | Título                                             | Archivo |
|------------|----------------------------------------------------|---------|
| Figura E.1 | Distribución de Alertas por Severidad              | `figures/severity_distribution.png` |
| Figura E.2 | Distribución de Alertas por Tipo                   | `figures/alert_distribution.png` |
| Figura E.3 | MTTR por Fase del Workflow                         | `figures/mttr_by_phase.png` |
| Figura E.4 | MTTR por Severidad (boxplot)                       | `figures/mttr_severity_boxplot.png` |
| Figura E.5 | Percentiles MTTR                                   | `figures/GE2_percentiles.png` |
| Figura E.6 | Tasas de Éxito por Tipo de Alerta                  | `figures/GE3_success_rates.png` |
| Figura E.7 | Evolución de MTTR (tendencia diaria, Grafana)      | `figures/grafana_panel_10_Grafico_5_3___Evolucion_MTTR__tendencia_diaria_.png` |
| Figura E.8 | Alertas Procesadas por Hora (Grafana)              | `figures/grafana_panel_12_Grafico_5_4___Alertas_procesadas_por_hora__through.png` |
| Figura E.9 | MTTR por Tipo de Alerta (Grafana)                  | `figures/grafana_panel_13_MTTR_por_Tipo_de_Alerta.png` |
| Figura E.10 | Tasa de Éxito por Severidad (Grafana)             | `figures/grafana_panel_14_Tasa_de__xito_por_Severidad.png` |
| Figura E.11 | Salud de Servicios                                | `figures/service_health.png` |
| Figura E.12 | Estado de Casos en TheHive                         | `figures/thehive_case_status.png` |
| Figura E.13 | Duración de Workflows                              | `figures/workflow_durations.png` |
| Figura E.14 | Volumen de Logs en Loki                            | `figures/loki_log_volume.png` |
| Figura E.15 | Mapa de Calor de Logs                              | `figures/loki_log_heatmap.png` |

## Figuras del Anexo J (Diagramas Mermaid)

| Figura     | Título                                        |
|------------|-----------------------------------------------|
| Figura J.1 | Arquitectura de Alto Nivel (flowchart LR)     |
| Figura J.2 | Arquitectura de Despliegue Docker (graph TD)  |
| Figura J.3 | Arquitectura Hexagonal (flowchart TD)         |
| Figura J.4 | Diagrama de Contexto C4 (C4Context)           |
| Figura J.5 | Flujo E2E de Alertas (sequenceDiagram)        |
| Figura J.6 | Árbol de Decisión del Playbook (flowchart)    |
| Figura J.7 | Flujo de Integración API (sequenceDiagram)    |
| Figura J.8 | Respuesta Automatizada (sequenceDiagram)      |
| Figura J.9 | Cronograma Objetivos SMART (gantt)            |
| Figura J.10| Roadmap por Semanas (gantt)                   |
| Figura J.11| Matriz de Priorización de Riesgos (graph)     |
| Figura J.12| GMinst4ll: Flujo de Infección (graph TD)      |
| Figura J.13| Pipeline SOAR para IoCs GMinst4ll (graph LR)  |

---

**Notas sobre las Figuras:**

1. **Formato de Imágenes**: Todas las figuras están en formato PNG o SVG con resolución mínima de 300 DPI para
   impresión.

2. **Convenciones de Nomenclatura**: Figura [Capítulo].[Número]. Los anexos usan la letra del anexo como prefijo
   (Figura E.1, Figura J.1, etc.).

3. **Colores en Diagramas**: Se utiliza una paleta consistente:
   - Azul: Componentes de datos
   - Verde: Componentes de aplicación
   - Naranja: Componentes de integración
   - Rojo: Componentes de seguridad

4. **Actualización**: Las figuras han sido actualizadas con los datos experimentales obtenidos durante la validación
   del sistema en agosto de 2026.

5. **Total**: 39 figuras (11 en capítulos + 15 en Anexo E + 13 en Anexo J).
