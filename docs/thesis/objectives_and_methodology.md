# 3. Objetivos concretos y metodología de trabajo

Este capítulo define qué se quiere demostrar y cómo se organiza el desarrollo. El resultado esperado es un laboratorio SOAR mínimo viable que ejecute un playbook E2E en dos escenarios y produzca métricas para la evaluación.

## 3.1. Objetivo general

Demostrar que un playbook SOAR automatizado reduce el tiempo de respuesta y mejora la consistencia y trazabilidad en la gestión de alertas de ransomware. El entorno debe ser reproducible, usar herramientas open source y generar evidencias verificables.

El objetivo se alcanza cuando el laboratorio ejecuta el flujo completo en dos escenarios (malicioso y benigno), cumple los umbrales de rendimiento (reducción de MTTR ≥ 50 % respecto al baseline manual) y genera evidencias completas (logs, capturas y métricas).

## 3.2. Objetivos específicos

Para alcanzar el objetivo general, el trabajo se divide en objetivos específicos:

### 3.2.1. Objetivos Estratégicos

Los objetivos estratégicos se agrupan en cuatro áreas: diseño arquitectónico, implementación funcional, validación empírica y documentación reproducible.

- **Diseño Arquitectónico**

Diseñar una arquitectura SOAR modular y reproducible basada en TheHive, Cortex y Shuffle. Se valida con una arquitectura documentada con diagramas técnicos, especificaciones de integración definidas, un plan de escalabilidad establecido y una configuración Docker Compose estructurada. Soporte documental en `docs/02-architecture.md`, `docs/03-api-and-integrations.md` e `infra/docker/compose/`.

- **Implementación Funcional**

Implementar un playbook E2E en Shuffle con integración entre TheHive, Cortex y Shuffle. Se cumple cuando hay un playbook funcional E2E en dos escenarios, una integración operativa sin intervención manual, un simulador SIEM funcional y una lógica de contención simulada operativa. El playbook está en `docs/thesis/appendix_b.md`, los scripts en `src/soar_lab/simulator/`, `src/soar_lab/infrastructure/messaging/send_alert.py`, `src/soar_lab/application/use_cases/analytics_service.py` y los logs en `runtime/logs/`.

- **Evaluación Experimental**

Aquí se busca validar la eficacia mediante métricas cuantitativas como MTTR y tasa de éxito. Los criterios de éxito son MTTR p50 ≤ 120s y p90 ≤ 180s, tasa de éxito ≥ 95 %, un dataset de al menos 50 ejecuciones por escenario y un análisis estadístico descriptivo (media, percentiles, desviación estándar, coeficiente de variación). Resultados y código asociado en `reports/e2e/`, `src/soar_lab/application/use_cases/`, `src/soar_lab/domain/statistical_calculator.py`, `src/soar_lab/data/calc_kpis.py`, `tests/e2e/` y `tests/integration/`.

- **Documentación Reproducible**

Documentar exhaustivamente el proceso para permitir la reproducción por terceros. La validación consiste en una guía de instalación y configuración completa, documentación de playbooks con contexto, validación de reproducción mediante Makefile y documentación técnica completa. Material en `docs/`, `docs/04-operations.md`, el Makefile, `docs/03-api-and-integrations.md` y `apps/docs-site/`.

La **Tabla 3** resume los cuatro objetivos estratégicos con sus métricas de éxito, valor objetivo y evidencia requerida.

## Tabla 3: Resumen de Objetivos Estratégicos y Métricas de Éxito

| ID       | Objetivo Específico        | Métricas de Éxito      | Valor Objetivo | Evidencia Requerida         |
|----------|----------------------------|------------------------|----------------|-----------------------------|
| **TE-1** | Diseño arquitectónico SOAR | Componentes integrados | 5+ componentes | Diagramas, especificaciones |
| **TE-2** | Implementación funcional   | Playbook E2E operativo | 2 escenarios (malicioso y benigno) | Scripts funcionales, logs   |
| **TE-3** | Validación experimental    | Reducción MTTR         | ≥50%           | Resultados estadísticos     |
| **TE-4** | Documentación reproducible | Guías completas        | 100% cobertura | Tutoriales, validación      |

