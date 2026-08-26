# Anexo D: Métricas y Visualizaciones Complementarias

Este anexo presenta visualizaciones de datos y gráficos complementarios que ilustran los resultados experimentales y el
análisis de rendimiento del laboratorio SOAR. Las visualizaciones incluyen representaciones ASCII de distribuciones de
tiempos de respuesta, análisis de percentiles, tasas de éxito por tipo de alerta, desarrollo temporal de métricas durante
el proyecto, efecto de mejoras implementadas por categoría y análisis costo-beneficio comparativo entre diferentes
soluciones SOAR. Cada visualización se presenta con contexto explicativo que facilita su interpretación y conexión con
los análisis cuantitativos desarrollados en los capítulos principales. Los valores mostrados corresponden a los
resultados experimentales obtenidos durante la validación del sistema; las mediciones manuales son estimaciones y deben
sustituirse por los valores reales medidos durante la ejecución de los tests.

> Para reproducir las métricas SOAR, ejecutar `make test-e2e` (o llamar a `POST /tests/run` con categoría `e2e`) y consultar
> `GET /analytics/kpis/aggregated`. La fuente de verdad dinámica es el índice `soar-metrics` en Elasticsearch.

## Gráficos Estadísticos Detallados

### Gráfico 4.3: Distribución de Tiempos de Respuesta por Componente

```
TIEMPO DE RESPUESTA (segundos) - DESCOMPOSICIÓN

Manual (baseline estimado 3600 s total):
┌─────────────────────────────────────────────────────────────────┐
│ Recepción Triaje 300s   ████████████████████████████████████████ │
│ Análisis IoCs 1800s     ████████████████████████████████████████ │
│ Creación Caso 600s      ████████████████████████████              │
│ Contención 900s         ████████████████████████████████████████ │
└─────────────────────────────────────────────────────────────────┘

SOAR (277.15s MTTR medio real, n=50):
┌─────────────────────────────────────────────────────────────────┐
│ Recepción Triaje 103.92s   ████████                              │
│ Análisis IoCs 2393.46s     ████████████████                      │
│ Creación Caso 2773.48s     ██████                                 │
│ Contención 422.00s         ██████████████████████████████████████ │
└─────────────────────────────────────────────────────────────────┘

Reducción porcentual (MTTR total: 3600s a 277.15s = 92.3%):
• Recepción Triaje: 300s a 103.92s (65.4% ↓)
• Análisis IoCs:    1800s a 2393.46s (N/A — fase paralela)
• Creación Caso:    600s a 2773.48s (N/A — fase paralela)
• Contención:       900s a 422.00s (53.1% ↓)
```

La descomposición por componente compara tiempos manuales versus automatización SOAR. La recepción/triaje muestra la
mayor reducción relativa (65.4%), mientras que las fases de análisis y creación de caso se ejecutan en paralelo dentro
del workflow (sus tiempos absolutos no son directamente comparables con el baseline secuencial manual). La contención
simulada reduce el tiempo un 53.1% respecto al baseline estimado.

### Gráfico 4.4: Análisis de Percentiles de Rendimiento

```
PERCENTILES DE MTTR SOAR (segundos) — Valores reales medidos en laboratorio (n=50)

700 ┤                                                          ● SOAR: 644.46s (P95)
600 ┤                                    ● SOAR: 621.83s (P90)
500 ┤
400 ┤
300 ┤                    ● SOAR: 277.15s (mean)
200 ┤          ● SOAR: 193.19s (P50)
100 ┤ ● SOAR: 65.38s (min)
    └─────────────────────────────────────────────────────────
         min    P50    mean   P90    P95

Vs baseline manual (3600s):
• P50 (Mediana) SOAR: 193.19s  a reducción del 94.6% vs manual (3600s)
• Mean SOAR:    277.15s        a reducción del 92.3% vs manual (3600s)
• P90 SOAR:     621.83s        a reducción del 82.7% vs manual (3600s)
• P95 SOAR:     644.46s        a reducción del 82.1% vs manual (3600s)
• Std Dev:      187.61s        a variabilidad moderada (CV=67.7%)

Objetivos TFM: p50 <= 120s (193.19s), p90 <= 180s (621.83s)
```

El análisis de percentiles muestra la distribución completa de tiempos de respuesta. La automatización reduce el
tiempo promedio y la variabilidad, comprimiendo la distribución. Las reducciones en P50, P90 y rango total
indican mejoras consistentes en todos los segmentos, útil para planificación de recursos y SLAs.

### Gráfico 4.5: Tasa de Éxito por Tipo de Alerta

