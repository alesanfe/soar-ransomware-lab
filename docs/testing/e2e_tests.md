# E2E Tests

Tests end-to-end (E2E) para el proyecto SOAR Ransomware Lab. Estos tests validan el flujo completo del sistema desde la
recepción de una alerta hasta la respuesta automatizada.

## Propósito

Los tests E2E validan:

- Flujo completo de ransomware detection
- Integración de todos los servicios
- Coordinación de workflows
- Generación y uso de IOCs
- Actualización de métricas KPI
- Respuesta automatizada a incidentes

## Requisitos

### Servicios Requeridos

Todos los servicios deben estar en ejecución:

- **Elasticsearch**: `localhost:19200`
- **MISP**: `localhost:8083`
- **TheHive**: `localhost:19000`
- **Shuffle**: `localhost:8081`
- **Wazuh**: `localhost:55100`
- **Grafana**: `localhost:8084`
- **Promtail/Loki**: Logging stack

### Configuración Requerida

- `.env.full` configurado con todas las credenciales
- Webhook Shuffle inicializado
- Índices Elasticsearch creados
- Workflows Shuffle configurados

## Preparación del Entorno

El flujo canónico utiliza los targets de `make`. No se recomienda levantar el stack con `docker compose up -d` directamente porque `make` configura `.env.full`, perfiles, secretos y datos previos.

```bash
# 1. Generar secretos e IOCs de prueba
make generate-secrets
make generate-iocs

# 2. Limpiar entorno previo y levantar stack completo
make reset
make up

# 3. Verificar salud de los servicios
make health

# 4. Inicializar workflow y webhook de Shuffle
make init-webhook
```

### Verificar configuración

```bash
# Verificar Elasticsearch
curl -u "elastic:$ELASTIC_PASSWORD" http://localhost:19200/_cluster/health

# Verificar MISP
curl -H "Authorization: $MISP_API_KEY" http://localhost:8083/users/me

# Verificar Shuffle (API backend en 15001)
curl -H "Authorization: $SHUFFLE_DEFAULT_APIKEY" http://localhost:15001/api/v1/workflows
```

## Ejecución

### Ejecutar todos los tests E2E

```bash
make test-e2e
```

> **Nota:** `make test-e2e` ejecuta `pytest tests/e2e -v --no-cov` dentro del contenedor `soar_api`. Ejecutar `pytest tests/e2e/ -v` directamente en host puede fallar si el entorno no está preparado.

### Ejecutar tests específicos

```bash
# Tests de casos específicos
pytest tests/e2e/TC-01/ -v
pytest tests/e2e/TC-02/ -v

# Tests de KPI
pytest tests/e2e/TC-KPI-01/ -v
```

### Ejecutar con timeout extendido

```bash
pytest tests/e2e/ -v --timeout=300
```

### Ejecutar en modo verbose

```bash
pytest tests/e2e/ -v -s
```

## Catálogo de escenarios E2E

> **Nota:** La suite E2E evoluciona con el proyecto. Para obtener el listado real y recogible en cualquier entorno,
> ejecutar `python -m pytest tests/e2e --collect-only -q`.

### Escenarios funcionales representativos

