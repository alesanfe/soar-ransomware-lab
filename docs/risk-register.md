# Registro formal de riesgos aceptados (GOV-004)

> Cada entrada: impacto, probabilidad, controles compensatorios,
> responsable, fecha de aceptación, expiración y condición de cierre.
> Un riesgo aceptado **no está resuelto** — se revisa en su fecha de
> expiración.

## R-01 — OpenSearch + Dashboards sin autenticación

- **Componente**: `opensearch` (`plugins.security.disabled=true`),
  `opensearch-dashboards` (`DISABLE_SECURITY_DASHBOARDS_PLUGIN=true`).
- **Impacto**: Alto (lectura/escritura/borrado de índices por cualquier
  proceso que alcance el puerto).
- **Probabilidad**: Baja-media (solo red local del laboratorio).
- **Controles compensatorios** (aplicados 2026-11-08, TH-002/OSD-002):
  - Puertos publicados **solo en 127.0.0.1** (8201, 8202 — verificado
    con `docker ps`: todos los UIs y datastores en loopback; solo el
    edge nginx 80/443 y las ingestas del lab 1514/5160/15130/15160
    quedan en 0.0.0.0).
  - Stack en host de desarrollo personal, sin exposición externa.
  - Datos de laboratorio sintéticos (simulador), sin PII real.
  - Shuffle backend ya usa basic-auth (`admin`/secret) — el plugin es
    compatible si se activa en el futuro.
- **Responsable**: owner del repo.
- **Aceptado**: 2026-11-08 (ADR-0012). **Expira**: 2027-02-08.
- **Cierre**: activar OpenSearch Security (TLS interno + internal
  users) o frontar Dashboards con proxy autenticado (OSD-001).

## R-02 — TLS autofirmado en MISP — **CERRADO 2026-11-08**

- **Componente**: `misp` (`https://localhost:8083`).
- **Resolución**: PKI interna implementada (MISP-001). CA propia
  (`infra/docker/config/certs/ca.crt`, `CA:TRUE` + `keyCertSign`),
  certificado de servidor firmado con SANs `misp`/`localhost`/`127.0.0.1`
  y keyUsage `digitalSignature`+`keyEncipherment`. La CA se monta en el
  API (`/app/certs/ca.crt`, base y hardened overlay) y
  `health_check.py`/clientes verifican contra ella (`verify=ca.crt`,
  OpenSSL `Verify return code: 0`, fetch in-container HTTP 200).
- **Nota**: el error `CERT_TRUST_REVOCATION_STATUS_UNKNOWN` en Windows
  es comportamiento de Schannel con CAs internas offline — no indica un
  certificado inválido (verificado con OpenSSL e in-container).

## R-03 — TheHive 3.5.2 EOL — **CERRADO 2026-11-08**

- **Componente**: `thehive`.
- **Resolución**: migración completa a **TheHive 5.7.8-1**
  (`strangebee/thehive`, TH-001). Almacenamiento embebido
  JanusGraph/BerkeleyJE + Lucene — la dependencia de Elasticsearch y el
  índice `the_hive_17` ya no existen. `TheHiveClient` opera 100% sobre
  `/api/v1` (Query API para listados/filtros), el workflow Shuffle usa
  estados TH5 (`New`/`InProgress`/`FalsePositive` verificados E2E), el
  conector Cortex reporta `status: OK`, y el bootstrap
  (`init_thehive.py`) es idempotente (renueva la key solo cuando la
  actual no valida y la sincroniza a `.env`/`.env.full`/`.env.container`
  vía `/app/runtime/results/`).

## R-04 — Shuffle "unlicensed" y credenciales por defecto

- **Componente**: `shuffle-frontend`/`shuffle-backend` 2.2.1.
- **Impacto**: Medio (funciones enterprise ausentes; cuenta `admin`
  con password generado pero de valor por defecto si no se rota).
- **Probabilidad**: Baja.
- **Controles**: password provisionado desde `.env.full` (32 chars,
  aleatorio por instalación); puerto solo 127.0.0.1.
- **Responsable**: owner del repo.
- **Aceptado**: 2026-11-08. **Expira**: 2027-02-08.
- **Cierre**: n/a (limitación de la edición community; documentar
  alcance en UI).

## R-05 — Dependencias npm del docs-site con vulnerabilidades

- **Componente**: toolchain de build Docusaurus 3.10.2 (última
  versión publicada a 2026-11-08). Tras `npm audit fix`:
  **27 restantes** (3 low, 8 moderate, 1 high, 15 critical) — antes 41.
  Paquetes transitivos: `tinypool` (RCE por prototype pollution en
  opciones de worker), `serialize-javascript` (RCE/XSS vía
  `copy-webpack-plugin`/`css-minimizer-webpack-plugin`),
  `deepmerge` (prototype poisoning vía `@svgr/*`),
  `uuid`/`webpack-dev-server`/`sockjs`, `qs`/`express`.
- **Explotabilidad**: **nula en producción**. Todos los paquetes
  afectados solo existen en el stage de *build* (`node:22-alpine`,
  `npm ci && npm run build`). La imagen publicada es
  `nginx:1.27-alpine` sirviendo HTML/CSS/JS estático — Node, webpack,
  tinypool y demás **no están presentes en la imagen final**
  (verificado: `docker run soar-docs-site sh -c 'which node'` →
  ausente). Las vulnerabilidades requieren input hostil durante el
  build (procesamiento de assets/SVG/código), superficie que solo
  existe si el propio repositorio o la cadena de dependencias estuviera
  comprometida — mitigado por `package-lock.json` anclado + `npm ci`
  (instalación determinista).
- **Impacto**: Bajo (confidencialidad/integridad del build).
- **Probabilidad**: Muy baja (build de contenido propio, CI o host de
  desarrollo).
- **Controles compensatorios**:
  - Multistage: deps de build nunca llegan a runtime (DOCS-001).
  - `npm ci` con lockfile congelado (sin resolución flotante).
  - Sin secrets ni datos sensibles en el contexto de build
    (`.dockerignore` restringido).
  - Runtime nginx hardened: `read_only`, `no-new-privileges`, tmpfs.
- **Responsable**: owner del repo.
- **Aceptado**: 2026-11-08 (DOCS-003). **Expira**: al publicarse
  `@docusaurus/*` > 3.10.2 con fixes upstream — revisar mensualmente
  (`npm audit` en CI).
- **Cierre**: `npm audit` ≤ vulnerabilidades no explotables
  justificadas; auto-cierre al actualizar Docusaurus cuando upstream
  parchee `tinypool`/`serialize-javascript`.

## Revisión

| Riesgo | Próxima revisión |
| --- | --- |
| R-01..R-04 | 2027-02-08 (trimestral) |
| R-05 | Tras DOCS-003 |
