# Evaluación Simulador de Alertas — MITRE ATT&CK · Atomic Red Team

> **Fecha**: 2026-11-12 · Re-evaluación bajo fidelidad ATT&CK/ART (complementa `docs/42`, ISO 25010 y `docs/50`, victim host-level). **Resultado**: 1 defecto de fidelidad corregido + 2 gates. Score ~9.5/10.

## Defecto corregido

| ID | Defecto | Fix | Evidencia |
|----|---------|-----|-----------|
| SIM-EVAL-2-001 | **Incoherencia técnica↔táctica en 4 familias** — emitían técnicas ATT&CK cuyas tácticas canónicas no estaban declaradas: Akira (T1021.004→LM, T1068→PrivEsc, T1572→C2 no declaradas), LockBit Black (T1563→LM), ALPHV Linux (T1078→sin táctica compatible), RansomHub (T1068→PrivEsc, T1219→C2). Las alertas etiquetaban mal el kill-chain | Listas `tactics` completadas al mapeo canónico ATT&CK v14 | Gate `test_technique_tactic_coherence` — 25 bloques (22 familias + 3 stages TC-09) verificados técnica a técnica |

## Matriz pedida

| Dimensión | Estado verificado |
|-----------|-------------------|
| **Fidelidad técnica** | 34 técnicas ATT&CK reales emitidas (IDs válidos v14, sub-técnicas incluidas) · hashes **reales** de advisories CISA #StopRansomware + Unit42 + TC-33 (el de WannaCry es el SHA256 auténtico de wcry.exe) · C2 IPs/dominios/URLs reales documentados · 11/12 tácticas cubiertas (Collection omitida por diseño: las alertas llegan post-detección) |
| **Generación de eventos** | `detection_time` UTC ISO · severity HIGH por familia (MEDIUM en droppers — correcto) · `domain` siempre poblado (contrato GoogleDNS) · probabilidades calibradas: stage TC-09 20%, url 30%, c2_ips 15%, file_path 10% · round-robin determinista en replay |
| **Estabilidad** | Retry `>=500` (transitorios) no 4xx · webhook resolution env→info.json→token sin fallback hardcodeado · replay con `limit/delay/on_result` + guard división-cero · `random` no seeded documentado (variabilidad = propósito; replay = vía determinista) |
| **Validación de telemetría** | Live (eval 42): `--count 1` → 200 webhook → `soar-alerts` 973→1016 · coherencia ATT&CK ahora gateada · hashes vs `HashValidator` gateados · validación estructural por familia en unit tests |

## Verificado además

- **IDs ATT&CK**: las 34 emitidas son técnicas reales de ATT&CK Enterprise (gate `test_emitted_techniques_are_canonical_attack_ids` con mapa canónico — un typo futuro rompe la suite)
- **Anti-vacío**: el gate exige ≥20 bloques extraídos — si el formato de las familias cambia, el gate falla en vez de pasar en vacío
- Tácticas en title-case: es el formato que consumen los playbooks de Shuffle (`mitre_tactics` display field — coherente con el resto del pipeline)

## Residuales (justificados)

| Restricción | Naturaleza |
|-------------|------------|
| Familias clásicas sin advisory con hash sintético | Documentado en el dict — los advisories no publican SHA256 canónico por familia; las que sí lo tienen llevan el real |
| Emite alertas (post-detección), no telemetría cruda | Diseño: el victim-sim (doc 50) cubre telemetría host-level ART-style; este simula la capa SIEM |
| Solo 11/34 técnicas con regla Sigma en el catálogo | La detección del pipeline es IoC+analyzer-driven, no Sigma-driven — catálogo evaluado aparte (doc 56) |

## Regresión

`test_simulator.py`: 7 → **9 gates** (coherencia + IDs canónicos).
