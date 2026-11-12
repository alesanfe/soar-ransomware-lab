# Runbook: Tenzir ingest stalled

Alerta cubierta: `core_tenzir_ingest_stalled` — sin logs de
`tenzir-node` en Loki durante 10m (proxy de pipeline detenida o proceso
colgado sin crash).

## Diagnóstico

```bash
docker ps --filter name=soar_tenzir_node          # estado/health
docker logs soar_tenzir_node --tail 60            # errores recientes
# Web server (modo server: TLS + X-Tenzir-Token):
docker run --rm --network soar_net curlimages/curl:8.10.1 -sk \
    -X POST https://tenzir-node:5160/api/v0/pipeline/create \
    -H "X-Tenzir-Token: $TENZIR_TOKEN" -H 'Content-Type: application/json' \
    -d '{"definition":"export | head 1 | discard","hidden":true,"ttl":"5s"}'
# Pipelines declaradas:
docker exec soar_tenzir_node tenzir 'show pipelines'
```

Si el web server falló al arrancar (`failed to start server` en logs):
`--mode=upstream` solo puede bindear localhost — en este stack el modo
correcto es `server` (TLS + token). Ver `TENZIR_WEB_MODE` en `.env`.

## Acción

1. Proceso vivo pero sin actividad → reiniciar:
   `docker restart soar_tenzir_node` (los pipelines persisten en
   `/var/lib/tenzir`).
2. Token perdido tras reset de volumen →
   `bash scripts/setup/init_tenzir_token.sh --force` +
   `make init-webhook`.
3. El contenedor **huérfano** `tenzir-node` (imagen `:main`, red
   `tenzir-network`, API dev-mode en 0.0.0.0:5160) no es el servicio
   gestionado — no confundir al depurar; ver registro de deuda.
