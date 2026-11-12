# Evaluación multi-marco — Contenido de dominio (Sigma, playbook Shuffle, ATT&CK, CACAO/STIX)

> Evaluación formal del contenido de dominio: `detections/sigma/` (6
> reglas), `detections/attack-catalog.yaml`, el playbook SOAR
> (`scripts/setup/shuffle_workflow/` — `workflow_definition.py`,
> `workflow_actions.py`, 18 scripts embebidos) y los exports
> interoperables (`export_cacao.py`, `export_attack_stix.py`), siguiendo
> la metodología de `docs/25`/`27`-`35`: hallazgos verificados en vivo y
> pineados con gates (`tests/architecture/test_domain_content.py`,
> **9 gates**). Revisión 2026-11-11: **1 hallazgo semántico** corregido,
> export CACAO/STIX regenerado y validado. Global **~9.5/10**.

## Marco de evaluación

| Marco | Aplicación |
|---|---|
| ISO/IEC 25010 + 25040 | Idoneidad/corrección del contenido de dominio |
| Sigma spec | Well-formedness: title/id/status/logsource/detection/level/tags |
| MITRE ATT&CK | Validez de técnicas, deprecaciones, cobertura por tags |
| MITRE D3FEND | Contramedidas por técnica en el catálogo versionado |
| OASIS CACAO 2.0 | Export interoperable del playbook |
| OASIS STIX 2.1 | Bundle de cobertura ATT&CK |
| NIST SSDF / CWE-694 | Contenido reproducible, placeholders sustituidos |

## Evidencia de runtime (post-fix)

```
CACAO export   50 steps (1 start, 38 action, 9 parallel, 1 if-condition,
               1 end) — structural validation OK
STIX bundle    141 objetos, 53 técnicas — structural validation OK
TC-31/TC-24    17/17 verdes tras el fix de tags
workflow live  0 placeholders sin sustituir (__THEHIVE_*__,
               __SERVICE_TOKEN__, __ANALYZER_URL__…)
rules          6/6 well-formed; conditions ↔ selections consistentes
```

## Hallazgo corregido

| ID | Defecto | Verificación | Fix |
|----|---------|--------------|-----|
| DOM-EVAL-001 | **Atribución ATT&CK incompleta** — `ransomware-mitre-impact.yml` dispara sobre T1486+T1490+T1491 pero solo taggeaba `attack.t1486`: la cobertura por tags (la métrica que consume TC-31) infrarrepresentaba 2 técnicas detectadas realmente | grep tags vs selection values | tags `attack.t1490`/`attack.t1491` añadidos + entradas completas (nombre + d3fend) en `attack-catalog.yaml` — TC-31 exige membresía+contramedida; gate `test_matched_techniques_are_tagged` |

## Puntos positivos (verificados)

- **Modelo de decisión multi-fuente y explicable**: `calc_decision.py` pondera Cortex taxonomies (hash+IP+DShield+pDNS+GoogleDNS+IP-API), MISP IoCs, severidad, tipo, MITRE high-risk, Tenzir, Network Watcher y patrones Loki de ransomware — y expone `factors` (auditabilidad del veredicto: por qué contain/observe).
- **Idempotencia de casos**: `dedup_or_create_case` devuelve el caso existente por `alert_id` en vez de duplicar (TC-26).
- **Guards contra el defecto de plataforma**: las branches de Shuffle 2.2.1 nunca evalúan → cada nodo downstream se auto-guarda (`containment` rechaza `decision != "contain"`; `cortex_run_guarded` salta observables vacíos — DT-01).
- **Grafo completo verificado**: rama maliciosa (containment → notify_critical ∥ update_inprogress → mttr) + benigna (mark_fp → notify_info → mttr) → métricas/ES; sin becos sin salida.
- **Catálogo versionado con contrato**: `version: 2026-11`, técnicas con nombre + D3FEND, lista `deprecated` (t1086→t1059.001, t1117→t1218.010) que TC-31 hace cumplir.
- **Interoperabilidad real**: CACAO 2.0 con ids deterministas (uuid5) y la decisión exportada como `if-condition` — más fiel que el grafo runtime (documentado honestamente); STIX 2.1 con 53 técnicas.
- **Placeholders con disciplina**: todo `__TOKEN__` en scripts embebidos tiene su `.replace()` en `workflow_actions.py` — gate nuevo que lo hace cumplir para futuros scripts.

## Puntos negativos residuales (aceptados, justificados)

| Residual | Justificación |
|---|---|
| Reglas `status: experimental`, sin `author`/`date`/`falsepositives`/`references` | Campos opcionales de la spec; el lab documenta su procedencia en el repo — añadir `author`/`date` cuando el corpus crezca |
| Sin compilación sigma-cli a un backend real | Las reglas consumen un `product: soar-lab` propio; la validación estructural + admission e2e cubre la corrección — un backend concreto exigiría un logsource real |
| Scoring heurístico (umbrales 80/50) | Modelo deliberado y explicable; calibración fina sería tuning de dominio, no defecto |
| Decisión `contain` simulada | `mode: simulated` — el lab no aisla hosts reales por diseño |
| Branches Shuffle incondicionales | Limitación de plataforma documentada y compensada con self-guards |

## STRIDE del contenido

| Amenaza | Control | Estado |
|---|---|---|
| Spoofing (alerta falsa → acción) | firma HMAC webhook + admission pipeline + scoring multi-fuente | ✅ |
| Tampering (workflow/script) | placeholders sustituidos en build, exports deterministas | ✅ |
| Repudio | factors explicables + dedup por alert_id + evidencia e2e | ✅ |
| Info disclosure | tokens sólo en env/config, nunca embebidos tras sustitución | ✅ |
| DoS semántico (regla que nunca dispara) | conditions↔selections validados por gate | ✅ |

## Regresión

- **9/9 gates** `test_domain_content.py` verdes.
- **169/169** `tests/architecture/` totales verdes.
- **17/17** e2e TC-24+TC-31 tras el fix (832s, fixture de salud).

## Nota por ámbito

| Dimensión (ISO 25010) | Antes → Después |
|---|---|
| Corrección semántica | 8.5 → **9.5** — atribución ATT&CK completa |
| Cobertura de dominio | 9.0 → **9.5** — 6 vectores + catálogo versionado + deprecated |
| Interoperabilidad | 9.0 → **9.5** — CACAO/STIX válidos y regenerables |
| Auditabilidad | 9.0 → **9.5** — factors + catálogo + exports deterministas |
| Mantenibilidad | 8.5 → **9.5** — 9 gates estáticos nuevos |
| **Global** | ~8.8 → **~9.5** |