El cumplimiento de cada objetivo se reporta en el Capítulo 4 (Resultados) y se discute en el Capítulo 6 (Conclusiones).

### 3.2.2. Objetivos Operativos

Los objetivos operativos detallan los pasos de implementación:

- **Delimitar** el alcance del proyecto estableciendo inclusiones, exclusiones y restricciones de seguridad. El entorno
  no debe tener malware funcional ni dependencias externas complejas.

- **Definir** el flujo funcional del playbook E2E: etapas, entradas, salidas, evidencias y criterios de decisión para
  los escenarios benigno y malicioso.

- **Diseñar** la arquitectura en un host con Docker Compose, incluyendo servicios, dependencias, redes y volúmenes.

- **Verificar** que los servicios arrancan de forma estable tras el despliegue inicial.

- **Configurar** y conectar los componentes: TheHive (TheHive Project, 2024) para gestión de casos, Cortex (Cortex Project, 2024) para análisis y Shuffle (Shuffle Tools, 2024) para
  orquestación.

- **Construir** el mecanismo de ingesta de alertas por webhook y asegurar la validación del payload de entrada.

- **Implementar** la creación y actualización de casos en TheHive, incluyendo IoCs, etiquetas, estados y resúmenes.

- **Automatizar** el enriquecimiento de observables mediante analyzers en Cortex y establecer la lógica de decisión
  basada en umbral de score.

- **Simular** las acciones de contención y registrar evidencias en el caso sin cambios reales en sistemas productivos.

- **Implementar** integraciones simuladas: un SIEM simulado para emitir alertas y endpoints mock para EDR y firewall.

- **Medir** el rendimiento del flujo desde la alerta hasta la contención simulada y calcular los percentiles p50 y p90.

- **Generar** evidencias verificables: logs, capturas, trazas y métricas. Documentar el procedimiento para asegurar
  reproducibilidad.

**Criterios de cumplimiento**: el objetivo general se alcanza cuando el laboratorio ejecuta el flujo completo en dos
escenarios, cumple los umbrales de rendimiento y genera evidencias completas.

## 3.3. Metodología del trabajo

La metodología combina investigación aplicada con desarrollo tecnológico, siguiendo principios de DevSecOps. El proyecto se desarrolla entre finales de abril de 2026 y finales de agosto de 2026 (aproximadamente 4 meses, 18 semanas) y se estructura en cinco fases. La **Figura 2** muestra el cronograma Gantt con la distribución temporal de cada fase.

La planificación temporal evolucionó a lo largo del proyecto. La estimación inicial fue de 12 semanas, suficiente según el alcance previsto. Tras la fase de diseño se aumentó a 15 semanas para acomodar la integración de Cortex con analyzers externos y el stack de monitoreo, no contemplados inicialmente. Finalmente, la duración real fue de 18 semanas debido a la ampliación de la suite de pruebas (hasta 2041 tests) y la ejecución del experimento con n=50 ejecuciones.

```mermaid
gantt     title Figura 2: Cronograma Gantt del proyecto     dateFormat YYYY-MM-DD     axisFormat %d %b

    section Fase 1: Investigación y requisitos     Revisión literatura, análisis de requisitos     :a1, 2026-04-27, 3w

    section Fase 2: Diseño arquitectónico     Diseño hexagonal, topología Docker, contratos   :a2, after a1, 3w

    section Fase 3: Desarrollo e implementación     Implementación playbook, integraciones, API     :a3, after a2, 6w

    section Fase 4: Pruebas y validación     Tests E2E, experimentos n=50, análisis stats    :a4, after a3, 3w

    section Fase 5: Optimización y documentación     Redacción TFM, anexos, validación final               :a5, after a4, 3w
```

**Figura 2**: Cronograma Gantt del proyecto con las cinco fases distribuidas entre abril y agosto de 2026.

