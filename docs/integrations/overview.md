# Integraciones del SOAR Ransomware Lab

Este documento ofrece una visión general de las integraciones entre los componentes del SOAR Ransomware Lab.

## Índice

- [1. Resumen](#1-resumen)
- [2. Servicios Integrados](#2-servicios-integrados)
- [3. Flujo de Datos](#3-flujo-de-datos)
- [4. Contratos de API](#4-contratos-de-api)
- [5. Credenciales y Autenticación](#5-credenciales-y-autenticación)
- [6. Referencias](#6-referencias)
- [7. Versiones verificadas](#7-versiones-verificadas)

---

## 1. Resumen

El laboratorio integra herramientas de orquestación (Shuffle), gestión de casos (TheHive), análisis de IoCs (Cortex),
inteligencia de amenazas (MISP), detección (Wazuh) y observabilidad (Grafana, Loki, Promtail) para automatizar la
respuesta ante incidentes de ransomware.

## 2. Servicios Integrados

| Servicio            | Puerto host | Proxy Nginx (`https://soar.local`) | Rol                           | Estado                | Credenciales / Auth                         |
|---------------------|-------------|------------------------------------|-------------------------------|-----------------------|---------------------------------------------|
| **Web Management**  | 8085        | `/` (SPA principal)                | Panel de control centralizado | Implementado          | `WEB_UI_USER` / `WEB_UI_PASSWORD`           |
| **SOAR API**        | 8000        | `/api/`                            | Gestión y métricas del lab    | Implementado          | JWT Bearer (`admin` / `WEB_UI_PASSWORD`)    |
| **Shuffle UI**      | 8081        | No soportado                       | Orquestación de workflows     | Implementado          | `SHUFFLE_DEFAULT_USERNAME` / `SHUFFLE_DEFAULT_PASSWORD` |
| **Shuffle API**     | 15001       | `/shuffle-api/`                    | API del motor de Shuffle      | Implementado          | `SHUFFLE_DEFAULT_APIKEY` (incluye Orborus)  |
| **TheHive**         | 19000       | `/thehive/`                        | Gestión de casos              | Implementado          | admin / `THEHIVE_ADMIN_PASSWORD`            |
| **Cortex**          | 19001       | `/cortex/`                         | Análisis de observables       | Implementado          | admin / `CORTEX_ADMIN_PASSWORD`             |
| **MISP**            | 8083        | No soportado                       | Inteligencia de amenazas      | Implementado          | `MISP_ADMIN_EMAIL` / `MISP_ADMIN_PASSWORD`  |
| **Wazuh Manager API** | 55100     | No expuesto                        | SIEM/XDR API                  | Implementado          | `WAZUH_API_USERNAME` / `WAZUH_API_PASSWORD` |
| **Wazuh Dashboard** | 15601       | No soportado                       | Dashboards                    | Implementado          | admin / `WAZUH_INDEXER_PASSWORD`                |
| **Elasticsearch**   | 19200       | No expuesto                        | Búsqueda y almacenamiento     | Implementado          | `elastic` / `ELASTIC_PASSWORD`              |
| **Redis**           | N/A (no expuesto) | No expuesto                        | Caché y colas                 | Implementado          | `REDIS_PASSWORD`                            |
| **Grafana**         | 8084        | No soportado                       | Observabilidad y KPIs         | Implementado          | admin / `GRAFANA_ADMIN_PASSWORD`                |
| **docs-site**       | 8086        | No soportado                       | Documentación web             | Implementado          | -                                           |

> **Nota:** Los valores por defecto se toman de `.env.example`. En un despliegue real se generan con
> `soar-lab generate-secrets --env`. La interfaz de Shuffle no se sirve por Nginx porque usa rutas absolutas; el
> acceso directo por `http://localhost:8081` es obligatorio.

## 3. Flujo de Datos

1. **Detección**: Wazuh genera alertas y las envía a un webhook de Shuffle (configurado en
   `src/soar_lab/scripts/setup/init_shuffle_webhook.py`).
2. **Orquestación**: Shuffle recibe la alerta, la normaliza y lanza el workflow de respuesta.
3. **Análisis**: Cortex ejecuta analyzers sobre observables (hash, IP, dominio, etc.). Los analyzers se lanzan en
   contenedores efímeros gestionados por Orborus.
4. **Inteligencia**: MISP enriquece con IoCs y feeds de amenazas.
5. **Gestión**: TheHive crea un caso con observables, resultados de analyzers y métricas.
6. **Contención**: La contención del endpoint se simula en entornos controlados mediante scripts y APIs; la ejecución
   real sobre endpoints de producción queda fuera del alcance del laboratorio.
7. **Métricas**: Los KPIs (MTTR, etc.) se calculan en Shuffle, se indexan en el índice `soar-metrics` de Elasticsearch y se
   visualizan en el dashboard de Grafana.

> **Real vs. simulado:** Wazuh, TheHive, Cortex, MISP, Shuffle, Elasticsearch y Grafana son servicios reales levantados con
> Docker. Las acciones de contención sobre endpoints son simuladas salvo que se configuren agentes reales en la red de
> pruebas.

## 3.x Workarounds y limitaciones conocidas

### Cortex y MISP

- **Cortex** puede devolver `400` en workflows que requieren autenticación adicional o analyzers no inicializados. En `tests/e2e/TC-03/test_edge_cases.py` se omite la verificación de Cortex temporalmente (`TODO`).
- **MISP** puede devolver respuesta vacía por `403` o falta de eventos. El test TC-03 la omite mientras se ajusta la autenticación.

### Shuffle

- El webhook de Shuffle se crea con `init_shuffle_webhook.py`, que ajusta el workflow y genera `webhook_info.json`.
- Tras `make reset`, el `SHUFFLE_DEFAULT_APIKEY` cambia. `ShuffleClient` se auto-sana (`_fetch_real_apikey`) leyendo la clave de Elasticsearch.

### Elasticsearch / Grafana

- El índice real de métricas es `soar-metrics-v2`; `soar-metrics` es un alias. Esto corrige un mapping anterior donde `mttr_seconds` era `object`.
- Grafana 13 requiere el plugin `elasticsearch` como `GF_INSTALL_PLUGINS` y debe estar en `soar_net` para resolver `elasticsearch:9200`.

### Wazuh

- La API requiere contraseña compleja sin `@` ni `!` (p. ej. `<WAZUH_API_PASSWORD>`).
- Nginx depende de `wazuh.manager` en estado `service_started`, no `service_healthy`, por el tiempo de arranque.

## 4. Contratos de API

Los contratos detallados, endpoints, ejemplos de payloads y procedimientos de rotación de API keys se encuentran en:

- **[api_contracts.md](api_contracts.md)**
- **[API_DOCUMENTATION.md](../API_DOCUMENTATION.md)** (documentación completa de APIs)

## 5. Credenciales y Autenticación

Todas las contraseñas por defecto se definen en `.env.full` y se mantienen sincronizadas con los scripts de
inicialización:

- `init_thehive.py` genera el usuario y API key de TheHive.
- `reset_cortex.py` genera el usuario y API key de Cortex.
- `init_shuffle_webhook.py` configura el workflow y el API key de Shuffle.

Las claves más relevantes de `.env.full` son:

- `THEHIVE_API_KEY`
- `CORTEX_API_KEY`
- `SHUFFLE_DEFAULT_APIKEY`
- `MISP_API_KEY`
- `WAZUH_API_PASSWORD`
- `ELASTIC_PASSWORD`
- `REDIS_PASSWORD`
- `GRAFANA_ADMIN_PASSWORD`
- `WEB_UI_PASSWORD`

## 6. Referencias

- [api_contracts.md](api_contracts.md)
- [API_DOCUMENTATION.md](../API_DOCUMENTATION.md)
- [docs/architecture/overview.md](../architecture/overview.md)
- [docs/operations/configuration_manual.md](../operations/configuration_manual.md)
- [docs/architecture/version_matrix.md](../architecture/version_matrix.md)

## 7. Versiones verificadas

Las versiones canónicas de los componentes principales se consultan directamente en `infra/docker/compose/docker-compose.core.yml` y en [docs/architecture/version_matrix.md](../architecture/version_matrix.md).

| Componente | Versión verificada | Fuente | Documentación oficial |
|------------|--------------------|--------|-----------------------|
| **Shuffle** | `2.2.1` (`ghcr.io/shuffle/shuffle-frontend/backend/orborus:2.2.1`) | `infra/docker/compose/docker-compose.core.yml` | <https://shuffler.io/docs> |
| **TheHive** | `3.5.2-1` (`thehiveproject/thehive:3.5.2-1`) | `infra/docker/compose/docker-compose.core.yml` | <https://docs.strangebee.com/thehive/> |
| **Cortex** | `3.1.7-1` (imagen compatible con TheHive 3.x) | `infra/docker/compose/docker-compose.core.yml` | <https://docs.strangebee.com/cortex/> |
| **MISP** | `latest` (digest recomendado en producción) | `infra/docker/compose/docker-compose.misp.yml` | <https://www.misp-project.org/documentation/> |
| **Wazuh** | `4.14.0` | `infra/docker/compose/docker-compose.wazuh.yml` | <https://documentation.wazuh.com/> |
| **Elasticsearch** | `7.10.2` | `infra/docker/compose/docker-compose.yml` | <https://www.elastic.co/guide/en/elasticsearch/reference/7.10/index.html> |
| **OpenSearch** | `2.10.0` | `infra/docker/compose/docker-compose.opensearch.yml` | <https://opensearch.org/docs/latest/> |

> **Nota:** La imagen TheHive `3.5.2-1` es la que se despliega; la documentación de StrangeBee cubre tanto TheHive 3 como TheHive 5. La API y los endpoints principales no cambian para las operaciones usadas en este laboratorio.
