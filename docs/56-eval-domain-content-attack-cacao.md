# Evaluación Contenido de Dominio — MITRE ATT&CK / D3FEND / Sigma / STIX 2.1 / CACAO

> **Fecha**: 2026-11-12 · **Resultado**: **1 defecto de calidad corregido** + 5 gates nuevos (2 descubrieron invariantes de diseño al fallar). Score ~9,4/10.

## Defecto corregido

| ID | Defecto | Fix | Evidencia |
|----|---------|-----|-----------|
| DOM-EVAL-002 | Las 6 reglas Sigma carecían de `falsepositives` y `references` — calidad de regla incompleta (revisor sin contexto de FP ni fuentes) | `falsepositives` (escenarios benignos por regla) + `references` (URLs ATT&CK por técnica tageada, sub-técnicas como `/techniques/TXXXX/YYY/`) en las 6 | Gates que exigen ambos campos y que cada `attack.t*` tenga su URL de referencia |

## Matriz por dimensión

| Dimensión | Marco | Estado verificado |
|-----------|-------|-------------------|
| **Calidad de reglas** | Sigma spec | 6/6 well-formed: campos obligatorios, conditions referencian selections declarados, técnicas matcheadas = técnicas tageadas (DOM-EVAL-001), tags resuelven en catálogo versionado (sin deprecated), `falsepositives`+`references` ahora cubiertos |
| **Cobertura ATT&CK** | ATT&CK | Catálogo versionado `2026-11` con 11 técnicas curadas + lista `deprecated` (t1086 vetada); el bundle STIX abarca las **53 técnicas realmente ejercidas** (fixtures + scripts) — cobertura real > contrato curado |
| **Exportaciones válidas** | STIX 2.1 / CACAO 2.0 | **Live**: CACAO `type:playbook, spec:cacao-2.0, 50 steps` (start/38 action/9 parallel/if-condition/end) · STIX `141 objetos, validación estructural OK`. Ahora **gateado**: los tests ejecutan `convert()`/`build_bundle()` reales y exigen `validate_*()==[]` |
| **Mapeo defensivo** | D3FEND | Cada técnica del catálogo lleva array `d3fend` (countermeasures); el bundle STIX emite `course-of-action --mitigates--> attack-pattern` con URL canónica `d3fend.mitre.org` |
| **Automatización** | CACAO | Export `playbook` CACAO 2.0 desde el workflow Shuffle vivo; placeholders `__X__` todos sustituidos (gate); contención self-guard (workaround Shuffle 2.2.1 documentado); ambos outcomes (contain/observe) presentes |

## Invariantes descubiertos por los nuevos gates (documentados en código)

1. **`trigger_definitions` vacío en CACAO** — CACAO 2.0 **no modela triggers** (verificado contra spec CS01): el webhook se documenta en la descripción del start step. Correcto por diseño.
2. **`act_cortex_dyn_*`** — las exports llevan 13 nodos de analyzers cableados en runtime por init-webhook → drift check es builder ⊆ playbook, no igualdad.
3. **`act_containment` ausente en observe-only** — diferencia intencional de la variante (única excepción permitida por el gate).
4. **Constantes legacy** (`act_build_hive_summary`, `act_build_case_json`) — nodos fusionados en otros, documentados; el gate solo verifica ids realmente instanciados en `build_actions`.

## Residuales (justificados)

| Restricción | Naturaleza |
|-------------|------------|
| Catálogo de 11 técnicas | Subconjunto curado para TC-31; la cobertura real ejercida (53) vive en el bundle STIX |
| Sigma `status: experimental` | Honesto: reglas de lab sin telemetría de producción |
| Exports a `reports/` (gitignored) | Artefactos generados on-demand, no commiteados — coherente con la política del repo |

## Regresión

`test_domain_content.py`: 10 → **15 gates** · regresión completa tras cambios: ver resumen.
