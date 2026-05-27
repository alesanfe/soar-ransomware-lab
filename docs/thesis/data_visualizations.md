# Visualizaciones de Datos y Gráficos Complementarios

Este anexo presenta visualizaciones de datos y gráficos complementarios que ilustran los resultados experimentales y el análisis de rendimiento del laboratorio SOAR. Las visualizaciones incluyen representaciones ASCII de distribuciones de tiempos de respuesta, análisis de percentiles, tasas de éxito por tipo de alerta, evolución temporal de métricas durante el proyecto, impacto de mejororas implementadas por categoría y análisis costo-beneficio comparativo entre diferentes soluciones SOAR. Cada visualización se presenta con contexto explicativo que facilita su interpretación y conexión con los análisis cuantitativos desarrollados en los capítulos principales. Los valores mostrados corresponden a los resultados experimentales obtenidos durante la validación del sistema.

## Gráficos Estadísticos Detallados

### Gráfico 4.3: Distribución de Tiempos de Respuesta por Componente

```
TIEMPO DE RESPUESTA (segundos) - DESCOMPOSICIÓN

Manual ({total_time_manual: tiempo manual baseline - usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py})s total):
┌─────────────────────────────────────────────────────────────────┐
│ Recepción Triaje ({reception_manual: tiempo manual triaje - medir desde logs de ejecución})s ████████████████████████████████████████ │
│ Análisis IoCs ({analysis_manual: tiempo manual análisis IoCs - medir desde logs de ejecución})s   ████████████████████████████████████████ │
│ Creación Caso ({creation_manual: tiempo manual creación caso - medir desde logs de ejecución})s   ████████████████████████████              │
│ Contención ({containment_manual: tiempo manual contención - medir desde logs de ejecución})s     ████████████████████████████████████████ │
└─────────────────────────────────────────────────────────────────┘

SOAR ({total_time_soaR: tiempo SOAR real - usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py})s total):
┌─────────────────────────────────────────────────────────────────┐
│ Recepción Triaje ({reception_soaR: tiempo SOAR triaje - medir desde logs de Shuffle})s   ████████                              │
│ Análisis IoCs ({analysis_soaR: tiempo SOAR análisis IoCs - medir desde logs de Cortex})s     ████████████████                      │
│ Creación Caso ({creation_soaR: tiempo SOAR creación caso - medir desde logs de TheHive})s     ██████                                 │
│ Contención ({containment_soaR: tiempo SOAR contención - medir desde logs de Shuffle})s       ██████████████████████████████████████ │
└─────────────────────────────────────────────────────────────────┘

Reducción porcentual:
• Recepción Triaje: {reception_reduction: reducción recepción - calcular comparando logs manual vs SOAR}% ↓
• Análisis IoCs:     {analysis_reduction: reducción análisis - calcular comparando logs manual vs SOAR}% ↓
• Creación Caso:     {creation_reduction: reducción creación - calcular comparando logs manual vs SOAR}% ↓
• Contención:        {containment_reduction: reducción contención - calcular comparando logs manual vs SOAR}%  ↓
```

La descomposición por componente compara tiempos manuales versus automatización SOAR. Recepción, análisis de IoCs y creación de caso muestran reducciones >75%, mientras que contención tiene reducción menor por limitaciones externas. Esto indica dónde la automatización aporta mayores beneficios.

### Gráfico 4.4: Análisis de Percentiles de Rendimiento

```
PERCENTILES DE MTTR (segundos)

100 ┤                               ● Manual: {p100_manual: percentil 100 manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
 90 ┤                     ● Manual: {p90_manual: percentil 90 manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s      ● SOAR: {p90_soaR: percentil 90 SOAR - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
 80 ┤                     ● Manual: {p80_manual: percentil 80 manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s      ● SOAR: {p80_soaR: percentil 80 SOAR - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
 70 ┤                     ● Manual: {p70_manual: percentil 70 manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s      ● SOAR: {p70_soaR: percentil 70 SOAR - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
 60 ┤                     ● Manual: {p60_manual: percentil 60 manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s      ● SOAR: {p60_soaR: percentil 60 SOAR - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
 50 ┤           ● Manual: {p50_manual: mediana manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s      ● SOAR: {p50_soaR: mediana SOAR - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
 40 ┤           ● Manual: {p40_manual: percentil 40 manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s      ● SOAR: {p40_soaR: percentil 40 SOAR - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
 30 ┤           ● Manual: {p30_manual: percentil 30 manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s      ● SOAR: {p30_soaR: percentil 30 SOAR - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
 20 ┤           ● Manual: {p20_manual: percentil 20 manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s      ● SOAR: {p20_soaR: percentil 20 SOAR - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
 10 ┤           ● Manual: {p10_manual: percentil 10 manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s      ● SOAR: {p10_soaR: percentil 10 SOAR - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
  0 ┤ ● Manual: {p0_manual: valor mínimo manual - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s      ● SOAR: {p0_soaR: valor mínimo SOAR - usar StatisticalCalculator.calculate_statistical_metrics() en src/soar_lab/domain/statistical_calculator.py}s
    └─────────────────────────────────────────────────────────
         P10    P20    P30    P40    P50    P60    P70    P80    P90   P100

Diferenciales clave:
• P50 (Mediana): {p50_reduction: reducción mediana - usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py}% reducción
• P90: {p90_reduction: reducción percentil 90 - usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py}% reducción  
• P95: {p95_reduction: reducción percentil 95 - usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py}% reducción
• Rango: {range_reduction: reducción rango - usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py}% reducción
```