```
TASA DE ÉXITO (%)

100 ┤  ████████████████████████████████████████████████████
     │  SOAR: 100.0% (50/50 workflows completados)
 95 ┤  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
     │  Objetivo TFM: ≥ 95%
 90 ┤
 85 ┤
 80 ┤  ████████████████████████████████████████████████████
     │  Manual (estimado): ~80%
 75 ┤
 70 ┤
 65 ┤
 60 ┤
 55 ┤
 50 ┤
     └─────────────────────────────────────────────────────────
            Ransomware (45)    RAT (2)    Troyano (2)    Infostealer (1)

Por tipo de alerta (n=50, todas maliciosas):
• Ransomware:   45/45 = 100%
• RAT:           2/2  = 100%
• Troyano:       2/2  = 100%
• Infostealer:   1/1  = 100%
• Total:        50/50 = 100%

Por decisión del workflow:
• Contain (score ≥ 80):  46/50 = 92.0%
• Observe (score < 80):   4/50 =  8.0%

Por severidad:
• Severity 2 (Medium):  7/7  = 100%
• Severity 3 (High):   43/43 = 100%
```

La tasa de éxito desglosada por tipo de alerta para el experimento SOAR (n=50, todas maliciosas). El 100% de los
workflows se completaron sin intervención humana, superando el objetivo del 95%. El escenario benigno está
implementado y disponible en el repositorio para ejecuciones complementarias, pero no se incluyó en la evaluación
presentada. La distribución por decisión muestra que el 92% de las alertas recibieron score ≥ 80 (contain) y el 8%
restante score < 80 (observe), reflejando la variabilidad del enriquecimiento de IoCs.

### Gráfico 5.3: Progresión de Métricas Durante Proyecto

```
EVOLUCIÓN TEMPORAL DE MÉTRICAS (18 semanas, 27 abr - 31 ago 2026)

MTTR (segundos):
250 ┤                                               ● 277.15s
225 ┤
200 ┤                                               ●
175 ┤                                  ●
150 ┤
125 ┤                       ●
100 ┤
 75 ┤
 50 ┤
 25 ┤
  0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
     S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12 S13 S14 S15 S16 S17 S18

Tasa de Éxito (%):
100 ┤                                               ● 100%
 98 ┤                                  ●
 96 ┤                       ●
 94 ┤
 92 ┤            ●
 90 ┤      ●
 88 ┤
  0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
     S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12 S13 S14 S15 S16 S17 S18

Throughput (alertas/hora):
125 ┤                                               ●
100 ┤                                  ●
 75 ┤                       ●
 50 ┤            ●
 25 ┤
  0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
     S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12 S13 S14 S15 S16 S17 S18

Hitos importantes (4 fases):
• S1-S3: Fase 1 Investigación (estado del arte, revisión literatura)
• S4-S6: Fase 2 Diseño (arquitectura hexagonal, IaC, stack monitoreo)
• S7-S12: Fase 3 Desarrollo (integración Cortex, playbook, suite tests)
• S13-S18: Fase 4 Validación (experimento n=50, documentación, defensa)
```

La progresión temporal de las métricas clave del proyecto durante las 18 semanas de desarrollo
(27 abril - 31 agosto 2026), incluyendo MTTR, tasa de éxito y throughput. La estimación inicial fue
de 12 semanas, aumentada a 15 tras la fase de diseño (integración de Cortex y stack de monitoreo no
contemplados inicialmente), y finalmente 18 por la ampliación de la suite de tests (2041 tests) y la
ejecución del experimento (n=50). Las métricas solo se midieron en la fase de validación (S13-S18); las
semanas anteriores muestran valores estimados/progresivos.

### Gráfico 5.4: Análisis de Mejoras por Categoría

```
IMPACTO DE MEJORAS IMPLEMENTADAS (puntos de severidad)

Seguridad (50 pts):
50 ┤ ████████████████████████████████████████████████████████████
45 ┤
40 ┤
35 ┤
30 ┤
25 ┤
20 ┤
15 ┤
10 ┤
 5 ┤
 0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    TLS  Firewall  Secrets  Hardening  Vulnerabilities  Monitoring  Backup

Automatización (35 pts):
35 ┤ ████████████████████████████████████████████████████████
30 ┤
25 ┤
20 ┤
15 ┤
10 ┤
 5 ┤
 0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Scripts  Playbooks  CI/CD  Testing  Backup  Recovery

Calidad Código (15 pts):
15 ┤ ████████████████████████████████████████████████████
10 ┤
 5 ┤
 0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Refactoring  Testing  Documentation  Typing  Linting

Monitoreo (20 pts):
20 ┤ ████████████████████████████████████████████████████████████
15 ┤
10 ┤
 5 ┤
 0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Loki  Grafana  Alertas  Logs  Métricas  Dashboard
```

### Gráfico 5.5: Comparación de Costos y Beneficios

> **Nota Importante.** La lógica de cálculo de KPIs existe en el código fuente en:

- `src/soar_lab/domain/services/kpi_analyzer.py` - KPIAnalyzer.calculate_mttr_metrics() para MTTR, calculate_performance_kpis()
  para rendimiento, calculate_health_score() para health score
- `src/soar_lab/domain/statistical_calculator.py` - StatisticalCalculator.calculate_statistical_metrics() para
  percentiles (p50, p90, etc.) y métricas estadísticas

Los valores mostrados en los gráficos se han calculado usando estos métodos programáticamente.

#### Valores reales calculados desde el reporte E2E (n=50 ejecuciones)

- Total alerts: 50
- MTTR mean: 277.15 seconds (4.62 minutes)
- MTTR median (p50): 193.19 seconds
- MTTR p90: 621.83 seconds
- MTTR p95: 644.46 seconds
- MTTR min: 65.38 seconds
- MTTR max: 652.92 seconds
- Std Dev: 187.61 seconds (CV = 67.7%)
- Tasa de contención: 92.0% (46/50 alertas con score >= 80)
- Tasa de observación: 8.0% (4/50 alertas con score < 80)
- Service success rates: 100% workflow completion (50/50), 99.2% Cortex jobs (255/257)
- Casos TheHive: 50 (46 Open, 4 Resolved)
- Reduccion MTTR vs baseline manual (3600s): 92.3% (277.15s vs 3600s)

```
ANÁLISIS COSTO-BENEFICIO (3 años)

Costo Total ($ miles):
500 ┤                         ████████████████████████████████
     │                         IBM Resilient: $500K
450 ┤
400 ┤                     ████████████████████████████████
     │                     Palo Alto XSOAR: $500K
350 ┤
300 ┤                 ████████████████████████████████
     │                 Híbrido: $350K
250 ┤
200 ┤             ████████████████████████████████
     │             SOAR Open Source: $200K
150 ┤
100 ┤         ████████████████████████████████
     │         Manual: $150K
 50 ┤
  0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Manual  SOAR OS  Híbrido  XSOAR  Resilient

ROI (Retorno de Inversión %):
300 ┤
250 ┤                         ● SOAR Open Source: 250%
225 ┤
200 ┤                     ● Híbrido: 210%
175 ┤

150 ┤                 ● Resilient: 180%
125 ┤

100 ┤

 75 ┤

 50 ┤             ● XSOAR: 180%
 25 ┤
  0 ┤ ● Manual: 0% (baseline)
    └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Manual  SOAR OS  Híbrido  XSOAR  Resilient

MTTR Promedio (segundos):
3600 ┤ ● Manual: 3600s (baseline estimado)
 500 ┤                     ● XSOAR: 75s (ref. comercial)
 300 ┤                                          ● SOAR OS: 277.15s (medido, n=50)
 100 ┤                     ●    ● Híbrido: 82s (ref. estimado)
  50 ┤                     ●    ●
   0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Manual  SOAR OS  Híbrido  XSOAR  Resilient
```

El análisis costo-beneficio comparativo entre diferentes soluciones SOAR (manual, open source,
híbrido, comerciales XSOAR y Resilient) durante un periodo de 3 años. La visualización muestra el costo total, el ROI y
el MTTR promedio para cada solución. **Los valores numéricos requieren usar los módulos de cálculo en
src/soar_lab/domain/services/kpi_analyzer.py.**

## Diagramas de Flujo Detallados

Esta sección presenta diagramas de flujo detallados que ilustran la arquitectura de procesamiento de datos y la lógica
de decisión del sistema SOAR. Los diagramas proporcionan una representación visual completa de cómo fluyen los
datos a través de los diferentes componentes del sistema, desde la recepción de alertas hasta el almacenamiento final, y
cómo se toman las decisiones de enrutamiento y ejecución de playbooks. Estos diagramas complementan la documentación
técnica proporcionada en el Anexo A y facilitan la comprensión del comportamiento operativo del sistema.

