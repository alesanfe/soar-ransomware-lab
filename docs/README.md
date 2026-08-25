# Documentación del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
    - [1.3 Portal oficial de documentación](#13-portal-oficial-de-documentación)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Documentos principales](#31-documentos-principales)
    - [3.2 Assets](#32-assets)
    - [3.3 Archivo histórico](#33-archivo-histórico)
    - [3.4 Tesis (TFM)](#34-tesis-tfm)
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

Este directorio contiene toda la documentación técnica del proyecto SOAR Ransomware Lab, organizada en 6 documentos principales, assets, archivo histórico y la tesis de máster.

### 1.2 Contexto

La documentación se ha consolidado en 6 archivos principales que cubren todos los aspectos del proyecto. Cada documento sigue una estructura estándar de 6 secciones (Resumen, Alcance, Contenido, Validación, Problemas, Referencias).

La jerarquía de fuentes de verdad es:

1. Comportamiento verificable mediante pruebas y CI/CD.
2. Código fuente actual en `src/soar_lab/`, `apps/` e `infra/`.
3. Archivos Docker Compose, Dockerfiles y configuración de infraestructura.
4. `pyproject.toml`, dependencias y workflows de CI/CD.
5. Esquema OpenAPI generado por la aplicación (`assets/references/openapi.json`).
6. Documentación técnica vigente en este directorio.

### 1.3 Portal oficial de documentación

El sitio público de documentación se genera con **Docusaurus** a partir de este directorio `docs/` y se sirve en el contenedor `docs-site`:

- Acceso directo: `http://localhost:8086`

---

## 2. Alcance

### 2.1 Qué cubre

- Estructura general de la documentación del proyecto
- Enlaces a los 6 documentos principales
- Referencias a assets e histórico

### 2.2 Límites

Este documento es un índice y no cubre:

- Detalle de arquitectura (ver [02-architecture.md](02-architecture.md))
- Guías de instalación (ver [01-getting-started.md](01-getting-started.md))
- Planificación del proyecto (ver [06-project-management.md](06-project-management.md))
- Estrategia de pruebas (ver [05-testing.md](05-testing.md))

### 2.3 Dependencias

- Los 6 documentos principales en `docs/`
- Assets en `docs/assets/`
- README principal del proyecto (`/README.md`)

---

## 3. Contenido principal

### 3.1 Documentos principales

| Documento | Descripción |
|-----------|-------------|
| [01-getting-started.md](01-getting-started.md) | Visión general, requisitos, instalación, primer acceso y guía rápida. |
| [02-architecture.md](02-architecture.md) | Arquitectura hexagonal, Docker, código, seguridad y matriz de versiones. |
| [03-api-and-integrations.md](03-api-and-integrations.md) | API REST, endpoints, contratos e integraciones con TheHive, Cortex y Shuffle. |
| [04-operations.md](04-operations.md) | Configuración, infraestructura, backups, certificados, logging, troubleshooting y playbooks. |
| [05-testing.md](05-testing.md) | Estrategia de pruebas, suite, tests unitarios, de integración y E2E. |
| [06-project-management.md](06-project-management.md) | Objetivos, alcance, plan, requisitos, riesgos, deuda técnica y auditorías. |
| [glossary.md](glossary.md) | Glosario central de acrónimos, términos y componentes. |

### 3.2 Assets

- [`assets/images/`](assets/images/) — Capturas de pantalla organizadas por servicio (cortex, thehive, shuffle, docker).
- [`assets/references/`](assets/references/) — Referencias técnicas (OpenAPI, plantillas JSON).

### 3.3 Archivo histórico


### 3.4 Tesis (TFM)

- [`thesis/`](thesis/) — Documentación académica del Trabajo Fin de Máster. Puede incluir resultados parciales o simulados; las capacidades operativas deben validarse contra los documentos principales y el código.

---

## 4. Validación

### 4.1 Verificación

La documentación se mantiene como parte del pipeline CI/CD del proyecto.

### 4.2 Criterios de aceptación

- Todos los enlaces funcionan correctamente
- El contenido está sincronizado con la implementación
- Se sigue el formato y estilo establecido

### 4.3 Evidencias

- Historial de commits en el repositorio
- Reviews de código en pull requests
- Verificación de enlaces en CI/CD

---

## 5. Problemas y consideraciones

### 5.1 Limitaciones

No aplica.

### 5.2 Riesgos o incidencias

- La documentación puede desincronizarse de la implementación si no se actualiza regularmente
- Los enlaces pueden romperse si se reorganiza la estructura de archivos

### 5.3 Recomendaciones / troubleshooting

1. Actualizar secciones relevantes al realizar cambios en el código
2. Mantener la documentación sincronizada con la implementación
3. Ejecutar `vale docs/` para verificar enlaces

---

## 6. Referencias

- [01-getting-started.md](01-getting-started.md)
- [02-architecture.md](02-architecture.md)
- [03-api-and-integrations.md](03-api-and-integrations.md)
- [04-operations.md](04-operations.md)
- [05-testing.md](05-testing.md)
- [06-project-management.md](06-project-management.md)
- [glossary.md](glossary.md)
- [index.md](index.md)
- [Repositorio del Proyecto](https://github.com/alesanfe/soar-ransomware-lab.git)
- [Documentación de Shuffle](https://shuffler.io/docs)
- [Documentación de TheHive](https://docs.strangebee.com/thehive/)
- [Documentación de Cortex](https://docs.strangebee.com/cortex/)
- [Documentación de MISP](https://www.misp-project.org/documentation/)
- [Documentación de Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
