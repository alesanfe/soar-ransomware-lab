# ADR-0001: Composition root único

**Estado**: Aceptado · **Evidencia**: BUG-113

## Contexto

Existían dos wiring divergentes: `src/soar_lab/interfaces/api/__init__.py`
construía una app **inferior** (`InMemoryAlertRepository` sin SQLite, sin
clientes Docker/Redis, e importaba `scripts.test_service` — violación de
capas src→scripts), mientras `apps/api/Dockerfile` y la CLI usaban
`composition:create_app --factory`. Resultado: `uvicorn :app` ≠ producción.

## Decisión

`composition.py:CompositionRoot.create_app()` es el **único** punto de
wiring. `__init__.py` solo re-exporta `create_app`/`CompositionRoot`; el
símbolo `app` existe únicamente cuando `SOAR_SKIP_EAGER_INIT` no está
activo (para `uvicorn :app` legacy) y delega al mismo factory.
`TestService` vive en `application/use_cases/` con shim de
retrocompatibilidad en `scripts/`.

## Consecuencias

- Un solo lugar donde auditar wiring, TLS defaults y validación de config.
- `uvicorn soar_lab.interfaces.api:create_app --factory` ≡ Dockerfile ≡ CLI.
- Invariante testeada: `src` nunca importa `scripts` (test de arquitectura).
