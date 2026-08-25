# TRABAJO FIN DE MÁSTER

## Laboratorio SOAR para Respuesta ante Ransomware: Diseño, Implementación y Evaluación de una Plataforma de Orquestación, Automatización y Respuesta de Seguridad

**Autor**: [Nombre del Autor] - *Completar con nombre completo del autor del TFM*  
**Director/a**: [Nombre del Director/a] - *Completar con nombre completo y título académico del director/a del TFM*  
**Universidad**: [Nombre de la Universidad] - *Completar con nombre oficial de la universidad donde se presenta el
TFM*  
**Máster**: Máster en Ciberseguridad - *Completar si el máster tiene un nombre diferente*  
**Año Académico**: 2024-2025 - *Ajustar según el año académico correspondiente*  
**Fecha de Presentación**: [Fecha de defensa] - *Completar con fecha programada para la defensa del TFM*


## ÍNDICE GENERAL

### Página de Título

### Agradecimientos

### Índice General

### Resumen

### Abstract

### Lista de Abreviaturas

### Lista de Tablas

### Lista de Figuras

### CAPÍTULO 1: INTRODUCCIÓN

1.1. Contexto Actual de la Ciberseguridad
1.2. Problemática del Ransomware
1.3. Limitaciones de la Respuesta Manual a Incidentes
1.4. Justificación del Estudio
1.5. Hipótesis de Trabajo
1.6. Objetivos de la Investigación
1.7. Alcance y Limitaciones del Estudio
1.8. Estructura del Trabajo

### CAPÍTULO 2: ESTADO DEL ARTE Y MARCO TEÓRICO

2.1. Progresión del Ransomware
2.1.1. Primera Generación (2013-2016)
2.1.2. Segunda Generación (2016-2019)
2.1.3. Tercera Generación (2019-2022)
2.1.4. Cuarta Generación (2022-Presente)
2.2. Plataformas SOAR: Conceptos y Fundamentos
2.2.1. Definición y Componentes
2.2.2. Ciclo de Vida de la Respuesta a Incidentes
2.2.3. Tipos de Automatización en SOAR
2.3. Análisis Comparativo de Plataformas SOAR
2.3.1. TheHive: Características y Capacidades
2.3.2. Cortex: Motor de Análisis y Analyzers
2.3.3. Shuffle: Orquestación Visual y Workflows
2.3.4. Soluciones Comerciales vs Open Source
2.4. Marco Teórico de Automatización en Respuesta a Incidentes
2.4.1. Principios de Diseño de Playbooks
2.4.2. Métricas de Eficacia (MTTR, MTTD, etc.)
2.4.3. Modelos de Madurez en Respuesta a Incidentes

### CAPÍTULO 3: METODOLOGÍA

3.1. Enfoque Metodológico Adoptado
3.1.1. Investigación Aplicada con Desarrollo Tecnológico
3.1.2. Metodología Ágil con Principios DevSecOps
3.2. Fases del Proyecto
3.2.1. Fase I: Investigación y Análisis de Requisitos
3.2.2. Fase II: Diseño Arquitectónico
3.2.3. Fase III: Desarrollo e Implementación
3.2.4. Fase IV: Pruebas y Validación
3.2.5. Fase V: Optimización y Documentación
3.3. Tecnologías y Herramientas Utilizadas
3.3.1. Infraestructura como Código (IaC)
3.3.2. Contenerización con Docker
3.3.3. Automatización con Scripts y APIs
3.4. Diseño Experimental
3.4.1. Definición de Variables y Métricas
3.4.2. Diseño de Escenarios de Prueba
3.4.3. Procedimientos de Recolección de Datos
3.5. Consideraciones Éticas y de Seguridad

### CAPÍTULO 4: DISEÑO Y ARQUITECTURA DEL LABORATORIO

