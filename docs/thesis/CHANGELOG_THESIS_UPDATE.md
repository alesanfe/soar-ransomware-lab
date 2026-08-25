# Registro de cambios de la tesis

> La bibliografía canónica se mantiene en [`bibliographic_references.md`](bibliographic_references.md). Esta sección registra únicamente los cambios técnicos y editoriales sustantivos aplicados durante la remediación documental.

## 2026-07-19 — Revisión de docs/thesis (FASE 53)

- **Tesis / Troubleshooting (A.6.1).**
  - Expandido `docs/thesis/appendix_a.md` con problemas frecuentes concretos: contenedores, Elasticsearch/OpenSearch, conectividad, E2E Shuffle, Grafana/métricas, MISP DB, autenticación JWT y certificados SSL.
  - Añadidos pasos operativos, causas, criterios de verificación y criterios generales de aceptación.
  - Renumerada sección de logs de depuración a `A.6.3`.

- **Tesis / Makefile y secretos.**
  - Referenciado `make generate-secrets` y `soar-lab generate-secrets` como mecanismos oficiales para generar `.env.full` sin secretos por defecto en el repositorio.

- **Tesis / Tablas y secciones operativas.**
  - `docs/thesis/figures_tables_list.md` y `table_of_contents.md` mantienen la estructura; las tablas operativas se actualizan en `comparative_tables.md` y el resto del corpus de la tesis es una instantánea estática de la remediación.

## 2026-07-18 — Remediación documental masiva

- **Seguridad y secretos.**
  - `.env.example` saneado: todos los secretos se convirtieron en marcadores `<VARIABLE>`.
  - Creado `src/soar_lab/scripts/setup/generate_env.py` para generar `.env.full` y `infra/docker/compose/logging/grafana-datasources.yml` a partir de plantillas.
  - `grafana-datasources.yml` y `.env.full` añadidos a `.gitignore`; ya no se publican valores operativos.
  - `Makefile.linux` y `Makefile.win` actualizados: `make generate-secrets` genera el entorno y `make up` lo genera si falta.

- **Healthchecks.**
  - TheHive ahora usa `/api/status` en `docker-compose.api.yml`, Makefiles y guías para evitar falsos negativos durante la inicialización de Elasticsearch.

- **CLI y JWT.**
  - `soar-lab generate-secrets` añade `JWT_SECRET_KEY` a la salida `.env`.
  - Manual `docs/operations/cli_manual.md` sincronizado para reflejar la generación automática de JWT.

- **Tesis.**
  - `docs/thesis/appendix_a.md`, `specific_development.md`, `comparative_tables.md`, `conclusions_and_future_work.md` y `tfm.md` actualizados para advertir que el anexo es una instantánea estática y señalar los compose canónicos.
  - `comparative_tables.md`: TLS marcado como parcial/autofirmado.

## 2026-07-15 — Logging y métricas funcionales

- Stack Loki-Promtail-Grafana operativo; Grafana puede consultar `soar-metrics`.
- Corregido mapping de `soar-metrics` (`mttr_seconds` como `float`, `@timestamp` como `date`).
- `grafana-datasources.yml` apunta a `esVersion: 8.0.0` e índice `soar-metrics`.

---

> La bibliografía canónica se mantiene en [`bibliographic_references.md`](bibliographic_references.md).
> Se han eliminado 61 referencias placeholder inventadas (nombres académicos genéricos,
> conferencias sin autor, blogs sin URL específica, patentes con números irreales).

