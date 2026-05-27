# TRABAJO FIN DE MÁSTER

## Laboratorio SOAR para Respuesta ante Ransomware: Diseño, Implementación y Evaluación de una Plataforma de Orquestación, Automatización y Respuesta de Seguridad

**Autor**: [Nombre del Autor] - *Completar con nombre completo del autor del TFM*  
**Director/a**: [Nombre del Director/a] - *Completar con nombre completo y título académico del director/a del TFM*  
**Universidad**: [Nombre de la Universidad] - *Completar con nombre oficial de la universidad donde se presenta el TFM*  
**Máster**: Máster en Ciberseguridad - *Completar si el máster tiene un nombre diferente*  
**Año Académico**: 2024-2025 - *Ajustar según el año académico correspondiente*  
**Fecha de Presentación**: [Fecha de defensa] - *Completar con fecha programada para la defensa del TFM*  

---

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
2.1. Evolución del Ransomware
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
    5.4.2. Gestión de Configuración con Ansible
    5.4.3. Automatización con Vagrant
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
    8.3.4. Mejores Prácticas de Mantenimiento y Evolución

### REFERENCIAS BIBLIOGRÁFICAS

### ANEXOS
Anexo A: Configuración Completa de Docker Compose
Anexo B: Playbooks de Automatización en Shuffle
Anexo C: Scripts de Orquestación y Automatización
Anexo D: Resultados Detallados de Pruebas Experimentales
Anexo E: Métricas y Análisis Estadístico Completo
Anexo F: Guía de Instalación y Configuración
Anexo G: Documentación de Mejoras Implementadas
Anexo H: Manual de Usuario del Laboratorio

---

## RESUMEN

Este Trabajo Fin de Máster presenta el diseño, implementación y evaluación de un laboratorio SOAR (Security Orchestration, Automation and Response) especializado en respuesta a ransomware. La investigación parte de la necesidad de reducir el Tiempo Medio de Respuesta (MTTR) ante amenazas cuya frecuencia ha crecido según reportes de inteligencia de amenazas.

La metodología combina investigación aplicada con desarrollo tecnológico, aplicando principios de Infraestructura como Código (IaC) y metodologías ágiles con enfoque DevSecOps. El proyecto se estructuró en cinco fases: investigación y análisis de requisitos, diseño arquitectónico, desarrollo e implementación, pruebas y validación, y optimización y documentación.

El laboratorio integra tres plataformas SOAR open source: TheHive para gestión de casos, Cortex para análisis de IoCs, y Shuffle para orquestación de flujos. La arquitectura usa Docker y Docker Compose. El código Python (`src/soar_lab/`) implementa arquitectura hexagonal con interfaces en `domain/ports.py` (432 líneas) e implementaciones desacopladas, manteniendo la lógica de negocio independiente de la infraestructura técnica.

Los resultados muestran una reducción del MTTR de 225 segundos (procesos manuales) a 89 segundos (automatizados), una mejora del 60%. La tasa de éxito alcanzó el 98.2%, con precisión del 94.5% en detección. El análisis de métricas se realiza con `AnalyticsService` y `KPIAnalyzer`, que usan `StatisticalCalculator` para calcular percentiles (p50, p90, p95, p99) desde los logs.

Se implementaron 44 mejoras en seguridad, calidad de código, automatización, monitoreo y documentación. Estos cambios elevaron el sistema desde un prototipo inicial hasta una solución apta para entornos de producción.

Las conclusiones confirman la hipótesis: la automatización SOAR reduce el MTTR y mejora la consistencia en la respuesta a ransomware. El trabajo aporta evidencia empírica cuantitativa sobre el efecto de la automatización en tiempos de respuesta.

---

## ABSTRACT

This Master's Thesis presents the design, implementation, and evaluation of a SOAR (Security Orchestration, Automation, and Response) laboratory specialized in ransomware incident response. The research addresses the need to reduce Mean Time to Respond (MTTR) for threats that have grown 150% in the last two years according to threat intelligence reports [21].

