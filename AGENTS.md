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
make lint               # Suite de 31 linters (ruff/black/isort/flake8/mypy + pylint/bandit/vulture/radon/semgrep/yamllint/codespell/checkov/shellcheck/hadolint/actionlint...) -> reports/quality/lint-report.md + docs-lint
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
- **TheHive 5 (TH-001)**: la imagen es `strangebee/thehive` con almacenamiento embebido (JanusGraph/BerkeleyJE + Lucene) — **no usa Elasticsearch** ni el índice `the_hive_17`. La API es `/api/v1` (Query API `POST /api/v1/query` con `_name: listCase`/`filter`/`page` para listados); las entidades devuelven `_id`/`number` (el cliente aliasa a `id`/`caseId` para compat). Estados de caso válidos: `New`, `InProgress`, `TruePositive`, `FalsePositive`, `Indeterminate`, `Duplicated`, `Other` — **`Open`/`Resolved` NO existen en TH5**. Estados de task: `Waiting`/`InProgress`/`Completed`/`Cancel` (`Cancelled` es inválido). Health sin auth: `/api/v1/status/public` (`/api/v1/status` y `/api/status` requieren auth).
- **TheHive API key**: el bootstrap crea org `soar` + usuario `analyst@soar.local` (org-admin) — la key del superadmin `admin@thehive.local` NO puede crear casos en TH5. `init_thehive.py` es idempotente: renueva la key solo si la actual no valida y la escribe a `runtime/results/thehive_api_key.txt` (montado) + `.env`/`.env.full`/`.env.container`. Tras `make reset`, ejecutar `python scripts/setup/init_thehive.py` desde host (no hay target `make init-thehive`).
- **Shuffle workflow scripts**: los scripts embebidos (`scripts/setup/shuffle_workflow/scripts/*.py`) se incrustan en la definición del workflow en tiempo de setup — tras editarlos hay que re-ejecutar `make init-webhook` para que el workflow en vivo los recoja. Placeholders `__THEHIVE_INT__`/`__THEHIVE_KEY__` se sustituyen en `workflow_actions.py` — todo `load()` de un script que llame a TheHive necesita sus `.replace()`.
- **MISP TLS (MISP-001)**: el stack usa PKI interna — CA propia en `infra/docker/config/certs/` generada por `scripts/setup/gen_certs.sh` (`make certs`). El cert de MISP tiene SANs `misp`/`localhost`/`127.0.0.1` y la CA se monta en `soar_api` (`/app/certs/ca.crt`); `health_check.py` verifica contra ella. En Windows, Schannel puede reportar `CERT_TRUST_REVOCATION_STATUS_UNKNOWN` con CAs internas offline — es benigno (verificar con OpenSSL o desde dentro del docker). Ojo: `-subj "/C=..."` de openssl necesita `MSYS_NO_PATHCONV=1` en Git Bash.
- **Cortex analyzers**: requieren Docker-in-Docker, configurar `runners: ["docker"]` en cortex.conf
- **Cortex Robtex analyzer (DEPRECATED)**: Robtex_IP_Query_1_0 fallaba siempre (100%) porque Cloudflare bloquea el User-Agent `python-requests/2.x`. **Solución adoptada**: se ha reemplazado Robtex por **DShield_lookup_1_0** (SANS ISC IP reputation, free, sin API key) para IP lookup y **Mnemonic_pDNS_Public_3_0** (passive DNS público, free) para reverse PDNS. Ambos funcionan correctamente sin parches. Los analyzers de Robtex están en `_SKIP_DYNAMIC_NAMES` para que no se cableen automáticamente en el workflow. Los Dockerfiles parcheados siguen en `infra/docker/cortex-analyzers/robtex-*-patched/` por compatibilidad histórica pero ya no se usan.
- **Cortex GoogleDNS empty data**: GoogleDNS_resolve_1_0_0 fallaba cuando el workflow enviaba `data=""` (dominio vacío). **Solución**: el simulador ahora SIEMPRE incluye un campo `domain` válido (de TC-33 C2 infrastructure) en cada alerta, y `build_es_json.py` ahora indexa el campo `domain` en `soar-alerts`.
- **Script paths en contenedor**: los scripts están en `/app/scripts/` dentro del contenedor. `scripts/` está bind-mounted en `docker-compose.api.yml` (igual que `src/` y `tests/`), así que el host es la fuente de verdad — el `COPY scripts ./scripts` del Dockerfile solo aplica cuando el contenedor se recrea sin compose o desde imagen limpia. El Makefile usa `docker exec soar_api python /app/scripts/setup/<script>.py`.
- **`docker restart <container>` mata los `docker exec` en curso**: los tests E2E corren DENTRO de `soar_api` vía exec — reiniciar el API (VAL-002, cambios de middleware) aborta cualquier pytest en vuelo. Relanzarlos tras el restart.
- **Scripts canonical location**: `scripts/` en la raíz es la ubicación canónica. NO añadir scripts a `src/soar_lab/` — usar `scripts/` en la raíz.
- **webhook_info.json**: `init_shuffle_webhook.py` lo guarda en `/app/reports/validation/results/webhook_info.json`. Los tests E2E lo buscan allí
- **Loki**: puede tardar 30-60s en estar ready después de `make up`. HTTP 503 en `/ready` es normal durante el arranque
- **conftest.py**: usa `load_dotenv(override=True)` para que `.env.full` tenga prioridad sobre `os.environ`. Esto es correcto porque `init_thehive.py` y `reset_cortex.py` actualizan `.env.full` con las keys frescas
- **Hardened + nginx**: los servicios basados en `nginx:alpine` (nginx, web-management) necesitan `cap_add: [NET_BIND_SERVICE, CHOWN, SETUID, SETGID]` bajo `cap_drop: [ALL]` — el entrypoint hace `chown` en /var/cache/nginx y los workers hacen `setgid(101)`. Sin esas caps entran en crash-loop. `docs-site` es node :8080 y no las necesita.
- **OpenSearch red tras crash**: si el backend muere mid-flush, un índice puede quedar con shard primaria corrupta (`ALLOCATION_FAILED` → cluster red → TODOS los e2e fallan en setup). Diagnóstico: `GET _cat/shards?h=index,shard,prirep,state,unassigned.reason`. Índices prescindibles (p.ej. `notifications-000001`) se pueden borrar y el backend los recrea.
- **E2E largos desde host**: lanzar pytest detached dentro del contenedor (`docker exec -d soar_api sh -c "... > /tmp/run.log 2>&1"`) y hacer `tail` del log — un `docker exec` interactivo muere si se corta la sesión shell del host.
- **Load test locust permanente**: hay un generador de alertas locust activo (~1 ejecución/min, `source: webhook`) — las "ejecuciones fantasma" en OpenSearch son suyas, no un bug. Antes de medir, distinguir entre ejecuciones de test y ambientales por `started_at`/`alert_id`.
- **`.bandit` stale mount**: el contenedor `soar_api` fue creado con bind-mount `./.bandit:/app/.bandit` cuando existía como fichero; desde que se renombró a `bandit.yaml`, `docker restart soar_api` falla ("mount src .bandit: not a directory") y crea un directorio vacío `.bandit/` en el host. Workaround: borrar ese directorio y mantener una copia `.bandit` (igual que `bandit.yaml`) hasta que el contenedor se recree vía `docker compose up -d api`
- **API código stale tras restart largo**: uvicorn corre SIN `--reload`; el bind-mount de `src/` no recarga el proceso. Un `soar_api` up 19h sirve código viejo (rutas `/api/v1/queue/*` ausentes aunque existan en source). Tras cambios en `src/`, hacer `docker restart soar_api` para activarlos
- **Latencia desde host Windows**: medir `POST /api/v1/alerts` concurrente desde el host atraviesa el port-proxy de Docker Desktop (P95 ~6.3s para 60 conc). Dentro del contenedor (`docker exec soar_api`) el mismo burst da P95 ~174ms. Medir siempre dentro de la red docker para evidencia de rendimiento
- **E2E en host Windows**: `tests/e2e/pytest.ini` fija `timeout_method = signal` — rompe pytest-timeout en Windows (sin SIGALRM). Correr tests e2e dentro del contenedor (`docker exec soar_api pytest tests/e2e/...`) salvo la suite Playwright (`tests/e2e/TC-28/test_ui_playwright.py`), que es host-only y se ejecuta con `-c pytest.ini -m "requires_docker or not requires_docker" --no-cov` (el pytest.ini raíz des-selecciona `requires_docker` y exige coverage 80 %).
- **Eventual consistency**: los docs de OpenSearch (`workflowexecution-000001`) alcanzan `FINISHED` DESPUÉS de que la API de Shuffle lo reporte, y Promtail tarda >60 s en ingerir bajo carga. Nunca asserts de estado con una sola lectura — usar `self.wait_until` con `self.timeout("es_index")`/`("loki_ingest")`.
- **Payload del webhook Shuffle**: debe ser PLANO (campos top-level: `severity`, `alert_id`, `hostname`, `src_ip`, `hash`, `domain`, `correlation_id`, `trace_id` — como `build_alert_payload` en `tests/e2e/base/service_mixins.py`). Un payload anidado `{"alert":{...}}` es rechazado por `normalize_inputs` ("REJECTED: missing webhook severity") y deja la ejecución zombie en `EXECUTING` con 0 resultados hasta timeout.
- **Grafana dashboard provisioning version-gating**: el provisioner ignora ficheros cuyo `"version"` es ≤ al guardado en la DB de Grafana — editar un dashboard JSON sin bump de versión NO se re-importa aunque el fichero montado esté actualizado (el /api/dashboards sirve la versión vieja de DB). Tras editar `logging/*-dashboard.json`, subir `"version"` y hacer `up -d --force-recreate grafana`.
- **Grafana webhook contact point sin headers custom (10.3.4)**: `settings.headers` provisionado se guarda pero el sender NO lo aplica al wire (feature de versiones posteriores) — el receptor SOAR recibía 401. Usar `authorization_scheme`/`authorization_credentials` → envía `Authorization: Service-Token <token>`, aceptado por `_service_token_scope` como equivalente a `X-Service-Token`.
- **Render URL format**: `GET /render/d-solo/<dashboard_uid>?panelId=N` — el prefijo `uid/` en el path (`d-solo/uid/<uid>`) solo funciona para algunos dashboards y produce "Dashboard not found"/"Panel not found" en otros. TC-35 usa el formato canónico.
- **Loki labels**: los logs de contenedores se indexan con label `compose_service` (no `container_name`) — las queries LogQL de tests deben usar `{compose_service="api"}`.
- **`$__rate_interval` no se sustituye en render**: los macros de intervalo (`[$__rate_interval]`, `$__interval`) quedan literales cuando el renderer/abckend datasource no tiene contexto de panel → Loki devuelve `parse error ... not a valid duration` → `ds/query` 400 → panel colgado 60s. En dashboards provisionados usar rangos fijos (`[1m]`, `[5m]`).
- **Tempo backend en Grafana 10.3.4 solo soporta `queryType: 'traceId'`** en QueryData (`pkg/tsdb/tempo/tempo.go`) — `search`/`traceql`/`traceqlSearch`/`serviceMap` devuelven `unsupported query type` (500). El search UI va por CallResource (Explore). Para un panel "recent traces" usar el datasource `tempo-json` (marcusolsson-json) → `tempo:3200/api/search`.
- **marcusolsson-json-datasource: el campo de path es `urlPath`, no `url`**: `query.url` se ignora en proxy mode → fetch al root del datasource (404 → "No data"). Modelo real: `{method, urlPath, queryParams, fields:[{jsonPath,language:'jsonpath',name,type}]}`. Además es frontend-only: `POST /api/ds/query` devuelve "Plugin unavailable" — se valida vía render, no vía backend.
- **Grafana renderer clustered env names**: los válidos son `RENDERING_CLUSTERING_MODE`/`RENDERING_CLUSTERING_MAX_CONCURRENCY`/`RENDERING_CLUSTERING_TIMEOUT` (NO `RENDERING_CLUSTERED_*`). Verificar en el log del sidecar (`maxConcurrency`,`timeout`) — los defaults silencian typos. El renderer se degrada tras ~25 renders secuenciales; clustering + subir límites CPU/mem lo estabiliza.
- **Escribir dashboards JSON desde Windows**: `open(f,'w')` sin encoding usa cp1252 → caracteres como `—`/`É` corrompen el UTF-8 del fichero (json válido pero títulos mojibake o fichero no-decodificable). Siempre `encoding='utf-8'` + `ensure_ascii=False` en json.dump.
- **Servicio swarm `127-0-0-1` (bug corregido)**: con `SHUFFLE_WARM_APPS=true` + worker image previa a patch `0006`, cualquier error TCP al warm-app invocaba `findAppInfo→deploySwarmService` sin chequear el modo → creaba un servicio swarm `127-0-0-1` (3 réplicas `http_1.4.0`, crash-loop ~10 s/task, publica `*:33334`). Si reaparece (`docker service ls`), el worker image está desactualizada — rebuild via `make build-worker`. Fix: `0006-swarm-redeploy-guard.patch` — redeploy solo cuando `SHUFFLE_SWARM_CONFIG=run|swarm`.
- **`workflowexecution-*` rollover ISM — usar SIEMPRE el alias `workflowexecution`**: el índice rota (`-000001`→`-000002`→…) y los literales hardcodeados dejan de ver ejecuciones nuevas. Además el template de Shuffle no mapea `execution_argument` → cada índice nuevo puede traer mapping `text`+`.keyword` en vez de `keyword` puro, rompiendo wildcards term-level. Queries robustas: `bool.should` sobre `execution_argument` + `execution_argument.keyword`. `configure_es.py` parcha el template a `keyword` para próximos rollovers.
- **Bind-mounts relativos en compose**: las rutas relativas se resuelven contra el directorio del PRIMER `-f`, no contra el fichero que las declara. En `logging/docker-compose.logging.yml` los configs viven en `../config/` (→ `infra/docker/config/`), no `../../config/`. Si el source no existe, Docker crea un DIRECTORIO fantasma en el host — borrarlo y corregir la ruta.
- **`SHUFFLE_DEFAULT_APIKEY` queda horneada en el env de `shuffle-backend`**: el contenedor la recibe como variable de entorno al crearse — editar `.env` no la actualiza. Si la key rota (reset, `update_env_from_webhook.py`), recrear el backend con `docker compose ... up -d shuffle-backend`. Síntoma de key stale: el webhook sigue admitiendo (valida contra su propia config) pero las llamadas internas de housekeeping y `clean_shuffle_executions.py` devuelven 401 silencioso — los aborts no se aplican y las ejecuciones EXECUTING stale se acumulan.
- **Cortex `GET /api/analyzer` está paginado** (10 por defecto): un worker "desaparecido" puede estar en la página 2. Para comprobar presencia usar `POST /api/analyzer/_search` con `{"query": {}, "range": "all"}` o resolver por `workerDefinitionId`.
- **Cortex analyzers con required-config no credencial** (p.ej. `FileInfo_8_0` exige `manalyze_enable`, boolean con `defaultValue: false`): el filtro de "free analyzers" de `setup_analyzers_and_iocs.py` los descartaba → el worker nunca se instalaba y los tests que lo invocan por `workerDefinitionId` daban 404. `FORCE_INSTALL_IDS` en el script fuerza su instalación con los defaults declarados. Si falta un analyzer tras reset: `POST /api/organization/analyzer/{definition_id}` con `name` + `configuration` incluyendo los required items.
- **Runner detached para suites largas**: `docker exec -d` puede morir silenciosamente en Windows; el patrón fiable es `docker exec soar_api sh -c "nohup sh runner.sh > /tmp/log 2>&1 &"` — el exec retorna al instante y el proceso queda desvinculado del ciclo de vida del exec. Ojo: un proceso cuyo stdout/stderr apunta a un pipe muerto (p.ej. `| head` que ya terminó) recibe SIGPIPE al escribir — redirigir siempre a fichero.
- **`SHUFFLE_DEFAULT_APIKEY` puede quedar stale** tras reset/regeneración: el webhook sigue funcionando (la auth va en la URL del hook) pero `GET /api/v1/workflows` devuelve 401 → `clean_shuffle_executions.py` solo puede hacer la mitad ES-directa del cleanup. La key fresca se obtiene desde la UI de Shuffle o el bootstrap.
- **Workflow def cacheada por el backend**: Shuffle cachea la definición del workflow en memoria — parchear el doc en OpenSearch (`workflow`/`workflow_revisions`) NO afecta a ejecuciones nuevas hasta `docker restart soar_shuffle_backend`. Síntoma: el script embebido actualizado no corre (campos nuevos ausentes del result). Además, el `PUT /api/v1/workflows/{id}` del API rechaza el objeto persistido (HTTP 400) → parchear directamente en OpenSearch es la vía que funciona.
- **`docker restart` no re-interpola vars de compose**: `API_DOCS_ENABLED=true` en `.env` solo entra al proceso vía `docker compose -p soar ... --env-file .env up -d api` (recreate). Ojo: `-p` debe ser `soar` — un project name erróneo crea contenedores duplicados `soarransomwarelab_*` que además chocan en puertos publicados.
- **Warmapp orphans (bug corregido)**: los `warmapp-*` no llevan labels → el zombiecheck de orborus los ignoraba (patch 0004 cambió `baseString` a `__NO_MATCH__`) → workers force-killed/abortados dejaban warmapps vivos sin límite. Fix: orborus `0009-warmapp-orphan-sweep.patch` — reapa `warmapp-*` cuyo `worker-<execid>` ya no existe. Si acumulan `docker ps -a --filter name=warmapp`, rebuild de la imagen orborus.
- **MISP seeds de IOCs**: `tests/e2e` verifica que los IOCs "conocidos-maliciosos" existen en MISP — los siembra `scripts/setup/setup_analyzers_and_iocs.py` (evento `SOAR Lab - Ransomware IOCs (malicious)`), NO el workflow (`misp_create` solo escribe sha256+ip-dst). Si se añade un tipo de IOC a `ioc_samples.json`, hay que añadir su atributo al seeder (faltó `mail`/`email-src` → fallaba group_3).
- **MISP es HTTPS-only**: `localhost:8083` habla TLS con cert self-signed — HTTP plano recibe nginx `400` (sin redirect). Clientes/probes host-side deben usar `https://` (y `verify_ssl=False` o contexto no verificado).
- **`docs-site` bajo hardened**: necesita `read_only:true` + tmpfs en `/opt/docusaurus/.docusaurus` y `/opt/docusaurus/node_modules/.cache` (el dev server Docusaurus escribe cache al arrancar — sin tmpfs muere con `ENOENT mkdir`). Además `limits.memory` debe ser ≥2G (webpack dev compile supera 512M → SIGKILL/OOM en rutas pesadas; las páginas flapean `ERR_EMPTY_RESPONSE`). La imagen debe reconstruirse para aplicar el pin `node:22-alpine` — `node:lts` (v26) rompe Docusaurus 3.10 con `ENOENT mkdir '.docusaurus'`.
- **Imágenes stale tras cambiar Dockerfile**: `docker compose up` NO reconstruye — si el Dockerfile cambia (p.ej. pin de versión), hay que `docker build`/`make build-*` explícito o el contenedor corre la imagen antigua indefinidamente (docs-site corrió Node 26 con el pin a 22 ya commiteado).
- **Restarts de servicios**: `docker start` tarda minutos en quedar healthy (JVM de Cortex, MISP el más lento — `misp_restart`=600 s en `tests/e2e/base/timeouts.py`). Ventanas de 60 s son insuficientes.
- **Healthchecks `localhost` vs IPv6**: en imágenes alpine donde el servidor bindea solo IPv4 (`0.0.0.0:PORT`), `wget/curl http://localhost:PORT` falla con "connection refused" porque `localhost` resuelve a `::1` — el contenedor queda `unhealthy` aunque sirva tráfico real. Usar `127.0.0.1` explícito en el healthcheck (bug real en docs-site estático).
- **Coverage gate en tests parciales**: el `pytest.ini` raíz inyecta `--cov` con `fail_under=80` — cualquier corrida de un solo fichero (lint, oráculo) falla por cobertura aunque los tests pasen. Usar `make e2e-lint` o añadir `--no-cov` a corridas parciales (convención ya usada en el Makefile).
- **Analyzer residue (DinD)**: los analyzers de Cortex dejan contenedores `exited` con nombres aleatorios que nunca se auto-eliminan (`container prune until=1h` no los alcanza bajo carga continua). Orborus patch `0010-analyzer-residue-sweep` los reapa por namespace de imagen (`thehive-project/*`, `cortexneurons/*`) en cada zombiecheck.
- **Self-match en queries LogQL de errores (BUG-GRAF-13/14)**: Loki/Promtail loguean el *texto literal* de las queries → un `|~ "(?i)error|exception|traceback"` sin filtro de dominio se matchea a sí mismo (medido: 2982 hits de `loki` vs 0 de `api` en 30m, 92% ruido). Toda query de errores/logs debe excluir el stack de observabilidad con `compose_service!~"loki|grafana.*|prometheus|cadvisor|tempo|otel-collector|promtail"` o usar la variable `$service` del dashboard logs. Guardas: `scripts/quality/validate_dashboards.py` (estático) + TC-35 `test_error_query_excludes_observability_stack` (E2E).
- **Dashboard legacy eliminado (GRAF-011/012)**: `grafana-dashboard-soar-kpis.json` (formato export, nunca se provisionaba) fue borrado — la fuente única de verdad de cada dashboard es `infra/docker/compose/logging/<nombre>-dashboard.json`. TC-KPI-02 usa `kpi-dashboard.json` como fallback de import.
- **Alert rules con contrato operativo**: toda regla en `alert-rules.yml` lleva `labels.severity` (critical/warning/info), `labels.team: soar-ops` y `annotations.runbook` → `docs/20-observability-runbooks.md#RB-NN`. Cuidado YAML: un `summary:` que empiece por `>` rompe el parse (entrecomillar).
- **ES disk watermark**: el filesystem de datos de Elasticsearch se observó al ~94% usado (6% libre) — panel "ES disk / heap pressure" en `soar-saturation`. <10% libre activa watermarks (85/90/95%) → índices read-only. Liberar con `docker system prune` o borrando índices prescindibles.
- **`$__interval` sí se interpola en render** (a diferencia de `$__rate_interval`) — resuelto client-side antes del dispatch. Y `${__from:date:seconds}`/`${__to:date:seconds}` SÍ se interpolan dentro de `urlPath` del JSON datasource (la tabla de trazas respeta el rango global).

