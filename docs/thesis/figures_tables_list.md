# Lista de Figuras y Tablas

> Las páginas indicadas son orientativas y se confirmarán en el PDF final.

## Lista de Figuras

### Figuras del Capítulo 1: Introducción

| Figura     | Título                                            | Archivo |
|------------|---------------------------------------------------|---------|
| Figura 1.1 | Comparación MTTR Manual vs Automatizado           | `figures/Fig1_3_mttr_comparison.png` |

### Figuras del Capítulo 4: Desarrollo Específico

| Figura     | Título                                             | Archivo |
|------------|----------------------------------------------------|---------|
| Figura 4.1 | Arquitectura General del Laboratorio SOAR          | Anexo J (J.2) |
| Figura 4.2 | Diagrama de Despliegue Docker Compose              | Anexo J (J.3) |
| Figura 4.5 | Estado de Jobs de Cortex                           | `figures/cortex_job_status.png` |

### Figuras del Capítulo 3: Objetivos y Metodología

| Figura     | Título                                             | Archivo |
|------------|----------------------------------------------------|---------|
| Figura 3.1 | Cronograma Gantt del Proyecto                      | Mermaid (inline) |

### Figuras del Capítulo 5: Resultados, Discusión y Conclusiones

| Figura     | Título                                             | Archivo |
|------------|----------------------------------------------------|---------|
| Figura 5.1 | Resultados de MTTR (manual vs automatizado)        | `figures/Fig5_1_mttr_results.png` |
| Figura 5.2 | Tiempos por Componente del Workflow                | `figures/GE1_component_timings.png` |
| Figura 5.3 | Análisis de Percentiles MTTR (Grafana)             | `figures/grafana_panel_5_Grafico_4_4___Analisis_de_Percentiles_MTTR__distri.png` |
| Figura 5.4 | Distribución de Decisiones del Playbook            | `figures/decision_distribution.png` |
| Figura 5.5 | Distribución de Mejoras por Categoría              | `figures/Fig5_2_improvements_category.png` |
| Figura 5.6 | Análisis Coste-Beneficio SOAR Open Source vs Comercial | `figures/Fig5_5_cost_benefit.png` |

### Figuras del Anexo: Visualizaciones Complementarias

| Figura     | Título                                             | Archivo |
|------------|----------------------------------------------------|---------|
| Figura A.1 | Distribución de Alertas por Severidad              | `figures/severity_distribution.png` |
| Figura A.2 | Distribución de Alertas por Tipo                   | `figures/alert_distribution.png` |
| Figura A.3 | MTTR por Fase del Workflow                         | `figures/mttr_by_phase.png` |
| Figura A.4 | MTTR por Severidad (boxplot)                       | `figures/mttr_severity_boxplot.png` |
| Figura A.5 | Percentiles MTTR                                   | `figures/GE2_percentiles.png` |
| Figura A.6 | Tasas de Éxito por Tipo de Alerta                  | `figures/GE3_success_rates.png` |
| Figura A.7 | Evolución de MTTR (tendencia diaria, Grafana)      | `figures/grafana_panel_10_Grafico_5_3___Evolucion_MTTR__tendencia_diaria_.png` |
| Figura A.8 | Alertas Procesadas por Hora (Grafana)              | `figures/grafana_panel_12_Grafico_5_4___Alertas_procesadas_por_hora__through.png` |
| Figura A.9 | MTTR por Tipo de Alerta (Grafana)                  | `figures/grafana_panel_13_MTTR_por_Tipo_de_Alerta.png` |
| Figura A.10 | Tasa de Éxito por Severidad (Grafana)             | `figures/grafana_panel_14_Tasa_de__xito_por_Severidad.png` |
| Figura A.11 | Salud de Servicios                                | `figures/service_health.png` |
| Figura A.12 | Estado de Casos en TheHive                         | `figures/thehive_case_status.png` |
| Figura A.13 | Duración de Workflows                              | `figures/workflow_durations.png` |
| Figura A.14 | Volumen de Logs en Loki                            | `figures/loki_log_volume.png` |
| Figura A.15 | Mapa de Calor de Logs                              | `figures/loki_log_heatmap.png` |

### Figuras del Anexo J (Diagramas Mermaid)

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

## Lista de Tablas

### Tablas del Capítulo 1: Introducción

| Tabla     | Título                                               | Página |
|-----------|------------------------------------------------------|--------|
| Tabla 1.1 | Estadísticas de Incidentes de Ransomware (2020-2024) | 6      |
| Tabla 1.2 | Impacto Económico del Ransomware por Sector          | 7      |
| Tabla 1.3 | Limitaciones de Respuesta Manual vs Automatizada     | 8      |

### Tablas del Capítulo 2: Estado del Arte

| Tabla     | Título                                         | Página |
|-----------|------------------------------------------------|--------|
| Tabla 2.1 | Características de Generaciones de Ransomware  | 14     |
| Tabla 2.2 | Comparativa de Plataformas SOAR Open Source    | 21     |
| Tabla 2.3 | Métricas de Eficacia en Respuesta a Incidentes | 24     |
| Tabla 2.4 | Modelos de Madurez y KPIs Asociados            | 26     |
| Tabla 2.5 | Frameworks de Evaluación de Seguridad          | 28     |

### Tablas del Capítulo 3: Objetivos y Metodología

| Tabla     | Título                                     | Página |
|-----------|--------------------------------------------|--------|
| Tabla 3.1 | Objetivos Específicos y Criterios de Éxito | 31     |
| Tabla 3.2 | Tecnologías Utilizadas y Justificación     | 33     |
| Tabla 3.3 | Diseño Experimental: Variables y Control   | 35     |
| Tabla 3.4 | Plan de Gestión de Riesgos                 | 37     |
| Tabla 3.5 | Cronograma Detallado del Proyecto          | 39     |