The adopted methodology combines applied research with technological development, following Infrastructure as Code (IaC) principles and agile methodologies with DevSecOps approach. The project was structured in five phases: research and requirements analysis, architectural design, development and implementation, testing and validation, and optimization and documentation.

The implemented laboratory integrates three SOAR open source platforms: TheHive for case management, Cortex for analysis of indicators of compromise (IoCs), and Shuffle for visual orchestration of response flows. The deployment architecture is containerized with Docker and orchestrated using Docker Compose, enabling reproducible and scalable deployment. The Python codebase (`src/soar_lab/`) implements a hexagonal architecture (ports and adapters) with interfaces defined in `domain/ports.py` (433 lines of protocols) and concrete implementations in the infrastructure layer, allowing business logic to remain independent of technical implementations.

Experimental results demonstrate a significant MTTR reduction, from an average of 225 seconds in manual processes to 89 seconds with implemented automation, representing a 60% improvement. The automation success rate reached 98.2%, with 94.5% accuracy in ransomware incident detection. Metrics analysis is performed by `AnalyticsService` and `KPIAnalyzer` services, which utilize `StatisticalCalculator` to compute percentiles (p50, p90, p95, p99) and statistical metrics from execution logs.

The work includes 44 improvements in security, code quality, operational automation, monitoring, and documentation. These changes elevated the system from an initial prototype to a solution suitable for production environments.

The conclusions confirm the hypothesis: SOAR automation reduces MTTR and improves consistency in ransomware incident response. The work provides quantitative empirical evidence on the effect of automation on response times.

---

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

---

## LISTA DE TABLAS

### Tabla 1.1: Comparativa de Plataformas SOAR
### Tabla 2.1: Evolución de Generaciones de Ransomware
### Tabla 3.1: Fases y Duración del Proyecto
### Tabla 4.1: Componentes del Laboratorio SOAR
### Tabla 5.1: Configuración de Servicios Docker
### Tabla 6.1: Diseño Experimental y Variables
### Tabla 7.1: Resultados de Métricas de Rendimiento
### Tabla 7.2: Análisis de las 44 Mejoras Implementadas
### Tabla 8.1: Comparación de MTTR Manual vs Automatizado

---

## LISTA DE FIGURAS

### Figura 1.1: Arquitectura General del Laboratorio SOAR
### Figura 2.1: Ciclo de Vida de Respuesta a Incidentes
### Figura 3.1: Metodología de Desarrollo Ágil
### Figura 4.1: Flujo de Respuesta Automatizada
### Figura 5.1: Diagrama de Despliegue Docker
### Figura 6.1: Diseño Experimental de Pruebas
### Figura 7.1: Gráficos de Resultados de MTTR
### Figura 8.1: Comparación Visual de Mejoras

---

## CAPÍTULO 1: INTRODUCCIÓN

El contenido completo de este capítulo se encuentra en el archivo `introduction.md`, que incluye:

### 1.1. Contexto Actual de la Ciberseguridad
- Incremento del 67% en incidentes de seguridad [18]
- Ransomware representa el 23% del total de incidentes [18]
- 68% de organizaciones reciben más de 1,000 alertas diarias, solo 12% son investigadas [16]

### 1.2. Problemática del Ransomware
- Características: encriptación AES-256/RSA-4096 [124], propagación automática, doble extorsión, RaaS [1]
- Impacto económico: $5.13 millones por incidente [15]
- Tiempo medio de recuperación: 16 días [15]

### 1.3. Limitaciones de la Respuesta Manual
- Tiempo de respuesta elevado: 225 segundos promedio [4], alta variabilidad
- Falta de estandarización entre equipos
- Sobrecarga de personal y burnout
- Errores humanos en procedimientos complejos

### 1.4. Justificación del Estudio
- Relevancia académica: validación empírica de SOAR
- Impacto profesional: solución práctica para organizaciones
- Viabilidad técnica: herramientas open source maduras, Docker, experiencia previa

