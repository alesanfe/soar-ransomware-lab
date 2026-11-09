# Runbook: SQLite `database is locked` / base corrupta

## Síntomas

- `sqlite3.OperationalError: database is locked` inmediato (sin espera).
- Queries lentas o `database disk image is malformed`.
- API 503 en rutas que tocan `alert_repository`.

## Diagnóstico

```bash
# ¿Quién retiene el lock? Con WAL activo (ADR-0006) un writer bloquea a
# otro writer, pero las lecturas pasan.
docker exec soar_api fuser /app/runtime/data/soar_data.db 2>/dev/null || true
docker exec soar_api sqlite3 /app/runtime/data/soar_data.db "PRAGMA integrity_check;"
```

`busy_timeout=5000` ya absorbe contención corta; un lock inmediato
sostenido suele ser: otro proceso con el fichero abierto en modo
incompatible, o una transacción larga sin commit.

## Acción

```bash
# 1. Esperar a que muera la transacción retentora (busy_timeout la cubre);
#    si persiste >30s, reiniciar el proceso que la retiene:
docker restart soar_api

# 2. Si integrity_check falla (fichero corrupto):
docker exec soar_api sqlite3 /app/runtime/data/soar_data.db \
  ".recover" > /tmp/recovered.sql
# reconstruir la DB desde el volcado — DESTRUCTIVO, confirmar con usuario
```

## Prevención (ya aplicada)

- `journal_mode=WAL` — lectores no bloquean al writer.
- `busy_timeout=5000` — espera 5s en vez de fallar al instante.
- `foreign_keys=ON` + índices `idx_alert_*`.
