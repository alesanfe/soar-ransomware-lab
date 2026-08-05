# Coexistencia de Elasticsearch y OpenSearch

## Resumen de la decisión

El laboratorio despliega **dos motores de búsqueda simultáneamente**: Elasticsearch 7.10.2 y OpenSearch 2.10.0. Esta no es una redundancia accidental, sino una decisión técnica forzada por las incompatibilidades de las dependencias de cada servicio.

| Servicio | Motor de búsqueda | Motivo |
|---|---|---|
| TheHive 3.5.2 | Elasticsearch 7.10.2 | `elastic4play` no envía credenciales REST de forma fiable con `xpack.security.enabled=true` y presenta problemas de mapeo (`include_type_name`) con ES 8.x/OpenSearch 2.x. |
| Cortex 3.2.0 | Elasticsearch 7.10.2 | Misma librería subyacente que TheHive (`elastic4play` / `elastic4s`). Requiere API 7.x. |
| Lab API / KPI / Grafana | Elasticsearch 7.10.2 | Los datasources de Grafana y los índices de KPI (`soar-metrics`, `soar-alerts`) se crean sobre Elasticsearch. |
| Shuffle 2.2.1 | OpenSearch 2.10.0 | El backend y `orborus` de Shuffle usan el cliente de OpenSearch y no funcionan correctamente con Elasticsearch 8.x. |

## Por qué no se consolidó en un único motor

- **Shuffle** migró a OpenSearch porque el cliente/ backend no era compatible con Elasticsearch 8.x y la gestión de `include_type_name` era problemática.
- **TheHive/Cortex** permanecen en Elasticsearch 7.10.2 porque `elastic4play` está atado a la API 7.x. Subir a Elasticsearch 8.x o a OpenSearch 2.x genera errores de mapeo y autenticación REST.
- **Wazuh Indexer/Dashboard** utiliza internamente un fork de OpenSearch (`wazuh/wazuh-indexer` y `wazuh/wazuh-dashboard`), por lo que ya hay una tercera instancia basada en OpenSearch en la pila.

## Configuración actual

### Elasticsearch (`soar_elasticsearch`)

- Imagen: `docker.elastic.co/elasticsearch/elasticsearch:7.10.2`
- Red: `soar_net`
- Seguridad: `xpack.security.enabled=false` (necesario para evitar errores de *missing authentication credentials* en TheHive/Cortex).
- Credenciales en `.env.full`:
  - `ELASTIC_USERNAME=elastic`
  - `ELASTIC_PASSWORD=ElasticLab2024SecurePass`
- Configuración de aplicaciones:
  - `infra/docker/config/thehive.application.conf/thehive.conf`
  - `infra/docker/config/cortex.application.conf/cortex.conf`
- Scripts que interactúan con ES:
  - `src/soar_lab/scripts/setup/configure_es.py`
  - `src/soar_lab/scripts/setup/reset_cortex.py`
  - `src/soar_lab/scripts/setup/init_thehive.py`
  - `src/soar_lab/scripts/setup/init_shuffle_webhook.py`

### OpenSearch (`soar_opensearch`)

- Imagen: `opensearchproject/opensearch:2.10.0`
- Red: `soar_net`
- Seguridad: `plugins.security.disabled=true`
- Credenciales en `.env.full`:
  - `OPENSEARCH_USERNAME=admin`
  - `OPENSEARCH_PASSWORD=<generado por make generate-secrets>`
- Servicios consumidores:
  - `shuffle-backend` (`SHUFFLE_OPENSEARCH_URL=http://opensearch:9200`)
  - `orborus` (`SHUFFLE_OPENSEARCH_URL=http://opensearch:9200`)

## Dependencias en Docker Compose

- `thehive` y `cortex` dependen de `elasticsearch`.
- `shuffle-backend` y `orborus` dependen de `opensearch`.
- `api` se comunica con `elasticsearch` para health-checks y métricas.

## Riesgos y consideraciones

- **Doble consumo de recursos**: cada nodo aloca ~2 GB de heap (`ES_JAVA_OPTS` / `OPENSEARCH_JAVA_OPTS`). En entornos con poca RAM puede ser necesario escalar verticalmente.
- **Backups coherentes**: hay que respaldar dos conjuntos de datos (`soar_es_data` y `soar_opensearch_data`).
- **Hoja de ruta futura**: cuando TheHive/Cortex o sus forks soporten OpenSearch 2.x de forma nativa, Elasticsearch podrá eliminarse y Shuffle/OpenSearch/Wazuh Indexer podrían compartir un único clúster.

## Cómo verificar el estado de ambos motores

```powershell
# Elasticsearch
curl -sf http://localhost:19200/_cluster/health

# OpenSearch
curl -sf http://localhost:19200/_cluster/health  # OpenSearch escucha en 9200 interno, mapeado a 19200 en host según .env.full
```

Para ver qué servicios usan cada motor, consultar:

- `infra/docker/compose/docker-compose.yml` (Elasticsearch)
- `infra/docker/compose/docker-compose.opensearch.yml` (OpenSearch)
- `infra/docker/compose/docker-compose.core.yml` (TheHive, Cortex, Shuffle)
