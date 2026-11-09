# Validación de marcos — cuarta ronda (ISOs de proceso, madurez y modelos operativos)

> Evaluación del laboratorio contra marcos NO cubiertos en `docs/10`
> (ronda 1) ni `docs/12` (rondas 2-3): estándares de proceso de prueba
> (ISO/IEC/IEEE 29119, TMMi, IEEE 1012, ISO/IEC 5055), ISOs operativas
> (27005, 27043, 27039), guías NIST (800-137, 800-150, 800-190, 800-184,
> 800-37), modelos de adversario (Kill Chain, Diamond) y modelos de
> madurez (SOC-CMM/SIM3/MaGMa, OWASP DSOMM).

## Índice

- [1. Resumen](#1-resumen)
- [2. Alcance](#2-alcance)
- [3. Contenido principal](#3-contenido-principal)
- [4. Validación](#4-validación)
- [5. Problemas](#5-problemas)
- [6. Referencias](#6-referencias)

## 1. Resumen

### 1.1 Objetivo

Completar la evaluación multi-marco del proyecto con los estándares que
faltaban — énfasis en **proceso de prueba** (donde el proyecto acumula la
evidencia más fuerte: 2377 tests, defect-driven testing con regresión
permanente, mutation testing, gates de cobertura) y en **operación de
seguridad** (detección, investigación, TI sharing, contenedores,
recuperación, monitorización continua).

### 1.2 Contexto

Rondas previas: `docs/10` (NIST 800-61r2, ISO 27035/27001, ATT&CK/D3FEND,
CACAO, CSF 2.0, 800-207, OWASP API, ISO 25010, CIS Docker) y `docs/12`
(IR 8374, ISO 27002, 800-53r5, CIS v8, ASVS, SAMM, SSDF, SLSA,
Twelve-Factor, RGPD, RE&CT, TLP, OpenC2, CWE-25, STRIDE, LINDDUN,
ISO 22301, 800-92, OpenSSF). Esta ronda cierra las familias restantes.

## 2. Alcance

### 2.1 Qué cubre

15 marcos/modelos agrupados en: proceso de prueba (§3.1-3.4), gestión de
riesgo e investigación (§3.5-3.6), detección e inteligencia (§3.7-3.9),
plataforma y recuperación (§3.10-3.11), ciclo de vida RMF (§3.12),
modelos de adversario (§3.13) y madurez organizativa (§3.14-3.15).

### 2.2 Límites

Los modelos organizativos (SOC-CMM, SIM3) evalúan la capa tecnológica y
de proceso del laboratorio; las dimensiones de personas/servicios son
intrínsecamente académicas y se clasifican ➖/🟡, nunca ✅.

### 2.3 Dependencias

Veredictos apoyados en la evidencia viva acumulada: 103/103 tests
externos, cadena TC-00..33 + KPI en curso, BUG-001..065 con regresión,
perfil hardened verificado (VAL-016/017), exports CACAO/STIX (VAL-008).

## 3. Contenido principal

### 3.1 ISO/IEC/IEEE 29119 — Software Testing

El estándar organiza el proceso de prueba en: organización, gestión
(planificación, monitorización, control) y proceso dinámico (diseño,
entorno, ejecución, informe).

| Elemento | Veredicto | Evidencia |
| --- | --- | --- |
| Política/estrategia de prueba | ✅ | `docs/05-testing.md` como test policy; `pytest.ini` (markers, fail-under=80); `AGENTS.md` convenciones |
| Plan de pruebas por niveles | ✅ | `tests/` estratificado: unit, integration, atomic, e2e (TC-00..33 + TC-KPI-01..06), security, performance, quality, architecture, contracts, baseline, smoke |
| Diseño basado en técnicas | ✅ | límites/partición (parametrized), transición de estados (TC-26 aborts, TC-22 restart), property-based, mutation (mutmut), exploratorio→regresión (doc/13) |
| Documentación de casos | ✅ | TCs con `tc_id`, evidencia por caso (`manifest/result/assertions/evidence/`), tracking `reports/e2e/e2e_test_tracking.md` |
| Gestión de defectos | ✅ | ciclo de vida completo BUG-001..065: triaje→reproducción→test failing-first→fix→regresión (doc/13, §Definition of Done) |
| Monitorización/control | ✅ | gates CI (lint, coverage 80, security), KPI suites, reporte `generate_e2e_report` |
| Independencia del proceso | 🟡 | mismo equipo diseña prueba y producto (contexto académico); mitigado con revisión sistemática y falsos positivos documentados |

**Veredicto: 6/7 ✅, 1 🟡** — la conformidad práctica con 29119 es de los
puntos más sólidos del proyecto (el proceso de defectos de `docs/13` es
textbook 29119-2).

### 3.2 TMMi — Test Maturity Model Integration

| Nivel | Veredicto | Evidencia |
| --- | --- | --- |
| L2 Managed — política y planificación | ✅ | docs/05 + suites por niveles + tracking |
| L2 — monitorización y control | ✅ | artifacts por corrida, reporte e2e, coverage gate |
| L3 Defined — proceso estándar | ✅ | proceso defect-driven uniforme aplicado a 66 bugs; estructura TC homogénea (tc_id/evidence/cleanup) |
| L3 — formación/programa de prueba | 🟡 | sin roles formales (académico) |
| L4 Measured — medición del producto | ✅ | KPIs TC-KPI-01..06 (latencia, MTTR), mutation score, coverage 80 %, flakiness tracking (incidentes clasificados) |
| L4 — calidad del proceso de prueba | 🟡 | métricas del proceso en doc/13 §8 (reaperturas 0, 100 % regresión) pero sin SPC |
| L5 Optimization — prevención de defectos | ✅ | aprendizaje sistémico doc/13 §9 (cada bug → búsqueda de la familia + propiedad general) |
| L5 — mejora continua | ✅ | tests de regresión permanentes en CI; calidad de tests revisada (test-review, holistic) |

**Veredicto: L3 alcanzado con prácticas L4/L5** — inusual en laboratorios
académicos; la debilidad natural es la ausencia de organización formal.

### 3.3 ISO/IEC 5055 (CISQ) — Medidas automáticas de calidad de código

Las 4 características CISQ medidas automáticamente:

| Característica | Veredicto | Medida automática |
| --- | --- | --- |
| Reliability | ✅ | 2377 tests, mutation testing (mutmut), regresión de defectos, circuit breaker/retry testeados |
| Security | ✅ | bandit, scan-secrets, trufflehog CI, tests/security (inyección, JWT, payload) |
| Performance Efficiency | ✅ | TC-04 perf suite, TC-KPI-01..06 (latencia, throughput, MTTR), metrics endpoint |
| Maintainability | ✅ | radon (complejidad), xenon (gate CC), vulture (dead code), tests/architecture (capas hexagonales), ruff/black/isort/mypy |

**Veredicto: 4/4 características con medida automática en CI** — la
suite `tests/quality` + `scripts/quality` implementa el espíritu CISQ.

### 3.4 IEEE 1012 — Verification & Validation

| Elemento V&V | Veredicto | Evidencia |
| --- | --- | --- |
| Plan de V&V | ✅ | docs/05 (estrategia) + docs/08 (perfiles de ejecución) |
| Verificación de requisitos | ✅ | `docs/09-traceability-matrix` requisito→control→test→evidencia (RR-01..07, 68+5) |
| Verificación de diseño | ✅ | tests/architecture (dependencias hexagonales, ciclos — BUG-059), contracts/ |
| Verificación de implementación | ✅ | lint+typecheck+security gates, unit/integration (1700+) |
| Validación (sistema contra necesidad) | ✅ | cadena E2E TC-00..33+KPI como aceptación; exports CACAO/STIX validados (VAL-008) |
| Informes V&V | ✅ | docs/10-14 son el registro V&V; artifacts por test reproducibles |
| Gestión de anomalías | ✅ | clasificación por severidad/estado en doc/13 (REPORTADO→CERRADO, NO_REPRODUCIBLE, falso positivo) |

**Veredicto: V&V completo y documentado** — una de las áreas más maduras.

### 3.5 ISO/IEC 27005 — Gestión del riesgo

| Paso del proceso | Veredicto | Evidencia |
| --- | --- | --- |
| Establecimiento del contexto | ✅ | lab delimitado (académico, sin malware real, `docs/06`) |
| Identificación de riesgos | ✅ | matriz RR-01..07 (`docs/09`), riesgos §5 en cada doc de validación |
| Análisis/estimación | ✅ | severidad en registro de bugs (crítica/alta/media/baja), clasificación DEPENDIENTE_DEL_ENTORNO vs defecto |
| Evaluación | 🟡 | criterios implícitos en gates; sin apetito de riesgo formal (académico) |
| Tratamiento | ✅ | fixes con regresión, perfil hardened, compensaciones documentadas (ej. Robtex→DShield) |
| Aceptación | 🟡 | residuales declarados en docs/10-13; sin autoridad de aceptación formal |
| Comunicación | ✅ | documentación pública completa, informes reproducibles |
| Monitorización | 🟡 | tests de regresión + KPIs; sin revisión periódica formal del registro |

**Veredicto: 5/8 ✅, 3 🟡** — el ciclo es real; las partes faltantes son
las inherentes a un proyecto sin organización que lo gobierne.

### 3.6 ISO/IEC 27043 — Investigación de incidentes

| Principio | Veredicto | Evidencia |
| --- | --- | --- |
| Preparación (readiness) | ✅ | logging centralizado (Promtail→Loki), correlation_id end-to-end, timestamps UTC, retención de artifacts |
| Detección/notificación | ✅ | pipeline alerta→caso TheHive→enriquecimiento Cortex/MISP |
| Recolección de evidencia | ✅ | bundle por incidente-test: `manifest.json`, `evidence/`, assertions, cleanup log |
| Preservación/integridad | 🟡 | artifacts inmutables en `reports/validation/results`; sin cadena de custodia formal ni hashes (académico) |
| Análisis | ✅ | assertions semánticas por TC (nodos workflow, estados), Loki forense por correlation_id |
| Presentación | ✅ | e2e_report + KPI report como "informe de investigación" |
| Procesos de investigación propios | 🟡 | la "investigación" es test-driven; sin procedimiento DFIR manual |

**Veredicto: 5/7 ✅** — la trazabilidad por correlation_id es un
mecanismo genuino de clase forense.

### 3.7 ISO/IEC 27039 + NIST SP 800-94 — Detección de intrusión

| Elemento | Veredicto | Evidencia |
| --- | --- | --- |
| Motor IDS (firmas/anomalías) | ➖ | no hay Suricata/Snort/Sigma/YARA — el lab consume alertas, no las genera |
| Visibilidad de red | ✅ | network_watcher: inventario de contenedores, resolución IP, API `/connections`, inyección de hosts para contención |
| Pipeline de eventos | ✅ | Tenzir node como pipeline (`SHUFFLE_PIPELINE_URL`), ES+OpenSearch, Loki |
| Fuentes de detección | ✅ | simulador SIEM con `mitre_info` real (53 técnicas), TC-33 IoCs reales |
| Tuning de detección | 🟡 | umbrales del workflow documentados; sin gestión de reglas Sigma |
| Operación/mantenimiento IDPS | 🟡 | aplica a Tenzir/watcher, no a un IDS convencional |

**Veredicto: 🟡 parcial por diseño** — el laboratorio es la parte
**respond** de la ecuación detect→respond; la capa IDS queda simulada.
Brecha honesta registrada: sin reglas Sigma/YARA ni sensor de red real.

### 3.8 NIST SP 800-137 — Information Security Continuous Monitoring

| Estrategia ISCM | Veredicto | Evidencia |
| --- | --- | --- |
| Definir métricas | ✅ | KPIs formalizados (MTTR, latencia, cola, éxito workflow) en TC-KPI-01..06 |
| Establecer arquitectura | ✅ | Grafana + Loki + Promtail + `/metrics` + healthchecks 23/23 |
| Implementar | ✅ | `kpi_alerts.py`, `health_check_adapter`, `system_metrics_driver`, `/services/status` |
| Analizar/reportar | ✅ | KPI dashboards (Grafana), e2e_report con charts, baseline comparado |
| Responder | ✅ | el propio workflow responde a alertas; cleanup automático (clean-shuffle) |
| Revisar/actualizar | 🟡 | baselines preservados y comparados; sin cadencia formal de revisión |

**Veredicto: 5/6 ✅** — monitorización continua implementada de verdad,
no solo descrita.

### 3.9 NIST SP 800-150 — Threat Information Sharing

| Capacidad | Veredicto | Evidencia |
| --- | --- | --- |
| Consumo de TI | ✅ | MISP `restSearch` enriquece alertas (IoC→contexto) |
| Producción/compartición | ✅ | `export_attack_stix.py` (STIX 2.1), `export_cacao.py` (playbook compartible), `generate-iocs` |
| Formatos estándar | ✅ | STIX 2.1, CACAO — validados en VAL-008 |
| Transporte TAXII | 🟡 | existe dentro de MISP (sus scripts propios); el lab no implementa cliente/servidor TAXII |
| Manejo de marcado (TLP/PAP) | ✅ | cubierto en doc/12 §3.12 |
| Comunidad/confianza | ➖ | lab aislado — no hay peers de intercambio (académico) |

**Veredicto: 4/6 ✅, 1 🟡, 1 ➖** — sharing real vía formatos; el
transporte TAXII queda como mejora documentada.

### 3.10 NIST SP 800-190 — Application Container Security

| Riesgo/mitigación | Veredicto | Evidencia |
| --- | --- | --- |
| Vulnerabilidades de imagen | 🟡 | digest pinning verificado (`verify_image_digests.py`); sin escáner CVE de imágenes (trivy/grype) — mejora ya registrada en doc/12 A.8.8 |
| Config insegura | ✅ | hardened overlay: non-root uid1000, `cap_drop ALL`, `no-new-privileges`, read-only, seccomp (orborus) — verificado live VAL-016/017 |
| Secretos | ✅ | `.env.container` :ro montado, `.env.full` nunca montado (SOAR-018), generación fuerte (32+ B) |
| Contenedor→host | ✅ | socket proxy para DinD (Cortex runners), sin docker.sock crudo en hardened |
| Segmentación | ✅ | 3 redes (soar_net/ti_net/logging_net), nginx única puerta TLS |
| Runtime | ✅ | CIS Docker Benchmark validado con `docker inspect` (doc/10 §3.9); Redis NOAUTH |

**Veredicto: 5/6 ✅** — el perfil hardened es una implementación real
de 800-190, verificada con inspect, no solo YAML declarativo.

### 3.11 NIST SP 800-184 — Recovery (eventos cibernéticos / ransomware)

| Elemento | Veredicto | Evidencia |
| --- | --- | --- |
| Plan de recuperación | ✅ | `make backup/restore`, `make reset`, docs/04 operations |
| Backup verificado | ✅ | TC-22 `test_backup_integrity`, `test_backup_restore` — restauración REAL probada |
| Consistencia post-restart | ✅ | `test_docker_down_up`, `test_container_recreation`, `test_data_consistency_after_restart` |
| Limpieza post-incidente | ✅ | `clean_thehive_cases`, `clean_shuffle_executions` (ejecuciones stale saturaban Orborus — caso real documentado) |
| Lecciones aprendidas | 🟡 | informes generados; sin post-mortem formal por incidente |
| Prueba periódica del plan | ✅ | la cadena E2E ejercita backup/restore en cada ejecución completa |

**Veredicto: 5/6 ✅** — recuperación probada de verdad; seña de
madurez que IR 8374 ya destacó como inusual en labs.

### 3.12 NIST SP 800-37 — Risk Management Framework (ciclo)

| Paso RMF | Veredicto | Mapeo al laboratorio |
| --- | --- | --- |
| Categorize | ✅ | sistema categorizado por alcance (lab aislado, sin malware, datos sintéticos) |
| Select | ✅ | baseline elegido por mapeo multi-marco (docs/10-14): 27002, 800-53, CIS v8… |
| Implement | ✅ | controles implementados (auth, hardened, TLS, segmentación) |
| Assess | ✅ | evaluación con evidencia ejecutable — 68 verificados, 5 parciales (doc/12 §3.5) |
| Authorize | ➖ | sin autoridad autorizante — contexto académico |
| Monitor | ✅ | ISCM (§3.8): KPIs, Grafana, regresión continua |

**Veredicto: 4/5 aplicables ✅ + Authorize ➖** — el ciclo RMF se recorre
de facto; el paso faltante es institucional, no técnico.

### 3.13 Cyber Kill Chain / Unified Kill Chain / Diamond Model

| Fase (Kill Chain) | Cobertura | Evidencia |
| --- | --- | --- |
| Reconnaissance | 🟡 simulada | TTPs de recon en `mitre_info` del simulador |
| Weaponization/Delivery | ➖ | fuera de alcance (sin malware real — decisión deliberada) |
| Exploitation | 🟡 simulada | técnicas ATT&CK en alertas |
| Installation | ✅ simulada+detectada | TC-24 específico, persistencia como alerta |
| Command & Control | ✅ | TC-33 IoCs reales gminst4ll (C2 infra), DGA/dominios |
| Actions on Objectives | ✅ | cifrado/exfil como alertas ransomware TC-09; respuesta real (contención) |

**Diamond Model** (4 vértices): adversario=simulado (perfiles
ransomware), capacidad=TTPs ATT&CK mapeadas, infraestructura=C2/IoCs
reales (TC-33), víctima=host contenedor contenido (enforce). **4/4
vértices representados** — el modelo es coherente con el diseño.

### 3.14 SOC-CMM / SIM3 / MaGMa — Madurez de operaciones

| Dimensión SOC-CMM | Veredicto | Nota |
| --- | --- | --- |
| Tecnología | ✅ | stack SOAR completo funcional (10+ integraciones testeadas) |
| Proceso | ✅ | playbook CACAO, ciclo defect-driven, runbooks (Makefile targets) |
| Personas | ➖ | sin roles SOC (académico) |
| Servicios | 🟡 | el "servicio" es el pipeline detect→contain→notify |
| Negocio | ➖ | sin alineación empresarial |

**SIM3** (madurez de equipo de respuesta): detección ✅, análisis ✅
(enrich automático), respuesta ✅, coordinación/escalado 🟡 (notificación
implementada, escalado humano n/a).

**MaGMa** (gestión de casos de uso): catálogo de use-cases = TC-00..33 +
workflow; ciclo de vida UC (crear→probar→medir) implementado vía
framework E2E. ✅ para el alcance del lab.

### 3.15 OWASP DSOMM — DevSecOps Maturity Model

| Dimensión | Veredicto | Evidencia |
| --- | --- | --- |
| Build & Deployment | ✅ | CI multi-job, compose validado en CI, digest pinning, perfiles lab/hardened |
| Culture & Org | 🟡 | docs extensas, AGENTS.md, pre-commit — sin organización |
| Implementation | ✅ | hexagonal con tests de arquitectura, secrets scan pre-commit+CI |
| Test & Verification | ✅ | 2377 tests, security suite, mutation, coverage 80, e2e completo |
| Information Gathering | ✅ | Loki centralizado, métricas, dashboards |

**Veredicto: nivel alto en las dimensiones técnicas** — DSOMM confirma lo
que las rondas 1-3 midieron por control individual.

## 4. Validación

### 4.1 Verificación

- Cada veredicto ✅ cita evidencia ejecutable (test, script o artefacto
  verificado live en rondas previas o en esta sesión).
- Los 🟡 se distinguen en: mejora identificada (scanner de imágenes,
  TAXII), formalización ausente por contexto académico (aceptación de
  riesgo, roles), e intermitencia documentada (techo de capacidad
  TC-04).
- Los ➖ se limitan a elementos estructuralmente fuera de alcance
  (organización, autoridad, peers, motor IDS).

### 4.2 Criterios de aceptación

- Cero veredictos ✅ sin evidencia comprobable en repo o runtime.
- Clasificación honesta igual que la matriz §3.5 de doc/12
  (implementado/parcial/simulado/no aplica).

### 4.3 Evidencias

| Evidencia | Ubicación |
| --- | --- |
| Proceso de pruebas y defectos | `docs/13`, `tests/`, `pytest.ini` |
| KPIs y monitorización | `tests/e2e/TC-KPI-*`, `kpi_alerts.py`, Grafana |
| Hardening contenedores | `docker-compose.hardened.yml`, VAL-016/017 |
| TI sharing | `export_attack_stix.py`, `export_cacao.py`, MISP client |
| Recuperación | `tests/e2e/TC-22`, `make backup/restore` |
| Investigación | artifacts `manifest/evidence/assertions` por test, correlation_id→Loki |

## 5. Problemas

### 5.1 Limitaciones

- **Sin motor IDS real** (Sigma/YARA/Suricata): la detección se inyecta
  por el simulador — coherente con el objetivo SOAR, pero limita la
  evaluación 27039/800-94 a la capa de visibilidad.
- **TAXII no implementado** por el lab (solo dentro de MISP).
- **Dimensiones organizativas** de SOC-CMM/SIM3/TMMi/RAMF sin
  contraparte real: todo 🟡/➖ por contexto, no por defecto.
- **Cadena de custodia**: artifacts inmutables pero sin firmado/hash —
  suficiente para auditoría académica, insuficiente para forense legal.

### 5.2 Riesgos

- El techo de capacidad webhook→OpenSearch (TC-04) es un hallazgo de
  rendimiento que afecta a afirmaciones de Disponibilidad/Rendimiento en
  marcos como ISO 25010 — ya documentado, no ocultar.

### 5.3 Recomendaciones

1. **TAXII** (server ligero o cliente sobre MISP) cerraría 800-150 al
   100 % — mejora pequeña, valor académico alto.
2. **Escáner CVE de imágenes** (trivy en CI) cierra el 🟡 persistente
   800-190/27002-A.8.8.
3. **Reglas Sigma mínimas** (aunque sean evaluadas por Tenzir o por el
   propio simulador) abriría la cobertura 27039.
4. **Hash/firma de artifacts** de evidencia (sha256 manifiesto) subiría
   27043 un nivel a coste casi nulo.
5. Mantener la clasificación honesta implementado/simulado/parcial —
   es lo que distingue esta evaluación de un mapeo aspiracional.

## 6. Referencias

- ISO/IEC/IEEE 29119-1..5 — Software Testing.
- TMMi Foundation — Test Maturity Model integration.
- ISO/IEC 5055 — Automated Source Code Quality Measures (CISQ).
- IEEE 1012 — V&V of Software.
- ISO/IEC 27005 — Information security risk management.
- ISO/IEC 27043 — Incident investigation principles and processes.
- ISO/IEC 27039 — IDPS selection, deployment and operations.
- NIST SP 800-94 — Guide to Intrusion Detection and Prevention Systems.
- NIST SP 800-137 — ISCM for Federal Information Systems.
- NIST SP 800-150 — Guide to Cyber Threat Information Sharing.
- NIST SP 800-190 — Application Container Security Guide.
- NIST SP 800-184 — Guide for Cybersecurity Event Recovery.
- NIST SP 800-37r2 — Risk Management Framework.
- Lockheed Martin Cyber Kill Chain; Unified Kill Chain; Diamond Model.
- SOC-CMM; SIM3 (FIRST); MaGMa; OWASP DSOMM.