## Observability stack checklist (GRAF-043)

Al tocar dashboards/alertas/datasources del stack Grafana:

1. **Editar** `infra/docker/compose/logging/*-dashboard.json` — bump `"version"` (el provisioner es version-gated) y añadir `description` a cada panel nuevo.
2. **Queries de logs** deben llevar el filtro de dominio canónico `compose_service!~"loki|grafana.*|prometheus|cadvisor|tempo|otel-collector|promtail"` (o la variable `$service` — no introducir regex duplicadas nuevas).
3. **Validación estática**: `python scripts/quality/validate_dashboards.py` → 0 violations.
4. **Reglas nuevas**: `labels.severity` + `labels.team: soar-ops` + `annotations.runbook` apuntando a `docs/20-observability-runbooks.md`.
5. **Recreate**: `docker compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full up -d --force-recreate grafana`.
6. **E2E**: `pytest tests/e2e/TC-35` (17 tests: render de TODOS los paneles, targets, ES exporter, reglas, anti-self-match, p99, descripciones).
7. **Criterio de panel nuevo** (GRAF-DoD): cada panel debe responder una pregunta operativa concreta — no añadir paneles por volumen.

### SLOs del pipeline (GRAF-061)

| Señal | SLO lab | Alerta asociada |
|-------|---------|-----------------|
| Error log rate (app, dominio filtrado) | < 20 líneas/5m | `soar_high_error_log_rate` |
| DLQ depth | 0 mensajes | `soar_dlq_not_empty` |
| Stream consumer lag | < 50 msgs sostenido | `soar_stream_lag_high` |
| ES cluster health | green | `es_cluster_red` |
| Span latency p99 (spanmetrics) | < 1 s | panel sat-20 (sin alerta: lab) |
| Loki ingest | > 0 con servicios vivos | `soar_loki_ingest_stalled` |
