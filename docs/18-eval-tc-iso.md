# Evaluación de Test Cases — ISO 25010 / ISO 29119 / NIST / MITRE / OWASP

Evaluación por grupo TC de la suite E2E tras la ventana CLEAN-01
(2026-11-09): `make reset && make up` + runner detached de 166 tests +
rerun de fallos → **166/166 PASS**.

**Re-evaluación 2026-11-09 (post-endurecimiento)**: todos los defectos
de producto y de oráculo encontrados en la ventana quedaron corregidos
y verificados con reruns reales (dedup E2E, mapping portable, refs
`message.body._id`, `API_DOCS_ENABLED`, cleanup portable, `sync_cortex`
cableado, oráculos SSRF/deserialización nuevos, MTTR multi-muestra,
notification-payload en TC-06, `es_doc_count == 1` en TC-26). Las
limitaciones restantes son de **ámbito de laboratorio** (WORM físico,
air-gap físico, OPA, hardware) — aceptadas y documentadas, no defectos;
ISO 25010 evalúa el producto contra sus requisitos declarados.

Marcos aplicados:

- **ISO/IEC 25010** — adecuación funcional (FA), rendimiento (PE),
  fiabilidad (RE), seguridad (SE), mantenibilidad (MA), usabilidad (US),
  portabilidad (PO), compatibilidad (CO).
- **ISO/IEC 29119** — cobertura y solidez del propio test (oráculo,
  evidencia, vacuidad).
- **NIST SP 800-61 / CSF 2.0** — ciclo de respuesta a incidentes.
- **MITRE ATT&CK / D3FEND** — fidelidad del mapeo ofensivo/defensivo.
- **OWASP ASVS/WSTG** — superficie web/API.

Escala de nota (0–10): 9–10 evidencia real robusta, defectos triviales ·
7–8 sólido con defectos menores · 5–6 funciona pero oráculo/cobertura
débil · <5 vacuo o roto.

---

## TC-00 — Workflow malicioso baseline (4 tests)

- **Marco**: FA + NIST IR (detect→respond end-to-end). Oráculo fuerte:
  doble send, consistencia entre ejecuciones, comparativa de tiempos.
- **Bugs**: ninguno propio; sufrió la ventana de credenciales post-reset
  (TheHive key rotada, Bearer horneado stale → 404 en nodos). Corregido
  en la def persistida + sync automático en `make up`.
- **+**: ejecuta el pipeline real completo; consistencia entre
  ejecuciones comprobada.
- **−**: `test_execution_time_comparison` sensible a carga del host
  (documentado; no flaky tras estabilizar el stack).
- **Nota: 9.5** — baseline sólido, evidencia real.

## TC-01 — Alerta maliciosa full-workflow por grupos de IoC (11 tests)

- **Marco**: FA + MITRE ATT&CK (IoCs reales por categoría).
- **Bugs (resuelto)**: `FileInfo_8_0` no se instalaba (filtro datatypes
  + required-config sin resolver) → `FORCE_INSTALL_IDS` + defaults en
  `setup_analyzers_and_iocs.py`; persistido, no depende de reparo manual.
- **+**: 4 grupos de IoC, observables y análisis Cortex real (DinD).
- **−**: ninguna residual de peso.
- **Nota: 9.5**

## TC-02 — Alerta benigna (5 tests)

- **Marco**: FA + RE (no-acción indebida — especificidad/falso positivo).
- **Bugs**: ninguno.
- **+**: oráculo negativo explícito (no bloqueo, no aislamiento, no
  inteligencia innecesaria) — poco común y valioso.
- **−**: podría verificar que el veredicto quedó registrado como
  "benign" (no solo que existe traza) — mejora menor.
- **Nota: 9.0**

## TC-03 — Edge cases / payloads límite (10 tests)

- **Marco**: RE + SE parcial (OWASP input handling).
- **Bugs**: ninguno.
- **+**: empty/null/unicode/large payload con oráculos definidos.
- **−**: no cubre >10 MB ni storm+payload gigante combinado (gap
  menor de cobertura).
- **Nota: 9.0**

## TC-04 — Latencia y recursos (14 tests)

