# Validación de marcos — segunda ronda (otras ISOs, patrones y marcos)

## Índice

- [1. Resumen](#1-resumen)
- [2. Alcance](#2-alcance)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 NIST IR 8374 — Ransomware Risk Management](#31-nist-ir-8374--ransomware-risk-management)
  - [3.2 ISO/IEC 27002:2022](#32-isoiec-270022022)
  - [3.3 NIST SP 800-53r5](#33-nist-sp-800-53r5)
  - [3.4 CIS Critical Security Controls v8](#34-cis-critical-security-controls-v8)
  - [3.5 OWASP ASVS 4.0](#35-owasp-asvs-40)
  - [3.6 OWASP SAMM 2.0](#36-owasp-samm-20)
  - [3.7 NIST SSDF (SP 800-218)](#37-nist-ssdf-sp-800-218)
  - [3.8 SLSA 1.0](#38-slsa-10)
  - [3.9 Twelve-Factor App](#39-twelve-factor-app)
  - [3.10 RGPD / privacidad](#310-rgpd--privacidad)
  - [3.11 RE&CT](#311-rect)
  - [3.12 FIRST TLP / PAP](#312-first-tlp--pap)
  - [3.13 OpenC2](#313-openc2)
  - [3.14 CWE Top 25](#314-cwe-top-25)
  - [3.15 Patrones de diseño (SOLID / hexagonal / 12-factor resumen)](#315-patrones-de-diseño)
- [4. Validación](#4-validación)
- [5. Problemas](#5-problemas)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Complementar `docs/10` (10 marcos primarios) con una **segunda ronda**
de marcos, ISOs y patrones aplicables a la totalidad del proyecto:
respuesta a ransomware, catálogo ISO 27002, controles 800-53, CIS v8,
ASVS, SAMM, SSDF, cadena de suministro (SLSA), metodología cloud
(12-Factor), privacidad (RGPD), ciclo de respuesta (RE&CT), estándares
de marcado (TLP/PAP), orquestación alternativa (OpenC2) y debilidades
de software (CWE Top 25).

### 1.2 Contexto

Mismo enfoque que docs/10: veredicto por control (✅/🟡/➖/❌) con
evidencia verificable — fichero, test, comando ejecutado. Evaluado
sobre el stack de 23 contenedores y el árbol de fuentes actual.

## 2. Alcance

### 2.1 Qué cubre

14 marcos/patrónes adicionales, control a control donde el marco lo
permite. Cobertura de **todo el proyecto**: código `src/`, `tests/`,
`infra/`, `scripts/`, `docs/`, CI y operación del stack.

### 2.2 Límites

- Contexto laboratorio académico (igual que docs/10).
- ISO 27002 se evalúa por subconjunto aplicable (los controles físicos,
  de RRHH y proveedor no aplican a un proyecto de software).
- 800-53r5 se evalúa por familias seleccionadas (AC, AU, IA, IR, RA,
  SC, SI, CP, CM, SA, SR).

### 2.3 Dependencias

`docs/10-framework-validation-exhaustive.md` (ronda 1, evidencia base).

## 3. Contenido principal

### 3.1 NIST IR 8374 — Ransomware Risk Management

Perfil CSF específico para ransomware — **el marco más directamente
aplicable al laboratorio**:

| Función | Veredicto | Evidencia |
| --- | --- | --- |
| **Identify** — inventario y riesgo | ✅ | 23 servicios inventariados en compose; matriz RR-01..07 (`docs/09`); `make ps/health` |
| **Protect** — backups | ✅ | `make backup`/`make restore`; `BackupService` con validación de nombre (path traversal testado); TC-22 `test_backup_integrity`/`test_backup_restore` |
| Protect — protección de datos | ✅ | secretos generados (`generate_secrets.py`), `.env.container` :ro, TLS, scrub Promtail |
| **Detect** — alertas SIEM | ✅ | simulador (`simulate_alerts.py`) con mitre_info real; webhook Shuffle; 53 técnicas ATT&CK |
| Detect — indicadores ransomware | ✅ | TC-09 ransomware realista, TC-24 específico malware, TC-33 IoCs reales gminst4ll |
| **Respond** — playbook | ✅ | workflow completo detect→enrich→decide→act→notify; TheHive + notificación |
| Respond — contención | ✅ | `mode=enforce` real (disconnect+pause) o `simulated` |
| **Recover** — restauración | ✅ | `test_backup_restore`, `test_docker_down_up`, `test_container_recreation`, `test_data_consistency_after_restart` |
| Recover — lecciones | 🟡 | informes E2E/KPI generados; post-incidente formal es académico |

**Veredicto: 8/9 ✅** — la función Recover está genuinamente testeada,
lo cual es inusual en laboratorios.

### 3.2 ISO/IEC 27002:2022

Subconjunto aplicable (24 controles tecnológicos/organizativos):

| Control | Veredicto | Evidencia |
| --- | --- | --- |
| A.5.23 Servicios cloud | ➖ | lab autoalojado; aplica en despliegue cloud |
| A.5.31 Requisitos legales | ✅ | RGPD vía TC-23; contexto académico documentado |
| A.5.34 Privacidad y PII | ✅ | 7 tests TC-23 (masking, redaction, minimization) |
| A.8.2 Acceso privilegiado | 🟡 | api/redis root en lab; non-root en hardened |
| A.8.3 Restricción de acceso | ✅ | JWT+RBAC+`X-Service-Token`; `require_api_auth` |
| A.8.5 Autenticación segura | ✅ | JWT exp/iat, RBAC, tests anti-bypass (SOAR-028) |
| A.8.7 Protección malware | ✅ | pipeline detección→respuesta (objeto del lab) |
| A.8.8 Gestión de vulnerabilidades | 🟡 | bandit+scan-secrets+trufflehog; sin scanner CVE de imágenes (trivy/grype) — mejora |
| A.8.9 Gestión de configuración | ✅ | compose+templates+preflight+hardened overlay |
| A.8.11 Enmascaramiento de datos | ✅ | `test_pii_masking` + Promtail `<REDACTED>` |
| A.8.12 Prevención de fuga | ✅ | scan-secrets (repo/logs/imágenes) + trufflehog CI |
| A.8.13 Backup | ✅ | TC-22 (9 tests persistencia/restore) |
| A.8.14 Redundancia | 🟡 | restart policies 23/23; ES single-node (amarillo normal) |
| A.8.15 Registro (logging) | ✅ | Promtail→Loki todos los contenedores; x-request-id |
| A.8.16 Monitorización | ✅ | Grafana dashboards, healthchecks 23/23, `/services/status`, `/metrics` |
| A.8.20 Seguridad de red | ✅ | 3 redes aisladas; nginx única puerta TLS |
| A.8.22 Segregación | ✅ | soar_net/ti_net/logging_net; API en las 3 como puente único |
| A.8.24 Criptografía | ✅ | TLS 1.2/1.3 `HIGH:!aNULL:!MD5`; secrets 32+ bytes |
| A.8.25 Ciclo de vida seguro | ✅ | hexagonal, pre-commit, CI multi-job, perfiles |
| A.8.28 Codificación segura | ✅ | ruff/black/isort/flake8/mypy/bandit gates |
| A.8.29 Pruebas de seguridad | ✅ | tests/security + SOAR-028 (inyección, JWT, payloads) |
| A.8.31 Separación entornos | ✅ | `.env.testing` vs `.env.full`; perfiles lab/hardened |
| A.8.32 Gestión de cambios | 🟡 | git + CI; sin CAB formal (académico) |
| A.8.34 Test de aceptación | ✅ | suites E2E como criterio de aceptación |

**Veredicto: 18/24 ✅, 5 🟡, 1 ➖** — cobertura tecnológica sólida.

### 3.3 NIST SP 800-53r5

Familias seleccionadas:

| Control | Veredicto | Evidencia |
| --- | --- | --- |
| AC-2 Account management | ✅ | usuarios API + service tokens + credenciales por servicio |
| AC-3 Access enforcement | 🟡→✅ | `require_api_auth` opt-in; hardened enforce |
| AC-6 Least privilege | 🟡 | caps mínimas excepto AUDIT_WRITE MISP; non-root en hardened |
| AC-17 Remote access | ✅ | solo localhost publicado; TLS nginx |
| AU-2 Audit events | ✅ | x-request-id, test_audit_trail (TC-02) |
| AU-6 Audit review | ✅ | Loki query, Kibana/Grafana, e2e reports |
| AU-9 Audit protection | 🟡 | logs de docker mutables; Loki append-only |
| AU-12 Audit generation | ✅ | promtail docker_sd + pipeline_stages |
| IA-2 Identification/auth | ✅ | JWT firmado HS256 con secret 32B+ |
| IA-5 Credential mgmt | ✅ | generados, no hardcoded, en `.env.container` :ro |
| IR-4 Incident handling | ✅ | el propio lab implementa IR-4 |
| IR-5 Monitoring | ✅ | pipeline detect→alert continuo |
| IR-6 Reporting | ✅ | TheHive + notificaciones + métricas |
| IR-8 Response plan | ✅ | playbook + CACAO export + docs |
| RA-5 Vulnerability scanning | 🟡 | bandit+secrets; sin CVE scan de imágenes |
| SC-7 Boundary protection | ✅ | 3 redes + nginx gateway |
| SC-8 Transmission confidentiality | ✅ | TLS 1.2/1.3 externo; interno plano (documentado) |
| SC-12 Key mgmt | ✅ | secretos generados, no en imagen |
| SC-28 Data at rest | 🟡 | volúmenes sin cifrar (Docker Desktop) |
| SI-4 System monitoring | ✅ | Grafana/healthchecks/metrics |
| SI-5 Security alerts | ✅ | pipeline de alertas (función del lab) |
| SI-7 Integrity | 🟡 | digests verificados 17/17; sin firmas cosign |
| CP-9 Backup | ✅ | make backup + TC-22 |
| CP-10 Recovery | ✅ | TC-22 restore + recreate + consistency |
| CM-2 Baseline config | ✅ | compose + hardened overlay versionados |
| CM-7 Least functionality | 🟡 | puertos mínimos publicados; servicios lab amplios por diseño |
| SA-11 DevSecOps testing | ✅ | CI lint+tests+trufflehog |
| SR-11 Component authenticity | 🟡 | digests 17/17; sin firma provenance |

**Veredicto: 18 ✅, 10 🟡, 0 ❌** — los 🟡 concentrados en cadena de
suministro (firma/CVE-scan) y cifrado en reposo.

### 3.4 CIS Critical Security Controls v8

IG1 (56 safeguards) — los aplicables:

| Control | Veredicto | Evidencia |
| --- | --- | --- |
| 1 Inventario activos empresa | ✅ | compose 23 servicios + `docker ps` |
| 2 Inventario software | ✅ | `pyproject.toml` bounded + `requirements-docker.lock` |
| 3 Protección de datos | ✅ | secretos gestionados, scrub, masking |
| 4 Config segura | ✅ | compose + hardened + preflight |
| 5 Gestión de cuentas | ✅ | usuarios servicio + tokens dedicados |
| 6 Control de acceso | ✅ | RBAC + require_api_auth |
| 7 Gestión de vulnerabilidades | 🟡 | sin CVE scan continuo de imágenes |
| 8 Gestión de audit log | ✅ | Loki + retention + request-id |
| 9 Email/web protections | ➖ | sin email/web proxy en lab |
| 10 Defensas malware | ✅ | objeto del lab (simulado + analyzers reales) |
| 11 Recuperación de datos | ✅ | backup/restore testeado E2E |
| 12 Infraestructura de red | ✅ | 3 redes, nginx TLS |
| 13 Monitorización | ✅ | Grafana/health/Loki |
| 14 Awareness | ➖ | académico; docs forman al operador |
| 15 Proveedores | ➖ | dependencias pinneadas como proxy |
| 16 Seguridad de aplicaciones | ✅ | ASVS + tests security |
| 17 Gestión de incidentes | ✅ | IR-4 implementado (objeto del lab) |
| 18 Penetration testing | 🟡 | tests security e2e; sin pentest externo (académico) |

**Veredicto: 13 ✅, 2 🟡, 3 ➖.**

### 3.5 OWASP ASVS 4.0

Nivel L1 (aplicable a toda app) + L2 selectivo:

| Capítulo | Veredicto | Evidencia |
| --- | --- | --- |
| V1 Arquitectura | ✅ | hexagonal documentada + tests architecture |
| V2 Autenticación | ✅ | JWT exp/iat, login 401, service-token |
| V3 Sesiones | ✅ | stateless JWT; sin cookies de sesión |
| V4 Control de acceso | 🟡 | RBAC funcional; opt-in en lab, hardened enforce |
| V5 Validación de entradas | ✅ | Pydantic v2 + `PayloadSanitizer` + inyección testada |
| V6 Criptografía | ✅ | TLS correcta, secrets fuertes, HS256 con clave 32B |
| V7 Errores/logging | ✅ | HTTPException sin stack-trace; x-request-id |
| V8 Protección de datos | ✅ | TC-23 (PII masking, minimization, redaction) |
| V9 Comunicaciones | ✅ | TLS 1.2/1.3; headers `X-Frame-Options`/`X-XSS-Protection`/`X-Content-Type-Options`/`Referrer-Policy` en `nginx.conf` (verificados) |
| V10 Código malicioso | 🟡 | el lab procesa metadata de malware, no ejecutables — superficie pequeña; upload endpoints limitados a backup/import con nombre validado |
| V11 Lógica de negocio | 🟡 | rate limit opt-in (perfil lab); decision node testada |
| V12 Ficheros/archivos | 🟡 | backup/import validan nombre (path traversal testado); sin uploads arbitrarios |
| V13 API REST | ✅ | OpenAPI, Pydantic, auth configurable, rate limiting |
| V14 Configuración | ✅ | env-driven, `.env.container` :ro, docs toggle |

**Veredicto: 11 ✅, 3 🟡** — consistente con el perfil de laboratorio.

### 3.6 OWASP SAMM 2.0

Madurez 0–3 por práctica:

| Práctica | Stream A | Stream B | Nivel |
| --- | --- | --- | --- |
| **Governance** — Strategy & Metrics | objetivos definidos (TFM) | métricas KPI medibles | **2** |
| Governance — Policy & Compliance | docs/06+matrices | 27001 mapping exhaustivo | **2** |
| Governance — Education | ➖ académico | docs forman operador | **1** |
| **Design** — Threat Assessment | docs/02 threat model | riesgos RR-01..07 | **2** |
| Design — Security Requirements | ASVS/OWASP mapeado | trazabilidad 09 | **2** |
| Design — Security Architecture | hexagonal + Zero Trust | socket-proxy/segmentación | **2** |
| **Implementation** — Secure Build | CI gates + digests | pre-commit + bandit | **2** |
| Implementation — Secure Deployment | compose+hardened | preflight + env :ro | **2** |
| Implementation — Defect Mgmt | tests como gate | sin tracker formal de vulns | **1** |
| **Verification** — Architecture | tests architecture | socket-guardian | **2** |
| Verification — Requirements | 1905 tests | suites e2e como aceptación | **2** |
| Verification — Security Testing | tests/security e2e | SOAR-028 adversarial | **2** |
| **Operations** — Incident Mgmt | SOAR propio del lab | runbooks docs/04 | **3** |
| Operations — Environment | healthchecks+Grafana | socket proxy hardened | **2** |
| Operations — Operational Mgmt | backups+KPIs | runbooks documentados | **2** |

**Veredicto: madurez media ~2** — excepcional para contexto académico;
el punto débil es defect/vuln tracking formal (académico).

### 3.7 NIST SSDF (SP 800-218)

| Grupo | Práctica | Veredicto | Evidencia |
| --- | --- | --- | --- |
| **PO** | Roles/requisitos seguridad | ✅ | docs/06 + ASVS mapping |
| PO | Toolchain | ✅ | linters+tests+CI+pre-commit |
| PO | Entorno desarrollo | ✅ | perfiles, `.env.testing` |
| **PW** | Diseño seguro | ✅ | hexagonal, Zero Trust |
| PW | Componentes de terceros | 🟡 | digests verificados; sin SBOM/scan CVE continuo |
| PW | Herramientas build | ✅ | setuptools+CI reproducible |
| **PS** | Protección código | ✅ | git+CI+pre-commit+detect-secrets |
| PS | Releases/provenance | ❌ | sin firmado de releases ni attestation SLSA |
| PS | Archivo/retención | ✅ | versionado git |
| **RV** | Identificar vulns | 🟡 | bandit/scan-secrets/manual; sin proceso CVE formal |
| RV | Evaluar y remediar | ✅ | backlog SOAR/VAL ejecutado; fixes testeados |
| RV | Comunicación vulns | 🟡 | sin `security.txt`/proceso de reporte (académico) |

**Veredicto: 8 ✅, 3 🟡, 1 ❌** — el ❌ (provenance/firmado) es el gap
real de cadena de suministro.

### 3.8 SLSA 1.0

| Requisito | Veredicto | Evidencia |
| --- | --- | --- |
| Build scriptado | ✅ | Dockerfile + `make up` + CI |
| Provenance generado | ❌ | no se emite attestation SLSA |
| Aislamiento build | 🟡 | Docker build hermético relativo; builder local |
| Fuentes verificadas | 🟡 | digests 17/17 en `.env`/lock |

**Veredicto: SLSA L1 parcial** — build reproducible pero sin provenance
formal. Mejora: `docker buildx build --provenance` + lockfile.

### 3.9 Twelve-Factor App

| Factor | Veredicto | Evidencia |
| --- | --- | --- |
| I Codebase | ✅ | un repo, múltiples despliegues (perfiles) |
| II Dependencias | ✅ | `pyproject.toml` bounded `>=,<`; imágenes pinneadas+digests |
| III Config | ✅ | todo en env (`.env.full`/`.env.container`), nada en código |
| IV Backing services | ✅ | URLs por env; Redis/ES/HTTP tratados como recursos |
| V Build/release/run | ✅ | Dockerfile separado; compose release; runtime |
| VI Processes | ✅ | API stateless; Redis para estado compartido |
| VII Port binding | ✅ | servicios exportan puertos; nginx gateway |
| VIII Concurrency | 🟡 | uvicorn workers limitados por config; escala vertical lab |
| IX Disposability | ✅ | healthchecks 23/23, restart policies, graceful shutdown |
| X Dev/prod parity | ✅ | mismo stack en CI/local; perfiles lab/hardened |
| XI Logs | ✅ | stdout/stderr → Promtail→Loki |
| XII Admin processes | ✅ | `make backup` / `restore` / `init-webhook` / `clean-*` one-off |

**Veredicto: 11/12 ✅** — concurrencia limitada por diseño lab.

### 3.10 RGPD / privacidad

| Principio | Veredicto | Evidencia |
| --- | --- | --- |
| Minimización | ✅ | `test_data_minimization` — solo campos necesarios fluyen |
| Limitación de finalidad | ✅ | pipeline IR acotado; datos de test sintéticos/reales documentados |
| Exactitud | ✅ | validación Pydantic + TC-03 edge cases |
| Limitación de conservación | 🟡 | Loki con retention config; TheHive acumula casos (clean-thehive disponible) |
| Integridad/confidencialidad | ✅ | TLS, auth, masking (TC-23), secrets gestionados |
| Masking/seudonimización | ✅ | `test_pii_masking`, `test_secret_redaction`, scrub Promtail |
| Transferencias | ✅ | `test_external_filtering` — control sobre lo enviado a servicios externos |

**Veredicto: 6/7 ✅** — retención documentada como excepción lab.

### 3.11 RE&CT

Fases del marco Reactive Cyber Threat:

| Fase | Veredicto | Cobertura |
| --- | --- | --- |
| Preparation | ✅ | playbooks, herramientas, credenciales, simulador |
| Identification | ✅ | enrich: TheHive+Cortex+MISP+ES+Tenzir+Loki+Redis verificaciones |
| Containment | ✅ | `mode=enforce` (disconnect+pause) o simulated |
| Eradication | 🟡 | clean-thehive + reset; sin remediación host real (lab) |
| Recovery | ✅ | backup/restore TC-22 + consistency checks |
| Lessons learned | 🟡 | informes E2E/KPI; post-mortem formal académico |

**Veredicto: 4/6 ✅** — las 2 🟡 son inherentes al alcance académico.

### 3.12 FIRST TLP / PAP

| Control | Veredicto | Evidencia |
| --- | --- | --- |
| Campo TLP en modelo | ✅ | `Alert.tlp` (0–4) validado en dominio (`models.py`) |
| Validación TLP/PAP | ✅ | `test_tlp_pap_validation` (TC-01/TC-02) |
| Propagación a MISP/TheHive | ✅ | TLP en casos/eventos (tests e2e) |
| PAP (Permissible Actions) | ✅ | validado junto a TLP en TC-02 |

**Veredicto: cumplido** — marcado FIRST implementado en dominio.

### 3.13 OpenC2

| Control | Veredicto | Evidencia |
| --- | --- | --- |
| Lenguaje de comandos estandarizado | ➖ | **Alternativa**: CACAO elegido como estándar de playbook (OASIS) — OpenC2 es lenguaje de *comandos*, no de playbooks; el export CACAO implementado cubre la interoperabilidad de orquestación |
| Mapeo de acciones | 🟡 posible | las acciones `enforce` (deny/pause/restart) mapean 1:1 a acciones OpenC2 — trabajo futuro trivial |

**Veredicto: ➖ no aplica por decisión de diseño justificada** — CACAO
cubre la capa de playbook; OpenC2 sería complementario, no sustituto.

### 3.14 CWE Top 25

Mapeo con la superficie real del proyecto:

| CWE | Veredicto | Evidencia |
| --- | --- | --- |
| CWE-79 XSS | ✅ | tests security (payloads XSS) + output JSON API |
| CWE-89 SQLi | ✅ | sin SQL dinámico (ES/MISP APIs); tests injection |
| CWE-78 Command injection | ✅ | `test_security` payloads; sin `os.system`/`shell=True` en rutas |
| CWE-22 Path traversal | ✅ | backup name validator + tests |
| CWE-90 LDAP injection | ✅ | tests incluidos; sin LDAP real |
| CWE-502 Deserialization | ✅ | Pydantic strict; sin pickle/yaml.load unsafe (SafeLoader en tests) |
| CWE-306 Missing auth | 🟡→✅ | opt-in lab; enforced hardened |
| CWE-862 Missing authz | 🟡→✅ | RBAC + require_api_auth |
| CWE-798 Hardcoded creds | ✅ | scan-secrets gate; fixtures test explícitas |
| CWE-611 XXE | ➖ | sin parsing XML |
| CWE-787/125/416 memoria | ➖ | Python managed (no aplica directamente) |
| CWE-200 Info exposure | ✅ | errors sanitizados; docs toggle; scrub logs |
| CWE-319 Cleartext | 🟡 | HTTP interno plano (red aislada, documentado) |
| CWE-352 CSRF | ➖ | API stateless JWT, sin cookies |
| CWE-918 SSRF | 🟡 | URLs internas controladas por config; sanitización parcial |

**Veredicto: 8 ✅, 4 🟡, 3 ➖** — superficie Top-25 bien cubierta.

### 3.15 Patrones de diseño

| Patrón | Veredicto | Evidencia |
| --- | --- | --- |
| Hexagonal (ports & adapters) | ✅ | `domain`/`application`/`infrastructure`/`interfaces` + `test_hexagonal_imports` |
| SOLID | ✅ | composition root inyecta dependencias; interfaces `Protocol` (`clients.py`); SRP por router |
| Factory/Strategy | ✅ | `create_docker_client` con 3 estrategias de conexión |
| Repository | ✅ | `alert_repository` inyectado; `in_memory` para tests |
| Circuit breaker/retry | ✅ | `src/soar_lab/resilience/` (circuit breaker, retry, timeout) |
| Middleware/decorator | ✅ | `RateLimitMiddleware`, `require_api_auth`, trace-id |
| Composition root | ✅ | `interfaces/api/composition.py` |
| Singleton controlado | 🟡 | `app.state` como registro — convención FastAPI, aceptable |
| Fail-fast validation | ✅ | Pydantic dominio + config schemas |
| Defense in depth | ✅ | sanitizer → auth → RBAC → rate limit → docker guard |

**Veredicto: 9/10 ✅** — patrones aplicados con disciplina y
verificados por tests de arquitectura.

## 4. Validación

### 4.1 Verificación

Cada control cita fichero, test o comando. Los conteos agregados:

| Marco | ✅ | 🟡 | ➖ | ❌ |
| --- | --- | --- | --- | --- |
| NIST IR 8374 | 8 | 1 | 0 | 0 |
| ISO 27002 (subset) | 18 | 5 | 1 | 0 |
| NIST 800-53r5 | 18 | 10 | 0 | 0 |
| CIS Controls v8 | 13 | 2 | 3 | 0 |
| OWASP ASVS | 11 | 3 | 0 | 0 |
| OWASP SAMM | ~2 medio | — | — | — |
| NIST SSDF | 8 | 3 | 0 | 1 |
| SLSA | L1 parcial | — | — | — |
| 12-Factor | 11 | 1 | 0 | 0 |
| RGPD | 6 | 1 | 0 | 0 |
| RE&CT | 4 | 2 | 0 | 0 |
| FIRST TLP | 4 | 0 | 0 | 0 |
| OpenC2 | ➖ justificado | — | — | — |
| CWE Top 25 | 8 | 4 | 3 | 0 |
| Patrones diseño | 9 | 1 | 0 | 0 |

**Total ronda 2: ~120 controles — 0 ❌ funcionales** (el único ❌ es
provenance SLSA, gap real de cadena de suministro; los ➖ son no
aplicables por diseño).

### 4.2 Criterios de aceptación

- Marcos adicionales evaluados sobre **todo el proyecto** ✅
- Veredictos con evidencia reproducible ✅
- 🟡/❌ con justificación o tarea de mejora ✅

### 4.3 Evidencias

Mismo conjunto que docs/10 + `TC-23` (privacidad), `TC-22`
(persistencia), `requirements-docker.lock`, `.pre-commit-config.yaml`,
`.github/workflows/ci.yml` (trufflehog), `pyproject.toml` (bounded
deps), `promtail-config.yml` (pipeline_stages).

## 5. Problemas

### 5.1 Limitaciones

- Sin CVE-scanner continuo de imágenes (trivy/grype) — mejora
  recomendada para RA-5/CIS-7/SSDF-PW.
- Sin provenance SLSA ni firma de releases (cosign) — gap de supply
  chain real pero esperable en académico.
- Volúmenes sin cifrar en reposo (SC-28) — Docker Desktop.
- `security.txt` no publicado (RV comunicación vulns — académico).

### 5.2 Riesgos

- Igual que docs/10: auth opt-in en lab, HTTP interno plano.
- Los 🟡 de supply chain son el riesgo residual dominante.

### 5.3 Recomendaciones

1. Añadir `trivy image` al `make verify-digests` o CI para cerrar
   RA-5/CIS-7/SSDF-PW.
2. `docker buildx build --provenance=mode=max` para SLSA L2.
3. `SECURITY.md`/`security.txt` para RV comunicación.
4. Evaluar cifrado de volúmenes si el lab pasa a datos reales.

## 6. Referencias

- `docs/10-framework-validation-exhaustive.md` — ronda 1
- `docs/11-final-validation-report.md` — informe final consolidado
- NIST IR 8374, ISO/IEC 27002:2022, NIST SP 800-53r5, CIS Controls v8,
  OWASP ASVS 4.0 / SAMM 2.0, NIST SSDF SP 800-218, SLSA 1.0,
  12factor.net, RGPD, RE&CT, FIRST TLP 2.0, OASIS OpenC2, CWE Top 25

---

## 7. Addendum — Ronda 3 (STRIDE, LINDDUN, ISO 22301, NIST 800-92, OpenSSF, patrones)

Evaluación adicional mientras la suite E2E continúa (reanudada desde
TC-04 tras el fix de evidencia `payload.json`). Misma metodología:
verificación contra el stack en vivo y el árbol de trabajo.

### 7.1 STRIDE — modelo de amenazas del flujo de alerta

Flujo evaluado: `webhook → shuffle-backend → orborus → {thehive,
cortex, misp, elasticsearch, soar-api} → nginx/TLS`.

| Amenaza | Control | Veredicto |
| --- | --- | --- |
| **S**poofing — inyección de alertas falsas | Webhook sin firma/HMAC: cualquiera con la URL puede POST. Mitigado por red privada `soar_net` y URL no publicada; TC-19 valida rechazo de payloads maliciosos | 🟡 |
| **T**ampering — alteración de evidencia | Índices ES append-only + casos TheHive con audit log; `docker logs` crudos modificables localmente | 🟡 |
| **R**epudiation | `x-request-id` correlación extremo a extremo + audit trail | ✅ |
| **I**nfo disclosure — secretos en logs | `pipeline_stages` de Promtail redactan los 4 patrones reales antes de Loki; `docker logs` crudos = residual upstream | 🟡 |
| **D**oS — saturación | `mem_limit` 23/23, rate-limit middleware **verificado live** (`X-RateLimit-Limit: 300` global / `30` en `/auth` desde env, 429 + `Retry-After: 52` al superar cuota — tras BUG-045 los budgets env aplican), cap de 10 workers Orborus, `test_e2e` limpia ejecuciones stale | ✅ |
| **E**oP — escalada | `no-new-privileges`, `cap_drop`, 0 privileged, overlay non-root | ✅ |

### 7.2 LINDDUN — amenazas de privacidad

- **Datos**: `hostname`, `src_ip`, `hash`, `domain` — seudo-PII
  plausible en un entorno real; aquí todo sintético.
- **Linkability**: `correlation_id`/`trace_id` enlazan alerta→caso→
  IOCs→logs. Deseable para forense; documentado como decisión.
- **Minimización**: TC-23 cubre anonimización; TLP/PAP marca la
  clasificación por alerta.
- **Veredicto**: 🟡 — adecuado para lab; un despliegue real requeriría
  DPIA y cifrado selectivo de campos.

### 7.3 ISO 22301 — continuidad de negocio

| Aspecto | Detalle | Estado |
| --- | --- | --- |
| Backup/restore | `backup_driver`+`backup_service` en composition, rutas `/api/v1/backup/*`, `make backup`/`make restore` | ✅ |
| Auto-recovery | `restart: unless-stopped`/`always` en 23/23 + healthchecks 23/23 | ✅ |
| RPO/RTO formal | No definidos — aceptable en académico, requerido en producción | 🟡 |
| SPOF | ES single-node (yellow normal), MISP único — documentado | 🟡 |
| Degradación graceful | Circuit breaker por integración (ver §7.6) | ✅ |

### 7.4 NIST SP 800-92 — gestión de logs

- **Centralización**: Promtail (docker service discovery) → Loki →
  Grafana — ✅ arquitectura canónica.
- **Integridad/confidencialidad**: Loki append-only, acceso vía
  Grafana auth — ✅.
- **Sanitización**: 4 regex de redacción verificados contra líneas
  reales de log — ✅ (nuevo).
- **Retención**: `loki-config.yml` sin `retention_period` ni
  `limits_config` → retención indefinida — 🟡 (gap: definir e.g. 30d).
- **Sincronización temporal**: contenedores en UTC — ✅.

### 7.5 OpenSSF Scorecard (criterios aplicables)

| Check | Detalle | Estado |
| --- | --- | --- |
| Binary-Artifacts | Sin binarios en repo | ✅ |
| CI-Tests | `ci.yml` ejecuta suites + trufflehog | ✅ |
| Pinned-Dependencies | `requirements-docker.lock` (17/17 digests) + deps acotadas | ✅ |
| SAST | `make scan-secrets` + bandit en `make quality` | ✅ |
| License / Maintained | Licencia presente, desarrollo activo | ✅ |
| Token-Permissions | 2 workflows con `permissions:` explícito | 🟡 |
| Dependency-Update-Tool | Sin dependabot/renovate | ❌ |
| Security-Policy | Sin `SECURITY.md` | ❌ |
| Signed-Releases / SLSA provenance | No — ya en riesgos §5.2 | ❌ |

### 7.6 Patrones de arquitectura y resiliencia (auditoría de diseño)

| Patrón | Implementación | Veredicto |
| --- | --- | --- |
| Hexagonal / ports & adapters | `domain→application→infrastructure→interfaces`, composition root único | ✅ |
| Circuit Breaker | `base_client.py` envuelve **todas** las integraciones (TheHive, Cortex, MISP, Shuffle, ES) en GET/POST/PUT | ✅ |
| Retry + Timeout | `resilience/retry.py`, `resilience/timeout.py` | ✅ |
| Bulkhead (aislamiento de fallos) | 3 redes Docker aisladas; API único puente | ✅ |
| Correlation/Trace ID | `x-request-id` middleware + propagación | ✅ |
| Health check | 23/23 tras añadir renderer+backend | ✅ |
| Middleware pipeline (cross-cutting) | TraceId + RateLimit + auth como middleware/dependencias, no en handlers | ✅ |
| Guarded enforcement | `SOAR_CONTAIN_ENFORCE` + allowlist — patrón feature-flag de seguridad | ✅ |
| Outbox / Saga | No aplica — pipeline REST síncrono, razonable para lab | n/a |
| Evidence/audit por diseño | Bundle de evidencia por test (payload+workflow+salud+docker) — patrón auditable-artifact | ✅ |

### 7.7 Incidencias encontradas en esta ronda

1. **`payload.json` ausente en TC-04/05/19/26** — senders propios que
   bypassan `submit_alert`. Corregido: `_wrap_webhook_session` en
   `service_mixins.py` registra todo POST a `/api/v1/hooks/` como
   evidencia — solución central, no parche por test.
2. **Retención Loki indefinida** — resuelto: `retention_period: 720h` +
   compactor en `loki-config.yml`.
3. **Sin SECURITY.md ni gestor de actualización de dependencias** —
   quick-wins para OpenSSF.
4. **Bug `broadcast()` (websocket_manager)** — mutación de
   `active_connections` durante iteración: la conexión siguiente a una
   fallida nunca recibía el mensaje; y `remove()` sin guarda podía
   lanzar `ValueError` fuera del handler. Reproducido con 2 tests,
   corregido (snapshot + `disconnect()`).
5. **Bug `_AtomicContext.__exit__`** — un `commit()` fallido se
   reportaba como `TimeoutError` enmascarando el error real
   (`done=False` compartido para timeout y error). Reproducido con test,
   corregido (error real antes que timeout).
6. **CWE-532 en `auth.py`** — `logger.info(token[:20])` exponía
   material parcial de credencial por petición. Corregido: fingerprint
   `sha256[:12]` correlacionable y no reversible.

Técnicas aplicadas: barrido de `except` silenciosos (41 analizados,
mayoría degradación defensiva legítima en adaptadores), mutación-durante-
iteración (2 falsos positivos verificados como snapshots), defaults
mutables, `shell=True`/`pickle`/`yaml.load`/`eval` (0 hits),
`requests` sin `timeout` (0 hits), `utcnow` (0 hits), secretos en logs,
y revisión manual de circuit breaker/retry/timeout.

### 7.8 Resumen ronda 3

| Marco | ✅ | 🟡 | ❌ |
| --- | --- | --- | --- |
| STRIDE (6 amenazas) | 3 | 3 | 0 |
| LINDDUN | — | 1 | 0 |
| ISO 22301 (5 aspectos) | 3 | 2 | 0 |
| NIST SP 800-92 (5 aspectos) | 4 | 1 | 0 |
| OpenSSF (9 checks) | 5 | 1 | 3 |
| Patrones arquitectura (10) | 9 | 0 | 0 (1 n/a) |

**Ronda 3: 24 ✅ / 8 🟡 / 3 ❌**

## 8. Addendum — Ronda 4: auditoría estática exhaustiva archivo a archivo (bug hunt)

Revisión sistemática de todo `src/soar_lab/` (128 ficheros, ~16.5 k líneas)
con patrón → test de reproducción → fix mínimo → suite enfocada, más
regresión unitaria completa (**1353/1353 en verde**).

### 8.1 Bugs confirmados, reproducidos con test y corregidos

| # | Fichero | Defecto | Reproducción | Fix |
| --- | --- | --- | --- | --- |
| 7 | `infrastructure/path_service.py` | `config_provider` declarado opcional pero toda property hacía `.get()` → `AttributeError` | test unit (properties sin provider) | helper `_cfg` con guarda None |
| 8 | `integrations/shuffle/shuffle_helpers.py` | CWE-532: logueaba `apikey[-8:]` y el sufijo del header Authorization en DEBUG | inspección | fingerprint `sha256[:12]` |
| 9 | `persistence/sqlite_alert_repository.py` | `INSERT OR REPLACE` → en conflicto **borra+reinserta**: nuevo `id` autoincrement y `timestamp` reseteado (corrupción de historial en re-ingesta idempotente) — en las 3 tablas | test integración (id 1→2) | `ON CONFLICT(key) DO UPDATE` preservando `id`/`timestamp` |
| 10 | `interfaces/api/main.py` | `except WebSocketDisconnect` demasiado estrecho: `send_json` con `RuntimeError` dejaba conexión fantasma en el manager | test endpoint con ws falso | `disconnect()` en `finally` |
| 11 | `integrations/thehive/client.py` | `check_version_compatibility` comparaba listas de distinta longitud: `5.1` vs `5.1.0` → False | test unit | padding de ceros a igual longitud |
| 12 | `security/sanitization.py` | `whitelist` se aplicaba recursivamente: un dict anidado bajo clave permitida perdía **todos** sus campos | test unit (`data` → `{}`) | whitelist solo top-level; blacklist sigue recursiva |
| 13 | `config/logging.py` | `_JSON_FORMAT` con `%(message)s` sin escapar → JSON inválido ante comillas/saltos | test unit | `_JsonFormatter` con `json.dumps` |
| 14 | `infrastructure/pytest_test_runner.py` | Misma clase de fuga que `subprocess_runner`: `wait_for(communicate())` no mata al hijo en timeout → pytest huérfano | test con marker+psutil (PID vivo) | `proc.kill()` + `wait` en path de timeout |
| 15 | `interfaces/api/routes_services.py` | `SOAR_CONTAIN_ALLOW_PREFIX=""` → `startswith("")`=True → **bypass total de la allowlist** (contenedor arbitrario contenido) | test API (403 esperado, recibido 200) | `bool(prefix) and startswith(prefix)` |
| 16 | `application/use_cases/auth_service.py` | `==` en credenciales → CWE-208 timing side-channel en login | test con `compare_digest` parcheado (0 llamadas) | `hmac.compare_digest` en utf-8 |
| 17 | `interfaces/api/auth.py` | `hmac.compare_digest(str)` lanza `TypeError` con no-ASCII → token `X-Service-Token` no-ASCII → 500 en vez de 401 | test unit (`TypeError`) | comparación en bytes utf-8 |
| 18 | `interfaces/api/contracts.py` | `supported_versions or [v] if v else [DEFAULT]` → la lista explícita se **descartaba** cuando `version=""` | reproducción directa (`["1.0.0"]`) | paréntesis correctos |
| 19 | `config/settings.py` | `JWT_SECRET_KEY` con **default hardcodeado público** de 34 chars (pasaba la validación de longitud) → tokens falsificables si falta la env | inspección | fallo cerrado (None → AuthError) |
| 20 | `infrastructure/filesystem_storage.py` | `open()` sin `encoding` en 2 escrituras → crash/corrupción con no-ASCII bajo cp1252 (Windows) | test utf-8 round-trip | `encoding="utf-8"` + `default=str` |

### 8.2 Deuda técnica documentada (no corregida — bajo impacto o por diseño)

- `inject_hosts_file` (network_watcher): append a `/etc/hosts` sin dedup
  ni normalización de `\n` final (en la práctica Docker siempre termina
  con newline).
- `is_inside_container`: `Path("/app").exists()` puede dar falso
  positivo en Windows si existe `C:\app` — heurística documentada.
- `alert_generator._id`: `_counter > 9999` rompe `ALERT_ID_PATTERN`
  (`:04d` produce 5 dígitos) — improbable por proceso.
- `routes_analytics`: `create_*_use_case()` construye Settings+ES client
  por petición — deuda de rendimiento deliberada (simplicidad DI).
- `pytest_output_parser`: `float()` en línea TOTAL puede lanzar ante
  formato inesperado (la salida real de pytest siempre encaja).
- `parse_env_file` (validate_credentials): no quita comillas de valores
  (a diferencia de python-dotenv).
- `FilesystemStorage`: `self._base / key` sin validación propia — la
  capa de servicio (`BackupService._BACKUP_NAME_RE`) ya valida; la
  defensa en profundidad queda como mejora futura.
- `FilesystemStorage.list_keys`: glob `f"{prefix}*"` con `..` podría
  listar fuera del base — mismo caller-validated pattern.
- `scroll_search_generator`: no limpia el scroll context al terminar
  (expira solo en 1 m — aceptable).
- `misp.get_attribute_count`/`is_valid_alert_id`: `except → 0/False`
  confunde "servicio caído" con "sin datos" — semántica deliberada.

### 8.3 Falsos positivos descartados tras verificación

- `timeout.py`: `except: pass` solo envuelve callbacks de usuario; la
  función envuelta sí propaga errores (verificado).
- `thehive/client.py:370` y `rate_limit.py`: ya iteran sobre
  snapshots `list(...)` — mutación-durante-iteración no aplica.
- `misp/client.py:232`: `pop("attributes")` guardado por `if in`.
- `http_alert_sender`: mutación de `alert["trace_id"]` = propagación
  intencional documentada.
- `kpi_analyzer._check_service_success`: string no vacío = success es
  heurística deliberada para ids de job/case.
- AST-scan global: 0× `time.sleep` en `async def`, 0× `return` en
  `finally`, 0× `shell=True`/`pickle`/`yaml.load`/`eval`/`exec`,
  0× `datetime.now()` naive, 0× `.get(...)` subscript peligroso,
  0× `assert` en producción, todos los `requests.*` con timeout.

## 9. Addendum — Ronda 5: técnicas §8.1/8.6/8.9/8.10 (valores límite, property-based, diferenciales, metamórficas)

Aplicación de las técnicas restantes del patrón de caza de bugs
(`docs/13-defect-driven-testing.md` contiene la política formal, el
registro BUG-001..027 y las plantillas).

### 9.1 Bugs confirmados, reproducidos con test y corregidos

| # | Fichero | Defecto | Técnica | Fix |
| --- | --- | --- | --- | --- |
| 21 | `thehive/client.py` | `parse("abc")`→`[]`→padding `[0,0]` → `check_version_compatibility("5.1","abc")` devolvía `True` aunque el docstring exige `False` ante versión imparseable | valor límite | `not cur or not minimum → False` |
| 22 | `sqlite_alert_repository.py` | `AVG(coverage)=0.0` es falsy → `float(result) if result else None` confundía cobertura 0 % legítima con "sin datos" | valor límite | `is not None` |
| 23 | `http_alert_sender.py` | `queue.Queue(maxsize=0)` = **infinita** → `send_batch(max_queue_size=0)` desactivaba la backpressure en silencio (`put_nowait` nunca llena) | valor límite | `ValueError` si `max_queue_size` o `workers < 1` |
| 24 | `node_timing_extractor.py` | `float("garbage")` en `started_at`/`completed_at` de un doc ES malformado → `ValueError`/`TypeError` → 500 en endpoint | entrada malformada | try/except → degradación (duración 0, nodo saltado) |
| 25 | `sqlite_alert_repository.py` | SQLite `LIMIT -5` = **sin límite** → `get_alerts(limit=-5)` devolvía la tabla entera en vez de respetar "a lo sumo N" | valor límite | `limit = max(0, limit)` |
| 26 | `security/sanitization.py` | Una sola pasada de eliminación por regex **creaba** el patrón prohibido: `<scr<script></script>ipt>` → `<script>`, `jjavascript:avascript:` → `javascript:` (bypass XSS por no-idempotencia) | metamórfica (idempotencia) + ejemplo dirigido | bucle de eliminación a punto fijo |
| 27 | `validation/validators.py` | `IPValidator` aceptaba octetos con ceros a la izquierda (`010.1.2.3`, `000.000.000.000`) — ambigüedad octal; stdlib `ipaddress` los rechaza (clase filter-bypass en validadores) | diferencial vs `ipaddress` (Hypothesis, 300 ejemplos) | `g == str(int(g))` |

### 9.2 Property tests añadidos (`tests/unit/test_property_based.py`)

14 propiedades/metamórficas/diferenciales permanentes con Hypothesis:

- **Idempotencia del sanitizer** (metamórfica): `sanitize(sanitize(x)) == sanitize(x)` + ejemplos dirigidos de bypass anidado (script, `javascript:`).
- **Robustez**: payloads anidados arbitrarios nunca crashean `sanitize` ni `validate_response_schema`.
- **Cota de reintentos**: callable siempre-fallido se invoca exactamente `max_attempts` veces; éxito en intento *k* → *k* invocaciones (regresión de BUG-004 generalizada).
- **Comparación de versiones**: reflexividad + consistencia con orden de tuplas (diferencial).
- **Percentiles**: `min ≤ p50 ≤ p90 ≤ p95 ≤ p99 ≤ max`, `p50 == median` (metamórfica de orden).
- **Invariancia por traslación** (metamórfica): sumar Δ a todos los timestamps preserva duraciones en `extract_timings`.
- **Diferencial IP**: `IPValidator` ≡ `ipaddress` stdlib sobre el espacio de cuádruples con/sin padding.

### 9.3 Análisis histórico (§8.16) — hotspots validados

`git log` por ficheros más tocados en commits correctivos:

| Fichero | Churn | Resultado |
| --- | --- | --- |
| `tar_backup_driver.py` | 4 | BUG-tar (`--skip-old-files`) ya corregido |
| `sqlite_alert_repository.py` | 4 | BUG-009, 022, 025 |
| `http_alert_sender.py` | 4 | BUG-023 |
| `settings.py` | 5 | BUG-019 |
| `api/main.py` | 5 | BUG-010 |

Conclusión: los hotspots históricos **coinciden** con los ficheros con
defectos reales — quedan priorizados para futuras revisiones.

### 9.4 Descartado como diseño deliberado

`HashValidator` rechaza hashes hex todo-dígitos (`"1"*32`) — decisión con
test propio (`test_invalid_only_digits`); no se toca.

**Acumulado rondas 3–5: 27 bugs confirmados con prueba fallida, corregidos
y con regresión permanente; 75/75 tests del lote en verde.**

### 9.5 BUG-028 + incidente E2E 401 (INTERMITENTE)

| ID | Fichero | Defecto | Técnica | Fix |
|---|---|---|---|---|
| 28 | `shuffle_helpers.py` | f-string sin llaves: `f"?limit=DEFAULT_SHUFFLE_WORKFLOW_EXECUTIONS_LIMIT"` enviaba el **nombre** de la constante literal en la URL de `api_workflow_executions` | trazado de error E2E (401) | `?limit={DEFAULT_...}` interpolado |

**Incidente relacionado** (clasificado INTERMITENTE, no bug de
producción): `test_concurrent_alerts` falló con `401 Unauthorized` en
`/workflows/{id}/executions`. Evidencia: (a) el mismo cliente con la
misma clave devuelve 200 antes y después; (b) los logs de
`shuffle-backend` muestran `Api authentication failed: No users found
for this apikey` en esa ventana — inconsistencia interna de Shuffle
(apikey válida cuyo usuario no resolvía). No reproducible tras el
hecho; el bug del f-string es independiente (Shuffle toleraba el
`limit` literal con 200) y queda corregido con regresión
`TestApiWorkflowExecutions::test_limit_param_is_numeric`.

## 10. Addendum — Ronda 6: revisión fuera de `src/` (scripts/, tests/e2e infra, helpers)

Tras agotar `src/soar_lab` (128 ficheros, rondas 3–5), la auditoría se
extendió a los ~102 ficheros de `scripts/` + `apps/` y los 17 ficheros de
infraestructura E2E (`base/`, `helpers/`, `assertions/`). Técnicas:
barrido AST/patrones, trazado de contratos, fault injection sobre
plantillas, valores límite y verificación de returncodes.

### 10.1 Bugs confirmados, reproducidos con test y corregidos

| ID | Fichero | Defecto | Reproducción | Fix |
| --- | --- | --- | --- | --- |
| 29 | `scripts/reports/generate_e2e_report.py` | `mttd_median = sorted(v)[len(v)//2]` → elemento superior, no mediana real en n par ([10,20,30,40] → 30 en vez de 25) | unit con `_es_post` mockeado — FAILED 30.0≠25.0 | `statistics.median` |
| 30 | `tests/e2e/helpers/docker_control.py` | `stop/start/restart_container` devolvían `True` con cualquier exit code (éxito fantasma) | mock `returncode=1` → `True` — FAILED | `return result.returncode == 0` |
| 31 | `tests/e2e/helpers/timing.py` | `measure_time` contextmanager calculaba `elapsed` y lo **descartaba** (contextlib ignora el return tras yield) | `with measure_time() as t` → `None` — FAILED | yield de dict `{"elapsed"}` + `monotonic` |
| 32 | `tests/e2e/helpers/timing.py` | `calculate_percentiles` `int(p*n)` off-by-one: p50 de 10 muestras → 6º elemento | [1..10] p50→6 — FAILED | nearest-rank `ceil(p*n)-1` |
| 33 | `scripts/setup/generate_env.py` | `str.format` sobre plantilla Grafana → `KeyError` con llaves desconocidas (`${VAR:-default}` — formato que el propio repo usa en `config/templates/`) | fault injection (template hostil) — `KeyError: 'LOKI_URL'` | `.replace()` por placeholder |
| 34 | `tests/e2e/TC-06/test_critical_severity.py` | **Falso negativo de test**: matcher `"escalat"` no cubre `notify_critical` (el nodo de escalación real — ejecutó SUCCESS según `workflow_execution.json`); el test no podía pasar nunca | FAILED E2E + inspección de evidencia → PASSED tras fix | keywords `("escalat", "notify_critical")` |
| 35 | `tests/e2e/base/__init__.py` (+37 ficheros TC) | **Orden de init**: `self.t0` se fijaba en la subclase tras `super().setup_method()`, pero el setup base ya llamaba a `_log` (override que lee `t0`) → `AttributeError` tragado por `assert_grafana_healthy` y grabado como `grafana_healthy: False` silencioso — pytest PASSED pero JSON 10/11 en todos los TC | `assertions.json` en artifacts + test de setup stubbed (FAILED pre-fix con el mismo `AttributeError`) | `self.t0` inicializado al inicio de `setup_method` base (un fix para los 37 TC) |
| 36 | `workflow_validator.py` + `base/__init__.py` | `int(http_status)` sin guarda → `ValueError` con `status` no numérico (`{"status": "OK"}`) en result de nodo crítico — el validador crasheaba en vez de acumular el error | fault injection (status="OK") — FAILED pre-fix con `ValueError` | `int()` protegido; status no numérico no es HTTP status (mismo fix en ambos sitios) |
| 37 | `conftest.py` + `service_mixins.py` | Fallback a clave Shuffle **hardcodeada** (`c8410826-…`, stale de otra instalación) y a `"placeholder"` — config ausente enmascarada con credencial silenciosa | source-scan (conftest parchea sockets al import) — FAILED pre-fix | fail-closed: default `""` en ambos |
| 38 | `scripts/reports/test_summary.py` | `shell=True` con expresión `-m '...'` en comillas simples — en Windows `cmd.exe` no agrupa comillas simples → pytest lee `requires_external` como path, rc=4, **0 tests reportados como PASS** | reproducción live (`docker exec`, "file or directory not found") + test de argv capturado — FAILED pre-fix | argv list sin shell; expresión como un solo token |
| 39 | `e2e/helpers/cleanup.py` | `docker volume rm` / `docker network rm` ignoraban `returncode` → `True` aunque el borrado fallara (mismo patrón BUG-030) | subprocess mockado con rc=1 — FAILED pre-fix | acumula `ok &= rc == 0` por recurso |
| 40 | `quality/export_attack_stix.py` | `_attack_url` hacía `sub.lstrip('0')` → `T1485.001` generaba `/techniques/T1485/1/` en vez del canónico MITRE `/T1485/001/` (contradice su propio docstring) | 2 FAILED pre-fix (`/1/` vs `/001/`) | conserva el sub-ID con ceros |
| 41 | `test_init_shuffle_webhook.py` | **Test pollution**: el test mockeaba `ShuffleClient` pero el `init_shuffle_webhook()` real escribía `webhook_info.json` en `reports/validation/results/` → cada corrida de integración **sobrescribía la URL real del webhook con datos mock** ("trigger-001", "test-api-key") → tests E2E posteriores con HTTP 404 | archivo corrupto observado live (`org_id: "<Mock ...>"`) + suite: `webhook_info_path` sin `WEBHOOK_INFO_DIR` → FAILED pre-fix | fixture autouse `WEBHOOK_INFO_DIR→tmp_path` + test de aislamiento; webhook real regenerado con `init_shuffle_webhook.py` |
| 42 | `scripts/ci/e2e_suites.py` | `int(E2E_SUITE_START)` sin guarda → `ValueError` con valor no numérico e `IndexError` con valor ≥ nº suites | reproducción directa + 2 FAILED pre-fix | try/except + índice seguro con `<none>` |
| 43 | `tests/performance/test_stress.py` | `StressTester.percentile([])` → `IndexError` (index=-0.5 no entero → `sorted_data[0]`); `test_load._percentile` sí tenía el guarda | FAILED pre-fix con IndexError | guarda `if not data: return 0` |
| 44 | `tests/e2e/base/__init__.py` | `assert_evidence_complete` exigía `payload.json` incondicionalmente, pero solo `submit_alert`/POST envuelto lo escribe → tests sin submit (TC-10 Tenzir, checks de servicio) quedaban **FAILED 3/4 en el artifact** aunque pytest PASABA — falso negativo estructural en todos los result JSON y reports | FAILED pre-fix (`missing_required: ['payload.json']` con `execution_id=None`) | `payload.json` requerido solo si `execution_id` set |
| 45 | `infrastructure/config_provider.py` | `get("UPPERCASE_KEY")` solo consultaba attrs de `Settings` y `_config` (claves minúsculas) — env vars sin `@property` dedicada (`RATE_LIMIT_*`, `API_REQUIRE_AUTH`, `INTERNAL_SERVICE_TOKEN`, `DOCS_DIR`, `SHUFFLE_WEBHOOK_TOKEN`) se ignoraban silenciosamente: `RATE_LIMIT_PER_MINUTE=300` quedaba 100, auth nunca aplicaba el token real | FAILED pre-fix (`cp.get`→100 con env=300) + live: `Limit: 10`→`30`, `Limit: 100`→`300` tras fix | fallback `os.environ.get(key, default)` tras attr/`_config` |
| 46 | `TC-15/test_api_latency.py` + helpers E2E | Probes de latencia medían `list_cases()` sin acotar (range `0-1000` → 640 casos ≈ 13,6 s): el SLA (5/10 s) falla **determinísticamente** al crecer el volumen de casos — confunde tamaño de datos con responsividad (5 tests en rojo) | medición live `0-10`→0,2 s / `0-100`→1,5 s / `0-1000`→13,4 s; 5×FAILED replicados sin carga paralela; regresión con stub capturando args | `range_="0-50"` en probes; `sort=-createdAt, 0-200` en helpers de filtrado por correlation_id (evidence, isolation, lineage, dedup, case-wait) |
| 47 | `TC-26/test_extreme_load.py` | Sender webhook con `timeout=15` < escritura síncrona Shuffle→OpenSearch (~20-27 s bajo carga, deadline interno ~20 s) → ReadTimeouts sin respuesta; 5xx definitivos tratados como fatales; `test_backpressure` no contaba 5xx en la suma | sonda live: 10 burst → 9×ReadTimeout(15 s)+1×500; con 60 s → 1×200(27,3 s)+9×500(~20 s) | `_post_webhook` (timeout=60 + ≤2 reintentos solo si `status>=500`; ReadTimeout NO reintentado — riesgo duplicados) + `rejected_5xx` en backpressure |
| 48 | `TC-KPI-06/test_service_health.py` | Patrones de exclusión de abortos `TC-05/TC-19/TC-26/TC-07` (guion tras TC) nunca casaron `alert_id` reales `TCxx-` → código muerto; 42 abortos TC-26 contados como inesperados (7,0 % > 5 %) | consulta OpenSearch: 42 ABORTED no excluidos = 100 % `TC26-*`; failing-first `AttributeError` | `EXPECTED_ABORT_PATTERNS` con formatos reales `TC05/TC07/TC16/TC18/TC19/TC26` + regresión de casación literal |
| 49 | `kpi_analyzer.py` + `aggregated_kpis.py` | `mttr_seconds` aceptado **sin acotar** — una doc corrupta (MTTR 26,6 M s ≈ 308 días) desplazó `avg_mttr` ransomware a 47 857 s (~×280) | endpoint live 47857,36 s; doc outlier localizada (`≥100 000` → 1 doc); regresión: media 8,87 M s con outlier | bound `0 < mttr ≤ hours*3600` en ambas rutas + regresión `TestKpiAnalyzerMttrBounds`; doc contaminante eliminada |
| 50 | `docker-compose.hardened.yml` + `verify_image_digests.py` | `DOCKER_PROXY_IMAGE=…socket-proxy:0.4.1` — tag inexistente (los publicados llevan `v`); `make up HARDENED=1` fallaría al pull; `compose config` no resuelve manifests y la var no estaba en el verificador | `imagetools inspect :0.4.1` → `not found`; `:v0.4.1` → digest válido; `verify-digests`: `NOT SET` | tag `v0.4.1` + var añadida a `IMAGES` del verificador → 18/18 + regresión estructural |
| 51 | `TC-26/test_extreme_load.py` | Envío cuya respuesta no llegó (ReadTimeout/respuesta rota post-encolado) contado como error/rejected aunque la ejecución existía server-side — 10/10 execs FINISHED + 10 casos únicos + 0 5xx backend, pero pytest FAILED en `accepted`/`errors` | evidencia completa de aceptación vs assert de contabilidad cliente; failing-first `AttributeError` | `_reconcile_unanswered_sends`: reclasifica como aceptado si la ejecución existe (`get_workflow_executions`) — en storm, backpressure y duplicate_prevention |
| 52 | `TC-26/test_extreme_load.py` (esperas + semántica pérdida) | (a) `WORKFLOW_TIMEOUT=600` < drenaje medido (storm max 667 s → falsos TIMEOUT); (b) backpressure exigía todo-FINISHED cuando el stack descarta explícitamente por abort-governor (~1300 s, 27/29 ABORTED) — shed auditable ≠ pérdida | storm `Accepted:10/10`→`8 FINISHED+2 TIMEOUT`; backpressure `29 acc`→`5/29 FINISHED`, aborts verificados en OpenSearch | `STORM_WAIT_TIMEOUT=1200`, `BACKPRESSURE_WAIT_TIMEOUT=1800` + `_classify_exec_outcomes` (terminal auditable vs pérdida silenciosa) |

| 53 | `docker-compose.hardened.yml` + `config/logging.py` | `volumes: !reset` + secuencia en bloque es **descartado silenciosamente** por Compose v5.4.0 → api hardened arrancaba con cero mounts → código horneado Aug-20 sin fallback env BUG-045 → `API_REQUIRE_AUTH=true` inerte (auth abierta en el perfil supuestamente endurecido: `/backup/list` → 200 sin creds). Con mounts corregidos, api uid 1000 crash-loop: `logs/soar` 755 root + `setup_logging` propagaba `PermissionError` | `docker compose config`: api sin `volumes:`; test mínimo `!reset` vs `!override` en v5.4.0; batería auth live 401/200 tras fix | `!reset`→`!override`; mounts `runtime/coverage` + `runtime/data/api`; `setup_logging` degrada a consola; perms host `a+rwX`; regresión `TestHardenedApiVolumes` |

| 54 | `tests/performance/` (db + workflow) | (a) `terms` agg sobre `type` (text) → 400 fielddata; (b) `term` sobre `alert_id` (text) → IndexError determinista; (c) retry test mockeaba `execute_workflow` (la unidad bajo test) — el retry real quedaba fuera, imposible que reintentara | suite live `4 failed` reproducidos | `.keyword` en agg y terms; retry test contra `api_workflow_executions` + `_session.get` parcheado — ejerce el bucle real |

| 55 | `test_docker_build_validation.py` | Guarda con comentario «Skip when inside container» implementada como `assert` → 4 fallos deterministas en `pytest tests/integration` en contenedor (`apps/` no montado) | 4×FAILED reproducidos en contenedor; host verde | `pytest.skip` real en los 4 puntos — skip en contenedor, aserciones en host |
| 56 | `test_app_e2e.py` | `timeout=5` en probes `/backup/create`+`/backup/restore` — I/O pesada que excede 5 s bajo carga → falso fallo intermitente | FAILED en suite (read timeout=5), PASSED en solitario (~8 s) | `timeout=60` en ambos probes (el test mide disponibilidad, no latencia) |
| 57 | `pyproject.toml` (extra `quality`) | `tests/quality` invoca `interrogate`, `import-linter` y `pip_audit` sin estar declarados en el extra → `No module named` → 4-5 tests FAILED | `python3 -m interrogate` → module not found; `pip list` confirma ausencia | 3 paquetes añadidos al extra `quality` + instalados en contenedor vivo |
| 58 | `docker-compose.api.yml` + `docker-compose.hardened.yml` | `.bandit` (config root con skips) no montado en api → `bandit -c .bandit` aborta, stdout vacío → `parse_bandit` "Failed to parse" → 3 tests FAILED (familia BUG-053) | `/app/.bandit` inexistente; bandit `Could not read config file` | mount `.bandit` en ambos perfiles + regresión `TestQualityToolMounts` (8 asserts paramétricos) |
| 59 | `base_client.py` + `structured.py` + `middleware/trace_id.py` | Ciclo `infrastructure <-> interfaces` real: `trace_id_ctx`/`get_trace_id` en capa interfaces importado lazy por infra+logging — el lazy esquivaba el ImportError, no el edge | `test_no_circular_imports_ast` FAILED: 2 ciclos detectados | nuevo `common/trace_context.py` (capa base); middleware re-exporta; imports top-level desde `common` — ciclo eliminado estructuralmente |
| 60 | `base_client.py` + `simulate_alerts.py` | 7 errores ruff: E402 ×5 (imports tras monkey-patch DNS) + E501 ×2 (>100 chars) | `test_no_ruff_errors` FAILED con los 7 errores | imports `soar_lab.*` al bloque superior; f-strings partidas |
| 61 | `test_mutation_quality.py` | `assert results is not None` exigía artefactos de `mutmut run` on-demand (60-180 min) → FAILED determinista (clase BUG-055) | FAILED `No mutmut results found` | `assert` → `pytest.skip` documentado |

**Total acumulado: 61 bugs, 61/61 con regresión permanente.**

> Nota sobre BUG-035: el fallo era invisible a nivel pytest (los
> `record_assertion` son no fatales) y solo visible en los result JSON
> (`passed: 10/11`, `grafana_healthy` con error `'t0'`). Valida la regla
> del proyecto: los artifacts de evidencia son parte del oráculo del
> test, no solo el exit code.

### 10.2 Hardening preventivo (sin bug confirmado → no cuenta en el registro)

- `helpers/polling.py` — docstrings mentían ("returns False" pero lanza
  `TimeoutError`); corregidos + `time.time()`→`time.monotonic()` (código
  muerto, sin callers).
- `setup_analyzers_and_iocs.py` — `list(set(...))[0]` no determinista →
  `sorted(...)[0]` (seed reproducible).
- `helpers/timing.py` / `docker_control.py` — `time.time()`→`monotonic()`
  en bucles de espera.

### 10.3 Verificado sin defecto (muestra representativa)

- `clean_shuffle_executions.py` (operaciones destructivas) — defensivo
  por operación: 404→skip, no-200→warn, try/except acotado. `shell=True`
  en `test_summary.py` — solo comandos internos estáticos.
  `ast.literal_eval` en setup Shuffle — uso correcto (alternativa segura
  a `eval`).
- `config_mixin.load_env` — precedencia `os.environ` > `.env.full`
  intencional (documentado); difiere de conftest pero es por diseño.
- `evidence_mixin`, `cleanup_mixin`, `service_mixins`, `semantic_mixin`,
  `observability_mixin`, `run_context_mixin` — timeouts acotados,
  manejo de excepciones razonable para infra de test.

### 10.4 Estado E2E (cadena relanzada tras clean-shuffle)

- TC-04 `test_concurrent_alerts`: **PASSED 4/4** (151 s; la primera pasada
  ~302 s refleja la congestión previa, no el código corregido).
- TC-04 `test_single_alert_latency`: **PASSED 4/4** (78.7 s).
- TC-05 `test_concurrent_alerts` (6 tests): **4 PASSED + 2 ERROR de
  setup** — `Cortex: Read timed out (10 s)` en el health check inicial
  (transitorio, Cortex saturado por analyzers). **Re-run: 6/6 PASSED**
  (641 s para los 2 reintentados) con JSON 4/4 limpio — confirma tanto
  el carácter transitorio como el fix de BUG-035.
- TC-06 `test_critical_severity`: **5 PASSED + 1 FAILED** → tras
  BUG-034 corregido, `test_auto_escalation` **PASSED** (120 s). TC-06
  completo en verde.

Clasificación del incidente TC-05: `DEPENDIENTE_DEL_ENTORNO` — timeout de
10 s en health-check vs Cortex cargado; no indica defecto de producción
(el servicio respondía a peticiones reales). Residual: considerar
`read timeout` mayor en el health check de Cortex si se repite.

**Actualización TC-04 (tras BUG-062/063/064/065, docs/13)**: la cadena
TC-00..04 relanzada produjo 40 PASSED + 4 FAILED + 1 ERROR, todos en
`test_performance.py`. Los defectos deterministas se corrigieron:
- BUG-062: snapshot `.env.container` stale tras rotación de key → 401
  determinista (fix + 7 regresión).
- BUG-063: `test_queue_depth` consultaba `workflowexecution-000001` en
  Elasticsearch en vez de OpenSearch (test fix → PASSED).
- BUG-064: esperaba `std`, el contrato es `std_dev` (test fix → PASSED).
- BUG-065: los artifacts reportaban PASSED con pytest FAILED (fix + 6
  regresión; verificado live — los artifacts nuevos reportan FAILED).

Residual honesto: `test_concurrent_alerts` y `test_performance_suite`
siguen fallando de forma **intermitente** por el techo de capacidad
webhook→OpenSearch síncrono (perfil lab: ~2-3 escrituras concurrentes
sostenidas; en la última corrida limpia 2/10 submissions → HTTP 500).
El test es la evidencia del límite, no un bug de producto — su criterio
(10/10) excede la capacidad medida del stack; pasó 4/4 cuando el backend
no estaba congestionado.

**Efecto sistémico de BUG-035**: los JSON `FAILED 3/4`/`10/11` en TC-05,
TC-06 y varios TC-KPI-* compartían el patrón "una aserción grabada
falla" — la misma `grafana_healthy` fantasma. Tras el fix en la clase
base, el re-run de TC-05 escribe 4/4 sin aserciones falladas. Resta
verificar TC-07..TC-33 (sin artefactos aún en este entorno).