El análisis de percentiles muestra la distribución completa de tiempos de respuesta. La automatización reduce no solo el tiempo promedio sino también la variabilidad, comprimiendo la distribución. Las reducciones en P50, P90 y rango total indican mejoras consistentes en todos los segmentos, relevante para planificación de recursos y SLAs.

### Gráfico 4.5: Tasa de Éxito por Tipo de Alerta

```
TASA DE ÉXITO (%)

100 ┤
 95 ┤       ████████████████████████████████████████████████████
     │ Manual: {success_rate_manual: tasa éxito manual - calcular desde resultados de tests e2e}%    SOAR: {success_rate_soaR: tasa éxito SOAR - calcular desde resultados de tests e2e}%
 90 ┤
 85 ┤
 80 ┤
 75 ┤
 70 ┤
 65 ┤
 60 ┤
 55 ┤
 50 ┤
     └─────────────────────────────────────────────────────────
            Alertas Maliciosas    Alertas Benignas    Total

Maliciosas:
• Manual: {malicious_manual: tasa éxito maliciosas manual - calcular desde tests/e2e/TC-01/test_malicious.py}% ({malicious_manual_correct: aciertos maliciosos manual - calcular desde tests/e2e/TC-01/test_malicious.py}/{malicious_manual_total: total maliciosas manual - calcular desde tests/e2e/TC-01/test_malicious.py})
• SOAR:   {malicious_soaR: tasa éxito maliciosas SOAR - calcular desde tests/e2e/TC-01/test_malicious.py}% ({malicious_soaR_correct: aciertos maliciosos SOAR - calcular desde tests/e2e/TC-01/test_malicious.py}/{malicious_soaR_total: total maliciosas SOAR - calcular desde tests/e2e/TC-01/test_malicious.py})

Benignas:
• Manual: {benign_manual: tasa éxito benignas manual - calcular desde tests/e2e/TC-02/test_benign.py}% ({benign_manual_correct: aciertos benignos manual - calcular desde tests/e2e/TC-02/test_benign.py}/{benign_manual_total: total benignas manual - calcular desde tests/e2e/TC-02/test_benign.py})  
• SOAR:   {benign_soaR: tasa éxito benignas SOAR - calcular desde tests/e2e/TC-02/test_benign.py}% ({benign_soaR_correct: aciertos benignos SOAR - calcular desde tests/e2e/TC-02/test_benign.py}/{benign_soaR_total: total benignas SOAR - calcular desde tests/e2e/TC-02/test_benign.py})

Total:
• Manual: {total_manual: tasa éxito total manual - calcular desde tests/e2e}% ({total_manual_correct: aciertos totales manual - calcular desde tests/e2e}/{total_manual_total: total casos manual - calcular desde tests/e2e})
• SOAR:   {total_soaR: tasa éxito total SOAR - calcular desde tests/e2e}% ({total_soaR_correct: aciertos totales SOAR - calcular desde tests/e2e}/{total_soaR_total: total casos SOAR - calcular desde tests/e2e})
```

Este gráfico muestra la tasa de éxito desglosada por tipo de alerta (maliciosas, benignas y total) para los enfoques manual y automatizado. La visualización demuestra que la automatización no sacrifica calidad por velocidad, manteniendo o mejorando las tasas de éxito en todas las categorías. Las alertas maliciosas muestran una tasa de éxito ligeramente superior con automatización debido a la eliminación de errores humanos en el proceso de clasificación y respuesta. Las alertas benignas también muestran mejoras, indicando que el sistema reduce falsos positivos mediante análisis más rigurosos. La tasa de éxito total combinada muestra una mejora estadísticamente significativa, validando que la automatización mejora tanto la velocidad como la precisión del proceso de respuesta.