4.1. Arquitectura General del Sistema
4.1.1. Vista Lógica de Componentes
4.1.2. Vista de Despliegue
4.1.3. Vista de Datos
4.2. Diseño Detallado de Componentes
4.2.1. TheHive: Gestión de Casos y Colaboración
4.2.2. Cortex: Análisis de Indicadores de Compromiso
4.2.3. Shuffle: Orquestación y Automatización
4.2.4. Bases de Datos: Elasticsearch, Redis y MariaDB
4.3. Flujo de Respuesta Automatizada
4.3.1. Recepción y Procesamiento de Alertas
4.3.2. Creación y Gestión de Casos
4.3.3. Análisis de IoCs y Evidencias
4.3.4. Ejecución de Acciones de Contención
4.3.5. Notificación y Cierre de Incidentes
4.4. Diseño de Datos y Esquemas
4.4.1. Esquema de Alertas Ransomware
4.4.2. Modelo de Datos de Casos
4.4.3. Estructura de IoCs y Analizadores
4.5. Consideraciones de Seguridad y Privacidad
4.5.1. Principio de Mínimo Privilegio
4.5.2. Segmentación de Red y Aislamiento
4.5.3. Gestión de Secretos y Credenciales

### CAPÍTULO 5: IMPLEMENTACIÓN Y DESARROLLO

5.1. Configuración de Infraestructura
5.1.1. Docker Compose: Definición de Servicios
5.1.2. Gestión de Volúmenes y Persistencia
5.1.3. Redes Docker y Comunicación entre Servicios
5.2. Desarrollo de Playbooks de Automatización
5.2.1. Diseño del Flujo Principal de Ransomware
5.2.2. Implementación de Acciones de Análisis
5.2.3. Desarrollo de Acciones de Contención
5.2.4. Integración de Notificaciones y Reportes
5.3. Integración de Componentes SOAR
5.3.1. Conexión TheHive-Cortex
5.3.2. Integración Shuffle-TheHive
5.3.3. Configuración de Analyzers en Cortex
5.3.4. Personalización de Workflows en Shuffle
5.4. Automatización de Despliegue y Operaciones
5.4.1. Scripts de Orquestación
5.4.2. Makefile y Automatización de Tareas
5.4.3. Gestión de Secretos y Configuración
5.5. Implementación de Mejoras de Seguridad
5.5.1. Configuración de HTTPS/TLS
5.5.2. Implementación de Firewall de Red
5.5.3. Escaneo Automatizado de Vulnerabilidades

### CAPÍTULO 6: PRUEBAS Y VALIDACIÓN EXPERIMENTAL

6.1. Diseño Experimental
6.1.1. Definición de Hipótesis Experimentales
6.1.2. Variables Independientes y Dependientes
6.1.3. Procedimientos de Control de Variables
6.2. Escenarios de Prueba
6.2.1. Escenario 1: Incidente Malicioso Real
6.2.2. Escenario 2: Falso Positivo (Alerta Benigna)
6.2.3. Escenario 3: Condiciones de Carga Extrema
6.2.4. Escenario 4: Fallos de Componentes
6.3. Recolección y Procesamiento de Datos
6.3.1. Métricas de Tiempo de Respuesta
6.3.2. Métricas de Tasa de Éxito
6.3.3. Métricas de Uso de Recursos
6.3.4. Registro de Eventos y Logs
6.4. Análisis Estadístico de Resultados
6.4.1. Análisis Descriptivo de MTTR
6.4.2. Pruebas de Hipótesis con Tests Estadísticos
6.4.3. Análisis de Correlaciones
6.4.4. Visualización de Resultados
6.5. Validación de Resultados
6.5.1. Comparación con Línea Base Manual
6.5.2. Análisis de Significancia Estadística
6.5.3. Validación de Hipótesis de Trabajo

### CAPÍTULO 7: ANÁLISIS DE RESULTADOS Y DISCUSIÓN

