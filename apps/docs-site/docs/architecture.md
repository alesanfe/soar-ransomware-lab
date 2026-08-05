---
sidebar_position: 3
---

# Arquitectura

## Stack de Servicios

El laboratorio SOAR se compone de 15 contenedores Docker organizados en capas:

```
┌─────────────────────────────────────────────────────────────┐
│  Acceso (Nginx :80 / :443 → subpaths y TLS)                 │
├─────────────────────────────────────────────────────────────┤
│  SOAR: Shuffle UI :8081 │ Shuffle API :15001 │ Orborus     │
├─────────────────────────────────────────────────────────────┤
│  IR: TheHive :9000 │ Cortex :19001                          │
├─────────────────────────────────────────────────────────────┤
│  SIEM: Wazuh Manager :15141/1515/55100 │ Wazuh Dashboard :15601│
├─────────────────────────────────────────────────────────────┤
│  TI: MISP :8083                                             │
├─────────────────────────────────────────────────────────────┤
│  Gestión: API :8000 │ Web Management :8085 │ Docs :8086    │
├─────────────────────────────────────────────────────────────┤
│  Observabilidad: Grafana :8084 │ Loki :3100 interno       │
├─────────────────────────────────────────────────────────────┤
│  Datos: Elasticsearch :19200 │ Redis │ MariaDB (internos)   │
└─────────────────────────────────────────────────────────────┘
```

## Componentes

| Servicio         | Imagen                                   | Puerto (host)                | Descripción                  |
|------------------|------------------------------------------|------------------------------|------------------------------|
| nginx            | nginx:1.25-alpine                        | 80, 443                      | Reverse proxy y TLS        |
| thehive          | thehiveproject/thehive:3.5.2-1           | 9000                         | Gestión de casos             |
| cortex           | build: infra/docker/images/cortex        | 19001                        | Análisis de IoCs             |
| shuffle-backend  | ghcr.io/shuffle/shuffle-backend:2.2.1    | 15001                        | API del orquestador          |
| shuffle-frontend | ghcr.io/shuffle/shuffle-frontend:2.2.1   | 8081                         | UI del orquestador           |
| orborus          | ghcr.io/shuffle/shuffle-orborus:2.2.1    | —                            | Ejecutor de workers          |
| wazuh-manager    | wazuh/wazuh-manager:4.14.0               | 15141, 1515, 55100           | SIEM/XDR                     |
| wazuh-dashboard  | wazuh/wazuh-dashboard:4.14.0             | 15601                        | Dashboards (OpenSearch)      |
| wazuh-indexer    | wazuh/wazuh-indexer:4.14.0               | 9200                         | Índices Wazuh                |
| misp             | ghcr.io/misp/misp-docker/misp-core:latest| 8083                         | Threat Intelligence            |
| elasticsearch    | docker.elastic.co/elasticsearch/elasticsearch:7.10.2 | 19200              | Motor de búsqueda SOAR       |
| redis            | redis:7-alpine                           | interno                      | Caché y sesiones             |
| mariadb          | mariadb:10.11                            | interno                      | BD de MISP                   |
| api              | build: apps/api                          | 8000                         | API REST FastAPI             |
| web-management   | build: apps/web-management               | 8085                         | Panel Web de gestión         |
| docs_site        | build: apps/docs-site                    | 8086                         | Documentación Docusaurus     |
| grafana          | grafana/grafana:10.3.4                   | 8084                         | Métricas y logs              |

## Redes Docker

- **`soar_net`** — red interna principal (todos los servicios)
- **`soar_edge`** — red de acceso externo (nginx + servicios con UI)
- **`ti_net`** — red de threat intelligence (elasticsearch, MISP)

## Flujo de Datos

```
Wazuh Agent → Wazuh Manager → Shuffle Webhook / Tenzir → Shuffle Workflow
                    ↓                        ↓
              Wazuh Indexer / Elasticsearch       TheHive (casos)
                    ↓                        ↓
            Wazuh Dashboard              Cortex (enriquecimiento)
                    ↓                        ↓
                Grafana                   MISP (IoCs)
```

## Archivos de Configuración

- **Stack completo**: `infra/docker/compose/docker-compose*.yml`
- **Variables de entorno**: `.env.full`
- **Nginx**: `infra/docker/config/nginx/nginx.conf`
- **Cortex**: `infra/docker/config/cortex.application.conf/cortex.conf`
