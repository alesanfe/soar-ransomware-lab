# Índice General del Trabajo Fin de Máster

## Estructura Completa del Documento

### Páginas Preliminares

1. **Portada** — `cover_page.md`
2. **Resumen Ejecutivo / Abstract** — `executive_summary.md`
3. **Agradecimientos** — `acknowledgments.md`
4. **Lista de Abreviaturas** — `abbreviations_list.md`
5. **Índice de Figuras** — `figures_list.md`
6. **Índice de Tablas** — `tables_list.md`
7. **Índice General** (este documento)

### Cuerpo del Documento

#### **Capítulo 1: Introducción** — `introduction.md`

- Resumen en Español
- English Summary
- 1.1. Motivación
- 1.2. Planteamiento del problema
  - Descripción del problema
  - Pregunta de investigación
  - Propuesta de solución
- 1.3. Estructura del trabajo

#### **Capítulo 2: Estado del arte** — `state_of_the_art.md`

- 2.1. Respuesta a incidentes y ransomware como dominio de aplicación
- 2.2. Automatización, SOAR y playbooks en operaciones de seguridad
- 2.3. Laboratorios reproducibles, herramientas open source y evaluación
- 2.4. Síntesis y relación con el TFM

#### **Capítulo 3: Objetivos concretos y metodología de trabajo** — `objectives_and_methodology.md`

- 3.1. Objetivo general
- 3.2. Objetivos específicos
  - 3.2.1. Objetivos Estratégicos
  - 3.2.2. Objetivos Operativos
- 3.3. Metodología del trabajo
  - Pasos operativos para reproducir el experimento
  - Casos de error esperados
  - Criterios de verificación

#### **Capítulo 4: Desarrollo específico de la contribución** — `specific_development.md`

- 4.1. Desarrollo de software
  - 4.1.1. Identificación de requisitos
  - 4.1.2. Descripción de la herramienta software desarrollada
    - Arquitectura de Código Python
    - Arquitectura de Despliegue
    - Componentes Principales
    - Scripts de Automatización Desarrollados
    - Playbooks de Respuesta a Ransomware
    - Infraestructura Docker Compose
    - Sistema de Monitoreo
  - 4.1.3. Evaluación
    - 4.1.3.1. Diseño Experimental
    - 4.1.3.2. Procedimiento de Evaluación
    - 4.1.3.3. Resultados Experimentales
    - 4.1.3.4. Evaluación de Calidad del Sistema
    - 4.1.3.5. Sistema de Monitoreo
    - 4.1.3.6. Análisis de Mejoras Implementadas
    - 4.1.3.7. Discusión
    - 4.1.3.8. Limitaciones

#### **Capítulo 5: Conclusiones y trabajo futuro** — `conclusions_and_future_work.md`

- 5.1. Resumen de conclusiones principales
  - 5.1.1. Respuesta a la pregunta de investigación
  - 5.1.2. Cumplimiento de objetivos planteados
  - 5.1.3. Contribuciones teóricas y prácticas
  - 5.1.4. Implicaciones para la práctica profesional
  - 5.1.5. Limitaciones del estudio realizado
- 5.2. Trabajo futuro y líneas de investigación
  - 5.2.1. Mejoras técnicas inmediatas
  - 5.2.2. Investigaciones longitudinales propuestas
  - 5.2.3. Desarrollo de capacidades de Machine Learning
  - 5.2.4. Expansión a otros tipos de incidentes
  - 5.2.5. Investigaciones en Interfaz Humano-Máquina
- 5.3. Recomendaciones para organizaciones
  - 5.3.1. Guía de implementación práctica
  - 5.3.2. Consideraciones de adopción organizacional
  - 5.3.3. Métricas de éxito y KPIs recomendados
  - 5.3.4. Mejores prácticas de mantenimiento y desarrollo
- 5.4. Alcance del trabajo

### Secciones Finales

8. **Referencias bibliográficas** — `bibliographic_references.md`
9. **Declaración de originalidad** — `originality_declaration.md`
10. **Tablas comparativas de plataformas SOAR** — `appendix_c.md`
11. **Visualizaciones de datos y gráficos complementarios** — `appendix_d.md`
12. **Glosario** — `abbreviations_list.md`

