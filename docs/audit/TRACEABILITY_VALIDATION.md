# Validación de trazabilidad literal

| Estado | Ruta |
|--------|------|
| OK | `src/soar_lab/domain/services` |
| OK | `src/soar_lab/application/use_cases` |
| OK | `src/soar_lab/interfaces/api/models.py` |
| OK | `src/soar_lab/infrastructure/security` |
| OK | `src/soar_lab/infrastructure/jwt_token_provider.py` |
| OK | `src/soar_lab/config/schemas.py` |
| OK | `src/soar_lab/infrastructure/pytest_test_runner.py` |
| OK | `infra/docker/compose/docker-compose.yml` |
| OK | `infra/docker/compose/docker-compose.core.yml` |
| OK | `src/soar_lab/infrastructure/network_watcher` |
| OK | `infra/docker/config/nginx/ssl/soar.local.crt` |
| OK | `infra/docker/config/nginx/ssl/soar.local.key` |

## Swagger URL
- `docs/api/openapi.json` existe. Swagger UI accesible en `https://soar.local/api/docs` (Nginx) o `http://localhost:8000/docs` (directo).

## CLI paths
- `src/soar_lab/interfaces/api/cli.py`: OK

## Plan de gobernanza y validación
- `docs/project/governance_and_validation_plan.md`: plan consolidado de FASEs 54–65.
- `tests/architecture/test_hexagonal_imports.py`: test de dependencias hexagonales (FASE 56, N013).
- `pytest.ini`: marcador `architecture` registrado.
