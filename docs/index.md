# Índice de Documentación — SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
  - [1.1 Objetivo](#11-objetivo)
  - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
  - [2.1 Qué cubre](#21-qué-cubre)
  - [2.2 Límites](#22-límites)
  - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 Documentos principales](#31-documentos-principales)
  - [3.2 Assets](#32-assets)
  - [3.3 Archivo histórico](#33-archivo-histórico)
- [4. Validación](#4-validación)
  - [4.1 Verificación](#41-verificación)
  - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
  - [4.3 Evidencias](#43-evidencias)
- [5. Problemas](#5-problemas)
  - [5.1 Limitaciones](#51-limitaciones)
  - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
  - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones--troubleshooting)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Servir como punto de entrada único a la documentación técnica del SOAR Ransomware Lab, indexando los 6 documentos principales, los assets y el archivo histórico.

### 1.2 Contexto

---

## 2. Alcance

### 2.1 Qué cubre

- Índice de los 6 documentos principales
- Referencias a assets (imágenes, OpenAPI)
- Referencias al archivo histórico (TFM, auditorías, obsoletos)

### 2.2 Límites

- No incluye contenido técnico — solo enlaces
- No cubre documentación interna del código (docstrings)

### 2.3 Dependencias

- Los 6 documentos principales deben existir en `docs/`
- Los assets deben estar en `docs/assets/`

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

- [`assets/images/`](assets/images/) — Capturas de pantalla organizadas por servicio.
- [`assets/references/`](assets/references/) — Referencias técnicas (OpenAPI, plantillas JSON).

### 3.3 Archivo histórico

---

## 4. Validación

### 4.1 Verificación

Se verifica que todos los enlaces del índice apuntan a archivos existentes mediante `vale` y revisión manual.

### 4.2 Criterios de aceptación

- Los 6 documentos principales existen y siguen la estructura estándar de 6 secciones
- Los enlaces a assets y archive son válidos

### 4.3 Evidencias

- Resultados de `vale` en CI
- `ls docs/` muestra los 6 archivos + glossary.md + index.md

---

## 5. Problemas

### 5.1 Limitaciones

- El índice no incluye contenido técnico, solo enlaces

### 5.2 Riesgos o incidencias

- Enlaces rotos si se renombran archivos sin actualizar este índice

### 5.3 Recomendaciones / troubleshooting

- Actualizar este índice al añadir o renombrar documentos principales
- Ejecutar `vale docs/` para verificar enlaces

---

## 6. Referencias

- [01-getting-started.md](01-getting-started.md)
- [02-architecture.md](02-architecture.md)
- [03-api-and-integrations.md](03-api-and-integrations.md)
- [04-operations.md](04-operations.md)
- [05-testing.md](05-testing.md)
- [06-project-management.md](06-project-management.md)
- [glossary.md](glossary.md)