### Anexos

- **Anexo A** — `appendix_a.md` — Configuración Docker completa, scripts, troubleshooting
- **Anexo B** — `appendix_b.md` — Workflow SOAR completo (46 nodos, 60 ramas, 25 scripts Python)
- **Anexo C** — `appendix_c.md` — Gráficos y diagramas complementarios (las tablas se han reubicado en sus capítulos correspondientes)
- **Anexo D** — `appendix_d.md` — Métricas y visualizaciones complementarias
- **Anexo E** — `appendix_e.md` — Validación experimental (Quality Score 92.2/100, HPR 96.0/100)
- **Anexo F** — `appendix_f.md` — Registro de cambios técnicos y editoriales
- **Anexo G** — `appendix_g.md` — Estrategia de testing (2041 tests, pirámide, quality gates)
- **Anexo H** — `appendix_h.md` — Diagramas canónicos de arquitectura y flujos (13 diagramas Mermaid)


## Detalle de Contenido por Capítulo

### Capítulo 1: Introducción

**1.1. Motivación**

- Contexto actual de ciberseguridad
- Crecimiento del ransomware (67 % en incidentes, 23 % del total (CrowdStrike, 2024))
- Volumen de alertas y limitaciones humanas
- Necesidad crítica de automatización
- Figura 1: Comparación MTTR manual vs automatizado

**1.2. Planteamiento del problema**

- Limitaciones de respuesta manual
- Pregunta de investigación explícita
- Hipótesis de trabajo
- Propuesta de solución: laboratorio SOAR mínimo viable

**1.3. Estructura del trabajo**

- Descripción de los 5 capítulos principales
- Referencias y anexos

### Capítulo 2: Estado del arte

**2.1. Respuesta a incidentes y ransomware como dominio de aplicación**

- NIST SP 800-61, ISO/IEC 27035
- CISA, ENISA, Mandiant, CrowdStrike
- MITRE ATT&CK T1486

**2.2. Automatización, SOAR y playbooks en operaciones de seguridad**

- SIEM vs SOAR
- Playbooks vs runbooks (Kinyua y Awuah)
- IA/ML en respuesta a incidentes
- Stevens et al.: frameworks de diseño de playbooks
- Schlette et al.: 1217 playbooks analizados
- OASIS CACAO 2.0, Sigma, Shuffle

**2.3. Laboratorios reproducibles, herramientas open source y evaluación**

- Núñez Fernández: plataforma SIRP reproducible
- NIST SP 800-150: compartición de amenazas
- Quintero Tamayo et al.: playbooks para CSIRT
- Métricas temporales: p50, p90

**2.4. Síntesis y relación con el TFM**

- Tres ideas articuladoras
- Brecha identificada: falta de evidencia cuantitativa rigurosa
- Conexión con el método del TFM

### Capítulo 3: Objetivos y metodología

**3.1. Objetivo general**

- Demostrar que un playbook SOAR reduce MTTR y mejora consistencia
- Umbrales: reducción ≥ 50 %, P50 ≤ 120 s, P90 ≤ 180 s

**3.2. Objetivos específicos**

- 5 objetivos estratégicos (diseño, implementación, evaluación, documentación, optimización)
- 12 objetivos operativos
- Criterios de éxito medibles

**3.3. Metodología**

- Investigación aplicada + DevSecOps
- 5 fases (semanas 1-12)
- Stack tecnológico: Docker, Python, TheHive, Cortex, Shuffle
- Diseño experimental: variable independiente (manual vs SOAR), dependientes (MTTR, tasa de éxito,
  precisión, uso de recursos)
- Consideraciones éticas y de seguridad
- Pasos operativos, casos de error, criterios de verificación

### Capítulo 4: Desarrollo específico

**4.1.1. Identificación de requisitos**

- Funcionales, no funcionales, de integración
- Matriz de trazabilidad

**4.1.2. Herramienta desarrollada**

- Arquitectura hexagonal Python (domain/, application/, infrastructure/, interfaces/)
- Arquitectura de despliegue Docker Compose (18 servicios)
- Componentes: TheHive, Cortex, Shuffle, Elasticsearch, Grafana, Loki
- Scripts de automatización
- Playbooks de respuesta a ransomware
- Infraestructura Docker Compose
- Sistema de monitoreo

