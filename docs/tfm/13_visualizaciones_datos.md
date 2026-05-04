# Visualizaciones de Datos y Gráficos Complementarios

## Gráficos Estadísticos Detallados

### Gráfico 4.3: Distribución de Tiempos de Respuesta por Componente

```
TIEMPO DE RESPUESTA (segundos) - DESCOMPOSICIÓN

Manual ({total_time_manual: tiempo manual baseline - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})s total):
┌─────────────────────────────────────────────────────────────────┐
│ Recepción Triaje ({reception_manual: tiempo manual triaje - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})s ████████████████████████████████████████ │
│ Análisis IoCs ({analysis_manual: tiempo manual análisis IoCs - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})s   ████████████████████████████████████████ │
│ Creación Caso ({creation_manual: tiempo manual creación caso - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})s   ████████████████████████████              │
│ Contención ({containment_manual: tiempo manual contención - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})s     ████████████████████████████████████████ │
└─────────────────────────────────────────────────────────────────┘

SOAR ({total_time_soaR: tiempo SOAR real - ejecutar `make data-generate` luego `make data-view` para ver valor actual - datos en [scripts/tfm_data_enhancer.py](../scripts/tfm_data_enhancer.py)})s total):
┌─────────────────────────────────────────────────────────────────┐
│ Recepción Triaje ({reception_soaR: tiempo SOAR triaje - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})s   ████████                              │
│ Análisis IoCs ({analysis_soaR: tiempo SOAR análisis IoCs - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})s     ████████████████                      │
│ Creación Caso ({creation_soaR: tiempo SOAR creación caso - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})s     ██████                                 │
│ Contención ({containment_soaR: tiempo SOAR contención - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})s       ██████████████████████████████████████ │
└─────────────────────────────────────────────────────────────────┘

Reducción porcentual:
• Recepción Triaje: {reception_reduction: reducción recepción - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% ↓
• Análisis IoCs:     {analysis_reduction: reducción análisis - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% ↓
• Creación Caso:     {creation_reduction: reducción creación - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% ↓
• Contención:        {containment_reduction: reducción contención - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}%  ↓
```

### Gráfico 4.4: Análisis de Percentiles de Rendimiento

```
PERCENTILES DE MTTR (segundos)

100 ┤                               ● Manual: {p100_manual: percentil 100 manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
 90 ┤                     ● Manual: {p90_manual: percentil 90 manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s      ● SOAR: {p90_soaR: percentil 90 SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
 80 ┤                     ● Manual: {p80_manual: percentil 80 manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s      ● SOAR: {p80_soaR: percentil 80 SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
 70 ┤                     ● Manual: {p70_manual: percentil 70 manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s      ● SOAR: {p70_soaR: percentil 70 SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
 60 ┤                     ● Manual: {p60_manual: percentil 60 manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s      ● SOAR: {p60_soaR: percentil 60 SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
 50 ┤           ● Manual: {p50_manual: mediana manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s      ● SOAR: {p50_soaR: mediana SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
 40 ┤           ● Manual: {p40_manual: percentil 40 manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s      ● SOAR: {p40_soaR: percentil 40 SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
 30 ┤           ● Manual: {p30_manual: percentil 30 manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s      ● SOAR: {p30_soaR: percentil 30 SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
 20 ┤           ● Manual: {p20_manual: percentil 20 manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s      ● SOAR: {p20_soaR: percentil 20 SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
 10 ┤           ● Manual: {p10_manual: percentil 10 manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s      ● SOAR: {p10_soaR: percentil 10 SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
  0 ┤ ● Manual: {p0_manual: valor mínimo manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s      ● SOAR: {p0_soaR: valor mínimo SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}s
    └─────────────────────────────────────────────────────────
         P10    P20    P30    P40    P50    P60    P70    P80    P90   P100

Diferenciales clave:
• P50 (Mediana): {p50_reduction: reducción mediana - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% reducción
• P90: {p90_reduction: reducción percentil 90 - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% reducción  
• P95: {p95_reduction: reducción percentil 95 - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% reducción
• Rango: {range_reduction: reducción rango - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% reducción
```

### Gráfico 4.5: Tasa de Éxito por Tipo de Alerta

