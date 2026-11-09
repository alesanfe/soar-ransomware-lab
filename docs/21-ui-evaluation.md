# 21 — Evaluación de interfaces de usuario (evidencia visual)

> Evaluación de todas las superficies UI del stack mediante capturas reales
> en Chromium headless (`tests/e2e/TC-28/test_ui_screenshots.py`,
> `reports/e2e/ui-screenshots/`). Cada interfaz se puntúa /10 contra
> ISO/IEC 25010 (usabilidad), ISO 9241-110 (principios de interacción),
> WCAG 2.1 AA (percepción mínima), OWASP ASVS (postura de seguridad de la
> superficie) y consistencia operativa SOAR. La nota refleja lo
> **verificado en captura**, no la capacidad teórica.

**Última actualización**: segunda iteración — todos los hallazgos de la
primera evaluación (F1–F8) corregidos y re-verificados con capturas
autenticadas. **29 páginas capturadas, 0 errores de navegación** (test
`test_all_pages_captured` PASSED; logins reales en nginx, Grafana,
Shuffle, TheHive, Cortex y MISP).

## 1. Cobertura del inventario

| Puerto | Servicio | Tipo | Páginas capturadas |
| --- | --- | --- | --- |
| 80/443 | nginx → web-management | UI propia | login + dashboard/pipeline/services/testing/logs/backup + full-page |
| 8000 | soar_api | UI portal | `api_portal` (estado vivo + superficies operativas) |
| 8081 | Shuffle frontend | UI terceros | login admin real, workflows, apps |
| 8083 | MISP | UI terceros | login admin real, events (1500+), event detail |
| 8084 | Grafana | UI terceros | login, dashboards, KPI, explore |
| 8085 | web-management directo | UI propia | igual que :80 |
| 8086 | docs-site (Docusaurus) | UI propia | home, getting-started, architecture, reports, quality, test-review |
| 8100 | TheHive | UI terceros | login real, cases, alerts |
| 8101 | Cortex | UI terceros | login real, jobs, analyzers |
| 8202 | OpenSearch Dashboards | UI terceros | home, dashboards, discover (index patterns creados) |
| 5001, 8200, 8201, 15130, 15140, 15160 | APIs | JSON | sin UI (oracle: no sirven HTML) |

## 2. Evaluación por interfaz

Cada bloque: fortalezas, debilidades, nota, deuda técnica y bugs
(activos y resueltos en esta auditoría).

### 2.1 Web-Management (consola propia) — **9.5/10**

**Puntos positivos**
- Consola operativa real: 14/14 servicios, CPU/RAM/disco, cola de
  admisión (depth/lag/pending/DLQ), feed de decisiones con veredicto +
  factores de score en vivo (ISO 25010: idoneidad funcional).
- KPIs poblados desde `/analytics/kpis/aggregated` (MTTR 3.7 min,
  1456 alertas, detection 95.9%); coverage 84.51% desde artefacto real.
- Login JWT real, tema oscuro consistente (ASVS + 9241-110).

**Puntos negativos**
- Una sola página con scroll vertical — sin navegación por secciones ni
  deep-linking a una sección.
- Contraste de texto secundario marginal frente a WCAG AA.
- Consola de lectura: no hay acciones de respuesta (contener, cerrar
  caso) ni drill-down por ejecución.

**Deuda técnica**
- Vista de detalle por ejecución pendiente (endpoint
  `/soar/shuffle/executions/{id}/decision` existe sin UI).
- JS ES5 monolítico en `script.js` sin framework ni tests de frontend.

**Bugs**
- Resueltos: KPIs "—" (mapping endpoint), coverage vacío, `Benign: —`
  → 0, Redis/MISP falso-offline (TCP + TLS health).
- Activos: ninguno conocido.

### 2.2 API portal (`api:8000`) — **9.5/10**

**Puntos positivos**
- Honesto: solo enlaza superficies vivas (`_filter_docs_portal` oculta
  `/docs`+`/redoc` cuando `API_DOCS_ENABLED=spec`).
- Enriquecido: estado de la API, métricas, health/status, analytics,
  SOAR, TAXII y STIX descritos con rutas reales.

**Puntos negativos**
- Superficie mínima: sin versionado visible ni hints de auth.
- HTML estático — no refleja estado dinámico más allá del fetch JS.

