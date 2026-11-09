# Runbook — Rotación de service tokens sin downtime (S2)

Los tokens `INTERNAL_SERVICE_TOKEN` y `SHUFFLE_WEBHOOK_TOKEN` son
secretos estáticos por entorno. La rotación usa slots `*_PREV` como
ventana de gracia.

## Procedimiento

1. **Generar el secreto nuevo**:
   `python scripts/setup/generate_secrets.py` o `openssl rand -hex 32`.
2. **Copiar el valor actual al slot PREV** en `.env.full`:
   `INTERNAL_SERVICE_TOKEN_PREV=<valor-viejo>`
3. **Poner el nuevo valor** en `INTERNAL_SERVICE_TOKEN`.
4. **Redesplegar**: `make restart` (o recrear `soar_api`).
   - Los callers con el secreto viejo siguen autenticando (gracia) —
     cada uso queda auditado como `rotation-grace` y logueado WARNING.
5. **Migrar callers**: actualizar workflows Shuffle / clientes con el
   token nuevo. Vigilar que los logs dejen de emitir
   `rotation grace in use`.
6. **Limpiar el slot**: borrar `*_PREV` y redesplegar — el secreto
   viejo muere (`401`).

## Mismo procedimiento para el webhook token

`SHUFFLE_WEBHOOK_TOKEN` / `SHUFFLE_WEBHOOK_TOKEN_PREV` — ojo: el token
está embebido en las definiciones de workflow; tras rotar hay que
reinyectar el webhook con `make init-webhook` antes de limpiar el PREV.

## Verificación

`tests/unit/api/test_contain_enforce.py` cubre: PREV aceptado con
flag `rotation-grace`, PREV rechazado cuando el slot está vacío.