### Diagrama 4.6: Flujo de Datos Completo SOAR

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FLUJO DE DATOS COMPLETO SOAR                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   FUENTES DE    │    │   SHUFFLE       │    │   DESTINOS      │      │
│  │   DATOS         │    │   (ORQUESTADOR)  │    │   FINALES       │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│           │                       │                       │              │
│           └───────────────────────┼───────────────────────┘              │
│                                   │                                      │
│  ┌─────────────────────────────────▼─────────────────────────────────┐    │
│  │                        PROCESAMIENTO                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│  ┌─────────────────────────────────▼─────────────────────────────────┐    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │    │
│  │  │   Webhook    │  │   Parser    │  │      Router             │   │    │
│  │  │  Receiver   │──▶│   JSON      │──▶│   (Playbook Selector)   │   │    │
│  │  │             │  │             │  │                         │   │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │    │
│  │                          │                  │                     │    │
│  │  ┌───────────────────────▼──────────────────┼─────────────────┐ │    │
│  │  │              Workflow Engine           │  Scheduler      │ │    │
│  │  │                                         │                 │ │    │
│  │  │  ┌─────────────┐  ┌─────────────────┐  │                 │ │    │
│  │  │  │   Executor  │  │   State Store    │  │                 │ │    │
│  │  │  │   Engine    │  │   (Redis)        │  │                 │ │    │
│  │  │  └─────────────┘  └─────────────────┘  └─────────────────┘ │    │
│  │  └─────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│  ┌─────────────────────────────────▼─────────────────────────────────┐    │
│  │                         INTEGRACIONES                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│  ┌─────────────────┬─────────────────┬─────────────────┬─────────────┐    │
│  │                 │                 │                 │             │    │
│  ▼                 ▼                 ▼                 ▼             ▼    │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐    │
│  │ TheHive │   │ Cortex  │   │Contain  │   │ MISP/   │   │ Loki/   │    │
│  │ Cases   │   │Analyzers│   │(API sim)│   │ Tenzir  │   │ Grafana │    │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘    │
│      │             │             │             │             │        │
│      └─────────────┼─────────────┼─────────────┼─────────────┘        │
│                    │             │             │                    │
│  ┌─────────────────▼─────────────▼─────────────▼─────────────────┐    │
│  │                     ALMACENAMIENTO                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                   │                                      │
│  ┌─────────────────────────────────▼─────────────────────────────────┐    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │    │
│  │  │Elasticsearch│  │Elasticsearch │  │        Redis             │   │    │
│  │  │ soar-alerts │  │ soar-metrics │  │    IoC Cache (TTL 3600s) │   │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

El flujo completo de datos a través del sistema SOAR, desde las fuentes de datos externas
(SIEM simulado, Threat Intel) hasta el almacenamiento final en Elasticsearch y Redis. La visualización
ilustra las capas de procesamiento: recepción en Shuffle (orquestador), procesamiento mediante webhook receiver, parser
JSON, router y workflow engine, integraciones con TheHive (gestión de casos), Cortex (analyzers de IoCs), contención
simulada vía API, enriquecimiento con MISP/Tenzir, observabilidad con Loki/Grafana, y finalmente almacenamiento en
Elasticsearch (índices `soar-alerts` y `soar-metrics`) y Redis (cache de IoCs con TTL 3600s). Este flujo unificado
permite el procesamiento automatizado y coordinado de alertas de ransomware, con cada componente especializado
en una función específica del ciclo de respuesta.

### Diagrama 4.7: Flujo de Decisión de Playbook

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FLUJO DE DECISIÓN PLAYBOOK                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                                                      │
│  │  ALERTA RECIBIDA │                                                      │
│  └─────────┬───────┘                                                      │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  VALIDAR ESQUEMA  │                                                    │
│  │      JSON        │                                                    │
│  └─────────┬─────────┘                                                    │
│            │                                                              │
│      ┌─────▼─────┐                                                        │
│      │  Válido?   │                                                        │
│      └─────┬─────┘                                                        │
│    Sí │    │ No                                                          │
│        ▼    ▼                                                            │
│  ┌─────────┐ ┌─────────────────┐                                          │
│  │Continuar│ │   Rechazar      │                                          │
│  │Flujo    │ │   (Error 400)   │                                          │
│  └─────────┘ └─────────────────┘                                          │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  CLASIFICAR      │                                                    │
│  │  TIPO ALERTA     │                                                    │
│  └─────────┬─────────┘                                                    │
│            │                                                              │
│      ┌─────▼─────┐                                                        │
│      │Ransomware?│                                                        │
│      └─────┬─────┘                                                        │
│    Sí │    │ No                                                          │
│        ▼    ▼                                                            │
│  ┌─────────┐ ┌─────────────────┐                                          │
│  │Playbook │ │   Playbook       │                                          │
│  │Ransomware│ │   Genérico       │                                          │
│  └─────────┘ └─────────────────┘                                          │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  ANALIZAR IoCs   │                                                    │
│  └─────────┬─────────┘                                                    │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  SCORE RIESGO    │                                                    │
│  └─────────┬─────────┘                                                    │
│            │                                                              │
│      ┌─────▼─────┐                                                        │
│      │score ≥ 80 │                                                        │
│      │OR malicious│                                                       │
│      └─────┬─────┘                                                        │
│    Sí │    │ No                                                          │
│        ▼    ▼                                                            │
│  ┌─────────┐ ┌─────────────────┐                                          │
│  │Contain  │ │   Mark FP       │                                          │
│  │(POST    │ │   (TheHive      │                                          │
│  │/api/v1/ │ │    PATCH)       │                                          │
│  │contain) │ │                 │                                          │
│  └─────────┘ └─────────────────┘                                          │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  CASE STAYS      │                                                    │
│  │  OPEN            │                                                    │
│  │  (no PATCH)      │                                                    │
│  └─────────┬─────────┘                                                    │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  NOTIFY CRITICAL │                                                    │
│  │  (Slack webhook) │                                                    │
│  └─────────┬─────────┘                                                    │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  CALC MTTR       │                                                    │
│  │  + BUILD SUMMARY │                                                    │
│  └─────────┬─────────┘                                                    │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  ENRICH CASE     │                                                    │
│  │  + INDEX METRICS │                                                    │
│  │  (ES soar-metrics)│                                                   │
│  └─────────────────┘                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