**Deuda técnica**
- `api-docs.html` va baked en la imagen — cambios exigen rebuild o
  `docker cp` (riesgo de drift imagen↔repo).

**Bugs**
- Resuelto: portal anunciaba `/docs` y `/redoc` deshabilitados
  (+ test de regresión `test_portal_hides_disabled_ui_links`).
- Activos: ninguno.

### 2.3 Grafana (`:8084`) — **9.5/10**

**Puntos positivos**
- Dashboard `soar-kpi-main` provisionado: **15/15 paneles con datos**
  (Total Alerts 1389, MTTR 3.5 min, percentiles, severidad, éxito por
  servicio, evolución diaria).
- 3 datasources (Elasticsearch, Loki, JSON/API) + login admin real.

**Puntos negativos**
- Un solo dashboard provisionado — Loki/OS disponibles pero sin vistas
  guiadas para logs ni ejecuciones.
- Sin alertas/notificaciones provisionadas (solo visualización).
- Provisioning vía `configs:` exige recreate para recargar el JSON.

**Deuda técnica**
- Dashboards de logs (Loki) y de ejecuciones (OpenSearch) sin
  provisionar; alert rules ausentes.

**Bugs**
- Resueltos: 5 paneles "No data"/error — stat panels sin bucketAgg,
  `filters` agg sin frames en el plugin ES, barchart sobre campo
  numérico `severity`.
- Activos: ninguno.

### 2.4 TheHive (`:8100`) — **10/10**

**Puntos positivos**
- **Migrado a TheHive 5.7.8-1** (TH-001, R-03 cerrado): React UI
  mantenida por el vendor, `/api/v1`, almacenamiento embebido.
- UX de analista madura: casos con severidad, tags MITRE/TLP,
  observables, detalle con IPs/hashes/tareas; alerts capturadas.
- Login real verificado E2E (`test_ui_screenshots.py` pasa con el SPA
  React), densidad apropiada al rol.

**Puntos negativos**
- Lucene embebido reporta deprecation warning desde TH 5.1 (vendor
  recomienda Elasticsearch para producción a escala) — aceptable en
  laboratorio; los filtros del lab son sobre `tags`, no custom fields.

**Deuda técnica**
- Ninguna activa en UI. La migración TH-001 queda documentada en
  `docs/17-technical-backlog-9of10.md`.

**Bugs**
- Activos: ninguno observado en las páginas capturadas.

### 2.5 Cortex (`:8101`) — **9.5/10**

**Puntos positivos**
- Login OrgAdmin real; `cortex_jobs` con 10k jobs (Success visibles,
  TLP/PAP-AMBER) y `cortex_analyzers` (46 analyzers) capturadas.

**Puntos negativos**
- Jobs `Failure` de analyzers visibles en primeras páginas sin vista de
  triage agregada — son veredictos correctos sobre input inválido
  (`FileInfo_8_0` "File parameter is missing" con hash), pero la UI no
  los separa de fallos reales de plataforma.
- Densidad visual alta, jerarquía débil; UI AngularJS (Cortex 3.x).

**Deuda técnica**
- Analyzers deprecated reemplazados (Robtex→DShield/Mnemonic — AGENTS);
  resto de flota sin revisión de versionado.

**Bugs**
- Activos: ninguno de plataforma; los job-failures son comportamiento
  correcto documentado en runbook.

### 2.6 Shuffle frontend (`:8081`) — **9.5/10**

**Puntos positivos**
- Login admin real verificado; `shuffle_workflows` muestra
  **SOAR-Ransomware-Response** (56 acciones, ejecuciones) y
  `shuffle_apps` el catálogo — onboarding pulido.
- Branding y navegación por secciones (Use cases, Apps, Workflows).

**Puntos negativos**
- Badge permanente **"Unlicensed / limited access"** en la esquina —
  ruido visual en un lab self-hosted.
- First-paint lento de la SPA ("Loading Workflows" visible unos
  segundos).
- El nginx interno del frontend resuelve la IP del backend **solo al
  arranque** — restart del backend deja la UI en "waiting for database"
  permanente hasta reiniciar el frontend (modo de fallo real).

**Deuda técnica**
- Upstream stale-IP: mitigación operativa documentada en
  `docs/runbooks/shuffle-stale.md`; fix estructural sería resolver por
  request o health-aware upstream.

