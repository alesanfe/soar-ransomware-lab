# Plan de Migración a OpenSearch (Producción)

## Objetivo

Migrar el stack SOAR Ransomware Lab de Elasticsearch 7.10.2 a OpenSearch 2.10.0 para resolver la incompatibilidad de
Shuffle 2.2.1 con Elasticsearch (error 405 GET /{index}/_doc/).

## Estado actual

> **Situación real (julio 2026):** el stack SOAR principal sigue usando Elasticsearch 7.10.2 para Shuffle, TheHive 3.5.2, la API del laboratorio y las métricas `soar-metrics`. Wazuh ya opera con su propio OpenSearch embebido (`wazuh/wazuh-indexer:4.14.0`) de forma independiente; no se ha migrado el resto del stack.

| Servicio      | Imagen actual                                          | Estado                           |
|---------------|--------------------------------------------------------|----------------------------------|
| Elasticsearch | `docker.elastic.co/elasticsearch/elasticsearch:7.10.2` | Activo en SOAR core; incompatible con operaciones de índice de Shuffle 2.2.1 (error 405 GET /{index}/_doc/) |
| Kibana        | `docker.elastic.co/kibana/kibana:7.10.2`               | No desplegado en el stack actual; dependiente de ES si se usara |
| TheHive       | `thehiveproject/thehive:3.5.2-1`                       | NO compatible con OpenSearch 2.x |
| Shuffle       | `ghcr.io/shuffle/shuffle-backend:2.2.1`                | Compatible con OpenSearch; actualmente apunta a Elasticsearch 7.10.2 |
| Wazuh         | `wazuh/wazuh-manager:4.14.0`                           | Usa `wazuh-indexer:4.14.0` (OpenSearch embebido); compatible con OpenSearch 2.10.0 |
| MISP          | `ghcr.io/misp/misp-docker/misp-core:latest`            | No depende de ES                 |

## Arquitectura objetivo

| Servicio              | Imagen objetivo                                           | Notas                                    |
|-----------------------|-----------------------------------------------------------|------------------------------------------|
| OpenSearch            | `opensearchproject/opensearch:2.10.0`                     | Reemplaza Elasticsearch                  |
| OpenSearch Dashboards | `opensearchproject/opensearch-dashboards:2.10.0`          | Reemplaza Kibana                         |
| TheHive               | `strangebee/thehive:5.4.0` o `thehiveproject/thehive:4.1` | TheHive 4/5 es compatible con OpenSearch |
| Cortex                | `strangebee/cortex:3.1.7`                                 | Necesita TheHive 4/5                     |
| Wazuh Indexer         | `wazuh/wazuh-indexer:4.14.0`                              | Reemplaza Elasticsearch para Wazuh       |
| Wazuh Dashboard       | `wazuh/wazuh-dashboard:4.14.0`                            | Reemplaza Kibana para Wazuh              |
| Shuffle               | Se mantiene                                               | Apunta a OpenSearch                      |
| MISP                  | Se mantiene                                               | -                                        |

## Pasos de migración

### Fase 1: Preparación (backup)

1. Detener todos los contenedores
2. Backup de volúmenes (`es_data`, `kibana_data`, `thehive_files`, `cortex_data`, `wazuh_*`)
3. Snapshot de índices Elasticsearch en path de backup
4. Guardar configuraciones de `.env.full`

### Fase 2: Actualizar componentes

1. Reemplazar `infra/docker/compose/docker-compose.yml`:
    - `elasticsearch:7.10.2` → `opensearch:2.10.0`
    - Ajustar variables de entorno de OpenSearch
    - Cambiar puerto/paths si es necesario
    - Ajustar healthcheck
2. Reemplazar `infra/docker/compose/docker-compose.core.yml`:
    - `thehive:3.5.2-1` → `thehive:5.4.0` (o 4.1)
    - Añadir configuración de conexión a OpenSearch
    - Añadir Cortex si no existe
3. Reemplazar `infra/docker/compose/docker-compose.wazuh.yml`:
    - Añadir `wazuh-indexer:4.14.0`
    - Añadir `wazuh-dashboard:4.14.0`
    - Eliminar Kibana 7.10.2
4. Configurar Shuffle para apuntar a OpenSearch:
    - `SHUFFLE_OPENSEARCH_URL=http://opensearch:9200`
    - `SHUFFLE_ELASTIC=true`

### Fase 3: Migración de datos

Opción A - Snapshot/Restore (recomendada si es viable):

1. Crear snapshot en Elasticsearch 7.10.2
2. Montar snapshot en OpenSearch 2.10.0
3. Restaurar índices

Opción B - Reindexación:

1. Iniciar OpenSearch vacío
2. Usar Logstash con input Elasticsearch y output OpenSearch
3. Reindexar datos relevantes