| Caso | Archivo(s) | Objetivo | Servicios implicados | Artefactos generados |
|------|------------|----------|---------------------|----------------------|
| TC-00 | `TC-00/test_both_workflows*.py` | Validar comparación entre workflows de ransomware y benigno | Shuffle, TheHive | `webhook_info.json` |
| TC-01 | `TC-01/test_malicious.py` | Flujo completo de alerta maliciosa: recepción, caso y contención simulada | Shuffle, TheHive, Elasticsearch | Caso en TheHive, métricas en `soar-metrics` |
| TC-02 | `TC-02/test_benign.py` | Flujo de alerta benigna sin contención | Shuffle, TheHive | Caso cerrado/marcado benigno |
| TC-03 | `TC-03/test_edge_cases.py` | Manejo de casos límite (campos faltantes, URLs inválidas, concurrencia) | Shuffle, API | Logs de ejecución |
| TC-04 | `TC-04/test_performance.py` | Métricas de rendimiento bajo carga controlada | API, Elasticsearch | Métricas de latencia |
| TC-05 | `TC-05/test_concurrent_alerts.py` | Procesamiento concurrente de alertas | Shuffle, orborus | Múltiples ejecuciones de workflow |
| TC-06 | `TC-06/test_critical_severity.py` | Priorización por severidad crítica | Shuffle, TheHive | Caso crítico con escalación |
| TC-07 | `TC-07/test_missing_fields.py` | Robustez ante alertas con campos incompletos | API, Shuffle | Errores controlados |
| TC-08 | `TC-08/test_additional_fields.py` | Campos personalizados y extensibilidad de alertas | Shuffle, TheHive | Caso con observables extra |
| TC-09 | `TC-09/test_alert_simulation_accuracy.py`, `test_realistic_ransomware.py` | Fidelidad del simulador frente a ransomware real | API, Shuffle, Wazuh (simulado) | Alertas enriquecidas |
| TC-10 | `TC-10/test_tenzir_integration.py` | Integración con Tenzir (planificada/parcial) | Tenzir | Logs exportados |
| TC-11 | `TC-11/test_network_watcher_integration.py` | Conectividad del Network Watcher con la red de Shuffle | Docker, `soar_net` | Estado de red verificado |
| TC-12 | `TC-12/test_redis_integration.py` | Estado compartido y caché vía Redis | Redis | Claves de prueba |
| TC-13 | `TC-13/test_loki_integration.py` | Logging centralizado Loki/Promtail/Grafana | Logging stack | Logs consultables en Grafana |
| TC-14 | `TC-14/test_complete_soar_integration.py`, `test_traceability.py` | Flujo SOAR completo y trazabilidad de ejecución | Todos | Métricas, casos, logs enlazados |
| TC-15 | `TC-15/test_api_latency.py` | Latencia de endpoints críticos | API | Métricas de latencia |
| TC-16 | `TC-16/test_error_handling.py`, `test_error_rate.py` | Manejo y tasa de errores | API, Shuffle | Reporte de errores |
| TC-17 | `TC-17/test_network_watcher_monitoring.py` | Monitoreo del Network Watcher | Docker, Prometheus | Métricas de red |
| TC-18 | `TC-18/test_resilience.py`, `test_workflow_recovery.py` | Recuperación ante fallos de workflow | Shuffle, orborus | Reintentos exitosos |
| TC-19 | `TC-19/test_security.py` | Validación de autenticación y seguridad | API, JWT | Tokens validados |
| TC-20 | `TC-20/test_zero_trust.py` | Validación de políticas de acceso | API, Nginx | Políticas aplicadas |
| TC-21 | `TC-21/test_forensic.py` | Recolección de evidencia digital | Wazuh, MISP, TheHive | Evidencias adjuntas |
| TC-22 | `TC-22/test_persistence.py` | Persistencia de datos tras reinicios | SQLite, Elasticsearch | Datos recuperados |
| TC-23 | `TC-23/test_privacy.py` | Anonimización y privacidad de datos | API, Elasticsearch | Datos anonimizados |
| TC-24 | `TC-24/test_malware_specific.py` | Detección de comportamiento ransomware | MISP, Wazuh (simulado) | IoCs de malware |
| TC-25 | `TC-25/test_behavioral_detection.py` | Detección basada en comportamiento | Shuffle, Cortex (parcial) | Análisis de comportamiento |
| TC-26 | `TC-26/test_extreme_load.py` | Carga extrema y estabilidad | Todo el stack | Métricas de saturación |
| TC-27 | `TC-27/test_configuration.py` | Validación de configuración del entorno | CLI, `.env.full` | Configuración verificada |
| TC-28 | `TC-28/test_ui_e2e.py` | Navegación básica de la Web Management | Selenium (opcional) | Capturas/logs |
| TC-29 | `TC-29/test_large_evidence.py` | Manejo de grandes volúmenes de evidencia | Wazuh, TheHive | Evidencias grandes |
| TC-30 | `TC-30/test_offline_mode.py` | Modo offline y mocks de servicios | API, mocks | Tests aislados |
| TC-31 | `TC-31/test_compliance.py` | Cumplimiento de controles de seguridad | API, Wazuh | Reporte de compliance |
| TC-32 | `TC-32/test_golden_thread.py` | Trazabilidad completa del flujo E2E | Todos | Golden thread verificado |
| TC-KPI-01 | `TC-KPI-01/test_mttr_calculation.py` | Cálculo de MTTR | Elasticsearch, `soar-metrics` | Valor MTTR |
| TC-KPI-02 | `TC-KPI-02/test_kpi_dashboard.py` | Disponibilidad del dashboard Grafana | Grafana, Elasticsearch | Dashboard accesible |
| TC-KPI-03 | `TC-KPI-03/test_kpi_alerts.py` | KPIs derivados de alertas | Elasticsearch | Métricas indexadas |
| TC-KPI-04 | `TC-KPI-04/test_mttr_percentiles.py` | Percentiles de respuesta | Elasticsearch, `soar-metrics` | P50/P95 |
| TC-KPI-05 | `TC-KPI-05/test_service_success_rates.py` | Tasa de éxito de servicios | API, Elasticsearch | Ratios por servicio |
| TC-KPI-06 | `TC-KPI-06/test_kpi_data_coherence.py` | Coherencia entre KPIs y datos de origen | Elasticsearch, API | Validación cruzada |

### Targets Make y comandos canónicos

```bash
# Ejecutar toda la suite E2E
make test-e2e

# Casos individuales (targets make disponibles)
make test-e2e-tc01
make test-e2e-tc02
make test-e2e-tc10
make test-e2e-tc11
make test-e2e-tc12
make test-e2e-tc13
make test-e2e-tc14
make test-e2e-tc16
make test-e2e-tc18
make test-e2e-tc24
make test-e2e-tc26
make test-e2e-tc27
make test-e2e-tc30
make test-e2e-tc32
make test-e2e-kpi

# Alternativa directa con pytest (tras make up + make health)
python -m pytest tests/e2e/TC-01/ -v
python -m pytest tests/e2e/TC-03/ -v --timeout=300
python -m pytest tests/e2e/TC-KPI-01/ -v

# Recolección reproducible (fuente de verdad para conteos)
python -m pytest tests/e2e --collect-only -q
```