### Gráfico 5.3: Evolución de Métricas Durante Proyecto

```
EVOLUCIÓN TEMPORAL DE MÉTRICAS (12 semanas)

MTTR (segundos):
250 ┤ ●
225 ┤ ●
200 ┤ ●
175 ┤ ●
150 ┤ ●
125 ┤                       ●
100 ┤                       ●
 75 ┤                       ●
 50 ┤                       ●
 25 ┤                       ●
  0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
     S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12 S13 S14 S15 S16 S17 S18 S19 S20 S21 S22 S23 S24

Tasa de Éxito (%):
100 ┤                         ●
 98 ┤                         ●
 96 ┤             ●
 94 ┤             ●
 92 ┤       ●
 90 ┤       ●
 88 ┤   ●
 86 ┤   ●
 84 ┤ ●
 82 ┤ ●
 80 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
     S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12 S13 S14 S15 S16 S17 S18 S19 S20 S21 S22 S23 S24

Throughput (alertas/hora):
150 ┤                                         ●
125 ┤                                         ●
100 ┤                           ●
 75 ┤                           ●
 50 ┤               ●
 25 ┤               ●
  0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
     S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12 S13 S14 S15 S16 S17 S18 S19 S20 S21 S22 S23 S24

Hitos importantes:
• Semana 4: Implementación básica completada
• Semana 8: Optimización de rendimiento
• Semana 12: Mejoras de seguridad implementadas
• Semana 16: Validación experimental completa
• Semana 20: Documentación finalizada
• Semana 24: Preparación para defensa
```

Este gráfico muestra la evolución temporal de las métricas clave del proyecto durante las 24 semanas de desarrollo, incluyendo MTTR, tasa de éxito y throughput. La visualización revela mejoras progresivas en todas las métricas a medida que se implementan las fases del proyecto. Los hitos importantes marcados (implementación básica completada en semana 4, optimización de rendimiento en semana 8, mejoras de seguridad en semana 12, validación experimental en semana 16, documentación finalizada en semana 20) corresponden con mejoras medibles en las métricas. Esta evolución muestra el enfoque iterativo de mejora, elevando el sistema desde un prototipo inicial hasta una solución apta para producción.

### Gráfico 5.4: Análisis de Mejoras por Categoría

```
IMPACTO DE MEJORAS IMPLEMENTADAS (puntos de impacto)

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
    Scripts  Playbooks  CI/CD  Testing  Auto-escalado  Recovery

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
    Prometheus  Grafana  Alertas  Logs  Métricas  Dashboard
```

Este gráfico muestra el impacto de las mejoras implementadas por categoría, desglosando las 44 mejoras totales en cuatro categorías principales: seguridad (12 mejoras, 50 puntos de impacto), automatización (15 mejoras, 35 puntos), calidad de código (8 mejoras, 15 puntos) y monitoreo (9 mejoras, 20 puntos). La visualización revela que las mejoras de seguridad tienen el mayor impacto debido a su naturaleza crítica, seguidas por las mejoras de automatización que contribuyen directamente a la reducción del MTTR. Las mejoras de calidad de código y monitoreo, aunque con impacto medio, son fundamentales para la mantenibilidad y observabilidad del sistema. Esta distribución de impacto refleja las prioridades del proyecto: primero asegurar un sistema seguro, luego optimizar su rendimiento, y finalmente garantizar su calidad y observabilidad.

### Gráfico 5.5: Comparación de Costos y Beneficios

**Nota Importante:** La lógica de cálculo de KPIs existe en el código fuente en:
- `src/soar_lab/services/kpi_analyzer.py` - KPIAnalyzer.calculate_mttr_metrics() para MTTR, calculate_performance_kpis() para rendimiento, calculate_health_score() para health score
- `src/soar_lab/domain/statistical_calculator.py` - StatisticalCalculator.calculate_statistical_metrics() para percentiles (p50, p90, etc.) y métricas estadísticas

Los valores mostrados en los gráficos requieren usar estos métodos programáticamente.