7.1. Presentación de Resultados Cuantitativos
7.1.1. Métricas de Rendimiento del Sistema
7.1.2. Análisis de Tiempo Medio de Respuesta (MTTR)
7.1.3. Tasa de Éxito de Automatización
7.1.4. Precisión y Tasa de Falsos Positivos
7.2. Análisis Cualitativo de Resultados
7.2.1. Fortalezas Identificadas del Sistema
7.2.2. Debilidades y Limitaciones Detectadas
7.2.3. Factores Críticos de Éxito
7.2.4. Lecciones Aprendidas durante la Implementación
7.3. Discusión de Resultados en Contexto del Estado del Arte
7.3.1. Comparación con Estudios Previos
7.3.2. Contribuciones al Campo del Conocimiento
7.3.3. Implicaciones Prácticas para Organizaciones
7.3.4. Validación de la Hipótesis de Trabajo
7.4. Análisis de Mejoras Implementadas
7.4.1. Evaluación de las 44 Mejoras Identificadas
7.4.2. Impacto de las Mejoras Críticas de Seguridad
7.4.3. Beneficios de las Mejoras de Calidad de Código
7.4.4. Mejoras Operativas y de Monitoreo

### CAPÍTULO 8: CONCLUSIONES Y TRABAJO FUTURO

8.1. Resumen de Conclusiones Principales
8.1.1. Cumplimiento de Objetivos Planteados
8.1.2. Contribuciones Teóricas y Prácticas
8.1.3. Implicaciones para la Práctica Profesional
8.1.4. Limitaciones del Estudio Realizado
8.2. Trabajo Futuro y Líneas de Investigación
8.2.1. Mejoras Técnicas Inmediatas
8.2.2. Investigaciones Longitudinales Propuestas
8.2.3. Desarrollo de Capacidades de Machine Learning
8.2.4. Expansión a Otros Tipos de Incidentes
8.3. Recomendaciones para Organizaciones
8.3.1. Guía de Implementación Práctica
8.3.2. Consideraciones de Adopción Organizacional
8.3.3. Métricas de Éxito y KPIs Recomendados
8.3.4. Mejores Prácticas de Mantenimiento y Progresión

### REFERENCIAS BIBLIOGRÁFICAS

### ANEXOS

Anexo A: Configuración Completa de Docker Compose
Anexo B: Playbooks de Automatización en Shuffle
Anexo C: Scripts de Orquestación y Automatización
Anexo D: Resultados Detallados de Pruebas Experimentales
Anexo E: Métricas y Análisis Estadístico Completo
Anexo F: Guía de Instalación y Configuración
Anexo F2: Validación Experimental y Métricas de Calidad
Anexo G: Documentación de Mejoras Implementadas
Anexo H: Manual de Usuario del Laboratorio
Anexo I: Estrategia de Testing y Quality Assurance
Anexo J: Diagramas de Arquitectura y Flujos (Mermaid)


## RESUMEN

Este Trabajo Fin de Máster presenta el diseño, implementación y evaluación de un laboratorio SOAR (Security
Orchestration, Automation and Response) especializado en respuesta a ransomware. La investigación parte de la necesidad
de reducir el Tiempo Medio de Respuesta (MTTR) ante amenazas cuya frecuencia ha crecido según reportes de inteligencia
de amenazas (Verizon, 2024; CrowdStrike, 2024).

La metodología combina investigación aplicada con desarrollo tecnológico, aplicando principios de Infraestructura como
Código (IaC) y metodologías ágiles con práctica DevSecOps. El proyecto se estructuró en cinco fases: investigación y
análisis de requisitos, diseño arquitectónico, desarrollo e implementación, pruebas y validación, y optimización y
documentación.

El laboratorio integra tres plataformas SOAR open source: TheHive (TheHive Project, 2024) para gestión de casos, Cortex (Cortex Project, 2024) para análisis de IoCs, y
Shuffle (Shuffle Tools, 2024) para orquestación de flujos. La arquitectura usa Docker y Docker Compose (Docker Inc., 2024). El código Python (`src/soar_lab/`)
implementa arquitectura hexagonal con interfaces en `domain/ports/` (481 líneas en 4 módulos) e implementaciones desacopladas,
manteniendo la lógica de negocio independiente de la infraestructura técnica.

Los resultados muestran una reducción del MTTR de 3600 segundos (procesos manuales) a 277.15 segundos (automatizados), una
mejora del 92.3%. La tasa de éxito alcanzó el 100%, con una tasa de contención del 92.0% (score promedio 96.2/100). El análisis de métricas se
realiza con `AnalyticsService` y `KPIAnalyzer`, que usan `StatisticalCalculator` para calcular percentiles (p50, p90,
p95, p99) desde los logs.

