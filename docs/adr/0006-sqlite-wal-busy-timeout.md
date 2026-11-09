# ADR-0006: SQLite con WAL + busy_timeout + FK + índices

**Estado**: Aceptado · **Evidencia**: BUG-116 (EPIC-2)

## Contexto

17 `sqlite3.connect` crudos: journal en rollback mode, `busy_timeout=0`
(→ `database is locked` instantáneo bajo cualquier concurrencia), sin
foreign keys y cero índices sobre `alerts`.

## Decisión

`_connect()` único en `sqlite_alert_repository.py` aplica
`PRAGMA journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON`;
índices `idx_alert_{timestamp,status,severity}`. SQLite (no Postgres) por
simplicidad operativa del lab: fichero embebido, backup trivial, sin
servicio extra que operar.

## Consecuencias

- Lecturas concurrentes no bloquean al writer (WAL); escrituras esperan
  5s en vez de fallar al instante.
- Migraciones reales (Alembic/propio) quedan en backlog (P8) — el
  `CREATE TABLE IF NOT EXISTS` actual no versiona esquema.
- Revertido deliberadamente `CHECK(severity BETWEEN 1 AND 4)`: la columna
  es `TEXT` con vocabulario legacy ("high"/"critical") en tests y callers;
  enforcement en persistencia era la capa equivocada. La canonicalización
  1-4 vive en dominio/ingesta.