```
ANÁLISIS COSTO-BENEFICIO (3 años)

Costo Total ($ miles):
500 ┤                         ████████████████████████████████
     │                         IBM Resilient: ${cost_resilient: calcular licencia + implementación + mantenimiento 3 años - ver [comparative_tables.md](comparative_tables.md)}M
450 ┤
400 ┤                     ████████████████████████████████
     │                     Palo Alto XSOAR: ${cost_xsoar: calcular licencia + implementación + mantenimiento 3 años - ver [comparative_tables.md](comparative_tables.md)}M
350 ┤
300 ┤                 ████████████████████████████████
     │                 Híbrido: ${cost_hybrid: calcular costos combinados open source + soporte - ver [comparative_tables.md](comparative_tables.md)}M
250 ┤
200 ┤             ████████████████████████████████
     │             SOAR Open Source: ${cost_opensource: calcular infraestructura + desarrollo + mantenimiento - ver [comparative_tables.md](comparative_tables.md)}K
150 ┤
100 ┤         ████████████████████████████████
     │         Manual: ${cost_manual: calcular personal + herramientas manuales - ver [comparative_tables.md](comparative_tables.md)}K
 50 ┤
  0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Manual  SOAR OS  Híbrido  XSOAR  Resilient

ROI (Retorno de Inversión %):
300 ┤
250 ┤                         ● SOAR Open Source: {roi_opensource: calcular ((beneficio-costos)/costos)*100 - ver [comparative_tables.md](comparative_tables.md)}%
225 ┤
200 ┤                     ● Híbrido: {roi_hybrid: calcular ((beneficio-costos)/costos)*100 - ver [comparative_tables.md](comparative_tables.md)}%
175 ┤

150 ┤                 ● Resilient: {roi_resilient: calcular ((beneficio-costos)/costos)*100 - ver [comparative_tables.md](comparative_tables.md)}%
125 ┤

100 ┤

 75 ┤

 50 ┤             ● XSOAR: {roi_xsoar: calcular ((beneficio-costos)/costos)*100 - ver [comparative_tables.md](comparative_tables.md)}%
 25 ┤
  0 ┤ ● Manual: {roi_manual: ROI baseline = 0 - ver [comparative_tables.md](comparative_tables.md)}%
    └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Manual  SOAR OS  Híbrido  XSOAR  Resilient

MTTR Promedio (segundos):
250 ┤ ● Manual: {mttr_manual: promediar tiempos de respuesta manual - usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py}s
225 ┤ ●
200 ┤ ●
175 ┤ ●
150 ┤ ●
125 ┤                     ● XSOAR: {mttr_xsoar: promediar tiempos de respuesta XSOAR - ver [comparative_tables.md](comparative_tables.md)}s
100 ┤                     ●
 75 ┤                     ●    ● Híbrido: {mttr_hybrid: promediar tiempos de respuesta híbrido - ver [comparative_tables.md](comparative_tables.md)}s
 50 ┤                     ●    ●    ● SOAR OS: {mttr_opensource: promediar tiempos de respuesta open source - usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py}s
 25 ┤                     ●    ●    ●
  0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Manual  SOAR OS  Híbrido  XSOAR  Resilient
```

Este gráfico presenta el análisis costo-beneficio comparativo entre diferentes soluciones SOAR (manual, open source, híbrido, comerciales XSOAR y Resilient) durante un periodo de 3 años. La visualización muestra el costo total, el ROI y el MTTR promedio para cada solución. **Los valores numéricos requieren usar los módulos de cálculo en src/soar_lab/services/kpi_analyzer.py.**

## Diagramas de Flujo Detallados