Se implementaron 44 mejoras en seguridad, calidad de código, automatización, monitoreo y documentación. Estos cambios
elevaron el sistema desde un prototipo inicial hasta una solución apta para entornos de producción.

Las conclusiones confirman la hipótesis: la automatización SOAR reduce el MTTR y mejora la consistencia en la respuesta
a ransomware. El trabajo aporta evidencia empírica cuantitativa sobre el efecto de la automatización en tiempos de
respuesta.


## ABSTRACT

This Master's Thesis presents the design, implementation, and evaluation of a SOAR (Security Orchestration, Automation,
and Response) laboratory specialized in ransomware incident response. The research addresses the need to reduce Mean
Time to Respond (MTTR) for threats whose frequency has increased 67% according to threat intelligence
reports (CrowdStrike, 2024), with ransomware representing 23% of total security incidents (CrowdStrike, 2024).

The adopted methodology combines applied research with technological development, following Infrastructure as Code (IaC)
principles and agile methodologies with DevSecOps approach. The project was structured in five phases: research and
requirements analysis, architectural design, development and implementation, testing and validation, and optimization
and documentation.

The implemented laboratory integrates three SOAR open source platforms: TheHive (TheHive Project, 2024) for case management, Cortex (Cortex Project, 2024) for analysis
of indicators of compromise (IoCs), and Shuffle (Shuffle Tools, 2024) for visual orchestration of response flows. The deployment architecture
is containerized with Docker and orchestrated using Docker Compose (Docker Inc., 2024), enabling reproducible and scalable deployment. The
Python codebase (`src/soar_lab/`) implements a hexagonal architecture (ports and adapters) with interfaces defined in
`domain/ports/` (481 lines across 4 modules) and concrete implementations in the infrastructure layer, allowing business
logic to remain independent of technical implementations.

Experimental results demonstrate a significant MTTR reduction, from an average of 3600 seconds in manual processes to 277.15
seconds with implemented automation, representing a 92.3% improvement. The automation success rate reached 100%, with
92.0% threat containment rate (average score 96.2/100). Metrics analysis is performed by `AnalyticsService` and `KPIAnalyzer`
services, which utilize `StatisticalCalculator` to compute percentiles (p50, p90, p95, p99) and statistical metrics from
execution logs.

The work includes 44 improvements in security, code quality, operational automation, monitoring, and documentation.
These changes elevated the system from an initial prototype to a solution suitable for production environments.

The conclusions confirm the hypothesis: SOAR automation reduces MTTR and improves consistency in ransomware incident
response. The work provides quantitative empirical evidence on the effect of automation on response times.


## LISTA DE ABREVIATURAS

- **API**: Application Programming Interface
- **CI/CD**: Continuous Integration/Continuous Deployment
- **EDR**: Endpoint Detection and Response
- **IaC**: Infrastructure as Code
- **IoC**: Indicator of Compromise
- **KPI**: Key Performance Indicator
- **MTTD**: Mean Time to Detect
- **MTTR**: Mean Time to Respond
- **MTTI**: Mean Time to Investigate
- **MTTC**: Mean Time to Contain
- **SIEM**: Security Information and Event Management
- **SOAR**: Security Orchestration, Automation, and Response
- **TFM**: Trabajo Fin de Máster
- **XDR**: Extended Detection and Response


## LISTA DE TABLAS

### Tabla 1.1: Comparativa de Plataformas SOAR

### Tabla 2.1: Progresión de Generaciones de Ransomware

### Tabla 3.1: Fases y Duración del Proyecto

### Tabla 4.1: Componentes del Laboratorio SOAR

### Tabla 5.1: Configuración de Servicios Docker

### Tabla 6.1: Diseño Experimental y Variables

### Tabla 7.1: Resultados de Métricas de Rendimiento

### Tabla 7.2: Análisis de las 44 Mejoras Implementadas

