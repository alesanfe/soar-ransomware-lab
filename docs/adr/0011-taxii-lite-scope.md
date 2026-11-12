# ADR-0011: TAXII-lite — superficie read-only mínima sobre STIX

**Estado**: Aceptado · **Evidencia**: `application/use_cases/taxii_server.py`,
`interfaces/api/routes_taxii.py`, `tests/unit/application/test_taxii_server.py`
(12 tests), endpoints live verificados.

## Contexto

NIST SP 800-150 (cyber threat information sharing) nombra STIX/TAXII como
la pareja de intercambio de referencia. El lab ya exportaba STIX 2.1
(`/api/v1/stix/bundle`) pero carecía de la superficie TAXII que permite a
un consumidor estándar (MISP TAXII pull, cabby, taxii2-client) descubrir y
descargar los objetos.

Un servidor TAXII 2.1 completo exige: colecciones con ACL, recurso
`manifest`, recurso `status` (ingestas asíncronas), `versions` por objeto,
paginación por envelopes con cursores, y media-type negotiation estricta.

## Decisión

Implementar **TAXII-lite**: la porción read-only del protocolo que un
cliente TAXII 2.1 puede consumir sin adaptación:

- `GET /api/v1/taxii2/` — discovery (`api_roots`, `default`).
- `GET /api/v1/taxii2/api/` — API root (`versions: [taxii-2.1]`).
- `GET /api/v1/taxii2/api/collections/` + `/{id}/` — colección única
  `lab-alerts` (uuid5 determinista, `can_read`, `!can_write`).
- `GET .../{id}/objects/` — envelope STIX servido con
  `application/taxii+json;version=2.1`, flag `more` computado por
  sonda exacta (`limit+1`), filtro `match[type]`.
- `GET .../{id}/manifest/` — recurso manifest (spec lo exige en
  colecciones read): entradas `{id, date_added, version, media_type}`
  derivadas de `created`/`modified` de cada objeto.

Todo el contenido proviene de `StixExportUseCase` — una sola fuente de
objetos STIX, cero duplicación de lógica.

## Consecuencias

- Clientes TAXII pueden hacer discovery + pull de indicadores — cierra el
  control NIST 800-150 a nivel "parcial-implementado" con honestidad.
- **No hay** `status`, `versions`, ni write path — `status`/POST solo
  aplican a colecciones `can_write` según la spec; `versions` no aplica
  porque los objetos son deterministas (uuid5) e inmutables por id.
- La colección es una vista materializada del corpus (stateless) — sin
  cursores; `limit` es un bound simple, no paginación real.

## Alternativas descartadas

- **medallion/taxii2server completo**: añade un servidor WSGI externo,
  backend Mongo, y ACLs propias — sobreingeniería para un corpus que ya
  vive en el repositorio SQLite del lab.
- **Solo STIX file-export** (status quo): no satisface el patrón pull de
  NIST 800-150 ni cierra el gap del scorecard de integraciones.
