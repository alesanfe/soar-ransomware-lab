# Matriz de versiones técnicas

Esta matriz resume las versiones canónicas de las dependencias, imágenes Docker y herramientas utilizadas en el repositorio. La fuente de verdad sigue siendo `pyproject.toml`, los archivos `docker-compose*.yml` y `.github/workflows/ci.yml`.

## Proyecto

| Componente | Versión / Requisito | Fuente |
|------------|---------------------|--------|
| `soar-lab` (proyecto) | `1.4.0` | `pyproject.toml` |
| Python | `>=3.11` | `pyproject.toml` |
| Node.js (docs-site) | `>=18.0` | `apps/docs-site/package.json` |
| Docusaurus | `^3.0.0` | `apps/docs-site/package.json` |
| React | `^18.2.0` | `apps/docs-site/package.json` |

## Dependencias principales (Python)

| Paquete | Versión mínima | Fuente |
|---------|----------------|--------|
| FastAPI | `>=0.100.0` | `pyproject.toml` |
| Uvicorn | `>=0.23.0` | `pyproject.toml` |
| Pydantic | `>=2.0.0` | `pyproject.toml` |
| Redis (cliente) | `>=4.0.0` | `pyproject.toml` |
| Docker SDK | `>=6.0.0` | `pyproject.toml` |
| psutil | `>=5.9.0` | `pyproject.toml` |

## Calidad de código y tests

| Herramienta | Versión / Configuración | Fuente |
|-------------|-------------------------|--------|
| pytest | `>=7.0.0` | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| pytest-cov | `>=4.0.0` | `pyproject.toml` |
| pytest-asyncio | `>=0.21.0` | `pyproject.toml` |
| Black | `>=23.0.0` / longitud `100` / `py311` | `pyproject.toml`, `.pre-commit-config.yaml` |
| isort | `>=5.12.0` / perfil `black` | `pyproject.toml`, `.pre-commit-config.yaml` |
| flake8 | `>=6.0.0` / `max-line-length=100` | `pyproject.toml`, `.pre-commit-config.yaml` |
| mypy | `>=1.0.0` / `python_version=3.11` | `pyproject.toml` |
| pre-commit | `>=3.0.0` | `pyproject.toml` |
| ShellCheck | (versión del runner) | `.github/workflows/ci.yml` |

## Imágenes Docker

### Core / SOAR

| Servicio | Imagen | Fuente |
|----------|--------|--------|
| Redis | `redis:7-alpine` | `infra/docker/compose/docker-compose.core.yml` |
| TheHive | `thehiveproject/thehive:3.5.2-1` | `infra/docker/compose/docker-compose.core.yml` |
| Shuffle Frontend | `ghcr.io/shuffle/shuffle-frontend:2.2.1` | `infra/docker/compose/docker-compose.core.yml` |
| Shuffle Backend | `ghcr.io/shuffle/shuffle-backend:2.2.1` | `infra/docker/compose/docker-compose.core.yml` |
| Shuffle Orborus | `ghcr.io/shuffle/shuffle-orborus:2.2.1` | `infra/docker/compose/docker-compose.core.yml` |
| Tenzir Node | `tenzir/tenzir:main` | `infra/docker/compose/docker-compose.core.yml` |
| Nginx | `nginx:1.25-alpine` | `infra/docker/compose/docker-compose.api.yml` |

### Bases de datos e índices

| Servicio | Imagen | Fuente |
|----------|--------|--------|
| Elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch:7.10.2` | `infra/docker/compose/docker-compose.yml` |
| OpenSearch | `opensearchproject/opensearch:2.10.0` | `infra/docker/compose/docker-compose.opensearch.yml` |
| OpenSearch Dashboards | `opensearchproject/opensearch-dashboards:2.10.0` | `infra/docker/compose/docker-compose.opensearch.yml` |
| Grafana DB (Postgres) | `postgres:14-alpine` | `infra/docker/compose/logging/docker-compose.logging.yml` |

### Logging y observabilidad

| Servicio | Imagen | Fuente |
|----------|--------|--------|
| Grafana | `grafana/grafana:10.3.4` | `infra/docker/compose/logging/docker-compose.logging.yml` |
| Loki | `grafana/loki:2.9.10` | `infra/docker/compose/logging/docker-compose.logging.yml` |
| Promtail | `grafana/promtail:2.9.10` | `infra/docker/compose/logging/docker-compose.logging.yml` |

### MISP

| Servicio | Imagen | Fuente |
|----------|--------|--------|
| MISP DB | `mariadb:10.11` | `infra/docker/compose/docker-compose.misp.yml` |
| MISP Core | `ghcr.io/misp/misp-docker/misp-core:latest` | `infra/docker/compose/docker-compose.misp.yml` |
| MISP Modules | `ghcr.io/misp/misp-docker/misp-modules:latest` | `infra/docker/compose/docker-compose.misp.yml` |

### Wazuh

| Servicio | Imagen | Fuente |
|----------|--------|--------|
| Wazuh Manager | `wazuh/wazuh-manager:4.14.0` | `infra/docker/compose/docker-compose.wazuh.yml` |
| Wazuh Indexer | `wazuh/wazuh-indexer:4.14.0` | `infra/docker/compose/docker-compose.wazuh.yml` |
| Wazuh Dashboard | `wazuh/wazuh-dashboard:4.14.0` | `infra/docker/compose/docker-compose.wazuh.yml` |
| Generador de certificados Wazuh | `wazuh/wazuh-certs-generator:0.0.2` | `infra/docker/compose/wazuh/generate-indexer-certs.yml` |

## CI/CD y runners

| Componente | Versión | Fuente |
|------------|---------|--------|
| GitHub Actions runner | `ubuntu-latest` | `.github/workflows/ci.yml` |
| Python CI | `3.11` | `.github/workflows/ci.yml` |
| Node.js CI | `20` | `.github/workflows/ci.yml` |
| Trivy | `master` (`aquasecurity/trivy-action`) | `.github/workflows/ci.yml` |

## Notas de coherencia

- El proyecto requiere **Python 3.11+** en `pyproject.toml` y en `.github/workflows/ci.yml`.
- `apps/docs-site/package.json` declara `node>=18.0`, mientras que CI usa `node-version: '20'`; ambas son compatibles.
- `tenzir/tenzir:main` no está fijada a una versión semántica: se recomienda pin a una etiqueta release en producción.
- Las imágenes `misp-core` y `misp-modules` usan `latest`; esto puede introducir variabilidad en despliegues reproducibles. Considerar fijar a un digest SHA.
- Las versiones de Shuffle (`2.2.1`) y TheHive (`3.5.2-1`) coinciden con las variables documentadas en `docs/integrations/overview.md` y `docs/architecture/overview.md`.
