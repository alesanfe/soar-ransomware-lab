# SOAR Ransomware Lab - Tests

Este directorio contiene la suite completa de tests para el proyecto SOAR Ransomware Lab.

## Estado actual de la suite

- **Python soportado**: `>=3.11` (declarado en `pyproject.toml`).
- **Comando canónico**: `python -m pytest --collect-only -q`
- **Inventario detallado**: [`baseline/tests_inventory.json`](../../baseline/tests_inventory.json)
- **Generación de recuentos**: ejecutar `python -m pytest --collect-only -q` para obtener el recuento actual. El resultado anterior `collected 1944 items / 33 deselected / 1911 selected` es solo una referencia histórica.

## Pirámide de calidad

```
         E2E (pocos, lentos)
    Integración (algunos, servicios reales)
       Unitario / Atómico (muchos, rápidos)
```

- **Unit / Atomic**: rápidos, sin dependencias externas, se ejecutan con `make test-unit` / `make test-atomic`.
- **Integración**: validan adaptadores y servicios contra contenedores reales (`make test-integration`).
- **E2E / Smoke**: validan workflows completos del playbook (`make test-e2e`, `make test-smoke`).
- **Rendimiento / Seguridad**: tests específicos con infraestructura dedicada (`make test-performance`, `make test-security`).

## Flujo canónico de ejecución

```bash
# 1. Preparar credenciales y datos de prueba
make generate-secrets
make generate-iocs

# 2. Limpiar y levantar el stack
make reset
make up

# 3. Verificar salud antes de tests que requieren Docker
make health

# 4. Ejecutar tests por categoría
make test-unit          # No requiere Docker
make test-integration   # Requiere stack levantado
make test-smoke
make test-e2e
make test-all           # Requiere stack completo
```

## Estructura de Tests

```
tests/
├── atomic/          # Tests atómicos
├── integration/     # Tests de integración
├── unit/            # Tests unitarios
├── performance/     # Tests de rendimiento
├── security/        # Tests de seguridad
├── general/         # Utilidades generales
├── e2e/             # Tests end-to-end
├── fixtures/        # Datos de test compartidos
└── runners/         # Scripts de ejecución de tests
```

> Para recuentos reales, consultar `baseline/tests_inventory.json` o ejecutar `python -m pytest --collect-only -q`.

## Ejecución de Tests

### Comandos canónicos con Make

```bash
# Ejecutar tests unitarios (no requieren Docker)
make test-unit

# Ejecutar tests de integración (requiere make up + make health)
make test-integration

# Ejecutar tests E2E
make test-e2e

# Ejecutar smoke tests
make test-smoke

# Ejecutar todos los tests (requiere stack completo)
make test-all

# Ejecutar con cobertura
make test-coverage
```

### Ejecutar con pytest directo

```bash
# Tests unitarios
pytest tests/unit/ -v

# Tests de integración
pytest tests/integration/ -v

# Tests de rendimiento
pytest tests/performance/ -v

# Tests de seguridad
pytest tests/security/ -v

# Tests atómicos
pytest tests/atomic/ -v

# Tests E2E
pytest tests/e2e/ -v

# Todos los tests con cobertura
pytest tests/ --cov=src/soar_lab --cov-report=html --cov-report=term
```

> **Nota:** `pytest` directo no es el flujo recomendado para tests que requieren Docker o variables de entorno del stack. Los targets `make` configuran `.env.full`, perfiles de Compose y demás prerequisitos. Usar `make test-*` salvo para desarrollo aislado.

### Ejecutar tests específicos

```bash
pytest tests/unit/test_alert_validation.py -v
pytest tests/unit/test_alert_validation.py::TestAlertValidator::test_validate_structure -v
```

### Ejecutar por marcadores

```bash
# Solo tests unitarios
pytest tests/ -m unit -v

# Solo tests de integración
pytest tests/ -m integration -v

# Solo tests que requieren servicios en vivo
pytest tests/ -m live -v

# Solo tests que pueden ejecutarse offline
pytest tests/ -m offline -v
```

## Marcadores de Pytest

- `unit`: Tests unitarios (sin dependencias externas)
- `integration`: Tests de integración (requieren servicios externos)
- `e2e`: Tests end-to-end (sistema completo)
- `performance`: Tests de rendimiento
- `security`: Tests de seguridad
- `live`: Tests que requieren servicios en vivo
- `offline`: Tests que pueden ejecutarse sin servicios externos
- `smoke`: Tests de smoke (validación rápida)
- `regression`: Tests de regresión

