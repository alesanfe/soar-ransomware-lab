# Operación del Network Watcher

## Índice

- [1. Resumen](#1-resumen)
- [2. Arquitectura y funcionamiento](#2-arquitectura-y-funcionamiento)
- [3. Configuración](#3-configuración)
- [4. Healthcheck y endpoints](#4-healthcheck-y-endpoints)
- [5. Logs y diagnóstico](#5-logs-y-diagnóstico)
- [6. Recuperación manual](#6-recuperación-manual)
- [7. Referencias](#7-referencias)

---

## 1. Resumen

El `network-watcher` es un contenedor auxiliar que conecta automáticamente los workers y contenedores de aplicaciones de Shuffle a la red Docker `soar_net`. Esto permite que los pasos de los workflows resuelvan los nombres internos de los servicios SOAR (`shuffle-backend`, `elasticsearch`, `thehive`, `misp`, etc.).

---

## 2. Arquitectura y funcionamiento

El watcher escucha eventos Docker `container create` y `container start`, filtra los contenedores cuyo nombre comienza por `worker-`, `HTTP_` o contiene `_act_`, y realiza tres acciones:

1. **Conecta el contenedor a `soar_net`** (salvo que use `network_mode: container:...`).
2. **Inyecta entradas `/etc/hosts`** con las IPs reales de `shuffle-backend`, `elasticsearch`, `thehive` y `misp`.
3. **Reescribe `/etc/resolv.conf`** para usar el resolver embebido de Docker (`127.0.0.11`).
4. (Opcional) **Configura un forward de socket Docker** mediante `socat` para que los workers puedan arrancar contenedores de apps si es necesario.

Código fuente: `src/soar_lab/infrastructure/network_watcher/network_watcher.py`

Definición en Compose: `infra/docker/compose/docker-compose.core.yml`

| Parámetro | Valor por defecto | Descripción |
|-----------|-------------------|-------------|
| Puerto host | `${NETWORK_WATCHER_PORT:-15130}` | Mapeado a `8080` del contenedor |
| Red | `soar_net` | Red objetivo a la que conectar workers |
| `INJECT_HOSTS` | `shuffle-backend,elasticsearch,thehive,misp` | Hosts inyectados en `/etc/hosts` |
| `DOCKER_PROXY_HOST` | `host.docker.internal` | Destino del forward del socket Docker |
| `DOCKER_PROXY_PORT` | `2375` | Puerto del proxy TCP Docker |

---

## 3. Configuración

El servicio se levanta como parte del stack core:

```bash
make up
# o manualmente
docker compose -f infra/docker/compose/docker-compose.core.yml up -d network-watcher
```

Compose monta el socket Docker en modo solo lectura:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

> El watcher no puede ver la red desde fuera del host sin acceso al socket Docker.

---

## 4. Healthcheck y endpoints

El contenedor expone un servidor HTTP en `0.0.0.0:8080` con dos endpoints:

- `GET /health` → `{"status": "ok", "network": "soar_net"}` (o `503` si la red no existe).
- `GET /api/connections?limit=100&ip=x.x.x.x` → lista de contenedores conectados a `soar_net`.
- `GET /api/connections/<id>` → detalle de una conexión.

Desde el host:

```bash
curl http://localhost:15130/health
curl "http://localhost:15130/api/connections?limit=10"
```

---

## 5. Logs y diagnóstico

```bash
docker logs -f soar_network_watcher
```

Mensajes esperados:

```text
[watcher] Watching -> soar_net
[watcher] +net worker_... -> soar_net
[watcher] hosts injected into worker_...: ['shuffle-backend', 'elasticsearch', 'thehive', 'misp']
[watcher] resolv.conf fixed in worker_...
```

Síntomas de fallo:

- `docker.errors.NotFound: network soar_net` → no se creó la red; ejecuta `make up` o `docker network create soar_net`.
- `no IPs found for hosts injection` → los contenedores de destino no están en `soar_net`; revisa el estado de `thehive`, `misp`, etc.
- `socat binary not found` → la imagen base del watcher no incluye `socat`; el forward del socket se omite.

---

## 6. Recuperación manual

Si un worker de Shuffle no puede resolver `shuffle-backend` o `elasticsearch`:

```bash
# 1. Verificar que el watcher está corriendo
docker ps --filter name=soar_network_watcher

# 2. Reiniciar el watcher
docker restart soar_network_watcher

# 3. Forzar reconexión de un worker
WORKER_ID=$(docker ps -q --filter name=worker- | head -1)
docker network connect soar_net $WORKER_ID
docker restart $WORKER_ID

# 4. Inyectar hosts manualmente
docker exec -u root $WORKER_ID sh -c 'echo "$(getent hosts soar_shuffle_backend | awk "{print \$1}") shuffle-backend" >> /etc/hosts'
```

Si la red se ha perdido, recrear el stack completo es la opción más segura:

```bash
make down
make up
```

---

## 7. Referencias

- [src/soar_lab/infrastructure/network_watcher/network_watcher.py](../../src/soar_lab/infrastructure/network_watcher/network_watcher.py)
- [docker-compose.core.yml](../../infra/docker/compose/docker-compose.core.yml)
- [Tabla de puertos y URLs](ports_and_urls.md)
