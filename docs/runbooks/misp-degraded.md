# Runbook: MISP devuelve 500 / workers en FATAL

**Caso real observado (2026-11-06)**: `POST /events` → 500, `health: False`
con `prio_03`, `prio_04` y `scheduler_00` en estado FATAL de supervisord.

## Síntomas

- `MISPClient` → `IntegrationError [MISPClient] 500 Server Error`.
- `/users/heartbeat` puede responder aunque el backend esté roto.
- `docker logs soar_misp` → `exited: prio_0X (exit status 1; not expected)`
  → `entered FATAL state, too many start retries`.

## Diagnóstico

```bash
docker logs soar_misp 2>&1 | grep -iE "fatal|error|traceback" | tail -30
docker exec soar_misp supervisorctl status
docker exec soar_misp tail -50 /var/www/MISP/app/tmp/logs/error.log
```

Causas frecuentes: primera inicialización incompleta (DB migrations),
OOM en workers, o corrupción de `cake` jobs tras un stop abrupto.

## Acción

```bash
# 1. Restart blando (conserva volúmenes) — el caso observado NO se
#    recuperó en <60s; MISP tarda varios minutos en boot completo.
docker restart soar_misp
sleep 120

# 2. Si persiste FATAL: logs del worker concreto
docker exec soar_misp supervisorctl tail prio_03 stderr

# 3. Reset del servicio (destructivo para datos de MISP):
#    pedir confirmación al usuario antes de borrar el volumen.
```

## Verificación

```bash
docker exec soar_api python -c "…MISPClient.health_check()"   # → True
docker exec soar_api curl -sk https://misp/users/login | head
```

## Prevención

- Esperar a `healthcheck` verde antes de lanzar tests de integración.
- `make test-integration` dentro del contenedor — nunca desde el host
  (`.env.full` usa nombres de la red compose).