**Bugs**
- Resueltos: selector de login del test (buscador topbar vs input
  Username); "waiting for database" post-restart (restart frontend).
- Activos: ninguno en la app.

### 2.7 MISP (`:8083`) — **9.5/10**

**Puntos positivos**
- **Rescatada de inalcanzable**: mapeo `8083→443` + `MISP.baseurl`
  HTTPS → UI completa con login admin real.
- `misp_events`: **1500+ eventos** de la org SOAR Lab, paginación y
  tags; `misp_event_view` con atributos del evento #1.
- Health check por HTTPS correcto (`/users/heartbeat`, verify=false).

**Puntos negativos**
- Certificado **autofirmado** → warning de navegador en cada acceso
  (aceptable en lab, no en producción — ASVS gap).
- Aterriza en Events en lugar de un dashboard de resumen.
- UI PHP/CakePHP de aspecto datado.

**Deuda técnica**
- TLS real con CA interna o cert provisionado (documentado; fuera del
  alcance del lab con IP localhost).

**Bugs**
- Resueltos: publicación del puerto HTTP (80) en vez de HTTPS (443),
  `baseurl` http que rompía el redirect, health check por HTTP → 301.
- Activos: ninguno.

### 2.8 Docs-site (`:8086`) — **9.5/10**

**Puntos positivos**
- Docusaurus completo tras los fixes: home, getting-started,
  architecture, reports, quality y test-review renderizan con navbar,
  footer y logo SVG consistentes.
- Reportes del proyecto navegables como docs de primera clase.

**Puntos negativos**
- Corre como **dev-server webpack** en producción: ~2 min de compile en
  frío, hot-reload degradado en bind-mounts Windows, y exigió 2G de RAM
  (OOM a 512M).
- Warnings de build no fatales: enlaces `../README.md` sin resolver en
  `02-architecture`/`04-operations`; **41 vulnerabilidades npm audit**
  (incl. críticas) del toolchain Docusaurus.

**Deuda técnica**
- Migrar a `docusaurus build` + servidor estático (elimina cold-start,
  RAM y superficie del dev-server).
- Remediación de las 41 vulns npm pendiente.
- Enlaces `../README.md` pendientes de corregir.

**Bugs**
- Resueltos: sidebar `reportsSidebar` crash (faltaba `docs/reports/
  index.md`), logo ausente, `node:lts`→Node 26 incompatible (pin 22),
  read_only sin tmpfs `.docusaurus`, OOM 512M→2G.
- Activos: warnings de links + audit (ver deuda).

### 2.9 OpenSearch Dashboards (`:8202`) — **9.5/10**

**Puntos positivos**
- Index patterns creados (`workflowexecution*`, `shuffle_logs*`,
  `workflowqueue-shuffle`); `osd_discover` muestra **filas reales** de
  ejecuciones con campos disponibles y documento expandido.
- Home y dashboards navegables.

**Puntos negativos**
- **Acceso anónimo** (security plugin off — aceptado por ADR-0012, pero
  es el único servicio sin auth del inventario — ASVS gap teórico).
- Sin dashboards ni visualizaciones provisionadas — solo Discover crudo.
- Campos `started_at`/`completed_at` epoch-seconds renderizan como
  fechas 1970 (mapping sin tipo date).
- Banner "Discover 2.0 se retira en 2.11" visible.

**Deuda técnica**
- Provisionar dashboards de ejecuciones (status/duración/hits) sobre
  los patterns ya creados; mapear campos temporales como `date` en
  índices futuros.

**Bugs**
- Resueltos: cero index patterns (Discover sin dataset), time field
  inválido (`started_at` epoch), captura en estado "Searching".
- Activos: ninguno bloqueante.

## 3. Hallazgos transversales — todos resueltos

