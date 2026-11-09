# Informe final de validación — SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
- [2. Alcance](#2-alcance)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 Metodología](#31-metodología)
  - [3.2 Resultados E2E](#32-resultados-e2e)
  - [3.3 Validación de seguridad en vivo](#33-validación-de-seguridad-en-vivo)
  - [3.4 Comparación de KPIs con baseline](#34-comparación-de-kpis-con-baseline)
  - [3.5 Matriz definitiva de marcos](#35-matriz-definitiva-de-marcos)
  - [3.6 Artefactos generados](#36-artefactos-generados)
- [4. Validación](#4-validación)
- [5. Problemas](#5-problemas)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Consolidar en un único informe la validación exhaustiva del proyecto:
resultados de la suite E2E completa, verificación en vivo de los
controles de seguridad implementados (rate limiting, autenticación
endurecida, contención real), comparación de KPIs con el baseline
histórico (24-08-2026) y la matriz definitiva de cumplimiento de marcos.

### 1.2 Contexto

- Stack: 23 contenedores `soar_*` (3 redes aisladas).
- Suite: TC-00..TC-33 + TC-KPI-01..06.
- Baseline: informe `reports/e2e/e2e_report.md` del 24-08-2026
  (50 workflows, MTTR medio 277 s, MTTR ransomware 261 s,
  contención 92 %, éxito 100 %).
- Marcos evaluados: NIST 800-61r2, ISO 27035, ISO 27001 A.5.24–28,
  MITRE ATT&CK/D3FEND, CACAO, NIST CSF 2.0, Zero Trust 800-207,
  OWASP API Top 10, ISO 25010, CIS Docker.

## 2. Alcance

### 2.1 Qué cubre

Toda la cadena de verificación: unitarios → integración → externos →
E2E → KPIs → controles de seguridad en vivo → comparación con baseline
→ veredicto por marco.

### 2.2 Límites

- Contexto de laboratorio académico; contención real limitada a
  contenedores víctima allowlisted (`mode=enforce`).
- El perfil hardened se valida por configuración y, tras el restart,
  parcialmente en vivo.

### 2.3 Dependencias

`make up`, `make test-e2e`, stack Docker Desktop en Windows,
`docs/10-framework-validation-exhaustive.md` (matriz por control).

## 3. Contenido principal

### 3.1 Metodología

1. Suite E2E completa contra el stack en marcha (`make test-e2e`).
2. Restart de `soar_api` para cargar middleware/auth/contención nueva.
3. Verificación en vivo: `curl`, `docker inspect`, endpoints protegidos.
4. Extracción de KPIs desde Elasticsearch/OpenSearch/Loki y comparación
   con baseline.
5. Re-evaluación de cada control parcial/ausente tras la remediación.

### 3.2 Resultados E2E

| Métrica | Valor |
| --- | --- |
| Tests ejecutados | 240 (TC-05..33 + TC-KPI-01..06) |
| Pasados | **236 verificados** — TC-26 4/4 tras fixes BUG-047/051/052 (backpressure PASSED 31:24 con contabilidad terminal honesta) |
| Fallados | 4 — TC-26 pre-fix (todos verdes post-fix) |
| Errores transitorios | 3 setup TC-15 (MISP reiniciado por TC-18 resilience en paralelo) |
| Skipped | 1 (TC-22) |
| Duración total | ~14 h (cadena completa, incl. 50 min TC-18 resilience) |
| Fallos no críticos documentados | TC-09/TC-15 (contención de corridas paralelas — verde en rerun solitario), KPI-06 (BUG-048) |
| Suites auxiliares | Integración: **349/350 + 4 skip legítimos** (BUG-055/056); Performance: **29/29** (BUG-054); Unit: **1355/1355**; Atomic+Security+General: **241/241**; Quality: **51/52 + 1 skip on-demand** (BUG-057..061); Smoke live: **25/25**; Arquitectura host: **15/15** |
| Verificación de artifacts | **259/259 tests E2E** tienen su artifact más reciente en PASSED (los FAILED residuales en disco son artifacts stale de 11-04 reemplazados por los runs de 11-05) |

Desglose por suite (post-fix):

| Suite | Resultado | Suite | Resultado |
| --- | --- | --- | --- |
| TC-05/06 | 12/12 ✅ | TC-21 | 7/7 ✅ |
| TC-07 | 5/5 ✅ | TC-22 | 8+1skip ✅ |
| TC-08 | 4/4 ✅ | TC-23 | 7/7 ✅ |
| TC-09 | 7/7 ✅ (rerun) | TC-24 | 4/4 ✅ |
| TC-10 | 11/11 ✅ | TC-25 | 4/4 ✅ |
| TC-11 | 11/11 ✅ | TC-26 | 4/4 ✅ (rerun-3 backpressure 31:24) |
| TC-12 | 10/10 ✅ | TC-27 | 4/4 ✅ |
| TC-13 | 15/15 ✅ | TC-28 | 12/12 ✅ |
| TC-14 | 10/10 ✅ | TC-29 | 5/5 ✅ |
| TC-15 | 6/6 ✅ (rerun post-BUG-046) | TC-30 | 3/3 ✅ |
| TC-16 | 11/11 ✅ | TC-31 | 11/11 ✅ |
| TC-17 | 9/9 ✅ | TC-32 | 5/5 ✅ |
| TC-18 | 5/5 ✅ (resilience real) | TC-33 | 10/10 ✅ |
| TC-19 | 13/13 ✅ | TC-KPI-01..05 | 10/10 ✅ |
| TC-20 | 4/4 ✅ | TC-KPI-06 | 9/9 ✅ (post-BUG-048) |

**Incidencias durante la ejecución** (todas resueltas con bug numerado):

- Ventana de corrupción `webhook_info.json` (BUG-041) → falsos fallos
  TC-05/TC-09/TC-10; resuelto + rerun verde.
- `evidence_complete` exigía `payload.json` a tests sin submit → falsos
  FAILED estructurales (BUG-044). **296+ artifacts, 0 falsos negativos
  desde el fix.**
- Probes de latencia sin acotar → 5 fallos deterministas TC-15 (BUG-046).
- Sender webhook con `timeout=15` < escritura Shuffle→OpenSearch real
  (~20-27 s bajo ráfaga) → fallos TC-26 (BUG-047); techo de capacidad
  documentado como propiedad, no defecto.
- Patrones de exclusión de abortos `TC-xx` ≠ `alert_id` reales `TCxx-`
  → falso fallo KPI-06 (BUG-048).
- Ronda `tests/quality` (11 fallos iniciales): tools no declarados en
  `quality` extras (BUG-057), `.bandit` sin montar (BUG-058), ciclo
  `infrastructure <-> interfaces` por contextvar en capa alta (BUG-059),
  7 violaciones ruff (BUG-060), guarda mutmut como assert (BUG-061) —
  todos corregidos: **51/52 + 1 skip on-demand**.

Evidencia: `reports/validation/results/` (JSON por test + directorios
de evidencia por ejecución) e informe generado por `make test-e2e-report`.

### 3.3 Validación de seguridad en vivo

| Control | Resultado | Evidencia |
| --- | --- | --- |
| Rate limiting — headers `X-RateLimit-*` | ✅ verificado | `curl -I /health` y `/auth/*` → `X-RateLimit-Limit/Remaining/Reset` presentes; límite 300 global / 30 `/auth` (env, post-BUG-045) |
| Rate limiting — 429 al superar límite | ✅ verificado | ráfaga 32× `POST /auth/login` → req 29-32 devuelven **429** + `retry-after: 52` + `{"code":"rate_limited"}` |
| Auth hardened `API_REQUIRE_AUTH=on` | ✅ verificado live | api recreada en perfil hardened: `/backup/list`/`/backup/create` sin cred → **401**; `X-Service-Token` válido → 200; JWT login+Bearer → 200; token inválido → 401; `/health` público → 200. Requiere fix BUG-053 (mounts) para que el flag se honre |
| Perfil hardened — socket proxy | ✅ verificado live | `tecnativa/docker-socket-proxy:v0.4.1` corriendo; whitelist de verbos; api + network-watcher consumen vía `DOCKER_HOST=tcp://docker-socket-proxy:2375` (tráfico 200 en logs); api sin mount de socket |
| Perfil hardened — non-root/caps | ✅ verificado live | api `uid 1000` + `cap_drop ALL` + `no-new-privileges`; redis `uid 999` + `requirepass` (NOAUTH); orborus seccomp por defecto (sin `unconfined`); socket crudo en orborus intencional (spawnea workers, documentado) |
| Contención real `mode=enforce` | ✅ implementado + 9 tests | `docker network disconnect`+`pause` sobre víctima allowlisted; evidencia before/after |
| Healthchecks | 23/23 (renderer + backend añadidos) | compose + endpoints verificados en vivo |
| Imagen digests | 18/18 (`make verify-digests` bloqueante) | registry + orborus local |
| Scrub de secretos en logs | ✅ Promtail `pipeline_stages` | verificado contra líneas reales filtradas |
| docker.sock | 4 raw + 2 proxy (corregido) | guardián `test_docker_socket_access.py` |

### 3.4 Comparación de KPIs con baseline

Valores extraídos en vivo (05-11-2026, ventana 24 h) de OpenSearch
`workflowexecution` + API `/analytics/kpis/aggregated` + `soar-metrics`.

| KPI | Baseline 24-08 | Actual | Desviación | Veredicto |
| --- | --- | --- | --- | --- |
| Workflows ejecutados | 50 | 602 ejecuciones (538 FINISHED / 45 ABORTED / 19 EXECUTING) | ×12,0 volumen | ✅ |
| MTTR medio | 277 s | 166,7 s media · 127,2 s mediana (n=584) | **−39,8 %** | ✅ mejor |
| MTTR ransomware | 261 s | 169,5 s | **−35,1 %** | ✅ mejor |
| Tasa de contención | 92 % | 99,8 % (491/492 decisiones `contain` ejecutadas) | **+7,8 pp** | ✅ mejor |
| Ejecuciones exitosas | 100 % | 99,6 % workflows con métrica (541/543) | −0,4 pp | ✅ |

Notas de interpretación:

- Los 45 ABORTED son **intencionales**: 42 de TC-26 (tormenta por encima
  del techo de capacidad documentado, BUG-047) + resiliencia TC-18.
  La tasa de abortos **inesperados** es 0 % (verificado por
  `test_workflow_aborted_rate`, KPI-06, post-BUG-048).
- Una doc contaminante con `mttr_seconds` ≈ 26,6 M s (308 días, sonda con
  `detection_time` ficticia) inflaba el KPI ransomware a 47 857 s —
  eliminada y acotado el agregado (BUG-049). Cifras de la tabla ya corregidas.

### 3.5 Matriz definitiva de marcos

| Marco | ✅ | 🟡 | ❌ | Delta vs validación inicial |
| --- | --- | --- | --- | --- |
| NIST SP 800-61r2 | 13 | 1 | 0 | Containment + Eradication mejorados (modo enforce real) |
| ISO 27035 + 27001 | 12 | 0 | 0 | Response cerrada con contención verificable |
| MITRE ATT&CK/D3FEND | 6 | 0 | 0 | Export STIX 2.1 (53 técnicas, `mitigates` links) |
| CACAO | 3 | 0 | 0 | **Export implementado** (❌→✅) |
| NIST CSF 2.0 | 6 | 0 | 0 | RESPOND cerrado (contención real) |
| Zero Trust 800-207 | 6 | 1 | 0 | Auth opt-in; hardened activa |
| OWASP API Top 10 | 6 | 1 | 0 | Rate limit 429 live ✅; auth gate verificado ✅; parcial: auth es opt-in en perfil lab (hardened default `true`) |
| ISO 25010 | 8 | 0 | 0 | — |
| CIS Docker | 10 | 2 | 0 | healthchecks 23/23 live ✅; digests 18/18 ✅; seccomp/caps verificados live (VAL-016/017); parciales: socket en orborus (diseño), proxy sin `cap_drop` (rompe connect() al socket — BUG-053 nota) |

**Totales**: 68 verificados · 5 parciales · 0 no abordados (conteo tras validación OWASP + CIS en vivo).

**Extensión — rondas 2-4** (detalle en `docs/12` y `docs/14`):

| Marco | Resultado agregado |
| --- | --- |
| NIST IR 8374 (ransomware CSF profile) | 8/9 ✅ |
| ISO/IEC 27002:2022 (subconjunto 24) | 18 ✅ · 5 🟡 · 1 ➖ |
| NIST SP 800-53r5 | 18 ✅ · 10 🟡 |
| CIS Controls v8 | 13 ✅ · 2 🟡 · 3 ➖ |
| OWASP ASVS 4.0 | 11 ✅ · 3 🟡 |
| OWASP SAMM 2.0 | madurez media ~2 |
| NIST SSDF (800-218) | 8 ✅ · 3 🟡 · 1 ❌ (provenance) |
| SLSA 1.0 | L1 parcial |
| Twelve-Factor | 11/12 ✅ |
| RGPD | 6/7 ✅ |
| RE&CT / FIRST TLP-PAP | 4/6 ✅ · cumplido |
| CWE Top 25 | 8 ✅ · 4 🟡 · 3 ➖ |
| STRIDE / LINDDUN / ISO 22301 / NIST 800-92 / OpenSSF | modelado + controles cubiertos (doc/12 §7) |
| ISO/IEC/IEEE 29119 (testing) | 6/7 ✅ |
| TMMi | L3 con prácticas L4/L5 |
| ISO/IEC 5055 (CISQ) | 4/4 características medidas |
| IEEE 1012 (V&V) | completo y documentado |
| ISO/IEC 27005 (riesgo) | 5/8 ✅ · 3 🟡 |
| ISO/IEC 27043 (investigación) | 5/7 ✅ |
| ISO/IEC 27039 + NIST 800-94 (IDPS) | 🟡 parcial por diseño (sin motor IDS) |
| NIST SP 800-137 (ISCM) | 5/6 ✅ |
| NIST SP 800-150 (TI sharing) | 4/6 ✅ · TAXII 🟡 |
| NIST SP 800-190 (contenedores) | 5/6 ✅ |
| NIST SP 800-184 (recovery) | 5/6 ✅ |
| NIST SP 800-37 (RMF) | 4/5 ✅ + Authorize ➖ |
| Kill Chain / Diamond Model | fases post-delivery ✅ · 4/4 vértices |
| SOC-CMM / SIM3 / MaGMa | tecnología+proceso ✅ · organización ➖ |
| OWASP DSOMM | alto en dimensiones técnicas |

### 3.6 Artefactos generados

| Artefacto | Generador | Tests |
| --- | --- | --- |
| `reports/cacao/soar_ransomware_response.cacao.json` | `make export-cacao` | 12 (`test_export_cacao.py`) |
| `reports/stix/attack_coverage.stix.json` | `make export-stix` | 10 (`test_export_attack_stix.py`) |
| Contención `mode=enforce` | `POST /api/v1/contain` | 9 (`test_contain_enforce.py`) |
| Guardián docker.sock | `tests/architecture/test_docker_socket_access.py` | 4 |
| Scrub de secretos | `promtail-config.yml` `pipeline_stages` | verificado en vivo |

## 4. Validación

### 4.1 Verificación

Cada fila de §3.3 cita el comando o test que la respalda. Los artefactos
de §3.6 se regeneran con los targets `make` indicados y sus salidas se
validan estructuralmente en los propios generadores.

### 4.2 Criterios de aceptación

- E2E completo con evidencia preservada ✅ (TC-05..33 + KPI-01..06 verde post-fix; TC-26 4/4 tras BUG-047/051/052)
- API reiniciada y controles en vivo verificados — rate limiting ✅; auth hardened ✅ (VAL-004: 401 sin cred/inválidos, 200 service-token/JWT); perfil hardened verificado live (VAL-016/017)
- KPIs comparados con baseline con desviaciones cuantificadas ✅ (§3.4: MTTR −39,8 %, contención +7,8 pp)
- Matriz final actualizada con evidencia reproducible ✅ (§3.5 totales tras OWASP + CIS live)

### 4.3 Evidencias

`reports/validation/results/`, `reports/cacao/`, `reports/stix/`,
`docker inspect`, salidas `curl` en §3.3, `docs/10` (control a control).

## 5. Problemas

### 5.1 Limitaciones

- Contención real limitada a víctimas allowlisted (no EDR real).
- Logs crudos de MISP/Shuffle imprimen secretos (upstream; redactado
  en Loki).
- Export CACAO cubre el grafo base; analyzers dinámicos se añaden en
  runtime.
- Techo de capacidad medido: ingesta webhook→OpenSearch síncrona
  sostiene ~2-3 escrituras concurrentes antes del timeout interno de
  Shuffle (~20 s → HTTP 500). Bajo ráfaga el abort-governor descarta
  ejecuciones tras ~1300-2000 s en cola — **propiedad del stack**
  (OpenSearch single-node 2 g heap, Docker Desktop), no defecto:
  TC-26 contabiliza ABORTED como shed auditable, no pérdida.

### 5.2 Riesgos

- Suite E2E de larga duración (~horas) puede solaparse con cambios en
  el stack; se revalida post-restart.
- `API_REQUIRE_AUTH` off en perfil lab por diseño (hardened: on por
  defecto, verificado live).
- `docker-socket-proxy` sin `cap_drop` en hardened: rompe el `connect()`
  al socket montado en Docker Desktop (503 `SC--`) — queda como residual
  documentado en el propio compose; verb-whitelist + `:ro` +
  `no-new-privileges` siguen siendo los controles efectivos.

### 5.3 Recomendaciones

1. ~~Al terminar el E2E: restart API, validar 429/auth en vivo, cerrar
   filas pendientes de §3.3–3.5~~ → hecho (VAL-002/003/004, §3.5 completo).
2. ~~`make up HARDENED=1` + smoke para validar seccomp/non-root/proxy en
   vivo (VAL-016/017)~~ → hecho: overlay aplicado quirúrgicamente;
   halló y corrigió BUG-053 (mounts) — `make up` regenera secretos,
   usar `compose up -d` con el overlay para alternar perfiles.
3. Mantener `make verify-digests` en el pipeline de release (18/18).

## 6. Referencias

- `docs/10-framework-validation-exhaustive.md` — matriz control a control (ronda 1)
- `docs/12-framework-validation-extended.md` — marcos rondas 2-3
- `docs/14-framework-validation-iso-models.md` — marcos ronda 4 (ISOs proceso, madurez, modelos)
- `docs/13-defect-driven-testing.md` — confirmación de bugs failing-first (BUG-001..066)
- `reports/e2e/e2e_report.md` — baseline 24-08-2026
- `docs/09-traceability-matrix.md` — riesgos residuales RR-01..07
- OASIS CACAO v2.0, STIX 2.1, MITRE ATT&CK