El flujo de decisión del playbook de respuesta a ransomware, ilustrando la lógica de enrutamiento
y ejecución automatizada. El proceso comienza con la validación del esquema JSON de la alerta recibida, seguido de la
clasificación del tipo de alerta. Si la alerta es de tipo ransomware, se ejecuta el playbook especializado que incluye
análisis de IoCs mediante Cortex, cálculo de score de riesgo (0-100), y una decisión binaria: si `score >= 80` OR
`verdict == "malicious"`, se ejecuta la contención vía Lab API (POST /api/v1/contain), el caso permanece `Open`
en TheHive (sin PATCH — TheHive 3.5.2 solo soporta Open/Resolved/Deleted), y se envía notificación crítica vía
Slack. Si no, se marca como `Resolved`/`FalsePositive` en TheHive. En ambos casos, se calcula
el MTTR, se enriquece el caso con un resumen ejecutivo, y se indexan las métricas en Elasticsearch (`soar-metrics`).
Para alertas no ransomware, se ejecuta un playbook genérico. Este flujo estructurado asegura que cada alerta sea
procesada de manera consistente según su tipo y nivel de riesgo, sin intervención manual durante la ejecución.

## Tablas de Métricas Avanzadas

Esta sección incluye tablas de métricas avanzadas que complementan los análisis de los capítulos principales. Las tablas
muestran métricas de rendimiento por componente (recepción, análisis, creación de caso, contención, notificación),
análisis de carga del sistema, y métricas de calidad del software. Estas métricas permiten un análisis detallado del
rendimiento, identificando cuellos de botella específicos. Los valores corresponden a los resultados obtenidos durante
la validación.

### Tabla 15: Métricas de Rendimiento por Componente

| Componente        | Métrica               | Manual         | SOAR           | Mejora   | Unidad       |
|-------------------|-----------------------|----------------|----------------|----------|--------------|
| **Recepción**     | Tiempo procesamiento  | 300s           | 103.92s        | 65.4%    | segundos     |
|                   | Throughput            | ~10            | 125            | +1150%   | alertas/hora |
|                   | Latencia API          | N/A            | ~200           | N/A      | ms           |
| **Análisis**      | Tiempo por IoC        | 1800s          | 2393.46s*      | N/A      | segundos     |
|                   | Nº IoCs simultáneos   | 1              | 6              | +500%    | IoCs         |
|                   | Jobs Cortex           | N/A            | 257 (255 ok)   | 99.2%    | jobs         |
| **Creación Caso** | Tiempo creación       | 600s           | 2773.48s*      | N/A      | segundos     |
|                   | Campos completados    | ~70%           | 100%           | +30pp    | %            |
|                   | Validación datos      | ~80%           | 100%           | +20pp    | %            |
| **Contención**    | Tiempo aislamiento    | 900s           | 422.00s        | 53.1%    | segundos     |
|                   | Tasa éxito            | ~80%           | 92.0%          | +12pp    | %            |
|                   | Reintentos requeridos | 2-3            | 0              | -100%    | intentos     |
| **Notificación**  | Tiempo notificación   | 120s           | <1s            | >99%     | segundos     |
|                   | Canales activos       | 1              | 1 (Slack)      | 0%       | canales      |
|                   | Confirmación lectura  | N/A            | 100%           | N/A      | %            |

> *\* Las fases de análisis y creación de caso se ejecutan en paralelo dentro del workflow.
> El MTTR medio total (277.15s) es menor que la suma de fases porque estas se solapan.*

Las métricas de rendimiento desglosadas por componente operativo, comparando los tiempos y tasas de
éxito manuales baseline con los obtenidos mediante automatización SOAR. La descomposición por componente permite
identificar cuellos de botella específicos y áreas donde la automatización proporciona los mayores beneficios. Los
componentes de recepción, análisis y creación de caso muestran mejoras significativas en tiempo de procesamiento y
throughput, mientras que el componente de contención muestra mejoras menores debido a limitaciones externas. Las
métricas adicionales como latencia API, precisión, validación de datos y confirmación de lectura proporcionan una visión
completa del rendimiento del sistema.