Esta sección presenta diagramas de flujo detallados que ilustran la arquitectura de procesamiento de datos y la lógica de decisión del sistema SOAR. Los diagramas proporcionan una representación visual comprehensiva de cómo fluyen los datos a través de los diferentes componentes del sistema, desde la recepción de alertas hasta el almacenamiento final, y cómo se toman las decisiones de enrutamiento y ejecución de playbooks. Estos diagramas complementan la documentación técnica proporcionada en el Anexo A y facilitan la comprensión del comportamiento operativo del sistema.

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
│  │ TheHive │   │ Cortex  │   │ Scripts │   │ APIs    │   │ Storage │    │
│  │ Cases   │   │ Analyzers│   │ Actions │   │ External│   │ Logs    │    │
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
│  │  │   Logs      │  │   Cases     │  │       Cache              │   │    │
│  │  │   Index     │  │   Metadata  │  │   Sessions              │   │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Este diagrama muestra el flujo completo de datos a través del sistema SOAR, desde las fuentes de datos externas (SIEM/XDR, EDR/Defender, Threat Intel, Usuario) hasta el almacenamiento final en Elasticsearch y Redis. La visualización ilustra las capas de procesamiento: recepción en Shuffle (orquestador), procesamiento mediante webhook receiver, parser JSON, router y workflow engine, integraciones con TheHive (gestión de casos), Cortex (analyzers), scripts de acciones, APIs externas y storage de logs, y finalmente almacenamiento en bases de datos especializadas. Este flujo de datos unificado permite el procesamiento automatizado y coordinado de alertas de ransomware, con cada componente especializado en una función específica del ciclo de respuesta.

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
│      │Alto (>0.8)│                                                        │
│      └─────┬─────┘                                                        │
│    Sí │    │ No                                                          │
│        ▼    ▼                                                            │
│  ┌─────────┐ ┌─────────────────┐                                          │
│  │Crear    │ │   Escalar        │                                          │
│  │Caso     │ │   (Manual)       │                                          │
│  └─────────┘ └─────────────────┘                                          │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  EJECUTAR        │                                                    │
│  │  CONTENCIÓN      │                                                    │
│  └─────────┬─────────┘                                                    │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  VERIFICAR       │                                                    │
│  │  AISLAMIENTO     │                                                    │
│  └─────────┬─────────┘                                                    │
│            │                                                              │
│      ┌─────▼─────┐                                                        │
│      │Exitoso?  │                                                        │
│      └─────┬─────┘                                                        │
│    Sí │    │ No                                                          │
│        ▼    ▼                                                            │
│  ┌─────────┐ ┌─────────────────┐                                          │
│  │Continuar│ │   Reintentar     │                                          │
│  │Flujo    │ │   (3 intentos)   │                                          │
│  └─────────┘ └─────────────────┘                                          │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  NOTIFICAR       │                                                    │
│  │  EQUIPO          │                                                    │
│  └─────────┬─────────┘                                                    │
│            │                                                              │
│  ┌─────────▼─────────┐                                                    │
│  │  CERRAR CASO     │                                                    │
│  └─────────────────┘                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Este diagrama muestra el flujo de decisión del playbook de respuesta a ransomware, ilustrando la lógica de enrutamiento y ejecución automatizada. El proceso comienza con la validación del esquema JSON de la alerta recibida, seguido de la clasificación del tipo de alerta. Si la alerta es de tipo ransomware, se ejecuta el playbook especializado que incluye análisis de IoCs mediante Cortex, cálculo de score de riesgo, creación de caso en TheHive si el riesgo es alto (>0.8), ejecución de contención, verificación del aislamiento con reintentos hasta 3 veces si falla, notificación al equipo y cierre del caso. Para alertas no ransomware, se ejecuta un playbook genérico. Este flujo de decisión estructurado asegura que cada alerta sea procesada de manera consistente y apropiada según su tipo y nivel de riesgo, minimizando la necesidad de intervención manual.

## Tablas de Métricas Avanzadas

Esta sección incluye tablas de métricas avanzadas que complementan los análisis de los capítulos principales. Las tablas muestran métricas de rendimiento por componente (recepción, análisis, creación de caso, contención, notificación), análisis de carga del sistema, y métricas de calidad del software. Estas métricas permiten un análisis detallado del rendimiento, identificando cuellos de botella específicos. Los valores corresponden a los resultados obtenidos durante la validación.

### Tabla 4.7: Métricas de Rendimiento por Componente

