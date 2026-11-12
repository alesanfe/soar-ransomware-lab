# 44 — Evaluación: tooling operacional

> **Área**: `Makefile.win`/`Makefile.linux` (350 targets), `scripts/` (manifiesto, doctor, preflight), discoverability operativa.
> **Marcos**: ISO 25010 (operabilidad, mantenibilidad), SRE (toil reduction, runbook automation), GNU Make best practices.
> **Resultado**: ~9,5/10 (antes ~9,0/10). 1 defecto latente corregido, 8 gates nuevos, 0 drift cross-OS verificado.

## 1. Resumen

El tooling operacional es uno de los puntos más maduros del proyecto: 350 targets compartidos con **paridad perfecta** entre Windows y Linux, manifiesto de scripts auto-generado con gate de frescura en CI, `doctor.py` con diagnósticos accionables PASS/WARN, y preflight como prerequisito de `make up`. La deuda encontrada era latente más que activa.

## 2. Hallazgos corregidos

| ID | Severidad | Defecto | Corrección |
|----|-----------|---------|------------|
| OPS-EVAL-001 | Medium | **16 targets sin `.PHONY`** (`backup-core`, `drill-obs`, `verify`, `test-collect`, etc.) — sin colisión hoy, pero un fichero homónimo futuro haría que el target "succeediera" silenciosamente sin ejecutar nada | `.PHONY` completado en ambos Makefiles → 350/350 targets declarados; gate lo hace cumplir |

## 3. Verificación

- **Paridad**: extracción de targets por regex en ambos Makefiles → `win-only: []`, `linux-only: []`, 350 compartidos.
- **Referencias**: 0 rutas `scripts/*.py` muertas desde los Makefiles.
- **Sin duplicados**: 0 targets redefinidos en cada Makefile.
- **Manifiesto**: `generate_scripts_manifest.py --check` → "up to date" + gate en `ci.yml:94`.
- **Live**: `doctor.py` → PASS docker/compose/env/ES/Loki/webhook, WARN accionables (Hyper-V ports, redis-TLS con contexto de healthcheck del contenedor).
- **Scripts "huérfanos"**: los 75 sin referencia en Makefile/CI son `debug/` (uso manual intencional) o sub-scripts invocados por otros — todos catalogados en SCRIPTS-MANIFEST.md con criticality tags.

## 4. Positivos confirmados

- `doctor.py` produce diagnósticos accionables (incluye el pitfall documentado de Hyper-V ports, healthcheck de contenedor como contexto de fallos de sondeo TLS).
- `preflight` gatea `make up`; `up-lab` avisa del perfil inseguro explícitamente.
- Manifiesto generado por AST (docstring como propósito, `⚠ no docstring` visible en vez de silencioso), criticality tags (blocking/operational/tooling), `--check` en CI.
- `soar_test_runner` es tooling debug ad-hoc documentado (`mk_test_runner.py`), no un servicio olvidado.
- Scripts de operación vistos en evals anteriores: backup/drill con sha256+manifest, rotación 7-fases, export con scrub de secretos.

## 5. Residuales aceptados

- `soar_test_runner` `Exited 255` tras reinicio de Docker — `restart: no` por diseño (debug ad-hoc, se recrea con `mk_test_runner.py`).
- `redis ping` WARN en doctor — esperado: redis exige TLS; el WARN ya reporta `container health: healthy` como contexto correcto.
- 75 scripts sin referencia directa en Makefile/CI — descubribles vía manifiesto; `debug/` es manual por definición.

## 6. Gates

`tests/architecture/test_operational_tooling.py` (8): paridad win↔linux, `.PHONY` 100%, sin duplicados, sin refs muertas, gate de manifiesto en CI, sin scripts sueltos en raíz, targets operativos core, probes de doctor.