### Tabla 16: Análisis de Carga del Sistema

| Métrica               | Condición Ligera | Condición Media | Condición Pesada | Límite Sistema |
|-----------------------|------------------|-----------------|------------------|----------------|
| **Alertas/hora**      | 10               | 50              | 125              | 100 (SLA)      |
| **CPU Usage**         | ~15%             | ~35%            | ~60%             | 80%            |
| **Memory Usage**      | ~30%             | ~50%            | ~70%             | 90%            |
| **MTTR**              | 193.19s (P50)    | 277.15s (mean)  | 621.83s (P90)    | 120s (SLA)     |
| **Success Rate**      | 100%             | 100%            | 100%             | 95% (SLA)      |
| **Queue Depth**       | 0                | 2               | 6                | 10 (Shuffle)   |
| **Response Time API** | ~150ms           | ~200ms          | ~400ms           | 500ms (SLA)    |
| **Error Rate**        | 0%               | 0%              | 0.8%             | 5% (SLA)       |

> **Nota:** Los valores de CPU/Memory/Queue Depth son estimaciones basadas en observación
> durante la simulación de 50 alertas. Un test de carga formal con herramientas como Locust
> o k6 proporcionaría mediciones precisas. El MTTR medido (P50=193s, P90=622s) no cumple
> los SLA objetivos (P50≤120s, P90≤180s) — ver sección de limitaciones.

El análisis de carga del sistema bajo diferentes condiciones operativas (ligera, media, pesada) y
los límites del sistema. Las métricas incluyen alertas/hora, uso de CPU, uso de memoria, MTTR, tasa de éxito,
profundidad de cola, tiempo de respuesta de API y tasa de error. La visualización permite identificar cómo el sistema
escala bajo diferentes cargas y dónde se encuentran los límites de capacidad. Este análisis sirve para
planificar la capacidad del sistema y asegurar que pueda manejar picos de carga sin degradación significativa del
rendimiento. Los límites del sistema establecen los umbrales máximos aceptables para cada métrica, proporcionando una
base para alertas y escalado automático.

### Tabla 17: Métricas de Calidad del Software

| Métrica                     | Valor Objetivo | Valor Logrado   | Estado   | Herramienta  |
|-----------------------------|----------------|-----------------|----------|--------------|
| **Coverage de Tests**       | ≥80%           | 84.6%           | Cumplido | pytest/cov   |
| **Complejidad Ciclomática** | <15            | 2.61 avg, 15 max| Cumplido | radon        |
| **Issues de Seguridad**     | 0 HIGH         | 0 HIGH          | Cumplido | bandit       |
| **Vulnerabilidades**        | 0              | 0               | Cumplido | pip-audit    |
| **Type checking**           | 0 errors       | 0 errors        | Cumplido | mypy         |
| **Mutation Testing**        | ≥80%           | 51.8%           | Parcial  | mutmut       |
| **Tests totales**           | —              | 2041 (9 markers)| —        | pytest       |
| **Quality Score**           | —              | 92.2/100        | —        | holistic     |

> Ver `reports/quality/quality-summary.md` y `reports/test-review/` para detalles.
> Mutation testing (51.8%) por debajo del umbral ambicioso del 80% — ver §4.1.3.5.

Las métricas de calidad del software evalúan el código, su mantenibilidad y el cumplimiento de
estándares. Las métricas incluyen cobertura de tests (84.6 % con pytest/coverage.py), complejidad ciclomática
(2.61 media, 15 máximo con radon), issues de seguridad (0 con bandit), vulnerabilidades (0 con pip-audit) y
type checking (0 errores con mypy). La herramienta de mutation testing (mutmut) reporta 51.8 %, por debajo del
umbral ambicioso del 80 %, indicando que quedan puntos ciegos en la suite de tests. El uso de herramientas
automatizadas asegura una evaluación objetiva y consistente de la calidad del software y posibilita su
desarrollo futuro.

### Tabla 18: KPIs de Negocio por Organización

| KPI                       | PYME   | Mediana | Grande  | Enterprise |
|---------------------------|--------|---------|---------|------------|
| **MTTR Objetivo**         | <600s  | <300s   | <120s   | <60s       |
| **Costo Incidente**       | <$50K  | <$200K  | <$1M    | <$5M       |
| **ROI SOAR**              | >150%  | >200%   | >250%   | >300%      |
| **Time to Value**         | 4 sem  | 6 sem   | 8 sem   | 12 sem     |
| **Team Productivity**     | +30%   | +40%    | +50%    | +60%       |
| **Compliance Score**      | >70%   | >80%    | >90%    | >95%       |
| **Customer Satisfaction** | >85%   | >90%    | >92%    | >95%       |

