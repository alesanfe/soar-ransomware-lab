# Logging y observabilidad del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
- [2. Stack de logging centralizado](#2-stack-de-logging-centralizado)
- [3. Configuración de Promtail](#3-configuración-de-promtail)
- [4. Grafana y dashboards](#4-grafana-y-dashboards)
- [5. KPIs y fuente de verdad de métricas](#5-kpis-y-fuente-de-verdad-de-métricas)
- [6. WebSockets de la API](#6-websockets-de-la-api)
- [7. Visualizaciones reproducibles](#7-visualizaciones-reproducibles)
- [8. Diagnóstico](#8-diagnóstico)
- [9. Referencias](#9-referencias)

---

## 1. Resumen

El laboratorio centraliza logs de todos los contenedores Docker en **Loki** mediante **Promtail**, y los visualiza en **Grafana** (`http://localhost:8084`). Además, la API de gestión expone un endpoint WebSocket (`/ws/logs`) para streaming de logs en tiempo real.

---

## 2. Stack de logging centralizado

Servicios definidos en `infra/docker/compose/logging/docker-compose.logging.yml`:

| Servicio | Imagen | Puerto host | Redes | Función |
|----------|--------|-------------|-------|---------|
| Promtail | `grafana/promtail:2.9.10` | — | `soar_net`, `logging_net` | Descubre contenedores Docker y envía logs a Loki |
| Loki | `grafana/loki:2.9.10` | — | `logging_net` | Almacena y consulta logs |
| Grafana | `grafana/grafana:10.3.4` | `${GRAFANA_PORT:-8084}:3000` | `logging_net`, `soar_net` | Visualización de logs y KPIs |
| Grafana DB | `postgres:14-alpine` | — | `logging_net` | Base de datos de Grafana |

Levantar el stack:

```bash
make up
# o
docker compose -f infra/docker/compose/logging/docker-compose.logging.yml up -d
```

> **Nota:** Loki es una imagen mínima que no incluye `wget`, `curl` ni `bash`. No se le configura healthcheck ni se monta configuración externa: usa la configuración por defecto de la imagen.

---

## 3. Configuración de Promtail

Promtail se configura mediante un Docker `config`:

- Archivo origen: `infra/docker/compose/logging/promtail-config.yml`
- Destino en el contenedor: `/etc/promtail/config.yml`

Compose resuelve rutas `configs.file` relativas al directorio del primer archivo compose (`infra/docker/compose/`), por lo que la ruta correcta es `logging/promtail-config.yml` (sin `./`).

Promtail monta el socket Docker para descubrir dinámicamente los contenedores:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

```bash
# Ver logs de Promtail
docker logs -f soar_promtail
```

---

## 4. Grafana y dashboards

- URL: `http://localhost:8084`
- Credenciales por defecto: `admin` / `${GRAFANA_ADMIN_PASSWORD}` (sobrescribir en `.env.full`).
- Data source Elasticsearch se provisiona automáticamente en `/etc/grafana/provisioning/datasources/grafana-datasources.yml`.
- Dashboards provisionados desde `/etc/grafana/provisioning/dashboards/grafana-kpi-dashboard.yml`.

La contraseña del data source de Elasticsearch debe coincidir con `ELASTIC_PASSWORD` definido en `.env.full`.

```bash
# Probar datasource
curl -u admin:${GRAFANA_ADMIN_PASSWORD} http://localhost:8084/api/datasources
```

---

## 5. KPIs y fuente de verdad de métricas

Los indicadores del laboratorio fluyen de los siguientes componentes:

- **Generación**: `src/soar_lab/application/use_cases/analytics_service.py` y `src/soar_lab/domain/services/kpi_analyzer.py` calculan MTTR, detecciones y percentiles P50/P90 a partir de alertas y resultados de tests.
- **Persistencia primaria**: índice `soar-metrics` en Elasticsearch. El índice real es `soar-metrics-v2` y `soar-metrics` es un alias. Mapping:
  - `mttr_seconds` → `float`
  - `@timestamp` → `date`
  - `detected`, `contained`, `severity`, `test_id`, etc.
- **Inicialización**: `src/soar_lab/scripts/setup/init_shuffle_webhook.py` crea el índice con el mapping correcto si no existe.
- **Exportación CSV**: `artifacts/results/kpis.csv` generado por `AnalyticsService`; útil para análisis offline y para el TFM.
- **Visualización**: dashboard de Grafana `kpi-dashboard.json` consulta `soar-metrics` (`${DS_ELASTICSEARCH}`) y muestra MTTR, volumen de alertas y cumplimiento de umbrales.
- **Umbrales actuales**: p50 ≤ 120 s, p90 ≤ 180 s para el playbook E2E.
- **Fuente de verdad**: en caso de discrepancia, prevalece el **índice `soar-metrics` en Elasticsearch** (`soar-metrics-v2`); el CSV y Grafana son vistas derivadas.

## 6. WebSockets de la API

```javascript
const socket = new WebSocket('ws://localhost:8000/ws/logs');
socket.onmessage = (event) => {
    const logEntry = JSON.parse(event.data);
    console.log(logEntry);
};
```

Si el `log_reader` no está disponible, el endpoint envía entradas simuladas cada segundo.

### 6.1 Autenticación, acceso y reconexión

- El endpoint no requiere token en la apertura del socket en la implementación actual; se asume que la API está protegida por la red interna o por Nginx.
- URLs correctas:
  - Directo: `ws://localhost:8000/ws/logs`
  - Vía Nginx: `wss://soar.local/api/ws/logs` (Nginx añade `Upgrade` y `Connection`).
- Si se usa `https://soar.local`, `script.js` cambia a `wss:` y usa `soar.local` como host. Si se accede directo a `http://localhost:8000`, usa `ws:`.
- El SPA `web-management` no implementa reconexión automática. Si el socket se cierra, el usuario debe volver a pulsar *Start Live Logs*; alternativamente se puede recargar la página.
- En producción se recomienda implementar: validación de `Origin`, límite de conexiones por IP, autenticación en el handshake y reconexión con backoff exponencial.

---

## 7. Visualizaciones reproducibles

Para reproducir las visualizaciones principales sin depender de capturas de pantalla:

### 7.1 Grafana — dashboard KPI

1. Acceder a `http://localhost:8084`.
2. Seleccionar el dashboard provisionado `SOAR Ransomware KPI`.
3. El panel *MTTR* usa la consulta ES:
   ```json
   {"query":{"match_all":{}},"aggs":{"avg_mttr":{"avg":{"field":"mttr_seconds"}}}}
   ```
4. El panel *Alertas por día* agrupa `@timestamp` y `severity`.
5. Los umbrales visualizados son `P50 ≤ 120 s` y `P90 ≤ 180 s`.

### 7.2 Grafana — logs con Loki

1. Crear un panel con datasource Loki.
2. Ejemplo de consulta LogQL para ver logs de la API:
   ```logql
   {container_name="/soar_api"}
   ```
3. Filtrar por nivel:
   ```logql
   {container_name="/soar_api"} |= "ERROR"
   ```

### 7.3 Elasticsearch — verificar métricas directamente

```bash
# Número de documentos en soar-metrics
curl -s -u "elastic:${ELASTIC_PASSWORD}" \
  "http://localhost:19200/soar-metrics/_count"

# Promedio de mttr_seconds
curl -s -u "elastic:${ELASTIC_PASSWORD}" \
  -H "Content-Type: application/json" \
  -X POST "http://localhost:19200/soar-metrics/_search?size=0" \
  -d '{"aggs":{"avg_mttr":{"avg":{"field":"mttr_seconds"}}}}'
```

### 7.4 CSV offline

El archivo `artifacts/results/kpis.csv` se regenera al ejecutar tests de rendimiento o análisis y puede importarse en cualquier hoja de cálculo.

---

## 8. Diagnóstico

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| Grafana no muestra datos de Elasticsearch | Contraseña del data source no coincide con `ELASTIC_PASSWORD` | Revisar `ELASTIC_PASSWORD` en `.env.full`, regenerar con `make generate-secrets` y reiniciar Grafana |
| Grafana no resuelve `elasticsearch` | Grafana solo está en `logging_net` | Verifica que `docker-compose.logging.yml` incluya `soar_net` en el servicio `grafana` |
| Promtail no envía logs | No puede leer el socket Docker | Verifica que el volumen `/var/run/docker.sock` esté montado y Promtail tenga permisos |
| WebSocket se desconecta inmediatamente | `connection_manager` no inyectado en el app state | Reinicia el contenedor `soar_api` |

Comandos útiles:

```bash
# Logs de todos los servicios SOAR filtrados por contenedor en Loki
open http://localhost:8084/explore?orgId=1&left=%7B%22datasource%22:%22loki%22%7D

# Logs de un contenedor específico
docker logs -f soar_shuffle_backend

# Estado del stack de logging
docker compose -f infra/docker/compose/logging/docker-compose.logging.yml ps
```

---

## 7. Referencias

- [infra/docker/compose/logging/docker-compose.logging.yml](../../infra/docker/compose/logging/docker-compose.logging.yml)
- [infra/docker/compose/logging/promtail-config.yml](../../infra/docker/compose/logging/promtail-config.yml)
- [infra/docker/compose/logging/grafana-datasources.yml.template](../../infra/docker/compose/logging/grafana-datasources.yml.template) (plantilla; el fichero `.yml` se genera con `make generate-secrets`)
- [src/soar_lab/infrastructure/websocket_manager.py](../../src/soar_lab/infrastructure/websocket_manager.py)
- [src/soar_lab/interfaces/api/main.py](../../src/soar_lab/interfaces/api/main.py)