```
TASA DE ÉXITO (%)

100 ┤
 95 ┤       ████████████████████████████████████████████████████
     │ Manual: {success_rate_manual: tasa éxito manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}%    SOAR: {success_rate_soaR: tasa éxito SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}%
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
• Manual: {malicious_manual: tasa éxito maliciosas manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% ({malicious_manual_correct: aciertos maliciosos manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}/{malicious_manual_total: total maliciosas manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})
• SOAR:   {malicious_soaR: tasa éxito maliciosas SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% ({malicious_soaR_correct: aciertos maliciosos SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}/{malicious_soaR_total: total maliciosas SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})

Benignas:
• Manual: {benign_manual: tasa éxito benignas manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% ({benign_manual_correct: aciertos benignos manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}/{benign_manual_total: total benignas manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})  
• SOAR:   {benign_soaR: tasa éxito benignas SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% ({benign_soaR_correct: aciertos benignos SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}/{benign_soaR_total: total benignas SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})

Total:
• Manual: {total_manual: tasa éxito total manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% ({total_manual_correct: aciertos totales manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}/{total_manual_total: total casos manual - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})
• SOAR:   {total_soaR: tasa éxito total SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}% ({total_soaR_correct: aciertos totales SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)}/{total_soaR_total: total casos SOAR - ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py)})
```

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

### Gráfico 5.5: Comparación de Costos y Beneficios

```
ANÁLISIS COSTO-BENEFICIO (3 años)

Costo Total ($ miles):
500 ┤                         ████████████████████████████████
     │                         IBM Resilient: ${cost_resilient: calcular licencia + implementación + mantenimiento 3 años - ver [docs/12_tablas_comparativas.md](12_tablas_comparativas.md)}M
450 ┤
400 ┤                     ████████████████████████████████
     │                     Palo Alto XSOAR: ${cost_xsoar: calcular licencia + implementación + mantenimiento 3 años - ver [docs/12_tablas_comparativas.md](12_tablas_comparativas.md)}M
350 ┤
300 ┤                 ████████████████████████████████
     │                 Híbrido: ${cost_hybrid: calcular costos combinados open source + soporte - ver [docs/12_tablas_comparativas.md](12_tablas_comparativas.md)}M
250 ┤
200 ┤             ████████████████████████████████
     │             SOAR Open Source: ${cost_opensource: calcular infraestructura + desarrollo + mantenimiento - ver [docs/12_tablas_comparativas.md](12_tablas_comparativas.md)}K
150 ┤
100 ┤         ████████████████████████████████
     │         Manual: ${cost_manual: calcular personal + herramientas manuales - ver [docs/12_tablas_comparativas.md](12_tablas_comparativas.md)}K
 50 ┤
  0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Manual  SOAR OS  Híbrido  XSOAR  Resilient

ROI (Retorno de Inversión %):
300 ┤
250 ┤                         ● SOAR Open Source: {roi_opensource: calcular ((beneficio-costos)/costos)*100 - ver [scripts/calc_kpis.py](../scripts/calc_kpis.py)}%
225 ┤
200 ┤                     ● Híbrido: {roi_hybrid: calcular ((beneficio-costos)/costos)*100 - ver [scripts/calc_kpis.py](../scripts/calc_kpis.py)}%
175 ┤
150 ┤                 ● Resilient: {roi_resilient: calcular ((beneficio-costos)/costos)*100 - ver [scripts/calc_kpis.py](../scripts/calc_kpis.py)}%
125 ┤
100 ┤
 75 ┤
 50 ┤             ● XSOAR: {roi_xsoar: calcular ((beneficio-costos)/costos)*100 - ver [scripts/calc_kpis.py](../scripts/calc_kpis.py)}%
 25 ┤
  0 ┤ ● Manual: {roi_manual: ROI baseline = 0 - ver [docs/12_tablas_comparativas.md](12_tablas_comparativas.md)}%
    └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Manual  SOAR OS  Híbrido  XSOAR  Resilient

MTTR Promedio (segundos):
250 ┤ ● Manual: {mttr_manual: promediar tiempos de respuesta manual - ver [scripts/calc_kpis.py](../scripts/calc_kpis.py)}s
225 ┤ ●
200 ┤ ●
175 ┤ ●
150 ┤ ●
125 ┤                     ● XSOAR: {mttr_xsoar: promediar tiempos de respuesta XSOAR - ver [docs/12_tablas_comparativas.md](12_tablas_comparativas.md)}s
100 ┤                     ●
 75 ┤                     ●    ● Híbrido: {mttr_hybrid: promediar tiempos de respuesta híbrido - ver [docs/12_tablas_comparativas.md](12_tablas_comparativas.md)}s
 50 ┤                     ●    ●    ● SOAR OS: {mttr_opensource: promediar tiempos de respuesta open source - ver [scripts/calc_kpis.py](../scripts/calc_kpis.py)}s
 25 ┤                     ●    ●    ●
  0 └─┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┘
    Manual  SOAR OS  Híbrido  XSOAR  Resilient
```

