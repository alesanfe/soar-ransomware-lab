# Integration Tests

Tests de integración para el proyecto SOAR Ransomware Lab. Estos tests verifican la interacción entre diferentes
servicios y componentes del sistema.

## Propósito

Los tests de integración validan:

- Conectividad entre servicios (TheHive, MISP, Elasticsearch, Shuffle, Wazuh)
- Intercambio de datos entre componentes
- Manejo de errores en comunicaciones externas
- Idempotencia de operaciones
- Consistencia de datos entre servicios
- Compatibilidad de versiones

## Requisitos de Servicios

Para ejecutar estos tests, los siguientes servicios deben estar en ejecución:

### Servicios Requeridos

- **Elasticsearch**: `localhost:19200` (o puerto configurado en `.env.full`)
- **MISP**: `localhost:8083` (o puerto configurado en `.env.full`)
- **TheHive**: `localhost:19000` (o puerto configurado en `.env.full`)
- **Shuffle**: `localhost:8081` (o puerto configurado en `.env.full`)
- **Wazuh**: `localhost:55100` (o puerto configurado en `.env.full`)

### Verificar Servicios

```bash
# Verificar salud real de servicios (recomendado)
make health

# Verificar estado de servicios Docker
docker compose ps

# Verificar logs de servicios
docker compose logs -f <servicio>
```

> Un contenedor en estado `Up` no implica que el servicio esté listo. Usar `make health` antes de lanzar tests.

## Configuración

Asegúrate de que `.env.full` esté configurado con las credenciales correctas:

```bash
# Ejemplo de variables requeridas
ELASTIC_HOST=localhost
ELASTIC_PORT=19200
ELASTIC_USER=elastic
ELASTIC_PASSWORD=<ELASTIC_PASSWORD>

MISP_URL=http://localhost:8083
MISP_API_KEY=<MISP_API_KEY>

THEHIVE_URL=http://localhost:19000
THEHIVE_API_KEY=<THEHIVE_API_KEY>

SHUFFLE_URL=http://localhost:8081
SHUFFLE_API_KEY=<SHUFFLE_DEFAULT_APIKEY>

WAZUH_URL=https://localhost:55100
WAZUH_USER=admin
WAZUH_PASSWORD=<WAZUH_API_PASSWORD>
```

## Preparación y ejecución canónica

Los tests de integración requieren el stack Docker levantado, `.env.full` correcto y `make health` exitoso.

```bash
# 1. Levantar servicios y verificar salud
make up
make health

# 2. Ejecutar tests de integración (canónico)
make test-integration
```

### Ejecutar todos los tests de integración (directo)

```bash
pytest tests/integration/ -v
```

> **Nota:** `make test-integration` ejecuta `pytest tests/integration -v -m 'requires_docker or not requires_docker'` dentro del contenedor `soar_api`. Ejecutar `pytest` directo en host puede fallar si faltan variables o dependencias reales.

### Ejecutar tests específicos

```bash
# Tests de Elasticsearch
pytest tests/integration/test_elasticsearch_integration.py -v

# Tests de MISP
pytest tests/integration/test_misp_integration.py -v

# Tests de Shuffle
pytest tests/integration/test_init_shuffle_webhook.py -v

# Tests de Wazuh
pytest tests/integration/test_wazuh_integration.py -v
```

### Ejecutar con coverage

```bash
pytest tests/integration/ --cov=src/soar_lab --cov-report=html
```

## Categorías de Tests

### Conectividad de Servicios

- `test_elasticsearch_integration.py`: Integración completa con Elasticsearch
- `test_misp_integration.py`: Integración completa con MISP
- `test_thehive_integration.py`: Integración con TheHive
- `test_shuffle_integration.py`: Integración con Shuffle
- `test_wazuh_integration.py`: Integración completa con Wazuh
- `test_cortex_integration.py`: Integración con Cortex

### Inicialización y Configuración

- `test_init_shuffle_webhook.py`: Inicialización de webhook Shuffle
- `test_docker_compose_validation.py`: Validación de docker-compose
- `test_docker_runtime_status.py`: Estado de runtime Docker

### Comunicación y Datos

- `test_data_consistency.py`: Consistencia de datos entre servicios
- `test_idempotency.py`: Idempotencia de operaciones
- `test_metrics_export.py`: Exportación de métricas
- `test_external_service_failure.py`: Manejo de fallos de servicios externos

### Seguridad y Autorización

- `test_authorization.py`: Tests de autorización RBAC
- `test_security.py`: Tests de seguridad
- `test_auth.py`: Tests de autenticación

### API y Contratos

- `test_api_endpoints.py`: Tests de endpoints API
- `test_api_fastapi.py`: Tests de API FastAPI
- `test_api_integration.py`: Tests de integración API
- `test_contract_compliance.py`: Cumplimiento de contratos de servicio
- `test_openapi_spec_sync.py`: Sincronización de especificación OpenAPI

### Rendimiento y Condiciones de Carrera

- `test_race_conditions.py`: Condiciones de carrera
- `test_version_compatibility.py`: Compatibilidad de versiones
- `test_docker_partial_failure.py`: Recuperación de fallos parciales

## Fixtures

El archivo `conftest.py` en este directorio contiene fixtures específicos para tests de integración:

- `elasticsearch_client`: Cliente Elasticsearch configurado
- `misp_client`: Cliente MISP configurado
- `thehive_client`: Cliente TheHive configurado
- `shuffle_client`: Cliente Shuffle configurado
- `wazuh_client`: Cliente Wazuh configurado

## Solución de Problemas

### Tests fallan por conexión rechazada

Verifica que los servicios estén en ejecución:

```bash
docker compose ps
```

### Tests fallan por autenticación

Verifica las credenciales en `.env.full`:

```bash
# Verificar variables de entorno
cat .env.full | grep -E "(URL|API_KEY|PASSWORD)"
```

### Tests fallan por timeout

Aumenta el timeout en el test o verifica el rendimiento del servicio:

```bash
# Verificar uso de recursos
docker stats
```

### Tests de Elasticsearch fallan

Verifica que Elasticsearch esté saludable:

```bash
curl -u "elastic:<ELASTIC_PASSWORD>" http://localhost:19200/_cluster/health
```

### Tests de MISP fallan

Verifica que MISP esté accesible:

```bash
curl -H "Authorization: <MISP_API_KEY>" http://localhost:8083/users/me
```

## Tiempo de Ejecución

Los tests de integración pueden tardar más que los tests unitarios debido a:

- Latencia de red
- Tiempo de respuesta de servicios externos
- Operaciones de I/O

Tiempo estimado: 5-15 minutos (dependiendo de la carga del sistema)
