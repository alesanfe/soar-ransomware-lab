# AGENTS.md — SOAR Ransomware Lab

> Guía rápida para agentes automatizados (Devin, Copilot, etc.) que trabajan en este repositorio.

## PROHIBITED GIT OPERATIONS — READ THIS FIRST

**NEVER run any of these commands without explicit user confirmation in the current session:**

- `git reset` (any form: `--hard`, `--soft`, `--mixed`, `HEAD`, `HEAD~1`, etc.)
- `git checkout -- <path>` or `git checkout .` (discards working tree changes)
- `git checkout <branch>` (if there are uncommitted changes — ask first)
- `git stash` (any form: `push`, `drop`, `clear`, `apply`, `pop`)
- `git clean -fd` or `git clean` with any destructive flag
- `git rebase` (rewrites history)
- `git cherry-pick` (can conflict with working tree)
- `git revert` (creates commits without asking)
- `git rm` (removes tracked files)
- `git branch -D` (force delete branch)
- `git push --force` or `git push -f`
- `git commit --amend` (rewrites history)
- `git update-ref` (low-level ref manipulation)

**Why:** The user works for long periods without committing. A single `git reset --hard HEAD`
or `git checkout -- .` destroys weeks of uncommitted work. This has already caused data loss
in this project. The user's working tree is the source of truth, NOT the last commit.

**What to do instead:**
- If you need to inspect the state: use `git status`, `git diff`, `git log`, `git reflog` (read-only)
- If you think a destructive git operation is needed: STOP, explain exactly what you want to
  run and why, and wait for the user to confirm. Do not assume prior approval extends to new
  destructive operations.
- If a script you wrote broke files: fix the specific files with `edit`/`write` tools, do NOT
  use `git checkout` to "restore" them — that discards the user's other unrelated changes too.
- If you accidentally ran a destructive command: tell the user IMMEDIATELY, do not attempt to
  hide or quietly repair it.

## Project overview

Laboratorio SOAR (Security Orchestration, Automation and Response) para respuesta ante ransomware.
Arquitectura hexagonal en Python (FastAPI) + infraestructura Docker Compose con TheHive, Cortex,
Shuffle, MISP, Elasticsearch/OpenSearch, Grafana/Loki/Promtail.

- **Lenguaje**: Python 3.11+
- **Framework**: FastAPI + Pydantic v2
- **Empaquetado**: `pyproject.toml` (setuptools), `src/` layout
- **Tests**: pytest (2233 tests collected, 1905 selected, 328 deselected: unit, integration, atomic, e2e)
- **Make**: `Makefile` raíz delega a `Makefile.win` o `Makefile.linux` según OS

## Repository structure

```
src/soar_lab/ # Código de producción (hexagonal)
 domain/ # Entidades, puertos, servicios de dominio
 application/ # Casos de uso, ports input/output
 auth/ # Re-export de AuthService (fachada)
 common/ # Exceptions, utils compartidos
 config/ # Settings, esquemas, logging
 data/ # Esquemas y utilidades de datos
 db/ # Inicialización de base de datos
 infrastructure/ # Adaptadores: integraciones, persistencia, auth, storage, monitoring
 interfaces/ # API FastAPI, CLI, static
 logging/ # StructuredLogger wrapper
 resilience/ # Circuit breaker, retry, timeout
 security/ # PayloadSanitizer
 simulator/ # Simulador de alertas SIEM
 validation/ # Validadores reutilizables
tests/ # Suite completa (unit, integration, atomic, e2e, contracts, security, architecture, performance, quality, baseline)
infra/docker/ # Docker Compose + config + images personalizadas
scripts/ # Scripts standalone (CANONICAL location): setup, CI, reports, maintenance, quality, debug, safety
 scripts/setup/ # Scripts de setup (ejecutados dentro de Docker, baked en imagen)
docs/ # Documentación técnica (6 documentos principales + api + assets + thesis)
apps/ # apps/api (Dockerfile), apps/docs-site (Docusaurus), apps/web-management
reports/ # Reportes generados (e2e, quality, mutmut, test-review, holistic) — gitignored
runtime/ # Datos en runtime (volumes Docker, data, logs, results, backups) — gitignored
artifacts/ # Artefactos generados (backups, coverage, data, logs, results)
```

