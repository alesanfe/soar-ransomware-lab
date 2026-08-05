# 3. Objetivos concretos y metodología de trabajo

Este capítulo define qué se quiere demostrar y cómo se organiza el desarrollo. El resultado esperado es un laboratorio
SOAR mínimo viable que ejecute un playbook E2E en dos escenarios y produzca métricas para la evaluación.

## 3.1. Objetivo general

Demostrar que un playbook SOAR automatizado reduce el tiempo de respuesta y mejora la consistencia y trazabilidad en la
gestión de alertas de ransomware. El entorno debe ser reproducible, usar herramientas open source y generar evidencias
verificables.

El objetivo se alcanza cuando el laboratorio ejecuta el flujo completo en dos escenarios (malicioso y benigno), cumple
los umbrales de rendimiento (p50 ≤ 120 s y p90 ≤ 180 s) y genera evidencias completas (logs, capturas y métricas).

## 3.2. Objetivos específicos

Para alcanzar el objetivo general, el trabajo se divide en objetivos específicos:

### 3.2.1. Objetivos Estratégicos

Los objetivos estratégicos se agrupan en cinco áreas: diseño arquitectónico, implementación funcional, validación
empírica, documentación reproducible y optimización iterativa.

- **Diseño Arquitectónico**

El objetivo es diseñar una arquitectura SOAR modular y reproducible basada en TheHive, Cortex y Shuffle. El criterio de
éxito incluye una arquitectura documentada con diagramas técnicos, especificaciones de integración definidas, un plan de
escalabilidad establecido y una configuración Docker Compose estructurada. Las evidencias se encuentran en
`docs/architecture/overview.md`, `docs/architecture/docker_architecture.md`, `docs/integrations/` e
`infra/docker/compose/`.

- **Implementación Funcional**

Este objetivo consiste en implementar un playbook E2E en Shuffle con integración entre TheHive, Cortex y Shuffle. Se
considera exitoso cuando hay un playbook funcional E2E en dos escenarios, una integración operativa sin intervención
manual, un simulador SIEM funcional y una lógica de contención simulada operativa. Las evidencias incluyen el playbook
en `docs/operations/playbooks/ransomware_playbook_e2e.md`, los scripts en
`src/soar_lab/simulator/simulate_alerts.py`, `src/soar_lab/infrastructure/messaging/send_alert.py`,
`src/soar_lab/application/use_cases/analytics_service.py` y los logs en `artifacts/logs/`.

- **Evaluación Experimental**

El objetivo es validar la eficacia mediante métricas cuantitativas como MTTR y tasa de éxito. Los criterios de éxito son
MTTR p50 ≤ 120s y p90 ≤ 180s, tasa de éxito ≥ 95%, un dataset de al menos 50 ejecuciones por escenario y un análisis
estadístico con significancia. Las evidencias se encuentran en `artifacts/results/`, los servicios de análisis en
`src/soar_lab/application/use_cases/`, el calculador estadístico en `src/soar_lab/domain/statistical_calculator.py`, el script de
cálculo en `src/soar_lab/data/calc_kpis.py`, los resultados en `artifacts/results/kpis.csv` y los tests en `tests/e2e/`
y `tests/integration/`.

- **Documentación Reproducible**

Este objetivo busca documentar exhaustivamente el proceso para facilitar la reproducción por terceros. El éxito se mide
por una guía de instalación y configuración completa, documentación de playbooks con contexto, validación de
reproducción mediante Makefile y documentación técnica completa. Las evidencias se encuentran en `docs/`,
`docs/operations/configuration_manual.md`, el Makefile, la documentación de la API en `docs/integrations/api_contracts.md` y el
sitio de documentación en `apps/docs-site/`.

- **Optimización Iterativa**

El objetivo es identificar e implementar mejoras en código, infraestructura y documentación. Los criterios de éxito
incluyen un análisis sistemático de mejoras, implementación de mejoras críticas de seguridad, validación sin regresiones
y métricas comparativas pre/post. Las evidencias consisten en un documento de análisis, los tests en `tests/`, los tests
de rendimiento en `tests/performance/` y los tests de seguridad en `tests/security/`.

### 3.2.2. Objetivos Operativos

Los objetivos operativos detallan los pasos de implementación:

- **Delimitar** el alcance del proyecto estableciendo inclusiones, exclusiones y restricciones de seguridad. El entorno
  no debe tener malware funcional ni dependencias externas complejas.

- **Definir** el flujo funcional del playbook E2E: etapas, entradas, salidas, evidencias y criterios de decisión para
  los escenarios benigno y malicioso.

- **Diseñar** la arquitectura en un host con Docker Compose, incluyendo servicios, dependencias, redes y volúmenes.

- **Verificar** que los servicios arrancan de forma estable tras el despliegue inicial.

- **Configurar** e integrar los componentes: TheHive para gestión de casos, Cortex para análisis y Shuffle para
  orquestación.

- **Construir** el mecanismo de ingesta de alertas por webhook y garantizar la validación del payload de entrada.

- **Implementar** la creación y actualización de casos en TheHive, incluyendo IoCs, etiquetas, estados y resúmenes.

