# Tabla canónica de puertos y URLs del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
- [2. Tabla de servicios](#2-tabla-de-servicios)
- [3. Endpoints de la Lab API](#3-endpoints-de-la-lab-api)
- [4. Notas de acceso](#4-notas-de-acceso)
- [5. Validación rápida](#5-validación-rápida)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

Este documento es la fuente de verdad para los puertos, nombres de contenedor y URLs de acceso del laboratorio. Los valores por defecto se definen en `.env.example` y se pueden sobrescribir en `.env.full`.

Dominio local canónico: `soar.local` → `127.0.0.1` (añadir al archivo hosts, ver [installation_guide.md](../getting_started/installation_guide.md)).

---

## 2. Tabla de servicios

| Servicio                  | Host / Puerto por defecto | Puerto contenedor | Protocolo | URL canónica                              | Acceso vía Nginx | Nombre de contenedor (`COMPOSE_PROJECT_NAME=soar`) | Notas |
|---------------------------|----------------------------|-------------------|-----------|-------------------------------------------|------------------|----------------------------------------------------|-------|
| Nginx (proxy inverso)     | `80` / `443`               | `80` / `443`      | HTTP/HTTPS| `https://soar.local`                      | —                | `soar_nginx`                                       | Redirige 80→443. Termina TLS con `soar.local.crt`. |
| Web Management            | `${WEB_UI_PORT:-8085}`     | `80`              | HTTP      | `http://localhost:8085`                   | `/`              | `soar_web_management`                              | SPA servida también en raíz por Nginx. |
| Docs Site (Docusaurus)    | `${DOCS_PORT:-8086}`       | `8080`            | HTTP      | `http://localhost:8086`                   | No               | `soar_docs_site`                                   | SPA con rutas absolutas; acceso directo. |
| Lab API (FastAPI)         | `${API_PORT:-8000}`        | `8000`            | HTTP      | `http://localhost:8000` / `https://soar.local/api/` | `/api/`          | `soar_api`                                         | También accesible directo; Nginx añade headers CORS. |
| Shuffle UI                | `${SHUFFLE_UI_PORT:-8081}` | `80`              | HTTP      | `http://localhost:8081`                   | No               | `soar_shuffle_frontend`                            | React SPA; no soporta subpath. |
| Shuffle Backend           | `${SHUFFLE_API_PORT:-15001}`| `5001`           | HTTP      | `http://localhost:15001`                  | `/shuffle-api/`  | `soar_shuffle_backend`                             | Webhook de Shuffle apunta al contenedor `shuffle-backend:5001`. |
| Orborus                   | —                          | `5000`            | HTTP      | —                                         | No               | `soar_orborus`                                     | Sin puerto host; ejecuta workers dentro de Docker. |
| Network Watcher           | `${NETWORK_WATCHER_PORT:-15130}` | `8080`    | HTTP      | `http://localhost:15130`                  | No               | `soar_network_watcher`                             | Conecta workers de Shuffle a `soar_net`. |
| Tenzir Node               | `15160` / `15140`          | `5160` / `1514`   | HTTP/Syslog | `http://localhost:15160`                | No               | `soar_tenzir_node`                                 | `15160` API, `15140` ingest syslog. |
| TheHive                   | `${THEHIVE_HTTP_PORT:-19000}` | `9000`         | HTTP      | `http://localhost:19000`                  | `/thehive/`      | `soar_thehive`                                     | Acceso directo recomendado para validación inicial. |
| Cortex                    | `${CORTEX_HTTP_PORT:-19001}` | `9001`          | HTTP      | `http://localhost:19001`                  | `/cortex/`       | `soar_cortex`                                      | `/cortex/analyzers` desde Nginx. |
| Elasticsearch             | `${ELASTICSEARCH_PORT:-19200}` | `9200`         | HTTP      | `http://localhost:19200`                  | No               | `soar_elasticsearch`                               | Usado por TheHive, Cortex, Shuffle, Grafana y Wazuh. |
| OpenSearch (alternativo)  | `${OPENSEARCH_PORT:-19201}` | `9200`           | HTTP      | `http://localhost:19201`                  | No               | `soar_opensearch`                                  | Compose `docker-compose.opensearch.yml`; no se despliega por defecto. |
| MISP                      | `${MISP_PORT:-8083}`       | `80`              | HTTP/HTTPS| `http://localhost:8083`                   | No               | `soar_misp`                                        | MISP no soporta subpath proxy. |
| MISP DB                   | —                          | `3306`            | SQL       | —                                         | No               | `soar_misp_db`                                     | MariaDB 10.11; solo red interna. |
| Wazuh Manager             | `${WAZUH_API_PORT:-55100}` / `${WAZUH_EVENTS_PORT:-15141}` / `${WAZUH_ENROLLMENT_PORT:-1515}` / `${WAZUH_SYSLOG_PORT:-514}` | `55000` / `1514` / `1515` / `514` | HTTP/UDP  | `https://localhost:55100`                 | No               | `soar_wazuh_manager`                               | Puerto `55000` API REST, `1514` eventos, `1515` enroll, `514/udp` syslog. |
| Wazuh Indexer             | `${WAZUH_INDEXER_PORT:-9200}` | `9200`          | HTTPS     | `https://localhost:9200`                  | No               | `soar_wazuh_indexer`                               | Con seguridad activada (`wazuh.indexer`). |
| Wazuh Dashboard           | `${WAZUH_DASHBOARD_PORT:-15601}` | `5601`        | HTTPS     | `https://localhost:15601`                   | No               | `soar_wazuh_dashboard`                             | OpenSearch Dashboards con TLS; no soporta subpath proxy. |
| Redis                     | `${REDIS_PORT:-6379}`      | `6379`            | Redis     | `redis://localhost:6379`                  | No               | `soar_redis`                                       | Requiere `REDIS_PASSWORD` si está configurada. |
| Grafana                   | `${GRAFANA_PORT:-8084}`    | `3000`           | HTTP      | `http://localhost:8084`                   | No               | `soar_grafana`                                     | Data source Elasticsearch configurado vía provisioning. |
| Grafana DB (PostgreSQL)   | —                          | `5432`            | SQL       | —                                         | No               | `soar_grafana_db`                                  | Solo `logging_net`. |
| Loki                      | —                          | `3100`            | HTTP      | —                                         | No               | `soar_loki`                                        | Solo red interna (`logging_net`). |
| Promtail                  | —                          | —                 | HTTP      | —                                         | No               | `soar_promtail`                                    | Descubre contenedores por socket Docker. |

---

## 3. Endpoints de la Lab API

La API FastAPI expone los siguientes puertos de entrada principales. Todos se acceden bajo `http://localhost:8000` (directo) o `https://soar.local/api/` (vía Nginx), salvo indicación contraria.

| Método | Ruta | Descripción | Dependencias |
|--------|------|-------------|--------------|
| `POST` | `/auth/login` | Login y generación de JWT | `JWT_SECRET_KEY` |
| `POST` | `/auth/verify` | Verificación de token JWT | `JWT_SECRET_KEY` |
| `GET`  | `/health` | Healthcheck de la API | `config_provider` |
| `GET`  | `/analytics/metrics` | Métricas del sistema | `SystemMetricsDriver` |
| `GET`  | `/analytics/kpis` | KPIs calculados (MTTR, etc.) | `AnalyticsService` / ES |
| `GET`  | `/analytics/kpis/aggregated` | KPIs agregados de `soar-metrics` | Elasticsearch |
| `POST` | `/backup/create` | Crear backup `.tar.gz` | `BackupService`, `TarBackupDriver` |
| `POST` | `/backup/restore` | Restaurar backup | `BackupService`, `TarBackupDriver` |
| `GET`  | `/backup/list` | Listar backups disponibles | `BackupService` |
| `POST` | `/tests/run` | Ejecutar suite de tests vía `PytestTestRunner` | `pytest`, `.env.full` |
| `GET`  | `/services/status` | Estado de todos los servicios SOAR | `HealthService` |
| `GET`  | `/soar/thehive/cases` | Listar casos de TheHive | `TheHiveClient` |
| `GET`  | `/soar/thehive/health` | Healthcheck de TheHive | `TheHiveClient` |
| `GET`  | `/soar/cortex/analyzers` | Listar analyzers de Cortex | `CortexClient` |
| `GET`  | `/soar/cortex/health` | Healthcheck de Cortex | `CortexClient` |
| `GET`  | `/soar/misp/attributes` | Buscar atributos en MISP | `MISPClient` |
| `GET`  | `/soar/misp/health` | Healthcheck de MISP | `MISPClient` |

> **Nota:** La ingestión real de alertas no pasa por la Lab API, sino por el webhook de Shuffle creado por `init_shuffle_webhook.py`.

## 4. Notas de acceso

- **Nginx** es el punto de entrada recomendado para `https://soar.local`. Expone:
  - `/` → Web Management
  - `/api/` → Lab API
  - `/thehive/` → TheHive
  - `/cortex/` → Cortex
  - `/shuffle-api/` → Shuffle Backend
  - `/nginx-health` → healthcheck de Nginx
- **Swagger / OpenAPI de la Lab API**:
  - Directo (recomendado): `http://localhost:8000/docs` y `http://localhost:8000/openapi.json`.
  - Vía Nginx: `https://soar.local/api/docs` y `https://soar.local/api/openapi.json`.
  - Nota: `https://soar.local:8000/docs` **no es válido** porque Nginx solo escucha en `80` y `443`. El acceso directo usa `localhost:8000`; el acceso por dominio usa `https://soar.local/api/docs`.
  - Si los assets estáticos de Swagger no cargan por subpath, usar la URL directa `http://localhost:8000/docs` o configurar `root_path` en FastAPI.
- **Acceso directo** es necesario para servicios con SPA/assets absolutos o seguridad que no soporta subpath:
  - Shuffle UI (`8081`). Nota: Nginx **no expone** `/shuffle/`; el frontend de Shuffle no soporta subdirectorio sin recompilar. Usa siempre el puerto directo `http://localhost:8081`.
  - MISP (`8083`)
  - Grafana (`8084`)
  - Web Management (`8085`, aunque también está en `/`)
  - Docs Site (`8086`)
  - TheHive (`19000`)
  - Cortex (`19001`)
  - Elasticsearch (`19200`)
  - Wazuh Dashboard (`15601`)
- Los **puertos sin mapeo host** solo son alcanzables desde contenedores dentro de `soar_net` o `logging_net`.

---

## 5. Validación rápida

```bash
# Desde el host
curl -k https://soar.local/nginx-health
curl http://localhost:8000/health
curl http://localhost:8084/api/health

# Desde otro contenedor (por ejemplo, el propio API)
docker exec -it soar_api sh -c 'wget -qO- http://elasticsearch:9200/_cluster/health'
```

---

## 6. Referencias

- [Guía de instalación](../getting_started/installation_guide.md)
- [Arquitectura de red y Docker](../architecture/docker_architecture.md)
- [Nginx reverse proxy config](../../infra/docker/config/nginx/nginx.conf)
- [`.env.example`](../../.env.example)