### Tablas del Capítulo 4: Desarrollo Específico

| Tabla      | Título                                  | Página |
|------------|-----------------------------------------|--------|
| Tabla 4.1  | Requisitos Funcionales del Sistema SOAR | 44     |
| Tabla 4.2  | Requisitos No Funcionales y Métricas    | 46     |
| Tabla 4.3  | Matriz de Trazabilidad de Requisitos    | 48     |
| Tabla 4.4  | Configuración de Servicios Docker       | 50     |
| Tabla 4.5  | Scripts de Automatización Desarrollados | 53     |
| Tabla 4.6  | Analyzers Cortex Configurados           | 55     |
| Tabla 4.7  | Métricas de Monitoreo Implementadas     | 57     |
| Tabla 4.8  | Resultados Experimentales Detallados    | 59     |
| Tabla 4.9  | Análisis Comparativo de Rendimiento     | 61     |
| Tabla 4.10 | Mejoras Implementadas por Categoría     | 63     |
| Tabla 4.11 | Métricas de Rendimiento por Componente  | 65     |
| Tabla 4.12 | Análisis de Carga del Sistema           | 67     |
| Tabla 4.13 | Métricas de Calidad del Software        | 69     |

### Tablas del Capítulo 5: Conclusiones

| Tabla     | Título                                      | Página |
|-----------|---------------------------------------------|--------|
| Tabla 5.1 | Cumplimiento de Objetivos del Proyecto      | 72     |
| Tabla 5.2 | Contribuciones Académicas y Prácticas       | 74     |
| Tabla 5.3 | Análisis Costo-Beneficio de Soluciones SOAR | 76     |
| Tabla 5.4 | Recomendaciones por Tipo de Organización    | 78     |
| Tabla 5.5 | KPIs Recomendados para SOAR                 | 80     |

### Tablas del Anexo A

| Tabla     | Título                                    | Página |
|-----------|-------------------------------------------|--------|
| Tabla A.1 | Variables de Entorno Docker Compose       | 84     |
| Tabla A.2 | Configuración de Recursos por Contenedor  | 86     |
| Tabla A.3 | Comandos Make del Proyecto                | 88     |
| Tabla A.4 | Esquema de Base de Datos TheHive          | 90     |
| Tabla A.5 | Reglas de Alertamiento Prometheus         | 92     |
| Tabla A.6 | Guía de Instalación por Sistema Operativo | 94     |

## Índices Especiales

### Índice de Diagramas de Flujo

| Diagrama | Título                                      | Capítulo | Página |
|----------|---------------------------------------------|----------|--------|
| DF 1     | Flujo de Respuesta Automatizada Ransomware  | 4        | 52     |
| DF 2     | Proceso de Validación Experimental          | 3        | 38     |
| DF 3     | Flujo de Integración TheHive-Cortex-Shuffle | 4        | 54     |
| DF 4     | Flujo de Datos Completo SOAR                | 4        | 60     |
| DF 5     | Flujo de Decisión de Playbook               | 4        | 62     |
| DF 6     | Proceso de Backup y Recuperación            | A        | 93     |

### Índice de Gráficos Estadísticos

| Gráfico | Título                                              | Capítulo | Página |
|---------|-----------------------------------------------------|----------|--------|
| GE 1    | Distribución de Tiempos de Respuesta por Componente | 4        | 60     |
| GE 2    | Análisis de Percentiles de Rendimiento              | 4        | 61     |
| GE 3    | Tasa de Éxito por Tipo de Alerta                    | 4        | 62     |
| GE 4    | Evolución de Métricas Durante Proyecto              | 5        | 65     |
| GE 5    | Análisis de Mejoras por Categoría                   | 5        | 67     |
| GE 6    | Comparación de Costos y Beneficios                  | 5        | 69     |

### Índice de Capturas de Pantalla

| Captura | Título                         | Capítulo | Página |
|---------|--------------------------------|----------|--------|
| CP 1    | Interfaz Principal TheHive     | 4        | 89     |
| CP 2    | Dashboard Shuffle con Playbook | 4        | 90     |
| CP 3    | Grafana Dashboard de Monitoreo | 4        | 91     |
| CP 4    | Consola de Logs Centralizada   | A        | 85     |

### Índice de Diagramas de Arquitectura

| Arquitectura | Título                         | Capítulo | Página |
|--------------|--------------------------------|----------|--------|
| AR 1         | Arquitectura General SOAR      | 1        | 7      |
| AR 2         | Arquitectura Docker Detallada  | 3        | 40     |
| AR 3         | Arquitectura de Red Segmentada | 4        | 45     |
| AR 4         | Arquitectura de Monitoreo      | 4        | 56     |
| AR 5         | Arquitectura de Backup         | A        | 93     |

---

**Notas sobre las Figuras y Tablas:**

1. **Formato de Imágenes**: Todas las figuras están en formato PNG o SVG con resolución mínima de 300 DPI para
   impresión.

2. **Fuentes de Datos**: Las tablas con datos estadísticos incluyen fuentes y fechas de actualización.

3. **Convenciones de Nomenclatura**:
    - Figuras: Figura [Capítulo].[Número]
    - Tablas: Tabla [Capítulo].[Número]
    - Ecuaciones: Ecuación [Capítulo].[Número]

4. **Colores en Diagramas**: Se utiliza una paleta consistente:
    - Azul: Componentes de datos
    - Verde: Componentes de aplicación
    - Naranja: Componentes de integración
    - Rojo: Componentes de seguridad

5. **Actualización**: Las figuras y tablas han sido actualizadas con los datos experimentales obtenidos durante la
   validación del sistema en agosto de 2026.