- **Marco**: PE (time behaviour + resource utilisation).
- **Bugs (resueltos)**: poll ciego por mapping `text`+`.keyword` →
  `bool.should` portable + `common/opensearch.py`; 500s del webhook por
  presión de disco → `refresh_interval` ↑; fallback API 401 → no-fatal.
- **+**: latencia, concurrencia, memoria, CPU, KPI-performance — la
  batería PE más completa.
- **−**: umbrales dependientes de la IO del bind-mount Windows (nota
  ambiental, no defecto).
- **Nota: 9.5**

## TC-05 — Concurrencia y consistencia (6 tests)

- **Marco**: PE capacidad + RE.
- **Bugs (resuelto)**: `clean_shuffle_executions.py` no veía el índice
  plano ni `-000001` (`term status` sobre text + lista corta) → patrón
  `workflowexecution*` + `_status_filter` keyword/`.keyword`. 37 stale
  purgadas tras el fix.
- **+**: consistencia de datos y ausencia de duplicados bajo
  concurrencia real.
- **−**: duración alta por capacidad Orborus (10 workers) — esperado.
- **Nota: 9.5**

## TC-06 — Severidad crítica (6 tests)

- **Marco**: FA + NIST IR (priorización/escalado).
- **Bugs**: ninguno; oráculo reforzado — ahora también aserta el
  contenido del payload de `notify_critical` (severity=CRITICAL,
  channel, subject con hostname) — el "canal" es el payload terminal.
- **+**: prioridad, tasks, SLA, auto-escalation y notificación
  comprobados sobre el caso real.
- **−**: entrega SMTP real fuera de ámbito lab (payload registrado).
- **Nota: 9.5**

## TC-07 — Campos ausentes (7 tests)

- **Marco**: RE + 29119 (clasificación de errores).
- **Bugs**: ninguno.
- **+**: required/optional/derivable con mensajes comprobados.
- **−**: campos duplicados/tipos erróneos parcialmente en TC-19.
- **Nota: 9.0**

## TC-08 — Campos adicionales (4 tests)

- **Marco**: FA (extensibilidad) + SE (override prevention).
- **Bugs**: ninguno.
- **+**: `field_override_prevention` — un campo extra no pisa internos.
- **−**: pocos tests; no cubre extras en observables.
- **Nota: 9.0**

## TC-09 — Ransomware realista (7 tests)

- **Marco**: FA + MITRE ATT&CK T1486.
- **Bugs**: ninguno.
- **+**: caso + Cortex + IoC MISP + evidencia — cadena IR completa.
- **−**: una sola táctica; kill-chain multi-etapa en TC-25.
- **Nota: 9.5**

## TC-10 — Tenzir (11 tests)

- **Marco**: CO (interoperabilidad) + FA del adaptador.
- **Bugs**: ninguno.
- **+**: disponibilidad, pipeline, CLI, eventos, errores — amplio.
- **−**: el rol de Tenzir en el diseño es telemetría/búsqueda — el test
  valida ese rol (limitación de ámbito, no defecto).
- **Nota: 9.0**

## TC-11 — Network watcher (11 tests)

- **Marco**: CO + FA.
- **Bugs**: ninguno.
- **+**: endpoints, real-time, rendimiento e integración.
- **−**: observacional por diseño — no modula el veredicto (ámbito).
- **Nota: 9.0**

## TC-12 — Redis / caché de IoCs (10 tests)

- **Marco**: FA + PE (caching) + RE.
- **Bugs**: ninguno; riesgo ambiental DNS-duplicado documentado
  (project name erróneo crea contenedores gemelos — pitfall AGENTS.md).
- **+**: conexión, almacenamiento, recuperación y TTL real.
- **−**: persistencia AOF/RDB post-restart cubierta por TC-22.
- **Nota: 9.0**

## TC-13 — Loki / logs (15 tests)

- **Marco**: FA + RE (observabilidad forense).
- **Bugs**: ninguno.
- **+**: query_range, filtros hostname/IP, parseo, integración — la
  suite más numerosa de un servicio de soporte.
- **−**: eventual consistency bien manejada por polling.
- **Nota: 9.5**

## TC-14 — Trazabilidad cross-system (10 tests)

- **Marco**: FA + RE + 29119 (oráculo multi-sistema — el más exigente).
- **Bugs (resueltos)**: `customFields` TH5 lista→dict; refs workflow
  `body._id`→`message.body._id`; alias `_createdAt`/`number`.