- **Automatizar** el enriquecimiento de observables mediante analyzers en Cortex y establecer la lógica de decisión
  basada en umbral de score.

- **Simular** las acciones de contención y registrar evidencias en el caso sin cambios reales en sistemas productivos.

- **Implementar** integraciones simuladas: un SIEM simulado para emitir alertas y endpoints mock para EDR y firewall.

- **Medir** el rendimiento del flujo desde la alerta hasta la contención simulada y calcular los percentiles p50 y p90.

- **Generar** evidencias verificables: logs, capturas, trazas y métricas. Documentar el procedimiento para asegurar
  reproducibilidad.

- **Identificar** e implementar mejoras en código, infraestructura y documentación, priorizando las de seguridad.

**Criterios de cumplimiento**: el objetivo general se alcanza cuando el laboratorio ejecuta el flujo completo en dos
escenarios, cumple los umbrales de rendimiento y genera evidencias completas.

## 3.3. Metodología del trabajo

La metodología combina investigación aplicada con desarrollo tecnológico, siguiendo principios de DevSecOps. El proyecto
se estructura en cinco fases. Primero viene investigación y requisitos, que ocupa las semanas 1-2. Luego diseño
arquitectónico durante las semanas 3-4. Después desarrollo en las semanas 5-8. Luego pruebas y validación en las semanas
9-10. Finalmente optimización con documentación en las semanas 11-12.

El desarrollo empieza por definir el alcance y los requisitos. Se prioriza que el entorno sea reproducible y seguro,
además de permitir repetir ejecuciones bajo condiciones comparables. El criterio de éxito es medible: se evalúa la
ejecución del flujo en dos escenarios, las métricas dentro de umbral y la generación de evidencias verificables.

En cuanto al diseño arquitectónico, este usa una topología de despliegue en un host con Docker Compose. Los contratos de
integración especifican los puntos de conexión de cada componente, el mecanismo de autenticación y el formato de la
alerta. La lógica de decisión del playbook se puede ajustar mediante variables de configuración, como por ejemplo el
umbral de score de riesgo.

Una vez definido el diseño, se despliega el laboratorio y se verifica la conectividad entre componentes, el
almacenamiento de datos y la estabilidad. La integración sigue un orden incremental: primero TheHive, luego Cortex y
finalmente Shuffle como orquestador.

Tras las validaciones de integración, se construye el playbook E2E. El flujo incluye ingesta por webhook, validación de
datos, creación del caso, adjunto de indicadores, enriquecimiento con analyzers, lógica de decisión y cierre con
notificación. Para el manejo de errores se incluyen reintentos y rutas alternativas, lo que facilita el diagnóstico.

Con el fin de evitar dependencias externas se usan elementos simulados. Un script Python genera alertas hacia el
webhook, mientras que las acciones de contención se ejecutan mediante puntos simulados que registran la intención sin
aplicar cambios reales. El laboratorio incluye Wazuh como SIEM real, aunque es opcional para la ejecución del playbook
E2E.

La evaluación opera sobre dos escenarios. En el benigno, el análisis no supera el umbral y el caso se cierra sin
contención. En el malicioso se activa la contención simulada. En cada ejecución se registran marcas temporales para
calcular los percentiles p50 y p90.

**Stack tecnológico.** En cuanto a la infraestructura, esta se basa en Docker y Docker Compose junto con Python. Para
los datos y servicios se utiliza Elasticsearch, Redis, MariaDB y Nginx. Las plataformas SOAR principales son TheHive,
Cortex y Shuffle. Además, como componentes opcionales se incluyen MISP y Wazuh, junto con una API REST. El sistema de
logging integra Loki, Promtail y Grafana para monitoreo centralizado. Para el desarrollo se emplean herramientas como
Git, Make y pytest.

**Diseño experimental.** La variable independiente es el tipo de respuesta, comparando manual con SOAR. Las variables
dependientes son MTTR, tasa de éxito, precisión y uso de recursos. El entorno Docker, el dataset, el hardware y la
configuración se mantienen constantes. Además, el orden de ejecuciones se aleatoriza.

**Consideraciones éticas y de seguridad.** El laboratorio opera solo para fines académicos en un entorno aislado sin
datos reales. La segmentación de red contiene la actividad simulada y los secretos se gestionan mediante variables de
entorno. El diseño se alinea con GDPR, ISO 27001 y el NIST Cybersecurity Framework.

**Gestión de riesgos.** Los riesgos técnicos principales son el fallo de integración entre componentes, mitigado con
pruebas de conexión tempranas, y la aparición de vulnerabilidades, abordada con escaneos periódicos. En la planificación
se incorpora una holgura del 20% sobre la estimación de duración de cada fase y se realizan copias de seguridad diarias.
El sesgo experimental se controla mediante aleatorización del orden de ejecuciones y condiciones constantes, mientras
que las limitaciones de generalización se discuten en el capítulo de conclusiones.

La documentación técnica agrupa configuración, arquitectura, procedimientos de despliegue y organización de evidencias,
de modo que cualquier investigador pueda reproducir el experimento e interpretar los resultados.
