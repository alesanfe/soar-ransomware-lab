# Unit Tests

Tests unitarios para el proyecto SOAR Ransomware Lab. Estos tests verifican el funcionamiento de componentes
individuales de forma aislada, sin dependencias externas.

## Propósito

Los tests unitarios validan:

- Funciones y clases individuales
- Lógica de negocio
- Validación de datos
- Generación de datos (IOCs, secretos, KPIs)
- Clientes de servicios (mockeados)
- Utilidades y helpers

## Requisitos

### Mínimos

- Python 3.11+
- pytest
- pytest-cov (opcional, para coverage)

### No requiere servicios externos

Los tests unitarios no requieren servicios Docker en ejecución. Todas las dependencias externas están mockeadas.

## Ejecución

### Ejecutar todos los tests unitarios (canónico)

```bash
make test-unit
```

> `make test-unit` ejecuta `pytest tests/unit -v` dentro del contenedor `soar_api` tras sincronizar el código. Para desarrollo aislado en host (sin Docker):
>
> ```bash
> pytest tests/unit/ -v
> ```

### Ejecutar tests específicos

```bash
# Tests de clientes
pytest tests/unit/test_elasticsearch_client.py -v
pytest tests/unit/test_misp_client.py -v
pytest tests/unit/test_shuffle_client.py -v
pytest tests/unit/test_wazuh_client.py -v

# Tests de servicios
pytest tests/unit/test_auth_service.py -v
pytest tests/unit/test_backup_service.py -v
pytest tests/unit/test_health_service.py -v

# Tests de generadores
pytest tests/unit/test_ioc_generator.py -v
pytest tests/unit/test_generate_secrets.py -v
pytest tests/unit/test_generate_kpi_data.py -v

# Tests de validación
pytest tests/unit/test_validators.py -v
pytest tests/unit/test_config_schemas.py -v
```

### Ejecutar con coverage

```bash
pytest tests/unit/ --cov=src/soar_lab --cov-report=html --cov-report=term
```

### Ejecutar solo tests que fallen

```bash
pytest tests/unit/ -v --lf
```

### Ejecutar tests en paralelo

```bash
pytest tests/unit/ -v -n auto
```

## Categorías de Tests

### Clientes de Servicios

- `test_elasticsearch_client.py`: Cliente Elasticsearch
- `test_misp_client.py`: Cliente MISP
- `test_shuffle_client.py`: Cliente Shuffle
- `test_wazuh_client.py`: Cliente Wazuh
- `test_thehive_client.py`: Cliente TheHive
- `test_cortex_client.py`: Cliente Cortex
- `test_base_client.py`: Cliente base
- `test_http_client.py`: Cliente HTTP genérico

### Servicios

- `test_auth_service.py`: Servicio de autenticación
- `test_backup_service.py`: Servicio de backup
- `test_health_service.py`: Servicio de health check
- `test_cleanup_service.py`: Servicio de limpieza
- `test_test_service.py`: Servicio de tests

### Generadores

- `test_ioc_generator.py`: Generador de IOCs
- `test_generate_iocs.py`: Generación de IOCs
- `test_generate_secrets.py`: Generación de secretos
- `test_generate_kpi_data.py`: Generación de datos KPI
- `test_alert_generator.py`: Generador de alertas

### Validación y Schemas

- `test_validators.py`: Validadores
- `test_config_schemas.py`: Schemas de configuración
- `test_domain_models.py`: Modelos de dominio
- `test_schema_validation.py`: Validación de schemas (atomic)

### Utilidades

- `test_checksum_utils.py`: Utilidades de checksum
- `test_path_service.py`: Servicio de rutas
- `test_filesystem_storage.py`: Almacenamiento en filesystem
- `test_file_log_reader.py`: Lector de logs
- `test_log_parser.py`: Parser de logs

### Resiliencia

- `test_circuit_breaker.py`: Circuit breaker
- `test_retry_policy.py`: Política de reintentos
- `test_timeout_handling.py`: Manejo de timeouts
- `test_transaction_handling.py`: Manejo de transacciones
- `test_payload_sanitization.py`: Sanitización de payloads
- `test_structured_logging.py`: Logging estructurado

### Analítica y KPIs

- `test_analytics_service.py`: Servicio de analítica
- `test_kpi_analyzer.py`: Analizador de KPIs
- `test_kpi_alerts.py`: Alertas KPI
- `test_kpi_formatter.py`: Formateador de KPIs
- `test_statistical_calculator.py`: Calculadora estadística
- `test_calc_kpis.py`: Cálculo de KPIs

### API

- `test_api_auth.py`: Autenticación API
- `test_api_models.py`: Modelos API
- `test_api_composition.py`: Composición API
- `test_api_dependencies.py`: Dependencias API
- `test_api_cli.py`: CLI API

### Otros

- `test_settings.py`: Configuración
- `test_exceptions.py`: Excepciones
- `test_domain_ports.py`: Puertos de dominio
- `test_jwt_token_provider.py`: Proveedor de tokens JWT
- `test_websocket_manager.py`: Gestor de WebSockets

## Fixtures

El archivo `conftest.py` en este directorio contiene fixtures específicos para tests unitarios:

- `mock_settings`: Configuración mockeada
- `mock_redis_client`: Cliente Redis mockeado
- `mock_docker_client`: Cliente Docker mockeado

## Fixtures Globales

Los fixtures en `tests/conftest.py` también están disponibles:

- `sample_alert`: Alerta de ejemplo
- `sample_malicious_alert`: Alerta maliciosa de ejemplo
- `sample_benign_alert`: Alerta benigna de ejemplo
- `mock_elasticsearch_client`: Cliente Elasticsearch mockeado
- `mock_misp_client`: Cliente MISP mockeado
- `mock_shuffle_client`: Cliente Shuffle mockeado
- `mock_wazuh_client`: Cliente Wazuh mockeado

## Patrones de Tests

### Test básico

```python
def test_function_name():
    """Test description"""
    # Arrange
    input_data = {...}
    
    # Act
    result = function_to_test(input_data)
    
    # Assert
    assert result == expected_value
```

### Test con fixtures

```python
def test_with_fixture(mock_client):
    """Test with mock fixture"""
    mock_client.return_value = expected_data
    result = function_to_test()
    assert result == expected_value
```

### Test con excepciones

```python
def test_exception():
    """Test that exception is raised"""
    with pytest.raises(ValueError, match="expected message"):
        function_to_test(invalid_input)
```

## Coverage

Mantenemos un mínimo de coverage para tests unitarios:

- **Coverage general**: 80%
- **Funciones críticas**: 90%
- **Funciones de seguridad**: 95%

## Tiempo de Ejecución

Los tests unitarios son rápidos debido a que no hay dependencias externas:

- Tiempo estimado: 1-3 minutos
- Pueden ejecutarse en paralelo para mayor velocidad

## Solución de Problemas

### Tests fallan por import errors

Verifica que el directorio `src/` esté en el PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Tests fallan por mocks incorrectos

Verifica que los mocks estén configurados correctamente:

```bash
pytest tests/unit/test_file.py -v -s
```

### Coverage bajo

Añade tests para las rutas no cubiertas:

```bash
pytest tests/unit/ --cov=src/soar_lab --cov-report=html
# Abre htmlcov/index.html para ver el reporte
```