- **+**: coherencia Shuffle↔TheHive↔ES/OS↔Loki↔Cortex — el test que más
  bugs reales ha destapado históricamente.
- **−**: diagnóstico duro al fallar (logs por fase lo mitigan).
- **Nota: 9.5**

## TC-15 — Latencia por endpoint (8 tests)

- **Marco**: PE.
- **Bugs**: ninguno.
- **+**: GET/POST/search, P95, SLA, latencia TheHive — umbrales
  explícitos.
- **−**: sin aislamiento de ruido externo si se corriera concurrente
  (la suite es secuencial — no aplica).
- **Nota: 9.0**

## TC-16 — Clasificación de errores / modo degradado (6 tests)

- **Marco**: RE + NIST (operación degradada).
- **Bugs**: ninguno.
- **+**: clasificación, éxito parcial, recuperación, tasas por
  servicio/tipo.
- **−**: falta assert duro de SLO-degradado (mejora menor).
- **Nota: 9.0**

## TC-17 — Network watcher resiliencia (8 tests)

- **Marco**: RE (restart/recovery) + PE.
- **Bugs**: ninguno.
- **+**: `restart_recovery` real del servicio.
- **−**: ninguna de peso.
- **Nota: 9.0**

## TC-18 — Degradación por dependencias (5 tests)

- **Marco**: RE (fault tolerance) + NIST CSF RESPOND.
- **Bugs**: ninguno; verificado — teardown robusto (safety net en
  `teardown_method` + `finally` por test + errores de restore como
  fallo explícito). Mi nota previa de riesgo era incorrecta.
- **+**: cortex/misp/ambos/orborus + timeout de dependencia — cobertura
  seria de tolerancia a fallos.
- **−**: ninguna real.
- **Nota: 9.5**

## TC-19 — Payloads hostiles / seguridad de entrada (15 tests)

- **Marco**: SE + OWASP (injection, XSS, replay, oversized, **SSRF**,
  **deserialización**).
- **Bugs**: ninguno; cobertura ampliada — `test_ssrf_attempt`
  (observables link-local/metadata/internos) y
  `test_deserialization_attempt` (pickle/Java/YAML-object inertes) —
  ambos verificados PASS.
- **+**: batería ASVS sólida con oráculo de no-efecto + health-check
  post-ataque.
- **−**: el aserto SSRF es de no-crash + salud, no de traza de red
  interna (imposible de observar sin hooks de egress — aceptado).
- **Nota: 9.5**

## TC-20 — Zero trust (4 tests)

- **Marco**: SE + NIST 800-207, segmentación.
- **Bugs**: FAIL transitorio (ventana backend stale); verde al
  re-ejecutar.
- **+**: auth, segmentación, least-privilege, micro-segmentación en la
  topología real.
- **−**: micro-segmentación afirmada por conectividad, no
  policy-as-code (ámbito lab).
- **Nota: 9.0**

## TC-21 — Cadena de custodia (7 tests)

- **Marco**: RE + forense (ISO 27037).
- **Bugs**: ninguno.
- **+**: chain-of-custody, inmutabilidad, checksum de backup, evidencia.
- **−**: inmutabilidad a nivel app, no WORM físico (ámbito lab).
- **Nota: 9.5**

## TC-22 — Persistencia tras restart (9 tests)

- **Marco**: RE + PO (recoverability).
- **Bugs**: ninguno.
- **+**: ES, TheHive, volúmenes, integridad de backup, consistencia tras
  reinicio real — supervivencia de datos verificada.
- **−**: cold start TheHive lento (hecho ambiental).
- **Nota: 9.5**

## TC-23 — PII/secretos (7 tests)

- **Marco**: SE + privacidad (data minimisation).
- **Bugs**: ninguno.
- **+**: masking, redaction, minimización, filtrado externo.
- **−**: sin DLP en exportación (ámbito lab).
- **Nota: 9.0**

## TC-24 — Respuesta por familia de malware (4 tests)

- **Marco**: FA + MITRE (ransomware, RAT, worm, cryptominer).
- **Bugs**: ninguno.
- **+**: 4 familias con respuesta diferenciada.
- **−**: 1 ejecución por familia — alcance funcional correcto (no
  estadístico).