### Tabla 8.1: Comparación de MTTR Manual vs Automatizado


## LISTA DE FIGURAS

### Figura 1.1: Arquitectura General del Laboratorio SOAR

### Figura 2.1: Ciclo de Vida de Respuesta a Incidentes

### Figura 3.1: Metodología de Desarrollo Ágil

### Figura 4.1: Flujo de Respuesta Automatizada

### Figura 5.1: Diagrama de Despliegue Docker

### Figura 6.1: Diseño Experimental de Pruebas

### Figura 7.1: Gráficos de Resultados de MTTR

### Figura 8.1: Comparación Visual de Mejoras


## CAPÍTULO 1: INTRODUCCIÓN

El contenido completo de este capítulo se encuentra en el archivo `introduction.md`, que incluye:

### 1.1. Contexto Actual de la Ciberseguridad

- Incremento del 67% en incidentes de seguridad (CrowdStrike, 2024)
- Ransomware representa el 23% del total de incidentes (CrowdStrike, 2024)
- Las organizaciones reciben un promedio de 22,111 alertas de seguridad por semana, de las cuales solo el 35% son investigadas (IBM Security, 2024)

### 1.2. Problemática del Ransomware

El ransomware actual usa encriptación AES-256/RSA-4096, propagación automática, doble extorsión y RaaS (Al-Momani et al., 2024), con técnicas MITRE ATT&CK T1486 (MITRE, 2025). El coste promedio por brecha de datos en 2024 fue de $4.88 millones (IBM Security, 2024), con un tiempo medio de identificación y contención de 297 días.

### 1.3. Limitaciones de la Respuesta Manual

- Tiempo de respuesta elevado: 3600 segundos promedio (baseline manual), alta variabilidad
- Falta de estandarización entre equipos
- Sobrecarga de personal y burnout
- Errores humanos en procedimientos complejos

### 1.4. Justificación del Estudio

La justificación combina relevancia académica (validación empírica de SOAR), aplicación profesional (solución práctica para organizaciones) y viabilidad técnica (herramientas open source maduras, Docker, experiencia previa).

### 1.5. Hipótesis de Trabajo

- **Hipótesis Principal**: SOAR reduce el MTTR en al menos un 50 % mediante automatización
- **Hipótesis Secundarias**: (1) Mejora consistencia, (2) Integración multi-herramienta superior, (3) KPIs permiten
  optimización iterativa

### 1.6. Objetivos de la Investigación

- **Objetivo General**: Diseñar, implementar y evaluar laboratorio SOAR funcional
- **Objetivos Específicos**: Arquitectura escalable, flujo automatizado, validación con métricas, documentación
  reproducible, identificación de mejoras

### 1.7. Alcance y Limitaciones

- **Alcance**: Laboratorio completo con TheHive, Cortex, Shuffle; playbooks especializados; evaluación experimental
- **Limitaciones**: Entorno de laboratorio (no producción), dataset de 50 ejecuciones, dependencia de APIs externas,
  duración de 12 semanas

### 1.8. Estructura del Trabajo

- Capítulos 1-8: Introducción, Estado del arte, Metodología, Diseño, Implementación, Pruebas, Análisis, Conclusiones


## CAPÍTULO 2: ESTADO DEL ARTE Y MARCO TEÓRICO

El contenido completo de este capítulo se encuentra en el archivo `state_of_the_art.md`, que incluye la progresión del ransomware a través de sus cuatro generaciones (2013-2024), análisis de plataformas SOAR (definiciones, componentes, ciclo de vida de respuesta), comparativa detallada de TheHive, Cortex y Shuffle vs soluciones comerciales, marco teórico sobre diseño de playbooks y métricas de eficacia (MTTR, MTTD), y modelos de madurez en respuesta a incidentes.


## CAPÍTULO 3: METODOLOGÍA

El contenido completo de este capítulo se encuentra en el archivo `objectives_and_methodology.md`, que incluye el método (investigación aplicada con desarrollo tecnológico), metodología ágil con principios DevSecOps, las 5 fases del proyecto (investigación, diseño, desarrollo, pruebas y optimización), tecnologías y herramientas utilizadas (IaC, Docker, scripts y APIs), diseño experimental con definición de variables y métricas, y consideraciones éticas y de seguridad.


