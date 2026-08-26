# 1. Introducción

## Resumen en Español

Este trabajo diseña un laboratorio SOAR mínimo viable para evaluar si la automatización acelera la respuesta a incidentes de ransomware y mejora la consistencia en el manejo de alertas. La metodología consiste en implementar un playbook automatizado que integra TheHive, Cortex y Shuffle mediante Docker Compose, ejecutando pruebas con alertas maliciosas y benignas para medir tiempos de respuesta. Los resultados muestran una reducción del 92.3 % en MTTR (de 3600 s a 277.15 s, n=50), con 100 % de ejecuciones completadas. Se concluye que el sistema es viable para entornos de SOC y CSIRT, permitiendo comparaciones y extensiones futuras.

**Palabras clave**: SOAR, ransomware, automatización de respuesta, MTTR, laboratorio reproducible.

## English Summary

This work designs a minimum viable SOAR laboratory to evaluate whether automation accelerates ransomware incident response and improves consistency in alert handling. The methodology involves implementing an automated playbook integrating TheHive, Cortex, and Shuffle via Docker Compose, executing tests with malicious and benign alerts to measure response times. Results show a 92.3 % reduction in MTTR (from 3600 s to 277.15 s, n=50), with 100 % of workflows completed. It is concluded that the approach is viable for SOC and CSIRT environments, enabling comparisons and future extensions.

**Keywords**: SOAR, ransomware, incident response automation, MTTR, reproducible laboratory.

## 1.1. Motivación

Los incidentes de ransomware han aumentado en los últimos años. El Global Threat Intelligence Report 2024 indica un incremento del 67 % en incidentes de seguridad. Según el informe, el ransomware representa el 23 % del total (CrowdStrike, 2024). El Verizon DBIR confirma esta tendencia, situando el ransomware entre las amenazas más frecuentes en brechas verificadas (Verizon, 2024). Aun así, en muchos entornos la gestión de estos incidentes sigue basándose en tareas manuales. Esto genera retrasos, aumenta la carga del analista y dificulta conservar una traza del proceso. La automatización mediante plataformas SOAR (Security Orchestration, Automation and Response) surge como respuesta a estas limitaciones.

En la práctica, una alerta de ransomware exige varias tareas. Primero se valida la información. Luego se abre un caso, se añaden los observables y se consulta información contextual. Solo entonces se toma una decisión sobre la contención.
Cuando estas actividades se ejecutan manualmente, el tiempo de respuesta aumenta. También aparecen diferencias entre analistas, lo que dificulta la mejora continua. La **Figura 1** anticipa la magnitud de esta mejora: el MTTR (Mean Time to Respond, Tiempo Medio de Respuesta) pasa de 3600 s en la respuesta manual a 277.15 s con la respuesta automatizada SOAR, una reducción del 92.3 %. El baseline manual de 3600 s (1 hora) es conservador frente a los datos de la industria: CrowdStrike fija como benchmark ideal 60 minutos para contener (regla 1-10-60), pero la media real observada en su survey es de 16 horas (CrowdStrike, 2021). ReliaQuest reporta un MTTR tradicional de 2.3 días sin automatización (ReliaQuest, 2024), y la SANS SOC (Security Operations Center) Survey 2025 sitúa el tiempo mediano de triaje y escalado de alertas en 260 minutos (SANS Institute, 2025).

![Figura 1: Comparación MTTR manual vs automatizado](figures/Fig5_1_mttr_results.png)

**Figura 1**: Comparación del MTTR entre la respuesta manual (3600 s) y la respuesta automatizada SOAR (277.15 s),
que muestra una reducción del 92.3 %.

La fragmentación de herramientas obliga al analista a usar varios sistemas a la vez. Algunas tareas se repiten en casi todos los casos, como triage, enriquecimiento o actualización de tickets. Si se hacen a mano, consumen tiempo y aumentan los errores (Kinyua & Awuah, 2021). Sin un flujo estandarizado, es difícil medir la respuesta y comparar ejecuciones (Stevens et al., 2022).

La literatura sobre respuesta a incidentes apunta en esa dirección. NIST SP 800-61 (NIST, 2023) y los estudios sobre plataformas SOAR destacan el valor de centralizar datos, análisis y respuesta en un mismo flujo. Esta integración puede reducir tiempos y limitar errores de la intervención manual (Kinyua & Awuah, 2021; Mohammad & Lakshmisri, 2018).

En ransomware, el tiempo entre detección y contención condiciona el daño. El cifrado de archivos puede propagarse rápido a través de unidades compartidas (CISA, 2023). Por ello, un entorno controlado y reproducible sirve para probar configuraciones del flujo y comparar ejecuciones bajo las mismas condiciones.

Un laboratorio mínimo viable permite estudiar cómo un playbook integra herramientas y automatiza tareas sin los riesgos de un entorno productivo. En este trabajo, Cortex actúa como motor de análisis centralizando la consulta de observables mediante APIs. Es un patrón usado en contextos de SOC y CSIRT (Computer Security Incident Response Team, Equipo de Respuesta a Incidentes de Seguridad Informática) que aquí se evalúa en un entorno acotado.

## 1.2. Planteamiento del problema

### Descripción del problema