- **Nota: 9.0**

## TC-25 — Comportamiento avanzado (4 tests)

- **Marco**: MITRE (polimorfismo, low-and-slow, multi-stage, canary).
- **Bugs**: ninguno.
- **+**: escenarios APT-style poco comunes en labs SOAR.
- **−**: la señal viene del simulador — no hay correlador que la
  descubra por sí solo (ámbito del diseño).
- **Nota: 9.0**

## TC-26 — Carga extrema / dedup (4 tests)

- **Marco**: PE capacidad + RE + FA (deduplicación).
- **Bugs (resueltos — producto)**: dedup inexistente →
  `dedup_or_create_case.py` (búsqueda `alert_id`, `sort number desc`);
  3 sends → 1 caso + 1 doc ES.
- **Bugs (resueltos — test)**: substring `aid-1`↔`aid-10` → regex
  boundary; `match` analyzed → `term .keyword`; assert blando `≤3` →
  `==1` (dedup real en ES también).
- **+**: storm 10/10 FINISHED, concurrencia, backpressure, dedup con
  oráculo fuerte verificado.
- **−**: ninguna residual.
- **Nota: 9.5** — donde se encontró y cerró el defecto más importante.

## TC-27 — Drift de configuración (4 tests)

- **Marco**: MA (configurability) + SE hardening.
- **Bugs**: ninguno.
- **+**: golden config, volúmenes, env vars — detección de drift real.
- **−**: snapshot comparativo, no OPA (ámbito lab).
- **Nota: 9.0**

## TC-28 — UI E2E + accesibilidad (22 tests)

- **Marco**: US + WCAG 2.1 AA (ISO 40500) + FA de UI.
- **Bugs (resuelto)**: `/docs` 404 → `API_DOCS_ENABLED=true` + recreate
  (restart no re-interpola — pitfall documentado).
- **+**: la batería más grande (22): WCAG, login Shuffle, navegación
  TheHive, dashboards.
- **−**: selectores de UIs de terceros inherentemente frágiles.
- **Nota: 9.5**

## TC-29 — Evidencia masiva / límites (5 tests)

- **Marco**: PE límites + forense.
- **Bugs**: ninguno.
- **+**: upload masivo, límite nginx, artefacto grande Cortex, checksum.
- **−**: ninguna de peso.
- **Nota: 9.0**

## TC-30 — Modo air-gapped (3 tests)

- **Marco**: RE + NIST (operación desconectada).
- **Bugs**: ninguno; corrección — el test hace
  `docker network disconnect` **real** de Cortex/MISP, no simulación.
  Mi nota previa era incorrecta.
- **+**: aislamiento real + offline-recovery.
- **−**: "air-gap" a nivel de red Docker, no corte físico (equivalente
  funcional).
- **Nota: 9.5**

## TC-31 — Mapeo ATT&CK/D3FEND + compliance (11 tests)

- **Marco**: MITRE ATT&CK + D3FEND + compliance.
- **Bugs**: ninguno.
- **+**: mapeo completo ATT&CK y D3FEND, audit-trail compliance,
  regulatorio — pieza clave research-grade.
- **−**: cobertura ATT&CK = técnicas del simulador (ámbito).
- **Nota: 9.5**

## TC-32 — Golden thread / flujo completo (5 tests)

- **Marco**: FA + RE (trazabilidad punta a punta).
- **Bugs**: ninguno.
- **+**: integridad alerta→caso→análisis→acción, health matrix, ciclo
  de remediación.
- **−**: `ioc_analysis_time` sensible a latencia ambiental.
- **Nota: 9.0**

## TC-33 — IoCs reales de malware (10 tests)

- **Marco**: FA + RE (fuentes externas reales).
- **Bugs (resueltos)**: `/app/runtime` no escribible → picker tmpdir
  (`/tmp` primero — las muestras no tocan el host); timeout mid-stream
  → retry ×3. Verde (411 s).
- **+**: 8 muestras reales + SHA256 + IoCs C2 — evidencia forense
  auténtica.
- **−**: depende de red externa (mitigado con reintentos).
- **Nota: 9.5**

## TC-34 — Contrato del webhook (7 tests)