**4.1.3. Evaluación**

- Diseño experimental (50 runs, 2 escenarios)
- Resultados: MTTR 277.15 s, P50 193.19 s, P90 621.83 s, 92.3 % reducción
- Precisión: 8.0 % falsos positivos, 92.0 % clasificación correcta
- Uso de recursos: docker stats dentro de límites
- 5/7 objetivos cumplidos
- Quality Score 92.2/100, HPR 96.0/100
- Discusión: interpretación, comparación con literatura, consistencia (CV 67.7 %), análisis por subconjuntos
- Limitaciones

### Capítulo 5: Conclusiones

**5.1. Conclusiones principales**

- 5.1.1. Respuesta a la pregunta de investigación
- 5.1.2. Cumplimiento de objetivos (5/7)
- 5.1.3. Contribuciones teóricas y prácticas
- 5.1.4. Implicaciones para la práctica profesional
- 5.1.5. Limitaciones del estudio

**5.2. Trabajo futuro**

- Mejoras técnicas (analyzers concurrentes, Kubernetes, Zero Trust)
- Investigaciones longitudinales (12-24 meses)
- Machine Learning (detección predictiva, NLP, RL)
- Expansión a APT, insider threat, supply chain
- Interfaz humano-máquina (explicabilidad, carga cognitiva)

**5.3. Recomendaciones para organizaciones**

- Guía de implementación (4 fases)
- Adopción organizacional
- KPIs recomendados
- Mantenimiento y desarrollo

**5.4. Alcance del trabajo**

- Reducción 92.3 % MTTR con 50 ejecuciones
- Arquitectura hexagonal y modular transferible
- Software open source: accesible a pymes y CSIRTs
- Figura 11: Análisis coste-beneficio

### Anexos

**Anexo A** — `appendix_a.md`

- Configuración Docker completa
- Scripts de automatización
- Plantillas y configuraciones
- Guías de instalación

**Anexo B** — `appendix_b.md`

- Workflow SOAR completo (46 nodos, 60 ramas, 25 scripts Python)

**Anexo C** — `appendix_c.md`

- Gráficos ASCII de métricas (MTTR, percentiles, tasas de éxito)
- Diagramas de arquitectura complementarios
- Esquemas de flujo de procesos
- Las tablas comparativas se han reubicado en sus capítulos correspondientes con numeración APA

**Anexo D** — `appendix_d.md`

- Visualizaciones ASCII de métricas (MTTR, percentiles, tasas de éxito)
- Gráficos de evolución temporal y coste-beneficio
- 15 figuras generadas desde resultados experimentales y dashboards Grafana

**Anexo E** — `appendix_e.md`

- Resultados E2E (n=50): MTTR, contención, score, servicios
- Quality Score: 92.2/100 (complexity, coverage, security, linting)
- Holistic Project Radar: 96.0/100 (5 capas, 15 dimensiones)
- Test Review: 92.2/100 (7 dimensiones, 2041 tests)
- Infraestructura: 18 servicios, 18 contenedores, 131 env vars
- API: 38 endpoints (OpenAPI 3.1.0)

**Anexo F** — `appendix_f.md`

- Registro de cambios técnicos y editoriales aplicados durante el desarrollo

**Anexo G** — `appendix_g.md`

- 2041 tests en 184 archivos (unit, integration, e2e, atomic, security, performance)
- Pirámide: 65.9 % unit, 16.5 % integration, 13.8 % e2e (score 94.3/100)
- Coverage: 84.6 % líneas, 73.2 % ramas
- 49 test cases E2E (TC-00 a TC-33, TC-KPI-01 a 06)
- 9 marcadores pytest
- Quality gates: ruff 0 issues, mypy 0 errors, bandit 0 issues, pip-audit 0 vulns
- Mutation testing: 51.8 % (13969 mutantes, 5603 killed)

**Anexo H** — `appendix_h.md`

- 13 diagramas Mermaid canónicos
- Arquitectura: alto nivel, despliegue Docker, hexagonal, contexto C4
- Flujos: E2E alertas, árbol decisión playbook, integración API
- Gestión: Gantt objetivos SMART, roadmap semanal, matriz riesgos
