# Evaluación Suite de Tests — ISO 29119 · OWASP SAMM · NIST SSDF

> **Fecha**: 2026-11-12 · Re-evaluación bajo estándares de proceso de testing (complementa `docs/41`, ISO 25010/Google maturity). **Resultado**: 2 gaps corregidos. Score ~9.6/10.

## Defectos corregidos

| ID | Defecto | Fix | Gate |
|----|---------|-----|------|
| TST-EVAL-2-001 | **Resultados de tests no archivados** — los 3 jobs de CI corrían `-v` a consola: ningún artefacto JUnit → sin registro de completion por run (ISO 29119 §8.4 test completion reporting) | `--junitxml=reports/junit/{unit,local-suites,integration}.xml` + `upload-artifact` con `if: always()` (se archiva también en fallo — exactamente cuando más importa) | `test_ci_emits_junit_reports_for_test_jobs` |
| TST-EVAL-2-002 | **Ratchet de coverage por PR implícito** — Codecov con defaults, sin declaración de umbrales | `codecov.yml`: `project` target=auto threshold=1% (una PR no puede regresar >1pt) + `patch` target=80% (código nuevo al floor) | `test_coverage_ratchet_declared` |

## Matriz por dimensión

| Dimensión | Marco | Estado verificado |
|-----------|-------|-------------------|
| **Cobertura real** | ISO 29119 | `branch = True` (criterio de ramas, no solo líneas) + `fail_under=80` triple-enforced (.coveragerc + Makefiles) + ratchet PR codecov + `test_coverage_quality` anti-gaming |
| **Oráculos** | SAMM V-AA | Ratchet `e2e_oracle_audit` (117 fingerprints sembrados, fingerprint estable cross-platform) + categorías `no_oracle`/`except_pass`/`permissive_status`/`arbitrary_sleep`/`swallowed_assert` + hollow-body gate en atomic + mutation testing acotado en CI |
| **Calidad test-data** | ISO 29119 §5.2 | Sintética: `simulator/` genera alertas con IoCs fabricados · Hypothesis property-based · `.env.testing` con valores sintéticos separados · zero PII (dataset de lab) |
| **Seguridad pipeline** | SAMM V-ST | Todas las suites en CI (atomic+architecture+security+contract+quality — residual eval-41 cerrado) · compose `config` validation · `--strict-markers` · timeout 900 global · `pytest-randomly` orden aleatorio (detecta acoplamiento) · **sin rerunfailures** — flaky=defecto, fail-closed (gate) |
| **Detección secretos** | SSDF RV.3 | TruffleHog + `scan_secrets.py` + `test_no_high_entropy_secrets_in_tracked_source` (~2min, walk podado) + export_workflows scrub + allowlist estrecha — triple capa |

## Pirámide (conteo de ficheros)

unit 204 · e2e 170 · integration 48 · architecture 24 · quality 15 · atomic 5 — base ancha + capa distintiva de gates arquitectónicos (los ~356 tests de regresión de esta serie de evaluaciones).

## Positivos

- `mutmut junitxml` en CI acotado + `make mutation` completo on-demand
- Fingerprint AST estable 3.11↔3.13 (TST-EVAL-004)
- `pytest-randomly` + seed reportada → reordenamiento reproducible
- Secretos de tests: `.env.testing` separado con placeholders descriptivos (gate `.env.example` análogo)

## Residuales (justificados)

| Restricción | Naturaleza |
|-------------|------------|
| Suites e2e/performance/soak solo local (Docker) | Requieren stack vivo — no corren en CI por diseño (smoke E2E sí corre vía workflow dedicado) |
| 117 findings baselinados | Revisados individualmente (eval 41); el ratchet bloquea nuevos |
| codecov.yml sin verificación contra el servicio | Config declarativa; si la app Codecov no está instalada el archivo es inerte — el floor 80% sigue enforced local+CI |

## Regresión

`test_test_suite.py`: 9 → **14 gates**.