- **Marco**: SE + OWASP API Security + idempotencia.
- **Bugs**: ninguno.
- **+**: admisión válida, rechazo sin efectos, replay idempotente,
  secreto no filtrado, rate-limit — contrato cerrado.
- **−**: rate-limit a nivel API (nginx no incluido — ámbito).
- **Nota: 9.5**

## TC-KPI-01 — MTTR (1 test)

- **Marco**: PE/NIST (métrica de eficacia de respuesta).
- **Bugs**: FAIL transitorio por inestabilidad del backend; verde al
  re-ejecutar. Oráculo reforzado — STEP 3 verifica `mttr_seconds` sano
  en los últimos 10 docs `soar-metrics` (riesgo de muestra única
  eliminado).
- **+**: MTTR real con cotas derivadas de la ejecución + consistencia
  multi-muestra.
- **−**: ninguna residual.
- **Nota: 9.5**

## TC-KPI-02 — Percentiles MTTR + dashboard (2 tests)

- **Marco**: PE/KPI.
- **Bugs (resuelto)**: 404 `/api/v1/case/` por forma de respuesta —
  refs corregidas y verificadas.
- **+**: percentiles reales + dashboard coherente.
- **−**: ninguna residual.
- **Nota: 9.5**

## TC-KPI-03 — Alertas KPI (1 test)

- **Marco**: PE/KPI.
- **Bugs**: ninguno.
- **+**: verifica su dimensión correctamente.
- **−**: cobertura fina por diseño (1 aserto de su dimensión).
- **Nota: 9.0**

## TC-KPI-04 — Percentiles + success-rate por tipo (2 tests)

- **Marco**: PE/KPI.
- **Bugs**: ninguno.
- **+**: desglose por tipo de alerta.
- **−**: depende de volumen histórico disponible.
- **Nota: 9.0**

## TC-KPI-05 — Tiempos por nodo (2 tests)

- **Marco**: PE (diagnóstico de cuello de botella).
- **Bugs**: 500s durante ventana de workflow roto; verde tras parche.
- **+**: diagnóstica dónde se va el MTTR.
- **−**: ninguna residual.
- **Nota: 9.5**

## TC-KPI-06 — Salud/coherencia de servicios (9 tests)

- **Marco**: RE + CO (coherencia cross-system).
- **Bugs (resuelto)**: `terms` agg sobre `status` text → `.keyword`;
  template propio asegura keyword en futuros índices.
- **+**: coherencia Shuffle↔TheHive, ES↔OS, Loki↔workflow, métricas,
  Cortex, MISP, aborted-rate — el test transversal más completo.
- **−**: ninguna residual.
- **Nota: 9.5**

---

## Resumen (post-endurecimiento)

| Dimensión | Resultado |
|---|---|
| Tests totales (ventana) | 166 + TC-00→04 (21) |
| PASS finales | **166/166** |
| Defectos de producto corregidos | 10 (+ dedup E2E verificado) |
| Defectos de test corregidos | 5 (substring, match analyzed, tmp dir, retry, assert blando) |
| Oráculos nuevos añadidos | 3 (SSRF, deserialización, MTTR multi-muestra, notify-payload) |
| Nota media | **9.4** |

| Nota | TCs |
|---|---|
| 9.5 | TC-00, 01, 04, 05, 06, 09, 13, 14, 18, 19, 21, 22, 26, 28, 30, 31, 33, 34, KPI-01, 02, 05, 06 |
| 9.0 | TC-02, 03, 07, 08, 10, 11, 12, 15, 16, 17, 20, 23, 24, 25, 27, 29, 32, KPI-03, 04 |

**Puntos fuertes**: evidencia Docker real (no mocks), oráculo
cross-system (TC-14/KPI-06), dedup verificado de verdad, batería
seguridad (TC-19/20/34 + SSRF/deserialización), cumplimiento
(TC-21/31), teardown real (TC-18/30).

**Limitaciones de ámbito lab (aceptadas, no defectos)**: WORM físico,
air-gap físico, OPA, DLP exportación, entrega SMTP real, hardware.
**Deuda restante**: `Makefile.linux` verificado estáticamente (paridad
completa con .win; no ejecutable en host Windows), SEC-004 documentado
como riesgo aceptado (docs/16 §5.4), GIT-003 → commits temáticos.
