---
sidebar_position: 3
---

# Arquitectura

## Stack de Servicios

El laboratorio SOAR se compone de 15 contenedores Docker organizados en capas:

```
┌─────────────────────────────────────────────────────────────┐
│  Acceso (Nginx :80 / :8080 / :8081 / :443)                   │
├─────────────────────────────────────────────────────────────┤
│  SOAR: Shuffle UI :8081 │ Shuffle API :5001 │ Orborus       │
├─────────────────────────────────────────────────────────────┤
│  IR: TheHive :9000 │ Cortex :9001                           │
├─────────────────────────────────────────────────────────────┤
│  SIEM: Wazuh Manager │ Kibana :15601                        │
├─────────────────────────────────────────────────────────────┤
│  TI: MISP :8082                                             │
├─────────────────────────────────────────────────────────────┤
│  Gestión: API :8000 │ Docs :8080                            │
├─────────────────────────────────────────────────────────────┤
│  Datos: Elasticsearch │ Redis │ MariaDB (internos)          │
└─────────────────────────────────────────────────────────────┘
```

## Componentes

| Servicio         | Imagen                     | Puerto              | Descripción            |
|------------------|----------------------------|---------------------|------------------------|
| nginx            | nginx:1.25-alpine          | 80, 8080, 8081, 443 | Reverse proxy y Web UI |
| thehive          | strangebee/thehive:5       | 9000                | Gestión de casos       |
| cortex           | thehive4py/cortex          | 9001                | Análisis de IoCs       |
| shuffle-backend  | shuffler.io/shuffle:1.3.0  | 5001                | API del orquestador    |
| shuffle-frontend | shuffler.io/frontend:1.3.0 | 8081                | UI del orquestador     |
| orborus          | shuffler.io/orborus:1.3.0  | —                   | Ejecutor de workers    |
| wazuh-manager    | wazuh/wazuh-manager:4.14.0 | 1514-1516           | SIEM/XDR               |
| kibana           | kibana:7.17.29             | 15601               | Dashboards (Kibana)    |
| misp             | ghcr.io/misp/misp-docker   | 8082                | Threat Intelligence    |
| elasticsearch    | elasticsearch:7.17.29      | interno             | Motor de búsqueda      |
| redis            | redis:7-alpine             | interno             | Caché y sesiones       |
| misp_db          | mariadb                    | interno             | BD de MISP             |
| api              | build: apps/api            | 8000                | API REST FastAPI       |
| docs_site        | build: apps/docs-site      | 8080                | Documentación          |

## Redes Docker

- **`soar_net`** — red interna principal (todos los servicios)
- **`soar_edge`** — red de acceso externo (nginx + servicios con UI)
- **`ti_net`** — red de threat intelligence (elasticsearch, MISP)

## Flujo de Datos

```
Wazuh Agent → Wazuh Manager → Webhook → Shuffle
                    ↓                        ↓
              Elasticsearch            TheHive (casos)
                    ↓                        ↓
                Kibana              Cortex (enriquecimiento)
                                            ↓
                                       MISP (IoCs)
```

## Archivos de Configuración

- **Stack completo**: `infra/docker/docker-compose.yml`
- **Variables de entorno**: `.env.full`
- **Nginx**: `infra/docker/nginx.conf`
- **Cortex**: `infra/docker/docker/cortex.application.conf`
