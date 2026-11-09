# ADR-0010: TheHive 3.5.2 legacy — riesgo aceptado y acotado

**Estado**: **Superseded** (2026-11-08, TH-001) · La migración se
ejecutó: `strangebee/thehive:5.7.8-1` con almacenamiento embebido
(JanusGraph/BerkeleyJE + Lucene — sin Cassandra ni Elasticsearch),
cliente reescrito a `/api/v1` + Query API y bootstrap idempotente
(org `soar` + `analyst@soar.local`). Ver §3.32 de
`docs/17-technical-backlog-9of10.md`. Este documento permanece como
registro histórico de la decisión previa.

**Estado original**: Aceptado · **Evidencia**: stack verificado E2E (TC-01, 336 s)
con `soar_thehive` 3.5.2; CVEs de la línea 3.x documentadas abajo.

## Contexto

TheHive 3.5.2 (2019/2020) es la última release de la línea 3.x, fuera de
soporte desde hace años. TheHive 5.x es incompatible a nivel de API
(modelo de alertas/casos reescrito, `thehive4py` ≠ `thehive5py`) y exige
Elasticsearch 7.x + Cassandra + storage de ficheros — un salto de stack,
no de versión.

El laboratorio depende de la API REST 3.x en dos superficies:

- `infrastructure/integrations/thehive/client.py` — creación de casos.
- `scripts/setup/init_thehive.py` — API key + org admin.

## Decisión

**Permanecer en 3.5.2 y aceptar el riesgo explícitamente**, con las
cotas siguientes:

1. **Riesgo contenido por diseño de red**: TheHive no está expuesto al
   host salvo a través del proxy nginx (443) y la red `ti_net` es
   interna; en un entorno de laboratorio aislado el impacto de CVEs
   web de 3.x queda dentro del perímetro del lab.
2. **La deuda está contabilizada, no ignorada**: queda registrada aquí
   como decisión consciente con criterio de reversa.
3. **Criterio de migración**: migrar a TheHive 5.x cuando (a) se
   necesite el modelo de alertas→observables→casos de v5, (b) el lab
   pase a un entorno no aislado, o (c) se adopte `thehive4py` en modo
   compat (v5 lo soporta parcialmente). El punto de cambio es
   `thehive/client.py` — un solo adaptador.

## Consecuencias

- CVEs conocidas de la línea 3.x (XSS en UI, SSRF en webhooks,
  auth-bypass en endpoints legados) permanecen — mitigadas por el
  aislamiento de red y el uso exclusivamente programático vía API key.
- El scorecard de seguridad descuenta el riesgo en el campo 4
  (integraciones), no lo oculta.
- `THEHIVE_API_KEY` se regenera por reset — el runbook
  `docs/04-operations.md` documenta el flujo.

## Alternativas descartadas

- **TheHive 5.x ahora**: requiere Cassandra + S3/FS storage + nueva
  librería cliente; ~3 servicios nuevos y reescritura del adaptador por
  un beneficio que el lab no ejercita (colaboración multi-analista,
  taxonomías v5).
- **Otro case manager** (DFIR-IRIS, RTIR): rompería la trazabilidad
  académica TheHive+Cortex — la pareja es el estándar de facto que el
  lab estudia.