## Build & install

```bash
# Instalar en modo desarrollo
pip install -e ".[dev,test,quality]"

# Instalar pre-commit hooks
pre-commit install
```

## Verification commands

```bash
# === Tests ===
make test-unit          # Solo unit tests (en Docker)
make test-integration   # Tests de integración (en Docker)
make test-e2e           # Tests end-to-end (requiere Docker levantado)
make test-coverage      # Tests con cobertura (en Docker)
make test-atomic        # Tests atómicos
make test-performance   # Tests de rendimiento
make test-security      # Tests de seguridad
make test-smoke         # Smoke tests
make test-all           # Todos los tests

# === Linting ===
make lint               # Ruff + Black + isort + mypy + flake8 + docs-lint (un solo comando)
make docs-lint          # Linters de docs (markdownlint, lychee, docs_quality) + generación Sphinx
make lint-fix           # Aplicar fixes automáticos (black + isort + ruff)
make deps-lint          # Instalar dependencias de linters

# === Quality ===
make quality            # Suite completa de quality/ (radon, bandit, vulture, etc.)
make mutation           # Mutation testing con mutmut en Docker (on-demand, 60-180 min)
make test-review        # Informe de revisión de tests (7 dimensiones) -> reports/test-review/
make holistic-review    # Holistic Project Radar (5 capas, 16 dims) -> reports/holistic/

# === Docker ===
make up                 # Levantar todo el stack
make down               # Parar el stack
make restart            # Reiniciar el stack
make health             # Healthcheck de todos los servicios
make logs               # Logs de todos los servicios
make logs-service       # Logs de un servicio específico (make logs-service s=api)
make ps                 # Estado de contenedores
make clean              # Limpiar archivos temporales (reports, runtime logs)
make clean-shuffle      # Limpiar ejecuciones stale de Shuffle
make reset              # Reset completo (down + clean + up)
make validate-credentials  # Validar credenciales de servicios

# === Simulación ===
make simulate-malicious  # Enviar alerta maliciosa al workflow
make simulate-benign     # Enviar alerta benigna
make simulate-batch      # Enviar lote de alertas
make simulate            # Enviar alerta (interactivo)
make generate-iocs       # Generar IoCs de prueba
make generate-secrets    # Generar secretos y claves
make metrics             # Generar KPIs y métricas
make init-webhook        # (Re)inicializar webhook de Shuffle

# === Backups ===
make backup              # Crear backup
make restore             # Restaurar backup

# === Dev ===
make install-dev         # Instalar en modo desarrollo
make dev-shell           # Shell interactivo en contenedor API
make dev-debug           # Debug con pdb en contenedor API
make docs-serve          # Servir docs localmente (Docusaurus)
make docs-build          # Build docs (Docusaurus)
```

## Code conventions

- **Line length**: 100 caracteres (black + flake8)
- **Imports**: isort con profile black
- **Tipado**: mypy con `--ignore-missing-imports`
- **Arquitectura**: hexagonal — el dominio NO depende de infraestructura ni frameworks
- **Composition root**: `src/soar_lab/interfaces/api/composition.py`
- **Tests**: usar `pytest` con fixtures, mocks para servicios externos
- **No dejar scripts `_*.py` sueltos en la raíz** — usar `scripts/debug/` si es necesario

## Documentation structure

La documentación técnica vive en `docs/` con 6 documentos principales:
- `01-getting-started.md` — Instalación, requisitos y guía rápida
- `02-architecture.md` — Arquitectura hexagonal, Docker, código, seguridad
- `03-api-and-integrations.md` — API REST, endpoints e integraciones
- `04-operations.md` — Configuración, infraestructura, backups, troubleshooting
- `05-testing.md` — Estrategia de pruebas y suite
- `06-project-management.md` — Objetivos, plan, riesgos, auditorías
- `glossary.md` — Glosario central
- `index.md` — Índice de documentación