**Fase 1 — Investigación y requisitos (abril-mayo 2026, 3 semanas).** Revisión de la literatura sobre respuesta a
incidentes, ransomware y plataformas SOAR. Identificación de la brecha cuantitativa en la literatura. Definición de requisitos funcionales, no funcionales y de integración. Selección del stack tecnológico open source.

**Fase 2 — Diseño arquitectónico (mayo 2026, 3 semanas).** Diseño de la arquitectura hexagonal del código
Python. Definición de la topología Docker Compose con segmentación de redes. Especificación de contratos de integración entre TheHive, Cortex y Shuffle. Diseño del modelo de scoring y del flujo del playbook.

**Fase 3 — Desarrollo e implementación (junio-julio 2026, 6 semanas).** Implementación del playbook E2E en
Shuffle con 46 nodos y 25 scripts Python. Integración con TheHive (gestión de casos) y Cortex (análisis de IoCs).
Desarrollo del simulador SIEM y de la lógica de contención simulada. Implementación de la API FastAPI con arquitectura hexagonal. Configuración del stack de monitoreo (Loki, Promtail, Grafana).

**Fase 4 — Pruebas y validación (julio-agosto 2026, 3 semanas).** Ejecución de la suite de pruebas
completa (2041 tests). Realización del experimento con n=50 ejecuciones en dos escenarios (malicioso y benigno).
Análisis estadístico descriptivo: media, percentiles, desviación estándar, coeficiente de variación. Mutation testing con mutmut.

**Fase 5 — Optimización y documentación (agosto 2026, 3 semanas).** Redacción de la memoria del TFM y los anexos.
Validación final de reproducibilidad con `make up` y `pytest tests/e2e/`.

El desarrollo empieza por definir el alcance y los requisitos. Se prioriza que el entorno sea reproducible y seguro, además de posibilitar repetir ejecuciones bajo condiciones comparables. La validación es medible: se evalúa la ejecución del flujo en dos escenarios, las métricas dentro de umbral y la generación de evidencias verificables.

En cuanto al diseño arquitectónico, este usa una topología de despliegue en un host con Docker Compose. Los contratos de integración especifican los puntos de conexión de cada componente, el mecanismo de autenticación y el formato de la alerta. La lógica de decisión del playbook se puede ajustar mediante variables de configuración, como por ejemplo el umbral de score de riesgo.

Una vez definido el diseño, se despliega el laboratorio y se verifica la conectividad entre componentes, el almacenamiento de datos y la estabilidad. La integración sigue un orden incremental: primero TheHive, luego Cortex y finalmente Shuffle como orquestador.

Tras las validaciones de integración, se construye el playbook E2E. El flujo incluye ingesta por webhook, validación de datos, creación del caso, adjunto de indicadores, enriquecimiento con analyzers, lógica de decisión y cierre con notificación. Para el manejo de errores se incluyen reintentos y rutas alternativas, lo que facilita el diagnóstico.

Con el fin de evitar dependencias externas se usan elementos simulados. Un script Python genera alertas hacia el webhook, mientras que las acciones de contención se ejecutan mediante puntos simulados que registran la intención sin aplicar cambios reales. El laboratorio incluye Wazuh (Wazuh, 2024) como SIEM real, aunque es opcional para la ejecución del playbook E2E.

La evaluación opera sobre dos escenarios. En el benigno, el análisis no supera el umbral y el caso se cierra sin contención. En el malicioso se activa la contención simulada. En cada ejecución se registran marcas temporales para calcular los percentiles p50 y p90.

**Stack tecnológico.** En cuanto a la infraestructura, esta se basa en Docker y Docker Compose (Docker Inc., 2024)
junto con Python. Para los datos y servicios se utiliza Elasticsearch (Elastic, 2024), Redis (Redis Ltd., 2024), MariaDB y Nginx (Nginx, 2024). Las plataformas SOAR principales son TheHive (TheHive Project, 2024), Cortex (Cortex Project, 2024) y Shuffle (Shuffle Tools, 2024). Además, como componentes opcionales se incluyen MISP (MISP Project, 2024) y Wazuh (Wazuh, 2024), junto con una API REST. El sistema de logging integra Loki (Grafana Labs, 2024b), Promtail (Grafana Labs, 2024c) y Grafana (Grafana Labs, 2024) para monitoreo centralizado. Para el desarrollo se emplean herramientas como Git, Make y pytest (pytest, 2024).