Opción C - Fresh deploy (para lab nuevo):

1. No migrar datos
2. Reconfigurar Shuffle/TheHive/Wazuh desde cero

### Fase 4: Validación

1. Health check OpenSearch: `GET /_cluster/health`
2. Health check Shuffle: `GET /api/v1/health`
3. TheHive 4/5 se conecta a OpenSearch
4. Wazuh Indexer se conecta
5. Tests de integración: `pytest tests/integration/test_shuffle_integration.py`
6. Tests E2E: `pytest tests/e2e/`

### Fase 5: Ajustes

1. Actualizar datasources de Grafana (la URL puede seguir siendo `opensearch:9200`)
2. Reemplazar dashboards de Kibana por OpenSearch Dashboards
3. Documentar nuevas URLs y credenciales
4. Actualizar `nginx` si redirige a Kibana

## Riesgos identificados

| Riesgo                                                                                  | Impacto | Mitigación                       |
|-----------------------------------------------------------------------------------------|---------|----------------------------------|
| TheHive 3.5.2 → 4/5 requiere migración de base de datos                                 | Alto    | Backup + test en staging         |
| Cortex con OpenSearch 2.x puede requerir `compatibility.override_main_response_version` | Medio   | Probar con TheHive 4/5           |
| Kibana dashboards no migran automáticamente                                             | Medio   | Recrear en OpenSearch Dashboards |
| Elasticsearch 7.10.2 → OpenSearch 2.10.0 snapshot puede fallar                          | Medio   | Usar reindexación como fallback  |
| Wazuh 4.14.0 incluye manager, indexer y dashboard en `docker-compose.wazuh.yml`           | Medio   | Validar TLS e Indexer URL        |

## Decisión pendiente

Para migrar a OpenSearch en producción es necesario:

1. Actualizar TheHive 3.5.2 a TheHive 4/5
2. Reemplazar Kibana por OpenSearch Dashboards
3. Añadir Wazuh Indexer y Dashboard
4. Migrar/resetear datos

## Recomendación

Para un entorno de producción real, la migración a OpenSearch es la solución correcta y gratuita. Sin embargo, requiere
un esfuerzo de migración significativo y no puede hacerse en un solo paso sin validar cada componente.

## Primer paso sugerido

Realizar una migración por fases, empezando por un entorno de staging donde:

1. Se reemplace Elasticsearch por OpenSearch 2.10.0
2. Se valide que Shuffle funciona correctamente
3. Se integre TheHive 4/5 con OpenSearch
4. Se migre Wazuh a Wazuh Indexer

## Plan de rollback

| Paso | Acción | Comando / Referencia |
|------|--------|----------------------|
| 1 | Detener stack migrado | `docker compose -f infra/docker/compose/docker-compose.yml -f ... down` |
| 2 | Restaurar volúmenes desde backup (`es_data`, `thehive_files`, `cortex_data`) | `docker volume rm ...` y recrear desde snapshot o `tar` |
| 3 | Restaurar `.env.full` y compose files originales | `git checkout -- .env.full infra/docker/compose/*.yml` |
| 4 | Levantar stack original con Elasticsearch 7.10.2 y TheHive 3.5.2-1 | `make up` |
| 5 | Verificar healthchecks (`GET /_cluster/health`, TheHive `/api/status`, `/health`) | `curl` / `docker ps` |
| 6 | Re-ejecutar `pytest tests/e2e/` y `tests/integration/test_shuffle_integration.py` | `pytest` |

> **Nota:** Conservar siempre los backups de volúmenes y snapshots antes de iniciar la migración. El rollback completo es viable si los volúmenes originales no se eliminaron (`docker compose down -v` sin backup implica pérdida de datos).

## Decisiones sobre métricas de Grafana

- **Datasource actual:** Grafana apunta a `elasticsearch:9200` con índice `soar-metrics` (alias a `soar-metrics-v2`). En OpenSearch, el datasource debe seguir apuntando al mismo nombre de servicio (`opensearch:9200`) tras levantar el contenedor reemplazado.
- **Mapping `soar-metrics`:** el mapping vigente (`mttr_seconds` float, `@timestamp` date) se replica en OpenSearch mediante `init_shuffle_webhook.py` o script equivalente.
- **Dashboards:** `infra/docker/compose/logging/kpi-dashboard.json` usa consultas Elasticsearch DSL compatibles con OpenSearch 2.x; no requieren cambios sintácticos, solo actualizar el datasource UID si se regenera.
- **Decisiones pendientes:**
  1. Si se usa `compatibility.override_main_response_version` en OpenSearch para TheHive/Cortex, documentar el flag en `docker-compose.yml`.
  2. Evaluar si se reemplaza Grafana datasource por `grafana-opensearch-datasource` plugin para soportar funciones avanzadas; esto es opcional.