Cada documento principal sigue esta estructura de 6 secciones:
1. Resumen (1.1 Objetivo, 1.2 Contexto)
2. Alcance (2.1 Qué cubre, 2.2 Límites, 2.3 Dependencias)
3. Contenido principal (3.x adaptado a cada doc)
4. Validación (4.1 Verificación, 4.2 Criterios de aceptación, 4.3 Evidencias)
5. Problemas y consideraciones (5.1 Limitaciones, 5.2 Riesgos, 5.3 Recomendaciones)
6. Referencias

La tesis (TFM) vive en `docs/thesis/`. Sus archivos markdown son la fuente de verdad del documento académico; las modificaciones deben limitarse a correcciones de estilo, reducción de patrones de texto IA y ajustes editoriales, sin alterar el contenido técnico ni los resultados experimentales.

## Environment

- `.env.full` contiene las variables reales (NO subir al repo, está en `.gitignore`)
- `.env.example` documenta las variables necesarias
- `.env.testing` para entorno de tests
- Nunca commitear secretos, API keys o contraseñas

## CI/CD

- `.github/workflows/ci.yml` — lint, tests, validación de compose
- `.github/workflows/vale.yml` — linting de documentación
- `.github/ISSUE_TEMPLATE/` — plantillas para issues (bug, feature, EDT)

## Common pitfalls

- **Docker Desktop en Windows**: puertos 2976-3075, 5600-5699, 55000-55099 reservados por Hyper-V
- **Elasticsearch single-node**: estado `yellow` es normal (no puede asignar réplicas)
- **Shuffle webhook**: tras `make reset`, regenerar con `make init-webhook`
- **Shuffle stale executions**: los workflows interrumpidos (test failures, restarts) dejan ejecuciones en `EXECUTING` en OpenSearch que saturan el Orborus (max 10 workers). Limpiar con `make clean-shuffle` antes de tests E2E. `make test-e2e` ya lo hace automáticamente. Script: `scripts/maintenance/clean_shuffle_executions.py`
- **TheHive API key**: tras reset, regenerar con `python scripts/setup/init_thehive.py` (no hay target `make init-thehive`)
- **Cortex analyzers**: requieren Docker-in-Docker, configurar `runners: ["docker"]` en cortex.conf
- **Cortex Robtex analyzer (DEPRECATED)**: Robtex_IP_Query_1_0 fallaba siempre (100%) porque Cloudflare bloquea el User-Agent `python-requests/2.x`. **Solución adoptada**: se ha reemplazado Robtex por **DShield_lookup_1_0** (SANS ISC IP reputation, free, sin API key) para IP lookup y **Mnemonic_pDNS_Public_3_0** (passive DNS público, free) para reverse PDNS. Ambos funcionan correctamente sin parches. Los analyzers de Robtex están en `_SKIP_DYNAMIC_NAMES` para que no se cableen automáticamente en el workflow. Los Dockerfiles parcheados siguen en `infra/docker/cortex-analyzers/robtex-*-patched/` por compatibilidad histórica pero ya no se usan.
- **Cortex GoogleDNS empty data**: GoogleDNS_resolve_1_0_0 fallaba cuando el workflow enviaba `data=""` (dominio vacío). **Solución**: el simulador ahora SIEMPRE incluye un campo `domain` válido (de TC-33 C2 infrastructure) en cada alerta, y `build_es_json.py` ahora indexa el campo `domain` en `soar-alerts`.
- **Script paths en contenedor**: los scripts están en `/app/scripts/` dentro del contenedor (Dockerfile hace `COPY scripts ./scripts`). El Makefile usa `docker exec soar_api python /app/scripts/setup/<script>.py`.
- **Scripts canonical location**: `scripts/` en la raíz es la ubicación canónica. NO añadir scripts a `src/soar_lab/` — usar `scripts/` en la raíz.
- **webhook_info.json**: `init_shuffle_webhook.py` lo guarda en `/app/reports/validation/results/webhook_info.json`. Los tests E2E lo buscan allí
- **Loki**: puede tardar 30-60s en estar ready después de `make up`. HTTP 503 en `/ready` es normal durante el arranque
- **conftest.py**: usa `load_dotenv(override=True)` para que `.env.full` tenga prioridad sobre `os.environ`. Esto es correcto porque `init_thehive.py` y `reset_cortex.py` actualizan `.env.full` con las keys frescas
