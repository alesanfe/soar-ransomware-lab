# Objetivos SMART (EDT 1.2)

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Objetivos principales](#31-objetivos-principales)
    - [3.2 Objetivos específicos](#32-objetivos-específicos)
    - [3.3 Métricas de éxito](#33-métricas-de-éxito)
    - [3.4 Cronograma](#34-cronograma)
    - [3.5 Hitos](#35-hitos)
- [4. Validación](#4-validación)
    - [4.1 Verificación](#41-verificación)
    - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
    - [4.3 Evidencias](#43-evidencias)
- [5. Problemas y consideraciones](#5-problemas-y-consideraciones)
    - [5.1 Limitaciones](#51-limitaciones)
    - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
    - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones--troubleshooting)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Este documento presenta los objetivos SMART del proyecto y su relación con la Estructura de Desglose del Trabajo (EDT),
indicando dónde se almacenarán las pruebas y evidencias en el repositorio para garantizar la trazabilidad y validación
académica.

### 1.2 Contexto

El proyecto se basa en la EDT definida y el contexto del laboratorio SOAR para respuesta ante incidentes de ransomware.
Cada objetivo está alineado con las tareas del EDT y vinculado con la estructura del repositorio, asegurando
trazabilidad y organización académica rigurosa. Las evidencias se almacenarán en ubicaciones específicas del repositorio
para facilitar su validación.

## 2. Alcance

### 2.1 Qué cubre

Este documento cubre:

- 20 objetivos SMART definidos para el proyecto
- Métricas y umbrales para cada objetivo
- Métodos de medida y ubicación de evidencias
- Relación entre objetivos y EDT
- Estructura del repositorio para almacenamiento de evidencias

### 2.2 Límites

Este documento no cubre:

- Detalles técnicos de implementación (ver docs/architecture/overview.md)
- Estrategias de seguridad (ver docs/architecture/security.md)
- Planificación detallada del proyecto (ver docs/project/plan.md)
- Alcance del proyecto (ver docs/project/scope.md)

### 2.3 Dependencias

Este documento depende de:

- EDT definida (docs/project/plan.md)
- Alcance del proyecto (docs/project/scope.md)
- Documentación de arquitectura (docs/architecture/overview.md)
- Estrategia de pruebas (docs/testing/)

## 3. Contenido principal

### 3.1 Objetivos principales

#### Ubicación de Evidencias

Las evidencias se almacenarán en:

- **Pruebas Unitarias y E2E**: `tests/unit/` (pruebas unitarias), `tests/e2e/TC-01/test_malicious.py` (escenario
  malicioso), `tests/e2e/TC-02/test_benign.py` (escenario benigno)
- **Resultados y Métricas**: `artifacts/results/kpis.csv` (archivo CSV con KPIs calculados)
- **Documentación Técnica y Validación**: `docs/operations/playbooks/ransomware_playbook_e2e.md` (playbook E2E),
  `docs/testing/` (estrategia de pruebas)
- **Logs del Flujo**: `artifacts/logs/playbook_execution.log` (logs de ejecución del playbook)

#### Relación con EDT y Repositorio

Cada objetivo corresponde a tareas específicas del EDT:

- **Infraestructura (EDT 4.x)**: Objetivos 1, 8, 13, 14.
- **Playbook y scripts (EDT 5.x, 6.x)**: Objetivos 2, 5, 6.
- **Pruebas y métricas (EDT 7.x)**: Objetivos 3, 9, 10, 15, 16, 17, 18, 19.
- **Documentación y cierre (EDT 8.x)**: Objetivos 4, 11, 12, 20.

La estructura del repositorio soporta esta organización, con carpetas dedicadas para pruebas (`tests/`), resultados (
`artifacts/results/`), documentación (`docs/`) y scripts (`scripts/`), garantizando la trazabilidad necesaria para un
TFM académico riguroso.

**Estructura del repositorio:**

- `tests/unit/` - 37 archivos de pruebas unitarias de componentes individuales
- `tests/e2e/TC-01/test_malicious.py` - Test E2E escenario malicioso
- `tests/e2e/TC-02/test_benign.py` - Test E2E escenario benigno
- `tests/e2e/TC-03/test_edge_cases.py` - Test E2E casos extremos
- `artifacts/results/kpis.csv` - Archivo CSV con KPIs calculados por `src/soar_lab/services/kpi_analyzer.py`
- `src/soar_lab/infrastructure/http_alert_sender.py` - Módulo para enviar alertas simuladas
- `src/soar_lab/services/backup_service.py` - Servicio de backup/restore
- `infra/docker/compose/docker-compose.yml` - Compose principal
- `infra/docker/compose/docker-compose.core.yml` - Compose servicios core
- `infra/docker/compose/docker-compose.misp.yml` - Compose MISP
- `infra/docker/compose/docker-compose.wazuh.yml` - Compose Wazuh
- `infra/docker/compose/docker-compose.api.yml` - Compose API y docs
- `infra/docker/compose/logging/docker-compose.logging.yml` - Compose stack de logging
- `Makefile` - Automatización de despliegue y gestión

### 3.2 Objetivos específicos

#### Flujo de Cumplimiento de Objetivos

1. **Fase de Infraestructura**: Implementación del laboratorio, API, CLI y automatización (Objetivos 1, 8, 13, 14)
2. **Fase de Desarrollo**: Playbook E2E, integración SIEM y contención simulada (Objetivos 2, 5, 6)
3. **Fase de Validación**: Métricas MTTR, pruebas especializadas y KPIs (Objetivos 3, 9, 10, 15, 16, 17, 18, 19)
4. **Fase de Cierre**: Documentación técnica, analytics, preparación defensa y evidencia de aprobación (Objetivos 4, 11,
   12, 20)

### 3.3 Métricas de éxito

#### Tabla de Objetivos SMART y Ubicación de Evidencias

| Nº | Objetivo                       | Descripción                                                                                                                                                                                                    | Métrica               | Umbral                             | Método de Medida                                                             | Evidencia                                                                                                                 |
|----|--------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------|------------------------------------|------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| 1  | Implementación del Laboratorio | Desplegar entorno reproducible con TheHive, Cortex y Shuffle mediante Docker Compose (`infra/docker/compose/docker-compose.yml`, `infra/docker/compose/docker-compose.core.yml`).                              | Servicios activos     | 100% contenedores funcionando      | Verificación con `docker ps` y `make up`                                     | Capturas en `docs/operations/configuration_manual.md`                                                                     |
| 2  | Desarrollo del Playbook E2E    | Crear flujo automatizado desde alerta hasta contención simulada en Shuffle (`playbooks/shuffle/`).                                                                                                             | Ejecución completa    | 2 escenarios (malicioso y benigno) | Logs del SOAR y casos en TheHive                                             | Evidencias en `tests/e2e/TC-01/test_malicious.py` y `tests/e2e/TC-02/test_benign.py`                                      |
| 3  | Validación de Métricas MTTR    | Medir tiempo de respuesta desde alerta hasta contención mediante timestamps en logs.                                                                                                                           | Percentiles p50 y p90 | p50 ≤ 120 s; p90 ≤ 180 s           | Timestamps y cálculo estadístico con `src/soar_lab/services/kpi_analyzer.py` | `artifacts/results/kpis.csv` y `docs/operations/playbooks/ransomware_playbook_e2e.md`                                     |
| 4  | Documentación Técnica          | Generar documentación completa (arquitectura, configuración, resultados, API, docs-site, CLI, analytics).                                                                                                      | Documento final       | 100% apartados completados         | Checklist y revisión                                                         | `docs/` (architecture/overview.md, apps/api/api-docs.html, apps/docs-site/, src/soar_lab/cli.py, src/soar_lab/analytics/) |
| 5  | Integración SIEM Simulada      | Configurar SIEM simulado para generar alertas mediante `src/soar_lab/infrastructure/http_alert_sender.py`.                                                                                                     | Alertas procesadas    | 100% sin errores                   | Logs en Shuffle y casos en TheHive                                           | `src/soar_lab/infrastructure/http_alert_sender.py` + capturas en `docs/operations/playbooks/ransomware_playbook_e2e.md`   |
| 6  | Contención Simulada            | Implementar contención simulada en código Python (`src/soar_lab/services/containment_service.py`).                                                                                                             | Acciones ejecutadas   | 100% completadas                   | Logs del servicio y confirmación en flujo                                    | `src/soar_lab/services/containment_service.py`                                                                            |
| 7  | Seguridad del Entorno          | Garantizar uso exclusivo de muestras inertes, gestión de certificados SSL (`scripts/utils/gen_certs.sh`) y validación de esquemas (`src/soar_lab/validation/`, `src/soar_lab/schemas/`).                       | Incidentes            | 0 incidentes                       | Revisión del contenido y validación                                          | `docs/architecture/security.md`, certificados en `infra/docker/certs/`                                                    |
| 8  | Automatización Integral        | Implementar despliegue con Makefiles, Docker Compose, CI/CD (`scripts/ci/`), testing automatizado (`scripts/testing/`, `scripts/automation/`), backup/restore (`scripts/infra/`) y Vagrant (`infra/vagrant/`). | Despliegue automático | 100% servicios levantados          | Ejecución de scripts y verificación                                          | `Makefile`, `infra/docker/compose/`, `scripts/ci/`, `scripts/infra/`, `infra/vagrant/`                                    |
| 9  | Pruebas Atómicas               | Ejecutar pruebas atómicas de componentes individuales (`tests/atomic/`: alertas, IoCs, KPIs, esquemas, secrets).                                                                                               | Casos probados        | 90% pruebas pasan                  | `pytest tests/atomic/ -v`                                                    | Resultados en `artifacts/results/atomic_tests.json`                                                                       |
| 10 | Pruebas de Integración         | Ejecutar pruebas de integración entre TheHive, Cortex, Shuffle, API y otros componentes (`tests/integration/`).                                                                                                | Casos probados        | 85% pruebas pasan                  | `pytest tests/integration/ -v`                                               | Resultados en `artifacts/results/integration_tests.json`                                                                  |
| 11 | Pruebas de Seguridad           | Ejecutar pruebas de seguridad para validar autenticación, autorización, validación de entrada y controles de acceso (`tests/security/`).                                                                       | Casos probados        | 100% pruebas pasan                 | `pytest tests/security/ -v`                                                  | Resultados en `artifacts/results/security_tests.json`                                                                     |
| 12 | Pruebas de Rendimiento         | Ejecutar pruebas de rendimiento para validar tiempos de respuesta de API, analyzers y componentes críticos (`tests/performance/`).                                                                             | Tiempos de respuesta  | ≤ umbrales definidos               | `pytest tests/performance/ -v`                                               | Resultados en `artifacts/results/performance_tests.json`                                                                  |
| 13 | Pruebas de Producción          | Ejecutar smoke tests para validación rápida de despliegues en producción (`tests/production/`).                                                                                                                | Casos probados        | 100% pruebas pasan                 | `pytest tests/production/ -v`                                                | Resultados en `artifacts/results/smoke_tests.json`                                                                        |
| 14 | KPIs y Análisis                | Calcular KPIs, analytics de TFM (`src/soar_lab/analytics/`) y métricas de servicios (`scripts/metrics/`).                                                                                                      | KPIs calculados       | Informe con gráficos               | Análisis estadístico y visualización                                         | `artifacts/results/kpis.csv`, `src/soar_lab/analytics/`, `scripts/metrics/`                                               |
| 15 | Preparación Defensa TFM        | Crear presentación, resumen ejecutivo y analytics para evidencia académica (`src/soar_lab/analytics/`).                                                                                                        | Presentación lista    | 100% diapositivas completadas      | Validación y ensayo                                                          | Documentación en `docs/project/`, datos en `artifacts/data/`                                                              |
| 16 | Evidencia de Aprobación        | Obtener validación formal del alcance y objetivos.                                                                                                                                                             | Archivo firmado       | Documento archivado                | Confirmación por correo y almacenamiento                                     | Carpeta `docs/project/` (scope.md, objectives.md, plan.md)                                                                |
| 17 | API del Laboratorio            | Implementar y desplegar la API REST del laboratorio con FastAPI para gestión de servicios, health checks, métricas, tests y backups (`src/soar_lab/api/`, `apps/api/`).                                        | Endpoints funcionales | Cobertura ≥ 80%                    | Tests de integración, `/docs`                                                | `apps/api/api-docs.html`, logs `soar_api`                                                                                 |
| 18 | CLI del Laboratorio            | Implementar CLI para gestión del laboratorio con comandos para alertas, configuración, validación y operaciones comunes (`src/soar_lab/cli.py`).                                                               | Comandos funcionales  | 100% comandos ejecutan             | Tests unitarios, `--help`                                                    | `src/soar_lab/cli.py`, documentación en README                                                                            |
| 19 | Sitio de Documentación         | Desplegar sitio de documentación Docusaurus con documentación completa del laboratorio, getting started y guías de uso (`apps/docs-site/`).                                                                    | Sitio funcional       | 100% páginas renderizan            | Tests de navegador, revisión enlaces                                         | `apps/docs-site/`, capturas de pantalla                                                                                   |
| 20 | Interfaz Web de Gestión        | Desplegar interfaz web de gestión para monitoreo del laboratorio, visualización de servicios y operaciones básicas (`apps/web-management/`).                                                                   | UI funcional          | Dashboard muestra estado real      | Tests de navegador, pruebas manuales                                         | `apps/web-management/`, capturas de pantalla                                                                              |

### 3.4 Cronograma

#### Diagrama de Gantt del Cronograma de Objetivos

```mermaid
gantt
    title Cronograma de Objetivos SMART - SOAR Ransomware Lab
    dateFormat  YYYY-MM-DD
    section Fase 1: Infraestructura
    Objetivo 1: Laboratorio desplegado         :active, obj1, 2025-05-01, 14d
    Objetivo 8: Automatización configurada     :obj8, after obj1, 7d
    Objetivo 17: API del Laboratorio           :obj17, after obj8, 7d
    Objetivo 18: CLI del Laboratorio           :obj18, after obj17, 5d
    section Fase 2: Desarrollo
    Objetivo 2: Playbook E2E                   :obj2, 2025-05-15, 21d
    Objetivo 5: Integración SIEM               :obj5, after obj2, 7d
    Objetivo 6: Contención simulada            :obj6, after obj5, 7d
    Objetivo 19: Sitio de Documentación        :obj19, after obj6, 7d
    Objetivo 20: Interfaz Web de Gestión       :obj20, after obj19, 7d
    section Fase 3: Validación
    Objetivo 3: Métricas MTTR                  :obj3, 2025-06-05, 14d
    Objetivo 9: Pruebas Atómicas               :obj9, after obj3, 5d
    Objetivo 10: Pruebas de Integración        :obj10, after obj9, 7d
    Objetivo 11: Pruebas de Seguridad          :obj11, after obj10, 5d
    Objetivo 12: Pruebas de Rendimiento        :obj12, after obj11, 5d
    Objetivo 13: Pruebas de Producción         :obj13, after obj12, 3d
    Objetivo 14: KPIs y Análisis               :obj14, after obj13, 7d
    section Fase 4: Cierre
    Objetivo 4: Documentación técnica           :obj4, 2025-06-26, 7d
    Objetivo 15: Preparación defensa TFM        :obj15, after obj4, 7d
    Objetivo 16: Evidencia aprobación          :obj16, after obj15, 7d
```

#### Fases del Proyecto

| Fase                        | Duración  | Objetivos                | Entregables                                                        |
|-----------------------------|-----------|--------------------------|--------------------------------------------------------------------|
| **Fase 1: Infraestructura** | 4 semanas | 1, 8, 17, 18             | Laboratorio desplegado, automatización, API, CLI                   |
| **Fase 2: Desarrollo**      | 5 semanas | 2, 5, 6, 19, 20          | Playbook E2E, integración SIEM, scripts, docs-site, web-management |
| **Fase 3: Validación**      | 4 semanas | 3, 9, 10, 11, 12, 13, 14 | Métricas MTTR, pruebas especializadas, KPIs                        |
| **Fase 4: Cierre**          | 2 semanas | 4, 15, 16                | Documentación técnica, presentación, aprobación                    |

### 3.5 Hitos

#### Matriz de Trazabilidad: Objetivos vs Entregables

| Objetivo | Entregable Principal                | Entregable Secundario                | Ubicación en Repositorio                                                    | EDT Relacionada | Estado    |
|----------|-------------------------------------|--------------------------------------|-----------------------------------------------------------------------------|-----------------|-----------|
| 1        | Laboratorio SOAR desplegado         | Capturas de servicios                | `docs/operations/configuration_manual.md`                                   | EDT 4.1         | Pendiente |
| 2        | Playbook E2E implementado           | Logs de ejecución                    | `tests/e2e/TC-01/test_malicious.py`, `tests/e2e/TC-02/test_benign.py`       | EDT 5.1         | Pendiente |
| 3        | Métricas MTTR validadas             | Archivo KPIs                         | `artifacts/results/kpis.csv`                                                | EDT 7.1         | Pendiente |
| 4        | Documentación técnica completa      | Revisión                             | `docs/architecture/`, `apps/api/api-docs.html`, `apps/docs-site/`           | EDT 8.1         | Pendiente |
| 5        | Integración SIEM simulada           | Script de alertas                    | `src/soar_lab/infrastructure/http_alert_sender.py`                          | EDT 5.2         | Pendiente |
| 6        | Scripts de contención               | Logs de ejecución                    | `src/soar_lab/services/containment_service.py`                              | EDT 6.1         | Pendiente |
| 7        | Seguridad validada                  | Documento de seguridad, certificados | `docs/architecture/security.md`, `infra/docker/certs/`                      | EDT 4.2         | Pendiente |
| 8        | Automatización integral configurada | Scripts CI/CD, backup                | `Makefile`, `scripts/ci/`, `scripts/infra/`, `infra/vagrant/`               | EDT 4.3         | Pendiente |
| 9        | Pruebas atómicas completadas        | Informe de pruebas                   | `tests/atomic/`, `artifacts/results/atomic_tests.json`                      | EDT 7.2         | Pendiente |
| 10       | Pruebas de integración completadas  | Informe de pruebas                   | `tests/integration/`, `artifacts/results/integration_tests.json`            | EDT 7.2         | Pendiente |
| 11       | Pruebas de seguridad completadas    | Informe de pruebas                   | `tests/security/`, `artifacts/results/security_tests.json`                  | EDT 7.2         | Pendiente |
| 12       | Pruebas de rendimiento completadas  | Informe de pruebas                   | `tests/performance/`, `artifacts/results/performance_tests.json`            | EDT 7.2         | Pendiente |
| 13       | Pruebas de producción completadas   | Informe de pruebas                   | `tests/production/`, `artifacts/results/smoke_tests.json`                   | EDT 7.2         | Pendiente |
| 14       | KPIs calculados y analizados        | Gráficos y análisis                  | `artifacts/results/kpis.csv`, `src/soar_lab/analytics/`, `scripts/metrics/` | EDT 7.3         | Pendiente |
| 15       | Presentación TFM preparada          | Diapositivas, analytics              | `docs/project/`, `artifacts/data/`                                          | EDT 8.2         | Pendiente |
| 16       | Evidencia de aprobación             | Documento firmado                    | `docs/project/` (scope.md, objectives.md, plan.md)                          | EDT 8.3         | Pendiente |
| 17       | API del Laboratorio desplegada      | API funcional                        | `src/soar_lab/api/`, `apps/api/api-docs.html`                               | EDT 4.1         | Pendiente |
| 18       | CLI del Laboratorio implementada    | CLI funcional                        | `src/soar_lab/cli.py`, README.md                                            | EDT 4.1         | Pendiente |
| 19       | Sitio de Documentación desplegado   | Sitio funcional                      | `apps/docs-site/`, capturas de pantalla                                     | EDT 8.1         | Pendiente |
| 20       | Interfaz Web de Gestión desplegada  | UI funcional                         | `apps/web-management/`, capturas de pantalla                                | EDT 4.1         | Pendiente |

**Leyenda de EDT:**

- EDT 4.x: Infraestructura y automatización
- EDT 5.x: Desarrollo de playbook e integraciones
- EDT 6.x: Scripts de contención y respuesta
- EDT 7.x: Pruebas, validación y métricas
- EDT 8.x: Documentación y cierre del proyecto

#### Hitos Principales

- **Hito 1**: Laboratorio SOAR desplegado, API y CLI funcionales (Semana 4)
- **Hito 2**: Playbook E2E implementado, docs-site y web-management desplegados (Semana 9)
- **Hito 3**: Métricas MTTR validadas, pruebas especializadas completadas y KPIs calculados (Semana 13)
- **Hito 4**: Documentación completa, analytics de TFM y aprobación formal (Semana 15)

## 4. Validación

### 4.1 Verificación

Los objetivos se verifican mediante:

- Ejecución de pruebas automatizadas (`pytest tests/unit/`, `pytest tests/e2e/`)
- Revisión de evidencias en ubicaciones especificadas (`tests/e2e/TC-01/`, `tests/e2e/TC-02/`, `artifacts/results/`)
- Validación de métricas contra umbrales definidos mediante `src/soar_lab/services/kpi_analyzer.py`
- Revisión de documentación (`docs/architecture/`, `docs/project/`)
- Confirmación de aprobación formal

### 4.2 Criterios de aceptación

Los objetivos se consideran cumplidos cuando:

- Todas las métricas alcanzan los umbrales especificados
- Las evidencias están almacenadas en las ubicaciones correctas
- La documentación está completa y revisada
- Las pruebas pasan sin errores
- Validación formal

### 4.3 Evidencias

Las evidencias de validación incluyen:

- Capturas de pantalla de servicios funcionando
- Logs de ejecución de playbooks y scripts
- Resultados de pruebas automatizadas
- Archivo `artifacts/results/kpis.csv` con KPIs
- Documentación técnica completa
- Presentación de defensa TFM
- Documento de aprobación firmado

## 5. Problemas y consideraciones

### 5.1 Limitaciones

- **Dependencia de validación**: Algunos objetivos requieren validación
- **Tiempo de ejecución**: Pruebas E2E pueden requerir tiempo considerable
- **Recursos**: Requiere 8GB RAM mínimo para ejecución completa
- **Muestras inertes**: Limitación en uso de muestras reales de ransomware

### 5.2 Riesgos o incidencias

- **Objetivos no cumplidos**: Umbrales de métricas no alcanzados
- **Evidencias perdidas**: Falta de trazabilidad en almacenamiento
- **Validación rechazada**: Documentación o resultados no aprobados
- **Falta de tiempo**: Objetivos no completados en plazo establecido

### 5.3 Recomendaciones / troubleshooting

**Objetivo no cumplido:**

```bash
# Verificar estado de servicios
docker ps

# Ejecutar pruebas específicas
pytest tests/e2e/ -v

# Revisar logs de ejecución
cat artifacts/logs/playbook_execution.log
```

**Evidencias no encontradas:**

```bash
# Verificar estructura de directorios
ls -la tests/
ls -la artifacts/results/
ls -la docs/project/

# Revisar configuración de almacenamiento
cat .env.full | grep ARTIFACTS
```

**Métricas fuera de umbral:**

```bash
# Revisar archivo de KPIs
cat artifacts/results/kpis.csv

# Re-ejecutar pruebas para recopilar nuevos datos
pytest tests/e2e/ --generate-kpis
```

**Validación rechazada:**

- Revisar feedback
- Actualizar documentación según comentarios
- Reenviar para validación

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Documentación de MISP**: https://www.misp-project.org/documentation/
- **Documentación de Wazuh**: https://documentation.wazuh.com/
- **Documentación de Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **Documentación de Arquitectura**: [docs/architecture/overview.md](../architecture/overview.md)
- **Documentación de Seguridad**: [docs/architecture/security.md](../architecture/security.md)
- **Plan del Proyecto**: [docs/project/plan.md](plan.md)
- **Alcance del Proyecto**: [docs/project/scope.md](scope.md)

---