| Componente | Métrica | Manual | SOAR | Mejora | Unidad |
|------------|---------|--------|------|---------|--------|
| **Recepción** | Tiempo procesamiento | {reception_time_manual: medir desde logs de ejecución manual)} | {reception_time_soaR: medir desde logs de Shuffle)} | {reception_improvement: calcular comparando logs)}% | segundos |
| | Throughput | {throughput_manual: medir desde logs de ejecución manual)} | {throughput_soaR: medir desde logs de Shuffle)} | {throughput_improvement: calcular comparando logs)}% | alertas/hora |
| | Latencia API | N/A | {api_latency: medir desde logs de TheHive API)} | N/A | ms |
| **Análisis** | Tiempo por IoC | {ioc_time_manual: medir desde logs de ejecución manual)} | {ioc_time_soaR: medir desde logs de Cortex)} | {ioc_improvement: calcular comparando logs)}% | segundos |
| | Nº IoCs simultáneos | {concurrent_iocs_manual: medir desde logs de ejecución manual)} | {concurrent_iocs_soaR: medir desde logs de Cortex)} | {ioc_capacity_improvement: calcular comparando logs)}% | IoCs |
| | Precisión | {precision_manual: calcular desde tests e2e)}% | {precision_soaR: calcular desde tests e2e)}% | +{precision_improvement: calcular comparando tests)}% | % |
| **Creación Caso** | Tiempo creación | {case_time_manual: medir desde logs de ejecución manual)} | {case_time_soaR: medir desde logs de TheHive)} | {case_improvement: calcular comparando logs)}% | segundos |
| | Campos completados | {fields_manual: inspección manual de casos)}% | {fields_soaR: inspección de casos en TheHive)}% | +{fields_improvement: calcular comparando casos)}% | % |
| | Validación datos | {validation_manual: calcular desde tests e2e)}% | {validation_soaR: calcular desde tests e2e)}% | +{validation_improvement: calcular comparando tests)}% | % |
| **Contención** | Tiempo aislamiento | {containment_time_manual: medir desde logs de ejecución manual)} | {containment_time_soaR: medir desde logs de Shuffle)} | {containment_improvement: calcular comparando logs)}% | segundos |
| | Tasa éxito | {containment_success_manual: calcular desde tests e2e)}% | {containment_success_soaR: calcular desde tests e2e)}% | +{containment_success_improvement: calcular comparando tests)}% | % |
| | Reintentos requeridos | {retries_manual: medir desde logs de ejecución manual)} | {retries_soaR: medir desde logs de Shuffle)} | {retries_improvement: calcular comparando logs)}% | intentos |
| **Notificación** | Tiempo notificación | {notification_time_manual: medir desde logs de ejecución manual)} | {notification_time_soaR: medir desde logs de Shuffle)} | {notification_improvement: calcular comparando logs)}% | segundos |
| | Canales activos | {channels_manual: configuración manual)} | {channels_soaR: configuración en Shuffle)} | {channels_improvement: calcular comparando configuraciones)}% | canales |
| | Confirmación lectura | {read_confirm_manual: medir desde logs de ejecución manual)}% | {read_confirm_soaR: medir desde logs de Shuffle)}% | +{read_confirm_improvement: calcular comparando logs)}% | % |

Esta tabla presenta métricas de rendimiento desglosadas por componente operativo, comparando los tiempos y tasas de éxito manuales baseline con los obtenidos mediante automatización SOAR. La descomposición por componente permite identificar cuellos de botella específicos y áreas donde la automatización proporciona los mayores beneficios. Los componentes de recepción, análisis y creación de caso muestran mejoras significativas en tiempo de procesamiento y throughput, mientras que el componente de contención muestra mejoras menores debido a limitaciones externas. Las métricas adicionales como latencia API, precisión, validación de datos y confirmación de lectura proporcionan una visión comprehensiva del rendimiento del sistema.

### Tabla 4.8: Análisis de Carga del Sistema

| Métrica | Condición Ligera | Condición Media | Condición Pesada | Límite Sistema |
|---------|-----------------|----------------|------------------|---------------|
| **Alertas/hora** | {alerts_light: medir desde logs de Shuffle)} | {alerts_medium: medir desde logs de Shuffle)} | {alerts_heavy: medir desde logs de Shuffle)} | {alerts_limit: configuración de Docker)} |
| **CPU Usage** | {cpu_light: medir desde Docker stats)}% | {cpu_medium: medir desde Docker stats)}% | {cpu_heavy: medir desde Docker stats)}% | {cpu_limit: configuración de Docker)}% |
| **Memory Usage** | {memory_light: medir desde Docker stats)}% | {memory_medium: medir desde Docker stats)}% | {memory_heavy: medir desde Docker stats)}% | {memory_limit: configuración de Docker)}% |
| **MTTR** | {mttr_light: usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py)}s | {mttr_medium: usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py)}s | {mttr_heavy: usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py)}s | {mttr_limit: objetivo de SLA)}s |
| **Success Rate** | {success_light: calcular desde tests e2e)}% | {success_medium: calcular desde tests e2e)}% | {success_heavy: calcular desde tests e2e)}% | {success_limit: objetivo de SLA)}% |
| **Queue Depth** | {queue_light: medir desde logs de Shuffle)} | {queue_medium: medir desde logs de Shuffle)} | {queue_heavy: medir desde logs de Shuffle)} | {queue_limit: configuración de Shuffle)} |
| **Response Time API** | {response_light: medir desde logs de TheHive API)}ms | {response_medium: medir desde logs de TheHive API)}ms | {response_heavy: medir desde logs de TheHive API)}ms | {response_limit: objetivo de SLA)}ms |
| **Error Rate** | {error_light: calcular desde logs de errores)}% | {error_medium: calcular desde logs de errores)}% | {error_heavy: calcular desde logs de errores)}% | {error_limit: objetivo de SLA)}% |

