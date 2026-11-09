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
| ----------- | ------------- |
| [01-getting-started.md](01-getting-started.md) | Visión general, requisitos, instalación, primer acceso y guía rápida. |
| [02-architecture.md](02-architecture.md) | Arquitectura hexagonal, Docker, código, seguridad y matriz de versiones. |
| [03-api-and-integrations.md](03-api-and-integrations.md) | API REST, endpoints, contratos e integraciones con TheHive, Cortex y Shuffle. |
| [04-operations.md](04-operations.md) | Configuración, infraestructura, backups, certificados, logging, troubleshooting y playbooks. |
| [05-testing.md](05-testing.md) | Estrategia de pruebas, suite, tests unitarios, de integración y E2E. |
| [06-project-management.md](06-project-management.md) | Objetivos, alcance, plan, requisitos, riesgos, deuda técnica y auditorías. |
| [07-framework-evaluation.md](07-framework-evaluation.md) | Evaluación de marcos (NIST, MITRE, OWASP, CIS, ISO) con evidencia. |
| [08-execution-profiles.md](08-execution-profiles.md) | Perfiles laboratorio/desarrollo/CI/hardened y su configuración. |
| [09-traceability-matrix.md](09-traceability-matrix.md) | Matriz requisitos → componentes → tests → KPIs y riesgos residuales. |
| [10-framework-validation-exhaustive.md](10-framework-validation-exhaustive.md) | Validación control-a-control de los 10 marcos + ISO 27001 Annex A, con evidencia en vivo. |
| [11-final-validation-report.md](11-final-validation-report.md) | Informe final: E2E, seguridad en vivo, KPIs vs baseline y matriz definitiva. |
| [12-framework-validation-extended.md](12-framework-validation-extended.md) | Segunda ronda: NIST IR 8374, ISO 27002, 800-53r5, CIS v8, ASVS, SAMM, SSDF, SLSA, 12-Factor, RGPD, RE&CT, TLP, OpenC2, CWE. |
| [13-defect-driven-testing.md](13-defect-driven-testing.md) | Política de confirmación de bugs (failing-first): registro BUG-001..066, técnicas §8, DoD, plantillas y métricas. |
| [14-framework-validation-iso-models.md](14-framework-validation-iso-models.md) | Cuarta ronda: ISO 29119/TMMi/5055/IEEE 1012, ISO 27005/27043/27039, NIST 800-137/150/190/184/37, Kill Chain, Diamond, SOC-CMM/SIM3/MaGMa, DSOMM. |
| [15-project-evaluation-scorecard.md](15-project-evaluation-scorecard.md) | Evaluación integral por campos: fortalezas, debilidades, mejoras priorizadas y nota /10 en 16 dimensiones (global 7,9/10). |
| [16-formal-audit-iso25040.md](16-formal-audit-iso25040.md) | Auditoría formal ISO 25040: puntuación control-a-control E0–E4, puertas de calidad, hallazgos y backlog. 67/100 → 5,9/10 (cap GATE-2 lab) / 6,7/10 (hardened). |
| [17-technical-backlog-9of10.md](17-technical-backlog-9of10.md) | Backlog técnico priorizado P0–P3 hacia ≥9/10: criterios de aceptación, esfuerzo, gates finales y orden de despliegue. |
| [18-e2e-suite-backlog-9of10.md](18-e2e-suite-backlog-9of10.md) | Backlog maestro de la suite E2E (5,6→9/10): eliminación de falsos verdes, correlación, aislamiento, contratos, evidencia E4 y gates de concesión. |
| [19-threat-model-stride.md](19-threat-model-stride.md) | Threat model STRIDE de la superficie real de la API: amenazas → controles verificados → residuales aceptados. |
| [`adr/`](adr/0000-index.md) | Architecture Decision Records — decisiones tomadas y verificadas en código (0001-0008). |
| [`runbooks/`](runbooks/README.md) | Runbooks operativos de los modos de fallo observados (Redis, MISP, SQLite, TheHive, Shuffle, ES, DLQ). |
| [glossary.md](glossary.md) | Glosario central de acrónimos, términos y componentes. |

### 3.2 Assets

- `assets/images/` — Capturas de pantalla organizadas por servicio.
- `assets/references/` — Referencias técnicas (OpenAPI, plantillas JSON).

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
- [07-framework-evaluation.md](07-framework-evaluation.md)
- [08-execution-profiles.md](08-execution-profiles.md)
- [09-traceability-matrix.md](09-traceability-matrix.md)
- [10-framework-validation-exhaustive.md](10-framework-validation-exhaustive.md)
- [11-final-validation-report.md](11-final-validation-report.md)
- [12-framework-validation-extended.md](12-framework-validation-extended.md)
- [13-defect-driven-testing.md](13-defect-driven-testing.md)
- [14-framework-validation-iso-models.md](14-framework-validation-iso-models.md)
- [15-project-evaluation-scorecard.md](15-project-evaluation-scorecard.md)
- [16-formal-audit-iso25040.md](16-formal-audit-iso25040.md)
- [17-technical-backlog-9of10.md](17-technical-backlog-9of10.md)
- [18-e2e-suite-backlog-9of10.md](18-e2e-suite-backlog-9of10.md)
- [19-threat-model-stride.md](19-threat-model-stride.md)
- [adr/0000-index.md](adr/0000-index.md)
- [runbooks/README.md](runbooks/README.md)
- [glossary.md](glossary.md)