**Diseño experimental.** La variable independiente es el tipo de respuesta, comparando manual con SOAR. Las variables
dependientes son MTTR, tasa de éxito, precisión y uso de recursos. El entorno Docker, el dataset, el hardware y la configuración se mantienen constantes. Además, el orden de ejecuciones se aleatoriza.

**Consideraciones éticas y de seguridad.** El laboratorio opera solo para fines académicos en un entorno aislado sin
datos reales. La segmentación de red contiene la actividad simulada y los secretos se gestionan mediante variables de entorno. El diseño se alinea con el Reglamento General de Protección de Datos (European Union, 2018), la California Consumer Privacy Act (State of California, 2020) y la Health Insurance Portability and Accountability Act (U.S. Department of Health & Human Services, 2023) en cuanto a protección de datos, ISO 27001 (ISO/IEC, 2022) e ISO 27002 (ISO/IEC, 2023) en gestión de seguridad, y el NIST Cybersecurity Framework (NIST, 2024a).

**Gestión de riesgos.** Los riesgos técnicos principales son el fallo de integración entre componentes, mitigado con
pruebas de conexión tempranas, y la aparición de vulnerabilidades, abordada con escaneos periódicos. En la planificación se incorpora una holgura del 20 % sobre la estimación de duración de cada fase y se realizan copias de seguridad diarias.
El sesgo experimental se controla mediante aleatorización del orden de ejecuciones y condiciones constantes, mientras que las limitaciones de generalización se discuten en el capítulo de conclusiones.

La documentación técnica agrupa configuración, arquitectura, procedimientos de despliegue y organización de evidencias, de modo que cualquier investigador pueda reproducir el experimento e interpretar los resultados.

### Pasos operativos para reproducir el experimento

1. **Definir la línea base manual.** Simular la recepción de una alerta de ransomware y contabilizar el tiempo
   empleado en validación, apertura de caso, enriquecimiento, decisión y cierre.
2. **Implementar el laboratorio.** Clonar el repositorio, ejecutar `make generate-secrets` y `make up` siguiendo
   `docs/01-getting-started.md`.
3. **Ejecutar el playbook E2E.** Lanzar `pytest tests/e2e/` para las dos líneas de alerta: maliciosa y benigna.
4. **Medir MTTR.** Extraer `mttr_seconds` del índice `soar-metrics` o del cálculo del workflow.
5. **Comparar manual vs automatizado.** Evaluar si el MTTR y la consistencia mejoran respecto a la línea base manual.

### Casos de error esperados

- Falta de recursos (`vm.max_map_count`, memoria) impide el arranque de Elasticsearch.
- Errores de DNS entre contenedores hacen que los workers de Shuffle no resuelvan `shuffle-backend`.
- La API key de Shuffle cambia tras `make reset` y queda desactualizada en `.env.full`.
- Credenciales con `@` o `!` provocan errores de escaping en MariaDB u otros servicios.

### Criterios de verificación

- `make up` finaliza con todos los contenedores `healthy` según `docker compose ps`.
- `pytest tests/e2e/` devuelve el 100 % de tests PASSED.
- El dashboard de Grafana muestra métricas (`mttr_seconds`, `p50`, `p90`) y confirma la reducción del MTTR respecto
  al baseline manual.
- Los logs del playbook y las entradas en TheHive/Cortex evidencian trazabilidad completa de la alerta.

---

## Índice de Figuras del Capítulo 3

| Figura    | Título                          | Archivo          |
|-----------|---------------------------------|------------------|
| Figura 2 | Cronograma Gantt del proyecto | Mermaid (inline) |

## Índice de Tablas del Capítulo 3

| Tabla   | Título                                          |
|---------|-------------------------------------------------|
| Tabla 3 | Objetivos Específicos con Métricas de Éxito     |