En muchos SOC, la gestión de incidentes de ransomware se basa en procesos manuales, integraciones parciales y criterios no estandarizados (Kinyua & Awuah, 2021). Esta situación incrementa los tiempos de respuesta, introduce variabilidad y dificulta generar evidencias completas. Como la demora en la contención amplifica el impacto del cifrado, esa variabilidad puede afectar a la severidad del incidente (CISA, 2023).

La automatización mediante plataformas SOAR y playbooks aparece en la literatura como una alternativa para reducir carga manual y ordenar los procesos de decisión (Kinyua & Awuah, 2021; Mohammad & Lakshmisri, 2018). Esto no implica eliminar la supervisión humana, especialmente en acciones de mayor consecuencia. Pero su adopción plantea dificultades como la complejidad de los entornos productivos, las licencias comerciales y la dificultad de medir su efecto en condiciones controladas.

### Pregunta de investigación

La pregunta que guía este trabajo es:

> **¿En qué medida un playbook SOAR automatizado, desplegado en un laboratorio reproducible basado en herramientas
> open source, reduce el MTTR y mejora la consistencia de la respuesta a alertas de ransomware respecto a la respuesta
> manual?**

Esta pregunta se desagrega en tres aspectos verificables: (1) la reducción cuantitativa del tiempo de respuesta (MTTR), (2) la mejora de la consistencia mediante un flujo estandarizado y trazable, y (3) la viabilidad técnica de un entorno reproducible con herramientas open source. La hipótesis de trabajo, detallada en el Capítulo 3, sostiene que la automatización SOAR reduce el MTTR en al menos un 50 % y mejora la consistencia frente a los procesos manuales.

### Propuesta de solución

Este trabajo propone el diseño e implementación de un laboratorio SOAR mínimo viable, reproducible y autocontenido que materialice un playbook orientado a ransomware. No se pretende desplegar una solución de producción completa. El objetivo es mostrar cómo un flujo automatizado puede combinar la recepción de alertas, la normalización de datos, la gestión de casos, el enriquecimiento de observables y la contención simulada de manera coherente y trazable.

Al ser reproducible, el laboratorio permite evaluar cambios del playbook sobre una misma línea base. Esto facilita comparaciones y deja margen para extensiones futuras. Los pasos operativos para reproducir el experimento, los casos de error esperados y los criterios de verificación se detallan en el Capítulo 3 (Metodología).

Los resultados obtenidos confirman la hipótesis: el playbook SOAR reduce el MTTR medio en un 92.3 % (de 3600 s estimados a 277.15 s medidos sobre 50 ejecuciones), superando el objetivo del 50 %. La consistencia mejora estructuralmente, pues todas las ejecuciones siguen el mismo flujo trazable. El entorno reproducible con herramientas open source resulta viable técnicamente (10/10 servicios healthy, 50/50 workflows completados). Dos umbrales ambiciosos de percentiles (P50 ≤ 120 s, P90 ≤ 180 s) no se alcanzaron en el conjunto completo, lo que se discute junto a las limitaciones del estudio en el Capítulo 5.

## 1.3. Estructura del trabajo

El documento se organiza en páginas preliminares, cinco capítulos, referencias y anexos.

**Páginas preliminares.** Portada, resumen ejecutivo y abstract, agradecimientos, lista de abreviaturas, índice de
figuras, índice de tablas e índice general.

**Capítulo 1: Introducción.** Plantea la motivación, el problema de investigación, la pregunta de investigación y la
estructura del trabajo.

**Capítulo 2: Estado del arte.** Revisa la literatura sobre respuesta a incidentes, ransomware y plataformas SOAR e
identifica las lagunas que esta investigación aborda.

**Capítulo 3: Objetivos y metodología.** Presenta los objetivos generales y específicos, el diseño experimental y el
plan de gestión de riesgos.

**Capítulo 4: Desarrollo específico.** Detalla los elementos técnicos del ensayo, incluyendo requisitos, arquitectura,
implementación del playbook y resultados experimentales.

**Capítulo 5: Conclusiones y trabajo futuro.** Presenta los hallazgos, debate las limitaciones del estudio y formula
sugerencias para entornos que deseen aplicar capacidades SOAR similares.

**Referencias.** Lista completa de fuentes citadas en el texto, ordenadas alfabéticamente.

**Anexos.**

- Anexo A: documentación técnica requerida para reproducir el ensayo (configuración Docker, scripts, guías de
  instalación).
- Anexo B: workflow SOAR completo (46 nodos, 60 ramas, 25 scripts Python).
- Anexo C: gráficos y diagramas complementarios (las tablas comparativas se han reubicado en sus capítulos
  correspondientes).
- Anexo D: métricas y visualizaciones complementarias (26 figuras generadas desde resultados experimentales y
  dashboards de Grafana).
- Anexo E: validación experimental consolidada (Quality Score 92.2/100, HPR 96.0/100).
- Anexo F: registro de cambios técnicos y editoriales aplicados durante el desarrollo.
- Anexo G: estrategia de testing (2041 tests, pirámide, quality gates).
- Anexo H: diagramas canónicos de arquitectura y flujos (13 diagramas Mermaid).

---

## Índice de Figuras del Capítulo 1

| Figura    | Título                                    | Archivo                              |
|-----------|-------------------------------------------|--------------------------------------|
| Figura 1 | Comparación MTTR manual vs automatizado | `figures/Fig5_1_mttr_results.png` |

## Índice de Tablas del Capítulo 1

Este capítulo no contiene tablas.
