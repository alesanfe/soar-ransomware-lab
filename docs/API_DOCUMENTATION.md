# Documentación de la API SOAR Lab

La fuente de verdad de los contratos de la API es el archivo `docs/api/openapi.json`
generado automáticamente por FastAPI.

- **OpenAPI**: `docs/api/openapi.json`
- **Swagger UI** (en ejecución): `http://localhost:8000/docs` o `https://soar.local/api/docs`
- **ReDoc** (en ejecución): `http://localhost:8000/redoc`

## Información general

- **Título**: SOAR Lab Management API
- **Versión**: 1.0.0
- **Descripción**: REST API for SOAR Ransomware Lab Management
- **Base URL**: `http://localhost:8000` / `https://soar.local/api/`
- **Autenticación**: JWT Bearer (`Authorization: Bearer <token>`)

## Autenticación

Obtén un token con el endpoint `POST /auth/login`:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \

  -H "Content-Type: application/json" \

  -d '{"username":"admin","password":"<WEB_UI_PASSWORD>"}' | jq -r '.access_token')
```

Usa el token en siguientes peticiones:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/health
```

## Endpoints

| Método | Ruta | Resumen | Tags |
|--------|------|---------|------|
| `GET` | `/` | Root |  |
| `GET` | `/health` | Health |  |
| `POST` | `/auth/login` | Login |  |
| `POST` | `/auth/verify` | Verify Auth |  |
| `GET` | `/analytics/metrics` | Get Metrics |  |
| `GET` | `/analytics/kpis` | Get Kpis |  |
| `POST` | `/backup/create` | Create Backup |  |
| `GET` | `/backup/list` | List Backups |  |
| `POST` | `/backup/restore` | Restore Backup |  |
| `POST` | `/tests/run` | Run Tests |  |
| `GET` | `/services/status` | Get Services Status |  |
| `GET` | `/soar/thehive/cases` | Thehive List Cases |  |
| `GET` | `/soar/thehive/cases/{case_id}` | Thehive Get Case |  |
| `GET` | `/soar/thehive/cases/{case_id}/observables` | Thehive Get Observables |  |
| `GET` | `/soar/thehive/cases/{case_id}/tasks` | Thehive Get Tasks |  |
| `GET` | `/soar/thehive/health` | Thehive Health |  |
| `GET` | `/analytics/kpis/aggregated` | Get Aggregated Kpis |  |
| `GET` | `/soar/cortex/analyzers` | Cortex List Analyzers |  |
| `GET` | `/soar/cortex/jobs` | Cortex List Jobs |  |
| `GET` | `/soar/cortex/jobs/{job_id}` | Cortex Get Job |  |
| `GET` | `/soar/cortex/jobs/{job_id}/report` | Cortex Get Job Report |  |
| `GET` | `/soar/cortex/health` | Cortex Health |  |
| `GET` | `/soar/misp/attributes` | Misp Search Attributes |  |
| `GET` | `/soar/misp/events` | Misp List Events |  |
| `GET` | `/soar/misp/events/{event_id}` | Misp Get Event |  |
| `GET` | `/soar/misp/health` | Misp Health |  |
| `GET` | `/soar/shuffle/workflows` | Shuffle List Workflows |  |
| `GET` | `/soar/shuffle/workflows/{workflow_id}` | Shuffle Get Workflow |  |
| `GET` | `/soar/shuffle/workflows/{workflow_id}/executions` | Shuffle Get Executions |  |
| `GET` | `/soar/shuffle/workflows/{workflow_id}/executions/{execution_id}` | Shuffle Get Execution |  |
| `GET` | `/soar/shuffle/health` | Shuffle Health |  |
| `GET` | `/soar/elasticsearch/count` | Es Count |  |
| `GET` | `/soar/elasticsearch/latest` | Es Latest |  |
| `GET` | `/soar/elasticsearch/health` | Es Health |  |
| `GET` | `/soar/wazuh/agents` | Wazuh List Agents |  |
| `GET` | `/soar/wazuh/agents/{agent_id}` | Wazuh Get Agent |  |
| `GET` | `/soar/wazuh/agents/{agent_id}/vulnerabilities` | Wazuh Agent Vulns |  |
| `GET` | `/soar/wazuh/manager` | Wazuh Manager Info |  |
| `GET` | `/soar/wazuh/health` | Wazuh Health |  |
| `GET` | `/soar/status` | Soar Status |  |

## Notas

- Todos los endpoints protegidos requieren `Authorization: Bearer <token>`.
- Las respuestas de error usan el esquema HTTP estándar de FastAPI.
- Para detalles de esquemas de petición/respuesta, consulta `docs/api/openapi.json` o Swagger UI.

## Servicios externos

La API del laboratorio actúa como fachada sobre servicios desplegados en Docker:

| Servicio | Puerto host | Contenedor (red `soar_net`) |
|----------|-------------|-----------------------------|
| TheHive | 19000 | `thehive:9000` |
| Cortex | 19001 | `cortex:9001` |
| MISP | 8083 | `misp:80` |
| Shuffle Backend | 15001 | `shuffle-backend:5001` |
| Elasticsearch | 19200 | `elasticsearch:9200` |
| Wazuh Manager | 55100 | `wazuh-manager:55000` |
| Grafana | 8084 | `grafana:3000` |

Para la configuración de Nginx, DNS local y certificados, ver
[docs/operations/ports_and_urls.md](operations/ports_and_urls.md) y
[docs/getting_started/installation_guide.md](getting_started/installation_guide.md).