## CAPÍTULO 4: DISEÑO Y ARQUITECTURA DEL LABORATORIO

El contenido completo de este capítulo se encuentra en el archivo `specific_development.md` (secciones 4.1.2.1-4.1.2.6), que incluye la arquitectura general del sistema con vista lógica de componentes, arquitectura hexagonal del código Python (`src/soar_lab/`), diseño de componentes (TheHive, Cortex, Shuffle, bases de datos), flujo de respuesta automatizada desde recepción de alertas hasta cierre, diseño de datos y esquemas (alertas ransomware, IoCs, analizadores), y consideraciones de seguridad (mínimo privilegio, segmentación de red, gestión de secretos).


## CAPÍTULO 5: IMPLEMENTACIÓN Y DESARROLLO

El contenido completo de este capítulo se encuentra en los archivos `specific_development.md` y `appendix_a.md`, que incluyen configuración de infraestructura con Docker Compose, desarrollo de playbooks de automatización para ransomware, conexión de componentes SOAR (TheHive-Cortex-Shuffle), scripts de orquestación y automatización (`scripts/setup/`, `src/soar_lab/application/use_cases/`, `src/soar_lab/domain/services/`, `src/soar_lab/infrastructure/monitoring/`), e implementación de mejoras de seguridad (TLS 1.3, firewall, hardening).


## CAPÍTULO 6: PRUEBAS Y VALIDACIÓN EXPERIMENTAL

El contenido completo de este capítulo se encuentra en el archivo `specific_development.md` (secciones 4.1.3.1-4.1.3.6), que incluye el diseño experimental con hipótesis H0 y H1, variables (independiente: tipo de respuesta; dependiente: MTTR; controladas: entorno, dataset), escenarios de prueba (alerta maliciosa `tests/e2e/TC-01/test_malicious.py`, falso positivo benigno `tests/e2e/TC-02/test_benign.py`, casos de borde `tests/e2e/TC-03/test_edge_cases.py`, flujo E2E completo `tests/integration/test_app_e2e.py`), métricas recolectadas (MTTR, tasa de éxito, uso de recursos, logs de ejecución), análisis estadístico (reducción del 92.3% en MTTR de 3600s a 277.15s, 50 ejecuciones, score promedio 96.2), y validación de hipótesis mediante análisis descriptivo (percentiles, desviación estándar, CV).


## CAPÍTULO 7: ANÁLISIS DE RESULTADOS Y DISCUSIÓN

El contenido completo de este capítulo se encuentra en los archivos `specific_development.md`, `appendix_e.md` y `appendix_c.md`, que incluyen resultados cuantitativos (MTTR de 3600s a 277.15s con 92.3% de reducción, tasa de éxito 100%, tasa de contención 92.0%, falsos negativos 8.0%), métricas de rendimiento (disponibilidad 99.7%, throughput 125 alertas/hora, score promedio 96.2/100), análisis cualitativo (fortalezas, debilidades, factores críticos de éxito, lecciones aprendidas), discusión en contexto del estado del arte (comparación con estudios previos, contribuciones al campo), y análisis de las 44 mejoras implementadas por categoría (seguridad, calidad de código, automatización, monitoreo).


## CAPÍTULO 8: CONCLUSIONES Y TRABAJO FUTURO

El contenido completo de este capítulo se encuentra en el archivo `conclusions_and_future_work.md`, que incluye conclusiones principales (cumplimiento de objetivos, contribuciones teóricas y prácticas), implicaciones para PYMEs, grandes corporaciones y ámbito educativo, limitaciones del estudio (entorno de laboratorio, dataset de 50 ejecuciones, duración de 12 semanas), trabajo futuro (mejores técnicas como Redis cluster, Kubernetes, Zero Trust, e investigaciones longitudinales), desarrollo de ML (detección predictiva, clasificación automática con NLP, optimización con Reinforcement Learning), expansión a APTs, insider threat y supply chain, y recomendaciones para organizaciones (guía de implementación en 4 fases, KPIs recomendados).