## Diagramas de Flujo Detallados

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
│  │  │Elasticsearch│  │ PostgreSQL   │  │        Redis             │   │    │
│  │  │   Logs      │  │   Cases     │  │       Cache              │   │    │
│  │  │   Index     │  │   Metadata  │  │   Sessions              │   │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

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

## Tablas de Métricas Avanzadas

### Tabla 4.7: Métricas de Rendimiento por Componente

| Componente | Métrica | Manual | SOAR | Mejora | Unidad |
|------------|---------|--------|------|---------|--------|
| **Recepción** | Tiempo procesamiento | {reception_time_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {reception_time_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {reception_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | segundos |
| | Throughput | {throughput_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {throughput_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {throughput_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | alertas/hora |
| | Latencia API | N/A | {api_latency: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | N/A | ms |
| **Análisis** | Tiempo por IoC | {ioc_time_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {ioc_time_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {ioc_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | segundos |
| | Nº IoCs simultáneos | {concurrent_iocs_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {concurrent_iocs_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {ioc_capacity_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | IoCs |
| | Precisión | {precision_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {precision_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | +{precision_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | % |
| **Creación Caso** | Tiempo creación | {case_time_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {case_time_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {case_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | segundos |
| | Campos completados | {fields_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {fields_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | +{fields_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | % |
| | Validación datos | {validation_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {validation_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | +{validation_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | % |
| **Contención** | Tiempo aislamiento | {containment_time_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {containment_time_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {containment_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | segundos |
| | Tasa éxito | {containment_success_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {containment_success_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | +{containment_success_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | % |
| | Reintentos requeridos | {retries_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {retries_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {retries_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | intentos |
| **Notificación** | Tiempo notificación | {notification_time_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {notification_time_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {notification_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | segundos |
| | Canales activos | {channels_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {channels_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {channels_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | canales |
| | Confirmación lectura | {read_confirm_manual: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {read_confirm_soaR: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | +{read_confirm_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | % |

### Tabla 4.8: Análisis de Carga del Sistema

| Métrica | Condición Ligera | Condición Media | Condición Pesada | Límite Sistema |
|---------|-----------------|----------------|------------------|---------------|
| **Alertas/hora** | {alerts_light: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {alerts_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {alerts_heavy: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {alerts_limit: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} |
| **CPU Usage** | {cpu_light: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {cpu_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {cpu_heavy: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {cpu_limit: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% |
| **Memory Usage** | {memory_light: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {memory_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {memory_heavy: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {memory_limit: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% |
| **MTTR** | {mttr_light: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s | {mttr_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s | {mttr_heavy: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s | {mttr_limit: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s |
| **Success Rate** | {success_light: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {success_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {success_heavy: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {success_limit: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% |
| **Queue Depth** | {queue_light: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {queue_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {queue_heavy: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {queue_limit: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} |
| **Response Time API** | {response_light: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}ms | {response_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}ms | {response_heavy: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}ms | {response_limit: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}ms |
| **Error Rate** | {error_light: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {error_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {error_heavy: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {error_limit: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% |

### Tabla 4.9: Métricas de Calidad del Software

| Métrica | Valor Objetivo | Valor Logrado | Estado | Herramienta |
|---------|----------------|----------------|---------|-------------|
| **Coverage de Tests** | >{test_coverage_target: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {test_coverage_achieved: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | ✅ | pytest |
| **Complejidad Ciclomática** | <{complexity_target: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {complexity_achieved: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | ✅ | radon |
| **Deuda Técnica** | <{debt_target: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} día | {debt_achieved: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} días | ✅ | sonarqube |
| **Duplicación de Código** | <{duplication_target: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | {duplication_achieved: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | ✅ | PMD |
| **Issues de Seguridad** | {security_target: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {security_achieved: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | ✅ | bandit |
| **Performance Score** | >{performance_target: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {performance_achieved: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | ✅ | lighthouse |
| **Accessibility Score** | >{accessibility_target: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {accessibility_achieved: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | ✅ | axe-core |
| **SEO Score** | >{seo_target: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | {seo_achieved: ejecutar `make test-coverage` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} | ✅ | lighthouse |

### Tabla 5.4: KPIs de Negocio por Organización

| KPI | PYME | Mediana | Grande | Enterprise |
|-----|------|---------|--------|-------------|
| **MTTR Objetivo** | <{mttr_sme: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s | <{mttr_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s | <{mttr_large: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s | <{mttr_enterprise: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s |
| **Costo Incidente** | <${cost_sme: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}K | <${cost_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}K | <${cost_large: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}K | <${cost_enterprise: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}M |
| **ROI SOAR** | >{roi_sme: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | >{roi_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | >{roi_large: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | >{roi_enterprise: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% |
| **Time to Value** | {value_sme: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} semanas | {value_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} semanas | {value_large: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} semanas | {value_enterprise: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} semanas |
| **Team Productivity** | +{productivity_sme: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | +{productivity_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | +{productivity_large: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | +{productivity_enterprise: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% |
| **Compliance Score** | >{compliance_sme: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | >{compliance_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | >{compliance_large: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | >{compliance_enterprise: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% |
| **Customer Satisfaction** | >{satisfaction_sme: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | >{satisfaction_medium: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | >{satisfaction_large: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% | >{satisfaction_enterprise: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% |

---

## Visualizaciones de Impacto

### Impacto Visual de Mejoras

```
ANTES vs DESPUÉS - COMPARACIÓN VISUAL

┌─────────────────────────────────────────────────────────────────┐
│                        ANTES (Manual)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Alerta SIEM ──▶ Analista Humano ──▶ {manual_triage: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s                      │
│                          │                                   │
│                          ▼                                   │
│  Análisis IoCs ──▶ Herramientas manuales ──▶ {manual_analysis: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s              │
│                          │                                   │
│                          ▼                                   │
│  Creación Caso ──▶ TheHive manual ──▶ {manual_case: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s                     │
│                          │                                   │
│                          ▼                                   │
│  Contención ──▶ Scripts manuales ──▶ {manual_containment: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s                     │
│                          │                                   │
│                          ▼                                   │
│  Total MTTR: {manual_total: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} segundos                                        │
│  Success Rate: {manual_success: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}%                                               │
│  Consistency: Baja                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       DESPUÉS (SOAR)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Alerta SIEM ──▶ Shuffle Webhook ──▶ {soar_triage: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s                       │
│                          │                                   │
│                          ▼                                   │
│  Análisis IoCs ──▶ Cortex Analyzers ──▶ {soar_analysis: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s                    │
│                          │                                   │
│                          ▼                                   │
│  Creación Caso ──▶ TheHive API ──▶ {soar_case: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s                      │
│                          │                                   │
│                          ▼                                   │
│  Contención ──▶ Shuffle Playbooks ──▶ {soar_containment: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}s                      │
│                          │                                   │
│                          ▼                                   │
│  Total MTTR: {soar_total: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))} segundos                                       │
│  Success Rate: {soar_success: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}%                                                │
│  Consistency: Alta                                               │
│                          │                                   │
│                          ▼                                   │
│  Creación Caso ──▶ TheHive API ──▶ {soar_case: medir creación API - ver [docs/api.md](../docs/api.md)}s                         │
│                          │                                   │
│                          ▼                                   │
│  Contención ──▶ Scripts Auto ──▶ {soar_containment: medir contención automatizada - ver [docs/technical.md](../docs/technical.md)}s                         │
│                          │                                   │
│                          ▼                                   │
│  Total MTTR: {soar_total: sumar tiempos SOAR - ver [scripts/calc_kpis.py](../scripts/calc_kpis.py)} segundos                                         │
│  Success Rate: {soar_success: calcular (aciertos_soaR/total_soaR)*100 - ver [tests/e2e/TC-01/test_malicious.py](../tests/e2e/TC-01/test_malicious.py)}%                                             │
│  Consistency: Alta                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

MEJORAS CLAVE:
• Reducción MTTR: {mttr_reduction: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}%
• Aumento éxito: +{success_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}%
• Mejora consistencia: {consistency_improvement: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}% menos variabilidad
• Escalabilidad: {scalability: ejecutar `make data-view` para ver valor actual - datos en [scripts/tfm_data_viewer.py](../scripts/tfm_data_viewer.py))}x más capacidad
```

Estas visualizaciones complementan las tablas y diagramas previos, proporcionando una visión completa y detallada de todos los aspectos del proyecto SOAR Ransomware Lab, desde métricas técnicas hasta análisis de negocio y comparativas de soluciones.
