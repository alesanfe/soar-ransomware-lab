# Perfiles de ejecución — SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
- [2. Alcance](#2-alcance)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 Perfil laboratorio](#31-perfil-laboratorio-defecto)
  - [3.2 Perfil desarrollo](#32-perfil-desarrollo)
  - [3.3 Perfil CI](#33-perfil-ci)
  - [3.4 Perfil hardened](#34-perfil-hardened)
  - [3.5 Requisitos de recursos](#35-requisitos-de-recursos)
  - [3.6 Comandos por perfil](#36-comandos-por-perfil)
- [4. Validación](#4-validación)
- [5. Problemas](#5-problemas)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Definir las diferencias operativas entre los perfiles **laboratorio**,
**desarrollo**, **CI** y **hardened**, qué configuraciones inseguras se
aceptan solo en laboratorio, y cómo activar el endurecimiento.

### 1.2 Contexto

Creado para SOAR-023 tras introducir el overlay
`infra/docker/compose/docker-compose.hardened.yml` y los controles
configurables de API (rate limiting, auth de servicio, Swagger).

## 2. Alcance

### 2.1 Qué cubre

Arranque, configuración, servicios y comandos de cada perfil; requisitos
de CPU/RAM/disco; procedimiento de backup/restore y validación.

### 2.2 Límites

El perfil hardened sigue siendo un laboratorio: no pretende cumplir
requisitos de producción (sin PKI real, sin HA, red compartida).

### 2.3 Dependencias

`make up`, `scripts/setup/preflight_check.py`,
`infra/docker/compose/*.yml`, `.env.full`.

## 3. Contenido principal

### 3.1 Perfil laboratorio (defecto)

Arranque estándar: `make up`.

- Todos los servicios (~23 contenedores): Shuffle, TheHive, Cortex,
  MISP, Elasticsearch, OpenSearch, Redis, Grafana/Loki/Promtail,
  Tenzir, network-watcher, API, docs, web-management, Nginx.
- Servicios con inicialización lenta (esperados tras `make up`):
  **Loki** 30-60 s hasta `/ready` (503 inicial normal), **TheHive** y
  **Cortex** (JVM, varios minutos hasta `healthy`), **MISP** (warmup de
  taxonomías/galaxias). `make health` los muestra en `starting` durante
  ese periodo.
- Configuraciones inseguras **aceptadas deliberadamente**:
  - `docker.sock` en api/cortex/shuffle-backend/orborus/network-watcher/promtail.
  - `seccomp:unconfined` en orborus.
  - `user: root` en api y redis.
  - `SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY=true` (cert autofirmado).
  - Tenzir `--mode=dev`.
  - Swagger habilitado en API y Shuffle.
  - `API_REQUIRE_AUTH=false` (endpoints mutadores abiertos en red lab).
- Uso: TFM, demos, desarrollo de workflows, suite E2E completa.

### 3.2 Perfil desarrollo

Igual que laboratorio, más iteración rápida:

- `src/` y `tests/` van bind-mounted (ya lo están) → cambios de código
  en caliente, solo `docker restart soar_api` para recargar la app.
- `RATE_LIMIT_ENABLED=false` opcional para no throttlar pruebas manuales.
- `LOG_LEVEL=DEBUG` recomendado.

### 3.3 Perfil CI

Sin stack Docker completo: solo suites sin dependencias externas.

```bash
make test-unit            # 1282 tests
make test-atomic          # atomic + architecture
make test-integration     # integration/security/contracts sin externos
make test-smoke           # smoke (markers smoke/requires_docker)
```

Workflow `.github/workflows/ci.yml`: lint + tests + Trivy + TruffleHog +
markdownlint + lychee + contracts OpenAPI.

### 3.4 Perfil hardened

```bash
make up HARDENED=1
```

Añade `docker-compose.hardened.yml` encima de los ficheros base:

| Servicio | Cambio vs lab |
| --- | --- |
| `docker-socket-proxy` | **nuevo** — proxy con whitelist de verbos (CONTAINERS/NETWORKS/INFO/EVENTS/EXEC/POST/PING) |
| api | `user: 1000:1000` (variable `API_UID`/`API_GID`), sin `docker.sock`, `DOCKER_HOST=tcp://docker-socket-proxy:2375` |
| network-watcher | sin `docker.sock`, Docker vía proxy |
| redis | `user: redis` (sin chown de arranque) |
| orborus | `security_opt` reset → perfil seccomp por defecto |
| thehive, cortex | `no-new-privileges:true` |

Variables adicionales recomendadas en `.env`:

```text
API_REQUIRE_AUTH=true            # exige JWT o X-Service-Token en endpoints mutadores
INTERNAL_SERVICE_TOKEN=<hex64>   # ya generado en .env.full
API_DOCS_ENABLED=spec            # openapi.json sí, UI Swagger no
SHUFFLE_SWAGGER_ENABLED=false
SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY=false   # requiere CA confiable para OpenSearch
TENZIR_WEB_MODE=<modo-producción>
```

**Nota sobre TLS/OpenSearch (SOAR-015)**: con `SKIPSSL_VERIFY=false`
hay que montar el CA bundle en shuffle-backend o instalar certificados
firmados; de lo contrario la verificación falla. Procedimiento de
certificados: `make certs` + montar el CA en el servicio (documentar en
`.env` antes de activarlo).

**Nota SOAR-011**: con `API_REQUIRE_AUTH=true` el workflow necesita
enviar `X-Service-Token`; los scripts del workflow ya lo envían si la
variable existe al regenerar (`make init-webhook`).

### 3.5 Requisitos de recursos

| Recurso | Mínimo | Recomendado |
| --- | --- | --- |
| RAM Docker VM | 10 GB | 16 GB |
| Disco libre | 20 GB | 40 GB |
| CPU | 4 cores | 8 cores |

`make preflight` comprueba Docker, Compose, disco, memoria, puertos y
rangos reservados de Hyper-V.

### 3.6 Comandos por perfil

| Acción | Comando |
| --- | --- |
| Preflight | `make preflight` |
| Arranque lab | `make up` |
| Arranque hardened | `make up HARDENED=1` |
| Parada | `make down` |
| Estado | `make ps`, `make health` |
| Logs | `make logs` / `make logs-service s=api` |
| Backup | `make backup` |
| Restore | `make restore` |
| E2E completo | `make test-e2e` (limpia Shuffle + TheHive antes) |
| Externos | `make test-external` / `make test-docker` |
| Escaneo secretos | `make scan-secrets` |

### 3.7 Gestión de secretos y rotación

- **Ficheros**: `.env.full` es el env canónico (con secretos reales del
  laboratorio; en este proyecto académico está versionado a propósito).
  `build_local_env.py` genera `.env` (host) y `.env.container` (subset
  montado en los contenedores) — la API ya no recibe `.env.full` entero.
- **Rotación completa**: `python scripts/setup/generate_secrets.py`
  regenera claves y contraseñas; después `python
  scripts/setup/init_thehive.py` (key de TheHive), `scripts/setup/
  reset_cortex.py` (keys de Cortex) y `make init-webhook` (webhook de
  Shuffle). Los tests leen siempre `.env.full` con `override=True`, así
  que toman las claves frescas automáticamente.
- **Rotación puntual**: editar la variable en `.env.full`, regenerar
  `.env`/`.env.container` con `python scripts/setup/build_local_env.py` y
  `make restart`.
- **Ante una exposición** (p. ej. si el repo se comparte fuera del
  entorno académico): rotar todas las credenciales con el procedimiento
  anterior, `make scan-secrets` para verificar que los valores antiguos
  ya no aparecen en repo/logs/imágenes, y revisar `docker logs` de los
  servicios que imprimían secretos (MISP, shuffle-backend — ver
  `scripts/quality/scan_secrets.py`).
- **Escaneo continuo**: `make scan-secrets` (o
  `python scripts/quality/scan_secrets.py --mode repo|logs|images`)
  cubre repositorio, logs de contenedores `soar_*` y metadatos de
  imágenes. CI ejecuta además trufflehog sobre el repo.

## 4. Validación

### 4.1 Verificación

- `docker compose ... -f docker-compose.hardened.yml config` produce un
  plan válido (verificado: api sin socket, orborus sin seccomp,
  redis user=redis, proxy añadido).
- Tests unitarios del rate limiter y `require_api_auth`: 18/18.

### 4.2 Criterios de aceptación

- Servicios por perfil documentados ✅
- Configuraciones inseguras del lab listadas ✅
- Activación de TLS/non-root/verificación explicada ✅
- Requisitos de recursos ✅
- Comandos de arranque/parada/backup/validación ✅

## 5. Problemas

### 5.1 Limitaciones

- El arranque hardened completo no se ha ejecutado todavía end-to-end
  (el overlay fue validado con `docker compose config`); ejecutar la
  suite E2E en hardened es tarea pendiente.
- `API_REQUIRE_AUTH=true` requiere regenerar el webhook de Shuffle para
  que los nodos HTTP envíen `X-Service-Token`.
- `SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY=false` exige gestión de CA; sin ella
  el backend no arranca contra OpenSearch.

### 5.2 Riesgos o incidencias

- En Linux, `API_UID=1000` puede no tener permisos sobre bind mounts si
  los directorios `runtime/` pertenecen a otro usuario (en Docker
  Desktop/Windows no aplica).
- orborus sin `seccomp:unconfined` puede fallar al spawner workers en
  algunos kernels; si aparece, crear perfil seccomp específico en
  `infra/docker/seccomp/`.

### 5.3 Recomendaciones

- Validar `make up HARDENED=1` + `make test-e2e` en una ventana sin
  ejecuciones activas.
- Mantener `.env.container` regenerado (`make up` lo hace en el paso 3).

## 6. Referencias

- `infra/docker/compose/docker-compose.hardened.yml`
- `docs/04-operations.md`, `docs/07-framework-evaluation.md`
- `AGENTS.md` (pitfalls de Docker Desktop en Windows)
- CIS Docker Benchmark; tecnativa/docker-socket-proxy.

## 7. Manifiesto de perfiles Docker (DK-P0-003)

`make up` levanta el perfil **hardened por defecto** (DK-P0-001). El perfil
relajado exige opt-in explícito: `make up-lab` o `make up LAB=1`, que imprime
una advertencia visible.

| Propiedad | hardened (default) | lab (`up-lab`) |
| --- | --- | --- |
| API user | `${API_UID:-1000}` no-root | root |
| docker.sock en api/network-watcher | No — via `docker-socket-proxy` (verbs whitelist) | Sí, RW |
| docker.sock residual | cortex, shuffle-backend, orborus (workers) + promtail ro — excepciones con caducidad | igual, sin registro |
| API_REQUIRE_AUTH | `true` por defecto; `false` es violación CRITICAL del validador | opt-in |
| seccomp | default de Docker (orborus sin `unconfined`) | orborus `unconfined` |
| pids limit | 24/24 servicios (`deploy.resources.limits.pids`) | ausente |
| cap_drop ALL | api, network-watcher, redis, grafana, grafana-renderer, docs-site, nginx, web-management | ausente |
| no-new-privileges | todos los servicios | solo donde el base lo declara |
| read_only + tmpfs | nginx, docs-site, grafana-renderer, promtail | ausente |
| Uso permitido | defecto, CI, auditoría, demos | SOLO máquina aislada desechable |

Validación fail-closed: `python scripts/setup/validate_compose_security.py
--profile hardened` — excepciones en
`infra/docker/compose/security-exceptions.json` (razón + caducidad;
una excepción caducada vuelve a ser violación). Gate en CI
(`validate-compose` job) + regresión rendered en
`tests/integration/test_compose_rendered.py` (BUG-053) y checks estáticos en
`tests/unit/config/test_compose_security.py`.
