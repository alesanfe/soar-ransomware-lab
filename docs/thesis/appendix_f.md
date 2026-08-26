# Anexo F: Documentación de Mejoras Implementadas

> La bibliografía canónica se mantiene en [`bibliographic_references.md`](bibliographic_references.md). Este anexo registra
> únicamente los cambios técnicos y editoriales sustantivos aplicados durante la remediación documental.

## 2026-07-19 — Revisión de docs/thesis

- **Tesis / Troubleshooting (A.6.1).**
  - Expandido `docs/thesis/appendix_a.md` con problemas frecuentes concretos: contenedores, Elasticsearch/OpenSearch, conectividad, E2E Shuffle, Grafana/métricas, MISP DB, autenticación JWT y certificados SSL.
  - Añadidos pasos operativos, causas, criterios de verificación y criterios generales de aceptación.
  - Renumerada sección de logs de depuración a `A.6.3`.

- **Tesis / Makefile y secretos.**
  - Referenciado `make generate-secrets` y `soar-lab generate-secrets` como mecanismos oficiales para generar `.env.full` sin secretos por defecto en el repositorio.

- **Tesis / Tablas y secciones operativas.**
  - `docs/thesis/figures_list.md`, `tables_list.md` y `table_of_contents.md` mantienen la estructura; las tablas operativas se actualizan en `appendix_c.md` y el resto del corpus de la tesis es una instantánea estática de la remediación.

## 2026-07-18 — Remediación documental masiva

- **Seguridad y secretos.**
  - `.env.example` documentado como plantilla no operativa; los secretos reales se generan con `make generate-secrets` y se escriben en `.env.full` (en `.gitignore`).
  - Creado `scripts/setup/generate_env.py` para generar `.env.full` y `infra/docker/config/templates/grafana-datasources.yml.template` a partir de plantillas.
  - `grafana-datasources.yml` y `.env.full` añadidos a `.gitignore`; ya no se publican valores operativos.
  - `Makefile.linux` actualizado: `make generate-secrets` invoca `generate_env.py` para generar `.env.full` y `grafana-datasources.yml` desde plantillas; `make up` lo genera si falta. `Makefile.win` mantiene `generate_secrets.py` como target de generación de secretos individuales.

- **Healthchecks.**
  - TheHive ahora usa `/api/status` en `docker-compose.core.yml`, Makefiles y guías para evitar falsos negativos durante la inicialización de Elasticsearch.

- **CLI y JWT.**
  - `soar-lab generate-secrets` añade `JWT_SECRET_KEY` a la salida `.env`.
  - `docs/04-operations.md` sincronizado para reflejar la generación automática de JWT.

- **Tesis.**
  - `docs/thesis/appendix_a.md`, `specific_development.md`, `appendix_c.md`, `conclusions_and_future_work.md` actualizados para advertir que el anexo es una instantánea estática y señalar los compose canónicos.
  - `appendix_e.md`: TLS marcado como self-signed en la matriz de estado real/simulado/planificado.

## 2026-07-15 — Logging y métricas funcionales

- Stack Loki-Promtail-Grafana operativo; Grafana puede consultar `soar-metrics`.
- Corregido mapping de `soar-metrics` (`mttr_seconds` como `float`, `@timestamp` como `date`).
- `grafana-datasources.yml` apunta a `esVersion: 8.0.0` e índice `soar-metrics`.

---

> La bibliografía canónica se mantiene en [`bibliographic_references.md`](bibliographic_references.md).
> Durante la remediación documental se depuraron las referencias placeholder inventadas
> (nombres académicos genéricos, conferencias sin autor, blogs sin URL específica, patentes
> con números irreales) y se reemplazaron por fuentes verificables con DOI o URL real.

