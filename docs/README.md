# Documentación del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
    - [1.3 Distinción histórica y académica](#13-distinción-histórica-y-académica)
    - [1.4 Portal oficial de documentación](#14-portal-oficial-de-documentación)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Visión general del proyecto](#31-visión-general-del-proyecto)
    - [3.2 Características principales](#32-características-principales)
    - [3.3 Arquitectura](#33-arquitectura)
    - [3.4 Inicio rápido](#34-inicio-rápido)
    - [3.5 Recursos adicionales](#35-recursos-adicionales)
- [4. Validación](#4-validación)
    - [4.1 Verificación](#41-verificación)
    - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
    - [4.3 Evidencias](#43-evidencias)
- [5. Problemas y consideraciones](#5-problemas-y-consideraciones)
    - [5.1 Limitaciones](#51-limitaciones)
    - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
    - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones--troubleshooting)
- [6. Referencias](#6-referencias)
- [7. Glosario](#7-glosario)

---

## 1. Resumen

### 1.1 Objetivo

Este directorio contiene toda la documentación del proyecto SOAR Ransomware Lab, incluyendo arquitectura, seguridad,
pruebas y guías de usuario.

### 1.2 Contexto

La documentación está organizada en cuatro categorías principales: documentación core, infraestructura, gestión de
proyecto y pruebas. Cada categoría contiene documentos específicos que cubren diferentes aspectos del proyecto.

La jerarquía de fuentes de verdad es:

1. Comportamiento verificable mediante pruebas y CI/CD.
2. Código fuente actual en `src/soar_lab/`, `apps/` e `infra/`.
3. Archivos Docker Compose, Dockerfiles y configuración de infraestructura.
4. `pyproject.toml`, dependencias y workflows de CI/CD.
5. Esquema OpenAPI generado por la aplicación (`/openapi.json`).
6. Documentación técnica vigente en este directorio.
7. Informes de auditoría históricos en `docs/audit/legacy/`.

### 1.3 Distinción histórica y académica

- `docs/audit/legacy/` contiene informes históricos. No deben usarse como instrucciones operativas sin verificar vigencia.
- `docs/thesis/` contiene la documentación académica del TFM. Puede incluir resultados parciales o simulados; las capacidades operativas deben validarse contra `docs/operations/`, `docs/architecture/` y el código.

### 1.4 Portal oficial de documentación

El sitio público de documentación se genera con **Docusaurus** a partir de este directorio `docs/` y se sirve en el contenedor `docs-site`:

- Acceso directo: `http://localhost:8086`
- (No se usa MkDocs ni Sphinx; `docs-site` es la única fuente de documentación web.)

## 2. Alcance

### 2.1 Qué cubre

Este documento cubre:

- Estructura general de la documentación del proyecto
- Descripción de cada categoría de documentación
- Enlaces rápidos a documentos clave
- Pautas de mantenimiento de documentación

### 2.2 Límites

Este documento es un índice de documentación y no cubre:

- Detalle de arquitectura (ver docs/architecture/overview.md)
- Guías de usuario (ver docs/getting_started/user_guide.md)
- Planificación del proyecto (ver docs/project/plan.md)
- Estrategia de pruebas (ver docs/testing/test_suite.md)

### 2.3 Dependencias

Este documento depende de:

- Todos los documentos en el directorio docs/
- README principal del proyecto (/README.md)

## 3. Contenido principal

### 3.1 Visión general del proyecto

#### Getting Started

- **[getting_started/overview.md](getting_started/overview.md)** - Visión general del laboratorio
- **[getting_started/installation_guide.md](getting_started/installation_guide.md)** - Guía de instalación
- **[getting_started/user_guide.md](getting_started/user_guide.md)** - Guía de usuario y procedimientos operacionales

#### Architecture

- **[architecture/overview.md](architecture/overview.md)** - Arquitectura completa del sistema y diseño
- **[architecture/hexagonal-structure.md](architecture/hexagonal-structure.md)** - Estructura del paquete Python y
  organización por capas hexagonales
- **[architecture/code_structure.md](architecture/code_structure.md)** - Guía de la estructura de `src/soar_lab/`
  (domain, application, infrastructure, interfaces)
- **[architecture/applications.md](architecture/applications.md)** - Aplicaciones del proyecto (api, docs-site,
  web-management)
- **[architecture/docker_architecture.md](architecture/docker_architecture.md)** - Arquitectura Docker, archivos compose
  y despliegue
- **[architecture/security.md](architecture/security.md)** - Consideraciones de seguridad y mejores prácticas

#### Operations

- **[operations/configuration_manual.md](operations/configuration_manual.md)** - Manual de configuración completo
- **[operations/infrastructure_guide.md](operations/infrastructure_guide.md)** - Guía de la estructura de `infra/`
  y uso de Docker Compose
- **[operations/ports_and_urls.md](operations/ports_and_urls.md)** - Tabla canónica de puertos, URLs y acceso
- **[operations/network_watcher.md](operations/network_watcher.md)** - Operación y recuperación del Network Watcher
- **[operations/cli_manual.md](operations/cli_manual.md)** - CLI `soar-lab` y simulador de alertas Windows
- **[operations/logging_and_observability.md](operations/logging_and_observability.md)** - Stack Loki, Promtail, Grafana
  y WebSocket `/ws/logs`
- **[operations/backup_and_restore.md](operations/backup_and_restore.md)** - Backups de la API y volúmenes Docker
- **[operations/web_management_manual.md](operations/web_management_manual.md)** - Web Management UI
- **[operations/playbooks/ransomware_playbook_e2e.md](operations/playbooks/ransomware_playbook_e2e.md)** - Documentación
  de playbook E2E
- **[operations/troubleshooting.md](operations/troubleshooting.md)** - Guía de troubleshooting

#### Integrations

- **[integrations/overview.md](integrations/overview.md)** - Visión general de integraciones, servicios y credenciales
- **[integrations/api_contracts.md](integrations/api_contracts.md)** - Especificaciones y contratos de APIs

#### Audit

- **[audit/README.md](audit/README.md)** - Índice de informes de auditoría y aseguramiento de calidad

#### Project Management

- **[project/scope.md](project/scope.md)** - Alcance y límites del proyecto
- **[project/objectives.md](project/objectives.md)** - Objetivos SMART y entregables
- **[project/plan.md](project/plan.md)** - Cronograma y roadmap del proyecto
- **[project/risks.md](project/risks.md)** - Gestión de riesgos y mitigación

#### Testing

- **[testing/README.md](testing/README.md)** - Índice de documentación de pruebas
- **[testing/test_suite.md](testing/test_suite.md)** - Documentación completa de la suite de pruebas
- **[testing/docker_testing_strategy.md](testing/docker_testing_strategy.md)** - Estrategia de pruebas de Docker

#### Thesis (TFM)

- **[thesis/](thesis/)** - Documentación completa de la Tesis de Máster (múltiples archivos)

### 3.2 Características principales

#### Enlaces Rápidos

- [Inicio Rápido](../README.md) - README principal del proyecto
- [Guía de Usuario](getting_started/user_guide.md) - Procedimientos operacionales
- [Visión General de Arquitectura](architecture/overview.md) - Diseño del sistema
- [Suite de Pruebas](testing/test_suite.md) - Documentación de pruebas
- [Plan de remediación de documentación](project/documentation_remediation_tasks.md) - Tareas y fases de revisión documental

### Estado de la documentación

| Área | Documentos clave | Estado | Última revisión | Responsable |
|------|------------------|--------|-----------------|-------------|
| Getting Started | [overview.md](getting_started/overview.md), [installation_guide.md](getting_started/installation_guide.md), [user_guide.md](getting_started/user_guide.md) | En revisión | 2026-07-18 | Maintainer |
| Arquitectura | [overview.md](architecture/overview.md), [code_structure.md](architecture/code_structure.md), [docker_architecture.md](architecture/docker_architecture.md), [security.md](architecture/security.md), [hexagonal-structure.md](architecture/hexagonal-structure.md), [composition_root.md](architecture/composition_root.md), [applications.md](architecture/applications.md) | En revisión | 2026-07-18 | Maintainer |
| Operaciones | [configuration_manual.md](operations/configuration_manual.md), [troubleshooting.md](operations/troubleshooting.md), [infrastructure_guide.md](operations/infrastructure_guide.md), [ports_and_urls.md](operations/ports_and_urls.md), [network_watcher.md](operations/network_watcher.md), [logging_and_observability.md](operations/logging_and_observability.md), [backup_and_restore.md](operations/backup_and_restore.md), [certificate_lifecycle.md](operations/certificate_lifecycle.md), [playbooks/ransomware_playbook_e2e.md](operations/playbooks/ransomware_playbook_e2e.md) | En revisión | 2026-07-18 | Maintainer |
| Integraciones | [overview.md](integrations/overview.md), [api_contracts.md](integrations/api_contracts.md), [API_DOCUMENTATION.md](API_DOCUMENTATION.md) | En revisión | 2026-07-18 | Maintainer |
| Pruebas | [test_suite.md](testing/test_suite.md), [tests_overview.md](testing/tests_overview.md), [README.md](testing/README.md), [docker_testing_strategy.md](testing/docker_testing_strategy.md) | Conteos actualizados; E2E OK | 2026-07-18 | Maintainer |
| Proyecto | [objectives.md](project/objectives.md), [plan.md](project/plan.md), [scope.md](project/scope.md), [risks.md](project/risks.md), [glossary.md](project/glossary.md), [documentation_remediation_tasks.md](project/documentation_remediation_tasks.md) | En revisión | 2026-07-19 | Maintainer |
| Auditoría | [README.md](audit/README.md), [legacy/](audit/legacy/) | En revisión | 2026-07-19 | Maintainer |
| Migración | [opensearch_migration_plan.md](migration/opensearch_migration_plan.md) | Pendiente | — | Maintainer |
| Tesis | [introduction.md](thesis/introduction.md), [executive_summary.md](thesis/executive_summary.md), [glossary.md](thesis/glossary.md), [thesis/](thesis/) | En revisión | 2026-07-18 | Maintainer |
| CI/CD | `.github/workflows/ci.yml`, `.github/workflows/vale.yml`, [docs_quality.py](../src/soar_lab/scripts/ci/docs_quality.py) | Revisado | 2026-07-19 | Maintainer |

> **Fuente de verdad**: el código en `src/soar_lab/`, `apps/` e `infra/`, el esquema `docs/api/openapi.json` y la salida de `pytest --collect-only`.

### 3.3 Arquitectura

El sistema sigue una **arquitectura hexagonal (Ports and Adapters)**: el dominio (`src/soar_lab/domain/`) define modelos y puertos; la capa de aplicación (`src/soar_lab/application/`) implementa casos de uso; la infraestructura (`src/soar_lab/infrastructure/`) provee adaptadores concretos (clientes HTTP, repositorios, drivers); las interfaces (`src/soar_lab/interfaces/`) exponen la API FastAPI y el panel web. El cableado centralizado de dependencias ocurre en [`src/soar_lab/interfaces/api/composition.py`](../src/soar_lab/interfaces/api/composition.py). Para el detalle técnico, ver [architecture/overview.md](architecture/overview.md).

### 3.4 Inicio rápido

Para comenzar con el proyecto SOAR Ransomware Lab:

1. Leer la [Visión General](getting_started/overview.md) para entender el propósito del laboratorio
2. Consultar la [Guía de Instalación](getting_started/installation_guide.md) para instrucciones de instalación
3. Consultar la [Guía de Usuario](getting_started/user_guide.md) para procedimientos operacionales
4. Revisar la [Arquitectura](architecture/overview.md) para entender el diseño del sistema
5. Ejecutar la [Suite de Pruebas](testing/test_suite.md) para validar el entorno

### 3.5 Recursos adicionales

- **Documentación Académica (TFM)**: [thesis/](thesis/) - Documentación completa de la Tesis de Máster
- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Issues y Soporte**: GitHub Issues del repositorio

## 4. Validación

### 4.1 Verificación

La documentación se mantiene como parte del pipeline CI/CD del proyecto.

### 4.2 Criterios de Aceptación

La documentación se considera actualizada cuando:

- Todos los enlaces funcionan correctamente
- El contenido está sincronizado con la implementación
- Se sigue el formato y estilo establecido
- Todos los procedimientos y comandos documentados han sido probados

### 4.3 Evidencias

Las evidencias de actualización de documentación incluyen:

- Historial de commits en el repositorio
- Reviews de código en pull requests
- Verificación de enlaces en CI/CD

## 5. Problemas y consideraciones

### 5.1 Limitaciones

No aplica.

### 5.2 Riesgos o incidencias

**Riesgos de Desincronización:**

- La documentación puede desincronizarse de la implementación si no se actualiza regularmente
- Los enlaces pueden romperse si se reorganiza la estructura de archivos

### 5.3 Recomendaciones / troubleshooting

**Mantenimiento de Documentación:**

Para contribuciones:

1. Actualizar secciones relevantes al realizar cambios en el código
2. Mantener la documentación sincronizada con la implementación
3. Seguir el formato y estilo establecido
4. Probar todos los procedimientos y comandos documentados

## 6. Referencias

## 7. Glosario

Para la definición detallada de acrónimos y términos técnicos (MTTR, KPI, E2E, CORS, JWT, SSO, MFA, WAF, IaC, etc.) consulta **[GLOSSARY.md](GLOSSARY.md)**.

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Documentación de MISP**: https://www.misp-project.org/documentation/
- **Documentación de Wazuh**: https://documentation.wazuh.com/
- **Documentación de Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **Plan de Gobernanza, Validación y Cierre**: [project/governance_and_validation_plan.md](project/governance_and_validation_plan.md)
- **Trazabilidad de validación**: [audit/TRACEABILITY_VALIDATION.md](audit/TRACEABILITY_VALIDATION.md)

Para la información más actualizada, siempre referirse al repositorio principal del proyecto.
