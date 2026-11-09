# Validación exhaustiva de marcos — SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
- [2. Alcance](#2-alcance)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 NIST SP 800-61r2](#31-nist-sp-800-61r2--ciclo-de-respuesta-a-incidentes)
  - [3.2 ISO/IEC 27035 e ISO/IEC 27001 Annex A](#32-isoiec-27035-e-isoiec-27001-annex-a)
  - [3.3 MITRE ATT&CK / D3FEND](#33-mitre-attck--d3fend)
  - [3.4 CACAO](#34-cacao)
  - [3.5 NIST CSF 2.0](#35-nist-csf-20--seis-funciones)
  - [3.6 NIST SP 800-207 (Zero Trust)](#36-nist-sp-800-207-zero-trust)
  - [3.7 OWASP API Security Top 10 (2023)](#37-owasp-api-security-top-10-2023)
  - [3.8 ISO/IEC 25010](#38-isoiec-25010--las-8-características)
  - [3.9 CIS Docker Benchmark](#39-cis-docker-benchmark--verificado-con-docker-inspect)
  - [3.10 Evidencia en vivo](#310-evidencia-en-vivo-04-11-2026)
- [4. Validación](#4-validación)
- [5. Problemas](#5-problemas)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Validación control-a-control de los marcos que el laboratorio declara
implementar. A diferencia de `07-framework-evaluation.md` (evaluación
por fases), este documento desglosa **cada control individual** con un
veredicto (✅ implementado / 🟡 parcial / ➖ no aplica / ❌ ausente) y
evidencia verificable: fichero, test, o salida de comando sobre el stack
en ejecución.

### 1.2 Contexto

Ejecutado el 04-11-2026 sobre el stack en marcha (23 contenedores
`soar_*`, todos healthy). Los comandos de verificación en vivo se citan
literales en §3.10 y en las celdas de evidencia.

## 2. Alcance

### 2.1 Qué cubre

10 marcos del backlog + controles de gestión de incidentes de
ISO/IEC 27001:2022 Annex A (A.5.24–A.5.28), añadidos por completitud
dado que el laboratorio implementa el ciclo IR completo.

### 2.2 Límites

- Veredictos en contexto de laboratorio académico; la contención es
  simulada (`status="simulated"`) y así se evalúa.
- Los controles del perfil hardened se evalúan por configuración
  (`docker-compose.hardened.yml` validado con `compose config`, exit 0);
  la validación live (VAL-016/017) se realiza tras la cadena E2E.

### 2.3 Dependencias

Stack levantado con `make up`; `docker inspect`, `curl`, greps sobre
`src/`, `tests/`, `infra/`.

## 3. Contenido principal

### 3.1 NIST SP 800-61r2 — ciclo de respuesta a incidentes

| Fase / control | Veredicto | Evidencia |
| --- | --- | --- |
| **Preparation** — políticas y plan | ✅ | `docs/06-project-management.md`, playbooks del workflow `SOAR-Ransomware-Response`, setup reproducible 19 pasos |
| Preparation — herramientas | ✅ | 23 servicios orquestados; preflight automático (`make preflight`) |
| Preparation — capacitación/reproducibilidad | ✅ | `.env.example`, `generate_secrets.py`, Makefile documentado |
| **Detection & Analysis** — sensores | ✅ | Simulador SIEM (`src/soar_lab/simulator/`), network-watcher, Tenzir, Promtail→Loki |
| Detection — análisis/enriquecimiento | ✅ | Cortex (10 analyzers activos, verificado `/api/analyzer`), MISP, Elasticsearch `soar-alerts` |
| Detection — priorización | ✅ | Scoring pondera técnicas de alto riesgo (`scoring` en domain) |
| Detection — notificación | ✅ | Webhook → Shuffle → decision node; tests TC-01/TC-02 |
| **Containment** — estrategia | ✅ Simulado + **enforce real** | Nodo `containment` → `POST /api/v1/contain`. Modo `simulated` por defecto; modo `enforce` (`SOAR_CONTAIN_ENFORCE=1`) ejecuta contención real verificable: `docker network disconnect` + `pause` sobre contenedor víctima allowlisted (`soar.victim=true` / prefijo `victim_`), con evidencia before/after en la respuesta — 9 tests (`test_contain_enforce.py`) |
| Containment — evidencia | ✅ | Traza completa: correlation_id en ES+OpenSearch+Loki (TC-32 golden thread) |
| **Eradication** | 🟡 Nivel lab | Limpieza de casos TheHive (`clean-thehive`), reset de stack (`make reset`), `container_pause` real sobre la víctima en modo enforce; no hay imágenes/hosts reales comprometidos que erradicar por diseño |
| **Recovery** — restauración | ✅ | `/backup/create`, `/backup/restore` + TC-22 persistencia |
| Recovery — validación post-recuperación | ✅ | Smoke tests (25) + health checks tras restore |
| **Post-Incident** — lessons learned | ✅ | KPIs MTTR (TC-KPI-01..06), informe E2E (`scripts/reports/generate_e2e_report.py`) |
| Post-Incident — retención de evidencia | ✅ | Forense TC-21, IoCs reales TC-33, casos TheHive persistentes |

### 3.2 ISO/IEC 27035 e ISO/IEC 27001 Annex A

| Control | Veredicto | Evidencia |
| --- | --- | --- |
| 27035 — Plan & Prepare | ✅ | igual que NIST Preparation |
| 27035 — Detection & Reporting | ✅ | pipeline simulador→webhook→workflow verificado E2E |
| 27035 — Assessment & Decision | ✅ | `calc_decision.py` (benign/malicious → contain/monitor) |
| 27035 — Response | ✅ | contención real ejecutable (modo enforce verificable) + notificación a TheHive real |
| 27035 — Lessons Learnt | ✅ | KPIs + informe + matriz de trazabilidad |
| **A.5.24** Planificación de gestión de incidentes | ✅ | playbooks, runbooks (`docs/04-operations.md`) |
| **A.5.25** Evaluación y decisión de eventos | ✅ | scoring + decision gate en workflow |
| **A.5.26** Respuesta a incidentes | ✅ | orquestación real end-to-end; acción final simulada *o* real (`mode=enforce` → docker disconnect+pause verificable) |
| **A.5.27** Aprendizaje de incidentes | ✅ | MTTR histórico vs actual (SOAR-004), TC-KPI |
| **A.5.28** Recolección de evidencia | ✅ | TC-21 forense, TC-32 golden thread, logs Loki correlacionados |
| A.8.15 Registro de logs | ✅ | Promtail→Loki→Grafana; `x-request-id` propagado (verificado: `curl -I /health` devuelve `x-request-id`) |
| A.8.16 Monitorización | ✅ | Grafana KPI dashboard + `/analytics/*` + node-timings |
| A.8.25 Desarrollo seguro | ✅ | quality gates CI: ruff/black/isort/flake8/mypy/bandit/vulture/radon, coverage ≥ 80 % |

### 3.3 MITRE ATT&CK / D3FEND

| Control | Veredicto | Evidencia |
| --- | --- | --- |
| Mapeo de técnicas | ✅ | **53 IDs únicos** `T1xxx(.xxx)` en `src/`, `tests/`, `scripts/` — incluye T1486 (Data Encrypted), T1490 (Inhibit Recovery), T1021.004 (SSH), sub-técnicas |
| Mapeo de tácticas | ✅ | `MITREInfo` valida `TA0001`–`TA0010` (`config/schemas/mitre.py`) |
| Alertas con contexto ATT&CK | ✅ | Simulador emite mitre_info por alerta; TC-09 ransomware realista |
| D3FEND — contramedidas | ✅ | TC-29/TC-31 `test_compliance.py` validan alineación acción↔mitigación |
| Cobertura ofensiva realista | ✅ | TC-33 IoCs reales de campaña gminst4ll |
| Gap | ✅ | Export STIX 2.1 implementado: `scripts/quality/export_attack_stix.py` → `reports/stix/attack_coverage.stix.json` (141 objetos: 53 attack-pattern con `external_references` a attack.mitre.org, course-of-action por respuesta, `mitigates` relationships, grouping por escenario; 10 tests unitarios). TAXII sigue fuera de alcance (los IoCs viven en MISP, que sí lo soporta) |

### 3.4 CACAO

| Control | Veredicto | Evidencia |
| --- | --- | --- |
| Playbook ejecutable | ✅ | `SOAR-Ransomware-Response` en Shuffle (webhook → enrich → decide → act → notify) |
| Serialización CACAO (JSON estándar) | ✅ | `scripts/quality/export_cacao.py` → `reports/cacao/soar_ransomware_response.cacao.json`: playbook `cacao-2.0` válido (44 steps: 40 action + start/end + parallel fan-out + if-condition para la puerta de decisión; IDs deterministas uuid5; 12 tests unitarios) |
| Semántica equivalente | ✅ | trigger/actions/decision gates mapean a CACAO playbook steps; el export es *más* fiel que el grafo runtime (Shuffle 2.2.1 no evalúa condiciones de branch; el if-condition CACAO modela la semántica real) |

**Veredicto**: cumplido — elementos sin equivalencia directa documentados en `unmet_requirements` (posiciones de canvas, bindings `$var`, analyzers dinámicos añadidos en runtime)
(`scripts/setup/shuffle_workflow/` tiene los artefactos fuente).

### 3.5 NIST CSF 2.0 — seis funciones

| Función | Veredicto | Evidencia |
| --- | --- | --- |
| **GOVERN** (nueva en 2.0) | ✅ | Roles/responsabilidades documentadas, riesgos residuales trazados (RR-01..RR-xx en `09`), política de secretos |
| **IDENTIFY** | ✅ | Inventario de activos = compose declarativo; superficie mapeada por ATT&CK; diagramas en `02-architecture.md` |
| **PROTECT** | ✅ | JWT+RBAC, sanitización, TLS nginx, gestión de secretos, rate limiting |
| **DETECT** | ✅ | SIEM sim, watchers, Tenzir, Loki, analyzers — pipeline verificado |
| **RESPOND** | ✅ | Orquestación completa; contención ejecutable real sobre víctimas allowlisted (modo enforce con evidencia before/after) |
| **RECOVER** | ✅ | Backup/restore probado (TC-22), `make reset` + restauración de credenciales |

### 3.6 NIST SP 800-207 (Zero Trust)

| Pilar | Veredicto | Evidencia |
| --- | --- | --- |
| Identidad | ✅ | JWT con exp/iat + roles ADMIN/ANALYST/READONLY + `X-Service-Token` para workload |
| Dispositivos/cargas | 🟡 | Healthchecks en todos los servicios; auth de endpoints opt-in (`API_REQUIRE_AUTH`) |
| Redes | ✅ | **3 redes aisladas** verificadas en vivo (`soar_net`, `ti_net`, `logging_net`); TC-20 valida segmentación; TC-30 air-gap |
| Cargas de trabajo | ✅ | Contenedores con healthcheck, límites de memoria, restart policy |
| Datos | ✅ | ES/OpenSearch con índices dedicados (`soar-alerts`, `workflowqueue`); acceso por API key |
| Visibilidad | ✅ | Loki+Grafana+Promtail+Tenzir; request-id end-to-end |
| Automatización | ✅ | Shuffle orquesta todo el ciclo; preflight/Makefile |

### 3.7 OWASP API Security Top 10 (2023)

| Riesgo | Veredicto | Evidencia |
| --- | --- | --- |
| API1 Broken Object Level Authorization | 🟡 | JWT+RBAC a nivel función; no hay objetos multi-tenant — el riesgo es bajo por diseño (sin ownership por usuario) |
| API2 Broken Authentication | ✅ | JWT exp/iat verificado; `curl` con credenciales malas → **401 en vivo**; tests de falsificación/bypass |
| API3 Broken Object Property Authorization | ✅ | `response_model` Pydantic fijos; sanitización de entrada exhaustiva |
| API4 Unrestricted Resource Consumption | ✅ | `RateLimitMiddleware` (sliding window, keying token/IP, reglas por prefijo, 429+`Retry-After`) — 12 tests unitarios + **verificado en vivo**: headers `X-RateLimit-*` en todas las respuestas, límite 300 global / 30 en `/auth` leídos de env (BUG-045), ráfaga de 32 req a `/auth/login` → 429 con `retry-after` y `{"code":"rate_limited"}`. Webhook `WEBHOOK_PAYLOAD_MAX_SIZE=64KB` |
| API5 Broken Function Level Authorization | ✅ | `require_api_auth` verificado **en vivo en perfil hardened** (VAL-004): `/backup/list`+`/backup/create` sin cred → 401; `X-Service-Token` válido → 200; JWT login+Bearer → 200; inválido → 401; `/health` público → 200. En perfil lab sigue opt-in (`API_REQUIRE_AUTH=false` en `.env` intencional) — BUG-053 corrigió mounts que impedían que el flag aplicara |
| API6 Unrestricted Access to Sensitive Business Flows | 🟡 | `/tests/run`, `/backup/restore` protegidos solo en hardened; rate limit en `/api/v1/contain` |
| API7 SSRF | ✅ | Proxies `/soar/*` a upstreams fijos internos; path params tipados vía Pydantic; sin URLs arbitrarias de usuario |
| API8 Security Misconfiguration | 🟡 | TLS 1.2/1.3 + `HIGH:!aNULL:!MD5` en nginx (verificado); Swagger configurable; CORS por env; **API interna HTTP plano** entre contenedores (red docker aislada — aceptable) |
| API9 Improper Inventory Management | ✅ | OpenAPI versionado + `test_openapi_spec_sync.py` en CI garantiza spec↔código |
| API10 Unsafe Consumption of APIs | ✅ | Circuit breaker + retry + timeout en clientes de integración; sanitización de respuestas externas |

### 3.8 ISO/IEC 25010 — las 8 características

| Característica | Veredicto | Evidencia |
| --- | --- | --- |
| Adecuación funcional | ✅ | E2E TC-00..33 cubren el flujo completo + edge cases |
| Eficiencia | ✅ | `tests/performance/` (20 tests externos: latencia, throughput, concurrencia), TC-26 carga extrema |
| Compatibilidad | ✅ | FastAPI + estándares (OpenAPI, STIX vía MISP, syslog→Loki) |
| Usabilidad | ✅ | Web management UI + docs-site + `make` autodocumentado |
| Fiabilidad | ✅ | Circuit breaker, retry, timeout, modo degradado TC-18, recuperación TC-16 |
| Seguridad | ✅ | Suite dedicada (LDAPi, traversal, XSS, JWT forgery, payloads 1 MB) + sanitizer |
| Mantenibilidad | ✅ | Hexagonal enforceado AST, complejidad ponderada en `calculate_quality_score.py`, docstrings ~95 %, vulture 0 |
| Portabilidad | ✅ | 23 contenedores Compose, Makefile win/linux, perfiles documentados |

### 3.9 CIS Docker Benchmark — verificado con `docker inspect`

| Control | Estado en vivo | Evaluación |
| --- | --- | --- |
| `privileged` | **0/23** contenedores | ✅ |
| `cap_add` | solo `CAP_AUDIT_WRITE` (MISP — la imagen misp-docker escribe audit records desde su entrypoint; residual: prueba sin la cap documentada como mejora pendiente) | 🟡 justificado |
| `seccomp:unconfined` | solo `soar_orborus` en perfil lab — **eliminado en hardened y verificado live**: `SecurityOpt=[]` (perfil default Docker) con orborus healthy y spawneando workers | ✅ hardened / 🟡 lab |
| `user` | `root` explícito: api, redis en lab; **hardened verificado live**: api `uid 1000` + `cap_drop ALL` + `no-new-privileges`, redis `uid 999` | ✅ hardened / 🟡 lab |
| docker.sock | 4 mounts raw (api, orborus, watcher, promtail) + **cortex y shuffle-backend** vía `docker.proxy.sock` de Docker Desktop; **hardened verificado live**: socket-proxy `v0.4.1` sirviendo tráfico real (200) a api + network-watcher con verbos whitelisteados; orborus conserva socket crudo por diseño (spawnea workers); guardián `tests/architecture/test_docker_socket_access.py` | ✅ hardened / 🟡 justificado |
| `read_only` rootfs | 0 contenedores | ➖ no aplicado (bind-mounts de desarrollo) |
| Límites de memoria | **23/23** con `mem_limit` (256 MB–4 GB) | ✅ |
| Restart policy | 23/23 `unless-stopped` | ✅ |
| Healthcheck | **23/23 definidos** — añadidos renderer (`wget :8081/`) y shuffle-backend (`/api/v1/health`, verificado 200 en vivo); **21/23 reportan healthy en vivo** — `soar_shuffle_backend` y `soar_grafana_renderer` corren desde antes de definirse (lo activa el próximo `make up`) | ✅ |
| Logging centralizado | Promtail→Loki todos los contenedores | ✅ |
| Imágenes con digest | `verify_image_digests.py` — **17/17 verificados** (16 registry + orborus local vía `docker image inspect`); `make verify-digests` = gate bloqueante (exit 1); en `make up` avisa sin bloquear (tolerancia offline documentada) | ✅ |
| Red expuesta mínima | puertos publicados solo a localhost donde aplica | ✅ |

### 3.10 Evidencia en vivo (04-11-2026)

```text
docker network ls        → soar_net, ti_net, logging_net (API en las 3)
docker inspect sock      → 4 raw mounts + cortex y shuffle-backend
                           vía docker.proxy.sock
docker inspect user      → api=root, redis=root (hardened: non-root)
docker inspect seccomp   → solo orborus unconfined
nginx ssl_protocols      → TLSv1.2 TLSv1.3
curl -I /health          → x-request-id + X-RateLimit-* presentes
                           (post-restart VAL-002; límites env 300/30 post-BUG-045)
curl /backup/list        → 200 sin auth (lab: API_REQUIRE_AUTH off)
curl -X POST /auth/login (credenciales malas) → 401
ráfaga 32× /auth/login   → req 29-32: 429 + retry-after + rate_limited
cortex /api/analyzer     → 10 analyzers activos
grep T-IDs               → 53 IDs ATT&CK únicos (incl. sub-técnicas)
```

## 4. Validación

### 4.1 Verificación

Cada control cita fichero, test o comando ejecutado durante esta
validación. Los comandos de §3.10 se ejecutaron contra el stack en
marcha con la suite E2E corriendo en paralelo.

### 4.2 Criterios de aceptación

- Todos los marcos del backlog evaluados control a control ✅
- Cobertura real/simulada/parcial diferenciada por control ✅
- Evidencia reproducible (comandos literales) ✅
- Conteo de docker.sock **corregido** frente a la estimación previa
  (4 raw + 1 proxy vs "5–6" estimado) ✅

### 4.3 Evidencias

`docker inspect` (23 contenedores), `grep` sobre `src/`/`tests/`,
endpoints en vivo, `nginx.conf`, `docker-compose.hardened.yml`.

## 5. Problemas

### 5.1 Limitaciones

- CACAO: export a estándar implementado (`export_cacao.py`, VAL-007).
  Limitación residual: export del grafo *base* — los analyzers Cortex
  dinámicos se añaden en runtime según disponibilidad.
- Auth de endpoints críticos opt-in: en lab `/backup/*` responde sin
  credenciales (decisión documentada para UX del laboratorio; hardened
  lo activa con `API_REQUIRE_AUTH=true`).
- ~~Rate limiting pendiente de restart~~ → **resuelto (VAL-002/003)**:
  tras `docker restart soar_api` los headers `X-RateLimit-*` aparecen en
  todas las respuestas y la ráfaga de 32 req a `/auth/login` produce
  429 + `retry-after`. Además BUG-045 corrigió la lectura de los límites
  desde env (`RATE_LIMIT_*`/`API_REQUIRE_AUTH` se ignoraban por el lookup
  case-sensitive de `InfrastructureConfigProvider.get`).

### 5.2 Riesgos o incidencias

- Logs de MISP/shuffle-backend imprimen secretos en arranque
  (`REDIS_PASSWORD` en URL de session.save_path, `MISP_ADMIN_PASSWORD`,
  `MISP_API_KEY`, `SIEM_WEBHOOK_TOKEN` en URL de hook — comportamiento
  upstream de las imágenes, no modificable sin fork).
  **Mitigado en la capa de ingestión**: `pipeline_stages` de Promtail
  redactan estos patrones antes de Loki (verificado contra las líneas
  reales). Los `docker logs` crudos siguen conteniéndolos — residual.
- `.env.full` versionado: aceptado por el autor (académico).

### 5.3 Recomendaciones

1. ~~Tras el E2E: restart API → verificar 429/`X-RateLimit-*`~~ → hecho:
   verificado en vivo (VAL-002/003). ~~Re-evaluar API5 con
   `API_REQUIRE_AUTH=true`~~ → hecho (VAL-004): 401 sin cred/inválidos,
   200 con service-token y JWT.
2. ~~`make up HARDENED=1` + smoke para validar el overlay en vivo
   (seccomp de orborus, usuarios non-root, socket proxy)~~ → hecho
   (VAL-016/017): overlay levantado quirúrgicamente (`compose up -d` con
   el file hardened — `make up` regenera secretos); proxy `v0.4.1`
   sirviendo tráfico real, api uid 1000 + `cap_drop ALL`, redis 999 +
   NOAUTH, orborus seccomp default. BUG-053 documenta el fix de mounts
   que hizo esto posible.
3. ~~Export CACAO~~ → implementado: `scripts/quality/export_cacao.py`
   (playbook `cacao-2.0`, 44 steps, if-condition real para la puerta de
   decisión).
4. ~~Scrub de logs~~ → hecho: `pipeline_stages` de redacción en
   Promtail (raw docker logs = residual upstream documentado).

## 6. Referencias

- `docs/07-framework-evaluation.md` (evaluación resumida)
- `docs/08-execution-profiles.md`, `docs/09-traceability-matrix.md`
- NIST SP 800-61r2, ISO/IEC 27035, ISO/IEC 27001:2022 Annex A,
  MITRE ATT&CK v16, MITRE D3FEND, OASIS CACAO v2.0, NIST CSF 2.0,
  NIST SP 800-207, OWASP API Security Top 10 2023, ISO/IEC 25010:2023,
  CIS Docker Benchmark v1.6.