## REFERENCIAS BIBLIOGRÁFICAS

Las referencias bibliográficas completas (125 referencias) se encuentran detalladas en el archivo
`bibliographic_references.md`, organizadas por categorías:

- **Artículos Académicos y Papers** (5 referencias) - (Al-Momani et al., 2024) Al-Momani et al., (Kinyua & Awuah, 2021) Kinyua & Awuah, (Mohammad & Lakshmisri, 2018) Mohammad & Lakshmisri,
  (Obuse et al., 2023) Obuse et al., (Quintero Tamayo et al., 2023) Quintero Tamayo et al.
- **Informes de Industria y Threat Intelligence** (8 referencias) - (IBM Security, 2024) IBM Security, (Verizon, 2024) Verizon DBIR, (CrowdStrike, 2024) CrowdStrike,
  (Mandiant, 2024) Mandiant, (Sophos, 2024) Sophos, (CISA, 2023) CISA, (MITRE, 2025) MITRE ATT&CK, (Microsoft, 2024) Microsoft
- **Documentación Técnica y Especificaciones** (17 referencias) - (TheHive Project, 2024) TheHive, (Cortex Project, 2024) Cortex, (Shuffle Tools, 2024) Shuffle, (Elastic, 2024)
  Elasticsearch, (Docker Inc., 2024) Docker, (Nginx, 2024) Nginx, (Prometheus, 2024) Prometheus, (Grafana Labs, 2024) Grafana, (MITRE Corporation, 2024) MITRE ATT&CK, (NIST, 2024a) NIST Framework, (FIRST, n.d.) FIRST, [36a-f] MISP, Redis, Loki, Promtail, Tenzir, OpenSearch
- **Frameworks y Herramientas de Desarrollo** (11 referencias) - (FastAPI, 2024) FastAPI, (Pydantic, 2024) Pydantic, (pytest, 2024) pytest, (pytest-cov, 2024) pytest-cov, (Astral, 2024) Ruff, (Python Software Foundation, 2024) mypy, (PyCQA, 2024a) radon, (PyCQA, 2024b) bandit, (jendrikse, 2024) vulture, (mutmut, 2024) mutmut, (pip-audit, 2024) pip-audit
- **Estándares y Normativas** (10 referencias) - (ISO/IEC, 2022) ISO/IEC 27001:2022, (ISO/IEC, 2023) ISO/IEC 27002:2023, (NIST, 2023) NIST SP
  800-61, (NIST, 2024b) NIST SP 800-150, (ENISA, 2023) ENISA, (CIS, 2024) CIS Controls, (GDPR, 2018) GDPR, (CCPA, 2020) CCPA, (HIPAA, 2023) HIPAA, (NIST, 2025) NIST SP 800-61r3, (OASIS, 2023) OASIS CACAO
- **Libros y Capítulos de Libros** (1 referencia) - (Atluri & Warner, 2008) Atluri & Warner
- **Tesis Doctorales y Trabajos de Investigación** (1 referencia) - (Núñez Fernández, 2023) Núñez Fernández (UDC)
- **Conferencias y Proceedings** (2 referencias) - (Schlette et al., 2024) Schlette et al., (Stevens et al., 2022) Stevens et al.
- **Repositorios de Código y Proyectos Open Source** (10 referencias) - TheHive, Cortex, Shuffle, Elasticsearch,
  Prometheus, Grafana, Docker, Nginx, MITRE ATT&CK, Sigma
- **Recursos del Proyecto SOAR Ransomware Lab** (9 referencias) - Repositorio GitHub, documentación, scripts, módulos
  Python, suite de pruebas, configuración Docker, playbooks, Makefile, resultados
- **Normas y Especificaciones Técnicas** (6 referencias) - RFC 8446 (TLS 1.3), RFC 7519 (JWT), RFC 2616 (HTTP/1.1), RFC 3986 (URI), ISO/IEC 27035, Agrawal & Boneh (2024)
- **Fuentes Externas de Threat Intelligence** (3 referencias) - (VirusTotal, 2024) VirusTotal, (AbuseIPDB, 2024) AbuseIPDB, (Wazuh, 2024) Wazuh

