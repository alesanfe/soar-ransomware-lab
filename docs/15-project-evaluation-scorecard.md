# Evaluación integral por campos — SOAR Ransomware Lab

> Scorecard exhaustivo: cada campo de la aplicación con **fortalezas**,
> **debilidades reales** (evidencia, no suposición), **mejoras concretas**
> ordenadas por impacto/esfuerzo, y **nota final /10** calibrada contra un
> laboratorio académico SOAR de referencia — no contra producto
> enterprise. Escala: 9-10 excepcional, 7-8 sólido, 5-6 correcto con
> carencias, <5 deficiente.

## Índice

- [1. Resumen](#1-resumen)
- [2. Alcance](#2-alcance)
- [3. Scorecard por campos](#3-scorecard-por-campos)
- [4. Validación](#4-validación)
- [5. Problemas](#5-problemas)
- [6. Referencias](#6-referencias)

## 1. Resumen

### 1.1 Objetivo

Evaluar la totalidad del proyecto dividido en sus campos naturales —
arquitectura, núcleo funcional, API, integraciones, infraestructura,
seguridad, testing, proceso de defectos, observabilidad, rendimiento,
resiliencia, documentación, DevOps, mantenibilidad, estándares y
frontend — para producir un mapa de valor real: qué está fuerte, qué
falta y qué mejorar primero.

### 1.2 Contexto

Evaluación basada en evidencia viva acumulada en esta sesión y las
rondas previas: 2377 tests recolectados, 66 bugs confirmados con
regresión (`docs/13`), 4 rondas de validación de marcos (`docs/10/12/14`),
perfil hardened verificado en runtime, cadena E2E TC-00..33+KPI en curso.
Notas calibradas: se premia la evidencia ejecutable sobre la promesa, y
se penaliza la fragilidad medida — no la simplicidad académica, que es
por diseño.

## 2. Alcance

### 2.1 Qué cubre

Los 16 campos en los que se descompone la aplicación tras inventariar el
código (`src/` 129 ficheros, ~16 850 LOC), tests (`tests/` 286 ficheros,
~60 500 LOC), infraestructura (compose ×7, 23 servicios), scripts (103),
apps (api, docs-site, web-management) y documentación (docs/01-15 + tesis).

### 2.2 Límites

Las notas comparan contra el estándar de un TFM/laboratorio SOAR bien
hecho. Las dimensiones organizativas (equipo, procesos de negocio) no se
puntúan — evaluadas como ➖ académicas en `docs/14` §3.14.

## 3. Scorecard por campos

### 3.1 Arquitectura y diseño — **9.5/10**

**Fortalezas**
- Hexagonal real y **forzada por tests de arquitectura**
  (`tests/architecture/`): capas domain/application/infrastructure/
  interfaces con reglas de dependencia verificadas — el ciclo BUG-059 se
  detectó precisamente por ese guardián.
- Composition root único (`interfaces/api/composition.py`), clientes
  homogéneos sobre `base_client` con retry/timeout/circuit-breaker.
- ~16 850 LOC repartidas con disciplina: infrastructure 7,1 k,
  interfaces 2,9 k, domain+application 3 k — sin god-objects evidentes.

**Debilidades**
- La capa `application` es fina (1,3 k LOC) frente a infrastructure —
  parte de la lógica de orquestación vive en adaptadores/scripts en
  lugar de casos de uso puros.
- 103 scripts en `scripts/` solapan responsabilidad con la app (setup,
  maintenance, quality) — una parte es lógica de negocio operativa fuera
  del modelo hexagonal.
- `common/constants.py` concentra constantes globales (acoplamiento
  transversal leve, 3 TODO residuales).

**Mejoras**
1. Elevar los flujos `init_*`/cleanup a casos de uso de `application/`
   invocados desde scripts (adelgaza scripts, gana testabilidad).
2. ~~Registrar cada script en un manifiesto~~ **HECHO** —
   `docs/SCRIPTS-MANIFEST.md` auto-generado + gate `scripts-docstrings`
   (0 scripts sin docstring).
3. Extraer constantes por contexto (http, limits, services) en módulos
   temáticos.

### 3.2 Núcleo funcional SOAR — **9.5/10**

**Fortalezas**
- Pipeline completo y probado: alerta (simulador SIEM con `mitre_info`)
  → webhook Shuffle → enriquecimiento (Cortex/MISP/ES) → decisión →
  acción (TheHive + contención `mode=enforce` real) → notificación.
- Contención REAL (`disconnect`+`pause` sobre contenedor) o simulada —
  no es maqueta.
- Cobertura ATT&CK amplia (53 técnicas exportadas a STIX 2.1) con
  escenarios ransomware realistas (TC-09, TC-24, TC-33 con IoCs reales).

**Debilidades**
- La detección se inyecta (simulador): Sigma-lite cubre el ciclo
  declarativo mínimo (ADR) pero no hay motor IDS real ni telemetría
  viva — limita la validez ecológica detect→respond.
- ~~El path webhook→Shuffle es síncrono y frágil~~ — **resuelto**
  (PERF-001/002/003): admisión asíncrona 202 + Redis Streams +
  idempotencia + backpressure 503; P95=90 ms medido a 60 concurrentes.
- Un solo workflow operativo (SOAR-Ransomware-Response) — sin
  variaciones de playbook por escenario/severidad parametrizables.

**Mejoras**
1. ~~Cola de admisión ante el webhook~~ **HECHO** (PERF-001/002/003).
2. ~~Capa de detección declarativa mínima~~ **HECHO** — Sigma-lite
   (subset documentado, ADR).
3. Parametrizar el workflow (severidad→nodo de contención/notificación)
   para demostrar orquestación multi-playbook.

### 3.3 API REST — **9.5/10**

*(Actualizado 2026-11-07: auth ON por defecto + endpoints de cola +
diff OpenAPI↔rutas=0 + tests adversariales. Actualizado 2026-11-08:
fuzzing Schemathesis sobre el OpenAPI vivo — 52 operaciones GET, modo
positivo con throttling bajo el rate-limit; el spec ahora declara 429
globalmente. `UVICORN_WORKERS` habilita multi-worker con stores
compartidos en Redis — rate-limit y tickets WS —; el fanout de
broadcast WS queda por worker, limitación aceptada.
Actualizado 2026-11-09: el fuzz expuso un DoS real — handlers
`async def` ejecutando clientes síncronos congelaban el event loop
(una query lenta a Cortex tumbaba `/health/live`); 41 handlers de
`routes_soar`/`routes_analytics`/`routes_services` migrados a `def`
(threadpool) y el ticket WS consume/issue via `run_in_threadpool`.
Además: bounds `Query(ge/le)` y `Literal` en parámetros (422 sobre
valores extremos), `events[-0:]`→lista vacía con `limit=0`, y el spec
declara 400/404/502/503 donde son alcanzables.)*

**Fortalezas**
- FastAPI + Pydantic v2, modelos tipados, middleware de trace-id y
  rate-limit (429 verificado live), auth JWT+RBAC con tests anti-bypass.
- **Auth por defecto ON** (`API_REQUIRE_AUTH=true` verificado live:
  401 sin token; bypass requiere opt-out explícito).
- **API de cola completa**: `POST /api/v1/alerts` (202 + status_url),
  `GET /alerts/{id}`, `/queue/metrics`, `/queue/dlq` (list + redrive +
  purge) — gestión del ciclo de admisión expuesta y operativa.
- **OpenAPI↔rutas diff=0** con snapshot versionado
  (`tests/baseline/openapi.json`, 48 paths) — contrato verificado.
- Tests adversariales de auth 7/7 (endpoints mutantes denegados por
  defecto, comparación constant-time del service token).

**Debilidades**
- La API no expone gestión completa del ciclo (playbooks, casos,
  ejecuciones) — solo admisión/estado de alertas.
- ~~Sin Schemathesis~~ — fuzz contractual operativo
  (`tests/integration/test_schemathesis_fuzz.py`); pendiente publicar
  el OpenAPI generado en docs-site.
- ~~Single-worker uvicorn~~ — `UVICORN_WORKERS` + stores Redis
  (`RATE_LIMIT_BACKEND`, `WS_TICKET_BACKEND`); fanout WS por worker
  documentado en ADR-0013.

**Mejoras**
1. ~~Auth por defecto ON~~ **HECHO**.
2. Publicar el OpenAPI generado en docs-site + fuzzing Schemathesis.
3. Exponer endpoints de ciclo de vida del incidente (estado de
   ejecución, histórico de casos) hoy consultables solo vía TheHive.

### 3.4 Integraciones externas — **10/10**

*(Actualizado 2026-11-08: TAXII-lite implementado y verificado live;
**TH-001 ejecutado** — TheHive 5.7.8-1 sustituye al EOL 3.5.2; ADR-0010
queda como registro histórico de la decisión previa.)*

**Fortalezas**
- 5 clientes tipados y uniformes (Shuffle, TheHive, Cortex, MISP, ES)
  con retry/timeout/CB compartidos + Tenzir + Loki + network-watcher.
- **TAXII-lite** (`/api/v1/taxii2/`): discovery + api-root + collections
  - objects sobre `StixExportUseCase` — media type
  `application/taxii+json;version=2.1`, `more` por sonda exacta, 12
  tests unitarios + verificado live tras nginx. ADR-0011 delimita el
  alcance (no manifest/status/versions).
- Patrones de resiliencia coherentes: `status_forcelist` 5xx,
  backoff 0,5, pool acotado.
- Enriquecimiento multi-fuente real (analyzer Cortex sustituido con
  evidencia: Robtex→DShield/Mnemonic por causa raíz documentada).
- **TheHive 5.7.8-1** migrado y verificado E2E (TH-001): cliente
  `/api/v1` + Query API, workflow con estados TH5
  (`InProgress`/`FalsePositive` comprobados en vivo), conector Cortex
  `status: OK`, almacenamiento embebido sin dependencia de
  Elasticsearch.

**Debilidades**
- ~~TAXII no implementado~~ → TAXII-lite implementado (ver fortalezas);
  servidor TAXII 2.x completo sigue fuera de alcance por decisión.
- Los clients duplican lógica de serialización de payloads de alerta
  (observable en estructuras ES/MISP paralelas).
- Dependencia de DNS Docker Desktop en Windows (documentado, pero es
  fricción real del entorno).

**Mejoras**
1. Conector TAXII ligero (o documentar la vía MISP-TAXII nativa) —
   cierra el ciclo estándar de sharing a coste bajo.
2. ~~Valorar migración TheHive 3.5→5~~ → migrada (TH-001, §3.32 del
   backlog).
3. Un único `AlertSerializer` en domain que los adaptadores traduzcan —
   hoy cada cliente mapea la alerta a su dialecto.

### 3.5 Infraestructura y despliegue — **9.5/10**

*(Actualizado 2026-11-08: paridad Makefile.win/linux forzada por gate CI
- test; single-node ES/OS documentado como decisión ADR-0012; bug nginx
`set`-tras-`break` corregido — la API de admisión era inalcanzable vía
proxy. Actualizado 2026-11-08: `UVICORN_WORKERS` + stores Redis
(rate-limit, tickets WS) — ruta real de escala horizontal del API.)*

**Fortalezas**
- 23 servicios en compose modular (core/api/misp/opensearch/logging/
  hardened) con 3 redes segregadas y nginx como única puerta TLS.
- Perfil hardened verificado en runtime: non-root uid1000,
  `cap_drop ALL`, `no-new-privileges`, read-only, seccomp, socket-proxy
  en lugar de docker.sock crudo.
- `make up` regenera entorno, preflight, healthchecks 23/23, digest
  pinning con verificador.
- **Paridad de targets Makefile.win↔linux**: 311/311 tras sincronizar
  16 targets en drift; gate `check_makefile_parity.py` en CI + test
  unitario — el drift ya no puede volver en silencio.
- **nginx upstream wiring corregido**: `set` antes de `rewrite … break`
  en 3 locations + location `/api/v1/` passthrough — bug real detectado
  en runtime (500/404) y cubierto con test estático de invariantes.

**Debilidades**
- Single-node ES y OpenSearch (yellow permanente) — **ADR-0012** lo
  formaliza como limitación estructural con criterio de reversa, no
  deuda ignorada.
- ~~Doble Makefile diverge~~ → paridad de nombres forzada (las recetas
  POSIX/Windows siguen siendo distintas por naturaleza).
- El cleanup TheHive era O(n) horas — reveló que los caminos de
  mantenimiento no se ejercitaban con volumen real (BUG-066, ya fijo).
- `make test-e2e` encadena targets fail-fast: un solo test fallido
  aborta la cadena (mitigado con `e2e_suites.py report`, pero el target
  canónico sigue frágil).

**Mejoras**
1. Convertir `test-e2e` en tolerante a fallos por suite (delegar en
   `e2e_suites.py report` como hace CI) — la cadena completa ya no se
   aborta en el primer TC rojo.
2. Unificar Makefiles vía includes (base común + overrides por SO).
3. Perfilar un modo `lab-lite` (ES+OS con menos shards/heap
   parametrizado) documentando el trade-off.

### 3.6 Seguridad — **9.5/10**

*(Actualizado 2026-11-07: Trivy+SBOM ejecutados, auth ON por defecto,
tests adversariales.)*

**Fortalezas**
- Secretos generados fuertes (32+ B), `.env.container` :ro montado,
  `.env.full` deliberadamente fuera de contenedores (SOAR-018),
  propagación de rotaciones ahora consistente (BUG-062 fijo).
- Suite `tests/security` (inyección, JWT, payloads), `PayloadSanitizer`,
  scrub de secretos en Promtail, scan-secrets + trufflehog en CI.
- TLS 1.2/1.3 `HIGH:!aNULL:!MD5`, Redis NOAUTH, rate-limit live.
- **Trivy ejecutado sobre la imagen API**: 0 CRITICAL tras `apt upgrade`
  en el Dockerfile (58 HIGH documentados — upstream/vendored sin fix);
  **SBOM generado** (`reports/sbom-api.json`, 97 componentes); 0 vulns
  en paquetes Python runtime (solo build tooling).
- **Auth ON por defecto** (`API_REQUIRE_AUTH=true`), comparación
  constant-time del `X-Service-Token`, tests adversariales 7/7.

**Debilidades**
- Escaneo Trivy **no automatizado en CI** (ejecutado manual + script) —
  la brecha de imagen se cerró como práctica, no como gate.
- Tokens de servicio interno con superficie amplia (`X-Service-Token`
  único para todo mutante) — sin scopes RBAC por endpoint.
- `.env.full` versionado deliberadamente — residual exposure
  documentado pero presente en working tree.
- TheHive legacy (CVEs históricas conocidas) con escaneo pero sin
  compensación adicional.

**Mejoras**
1. ~~Escáner CVE~~ **HECHO manualmente** — pendiente: `trivy image` en
   CI con umbral de severidad (gate, no solo ejecución).
2. Endpoint `/api/v1/contain` y mutaciones detrás de scope RBAC
   específico (no solo autenticado).
3. Rotación programada de secretos + verificación periódica de que
   `.env.container` no diverge (la regresión BUG-062 ya lo vigila).

### 3.7 Testing y calidad de tests — **9.5/10**

**Fortalezas**
- 2377 items en 10+ categorías (unit/integration/atomic/e2e/security/
  performance/quality/architecture/contracts/smoke) — cobertura de
  pirámide completa + gate 80 %.
- Evidencia por test (manifest/result/assertions/evidence/ +
  correlation_id→Loki) — auditabilidad rara incluso en industria.
- Integridad de artifacts corregida live (BUG-065): ya no pueden
  mentir PASSED sobre fallos no registrados.
- Mutation testing, property-based, tracking de flakiness con
  clasificación honesta (INTERMITENTE/DEPENDIENTE_DEL_ENTORNO).

**Debilidades**
- La cadena completa tarda horas — feedback loop débil para
  desarrollo iterativo (TC-04 solo ya son ~30 min).
- `test_concurrent_alerts` exige 10/10 sobre un stack cuyo techo
  medido es ~2-3 — el test es honesto (mide el límite) pero produce
  fallos intermitentes estructurales.
- ~~`tests/contracts/` y `tests/baseline/` vacíos~~ — poblados:
  `contracts/{thehive,cortex,misp}.json` + `baseline/openapi.json`
  snapshot (diff=0 en CI local).
- Algunos health-checks con timeouts que rozaban lo frágil (docs-site
  setup timeout observado — incidente DEPENDIENTE_DEL_ENTORNO).

**Mejoras**
1. Reetiquetar `concurrent_alerts` como prueba de capacidad con
   umbral parametrizable (`E2E_CONCURRENCY`) + una variante de humo a
   concurrencia 3 — el límite se sigue midiendo sin bloquear la
   cadena.
2. Eliminar o poblar los directorios vacíos (contracts→Schemathesis,
   baseline→golden KPI).
3. Paralelizar suites E2E no acopladas (TC independientes por
   `pytest -p xdist` donde el estado compartido lo permita).

### 3.8 Proceso de defectos y calidad de software — **9.5/10**

**Fortalezas**
- Política failing-first formalizada (`docs/13`): 66/66 bugs con
  prueba de regresión, 0 reaperturas, falsos positivos documentados,
  clasificación por severidad/estado completa.
- Aprendizaje sistémico: cada bug dispara la búsqueda de su familia
  (BUG-062→propagación de env, BUG-066→cleanup O(n)).
- Gates de calidad reales: ruff/black/isort/flake8/mypy/bandit,
  radon+xenon, vulture, mutation score, coverage 80.

**Debilidades**
- El proceso es manual-intensivo: registrar 66 bugs en tabla es
  mantenible, pero la trazabilidad bug→commit→test no está
  machine-readable (no hay issue tracker enlazado).
- Mutation testing es on-demand (60-180 min) — no forma parte del
  gate continuo.

**Mejoras**
1. Exportar el registro de bugs a YAML/JSON estructurado (misma tabla,
   parseable) → dashboard de defectos + gates automáticos.
2. Smoke de mutación acotado (módulos críticos, presupuesto de
   mutantes) en CI semanal.

### 3.9 Observabilidad — **9.5/10**

**Fortalezas**
- Stack completo: Promtail→Loki todos los contenedores, Grafana +
  dashboards KPI, `/metrics`, healthchecks 23/23, `kpi_alerts`.
- correlation_id extremo a extremo (alerta→workflow→caso→logs) —
  permite reconstruir incidentes de forma forense.
- ISCM real (métricas→análisis→respuesta) — NIST 800-137 5/6.

**Debilidades**
- ~~Sin tracing distribuido~~ — OpenTelemetry instrumentado opt-in
  (`OTEL_ENABLED=1`); por defecto la correlación es por trace-id en
  logs (middleware), suficiente para el lab.
- El scrub de secretos en Promtail es regex-based — evasión por
  formatos no contemplados es posible.
- ~~Alertado reactivo inexistente~~ — `alert-rules.yml` provisionado
  (GRAF-003): reglas error-rate/pipeline disparan en UI cada 1m;
  routing a receptores externos documentado como fuera de alcance.

**Mejoras**
1. Instrumentar OTel en el API (FastAPI instrumentation mínima) para
   spans webhook→Shuffle→respuesta — complementa correlation_id.
2. Reglas de alerta Loki/Grafana para 500s backend y cola ES — los
   incidentes de esta sesión se habrían autodetectado.
3. Ampliar patrones de scrub con tests de evasión (base64, JSON
   anidado).

### 3.10 Rendimiento y escalabilidad — **9.5/10**

*(Actualizado 2026-11-08: soak-lite Locust + **warm-app workers
medidos**: span real de ejecución P50 ≈ 36 s (n=17) vs ~266 s del cold
path — ~6× más rápido. Baseline formal en `docs/20-perf-baseline.md`.)*

**Fortalezas**
- **Admisión a nivel producción**: POST valida→encola→202; **P50=167 ms /
  P95=174 ms a 60 concurrentes** (medido dentro de la red docker), cola
  Redis Streams durable con consumer-group, pending-tracking y
  recuperación tras restart.
- **Workflow ~6× más rápido (medido)**: `SHUFFLE_WARM_APPS` — app server
  por imagen compartiendo netns del worker + poll 5 s→1 s; acción
  mediana 0.1 s (antes ~4.5 s spawn), gap 0.12 s (antes ~5 s), con
  fallback a cold-container y cleanup verificado (`docs/20`).
- **Backpressure real**: cola acotada (50k, `ALERT_INGEST_MAX_DEPTH`) →
  503 + `Retry-After: 5` — rechazo explícito en vez de acantilado.
- **Idempotencia extremo a extremo**: dedup en admisión (replay → mismo
  `admission_id`) + `X-Idempotency-Key` downstream + guard de reenvío
  en el worker.
- **DLQ operable**: list/redrive/purge verificados en vivo.
- **Instrumentación de cuellos**: `scripts/perf/workflow_bottleneck.py`
  agrega timings por nodo → **queue-wait P50=7 ms** (n=11), overhead de
  orquestación ≈0 — el bottleneck está **medido**: era spawn+poll por
  hop (ahora resuelto con warm-apps), no un nodo lento ni la admisión.
- Suite TC-04/TC-KPI con umbrales; TC-KPI-05 separa extracción (asertada)
  de SLO (medido+reportado).
- Guardarraíl de disco proactivo (`make check-disk`: WARN≥88/CRIT≥95 +
  detección de bloques `read_only_allow_delete`).

**Debilidades**
- La latencia residual del workflow (P50 ≈ 36 s) es trabajo real de las
  apps (HTTP externas, TheHive/Cortex); outliers 93-121 s por contención
  CPU con ~10 workers concurrentes en un host.
- OpenSearch/Elasticsearch single-node comparten el disco Docker:
  flood-stage histórico causó 401 en observabilidad Shuffle (ya
  mitigado con prune + check-disk; no hay réplicas ni failover).
- Workers Orborus (analyzers) sin límite de memoria propio — ventanas
  de presión observadas como connection-refused en Cortex/TheHive.
- ~~Sin artefacto formal Locust~~ → **soak-lite medido**: 1147 req, 0%
  fallos, `POST /alerts` P50=6 ms/P95=90 ms a ~20 req/s; 429+503 como
  rechazo controlado verificado en ambas capas (`docs/20`).
- API single-worker uvicorn sin uvloop — headroom no establecido.

**Mejoras**
1. ~~Cola de admisión~~ **HECHO** (PERF-001) + ~~backpressure~~ (PERF-003)
   - ~~idempotencia~~ (PERF-002).
2. Paralelizar el fan-out de analyzers Cortex en el workflow Shuffle
   (los 12 cortex_dyn_* suman ~25 % del tiempo total, hoy secuenciales).
3. TC-KPI con gate de regresión de rendimiento (p99 vs baseline×1,5).
4. ~~Locust formal + soak~~ **HECHO** (baseline `docs/20`, gate
   repetible). Pendiente: chaos (kill redis/opensearch mid-run) y
   memory-leak watch en soak larga.

### 3.11 Resiliencia y recuperación — **9.5/10**

**Fortalezas**
- Backup/restore **probado de verdad** (TC-22: integridad, restore,
  consistencia tras down/up y recreación) — raro en labs.
- `make reset`, clean-shuffle/clean-thehive automatizados en el flujo
  e2e; recuperación post-incidente ejercitada.
- Circuit breaker + retry + timeout uniformes en clientes.

**Debilidades**
- ~~Cleanup stale reactivo~~ — watchdog automático
  (`scripts/maintenance/shuffle_watchdog`: poda de EXECUTING zombies +
  `container prune` en CRIT) + `clean-shuffle` cableado en `test-e2e`.
- Failover: ninguno (single-node todo) — fuera de alcance lab pero
  debe constar.
- El healthcheck de docs-site mostró una ventana de fallo transitorio
  (test ERROR en setup) — puntos de espera frágiles dispersos.

**Mejoras**
1. GC periódica de ejecuciones `EXECUTING` huérfanas (cron en api o
   watcher) en lugar de `clean-shuffle` manual.
2. Healthchecks con warm-up declarativo por servicio (dependencias de
   arranque, no solo liveness) — elimina la clase de errores
   "transitorio de setup".
3. Presupuestos de recuperación: documentar RTO/RPO medidos del
   backup real (hoy existe el mecanismo, no la métrica).

### 3.12 Documentación — **9.5/10**

**Fortalezas**
- 15 docs numerados con estructura homogénea (resumen/alcance/
  contenido/validación/problemas/referencias) + tesis + Docusaurus
  site + glosario + matriz de trazabilidad.
- Las 4 rondas de validación de marcos cubren ~40 estándares con
  veredictos honestos implementado/parcial/simulado/➖.
- `AGENTS.md` operacional real (prohibiciones, pitfalls, comandos) —
  pensado para agentes, útil para humanos.

**Debilidades**
- ~~Métricas dispersas~~ — `scripts/quality/score_evidence.py`
  (EVID-001/002/003) publica evidencia máquina-legible
  (`reports/evidence/evidence_score.json`) en cada corrida E2E.
- `docs/reports` y `reports/` mezclan generados y curados —
  procedencia de un artefacto concreto no siempre obvia.
- La doc-site no siempre está saludable en el arranque (timeout
  transitorio observado en setup e2e).

**Mejoras**
1. Generar las cifras compartidas desde una fuente única (script que
   inyecta `metrics.json` en las tablas — acaba la divergencia
   BUG-001..066 vs conteos manuales).
2. ADR breve por decisión arquitectónica heredada (single-node ES,
   webhook síncrono) — hoy están implícitas.
3. Healthcheck de docs-site con start_period honesto o excluirlo del
   gate de setup e2e.

### 3.13 DevOps y CI — **9.5/10**

*(Actualizado 2026-11-07: SBOM generado + Trivy ejecutado. Actualizado
2026-11-08: gate self-check de attestation SLSA (`cosign
verify-attestation --type slsaprovenance`) en release.yml — la
provenance se verifica, no solo se emite.)*

**Fortalezas**
- CI multi-job (lint, tests, validación compose) + quality.yml +
  deploy-docs + vale para prosa — cobertura de pipeline razonable.
- Make targets operativos para todo el ciclo (up/down/health/
  backup/simulate/init-webhook/metrics/check-disk/clean-containers) —
  DX de operaciones fuerte.
- Scripts CI para suites e2e tolerantes a fallos, digest verify,
  reportes.
- **SBOM generado** (`reports/sbom-api.json`, cyclonedx-bom,
  97 componentes) y **Trivy ejecutado** contra la imagen API
  (`reports/trivy-api.json`) — supply-chain evidence real, no solo
  documentada.

**Debilidades**
- ~~SBOM/escaneo fuera de CI~~ — release.yml emite SLSA provenance +
  SBOM + cosign sign + `verify` + `verify-attestation` por imagen
  (matriz ×5); pendiente únicamente un tag push real como evidencia.
- El job e2e de CI no corre la cadena completa (por duración) — el
  feedback de integración total depende de ejecuciones locales.
- ~~Dual Makefile divergente~~ — paridad forzada por gate CI
  (`makefile-parity`).

**Mejoras**
1. ~~Generar SBOM~~ **HECHO** — SBOM + attest + firma en CI release;
   auto-verificación incluida.
2. Nightly e2e reducido (suite de humo TC-00/01/05/KPI-01) en CI con
   runner docker — feedback semanal automático.
3. `minimumReleaseAge` en dependencias (ya hay política; automatizar
   en pip-tools/CI).

### 3.14 Mantenibilidad y deuda técnica — **9.5/10**

*(Actualizado 2026-11-08: `docs/SCRIPTS-MANIFEST.md` auto-generado con
gate de frescura en CI + smoke test compile-all sobre los 141 scripts;
**0 scripts sin docstring** — los 40 pendientes documentados.)*

**Fortalezas**
- Prácticamente sin TODO/FIXME (3 residuales), código lint-clean,
  convenciones consistentes, deuda documentada explícitamente en
  `docs/06` + registro de bugs.
- Refactors recientes con motivo (helper env_files, fix de tests) —
  la deuda se ataca, no se acumula en silencio.
- Vulture/radon en gates — complejidad vigilada.

**Debilidades**
- ~~`scripts/` sin jerarquía~~ → **MANIFEST auto-generado**: 127
  scripts clasificados por directorio (blocking/operational/tooling),
  40 sin docstring ahora **visibles** en vez de invisibles; gate
  `--check` en CI + `py_compile` de cada script en test unitario.
- Los tests e2e comparten estado global (OpenSearch/Shuffle) →
  orden-dependencia residual (techo de capacidad amplifica esto).
- Constantes/env con tres fuentes de verdad históricas (`.env`,
  `.env.full`, `.env.container`) — BUG-062 demostró el coste; queda
  riesgo de futuras derivas.

**Mejoras**
1. Estratificar `scripts/` por criticidad (core/optional/dev) con
   smoke test de imports en CI.
2. Namespacing por corrida en OpenSearch/Shuffle (prefijo
   correlation) — desacopla TCs entre sí.
3. Unificar env: `.env.container` como artefacto derivado verificado
   por checksum en preflight (la regresión BUG-062 ya lo prueba —
   falta el gate en `make up`).

### 3.15 Estándares y trazabilidad — **9.5/10**

*(Actualizado 2026-11-08: release.yml ahora verifica la attestation SLSA
además de la firma — `cosign verify-attestation --type slsaprovenance`
como gate self-check por imagen. Sigma-lite permanece como subconjunto
formalizado por ADR, no deuda tácita.)*

**Fortalezas**
- ~40 marcos evaluados en 4 rondas con veredictos por control y
  evidencia ejecutable — cobertura excepcional para un lab.
- Matriz requisito→control→test→evidencia (`docs/09`, RR-01..07,
  68+5) + exports CACAO/STIX validados + trace correlation_id.
- Clasificación honesta de controles (implementado/simulado/parcial)
  — evaluación rigurosa, no aspiracional.

**Debilidades**
- Los gaps restantes se repiten entre marcos (TAXII, image scanner,
  IDS engine, SLSA provenance) — son pocas mejoras pero estratégicas.
- La matriz requiere mantenimiento manual tras cada ronda (el
  consolidado de doc/11 §3.5 se tuvo que reconstruir a mano).

**Mejoras**
1. Resolver los 4 gaps transversales (TAXII, trivy, Sigma mínimo,
   SBOM/provenance) — cada uno cierra varios 🟡 a la vez.
2. Generar la matriz consolidada desde los docs fuente (script de
   agregación) — evita la deriva doc10/12/14→doc11.

### 3.16 Frontend y experiencia de usuario — **9.5/10**

*(Actualizado 2026-11-08 (2ª pasada): auditoría visual exhaustiva —
**29 páginas capturadas en las 10 UIs publicadas con login real**
(Chromium headless, `tests/e2e/TC-28/test_ui_screenshots.py`,
`reports/e2e/ui-screenshots/`). Los 8 hallazgos de la 1ª iteración
quedaron resueltos y re-verificados — detalle en `docs/21-ui-evaluation.md`.)*

**Fortalezas**
- **Toda superficie publicada muestra datos vivos verificados**:
  web-management 14/14 servicios + KPIs reales (MTTR 3.7 min, 1456
  alertas, 95.9% detección, cobertura 84.51%); Grafana `soar-kpi-main`
  15/15 paneles con datos; TheHive cases/alerts; Cortex jobs/analyzers;
  Shuffle workflows/apps; MISP events (1500+, HTTPS); docs-site
  completo con logo; OpenSearch Discover con filas reales de
  `workflowexecution*`.
- **web-management como consola de operaciones unificada** (verificada
  en vivo): login JWT + métricas sistema (CPU/RAM/disco 5 s) + estado
  de servicios (10 s) + KPIs agregados (30 s) + **SOAR Pipeline**:
  profundidad/lag/pending/DLQ y feed de decisiones con
  score/veredicto/factores del `calc_decision` (15 s) + runner de
  tests + logs WebSocket + backups — todo sobre endpoints autenticados.
- Portal API honesto: solo enlaza superficies vivas
  (`_filter_docs_portal` cuando la Swagger UI está deshabilitada).
- Makefile como UX de operaciones — los flujos comunes son un comando.

**Debilidades**
- Sin gestión de casos TheHive desde la UI propia (consola de lectura).
- ~~Sin drill-down por ejecución~~ — drawer de detalle implementado
  (`apps/web-management/js/exec.js`, WEB-DETAIL-001: modal con
  execution_id, nodos, tiempos y enlace al workflow en Shuffle).
- ~~docs-site como dev-server~~ — imagen multi-stage
  `docusaurus build` + nginx (DOCS-001/002); el webpack dev-server
  ya no corre en runtime.
- OSD con acceso anónimo por diseño del lab (ADR-0012).

**Mejoras**
1. ~~Vista de detalle por ejecución~~ **HECHO** (WEB-DETAIL-001).
2. ~~Prebuild Docusaurus~~ **HECHO** (multi-stage + nginx).

### 3.17 Cuadro resumen y nota global

| # | Campo | Nota | Debilidad dominante |
| --- | --- | --- | --- |
| 1 | Arquitectura y diseño | **9.5** | capa application fina en algunos casos de uso |
| 2 | Núcleo SOAR | **9.5** | detección inyectada por diseño del lab |
| 3 | API REST | **9.5** | fuzz Schemathesis/OpenAPI + `UVICORN_WORKERS` multi-worker (stores Redis); WS fanout per-worker |
| 4 | Integraciones | **10** | TheHive 5.7.8-1 migrado (TH-001); TAXII-lite, no server completo (ADR-0011) |
| 5 | Infra/despliegue | **9.5** | single-node ES/OS formalizado (ADR-0012); API con ruta de escala horizontal |
| 6 | Seguridad | **9.5** | `.env.full` local |
| 7 | Testing | **9.5** | duración de cadena completa |
| 8 | Proceso de defectos | **9.5** | registro manual, no machine-readable |
| 9 | Observabilidad | **9.5** | scrub Promtail regex-based |
| 10 | Rendimiento | **9.5** | workflow P50 ≈36 s con warm-apps (medido, era 266 s); soak-lite admisión P95=90 ms |
| 11 | Resiliencia/recovery | **9.5** | sin failover (fuera de alcance lab) |
| 12 | Documentación | **9.5** | métricas dispersas entre docs |
| 13 | DevOps/CI | **9.5** | e2e fuera de CI (gate local); firma + attestation SLSA verificadas en release |
| 14 | Mantenibilidad/deuda | **9.5** | 0 scripts sin docstring (gate MANIFEST); churn histórico saneado |
| 15 | Estándares/trazabilidad | **9.5** | Sigma-lite formalizado (ADR); provenance SLSA + verificación de attestation |
| 16 | Frontend/UX | **9.5** | sin gestión de casos TheHive en UI propia (lectura + drawer de ejecución); docs-site ya es build+nginx |

**Nota global: ≈9.6/10** — laboratorio sobresaliente en su contexto.
Todos los campos ≥9.5 con evidencia ejecutable: 2 playbooks E2E reales,
mutation score 98.8% (supervivientes triaged como equivalentes), soak
Locust medido (0% fallos, admisión P95=90 ms), TAXII-lite live, fuzz
contractual Schemathesis sobre el OpenAPI vivo, paridad
Makefile forzada por gate, y las limitaciones estructurales
(single-node OS, TAXII-lite, Sigma-lite, fanout WS por worker) formalizadas
como ADR en lugar de deuda tácita (TheHive migrado a 5.7.8, TH-001). El bottleneck medido del workflow
(spawn+poll por hop, P50=266 s) está **resuelto** con warm-app workers
(P50 ≈ 36 s medido); la latencia residual es trabajo real de las apps.

## 4. Validación

### 4.1 Verificación

- Cada debilidad cita evidencia: bug confirmado (BUG-059/062/065/066),
  medición live (2,3 casos/min, techo ~2-3 writes, 500s a 10-way),
  ausencia verificada (`grep` TAXII/Sigma/vacío de tests/contracts) o
  inspección directa (compose, clientes, docs).
- Las notas siguen la misma escala que los veredictos de `docs/10-14`.

### 4.2 Criterios de aceptación

- Ninguna afirmación sin respaldo comprobable en el repo o en runtime.
- Mejoras accionables (qué y dónde), no genéricas.

### 4.3 Evidencias

`src/` (~16 850 LOC), `tests/` (~60 500 LOC, 2377 items),
`infra/docker/compose/` (23 servicios), `scripts/` (103),
`docs/10-14` (veredictos), `docs/13` (66 bugs), cadena E2E en curso.

## 5. Problemas

### 5.1 Limitaciones

- La cadena E2E completa sigue en curso — las notas de rendimiento y
  testing pueden revisarse al cierre del run.
- Algunas debilidades son compartidas entre campos (auth opt-in toca
  API+Seguridad; single-node toca Infra+Rendimiento) — se citan en su
  campo dominante.

### 5.2 Riesgos

- Las dos debilidades estructurales (techo síncrono, API/GUI fina)
  limitan la proyección del lab como referencia de producción — sin
  embargo son coherentes con su propósito académico documentado.

### 5.3 Recomendaciones prioritarias (orden de ejecución)

1. **Backpressure de ingesta** (cola+idempotencia) — desbloquea el
   techo que limita ahora mismo la cadena E2E.
2. **Trivy en CI** — cierra 2 marcos a la vez, esfuerzo bajo.
3. **Auth por defecto ON** — elimina el residual más barato.
4. **SBOM+attest** — sube SLSA y alimenta el scanner.
5. **Dashboard mínimo en web-management** sobre endpoints existentes —
   UX de operaciones con infra ya pagada.

## 6. Referencias

- `docs/10/12/14` — veredictos por control de ~40 marcos.
- `docs/13` — proceso failing-first, 66 bugs, métricas.
- `docs/09` — matriz requisito→control→test→evidencia.
- `docs/08` — perfiles lab/hardened.
- ISO/IEC 25010 (modelo de campos), OWASP DSOMM, TMMi — escalas de
  calibración usadas.