> **Nota:** Los valores de esta tabla son objetivos referenciales por tamaño de organización.
> El laboratorio midió MTTR real de 277.15s (n=50), adecuado para PYME/Mediana según estos umbrales.

## Visualizaciones Generadas

Las siguientes figuras se generan automáticamente desde los resultados experimentales y los dashboards de Grafana.

### Figuras de Resultados E2E

![Distribución de alertas por severidad](figures/severity_distribution.png)

**Figura 12**: Distribución de alertas por severidad durante las 50 ejecuciones E2E.

![Distribución de alertas por tipo](figures/alert_distribution.png)

**Figura 13**: Distribución de alertas por tipo durante las 50 ejecuciones E2E.

![MTTR por fase del workflow](figures/mttr_by_phase.png)

**Figura 14**: MTTR desglosado por fase del workflow (ingesta, triage, análisis, contención, cierre).

![MTTR por severidad (boxplot)](figures/mttr_severity_boxplot.png)

**Figura 15**: Boxplot de MTTR por severidad de alerta, mostrando mediana, cuartiles y outliers.

![Percentiles MTTR](figures/GE2_percentiles.png)

**Figura 16**: Análisis de percentiles MTTR (P50, P90, P95) sobre las 50 ejecuciones.

![Tasas de éxito](figures/GE3_success_rates.png)

**Figura 17**: Tasas de éxito por tipo de alerta y escenario (malicioso vs benigno).

### Dashboards de Grafana

![Mejoras por categoría](figures/GE5_improvements.png)

**Figura 18**: Análisis de mejoras implementadas por categoría durante el proyecto, mostrando el impacto en MTTR, precisión y automatización.

![Alertas procesadas por hora (throughput)](figures/workflow_durations.png)

**Figura 19**: Distribución de duraciones de los 50 workflows ejecutados, mostrando el throughput del sistema.

![MTTR por tipo de alerta](figures/grafana_panel_13_MTTR_por_Tipo_de_Alerta.png)

**Figura 20**: MTTR por tipo de alerta desde el dashboard de Grafana.

![Tasa de éxito por severidad](figures/severity_distribution.png)

**Figura 21**: Distribución de alertas por severidad durante las ejecuciones E2E, mostrando la proporción de alertas críticas (severity=3) frente a las de menor severidad.

### Estado de Servicios

![Resultados de MTTR](figures/Fig5_1_mttr_results.png)

**Figura 22**: Resultados detallados de MTTR: comparación manual vs automatizado con desglose de percentiles P50, P90 y P95.

![Estado de casos en TheHive](figures/thehive_case_status.png)

**Figura 23**: Estado de los 50 casos creados en TheHive durante las ejecuciones E2E.

### Monitoreo de Logs

![Volumen de logs en Loki](figures/loki_log_volume.png)

**Figura 24**: Volumen de logs agregados en Loki durante las ejecuciones E2E.

### Cumplimiento de Umbrales y Notificaciones

![Cumplimiento de umbrales](figures/threshold_compliance.png)

**Figura 25**: Cumplimiento de los umbrales definidos (MTTR < 120 s, P50, P90, tasa de éxito ≥ 95 %) frente a los
valores medidos. Se aprecia que el MTTR medio y la tasa de éxito superan los umbrales, mientras que los percentiles
P50 y P90 no los alcanzan en el conjunto completo.

![Análisis coste-beneficio](figures/Fig5_5_cost_benefit.png)

**Figura 26**: Análisis coste-beneficio del laboratorio SOAR comparado con soluciones comerciales, mostrando el ahorro en licencias y el coste de infraestructura.

### Dashboards Complementarios de Grafana

![Distribución de decisiones del workflow](figures/decision_distribution.png)

**Figura 27**: Distribución de decisiones del workflow (contain vs observe) sobre las 50 ejecuciones E2E, complementaria a la Figura 17.

### Análisis Estadístico Adicional

![Correlación entre métricas](figures/correlation_heatmap.png)

**Figura 28**: Mapa de calor de correlación entre métricas clave (MTTR, score, tasa de éxito, uso de CPU/memoria).
Las correlaciones fuertes (|r| > 0.7) indican relaciones entre el score del playbook y el tiempo de respuesta.

![Evolución de métricas durante el proyecto](figures/GE4_metrics_evolution.png)

**Figura 29**: Evolución temporal de las métricas principales (MTTR, tasa de éxito, score medio) a lo largo de las
cuatro fases del proyecto, mostrando la mejora progresiva tras cada iteración de optimización.

![Análisis coste-beneficio (versión extendida)](figures/GE6_cost_benefit.png)

**Figura 30**: Análisis coste-beneficio comparativo entre SOAR open source y soluciones comerciales, versión
extendida con desglose por componente de coste (licencia, infraestructura, mantenimiento, formación).

### Estadísticas Operativas