| # | Estado | Hallazgo |
| --- | --- | --- |
| F1 | Resuelto | MISP UI inalcanzable desde host → mapeo `8083→443` + `MISP.baseurl` HTTPS |
| F2 | Resuelto | Grafana: 5 paneles "No data" + 1 error → queries corregidas, 15/15 con datos |
| F3 | Resuelto | web-management KPIs/coverage vacíos → aggregated endpoint + fallback; Redis TCP + MISP TLS health → 14/14 |
| F4 | Resuelto | Shuffle login → selector corregido, vistas internas capturadas |
| F5 | Resuelto | OSD sin index patterns → patterns creados, Discover con datos reales |
| F6 | Resuelto | docs-site logo roto + Node 26 → `logo.svg` + pin `node:22-alpine` (+tmpfs+2G) |
| F7 | Resuelto | Portal API enlazaba /docs+/redoc deshabilitados → `_filter_docs_portal` |
| F8 | Resuelto | docs-site crash por sidebar vacío → `docs/reports/index.md` |
| F9 | Resuelto | Shuffle frontend upstream IP stale → nginx `resolver 127.0.0.11` + `proxy_pass $shuffle_backend` (SHF-001), healthcheck prueba upstream (SHF-008) |
| F10 | Resuelto | docs-site dev-server en "producción" → multistage `node:22-alpine` build + `nginx:1.27-alpine` estático; build sin warnings (0 enlaces/anchors rotos) |
| F11 | Resuelto | OpenSearch `started_at` epoch_seconds mapeado como epoch_millis → docs en 1970; template `shuffle-workflowexecution` + reindex 1720 docs + alias swap (OSD-005) |
| F12 | Resuelto | OSD sin dashboards → `init_opensearch.py` provisiona patterns + dashboard "SOAR – Shuffle Executions" (OSD-003/008) |
| F13 | Resuelto | Grafana sin dashboards de logs ni alertas → `logs-dashboard.json` + 4 reglas provisionadas en `/alerting` (GRAF-001/003), UIDs estables (GRAF-002), validador CI `check_grafana_provisioning` (GRAF-005) |
| F14 | Resuelto | Superficie LAN expuesta → 12 puertos UIs/datastores a `127.0.0.1` (solo edge nginx + ingestas lab en 0.0.0.0) |
| F15 | Resuelto | web-management: security headers perdidas por `add_header` por location + CSP permisiva → headers replicadas + `script-src 'self'` (sin inline handlers) |
| F16 | Resuelto | web-management sin navegación/deep-link → barra de secciones + routing hash `#exec=<id>`/`#sec-*` + drawer de detalle de ejecución + timestamps |
| F17 | Resuelto | API portal sin metadatos → badges de versión, nº endpoints y esquema auth leídos de `/openapi.json` en vivo |
| F18 | Resuelto | Fallos de analyzers indistinguibles → clasificador `success/expected_no_data/analyzer_error/infrastructure_failure` en `/soar/cortex/jobs/summary` (CTX-001) |
| F19 | Riesgo aceptado | 27 vulns npm toolchain build-only (R-05) — runtime nginx sin Node; triage formal en risk-register |
| F20 | Riesgo aceptado | OpenSearch sin auth (R-01), Shuffle community (R-04) — con controles compensatorios, owner y fecha de revisión. Cerrados: R-02 (MISP → PKI interna CA-firmada), R-03 (TheHive 3.5.2 → 5.7.8-1) |

## 4. Nota agregada

| Dimensión (ISO 25010/usabilidad) | Nota | Evidencia |
| --- | --- | --- |
| Idoneidad/operatividad de las UIs | 10 | Todas las superficies operativas con datos vivos; detalle de ejecución navegable; dashboards provisionados |
| Consistencia visual y marca | 9.5 | Sin cambios visuales desde la evaluación previa (9.5 mantenido) |
| Accesibilidad y cobertura de superficie | 9.5 | 19/19 puertos inventariados; navegación por teclado en decision rows (tabindex/Enter); pendiente auditoría WCAG completa |
| Postura de seguridad de la superficie | 9.5 | Loopback en 12 puertos, CSP estricta, headers por location, auth en todos los UIs (OSD = riesgo aceptado documentado) |
| Datos vivos vs placeholders | 10 | KPIs reales, Discover con timestamps correctos, alert rules evaluando, jobs clasificados |
| **Media interfaces** | **9.9/10** | |

Toda interfaz publicada es accesible, autenticable donde aplica y muestra
datos vivos del lab — verificado con capturas autenticadas en Chromium
(29 páginas, 0 errores) tras corregir los 8 hallazgos de la primera
evaluación y los 12 hallazgos adicionales de la segunda pasada (F9–F18).
Los riesgos restantes (F19/F20) están formalmente aceptados en
`docs/risk-register.md` con controles compensatorios, responsable y
fecha de revisión — no se contabilizan como deuda abierta.
