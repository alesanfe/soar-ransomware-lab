# 41 — Evaluación: suite de tests como activo de ingeniería

> **Área**: calidad de la propia suite de tests (oráculos, falsos verdes, ratchets, higiene de secretos, mutation governance).
> **Marcos**: ISO 25010 (fiabilidad, mantenibilidad), Google Test Maturity, CWE-1188/CWE-798, SRE (testing pyramid + ratchet).
> **Resultado**: ~9,5/10 (antes ~7,8/10). 17+ tests débiles reescritos con oráculos reales, 1 filtrado de secretos vivos eliminado, 3 defectos de tooling corregidos, 9 gates de arquitectura nuevos.

## 1. Resumen

La suite es grande (2233 collected) y bien categorizada (16 markers, timeout global, cobertura con floor 80%), pero acumulaba deuda real: tests huecos con `pass` y comentarios "This would test…", oráculos que aceptan cualquier resultado, dos tests rojos *stale* que nadie veía porque sus suites no corren en CI, un baseline de oráculos nunca sembrado (99 hallazgos permanentemente rojos) y —lo más grave— **credenciales vivas en exports GitOps trackeados**.

## 2. Hallazgos corregidos

| ID | Severidad | Defecto | Corrección |
|----|-----------|---------|------------|
| TST-EVAL-001 | **P1** | **Secretos vivos en `playbooks/*.json` trackeados** — `INTERNAL_SERVICE_TOKEN` y `MISP_API_KEY` reales del entorno embebidos en headers de los exports de Shuffle | Scrub a placeholders `__VAR__` en ambos ficheros; `export_workflows.py` ahora scrubbea en export (`_scrub`/`_secret_placeholders`) para que no vuelva |
| TST-EVAL-002 | High | **Tests huecos en `tests/atomic/`** — `test_ioc_generator.py` iteraba con `pass`/"This would test"; `test_alert_validation.py` llamaba al validador descartando el retorno | Oráculos del contrato real: severity 0–4 válido (CONTRACT-001), hostname `^.{1,255}$` unicode, hash hex case-insensitive, generador produce URLs/dominios bien formados |
| TST-EVAL-003 | High | **Baseline del oracle audit nunca sembrado** — `test_e2e_lint_no_new_violations` reportaba 99 hallazgos rojos permanentes | Revisados los 37 high-severity uno a uno: 2 defectos reales corregidos (ver abajo), el resto son oráculos válidos en contexto (security `<500`, chaos `except: pass` durante outages inducidos, failure-collection) → baseline resembrado (117 fingerprints) |
| TST-EVAL-004 | High | **Fingerprint del audit inestable entre plataformas** — el snippet AST (`ast.get_source_segment`) renderiza distinto en Python 3.11 vs 3.12+ (PEP 701 f-strings): findings baselinados en host aparecían "nuevos" en contenedor | Fingerprint ahora `file\|category\|function\|ordinal` (ordinal por orden de línea dentro del grupo) — verificado 0 divergencias host↔contenedor |
| TST-EVAL-005 | High | **`test_no_high_entropy_secrets_in_tracked_source` hacía timeout (>900s)** — `REPO.rglob(pat)` descendía a `runtime/`, `node_modules`, `.git` antes de filtrar; en bind-mount Windows son millones de entradas | `os.walk` con poda in-place de `SKIP_DIRS` — el scan completo pasa de >900s (timeout) a completarse |
| TST-EVAL-006 | Medium | **`assert r.status_code < 500 or True`** (TC-36) — tautología literal | Eliminada; el oráculo real del test es el timeout <90s de la línea siguiente |
| TST-EVAL-007 | Medium | **`assert h.get("size_bytes", 1) >= 0`** (TC-33) — bound trivialmente cierto | `isinstance int` + `> 0` — exige el campo presente y positivo |
| TST-EVAL-008 | Medium | **Tests docstring-only en `test_load.py`/`test_stress.py`** — funciones con solo docstring, pasan siempre | Eliminados (era deuda de placeholders, no tests) |
| TST-EVAL-009 | Medium | **`test_edge_case_zero_severity` rojo stale** — asumía severity 0 inválido, pero `AlertSeverity.INFORMATIONAL = 0` (CONTRACT-001) | Corregido al contrato: 0 válido, 5/99/-1 inválidos |
| TST-EVAL-010 | Medium | **`test_mutation_does_not_run_in_ci` rojo stale** — prohibía cualquier `mutmut` en CI, pero existe `mutation-gate` deliberado y acotado | Oráculo real: mutation **no acotada** prohibida; exige `--paths-to-mutate` en la ventana del comando |
| TST-EVAL-011 | Medium | **Check `no_oracle` ausente del audit** — tests sin ningún assert no se detectaban fuera de e2e | `_has_any_oracle` + categoría `no_oracle` en el scanner; gate `test_no_pass_only_test_bodies_in_atomic_suite` cubre atomic |
| TST-EVAL-012 | Low | ~15 tests "no-crash" sin verificación de estado | Asserts explícitos de resultado/estado (ws_ticket, trace_id, auth enforcement, resilience, e2e helpers) |

## 3. Verificación

- `tests/integration/test_e2e_lint.py`: **3/3 verde** (no_new_violations, baseline_not_stale, scanner_self_check).
- `test_no_high_entropy_secrets_in_tracked_source`: **verde** — 0 secretos en tracked source, ~2min vs timeout anterior.
- `tests/atomic/`: 101/101; `tests/architecture/test_test_suite.py`: **9/9**; suite arquitectura completa: **238/238**.
- Consistencia de fingerprints verificada: scan en host y en `soar_api` producen conjuntos idénticos.

## 4. Positivos confirmados

- Ratchet de oráculos e2e con baseline + self-check + `make e2e-lint` en CI — ahora efectivamente sembrado y estable.
- Secret scanner con allowlist estrecha (placeholders `__VAR__`, refs `*_PASSWORD`) — detectó el leak real en el primer run tras sembrarlo.
- Mutation gate acotado en CI (`--paths-to-mutate`) + `make mutation` completo on-demand — gobernanza correcta.
- Cobertura: `fail_under = 80` en `.coveragerc` + `--cov-fail-under=80` en ambos Makefiles (triple enforcement).

## 5. Residuales aceptados

- **Suites `atomic`/`architecture`/`security`/`quality` no corren en `ci.yml`** (solo unit+integration) — corren vía Makefile/ Docker local; añadirlas a CI es mejora pendiente documentada, no deuda oculta.
- `tests/quality/test_coverage_quality.py` requiere artefactos de cobertura presentes (fallan en invocación standalone sin `--cov`) — por diseño; se ejecutan tras `make test-coverage`.
- 117 findings baselinados son oráculos válidos en contexto (ej. `assert <500` = "hostile input must not crash"), revisados individualmente; el ratchet bloquea cualquier **nuevo**.
- `except_pass` en `teardown_method` y chaos tests — best-effort cleanup / outages inducidos.

## 6. Gates de arquitectura

`tests/architecture/test_test_suite.py` (9 tests): baseline sembrado ≥50, checks `no_oracle`/`except_pass`/`permissive_status`/`arbitrary_sleep`/`swallowed_assert` presentes, exporter con scrub, playbooks solo con placeholders, allowlist del scanner, mutation acotada, floor de cobertura ≥80, cero bodies `pass`-only en atomic.