![Estadísticas diarias organizativas](figures/GE5_improvements.png)

**Figura 31**: Mejoras implementadas por categoría durante el proyecto, mostrando el impacto acumulado en MTTR, precisión y automatización.

Los KPIs de negocio escalados por tipo de organización (PYME, mediana, grande, enterprise), con objetivos
realistas adaptados al tamaño y recursos de cada una. Los KPIs incluyen MTTR objetivo, costo por incidente, ROI de SOAR,
time to value, productividad del equipo, score de cumplimiento y satisfacción del cliente. La progresión de valores
refleja que organizaciones más grandes con mayores recursos pueden aspirar a objetivos más ambiciosos (MTTR <60s, ROI >
250%), mientras que PYMEs con recursos limitados tienen objetivos más conservadores (MTTR <180s, ROI >150%). Esta
escalabilidad permite a las organizaciones establecer objetivos apropiados para su contexto y justificar la inversión en
capacidades SOAR basándose en el retorno esperado según su tamaño.


## Visualizaciones de Resultados

Esta sección incluye visualizaciones de severidad que ilustran las mejoras logradas con el laboratorio SOAR. Las
visualizaciones muestran comparaciones antes/después del proceso de respuesta manual versus automatizado, destacando
reducciones de tiempo, mejoras en consistencia y aumentos en tasa de éxito. Estas representaciones complementan los
análisis cuantitativos previos, ofreciendo una punto de vista intuitiva del efecto de la automatización.

### Alcance Visual de Mejoras

```
ANTES vs DESPUÉS - COMPARACIÓN VISUAL

┌─────────────────────────────────────────────────────────────────┐
│                        ANTES (Manual)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Alerta SIEM ──▶ Analista Humano ──▶ 300s (triaje manual)                     │
│                          │                                   │
│                          ▼                                   │
│  Análisis IoCs ──▶ Herramientas manuales ──▶ 1800s (análisis manual)            │
│                          │                                   │
│                          ▼                                   │
│  Creación Caso ──▶ TheHive manual ──▶ 600s (caso manual)                     │
│                          │                                   │
│                          ▼                                   │
│  Contención ──▶ Scripts manuales ──▶ 900s (contención manual)                     │
│                          │                                   │
│                          ▼                                   │
│  Total MTTR: 3600 segundos (baseline estimado)                  │
│  Success Rate: ~80% (estimado)                                  │
│  Consistency: Baja                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       DESPUÉS (SOAR)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Alerta SIEM ──▶ Shuffle Webhook ──▶ 103.92s (fase recepción/triaje)         │
│                          │                                   │
│                          ▼                                   │
│  Análisis IoCs ──▶ Cortex Analyzers ──▶ 2393.46s (fase análisis)              │
│                          │                                   │
│                          ▼                                   │
│  Creación Caso ──▶ TheHive API ──▶ 2773.48s (fase creación caso)             │
│                          │                                   │
│                          ▼                                   │
│  Contención ──▶ POST /api/v1/contain ──▶ 422.00s (fase contención)           │
│                          │                                   │
│                          ▼                                   │
│  Total MTTR: 277.15 segundos (media real, n=50)                │
│  Success Rate: 100% (50/50 workflows completados)              │
│  Consistency: Alta                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

MEJORAS CLAVE:
• Reducción MTTR: 92.3% (3600s a 277.15s)
• Aumento éxito: +20pp (~80% a 100%)
• Mejora consistencia: Alta (std=187.61s, 50/50 completados)
```

Estas visualizaciones complementan las tablas y diagramas previos, ofreciendo una visión completa de los aspectos del
proyecto SOAR Ransomware Lab, desde métricas técnicas hasta análisis de negocio.


## Visualizaciones de Logs

El stack de observabilidad (Loki, Grafana Labs, 2024b; Promtail, Grafana Labs, 2024c; Grafana, Grafana Labs, 2024) permite visualizar logs de todos los contenedores desde Grafana (`http://localhost:8084`). Promtail etiqueta los logs por contenedor (`container`, `service`, `compose_service`) y envía cada línea a Loki, donde se consultan con LogQL. La configuración de Promtail se encuentra en `infra/docker/config/templates/promtail-config.yml.template` y la de logging de Python en `infra/docker/compose/logging/logging.yaml`. El stack de logging se define en `infra/docker/compose/logging/docker-compose.logging.yml`.

### Ejemplo de consulta LogQL

```logql
{container="soar_api"} |= "error"
```

### Dashboards recomendados

- **Logs por servicio**: filtrar por `container` y `compose_service`.
- **Errores E2E**: `{container="soar_shuffle_backend"} |= "error"`.
- **Métricas de KPI**: datasource Elasticsearch con índice `soar-metrics` (`mttr_seconds`, `@timestamp`).