## Requisitos

### Para tests unitarios y atómicos

- Python 3.11+
- pytest
- pytest-cov (opcional, para coverage)

### Para tests de integración

- Todos los requisitos anteriores
- Servicios Docker en ejecución:
    - Elasticsearch
    - MISP
    - TheHive
    - Shuffle
    - Wazuh

### Para tests E2E

- Todos los requisitos anteriores
- Configuración completa del entorno (ver `.env.example`)

## Configuración

Los tests utilizan el archivo `.env.full` para configuración. Asegúrate de:

1. Copiar `.env.example` a `.env.full`
2. Configurar las credenciales de los servicios
3. Asegurarse de que los servicios Docker estén en ejecución

## Fixtures Compartidos

El archivo `conftest.py` en el directorio raíz de tests contiene fixtures compartidos:

- `sample_alert`: Alerta de ejemplo
- `sample_malicious_alert`: Alerta maliciosa de ejemplo
- `sample_benign_alert`: Alerta benigna de ejemplo
- `sample_ioc_package`: Paquete IOC de ejemplo
- `sample_misp_event`: Evento MISP de ejemplo
- `sample_workflow_data`: Datos de workflow de ejemplo
- `sample_metrics_data`: Datos de métricas de ejemplo
- `sample_wazuh_alert`: Alerta Wazuh de ejemplo
- `mock_elasticsearch_client`: Cliente Elasticsearch mockeado
- `mock_thehive_client`: Cliente TheHive mockeado
- `mock_misp_client`: Cliente MISP mockeado
- `mock_shuffle_client`: Cliente Shuffle mockeado
- `mock_wazuh_client`: Cliente Wazuh mockeado

## Pirámide de calidad

| Nivel | Tipo | Qué valida | Ejecución canónica |
|---|---|---|---|
| Unitarios | `tests/unit/` | Funciones, modelos, utilidades sin dependencias externas | `pytest tests/unit/ -v` |
| Atómicos | `tests/atomic/` | Componentes individuales con mocks | `pytest tests/atomic/ -v` |
| Integración | `tests/integration/` | Interacción entre adaptadores y clientes | `pytest tests/integration/ -v` |
| Seguridad | `tests/security/` | Validación de secretos, permisos, entradas maliciosas | `pytest tests/security/ -v` |
| Rendimiento | `tests/performance/` | Latencia, carga, benchmarks | `pytest tests/performance/ -v` |
| E2E | `tests/e2e/TC-*` | Flujo completo del playbook con servicios en ejecución | `pytest tests/e2e/ -v` |
| Smoke | marcadores `smoke*` | Salud mínima tras despliegue | `pytest -m smoke -v` |

No se incluyen conteos estáticos. Para conocer el estado actual:

```bash
# Linux/macOS
pytest --collect-only -q | grep -c "::"

# Windows
pytest --collect-only -q | find /c /v ""
```

Para obtener el desglose por categoría, usa los marcadores de `pyproject.toml`:

```bash
pytest --collect-only -q -m unit
pytest --collect-only -q -m integration
pytest --collect-only -q -m e2e
```

## Scripts de Ejecución

El directorio `runners/` contiene scripts personalizados para ejecución de tests:

- `pytest_runner.py`: Runner personalizado con reportes detallados
- `run_e2e_tests.sh`: Ejecuta un caso E2E dentro del contenedor `soar_api`

## Coverage

Para asegurar la calidad del código, mantenemos un mínimo de coverage:

- **Coverage general**: 70%
- **Funciones críticas**: 80%
- **Funciones de seguridad**: 90%

## Mutation Testing

Para verificar la calidad de los tests, utilizamos mutation testing:

- **Score mínimo**: 70%
- **Funciones críticas**: 80%
- **Funciones de seguridad**: 90%

## Solución de Problemas

### Tests fallan por credenciales

Verifica que `.env.full` esté configurado correctamente con las credenciales de los servicios.

### Tests fallan por servicios no disponibles

Asegúrate de que los servicios Docker estén en ejecución:

```bash
docker compose ps
```

### Tests de integración fallan

Verifica la conectividad a los servicios:

```bash
docker compose logs
```

## Contribución

Al añadir nuevos tests:

1. Sigue la estructura de directorios existente
2. Usa fixtures compartidos cuando sea posible
3. Añade docstrings claros
4. Usa marcadores apropiados
5. Mantén el coverage mínimo
