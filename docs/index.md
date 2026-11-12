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
| [18-eval-tc-iso.md](18-eval-tc-iso.md) | Evaluación de test cases (ISO 25010/29119, NIST, MITRE, OWASP) con matriz por TC. |
| [19-eval-observability-stack.md](19-eval-observability-stack.md) | Evaluación ISO del stack de observabilidad (Grafana/Loki/Tempo/ES/Promtail/OTel/Prometheus/cAdvisor). |
| [20-observability-runbooks.md](20-observability-runbooks.md) | Runbooks de observabilidad: alertas, diagnóstico y procedimientos operativos. |
| [20-perf-baseline.md](20-perf-baseline.md) | Baseline de rendimiento del admission path (soak-lite): latencias y throughput medidos. |
| [21-ui-evaluation.md](21-ui-evaluation.md) | Evaluación de interfaces de usuario con evidencia visual (UI-GLOBAL). |
| [22-subtest-evaluation.md](22-subtest-evaluation.md) | Evaluación a nivel subtest de la suite E2E completa. |
| [23-backlog-95-10.md](23-backlog-95-10.md) | Backlog exhaustivo → 9,5/10: todos los subtests faltantes priorizados. |
| [24-observability-backlog-203.md](24-observability-backlog-203.md) | Registro del backlog de observabilidad (203 ítems). |
| [26-e2e-ops-runbook.md](26-e2e-ops-runbook.md) | E2E Ops Runbook: runner, guard, recuperación y matriz de configuración. |
| [rbac-matrix.md](rbac-matrix.md) | Matriz común de roles y permisos (UI-GLOBAL-002). |
| [risk-register.md](risk-register.md) | Registro formal de riesgos aceptados (GOV-004). |
| [references.md](references.md) | Referencias cruzadas de la documentación. |
| [SCRIPTS-MANIFEST.md](SCRIPTS-MANIFEST.md) | Manifiesto de scripts del repositorio (generado). |
| [README.md](README.md) | Guía de lectura del directorio `docs/` (estructura y convenciones). |
| [25-eval-core-stack.md](25-eval-core-stack.md) | Evaluación multi-marco del stack core (TheHive/Cortex/Shuffle/ES/Redis) con ISO 25010/25040, CIS, STRIDE, NIST CSF. Global ~9,5/10. |
| [27-eval-misp-stack.md](27-eval-misp-stack.md) | Evaluación multi-marco del stack MISP (PKI TLS, red dedicada, backups+drill). Global ~9,5/10. |
| [28-eval-taxii-stack.md](28-eval-taxii-stack.md) | Evaluación multi-marco del servidor TAXII 2.1 (medallion endurecido, creds por env, ti_net). Global ~9,5/10. |
| [29-eval-sso-stack.md](29-eval-sso-stack.md) | Evaluación multi-marco del stack SSO (Keycloak + oauth2-proxy: realm templated, brute-force, non-root). Global ~9,5/10. |
| [30-eval-victim-stack.md](30-eval-victim-stack.md) | Evaluación multi-marco del victim-sim (nobody, cap_drop ALL, RO rootfs). Global ~9,5/10. |
| [31-eval-supply-chain.md](31-eval-supply-chain.md) | Evaluación multi-marco de la cadena de suministro / CI-CD (SLSA, SSDF, OWASP SCVS): pinning, permisos, Dependabot, lock, firma cosign. Global ~9,5/10. |
| [32-eval-api.md](32-eval-api.md) | Evaluación multi-marco de la API SOAR (FastAPI hexagonal, ASVS, STRIDE, CWE): auth default-deny, rate-limit, JWT, admission queue. Global ~9,5/10. |
| [33-eval-observability.md](33-eval-observability.md) | Evaluación multi-marco del stack de observabilidad (Grafana/Loki/Prometheus/Promtail/Tempo/OTEL/blackbox/cAdvisor/S3): 0 privileged, promtail→proxy, secrets fail-closed. Global ~9,5/10. |
| [34-eval-frontend.md](34-eval-frontend.md) | Evaluación multi-marco de la superficie frontend (web-management, docs-site, edge nginx): proxy /api+WS, capless uid 101, RO rootfs, edge loopback, XSS auditado. Global ~9,5/10. |
| [35-eval-backup-dr.md](35-eval-backup-dr.md) | Evaluación multi-marco del sistema backup/DR (NIST CSF RECOVER, 3-2-1): cobertura 100%, sha256+manifest, drills con RTO medido, retención. Global ~9,5/10. |
| [36-eval-domain-content.md](36-eval-domain-content.md) | Evaluación multi-marco del contenido de dominio (Sigma, playbook Shuffle, catálogo ATT&CK/D3FEND, exports CACAO/STIX). Global ~9,5/10. |
| [37-eval-admission-pipeline.md](37-eval-admission-pipeline.md) | Evaluación multi-marco del pipeline de admisión (Redis Streams, worker, lease, DLQ, forward firmado). Global ~9,5/10. |
| [38-eval-pki-secrets.md](38-eval-pki-secrets.md) | Evaluación multi-marco de la PKI interna y gestión de secretos (CA, certs, rotación, expiración monitorizada). Global ~9,5/10. |
| [39-eval-network-perimeter.md](39-eval-network-perimeter.md) | Evaluación multi-marco del perímetro de red (egress guard, network watcher, attach zero-trust). Global ~9,5/10. |
| [40-eval-data-layer.md](40-eval-data-layer.md) | Evaluación multi-marco de la capa de datos (SQLite, index templates/ILM de ES, ISM de OpenSearch, divergencia de persistencia). Global ~9,5/10. |
| [41-eval-test-suite.md](41-eval-test-suite.md) | Evaluación de la suite de tests como activo (oráculos, falsos verdes, ratchet e2e, higiene de secretos, mutation governance). Global ~9,5/10. |
| [42-eval-simulator.md](42-eval-simulator.md) | Evaluación del simulador de alertas (fidelidad de IoCs, contrato del validador, retry, packaging, CLI). Global ~9,5/10. |
| [43-eval-docs-product.md](43-eval-docs-product.md) | Evaluación de la documentación como producto (índice, OpenAPI sync, gates de calidad, sitio Docusaurus). Global ~9,5/10. |
| [44-eval-operational-tooling.md](44-eval-operational-tooling.md) | Evaluación del tooling operacional (paridad Makefiles, .PHONY, manifiesto de scripts, doctor/preflight). Global ~9,5/10. |
| [45-eval-residual-hardening.md](45-eval-residual-hardening.md) | Cierre de residuales endurecibles: suites locales en CI, Redis TLS en doctor, lychee bloqueante, Docusaurus throw, skips explícitos. Global ~9,5/10. |
| [46-eval-core-stack-iso-cis-nist.md](46-eval-core-stack-iso-cis-nist.md) | Re-evaluación del core stack (ES, OpenSearch, Redis, TheHive, Cortex, Shuffle) bajo ISO 27001 A.8/A.12/A.13, CIS 4/5/12 y NIST CSF PR.PS: TLS, cifrado, segmentación, credenciales, HA, healthchecks, hardening, vulnerabilidades. Global ~9,6/10. |
| [47-eval-misp-iso-cti.md](47-eval-misp-iso-cti.md) | Re-evaluación de MISP bajo ISO 27001 A.5.7/A.5.17/A.8, NIST SP 800-150 (CTI) y estándares STIX/TAXII: feeds, autenticación, PKI, compartición de IoCs, calidad de datos, control de acceso, taxonomías. Global ~9,4/10. |
| [48-eval-taxii-iso-cti.md](48-eval-taxii-iso-cti.md) | Re-evaluación de TAXII bajo ISO 27001 A.5.7/A.8, NIST SP 800-150 (CTI) y estándares STIX 2.1/TAXII 2.1: medallion + superficie lite, feeds, autenticación, PKI, compartición, calidad STIX, control de acceso. Global ~9,4/10. |
| [49-eval-sso-80063-oidc.md](49-eval-sso-80063-oidc.md) | Re-evaluación de SSO (Keycloak + oauth2-proxy) bajo ISO 27001 A.5/A.8, NIST SP 800-63 y OIDC/OAuth2 BCP: TLS end-to-end, MFA TOTP, rotación de refresh tokens, sesiones, roles, logout. Global ~9,6/10. |
| [50-eval-victim-mitre-caldera.md](50-eval-victim-mitre-caldera.md) | Re-evaluación del victim simulator bajo MITRE ATT&CK, CALDERA y Atomic Red Team: telemetría real a Loki (/proc/1/fd/1), kill-chain ransomware 10 TTPs/8 tácticas, perfil adversario + cleanup. Global ~9,5/10. |
| [51-eval-supply-chain-slsa-ssdf.md](51-eval-supply-chain-slsa-ssdf.md) | Re-evaluación supply chain/CI-CD bajo SLSA, NIST SSDF, ISO 27034 y SP 800-218: SBOM CycloneDX, cosign keyless, provenance L3, FROM digest-pinned, locks, secret scan, gates CI. Global ~9,6/10. |
| [52-eval-api-asvs.md](52-eval-api-asvs.md) | Re-evaluación del API custom SOAR bajo OWASP ASVS, API Security Top 10 e ISO 27034: AuthN/AuthZ, validación, rate limiting, errores, trazabilidad, observabilidad, hexagonal. Global ~9,6/10. |
| [53-eval-observability-otel-sre.md](53-eval-observability-otel-sre.md) | Re-evaluación de observabilidad bajo OpenTelemetry, SRE Golden Signals e ISO 27001 A.8: métricas/logs/trazas, retención, alertado burn-rate SLO, dashboards, visibilidad TLS. Global ~9,6/10. |
| [54-eval-frontend-cis-asvs-800190.md](54-eval-frontend-cis-asvs-800190.md) | Re-evaluación del serving frontend bajo CIS Docker Benchmark, OWASP ASVS y NIST 800-190: nginx hardening, capless, CSP, HSTS, TLS, healthchecks, aislamiento. Global ~9,6/10. |
| [55-eval-backup-dr-iso-22301.md](55-eval-backup-dr-iso-22301.md) | Re-evaluación de Backup/DR bajo ISO 22301, ISO 27031 y NIST SP 800-34: RPO/RTO, restauración real, cifrado AES-256, drills periódicos en CI, integridad, resiliencia. Global ~9,5/10. |
| [56-eval-domain-content-attack-cacao.md](56-eval-domain-content-attack-cacao.md) | Re-evaluación del contenido de dominio bajo MITRE ATT&CK, D3FEND, Sigma, STIX 2.1 y CACAO: calidad de reglas, cobertura, exports válidos, mapeo defensivo, automatización. Global ~9,4/10. |
| [57-eval-admission-pipeline-nist-cncf.md](57-eval-admission-pipeline-nist-cncf.md) | Re-evaluación del admission pipeline bajo NIST Reliability y CNCF resiliency: idempotencia, DLQ, retry, backpressure, ordering, observabilidad, recuperación. Global ~9,6/10. |
| [58-eval-pki-secrets-80057-owasp.md](58-eval-pki-secrets-80057-owasp.md) | Re-evaluación PKI/secretos bajo ISO 27001 A.8, NIST 800-57 y OWASP Secrets Management: rotación, almacenamiento, expiración, confianza CA, auditoría, distribución. Global ~9,3/10. |
| [59-eval-network-perimeter-800207-cis.md](59-eval-network-perimeter-800207-cis.md) | Re-evaluación del perímetro bajo NIST 800-207 (Zero Trust) y CIS 12/13: egress, segmentación, deny-all, inventario de flujos, TLS inspection. Global ~9,5/10. |
| [60-eval-test-suite-iso29119-samm.md](60-eval-test-suite-iso29119-samm.md) | Re-evaluación de la suite de tests bajo ISO 29119, OWASP SAMM y NIST SSDF: cobertura, oráculos, test-data, pipeline, secretos. Global ~9,6/10. |
| [61-eval-simulator-attack-art.md](61-eval-simulator-attack-art.md) | Re-evaluación del simulador de alertas bajo MITRE ATT&CK y Atomic Red Team: fidelidad técnica, eventos, estabilidad, telemetría. Global ~9,5/10. |
| [62-eval-docs-product-iso9001-devops.md](62-eval-docs-product-iso9001-devops.md) | Re-evaluación de docs como producto bajo ISO 9001 y docs-as-code: discoverability, enlaces, publicación consistente. Global ~9,6/10. |
| [63-eval-operational-tooling-sre-devops.md](63-eval-operational-tooling-sre-devops.md) | Re-evaluación del tooling operacional bajo SRE y DevOps Capability: reproducibilidad, paridad de entornos, enforcement. Global ~9,6/10. |
| [64-eval-residual-hardening-cis-80053.md](64-eval-residual-hardening-cis-80053.md) | Barrido transversal de superficie de ataque y deuda bajo CIS/NIST 800-53/ISO 27001: edge EOL corregido, cero deuda activa verificada. Global ~9,6/10. |
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