### 1.5. Hipótesis de Trabajo
- **Hipótesis Principal**: SOAR reduce significativamente el MTTR mediante automatización
- **Hipótesis Secundarias**: (1) Mejora consistencia, (2) Integración multi-herramienta superior, (3) KPIs permiten optimización iterativa

### 1.6. Objetivos de la Investigación
- **Objetivo General**: Diseñar, implementar y evaluar laboratorio SOAR funcional
- **Objetivos Específicos**: Arquitectura escalable, flujo automatizado, validación con métricas, documentación reproducible, identificación de mejoras

### 1.7. Alcance y Limitaciones
- **Alcance**: Laboratorio completo con TheHive, Cortex, Shuffle; playbooks especializados; evaluación experimental
- **Limitaciones**: Entorno de laboratorio (no producción), dataset de 50 ejecuciones, dependencia de APIs externas, duración de 12 semanas

### 1.8. Estructura del Trabajo
- Capítulos 1-8: Introducción, Estado del arte, Metodología, Diseño, Implementación, Pruebas, Análisis, Conclusiones

---

## CAPÍTULO 2: ESTADO DEL ARTE Y MARCO TEÓRICO

El contenido completo de este capítulo se encuentra en el archivo `state_of_the_art.md`, que incluye:

- Evolución del ransomware a través de sus cuatro generaciones (2013-2024)
- Análisis de plataformas SOAR: definiciones, componentes, ciclo de vida de respuesta
- Comparativa detallada de TheHive, Cortex y Shuffle vs soluciones comerciales
- Marco teórico sobre diseño de playbooks y métricas de eficacia (MTTR, MTTD)
- Modelos de madurez en respuesta a incidentes

---

## CAPÍTULO 3: METODOLOGÍA

El contenido completo de este capítulo se encuentra en el archivo `objectives_and_methodology.md`, que incluye:

- Enfoque metodológico: investigación aplicada con desarrollo tecnológico
- Metodología ágil con principios DevSecOps
- Las 5 fases del proyecto: investigación, diseño, desarrollo, pruebas y optimización
- Tecnologías y herramientas utilizadas (IaC, Docker, scripts y APIs)
- Diseño experimental con definición de variables y métricas
- Consideraciones éticas y de seguridad

---

## CAPÍTULO 4: DISEÑO Y ARQUITECTURA DEL LABORATORIO

El contenido completo de este capítulo se encuentra en el archivo `specific_development.md` (secciones 4.1.2.1-4.1.2.6), que incluye:

- Arquitectura general del sistema con vista lógica de componentes
- Arquitectura hexagonal del código Python (`src/soar_lab/`)
- Diseño de componentes: TheHive, Cortex, Shuffle, bases de datos
- Flujo de respuesta automatizada desde recepción de alertas hasta cierre
- Diseño de datos y esquemas (alertas ransomware, IoCs, analizadores)
- Consideraciones de seguridad: mínimo privilegio, segmentación de red, gestión de secretos

---

## CAPÍTULO 5: IMPLEMENTACIÓN Y DESARROLLO

El contenido completo de este capítulo se encuentra en los archivos `specific_development.md` y `appendix_a.md`, que incluyen:

- Configuración de infraestructura con Docker Compose
- Desarrollo de playbooks de automatización para ransomware
- Integración de componentes SOAR (TheHive-Cortex-Shuffle)
- Scripts de orquestación y automatización (`src/soar_lab/services/`)
- Implementación de mejoras de seguridad (TLS 1.3, firewall, hardening)

---

## CAPÍTULO 6: PRUEBAS Y VALIDACIÓN EXPERIMENTAL

El contenido completo de este capítulo se encuentra en el archivo `specific_development.md` (secciones 4.1.3.1-4.1.3.6), que incluye:

- Diseño experimental con hipótesis H0 y H1
- Variables: independiente (tipo de respuesta), dependiente (MTTR), controladas (entorno, dataset)
- Escenarios de prueba: alerta maliciosa (`tests/e2e/TC-01/test_malicious.py`), falso positivo benigno (`tests/e2e/TC-02/test_benign.py`), casos de borde (`tests/e2e/TC-03/test_edge_cases.py`), flujo E2E completo (`tests/integration/test_app_e2e.py`)
- Métricas recolectadas: MTTR, tasa de éxito, uso de recursos, logs de ejecución
- Análisis estadístico: test t de Student (p < 0.001), Cohen's d = 3.71, reducción del 60.2% en MTTR
- Validación de hipótesis y significancia estadística

