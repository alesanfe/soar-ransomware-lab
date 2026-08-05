# Documentación de Arquitectura Docker

> Este documento describe la arquitectura Docker del SOAR Ransomware Lab, incluyendo la organización de archivos
> Compose, configuración de redes, persistencia de datos y procedimientos de despliegue.

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Estrategia de contenerización](#31-estrategia-de-contenerización)
    - [3.2 Servicios y composición](#32-servicios-y-composición)
    - [3.3 Redes y volúmenes](#33-redes-y-volúmenes)
    - [3.4 Comandos y operaciones](#34-comandos-y-operaciones)
    - [3.5 Troubleshooting Docker](#35-troubleshooting-docker)
- [4. Validación](#4-validación)
    - [4.1 Verificación](#41-verificación)
    - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
    - [4.3 Evidencias](#43-evidencias)
- [5. Problemas y consideraciones](#5-problemas-y-consideraciones)
    - [5.1 Limitaciones](#51-limitaciones)
    - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
    - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones--troubleshooting)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Este documento describe la arquitectura Docker del SOAR Ransomware Lab, incluyendo la organización de archivos Compose,
configuración de redes, persistencia de datos y procedimientos de despliegue.

### 1.2 Contexto

El SOAR Ransomware Lab utiliza Docker Compose para orquestar 16 servicios a través de 4 redes con mejoras en networking,
persistencia de datos y logging. Para la arquitectura completa del sistema, ver [README.md](../../README.md).

## 2. Alcance

### 2.1 Qué cubre

Este documento cubre:

- Organización de archivos Docker Compose
- Configuración de redes Docker
- Estrategia de persistencia de datos
- Configuración de servicios y healthchecks
- Límites de recursos
- Configuración de logging
- Estrategia de backup
- Consideraciones de seguridad
- Procedimientos de mantenimiento

### 2.2 Límites

Este documento no cubre:

- Arquitectura de alto nivel del sistema (ver docs/architecture/overview.md)
- Detalles de configuración específicos de cada herramienta (ver documentación individual)
- Procedimientos operativos paso a paso (ver docs/getting_started/user_guide.md)
- Estrategias de pruebas específicas (ver docs/testing/)

### 2.3 Dependencias

Este documento depende de:

- Documentación oficial de Docker Compose
- Documentación de arquitectura (docs/architecture/overview.md)
- Documentación de seguridad (docs/architecture/security.md)
- Guía de usuario (docs/getting_started/user_guide.md)

## 3. Contenido principal

### 3.1 Estrategia de contenerización

#### Organización de archivos Compose

La orquestación se divide en varios archivos `docker-compose*.yml` bajo `infra/docker/compose/` para facilitar perfiles y arranque selectivo:

| Archivo | Propósito | Servicios principales |
|---|---|---|
| `infra/docker/compose/docker-compose.yml` | Redes, volúmenes globales y `elasticsearch` | `elasticsearch` |
| `infra/docker/compose/docker-compose.core.yml` | Core SOAR | `redis`, `thehive`, `cortex`, `shuffle-frontend`, `shuffle-backend`, `orborus`, `network-watcher`, `tenzir-node` |
| `infra/docker/compose/docker-compose.misp.yml` | Inteligencia de amenazas | `misp-db`, `misp-modules`, `misp` |
| `infra/docker/compose/docker-compose.wazuh.yml` | SIEM Wazuh | `wazuh.manager`, `wazuh.indexer`, `wazuh.dashboard` |
| `infra/docker/compose/docker-compose.api.yml` | API, portal y proxy | `api`, `docs-site`, `web-management`, `nginx` |
| `infra/docker/compose/logging/docker-compose.logging.yml` | Observabilidad | `grafana-db`, `grafana`, `loki`, `promtail` |

> Nota: Todos los comandos se ejecutan desde la raíz del repositorio, salvo indicación expresa.

#### Configuración auxiliar de logging

```
infra/docker/compose/logging/
├── docker-compose.logging.yml
├── promtail-config.yml        # descubrimiento de contenedores Docker → Loki
├── loki-config.yml            # archivo de referencia; compose usa la config por defecto de la imagen
├── grafana-datasources.yml    # datasource Elasticsearch para KPIs
├── grafana-kpi-dashboard.yml  # provisioning del dashboard
└── kpi-dashboard.json         # definición del dashboard de KPIs
```

#### Iniciar servicios

Desde la raíz, con `make up` (recomendado, incluye logging):

```bash
make up
```

Equivalente manual:

```bash
docker compose --env-file .env.full -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml up -d
```

#### Consideraciones de seguridad

- `ti_net` es `internal: true`; `soar_net` y `logging_net` no son internas en esta versión de laboratorio.
- `soar_edge` se define en el Compose base pero actualmente no se asigna a ningún servicio; la exposición externa se realiza mediante `ports:` mapeadas.
- `orborus` y `cortex` montan el socket Docker del host para lanzar analizadores; implica riesgo de escalada de privilegios y está limitado a entornos controlados.
- Los healthchecks se ejecutan dentro del contenedor y deben distinguirse entre *liveness*, *readiness* y salud funcional completa.

### 3.2 Servicios y composición

#### Tabla canónica de servicios

| Servicio | Imagen / build | Contenedor (por defecto) | Puerto host → contenedor | Redes | Healthcheck | Propósito |
|---|---|---|---|---|---|---|
| elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch:7.10.2` | `soar_elasticsearch` | `${ELASTICSEARCH_PORT:-19200}` → 9200 | `soar_net`, `ti_net` | `GET /_cluster/health` | Motor de búsqueda y métricas |
| redis | `redis:7-alpine` | `soar_redis` | 6379 → 6379 | `ti_net`, `soar_net` | `nc -z 127.0.0.1 6379` | Cache/cola con autenticación |
| thehive | `thehiveproject/thehive:3.5.2-1` | `soar_thehive` | `${THEHIVE_HTTP_PORT:-9000}` → 9000 | `soar_net` | `GET /api/status` | Gestión de casos |
| cortex | build `infra/docker/images/cortex/Dockerfile` | `soar_cortex` | `${CORTEX_HTTP_PORT:-19001}` → 9001 | `soar_net` | HTTP 2xx/3xx en `:9001/` | Motor de analizadores; monta `/var/run/docker.sock` |
| shuffle-frontend | `ghcr.io/shuffle/shuffle-frontend:2.2.1` | `soar_shuffle_frontend` | `${SHUFFLE_UI_PORT:-8081}` → 80 | `soar_net`, `ti_net` | `GET http://localhost:80` | UI de workflows |
| shuffle-backend | `ghcr.io/shuffle/shuffle-backend:2.2.1` | `soar_shuffle_backend` | `${SHUFFLE_API_PORT:-15001}` → 5001 | `soar_net`, `ti_net` | deshabilitado | Motor de workflows |
| orborus | `ghcr.io/shuffle/shuffle-orborus:2.2.1` | `soar_orborus` | — | `soar_net` | `nc -z shuffle-backend 5001` | Ejecutor de contenedores de analizadores |
| network-watcher | build `src/soar_lab/infrastructure/network_watcher` | `soar_network_watcher` | `${NETWORK_WATCHER_PORT:-15130}` → 8080 | `soar_net` | `GET /health` en `:8080` | Diagnóstico/recuperación de red (sincroniza `/etc/hosts` de workers) |
| tenzir-node | `tenzir/tenzir:main` | `soar_tenzir_node` | 15160 → 5160, 15140 → 1514 | `soar_net` | — | Nodo Tenzir (modo dev) |
| misp-db | `mariadb:10.11` | `soar_misp_db` | — | `soar_net` | `mysqladmin ping` | BD MISP (volumen Docker, no bind) |
| misp-modules | `ghcr.io/misp/misp-docker/misp-modules:latest` | `soar_misp_modules` | — | `soar_net` | socket `localhost:6666` | Módulos MISP |
| misp | `ghcr.io/misp/misp-docker/misp-core:latest` | `soar_misp` | `${MISP_PORT:-8083}` → 80 | `soar_net` | `GET /users/heartbeat` | Plataforma de inteligencia de amenazas |
| wazuh.manager | `wazuh/wazuh-manager:4.14.0` | `soar_wazuh_manager` | `${WAZUH_EVENTS_PORT:-15141}` → 1514, `${WAZUH_ENROLLMENT_PORT:-1515}` → 1515, `${WAZUH_SYSLOG_PORT:-514}` → 514/udp, `${WAZUH_API_PORT:-55100}` → 55000 | `soar_net` | `wazuh-control status` | Manager SIEM |
| wazuh.indexer | `wazuh/wazuh-indexer:4.14.0` | `soar_wazuh_indexer` | `${WAZUH_INDEXER_PORT:-9200}` → 9200 | `soar_net` | `GET /_cluster/health` (HTTPS, auth) | Índice Wazuh (OpenSearch) |
| wazuh.dashboard | `wazuh/wazuh-dashboard:4.14.0` | `soar_wazuh_dashboard` | `${WAZUH_DASHBOARD_PORT:-15601}` → 5601 | `soar_net` | deshabilitado | Dashboard Wazuh |
| api | build `apps/api/Dockerfile` (contexto raíz) | `soar_api` | `${API_PORT:-8000}` → 8000 | `soar_net`, `ti_net`, `logging_net` | `GET /health` | API FastAPI |
| docs-site | build `apps/docs-site/Dockerfile` (contexto raíz) | `soar_docs_site` | `${DOCS_PORT:-8086}` → 8080 | `soar_net` | deshabilitado | Portal Docusaurus |
| web-management | build `apps/web-management/Dockerfile` | `soar_web_management` | 8085 → 80 | `soar_net` | `pgrep nginx` | SPA web de operación |
| nginx | `nginx:1.25-alpine` | `soar_nginx` | 80 → 80, 443 → 443 | `soar_net`, `logging_net` | `GET /nginx-health` | Proxy inverso y TLS |
| grafana-db | `postgres:14-alpine` | `soar_grafana_db` | — | `logging_net` | `pg_isready -U grafana` | BD Grafana |
| grafana | `grafana/grafana:10.3.4` | `soar_grafana` | `${GRAFANA_PORT:-8084}` → 3000 | `logging_net`, `soar_net` | `GET /api/health` | Visualización KPIs/logs |
| loki | `grafana/loki:2.9.10` | `soar_loki` | — | `logging_net` | — (imagen sin shell) | Agregación de logs |
| promtail | `grafana/promtail:2.9.10` | `soar_promtail` | — | `logging_net`, `soar_net` | — | Envío de logs Docker a Loki |

**Notas de nomenclatura**:
- Los nombres de contenedor usan el prefijo `${COMPOSE_PROJECT_NAME:-soar}_` y `_` como separador (ej. `soar_api`).
- Los nombres de servicio con guión (`shuffle-frontend`, `wazuh.manager`) son los nombres internos de Docker Compose.
- `soar_api` es el nombre del **contenedor**; el **servicio** Compose es `api` y el **hostname** interno es `api`.

#### Healthchecks y dependencias

- `shuffle-backend` no tiene healthcheck configurado; `orborus` lo monitoriza mediante `nc -z shuffle-backend 5001`.
- `loki` usa la imagen mínima de Grafana Loki (`2.9.10`), sin shell ni curl, por lo que no dispone de healthcheck.
- `docs-site` y `wazuh.dashboard` tienen healthchecks deshabilitados en la configuración actual por requisitos de autenticación o tiempos de arranque.
- `thehive` usa `/api/status` para evitar falsos negativos mientras Elasticsearch prepara sus índices.

#### Límites de recursos

Valores extraídos de los archivos Compose; pueden ajustarse en `.env.full` o directamente en `deploy.resources`:

| Grupo | Servicios | CPU límite / reserva | Memoria límite / reserva |
|---|---|---|---|
| Grandes | `elasticsearch`, `thehive`, `cortex`, `shuffle-backend`, `misp` | 2.0 / 1.0 cores | 4GB / 2GB |
| Medianos | `redis`, `shuffle-frontend`, `orborus`, `wazuh.manager`, `wazuh.indexer`, `grafana`, `api` | 1.0 / 0.5 cores | 1-2GB / 0.5-1GB |
| Pequeños | `docs-site`, `web-management`, `promtail` | 0.5 / 0.25 cores | 256-512MB / 128-256MB |

### 3.3 Redes y volúmenes

#### Topología de red

| Red | CIDR | Tipo | Servicios | Propósito |
|---|---|---|---|---|
| `bridge` | — | `external: true` | Ninguno directamente | Red por defecto de Docker; declarada por compatibilidad |
| `soar_edge` | dinámico | bridge | Ningún servicio en la versión actual | Definida en el Compose base pero no asignada; la exposición externa se hace por `ports:` |
| `soar_net` | `10.100.0.0/16` | bridge | `elasticsearch`, `redis`, `thehive`, `cortex`, `shuffle-*`, `orborus`, `network-watcher`, `tenzir-node`, `misp*`, `wazuh.*`, `api`, `web-management`, `nginx`, `grafana`, `promtail` | Red principal del laboratorio |
| `ti_net` | `172.22.0.0/16` | `internal: true` | `elasticsearch`, `redis`, `api` | Aislada del exterior; tráfico de inteligencia de amenazas |
| `logging_net` | `172.23.0.0/16` | bridge | `grafana-db`, `grafana`, `loki`, `promtail`, `nginx` | Tráfico de observabilidad |

> **Importante:** `soar_edge` no conecta actualmente a los servicios; no confundirla con `soar_net`. El acceso externo se controla mediante mapeos de puertos del host.

#### DNS y aliases

- Docker Compose crea un servidor DNS interno (`127.0.0.11`) en cada red.
- Los nombres de servicio (`api`, `thehive`, `elasticsearch`) resuelven a la IP del contenedor dentro de la red.
- `orborus` lanza contenedores de analizadores en la red `soar_net` (o `${COMPOSE_PROJECT_NAME}_net` según `SHUFFLE_APP_NETWORK`); requiere que exista la red y que el socket Docker tenga permisos adecuados.
- `network-watcher` puede modificar `/etc/hosts` o DNS de contenedores dependientes para resolver problemas de conectividad (ver `docs/operations/network_watcher.md`).

#### Seguridad de red

- `ti_net` es la única red marcada como `internal: true`; no tiene salida a Internet.
- Los servicios expuestos al host (`ports:`) no están necesariamente en una red externa; el aislamiento depende del firewall del host.
- `api` pertenece a `soar_net`, `ti_net` y `logging_net` para orquestar integraciones y consumir métricas/logs.
- `nginx` conecta a `soar_net` y `logging_net`; termina TLS y enruta a `api` y `web-management`.

#### Estrategia de volúmenes

Los volúmenes se declaran en `infra/docker/compose/docker-compose.yml`. La mayoría son bind mounts que apuntan a `artifacts/`:

```
artifacts/
├── data/
│   ├── elasticsearch/   # es_data
│   ├── thehive/files/   # thehive_files
│   ├── cortex/          # cortex_data
│   ├── shuffle/apps/    # shuffle_apps
│   ├── shuffle/files/   # shuffle_files
│   ├── redis/           # redis_data
│   ├── misp/files/      # misp_files
│   ├── misp/configs/    # misp_configs
│   ├── wazuh/...        # múltiples bind mounts Wazuh
│   ├── loki/            # loki_data
│   └── grafana/         # grafana_data
├── logs/
│   ├── nginx/           # nginx_logs
│   └── misp/            # misp_logs
└── backups/             # montado en /app/backups (api)
```

**Casos especiales:**

- `misp_db` es un **volumen Docker normal** (no bind mount). En Windows/Docker Desktop, bind mounts de MariaDB generan errores de permisos (`rename`). Usar `docker compose down -v` elimina el volumen lógico, no un directorio local.
- Wazuh utiliza numerosos bind mounts bajo `artifacts/data/wazuh/` para `api_config`, `etc`, `logs`, `queue`, `var_multigroups`, `integrations`, `active_response`, `agentless`, `wodles`, `filebeat_etc` y `filebeat_var`.
- `wazuh-indexer-data`, `wazuh-dashboard-config` y `wazuh-dashboard-custom` son volúmenes Docker normales gestionados por el stack Wazuh.
- El logging stack usa volúmenes Docker normales para `grafana_db_data`, `grafana_data` y `loki_data`.

#### Logging

Cada servicio utiliza el driver `json-file` con rotación:

- `max-size`: 10 MB
- `max-file`: 3 archivos
- Total aproximado: ~30 MB por servicio en disco de Docker.

Ubicaciones adicionales:

- Host: `artifacts/logs/nginx/` y `artifacts/logs/misp/` (bind mounts explícitos).
- Streaming en vivo: `api` expone `/ws/logs` (WebSocket) y `/api/ws/logs` vía Nginx.
- Logging centralizado:
  - `promtail` descubre contenedores por el socket Docker y envía a `loki`.
  - `grafana` consulta `loki` y `elasticsearch` (`soar-metrics`) para logs y KPIs.

#### Estrategia de backup

- El servicio de backup reside en `src/soar_lab/application/use_cases/backup_service.py` y se expone en `/backup/create` y `/backup/restore`.
- Los artefactos se escriben en `artifacts/backups/` (montado en `/app/backups` del contenedor `api`).
- Para backup completo del laboratorio se recomienda detener el stack y copiar `artifacts/` (incluidos `data/` y `logs/`), además de exportar volúmenes Docker normales (`misp_db`, `wazuh-indexer-data`, etc.).


### 3.4 Comandos y operaciones

#### Comandos de Gestión

```bash
# Iniciar todos los servicios
make up

# Detener todos los servicios
make down

# Reiniciar el stack completo
make down && make up

# Ver estado de todos los servicios
docker ps --format "table {{.Names}}\t{{.Status}}"

# Ver logs de un servicio específico
docker logs soar_thehive --tail 50

# Acceder a un contenedor
docker exec -it soar_thehive bash
```

#### Mantenimiento

**Actualizaciones:**

- Actualizar imágenes Docker regularmente
- Revisar y actualizar archivos `infra/docker/compose/docker-compose*.yml`
- Aplicar parches de seguridad a contenedores

**Monitoreo:**

- Verificar health checks de servicios
- Monitorear uso de recursos con `docker stats`
- Revisar logs regularmente

### 3.5 Troubleshooting Docker

#### El servicio no inicia

```bash
# Revisar logs
docker logs <service_name>

# Verificar estado de salud
docker compose ps

# Reiniciar servicio específico
docker compose restart <service_name>
```

#### Problemas de conectividad de red

```bash
# Verificar conectividad de red
docker network inspect soar_net

# Probar conexión entre contenedores
docker exec <container1> ping <container2>
```

#### Problemas de persistencia de datos

```bash
# Verificar montajes de volúmenes
docker inspect <container_name> | grep -A 10 Mounts

# Verificar que existe el directorio de datos
ls -la artifacts/data/
```

#### Conflictos de puertos

```bash
# Verificar uso de puertos
netstat -tuln | grep <port>

# Cambiar puerto en .env.full
```

#### Alto uso de memoria

```bash
# Verificar uso de recursos
docker stats

# Ajustar límites de recursos en infra/docker/compose/docker-compose*.yml
```

#### Elasticsearch lento

```bash
# Verificar salud de Elasticsearch
curl http://localhost:19200/_cluster/health

# Aumentar límite de memoria en infra/docker/compose/docker-compose*.yml
```

#### Problema de Índice de Elasticsearch en TheHive

**Problema:** TheHive requiere el índice de Elasticsearch `the_hive_17` que puede no existir en una instalación fresca.

**Solución Actual:** El healthcheck se cambió para usar `/api/status` en lugar de `/api/health` para evitar la
dependencia del índice. El índice se creará automáticamente por TheHive al iniciar.

## 4. Validación

### 4.1 Verificación

La configuración Docker se verifica mediante:

- Ejecución de `docker compose config` para validar sintaxis
- Verificación de que todas las redes se crean correctamente (`docker network ls`)
- Verificación de que todos los volúmenes se montan correctamente (`docker volume ls`)
- Ejecución de health checks para cada servicio
- Pruebas de conectividad entre servicios en redes específicas

### 4.2 Criterios de aceptación

La configuración Docker se considera válida cuando:

- Todos los servicios inician sin errores
- Los health checks pasan para todos los servicios
- Las redes están correctamente configuradas y aisladas
- Los volúmenes se montan correctamente
- Los servicios pueden comunicarse entre sí según la topología de red
- Los logs se generan correctamente

### 4.3 Evidencias

Las evidencias de validación incluyen:

- Salida de `docker compose config` sin errores
- Salida de `docker compose ps` mostrando servicios en ejecución
- Salida de `docker network ls` mostrando las 4 redes
- Salida de `docker volume ls` mostrando volúmenes montados
- Logs de Docker Compose sin errores críticos
- Resultados de health checks (`docker inspect`)

## 5. Problemas y consideraciones

### 5.1 Limitaciones

- **Bind mounts en Windows**: El rendimiento de bind mounts puede ser menor en Windows Docker Desktop
- **Single-node Elasticsearch**: Configuración actual no soporta clustering
- **Recursos limitados**: Mínimo 8GB RAM requerido para stack completo

### 5.2 Riesgos o incidencias

- **Servicios no inician**: Puede ser debido a puertos ya en uso o conflictos de configuración
- **Problemas de conectividad de red**: Configuración incorrecta de redes internas
- **Problemas de persistencia de datos**: Montajes de volúmenes fallidos
- **Conflictos de puertos**: Puertos ya en uso por otros servicios
- **Problemas de rendimiento**: Recursos insuficientes o configuración subóptima

### 5.3 Recomendaciones / troubleshooting

**Recomendaciones Generales:**

- Para troubleshooting específico de Docker, ver sección 3.5
- Mantener las imágenes Docker actualizadas regularmente
- Monitorear el uso de recursos con `docker stats`
- Revisar logs regularmente para detectar problemas temprano
- Implementar una estrategia de backup regular

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Docker Compose**: https://docs.docker.com/compose/
- **Documentación de Docker Networking**: https://docs.docker.com/network/
- **Documentación de Docker Volumes**: https://docs.docker.com/storage/volumes/
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Documentación de MISP**: https://www.misp-project.org/documentation/
- **Documentación de Wazuh**: https://documentation.wazuh.com/
- **Documentación de Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **Documentación de Arquitectura**: [docs/architecture/overview.md](overview.md)
- **Documentación de Seguridad**: [docs/architecture/security.md](security.md)
- **Guía de Usuario**: [docs/getting_started/user_guide.md](../getting_started/user_guide.md)