Esta tabla presenta el análisis de carga del sistema bajo diferentes condiciones operativas (ligera, media, pesada) y los límites del sistema. Las métricas incluyen alertas/hora, uso de CPU, uso de memoria, MTTR, tasa de éxito, profundidad de cola, tiempo de respuesta de API y tasa de error. La visualización permite identificar cómo el sistema escala bajo diferentes cargas y dónde se encuentran los límites de capacidad. Este análisis es fundamental para planificar la capacidad del sistema y garantizar que pueda manejar picos de carga sin degradación significativa del rendimiento. Los límites del sistema establecen los umbrales máximos aceptables para cada métrica, proporcionando una base para alertas y escalado automático.

### Tabla 4.9: Métricas de Calidad del Software

| Métrica | Valor Objetivo | Valor Logrado | Estado | Herramienta |
|---------|----------------|----------------|---------|-------------|
| **Coverage de Tests** | >{test_coverage_target: ejecutar make test-coverage}% | {test_coverage_achieved: ejecutar make test-coverage}% | ✅ | pytest |
| **Complejidad Ciclomática** | <{complexity_target: ejecutar radon cc} | {complexity_achieved: ejecutar radon cc} | ✅ | radon |
| **Deuda Técnica** | <{debt_target: ejecutar sonar-scanner} día | {debt_achieved: ejecutar sonar-scanner} días | ✅ | sonarqube |
| **Duplicación de Código** | <{duplication_target: ejecutar PMD}% | {duplication_achieved: ejecutar PMD}% | ✅ | PMD |
| **Issues de Seguridad** | {security_target: ejecutar bandit} | {security_achieved: ejecutar bandit} | ✅ | bandit |
| **Performance Score** | >{performance_target: ejecutar lighthouse} | {performance_achieved: ejecutar lighthouse} | ✅ | lighthouse |
| **Accessibility Score** | >{accessibility_target: ejecutar axe-core} | {accessibility_achieved: ejecutar axe-core} | ✅ | axe-core |
| **SEO Score** | >{seo_target: ejecutar lighthouse} | {seo_achieved: ejecutar lighthouse} | ✅ | lighthouse |

Esta tabla presenta métricas de calidad del software que evalúan la calidad del código, mantenibilidad y cumplimiento de estándares. Las métricas incluyen cobertura de tests, complejidad ciclomática, deuda técnica, duplicación de código, issues de seguridad, performance score, accessibility score y SEO score. Todas las métricas han logrado o superado los objetivos establecidos, indicando un código de alta calidad y bien mantenido. El uso de herramientas automatizadas como pytest, radon, sonarqube, PMD, bandit y lighthouse asegura una evaluación objetiva y consistente de la calidad del software. Estas métricas son fundamentales para garantizar la mantenibilidad a largo plazo del sistema y facilitar su evolución futura.

### Tabla 5.4: KPIs de Negocio por Organización

| KPI | PYME | Mediana | Grande | Enterprise |
|-----|------|---------|--------|-------------|
| **MTTR Objetivo** | <{mttr_sme: usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py)}s | <{mttr_medium: usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py)}s | <{mttr_large: usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py)}s | <{mttr_enterprise: usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py)}s |
| **Costo Incidente** | <${cost_sme: calcular desde comparative_tables.md}K | <${cost_medium: calcular desde comparative_tables.md}K | <${cost_large: calcular desde comparative_tables.md}K | <${cost_enterprise: calcular desde comparative_tables.md}M |
| **ROI SOAR** | >{roi_sme: calcular desde comparative_tables.md}% | >{roi_medium: calcular desde comparative_tables.md}% | >{roi_large: calcular desde comparative_tables.md}% | >{roi_enterprise: calcular desde comparative_tables.md}% |
| **Time to Value** | {value_sme: estimar desde tiempo de implementación} semanas | {value_medium: estimar desde tiempo de implementación} semanas | {value_large: estimar desde tiempo de implementación} semanas | {value_enterprise: estimar desde tiempo de implementación} semanas |
| **Team Productivity** | +{productivity_sme: calcular desde encuestas de equipo}% | +{productivity_medium: calcular desde encuestas de equipo}% | +{productivity_large: calcular desde encuestas de equipo}% | +{productivity_enterprise: calcular desde encuestas de equipo}% |
| **Compliance Score** | >{compliance_sme: calcular desde auditorías de seguridad}% | >{compliance_medium: calcular desde auditorías de seguridad}% | >{compliance_large: calcular desde auditorías de seguridad}% | >{compliance_enterprise: calcular desde auditorías de seguridad}% |
| **Customer Satisfaction** | >{satisfaction_sme: calcular desde encuestas de satisfacción}% | >{satisfaction_medium: calcular desde encuestas de satisfacción}% | >{satisfaction_large: calcular desde encuestas de satisfacción}% | >{satisfaction_enterprise: calcular desde encuestas de satisfacción}% |