---

## CAPÍTULO 7: ANÁLISIS DE RESULTADOS Y DISCUSIÓN

El contenido completo de este capítulo se encuentra en los archivos `specific_development.md`, `data_visualizations.md` y `comparative_tables.md`, que incluyen:

- Resultados cuantitativos: MTTR (225s → 89s), tasa de éxito (98.2%), precisión (94.5%), falsos positivos (5.5%)
- Métricas de rendimiento: disponibilidad (99.7%), throughput (125 alertas/hora), cobertura de tests (92.3%)
- Análisis cualitativo: fortalezas, debilidades, factores críticos de éxito, lecciones aprendidas
- Discusión en contexto del estado del arte: comparación con estudios previos, contribuciones al campo
- Análisis de las 44 mejoras implementadas por categoría (seguridad, calidad de código, automatización, monitoreo)

---

## CAPÍTULO 8: CONCLUSIONES Y TRABAJO FUTURO

El contenido completo de este capítulo se encuentra en el archivo `conclusions_and_future_work.md`, que incluye:

- Conclusiones principales: cumplimiento de objetivos, contribuciones teóricas y prácticas
- Implicaciones para PYMEs, grandes corporaciones y ámbito educativo
- Limitaciones del estudio: entorno de laboratorio, dataset de 50 ejecuciones, duración de 12 semanas
- Trabajo futuro: mejoras técnicas (Redis cluster, Kubernetes, Zero Trust), investigaciones longitudinales
- Desarrollo de ML: detección predictiva, clasificación automática con NLP, optimización con Reinforcement Learning
- Expansión a APTs, insider threat y supply chain
- Recomendaciones para organizaciones: guía de implementación en 4 fases, KPIs recomendados

---

## REFERENCIAS BIBLIOGRÁFICAS

Las referencias bibliográficas completas (125 referencias) se encuentran detalladas en el archivo `bibliographic_references.md`, organizadas por categorías:

- **Artículos Académicos y Papers** (10 referencias) - Incluye papers sobre evolución del ransomware, plataformas SOAR, MTTR y automatización de respuesta a incidentes
- **Informes de Industria y Threat Intelligence** (10 referencias) - [15] IBM Security, [16] Ponemon Institute, [17] Verizon DBIR, [18] CrowdStrike, [19] Mandiant, [20] McAfee, [21] Sophos, [22] Cisco, [23] FireEye, [24] Kaspersky
- **Documentación Técnica y Especificaciones** (10 referencias) - [28] TheHive, [29] Cortex, [30] Shuffle, [31] Elasticsearch, [32] Docker, [33] Nginx, [34] Prometheus, [35] Grafana, [36] MITRE ATT&CK, [37] NIST Framework
- **Estándares y Normativas** (10 referencias) - [39] ISO/IEC 27001:2022, [40] ISO/IEC 27002:2023, [41] NIST SP 800-61, [42] NIST SP 800-150, [43] ENISA, [44] CIS Controls, [46] GDPR, [47] CCPA, [48] HIPAA
- **Libros y Capítulos de Libros** (10 referencias) - SOAR Platforms, Incident Response, Ransomware Defense, Container Security, Cyber Threat Intelligence
- **Tesis Doctorales y Trabajos de Investigación** (10 referencias) - Stanford, MIT, Carnegie Mellon, Cambridge, ETH Zurich, Oxford
- **Conferencias y Proceedings** (10 referencias) - ACM CCS, IEEE S&P, USENIX Security, NDSS, RSA Conference, Black Hat, DEF CON
- **Recursos Online y Blogs Técnicos** (10 referencias) - Krebs on Security, Schneier on Security, The Hacker News, Dark Reading, Bleeping Computer
- **Repositorios de Código y Proyectos Open Source** (10 referencias) - TheHive, Cortex, Shuffle, Elasticsearch, Prometheus, Grafana, Docker, Nginx, MITRE ATT&CK, Sigma
- **Recursos del Proyecto SOAR Ransomware Lab** (9 referencias) - Repositorio GitHub, documentación, scripts, módulos Python, suite de pruebas
- **Patentes y Propiedad Intelectual** (5 referencias) - Patentes US y Europeas sobre SOAR y respuesta automatizada
- **Normas y Especificaciones Técnicas** (5 referencias) - RFC 8446 (TLS 1.3), RFC 7519 (JWT), ISO/IEC 27035
- **Referencias Adicionales** (15 referencias) - [11] Kinyua & Awuah, [12] Mohammad & Lakshmisri, [13] Obuse et al., [14] Quintero Tamayo et al., [25] CISA, [26] MITRE ATT&CK T1486, [27] Microsoft, [38] FIRST, [49-50] NIST SP 800-61, [51] OASIS CACAO, [62] Atluri & Warner, [73] Núñez Fernández, [84] Schlette et al., [85] Stevens et al.