**Nota**: Todas las referencias fueron verificadas en 2024-2025. Los DOIs proporcionan acceso directo a los
documentos académicos cuando están disponibles.


## ANEXOS

Los anexos técnicos completos se encuentran en los siguientes archivos del proyecto:

- **Anexo A: Configuración Completa de Docker Compose** - Ver `appendix_a.md` (instantánea de configuración YAML; versión
  canónica en `infra/docker/compose/` y `.env.full`)
- **Anexo B: Playbooks de Automatización** - Ver `appendix_b.md` (Workflow SOAR completo: 46 nodos, 60 ramas,
  25 scripts Python embebidos, modelo de scoring 0-100, ramas contain/observe)
- **Anexo C: Scripts de Orquestación** - Ver `scripts/setup/` (`gen_certs.sh`, `check_deps.sh`,
  `init_thehive.py`, `init_shuffle_webhook.py`, 20 scripts de automatización)
  `src/soar_lab/infrastructure/security/` (`setup_firewall.sh`, `scan_vulnerabilities.sh`).
- **Anexo D: Resultados Experimentales Detallados** - Ver `appendix_e.md` (Visualizaciones ASCII de métricas,
  gráficos de MTTR, análisis estadístico)
- **Anexo E: Métricas y Análisis Estadístico** - Ver `appendix_c.md` (Tablas comparativas de plataformas,
  resultados experimentales, KPIs)
- **Anexo F: Guía de Instalación** - Ver `docs/` (Documentación de arquitectura, operaciones, integraciones)
- **Anexo F2: Validación Experimental** - Ver `appendix_f2.md` (Quality Score 92.2/100,
  HPR 96.0/100, 2041 tests, 38 endpoints API, 18 servicios, 20 objetivos SMART, mutation testing 51.8%)
- **Anexo G: Documentación de Mejoras** - Ver `appendix_g.md` (Registro de 44 mejoras implementadas)
- **Anexo H: Manual de Usuario** - Ver `docs/04-operations.md` (Operaciones del laboratorio:
  configuración, backups, troubleshooting, healthchecks) y `docs/01-getting-started.md` (instalación)
- **Anexo I: Estrategia de Testing** - Ver `appendix_i.md` (2041 tests, pirámide, 9 marcadores,
  coverage 84.6%, quality gates, 49 TCs E2E, mutation testing 51.8% sobre 11 050 mutantes, flujo canónico)
- **Anexo J: Diagramas Mermaid** - Ver `appendix_j.md` (13 diagramas canónicos: arquitectura
  Docker, hexagonal, C4, secuencias E2E, árbol decisión, Gantt SMART, matriz riesgos, GMinst4ll)

**Nota**: Todo el código fuente, configuraciones y documentación técnica están disponibles en el repositorio del
proyecto bajo los directorios `src/`, `infra/`, `docs/` y `tests/`.


## DECLARACIÓN DE ORIGINALIDAD

Yo, [Nombre del Autor] - *Completar con nombre completo del autor*, declaro que este Trabajo Fin de Máster es original y
ha sido realizado por mí bajo la dirección de [Nombre del Director/a] - *Completar con nombre completo del director/a*.
Las fuentes utilizadas han sido debidamente citadas y referenciadas según las normas académicas establecidas. Esta
declaración debe estar firmada y fechada en el momento de la defensa del TFM.

**Firma**: ________________________  
**Fecha**: ___ de ___________ de 2025 - *Completar con fecha de defensa*


## AGRADECIMIENTOS

El contenido completo de los agradecimientos se encuentra en el archivo `acknowledgments.md`, que incluye:

- Agradecimientos al director/a del TFM por su orientación y apoyo
- Al cuerpo docente del Máster en Ciberseguridad
- A la comunidad open source de TheHive, Cortex y Shuffle
- A profesionales de ciberseguridad del sector
- A familia, compañeros y amigos por su apoyo personal
- Reconocimiento de limitaciones y compromiso futuro

