# Evaluación de marcos — SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
- [2. Alcance](#2-alcance)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 NIST SP 800-61 / ISO/IEC 27035](#31-nist-sp-800-61--isoiec-27035---cobertura-alta)
  - [3.2 MITRE ATT&CK y MITRE D3FEND](#32-mitre-attck-y-mitre-d3fend---sobresaliente)
  - [3.3 CACAO](#33-cacao)
  - [3.4 NIST CSF 2.0 y NIST SP 800-207](#34-nist-csf-20-y-nist-sp-800-207---buena)
  - [3.5 OWASP API Top 10](#35-owasp-api-top-10---buena-con-mejoras-aplicadas)
  - [3.6 ISO/IEC 25010](#36-isoiec-25010---sobresaliente)
  - [3.7 CIS Docker](#37-cis-docker)
- [4. Validación](#4-validación)
- [5. Problemas](#5-problemas)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Consolidar la evaluación del laboratorio frente a los marcos de
ciberseguridad y calidad que declara implementar, distinguiendo entre
cobertura **real**, **simulada** y **parcial**, con evidencia trazable a
código, tests o documentación.

### 1.2 Contexto

Evaluación realizada sobre la versión 1.4.0 del laboratorio, tras la
ejecución de la suite completa (unit 1282, architecture/atomic 102,
integration/security/contracts 360, external 103, E2E TC-00..33 + KPIs).

## 2. Alcance

### 2.1 Qué cubre

Los 10 marcos declarados en el backlog: NIST SP 800-61, ISO/IEC 27035,
MITRE ATT&CK, MITRE D3FEND, CACAO, NIST CSF 2.0, NIST SP 800-207,
OWASP API Top 10, ISO/IEC 25010 y CIS Docker.

### 2.2 Límites

- La contención es **simulada** (`status="simulated"` en
  `/api/v1/contain`); no hay integración EDR/firewall real. Ninguna
  evaluación lo presenta como respuesta real.
- Es un laboratorio de investigación: los criterios de seguridad se
  evalúan en ese contexto, no contra un despliegue de producción.

### 2.3 Dependencias

Resultados E2E en `reports/e2e/` y suite de tests en `tests/`.

## 3. Contenido principal

### 3.1 NIST SP 800-61 / ISO/IEC 27035 — ✅ Cobertura alta

| Fase del ciclo | Cobertura | Evidencia |
| --- | --- | --- |
| Preparación | Real | Stack reproducible (`make up`, 19 pasos), generación de secretos, playbooks documentados |
| Detección y análisis | Real | Simulador SIEM → webhook Shuffle → enriquecimiento Cortex (44 analyzers) + MISP + VirusTotal |
| Contención | **Simulada** | Nodo `containment` llama a `/api/v1/contain` que registra la acción sin ejecutarla |
| Erradicación/recuperación | Real (nivel lab) | Backup/restore verificado en TC-22, persistencia de casos e IoCs |
| Post-incidente | Real | KPIs MTTR (TC-KPI-01..06), trazabilidad golden thread (TC-32), forense (TC-21), IoCs reales gminst4ll (TC-33) |

### 3.2 MITRE ATT&CK y MITRE D3FEND — ✅ Sobresaliente

- `MITREInfo` valida formato `TAxxxx`/`Txxxx(.xxx)`; scoring pondera 9
  técnicas de alto riesgo.
- TC-29/TC-31 verifican alineación acción ↔ mitigación D3FEND.
- Los workflows llevan metadatos ATT&CK por fase; TC-33 usa IoCs reales
  de campaña (gminst4ll).

### 3.3 CACAO — ⚠️ Parcial {#33-cacao}

El workflow SOAR es un playbook operativo ejecutado en Shuffle
(JSON propietario de Shuffle), no serializado en formato CACAO. La
semántica playbook (trigger → enrichment → decision → action) es
equivalente; falta exportación al estándar.

### 3.4 NIST CSF 2.0 y NIST SP 800-207 — ✅ Buena

- CSF: Identify/Protect/Detect/Respond/Recover cubiertos por diseño
  (TC-14 valida el flujo completo).
- Zero Trust: segmentación en 3 redes (`soar_net`, `ti_net`,
  `logging_net`) verificada por TC-20; modo air-gap en TC-30.

### 3.5 OWASP API Top 10 — ✅ Buena con mejoras aplicadas

| Riesgo | Estado | Evidencia |
| --- | --- | --- |
| API1 Broken Object Level Auth | Mitigado | JWT + RBAC (`auth_service`) |
| API2 Broken Authentication | Mitigado | JWT con exp/iat, tests de falsificación |
| API4 Unrestricted Resource Consumption | **Mitigado (nuevo)** | `RateLimitMiddleware` con presupuestos por cliente y reglas estrictas (`/auth` 10/min, `/api/v1/contain` 30/min); HTTP 429 + headers `X-RateLimit-*` (SOAR-010) |
| API5 Broken Function Level Auth | **Mejorado** | `require_api_auth` opcional (JWT o `X-Service-Token`) en `/backup/*`, `/tests/run`, `/api/v1/contain`, `/api/v1/cache/ioc` vía `API_REQUIRE_AUTH` (SOAR-011) |
| API8 Security Misconfiguration | Parcial | Swagger configurable (`API_DOCS_ENABLED`, SOAR-017); TLS 1.2/1.3 en Nginx |
| API9 Improper Inventory | Buena | Contratos OpenAPI versionados, test de sync |

### 3.6 ISO/IEC 25010 — ✅ Sobresaliente

- **Mantenibilidad**: arquitectura hexagonal enforceada por tests AST,
  complejidad ≤ 15, docstrings 94.6 %, Vulture 0 hallazgos tras SOAR-020.
- **Fiabilidad**: circuit breaker, retry, timeout, modo degradado (TC-18),
  recuperación de servicios (TC-16).
- **Seguridad**: PayloadSanitizer exhaustivo, suite de seguridad
  (LDAPi, traversal, XSS, JWT forgery, payloads 1 MB).
- **Portabilidad**: stack completo en Compose, perfiles de ejecución
  documentados en `08-execution-profiles.md`.
- **Eficiencia**: tests de rendimiento y latencia (TC-04, TC-15, TC-26).

### 3.7 CIS Docker — ⚠️ Aceptable para laboratorio {#37-cis-docker}

| Control | Lab | Hardened |
| --- | --- | --- |
| `docker.sock` montado | 4 contenedores raw (api, orborus, network-watcher, promtail) + cortex vía socket proxy de Docker Desktop — verificado en vivo con `docker inspect` | api + network-watcher usan `docker-socket-proxy` con verbos limitados (SOAR-012) |
| `seccomp:unconfined` | orborus | eliminado vía `security_opt: !reset []` (SOAR-013) |
| `user: root` | api, redis | `API_UID/API_GID`, usuario `redis` (SOAR-014) |
| TLS verify (OpenSearch) | `SKIPSSL_VERIFY=true` | parametrizable por env (SOAR-015) |
| Tenzir `--mode=dev` | activo | `TENZIR_WEB_MODE` (SOAR-016) |
| `.env.full` en contenedor | montado | `.env.container` filtrado + `:ro` (SOAR-018) |
| Digest de imágenes | verificado (no bloqueante) | idem |

Excepción documentada: orborus conserva el socket porque *spawnea*
contenedores de trabajo — un proxy no reduce materialmente el riesgo
ahí. Cortex accede al daemon a través de `/run/host-services/
docker.proxy.sock` (proxy de Docker Desktop, ya no raw). Shuffle-backend
y promtail: backend no monta socket; promtail lo usa solo lectura para
descubrimiento de logs.

## 4. Validación

### 4.1 Verificación

Cada afirmación enlaza a tests (`tests/e2e/TC-*`), código
(`src/soar_lab/`) o configuración (`infra/docker/compose/`).

### 4.2 Criterios de aceptación

- Cobertura real vs simulada diferenciada: ✅ (§3.1, §3.3).
- Limitaciones del laboratorio documentadas: ✅ (§2.2, §5).
- Resultados E2E actuales incorporados: ✅ (§2.1).

### 4.3 Evidencias

`reports/e2e/e2e_report.md`, `tests/e2e/TC-29`, `tests/e2e/TC-32`,
`tests/security/`, `infra/docker/compose/docker-compose.hardened.yml`.

## 5. Problemas

### 5.1 Limitaciones

- CACAO: no hay exportación del workflow al formato estándar.
- Contención simulada por diseño; extrapolar a producción requiere
  adaptadores EDR/firewall reales.
- La verificación TLS de OpenSearch en hardened requiere una CA
  propia (ver `08-execution-profiles.md`).

### 5.2 Riesgos o incidencias

- `.env.full` está versionado en git con credenciales de laboratorio —
  decisión aceptada por el autor (proyecto académico, RR-01 en
  `09-traceability-matrix.md`).
- Logs de MISP y shuffle-backend imprimen valores sensibles en
  arranque (detectado por `scan_secrets.py`).

### 5.3 Recomendaciones

- Mantener la distinción real/simulado/parcial en la memoria del TFM.
- Considerar export CACAO como trabajo futuro.

## 6. Referencias

- `docs/02-architecture.md`, `docs/04-operations.md`
- `docs/08-execution-profiles.md`, `docs/09-traceability-matrix.md`
- NIST SP 800-61r2, ISO/IEC 27035, MITRE ATT&CK, D3FEND, CACAO spec,
  NIST CSF 2.0, NIST SP 800-207, OWASP API Security Top 10 (2023),
  ISO/IEC 25010, CIS Docker Benchmark.
