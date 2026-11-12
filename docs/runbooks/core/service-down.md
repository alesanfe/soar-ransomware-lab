# Runbook: Core SOAR service unreachable (blackbox)

Alertas cubiertas: `core_service_down` (P0), `core_metrics_scrape_failing` (P1).

## Síntomas

- Grafana alerta: probe `probe_success{instance=...}` = 0 durante >3m.
- El servicio afectado puede ser thehive, cortex, shuffle-backend, redis,
  tenzir-node o network-watcher.

## Diagnóstico

```bash
# ¿Es el servicio o es el probador?
docker ps --filter name=soar_<svc>                    # ¿corre/healthy?
docker run --rm --network soar_net curlimages/curl:8.10.1 \
    -s -o /dev/null -w '%{http_code}\n' <target>       # ¿responde?
# ¿El blackbox exporter sigue en ambas redes?
docker inspect soar_blackbox_exporter --format \
    '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
# Debe incluir soar_net ADEMÁS de logging_net — sin ella todos los
# probes core leen 0 aunque los servicios estén sanos (regresión CORE-OBS).
```

Si el contenedor está `unhealthy`, mira su healthcheck y logs:

```bash
docker logs soar_<svc> --tail 80
docker inspect soar_<svc> --format '{{json .State.Health}}'
```

## Acción

1. Servicio caído → `docker restart soar_<svc>`; si vuelve a caer, mirar
   límites de memoria (`deploy.resources`) y errores de arranque.
2. Servicio sano pero probe=0 → verificar que blackbox está en
   `soar_net` (`docker network connect soar_net soar_blackbox_exporter`
   como workaround; el fix persistente está en
   `logging/docker-compose.logging.yml`).
3. Probe http_2xx falla con status 200 → el endpoint responde HTTP/1.0:
   corregir el servidor (watcher ya usa `protocol_version="HTTP/1.1"`).