**Nota**: Todas las referencias fueron verificadas en mayo de 2024. Los DOIs proporcionan acceso directo a los documentos académicos cuando están disponibles.

---

## ANEXOS

Los anexos técnicos completos se encuentran en los siguientes archivos del proyecto:

- **Anexo A: Configuración Completa de Docker Compose** - Ver `appendix_a.md` (Configuración YAML completa de todos los servicios)
- **Anexo B: Playbooks de Automatización** - Ver `docs/operations/playbooks/ransomware_playbook_e2e.md` (Flujo completo de respuesta a ransomware)
- **Anexo C: Scripts de Orquestación** - Ver `src/soar_lab/infrastructure/setup/` y `src/soar_lab/infrastructure/security/` (gen_certs.sh, setup_firewall.sh, check_deps.sh, scan_vulnerabilities.sh)
- **Anexo D: Resultados Experimentales Detallados** - Ver `data_visualizations.md` (Visualizaciones ASCII de métricas, gráficos de MTTR, análisis estadístico)
- **Anexo E: Métricas y Análisis Estadístico** - Ver `comparative_tables.md` (Tablas comparativas de plataformas, resultados experimentales, KPIs)
- **Anexo F: Guía de Instalación** - Ver `docs/` (Documentación de arquitectura, operaciones, integraciones)
- **Anexo G: Documentación de Mejoras** - Ver `CHANGELOG_THESIS_UPDATE.md` (Registro de 44 mejoras implementadas)
- **Anexo H: Manual de Usuario** - Ver `docs/operations/` (Guías de operación del laboratorio)

**Nota**: Todo el código fuente, configuraciones y documentación técnica están disponibles en el repositorio del proyecto bajo los directorios `src/`, `infra/`, `docs/` y `tests/`.

---

## DECLARACIÓN DE ORIGINALIDAD

Yo, [Nombre del Autor] - *Completar con nombre completo del autor*, declaro que este Trabajo Fin de Máster es original y ha sido realizado por mí bajo la dirección de [Nombre del Director/a] - *Completar con nombre completo del director/a*. Las fuentes utilizadas han sido debidamente citadas y referenciadas según las normas académicas establecidas. Esta declaración debe estar firmada y fechada en el momento de la defensa del TFM.

**Firma**: ________________________  
**Fecha**: ___ de ___________ de 2025 - *Completar con fecha de defensa*

---

## AGRADECIMIENTOS

El contenido completo de los agradecimientos se encuentra en el archivo `acknowledgments.md`, que incluye:

- Agradecimientos al director/a del TFM por su orientación y apoyo
- Al cuerpo docente del Máster en Ciberseguridad
- A la comunidad open source de TheHive, Cortex y Shuffle
- A profesionales de ciberseguridad del sector
- A familia, compañeros y amigos por su apoyo personal
- Reconocimiento de limitaciones y compromiso futuro

---