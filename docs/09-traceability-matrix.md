# Matriz de trazabilidad de requisitos — SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
- [2. Alcance](#2-alcance)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 Requisitos → tests](#31-requisitos--tests)
  - [3.2 TC-00..TC-33 → requisito validado](#32-tc-00tc-33--requisito-validado)
  - [3.3 KPIs → fases de respuesta](#33-kpis--fases-de-respuesta-a-incidentes)
  - [3.4 ATT&CK/D3FEND → workflows](#34-attckd3fend--workflows)
  - [3.5 Riesgos residuales](#35-riesgos-residuales)
- [4. Validación](#4-validación)
- [5. Problemas](#5-problemas)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Relacionar marcos → requisitos → componentes → tests → KPIs, de modo que
cada afirmación del diseño tenga verificación trazable y cada caso E2E
identifique qué requisito valida (SOAR-024).

### 1.2 Contexto

Versión 1.4.0, tras la remediación de tests y la introducción del perfil
hardened. Ver `07-framework-evaluation.md` para el detalle por marco.

## 2. Alcance

### 2.1 Qué cubre

Los requisitos derivados de los 10 marcos evaluados, los 34 casos E2E,
los 6 KPIs y los riesgos residuales conocidos.

### 2.2 Límites

La matriz cubre la capa de laboratorio; requisitos de producción real
(EDR, PKI, HA) están fuera de alcance y listados como trabajo futuro.

## 3. Contenido principal

### 3.1 Requisitos → tests

| Req | Marco | Componente | Tests |
| --- | --- | --- | --- |
| R-01 Detección de alertas SIEM | NIST 800-61 Detect | simulator + webhook Shuffle | TC-01, TC-02, TC-00 |
| R-02 Enriquecimiento multi-fuente | NIST 800-61 Analyze | Cortex, MISP, ES | TC-03, TC-14 |
| R-03 Decisión por scoring | Playbook | nodo `calc_decision` | TC-01, TC-02, TC-06 |
| R-04 Contención (simulada) | NIST 800-61 Contain | `/api/v1/contain` | TC-31 |
| R-05 Notificación/registro | Post-incident | TheHive cases, ES docs | TC-14, TC-32 |
| R-06 Trazabilidad e2e | ISO 27035 | correlation_id, golden thread | TC-32 |
| R-07 Persistencia y backup | NIST CSF Recover | volúmenes, backup svc | TC-22 |
| R-08 Resiliencia degradada | ISO 25010 Reliability | circuit breaker, retry | TC-16, TC-18 |
| R-09 Zero Trust segmentación | NIST 800-207 | 3 redes Compose | TC-20 |
| R-10 Air-gap / offline | Lab | modo offline | TC-30 |
| R-11 Forense | NIST 800-86 | IoCs, evidencias | TC-21, TC-33 |
| R-12 Seguridad API | OWASP API | JWT, RBAC, sanitizer, rate limit | TC-19, `tests/security/`, `tests/unit/api/test_rate_limit_middleware.py`, `test_require_api_auth.py` |
| R-13 Métricas de respuesta | ISO 27035 post | KPI pipeline ES/Grafana | TC-KPI-01..06 |
| R-14 Privacidad | Lab | redacción de datos | TC-23 |

### 3.2 TC-00..TC-33 → requisito validado

| TC | Fichero | Requisito principal |
| --- | --- | --- |
| TC-00 | test_both_workflows | R-01/R-02 ambos caminos del flujo |
| TC-01 | test_malicious | R-01..R-05 pipeline malicioso completo |
| TC-02 | test_benign | R-01..R-05 pipeline benigno (no contención) |
| TC-03 | test_edge_cases | R-02 robustez de entrada |
| TC-04 | test_performance | R-13 tiempos del pipeline |
| TC-05 | test_concurrent_alerts | R-02 concurrencia |
| TC-06 | test_critical_severity | R-03 scoring crítico |
| TC-07 | test_missing_fields | R-02 campos opcionales |
| TC-08 | test_additional_fields | R-02 campos extra |
| TC-09 | test_realistic_ransomware | R-01/R-11 escenario por etapas |
| TC-10 | test_tenzir_integration | R-05 integración Tenzir |
| TC-11 | test_network_watcher_integration | R-09 monitorización de red |
| TC-12 | test_redis_integration | R-04 caché de IoCs |
| TC-13 | test_loki_integration | R-13 logs centralizados |
| TC-14 | test_complete_soar_integration | R-01..R-06 flujo completo |
| TC-15 | test_api_latency | R-13 latencia API |
| TC-16 | test_error_handling | R-08 manejo de errores |
| TC-17 | test_network_watcher_monitoring | R-09 |
| TC-18 | test_resilience | R-08 degraded mode |
| TC-19 | test_security | R-12 (JWT, headers, rate limiting) |
| TC-20 | test_zero_trust | R-09 |
| TC-21 | test_forensic | R-11 |
| TC-22 | test_persistence | R-07 |
| TC-23 | test_privacy | R-14 |
| TC-24 | test_malware_specific | R-01 |
| TC-25 | test_behavioral_detection | R-02 |
| TC-26 | test_extreme_load | R-13/R-08 |
| TC-27 | test_configuration | R-12 config |
| TC-28 | test_ui_e2e | R-05 interfaces |
| TC-29 | test_compliance | R-12 marcos ATT&CK/D3FEND |
| TC-30 | test_offline_mode | R-10 |
| TC-31 | test_compliance | R-04 endpoint contención |
| TC-32 | test_golden_thread | R-06 |
| TC-33 | test_gminst4ll_real_iocs | R-11 IoCs reales |

### 3.3 KPIs → fases de respuesta a incidentes

| KPI | Fase (NIST 800-61) | Qué mide |
| --- | --- | --- |
| TC-KPI-01 MTTR | Detect→Recover | Tiempo medio total de respuesta |
| TC-KPI-02 Dashboard | Post-incident | Visualización KPI en Grafana |
| TC-KPI-03 Alertas KPI | Post-incident | Datos de alertas en ES |
| TC-KPI-04 Percentiles MTTR | Post-incident | Distribución p50/p90/p95 |
| TC-KPI-05 Node timings | Detect/Analyze/Respond | Tiempo por nodo del workflow |
| TC-KPI-06 Coherencia | Post-incident | Consistencia alert_id/correlation_id entre sistemas |

**Baseline histórica (24-ago-2026)**: 50 workflows, MTTR medio 277 s,
MTTR ransomware 261 s, contención 92 %, éxito de workflow 100 %.
La comparación con la ejecución actual queda en `reports/e2e/`.

### 3.4 ATT&CK/D3FEND → workflows

- Scoring: 9 técnicas de alto riesgo ponderan la decisión
  (`decision_engine`, `config/schemas/`).
- D3FEND: `Isolate`/`Contain` ↔ nodo 27 `containment` (TC-29/31);
  `Detect` ↔ enriquecimiento Cortex; `Restore` ↔ backup (TC-22).
- ATT&CK tactics/techniques propagados en documentos ES y casos
  TheHive (TC-32 trazabilidad).

### 3.5 Riesgos residuales

| ID | Riesgo | Estado |
| --- | --- | --- |
| RR-01 | `.env.full` versionado en git con secretos de laboratorio | **Aceptado por diseño** (proyecto académico — facilita reproducibilidad). Rotar si el repo pasa a entorno compartido/producción |
| RR-02 | Secretos en logs de MISP/shuffle-backend al arranque | Detectado por `make scan-secrets`; **redactado en Promtail** (`pipeline_stages`, verificado contra líneas reales); docker logs crudos = residual upstream |
| RR-03 | docker.sock en api/orborus/network-watcher/promtail raw + cortex/shuffle-backend vía `docker.proxy.sock` | Justificado (spawn de workers, monitorización, app lifecycle); documentado; hardened aísla api+watcher tras socket-proxy; guardián `test_docker_socket_access.py` |
| RR-04 | Contención simulada | Por diseño; **modo `enforce` disponible** (`SOAR_CONTAIN_ENFORCE=1` → disconnect+pause real sobre víctima allowlisted, evidencia before/after). No presentar como EDR real |
| RR-05 | TLS OpenSearch autofirmado | Hardened documenta CA propia (SOAR-015) |
| RR-06 | `seccomp` por defecto puede romper orborus en algunos hosts | Overlay hardened preparado; validar E2E en hardened |
| RR-07 | Rate limiting en memoria (no distribuido) | Aceptable a escala lab; documentado |

## 4. Validación

- Cada TC referenciado existe en `tests/e2e/TC-*/`.
- Riesgos residuales enlazan a backlog SOAR-018/019/012/015/016.

## 5. Problemas

- La matriz se mantiene manual; considerar generación desde markers
  pytest (`@pytest.mark.requirement("R-xx")`) como mejora futura.

## 6. Referencias

- `tests/e2e/`, `docs/07-framework-evaluation.md`,
  `docs/08-execution-profiles.md`, `reports/e2e/`.