### Estructura de directorios

```
tests/e2e/
├── TC-00/ to TC-32/        # Casos de prueba funcionales
├── TC-KPI-01/ to TC-KPI-06/ # Casos de validación de KPIs
├── assertions/              # Helpers de aserciones compartidas
├── conftest.py              # Fixtures globales (clientes, alertas, credenciales)
├── fixtures/                # Datos de prueba
├── helpers/                 # Utilidades de los tests E2E
└── pytest.ini               # Configuración específica de la suite E2E
```

## Fixtures

El archivo `conftest.py` en este directorio contiene fixtures específicos para tests E2E:

- `alert_from_wazuh`: Alerta simulada desde Wazuh
- `workflow_client`: Cliente Shuffle configurado
- `thehive_client`: Cliente TheHive configurado
- `misp_client`: Cliente MISP configurado
- `elasticsearch_client`: Cliente Elasticsearch configurado
- `wazuh_client`: Cliente Wazuh configurado

## Tiempo de Ejecución

Los tests E2E son los más lentos debido a:

- Latencia de red entre servicios
- Tiempo de ejecución de workflows
- Operaciones de I/O en múltiples servicios
- Tiempo de espera para respuestas asíncronas

Tiempo estimado: 15-30 minutos (dependiendo de la carga del sistema)

## Solución de Problemas

### Tests fallan por servicios no disponibles

Verifica que todos los servicios estén en ejecución y realmente listos:

```bash
make health
docker compose ps
docker compose logs -f <servicio>
```

> Un contenedor en estado `Up` no garantiza que el servicio esté listo. `make health` verifica endpoints internos.

### Tests fallan por servicios no listos, recursos insuficientes o Docker Desktop

1. **Servicios no listos:**
   - Ejecutar `make health` antes del test.
   - Consultar logs del servicio específico: `docker compose logs -f <servicio>`.
   - Esperar a que healthchecks finalicen; algunos servicios (Wazuh, TheHive) tardan minutos.

2. **Recursos insuficientes:**
   - Asignar al menos 8 GB de RAM y 4 vCPU a Docker / WSL.
   - Revisar `OOMKilled` con `docker inspect <contenedor> --format='{{.State.OOMKilled}}'`.

3. **Docker Desktop / WSL / Windows:**
   - Activar integración WSL2 y file sharing para el directorio del repo.
   - Ejecutar `make` desde WSL2 o PowerShell (no `cmd`).
   - Si `make` no está disponible: `make -f Makefile.win <target>` o usar WSL.

4. **Credenciales / `.env.full` desactualizadas:**
   - Tras `make reset` el apikey de Shuffle cambia; actualizar `.env.full` o confiar en `ShuffleClient._fetch_real_apikey()`.
   - Regenerar secretos: `make generate-secrets`.

### Tests fallan por webhook no inicializado

Inicializa el webhook Shuffle:

```bash
python src/soar_lab/scripts/setup/init_shuffle_webhook.py
```

### Tests fallan por timeout

Aumenta el timeout o verifica el rendimiento del sistema:

```bash
pytest tests/e2e/ -v --timeout=600
```

### Tests fallan por credenciales incorrectas

Verifica las credenciales en `.env.full`:

```bash
cat .env.full | grep -E "(API_KEY|PASSWORD)"
```

### Tests fallan por índices Elasticsearch no creados

Crea los índices necesarios:

```bash
curl -u elastic:$ELASTIC_PASSWORD -X PUT http://localhost:19200/soar-alerts
curl -u elastic:$ELASTIC_PASSWORD -X PUT http://localhost:19200/soar-iocs
curl -u elastic:$ELASTIC_PASSWORD -X PUT http://localhost:19200/soar-metrics
```

## Limpieza después de Tests

Los tests E2E pueden dejar datos en los servicios. Para limpiar:

### Limpiar Elasticsearch

```bash
curl -u elastic:$ELASTIC_PASSWORD -X DELETE http://localhost:19200/soar-*
```

### Limpiar TheHive

```bash
# Eliminar casos de prueba vía API o UI
```

### Limpiar MISP

```bash
# Eliminar eventos de prueba vía API o UI
```

### Limpiar Shuffle

```bash
# Eliminar ejecuciones de prueba vía API o UI
```

## Best Practices

### Ejecutar tests E2E

- Ejecutar en un entorno de pruebas aislado
- No ejecutar en producción
- Limpiar datos después de cada ejecución
- Verificar que no haya tests ejecutándose simultáneamente

### Desarrollo de tests E2E

- Mantener tests independientes entre sí
- Usar datos de prueba consistentes
- Limpiar recursos en teardown
- Documentar dependencias externas
