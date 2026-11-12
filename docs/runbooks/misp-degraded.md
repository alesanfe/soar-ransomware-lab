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
OOM en workers, redis sin TLS (`REDIS_HOST` debe ser `tls://redis`), o
corrupción de `cake` jobs tras un stop abrupto.

Desde MISP-EVAL-007, `misp-db` y `misp-modules` están en `misp_internal`,
no en `soar_net`. Desde `soar_api` deben aparecer como no resolubles; desde
`soar_misp` sí deben resolver:

```bash
docker exec soar_misp getent hosts misp-db misp-modules
docker exec soar_api python -c "import socket; socket.gethostbyname('misp-db')"  # debe fallar
```

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
docker exec soar_api curl --cacert /app/certs/ca.crt https://misp/users/heartbeat  # → 200
# Blackbox probes (Prometheus)
probe_success{instance=~".*misp.*"} == 1
```

## Prevención

- Esperar a `healthcheck` verde antes de lanzar tests de integración.
- `make test-integration` dentro del contenedor — nunca desde el host
  (`.env.full` usa nombres de la red compose).