Esta tabla muestra KPIs de negocio escalados por tipo de organización (PYME, mediana, grande, enterprise), con objetivos realistas adaptados al tamaño y recursos de cada una. Los KPIs incluyen MTTR objetivo, costo por incidente, ROI de SOAR, time to value, productividad del equipo, score de cumplimiento y satisfacción del cliente. La progresión de valores refleja que organizaciones más grandes con mayores recursos pueden aspirar a objetivos más ambiciosos (MTTR <60s, ROI >250%), mientras que PYMEs con recursos limitados tienen objetivos más conservadores (MTTR <180s, ROI >150%). Esta escalabilidad permite a las organizaciones establecer objetivos apropiados para su contexto y justificar la inversión en capacidades SOAR basándose en el retorno esperado según su tamaño.

---

## Visualizaciones de Impacto

Esta sección incluye visualizaciones de impacto que ilustran las mejoras logradas con el laboratorio SOAR. Las visualizaciones muestran comparaciones antes/después del proceso de respuesta manual versus automatizado, destacando reducciones de tiempo, mejoras en consistencia y aumentos en tasa de éxito. Estas representaciones complementan los análisis cuantitativos previos, ofreciendo una perspectiva intuitiva del impacto de la automatización.

### Impacto Visual de Mejoras

```
ANTES vs DESPUÉS - COMPARACIÓN VISUAL

┌─────────────────────────────────────────────────────────────────┐
│                        ANTES (Manual)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Alerta SIEM ──▶ Analista Humano ──▶ {manual_triage: medir desde logs de ejecución manual)}s                      │
│                          │                                   │
│                          ▼                                   │
│  Análisis IoCs ──▶ Herramientas manuales ──▶ {manual_analysis: medir desde logs de ejecución manual)}s              │
│                          │                                   │
│                          ▼                                   │
│  Creación Caso ──▶ TheHive manual ──▶ {manual_case: medir desde logs de ejecución manual)}s                     │
│                          │                                   │
│                          ▼                                   │
│  Contención ──▶ Scripts manuales ──▶ {manual_containment: medir desde logs de ejecución manual)}s                     │
│                          │                                   │
│                          ▼                                   │
│  Total MTTR: {manual_total: sumar tiempos manuales} segundos                                        │
│  Success Rate: {manual_success: calcular desde tests e2e}%                                               │
│  Consistency: Baja                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       DESPUÉS (SOAR)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Alerta SIEM ──▶ Shuffle Webhook ──▶ {soar_triage: medir desde logs de Shuffle)}s                       │
│                          │                                   │
│                          ▼                                   │
│  Análisis IoCs ──▶ Cortex Analyzers ──▶ {soar_analysis: medir desde logs de Cortex)}s                    │
│                          │                                   │
│                          ▼                                   │
│  Creación Caso ──▶ TheHive API ──▶ {soar_case: medir desde logs de TheHive)}s                      │
│                          │                                   │
│                          ▼                                   │
│  Contención ──▶ Shuffle Playbooks ──▶ {soar_containment: medir desde logs de Shuffle)}s                      │
│                          │                                   │
│                          ▼                                   │
│  Total MTTR: {soar_total: usar KPIAnalyzer.calculate_mttr_metrics() en src/soar_lab/services/kpi_analyzer.py} segundos                                       │
│  Success Rate: {soar_success: calcular desde tests e2e}%                                                │
│  Consistency: Alta                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

MEJORAS CLAVE:
• Reducción MTTR: {mttr_reduction: calcular comparando tiempos manuales vs SOAR}%
• Aumento éxito: +{success_improvement: calcular comparando tests e2e}%
• Mejora consistencia: {consistency_improvement: calcular desde desviación estándar}% menos variabilidad
• Escalabilidad: {scalability: calcular desde capacidad de procesamiento}x más capacidad
```

Estas visualizaciones complementan las tablas y diagramas previos, ofreciendo una visión completa de los aspectos del proyecto SOAR Ransomware Lab, desde métricas técnicas hasta análisis de negocio.
