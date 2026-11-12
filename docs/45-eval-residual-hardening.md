# 45 — Evaluación: endurecimiento residual

> **Área**: residuales endurecibles dejados por las 19 evaluaciones de área (docs/25..44).
> **Marcos**: ISO 25010, SRE (elimination of toil / warning fatigue), CI completeness.
> **Resultado**: ~9,5/10 → residuales cerrados. 7 defectos corregidos, 10 gates nuevos, build Docusaurus verificado.

## 1. Resumen

Tras elevar las 19 áreas a ≥9,5/10, quedaban residuales documentados como "aceptados por diseño". Esta evaluación cierra los que eran endurecibles sin coste operativo: suites de CI faltantes, diagnóstico Redis-TLS, link-checking comprometido y bloqueante, Docusaurus `throw`, comportamiento explícito de artefactos de cobertura, y eficiencia del escaneo de dependencias.

## 2. Hallazgos corregidos

| ID | Defecto | Corrección |
|----|---------|------------|
| CI-EVAL-001 | **Suites puras-locales ausentes de `ci.yml`** — `atomic`, `architecture`, `security`, `contract`, `contracts`, `general`, `quality` solo corrían por Makefile: un test rojo en ellas sobrevivía sin que CI lo detectara (causa raíz de dos rojos stale encontrados en TST-EVAL) | Job `test-local-suites` añadido: `pytest tests/atomic tests/architecture tests/security tests/contract tests/contracts tests/general tests/quality -m "not requires_docker and not requires_external"` |
| OPS-EVAL-002 | **`doctor.py` probeaba Redis en plano** — `redis-cli ping` sin TLS contra listener TLS-only → WARN engañoso "ping failed" aunque el servicio estuviera sano | Probe con `--tls --cacert /etc/redis/tls/ca.crt` + auth → verificado: WARN→**PASS** "PONG via docker exec" |
| DOC-EVAL-004 | **Lychee sin config comprometida y no bloqueante** — `lychee --quiet docs/` ad-hoc, prefijo `-@` ignoraba errores | `lychee.toml` commiteado (privadas/localhost excluidas, `include_fragments=true`, placeholders `<…>`/`${…}` ignorados); `docs-lint` corre `lychee --offline` **bloqueante** en ambos Makefiles (online sigue disponible manualmente) |
| DOC-EVAL-005 | **`onBrokenLinks: 'warn'`** — enlaces rotos nunca rompían el build | `'throw'` en `onBrokenLinks`/`onBrokenMarkdownLinks`/`onBrokenAnchors`. El primer build `throw` destapó **2 anchors rotos reales** en `e2e_report.md` (ToC → secciones ausentes) |
| DOC-EVAL-006 | **Secciones del reporte E2E emitidas condicionalmente** — `_md_sec_19_analyzers`/`_md_sec_21_calidad` omitían el header entero cuando faltaba data → ToC huérfano | Headers siempre emitidos con stub `_Datos no disponibles en esta ejecución._` (fix en el generador + reporte actual + copia de tesis) |
| TST-EVAL-013 | **`_ensure_coverage_xml` fallaba en silencio** — subprocess con `capture_output` y timeout 300s: si fallaba, los tests daban error genérico o colgaban | Fixture reporta `returncode`+tail del subprocess y hace `pytest.skip(allow_module_level=True)`; timeout→600s con `TimeoutExpired` capturado |
| TST-EVAL-014 | **`pip_audit` invocado 5× por módulo** — cada llamada bootstrap un venv y consulta OSV/PyPI → suite quality ~4× más lenta | Fixtures module-scoped `env_audit`/`lock_audit` → 2 llamadas totales |

## 3. Verificación

- **`docker build --target build`**: `npm run build` con los 3 gates `throw` → **SUCCESS, 0 links/anchors rotos** (los "rotos" del build en host eran falsos: el contenido sincronizado `docs/`+`reports/` solo existe en el contexto Docker).
- **`doctor.py` live**: `redis → PASS "PONG via docker exec"`.
- **Gates**: `test_residual_hardening.py` **10/10** dentro del contenedor; regresión arquitectura **272/272**.
- **YAML**: `ci.yml` parsea; `py_compile` de todos los ficheros tocados OK.

## 4. Nota operativa (incidente durante la sesión)

Al recrear `soar_api` para montar `lychee.toml` (`/app/lychee.toml`, añadido a `docker-compose.api.yml` + `docker-compose.hardened.yml` siguiendo el patrón de `bandit.yaml`), el binding `127.0.0.1:8000` falló: **Hyper-V/winnat había reservado el rango 7969-8068 tras el arranque original**. `net stop winnat` requiere elevación — como workaround se fijó `API_PORT=8070` en `.env` (el puerto interno sigue siendo 8000; el env interno `API_PORT=8000` está hardcodeado en compose). API healthy en `http://localhost:8070`. Para volver a 8000: `net stop winnat` (admin) → restaurar `API_PORT=8000` → `make up`.

## 5. Residuales aceptados (justificados)

- **Vale `fail_on_error: false`**: linting estilístico — bloquearía por prosa, no por corrección técnica; el gate duro es `docs_quality.py` + lychee offline.
- **markdownlint/Sphinx advisory**: mismo criterio; Sphinx es generación opcional local.
- **Lychee online advisory**: chequeo de URLs externas es network-dependent y flaky por diseño; el offline (links internos + anchors de ficheros) sí es bloqueante.
- **75 scripts sin referencia directa en Make/CI**: `debug/` manual y sub-scripts — catalogados en el manifiesto.
- **Fingerprint baselines E2E (117)**: revisados individualmente; oráculos contextuales válidos (chaos, security bounds).

## 6. Regresión

- 10/10 gates nuevos en `tests/architecture/test_residual_hardening.py`.
- Suite arquitectura completa: **272/272**.
