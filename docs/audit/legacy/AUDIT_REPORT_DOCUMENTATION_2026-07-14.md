# SOAR Ransomware Lab — Auditoría Integral de Documentación

**Fecha:** 2026-07-14  
**Auditor:** Cascade AI Assistant  
**Alcance:** Todo el repositorio `docs/`, `README.md`, `API_DOCUMENTATION.md`, `apps/api/docs/`,
`apps/api/api-docs.html`, imágenes de `docs/img/`, informes de auditoría acumulados.  
**Estado previo:** Múltiples correcciones parciales ya aplicadas en sesiones anteriores (puertos, `docker compose`,
Wazuh Dashboard, `apps/api/docs` parcial).  
**Estado actual tras la presente auditoría:** `DOCUMENTACIÓN PARCIALMENTE CORRECTA` — la mayoría de la documentación
técnica operativa está al día, pero quedan inconsistencias residuales, documentos históricos por archivar y archivos
académicos que requieren revisión manual.

---

## 1. Resumen ejecutivo

### Estado general

- **Documentación operativa principal** (`README.md`, `getting_started/`, `architecture/`, `operations/`,
  `integrations/`, `testing/`, `docs/README.md`) ha sido **actualizada** en gran medida.
- **Puertos y credenciales** se han alineado con `.env.full` y los Docker Compose (`TheHive 19000`, `Cortex 19001`,
  `Elasticsearch 19200`, `Shuffle API 15001`, `MISP 8083`, `Grafana 8084`, `Wazuh Dashboard 15601`,
  `Web Management 8085`, `Docs site 8086`, `API 8000`).
- **Comandos `docker-compose` han sido reemplazados por `docker compose`** en la mayoría de documentos técnicos, aunque
  persisten ocurrencias en `thesis/`, `docs/testing/legacy` y `appendix_a.md`.
- **Reemplazo de `Kibana` por `Wazuh Dashboard`** está avanzado en documentos operativos, pero aún aparece en
  `architecture/`, `apps/api/docs/kibana-api.*`, `thesis/`, y `CODE_ANALYSIS_REPORT_*.md`.
- **Informes de auditoría acumulados**: la mayoría de `AUDIT_*.md` se han archivado en `docs/audit/legacy/`. Aún quedan
  `TECHNICAL_AUDIT_REPORT_*.md` vacíos, `CODE_ANALYSIS_REPORT_*.md`, `GRAFANA_CHARTS_COMPARISON_*.md` y
  `CHANGELOG_THESIS_UPDATE.md` en `docs/testing/`.
- **`apps/api/docs/`** contiene aún páginas HTML con puertos obsoletos (`elasticsearch-api.html` usa `localhost:9201`;
  `wazuh-api.html` usa `localhost:55000`) y `web-nginx.html` fue corregido parcialmente en esta sesión.
- **`docs/img/`**: imágenes correctamente referenciadas en `user_guide.md`; no se detectaron imágenes huérfanas, pero no
  se verificó actualidad visual.
- **`docs/audit/README.md`** ya existe y apunta al `AUDIT_REPORT.md` raíz.

### Principales problemas restantes

1. **Puertos incorrectos en `apps/api/docs/`**: `elasticsearch-api.html` (9201), `wazuh-api.html` (55000).
2. **Comandos `docker-compose` y `docker-compose.yml` sin especificador de archivo** en `docs/project/risks.md`,
   `scope.md`, `docker_testing_strategy.md`, `test_suite.md`, `thesis/appendix_a.md`,
   `thesis/bibliographic_references.md`, `CHANGELOG_THESIS_UPDATE.md`, `specific_development.md`,
   `CODE_ANALYSIS_REPORT_*.md`.
3. **Referencias a `Kibana` como producto UI** en `architecture/overview.md`, `architecture/docker_architecture.md`,
   `thesis/abbreviations_list.md`, `thesis/appendix_a.md`, `thesis/comparative_tables.md`, `thesis/tfm.md`,
   `thesis/CHANGELOG_THESIS_UPDATE.md`, `CODE_ANALYSIS_REPORT_*.md`.
4. **Documentos académicos (`thesis/`)** no han sido auditados exhaustivamente y requieren `REVISAR_MANUALMENTE` (no se
   deben editar sin criterio).
5. **`docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_COMPLETE.md` y `2026-07-03_FINAL.md` están vacíos** (0 bytes) y
   deberían eliminarse.
6. **`docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-04_V4.md`, `CODE_ANALYSIS_REPORT_2026-07-04.md`,
   `GRAFANA_CHARTS_COMPARISON_2026-07-04.md` y `CHANGELOG_THESIS_UPDATE.md` son documentos históricos/duplicados que
   deberían moverse a `docs/audit/legacy/`.
7. **`docs/testing/README.md` debería actualizarse** para reflejar que `docs/audit/legacy/` es el destino de informes
   históricos.
8. **`README.md` raíz** todavía lista `docs/architecture/security.md` y `docs/operations/troubleshooting.md` como links,
   pero no `docs/integrations/overview.md` (aunque ya fue añadido en `docs/README.md`); además, el diagrama Mermaid
   debería revisarse para que refleje Grafana/Loki/Promtail y Wazuh Dashboard.
9. **`API_DOCUMENTATION.md`**: sección Nginx ya fue corregida, pero `/misp` y `/wazuh` como rutas Nginx no existen; la
   sección de `Kibana API` ya fue renombrada a `Wazuh Dashboard API`.
10. **`docs/operations/configuration_manual.md` y `troubleshooting.md`**: se corrigieron en sesiones previas; requieren
    re-verificación final tras los recientes ajustes.

### Prioridades

- **CRÍTICA**: completar `apps/api/docs/` (puertos, `Kibana` → `Wazuh Dashboard`), asegurar que `README.md` raíz y
  `docs/README.md` sean coherentes con la arquitectura final.
- **ALTA**: eliminar archivos vacíos de auditoría, archivar informes históricos restantes, limpiar `docker-compose` en
  documentos operativos (`risks.md`, `scope.md`, `docker_testing_strategy.md`, `test_suite.md`).
- **MEDIA**: revisar `thesis/` para coherencia (no reescribir, solo marcar `REVISAR_MANUALMENTE` y sugerir cambios).
- **BAJA**: actualizar diagramas Mermaid, `CHANGELOG_THESIS_UPDATE.md`, `bibliographic_references.md`.

---

## 2. Mapa documental actual

| Archivo                                                                                                       | Categoría        | Propósito esperado                                         | Estado                                                      | Acción                                                     | Prioridad |
|---------------------------------------------------------------------------------------------------------------|------------------|------------------------------------------------------------|-------------------------------------------------------------|------------------------------------------------------------|-----------|
| `README.md`                                                                                                   | Principal        | Entrada del proyecto, instalación rápida, URLs, estructura | Parcialmente actualizado                                    | ACTUALIZAR                                                 | CRÍTICA   |
| `docs/README.md`                                                                                              | Índice           | Mapa de documentación                                      | Actualizado recientemente                                   | MANTENER / ACTUALIZAR enlace audit                         | ALTA      |
| `docs/audit/README.md`                                                                                        | Índice           | Punto de acceso a auditorías                               | Nuevo, correcto                                             | MANTENER                                                   | BAJA      |
| `docs/audit/legacy/*`                                                                                         | Archivo          | Informes de auditoría históricos                           | Archivados correctamente                                    | MANTENER                                                   | BAJA      |
| `docs/architecture/overview.md`                                                                               | Arquitectura     | Visión general, capas, flujos                              | Corregido mayormente                                        | ACTUALIZAR referencias residuales (`kibana` como servicio) | MEDIA     |
| `docs/architecture/docker_architecture.md`                                                                    | Arquitectura     | Servicios, imágenes, puertos, redes, volúmenes             | Parcialmente actualizado                                    | ACTUALIZAR nombres de servicio/imagen y puertos residuales | MEDIA     |
| `docs/architecture/security.md`                                                                               | Arquitectura     | Seguridad, secretos, SSL, hardening                        | Revisado, posiblemente desactualizado                       | ACTUALIZAR                                                 | MEDIA     |
| `docs/getting_started/overview.md`                                                                            | Introducción     | Introducción rápida                                        | Actualizado                                                 | MANTENER                                                   | BAJA      |
| `docs/getting_started/installation_guide.md`                                                                  | Instalación      | Guía de instalación paso a paso                            | Actualizado                                                 | MANTENER / re-verificar                                    | ALTA      |
| `docs/getting_started/user_guide.md`                                                                          | Uso              | Flujo de usuario, capturas                                 | Actualizado                                                 | MANTENER                                                   | ALTA      |
| `docs/img/*`                                                                                                  | Evidencia visual | Capturas de UI y dashboards                                | Sin imágenes huérfanas detectadas; no verificada actualidad | REVISAR_MANUALMENTE                                        | BAJA      |
| `docs/integrations/api_contracts.md`                                                                          | Integraciones    | Contratos de API y ejemplos                                | Actualizado                                                 | MANTENER                                                   | MEDIA     |
| `docs/integrations/overview.md`                                                                               | Integraciones    | Visión general, matriz de servicios                        | Nuevo, correcto                                             | MANTENER                                                   | BAJA      |
| `docs/operations/configuration_manual.md`                                                                     | Operaciones      | Configuración de servicios                                 | Corregido                                                   | MANTENER / re-verificar                                    | ALTA      |
| `docs/operations/playbooks/ransomware_playbook_e2e.md`                                                        | Operaciones      | Playbook E2E                                               | Corregido                                                   | MANTENER                                                   | ALTA      |
| `docs/operations/troubleshooting.md`                                                                          | Operaciones      | Resolución de problemas                                    | Corregido                                                   | MANTENER / re-verificar                                    | ALTA      |
| `docs/project/objectives.md`                                                                                  | Proyecto         | Objetivos SMART                                            | Revisado                                                    | MANTENER                                                   | BAJA      |
| `docs/project/plan.md`                                                                                        | Proyecto         | Planificación y cronograma                                 | Corregido (PostgreSQL)                                      | MANTENER                                                   | BAJA      |
| `docs/project/risks.md`                                                                                       | Proyecto         | Gestión de riesgos                                         | Corregido parcialmente                                      | ACTUALIZAR comandos `docker-compose` y `Kibana` restantes  | ALTA      |
| `docs/project/scope.md`                                                                                       | Proyecto         | Alcance y límites                                          | Corregido                                                   | ACTUALIZAR comandos `docker-compose`                       | ALTA      |
| `docs/testing/README.md`                                                                                      | Testing          | Índice de testing y auditorías                             | Parcialmente actualizado                                    | ACTUALIZAR (archivos restantes en `docs/testing`)          | ALTA      |
| `docs/testing/test_suite.md`                                                                                  | Testing          | Suite de tests                                             | Corregido parcialmente                                      | ACTUALIZAR `docker-compose` residual                       | ALTA      |
| `docs/testing/docker_testing_strategy.md`                                                                     | Testing          | Estrategia Docker                                          | Corregido parcialmente                                      | ACTUALIZAR `docker-compose` y `Kibana` residual            | ALTA      |
| `docs/testing/CODE_ANALYSIS_REPORT_*.md`                                                                      | Histórico        | Análisis de código                                         | Histórico/duplicado                                         | ARCHIVAR                                                   | BAJA      |
| `docs/testing/GRAFANA_CHARTS_COMPARISON_*.md`                                                                 | Histórico        | Comparación dashboards                                     | Histórico                                                   | ARCHIVAR                                                   | BAJA      |
| `docs/testing/TECHNICAL_AUDIT_REPORT_*.md`                                                                    | Histórico        | Auditoría técnica                                          | Vacíos/duplicados                                           | ARCHIVAR / ELIMINAR vacíos                                 | ALTA      |
| `docs/testing/CHANGELOG_THESIS_UPDATE.md`                                                                     | Histórico        | Changelog académico                                        | Histórico/duplicado                                         | ARCHIVAR                                                   | BAJA      |
| `docs/thesis/*`                                                                                               | Académico        | Tesis/TFM y anexos                                         | No auditado en profundidad                                  | REVISAR_MANUALMENTE                                        | MEDIA     |
| `API_DOCUMENTATION.md`                                                                                        | API              | Referencia de APIs de servicios                            | Corregido parcialmente                                      | ACTUALIZAR anclas y rutas Nginx residuales                 | ALTA      |
| `apps/api/api-docs.html`                                                                                      | API              | Índice HTML de APIs (EN)                                   | Corregido en esta sesión                                    | MANTENER / re-verificar                                    | ALTA      |
| `apps/api/docs/index.html`                                                                                    | API              | Índice HTML de APIs (ES)                                   | Corregido en esta sesión                                    | MANTENER                                                   | ALTA      |
| `apps/api/docs/kibana-api.yaml`                                                                               | API              | OpenAPI Kibana/Wazuh Dashboard                             | Corregido                                                   | MANTENER                                                   | MEDIA     |
| `apps/api/docs/kibana-api.html`                                                                               | API              | HTML Kibana/Wazuh Dashboard                                | Corregido                                                   | MANTENER                                                   | MEDIA     |
| `apps/api/docs/web-nginx.html`                                                                                | API              | HTML Nginx                                                 | Corregido en esta sesión                                    | MANTENER                                                   | MEDIA     |
| `apps/api/docs/elasticsearch-api.html`                                                                        | API              | HTML Elasticsearch                                         | Puertos `9201` obsoletos                                    | ACTUALIZAR                                                 | CRÍTICA   |
| `apps/api/docs/wazuh-api.html`                                                                                | API              | HTML Wazuh                                                 | Puertos `55000` obsoletos                                   | ACTUALIZAR                                                 | CRÍTICA   |
| `apps/api/docs/thehive-api.html`, `cortex-api.html`, `misp-api.html`, `shuffle-api.html`, `soar-lab-api.html` | API              | HTML específicos                                           | Requieren re-verificación                                   | REVISAR_MANUALMENTE                                        | MEDIA     |
| `AUDIT_REPORT.md`                                                                                             | Auditoría        | Informe canónico                                           | Actualizado (2026-07-09)                                    | MANTENER                                                   | BAJA      |
| `AUDIT_REPORT_DOCUMENTATION_2026-07-14.md`                                                                    | Auditoría        | Este informe                                               | Nuevo                                                       | MANTENER                                                   | -         |

---

## 3. Contenido esperado por documento (ficheros críticos)

### 3.1 `README.md` (raíz)

**Propósito:** Entrada principal del proyecto.

**Debe contener:**

- Nombre, descripción, objetivo del laboratorio SOAR.
- Arquitectura resumida con Mermaid (incluyendo Grafana/Loki/Promtail, Wazuh Dashboard).
- Componentes: API, web management, docs site, Elasticsearch, Wazuh, MISP, TheHive, Cortex, Shuffle, Grafana, Redis,
  Loki, Nginx, Wazuh Dashboard.
- Requisitos: OS, Docker, Docker Compose, Vagrant, Python, Make.
- Instalación rápida y comandos `make up`, `make down`, `make reset`, `make test`, `make logs`.
- URLs/puertos del entorno correctos.
- Ejemplos de credenciales seguros (no secretos reales).
- Cómo ejecutar tests, consultar métricas, dashboards, docs.
- Estructura del repo y carpetas `runtime`, `artifacts`, `logs`, `results`.
- Enlaces a `getting_started/installation_guide.md`, `architecture/overview.md`, `operations/configuration_manual.md`,
  `testing/test_suite.md`, `operations/troubleshooting.md`.
- Advertencias de seguridad y estado actual.

**Falta actualmente:**

- El diagrama Mermaid no refleja Grafana/Loki/Promtail y Wazuh Dashboard (se usa `Kibana`).
- Lista de componentes incluye `Kibana` en lugar de `Wazuh Dashboard`.
- No incluye `docs/integrations/overview.md` y `docs/audit/README.md` en la guía de lectura.

**Acción recomendada:** ACTUALIZAR (CRÍTICA).

---

### 3.2 `docs/architecture/overview.md`

**Propósito:** Explicar la arquitectura general.

**Debe contener:**

- Visión general, diagramas Mermaid, capas, flujos de datos, simulación, alerta, enriquecimiento, respuesta.
- Relación entre `src/`, `apps/`, `infra/`, `docs/`, `tests/`, `runtime`.
- Dependencias internas y externas, servicios, estado actual.

**Problemas detectados:**

- Contenedor `kibana` se menciona con nombre e imagen `docker.elastic.co/kibana/kibana:7.17.29` (es correcto
  técnicamente, pero el servicio expuesto se llama `Wazuh Dashboard`).
- Volúmenes `kibana_data` correctamente documentados como `Wazuh Dashboard`.

**Acción recomendada:** ACTUALIZAR (MEDIA) — añadir nota explícita: "El contenedor Docker se llama `kibana` y usa la
imagen Kibana, pero el servicio funcional es `Wazuh Dashboard`".

---

### 3.3 `docs/architecture/docker_architecture.md`

**Propósito:** Explicar la arquitectura Docker real.

**Problemas detectados:**

- Tabla de servicios incluye `kibana` con imagen `docker.elastic.co/kibana/kibana:7.17.29` y puerto `15601:5601` (
  correcto técnicamente, pero el nombre expuesto al usuario debe ser `Wazuh Dashboard`).
- Comandos `docker compose config`, `docker compose ps`, etc. son correctos.

**Acción recomendada:** ACTUALIZAR (MEDIA) — renombrar fila `kibana` a `Wazuh Dashboard (kibana)` y revisar salud de
`kibana`.

---

### 3.4 `docs/architecture/security.md`

**Propósito:** Seguridad del entorno.

**Problemas detectados:**

- No se detectó `Kibana` ni `Kibana` en la escaneo automático; sin embargo, debe verificarse que no haya credenciales
  reales (contraseñas en texto plano) ni referencias a puertos 8080/8081/8082 obsoletos.

**Acción recomendada:** REVISAR_MANUALMENTE (MEDIA).

---

### 3.5 `docs/getting_started/installation_guide.md`

**Propósito:** Guía de instalación.

**Problemas detectados:**

- Puerto `15601` para Wazuh Dashboard correcto.
- `MISP 8083` correcto.
- Comandos `docker compose` y `make up` correctos.
- Aún se menciona `docker-compose.yml` sin `*.yml` en algunas líneas ("Ajustar límites de recursos en
  `docker-compose.yml`").

**Acción recomendada:** ACTUALIZAR (ALTA) — cambiar `docker-compose.yml` por `docker-compose*.yml` o nombre específico.

---

### 3.6 `docs/getting_started/user_guide.md`

**Propósito:** Guía de usuario.

**Problemas detectados:**

- `http://localhost:9001` para Shuffle API es correcto en el contexto Vagrant (evita conflictos con Docker), pero el
  documento debería aclarar que se trata del mapeo Vagrant y no del puerto Docker (`15001`).
- Imágenes referenciadas correctamente; falta verificar visualmente si capturas reflejan la UI actual.

**Acción recomendada:** ACTUALIZAR (MEDIA) — añadir aclaración Vagrant vs Docker.

---

### 3.7 `docs/operations/configuration_manual.md`

**Propósito:** Manual de configuración.

**Problemas detectados:**

- Corregido en sesiones previas (puertos, credenciales, `docker compose`).
- Re-verificar tras recientes cambios de Grafana (plugin Elasticsearch, `soar_net` de Grafana).

**Acción recomendada:** MANTENER / REVISAR_MANUALMENTE (ALTA).

---

### 3.8 `docs/operations/troubleshooting.md`

**Propósito:** Resolución de problemas.

**Problemas detectados:**

- Corregido en sesiones previas.
- Algunos bloques usan `docker compose -f ...` con múltiples ficheros; validar que el orden y la lista sean exactos.
- `docker-compose.yml` mencionado en "Ajustar límites de recursos en docker-compose.yml".

**Acción recomendada:** ACTUALIZAR (ALTA) — reemplazar `docker-compose.yml` por `docker-compose*.yml`.

---

### 3.9 `docs/operations/playbooks/ransomware_playbook_e2e.md`

**Propósito:** Playbook E2E.

**Problemas detectados:**

- Puerto de webhook `15001` y Cortex `19001` corregidos.
- Re-verificar URL de Shuffle API y workflow ID actual.

**Acción recomendada:** MANTENER / REVISAR_MANUALMENTE (ALTA).

---

### 3.10 `docs/integrations/api_contracts.md`

**Propósito:** Contratos de API.

**Problemas detectados:**

- Corregido en sesión anterior.
- Verificar que endpoints `/kibana` y `/kibana/api` se documenten como `Wazuh Dashboard`.

**Acción recomendada:** MANTENER / REVISAR_MANUALMENTE (MEDIA).

---

### 3.11 `docs/integrations/overview.md`

**Propósito:** Visión general de integraciones.

**Contenido:** Matriz de servicios, puertos, credenciales, flujo de datos, contratos.

**Acción recomendada:** MANTENER (BAJA).

---

### 3.12 `docs/testing/test_suite.md`

**Propósito:** Suite de tests.

**Problemas detectados:**

- `docker compose -f ...` correcto.
- `docker-compose down -v` residual.
- `pytest --cov=src/soar_lab` corregido.

**Acción recomendada:** ACTUALIZAR (ALTA) — reemplazar `docker-compose down -v` por `docker compose down -v`.

---

### 3.13 `docs/testing/docker_testing_strategy.md`

**Propósito:** Estrategia de testing Docker.

**Problemas detectados:**

- `docker-compose.yml` y `docker-compose ps`/`logs` residuales.
- `Kibana` residual en tabla de servicios.

**Acción recomendada:** ACTUALIZAR (ALTA).

---

### 3.14 `docs/testing/README.md`

**Propósito:** Índice de testing.

**Problemas detectados:**

- No refleja que los informes `AUDIT_*.md` ya se archivaron en `docs/audit/legacy/`.
- Aún menciona `docs/testing/AUDIT_*.md` (ya no existen).

**Acción recomendada:** ACTUALIZAR (ALTA).

---

### 3.15 `docs/project/risks.md`

**Propósito:** Gestión de riesgos.

**Problemas detectados:**

- Riesgos R1, R5, R10 corregidos parcialmente.
- Aún usa `docker-compose -f ... up -d` en una mitigación y `docker-compose ps`/`logs` en otras.
- `Kibana` aparece 2 veces (residuos).

**Acción recomendada:** ACTUALIZAR (ALTA) — reemplazar `docker-compose` por `docker compose` y `Kibana` por
`Wazuh Dashboard`.

---

### 3.16 `docs/project/scope.md`

**Propósito:** Alcance.

**Problemas detectados:**

- `docker-compose*.yml` y `docker compose ps` correctos, pero `docker-compose ps` y `docker-compose.yml` aún residuales.

**Acción recomendada:** ACTUALIZAR (ALTA).

---

### 3.17 `docs/project/plan.md`

**Propósito:** Planificación.

**Problemas detectados:**

- Corregido (PostgreSQL).
- Verificar fechas y duraciones realistas.

**Acción recomendada:** MANTENER (BAJA).

---

### 3.18 `docs/project/objectives.md`

**Propósito:** Objetivos.

**Problemas detectados:**

- No se detectó `Kibana` ni `docker-compose` automáticamente.
- Debe alinearse con `thesis/objectives_and_methodology.md`.

**Acción recomendada:** MANTENER / REVISAR_MANUALMENTE (BAJA).

---

### 3.19 `API_DOCUMENTATION.md`

**Propósito:** Referencia de APIs.

**Problemas detectados:**

- Ancla `Wazuh Dashboard API` corregida.
- Sección Nginx corregida (`/misp` y `/wazuh` eliminadas, `/shuffle-api` y `/kibana` añadidas).
- Posibles rutas `/kibana` en ejemplos de curl aún válidas técnicamente.

**Acción recomendada:** MANTENER / REVISAR_MANUALMENTE (ALTA).

---

### 3.20 `apps/api/docs/` y `apps/api/api-docs.html`

**Propósito:** Documentación HTML estática de APIs.

**Problemas detectados:**

- `api-docs.html` y `docs/index.html` corregidos (puertos, Kibana → Wazuh Dashboard).
- `kibana-api.yaml` y `kibana-api.html` corregidos.
- `web-nginx.html` corregido en esta sesión.
- `elasticsearch-api.html`: ejemplos usan `localhost:9201` (debe ser `localhost:19200`).
- `wazuh-api.html`: ejemplos usan `localhost:55000` (debe ser `localhost:55100`).
- Otros HTML (`thehive-api.html`, `cortex-api.html`, `misp-api.html`, `shuffle-api.html`, `soar-lab-api.html`) requieren
  re-verificación.

**Acción recomendada:** ACTUALIZAR (CRÍTICA) `elasticsearch-api.html` y `wazuh-api.html`; REVISAR_MANUALMENTE el resto.

---

## 4. Documentos duplicados, históricos u obsoletos

| Archivo                                                      | Clasificación | Motivo                          | Acción recomendada      |
|--------------------------------------------------------------|---------------|---------------------------------|-------------------------|
| `docs/audit/legacy/AUDIT_*.md`                               | HISTÓRICO     | Informes de fases anteriores    | ARCHIVAR (ya realizado) |
| `docs/audit/legacy/AUDIT_REPORT_DEVOPS_QA_*.md`              | HISTÓRICO     | Informes sucesivos de auditoría | ARCHIVAR (ya realizado) |
| `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_COMPLETE.md` | OBSOLETO      | Vacío (0 bytes)                 | ELIMINAR                |
| `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_FINAL.md`    | OBSOLETO      | Vacío (0 bytes)                 | ELIMINAR                |
| `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-04_V4.md`       | HISTÓRICO     | Informe técnico desfasado       | ARCHIVAR                |
| `docs/testing/CODE_ANALYSIS_REPORT_2026-07-04.md`            | HISTÓRICO     | Análisis de código desfasado    | ARCHIVAR                |
| `docs/testing/GRAFANA_CHARTS_COMPARISON_2026-07-04.md`       | HISTÓRICO     | Comparación de dashboards       | ARCHIVAR                |
| `docs/testing/CHANGELOG_THESIS_UPDATE.md`                    | HISTÓRICO     | Changelog de tesis              | ARCHIVAR                |
| `AUDIT_REPORT.md` (raíz)                                     | CANONICO      | Último informe aprobado         | MANTENER                |
| `AUDIT_REPORT_DOCUMENTATION_2026-07-14.md`                   | CANONICO      | Este informe                    | MANTENER                |

## 5. Propuesta de estructura documental final

```text
docs/
├── README.md
├── architecture/
│   ├── docker_architecture.md
│   ├── overview.md
│   └── security.md
├── getting_started/
│   ├── installation_guide.md
│   ├── overview.md
│   └── user_guide.md
├── img/
├── integrations/
│   ├── api_contracts.md
│   ├── overview.md
│   └── references/
│       └── thehive_template.json
├── operations/
│   ├── configuration_manual.md
│   ├── playbooks/
│   │   └── ransomware_playbook_e2e.md
│   └── troubleshooting.md
├── project/
│   ├── objectives.md
│   ├── plan.md
│   ├── risks.md
│   └── scope.md
├── testing/
│   ├── README.md
│   ├── test_suite.md
│   └── docker_testing_strategy.md
└── thesis/
    (sin cambios estructurales; revisar manualmente)
```

**Nota:** Todos los informes de auditoría con fecha `2026-07-04` y similares deben moverse a `docs/audit/legacy/` (o
`docs/audit/archive/` si se prefiere) y `docs/testing/README.md` actualizarse para reflejar el cambio.

---

## 6. Plan de actualización

| Prioridad | Documento                                                    | Acción                                                                                         | Motivo                         | Dependencias           |
|-----------|--------------------------------------------------------------|------------------------------------------------------------------------------------------------|--------------------------------|------------------------|
| CRÍTICA   | `apps/api/docs/elasticsearch-api.html`                       | Reemplazar `localhost:9201` por `localhost:19200`                                              | Puerto obsoleto                | -                      |
| CRÍTICA   | `apps/api/docs/wazuh-api.html`                               | Reemplazar `localhost:55000` por `localhost:55100`                                             | Puerto obsoleto                | -                      |
| CRÍTICA   | `README.md` raíz                                             | Actualizar diagrama y componentes (`Kibana` → `Wazuh Dashboard`, añadir Grafana/Loki/Promtail) | Entrada principal del proyecto | -                      |
| ALTA      | `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_COMPLETE.md` | Eliminar (vacío)                                                                               | Limpieza                       | -                      |
| ALTA      | `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_FINAL.md`    | Eliminar (vacío)                                                                               | Limpieza                       | -                      |
| ALTA      | `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-04_V4.md`       | Mover a `docs/audit/legacy/`                                                                   | Archivado                      | -                      |
| ALTA      | `docs/testing/CODE_ANALYSIS_REPORT_2026-07-04.md`            | Mover a `docs/audit/legacy/`                                                                   | Archivado                      | -                      |
| ALTA      | `docs/testing/GRAFANA_CHARTS_COMPARISON_2026-07-04.md`       | Mover a `docs/audit/legacy/`                                                                   | Archivado                      | -                      |
| ALTA      | `docs/testing/CHANGELOG_THESIS_UPDATE.md`                    | Mover a `docs/audit/legacy/`                                                                   | Archivado                      | -                      |
| ALTA      | `docs/testing/README.md`                                     | Actualizar índice tras mover archivos                                                          | Coherencia                     | Mover archivos previos |
| ALTA      | `docs/project/risks.md`                                      | Reemplazar `docker-compose` → `docker compose` y `Kibana` → `Wazuh Dashboard`                  | Comandos obsoletos             | -                      |
| ALTA      | `docs/project/scope.md`                                      | Reemplazar `docker-compose` residuales                                                         | Comandos obsoletos             | -                      |
| ALTA      | `docs/testing/test_suite.md`                                 | Reemplazar `docker-compose down -v`                                                            | Comando obsoleto               | -                      |
| ALTA      | `docs/testing/docker_testing_strategy.md`                    | Reemplazar `docker-compose` residuales                                                         | Comando obsoleto               | -                      |
| ALTA      | `docs/getting_started/installation_guide.md`                 | Reemplazar `docker-compose.yml`                                                                | Nombre genérico                | -                      |
| ALTA      | `docs/operations/troubleshooting.md`                         | Reemplazar `docker-compose.yml`                                                                | Nombre genérico                | -                      |
| MEDIA     | `docs/architecture/overview.md`                              | Aclarar `kibana` vs `Wazuh Dashboard`                                                          | Nomenclatura                   | -                      |
| MEDIA     | `docs/architecture/docker_architecture.md`                   | Aclarar `kibana` vs `Wazuh Dashboard`                                                          | Nomenclatura                   | -                      |
| MEDIA     | `docs/thesis/abbreviations_list.md`                          | Revisar `Kibana` → `Wazuh Dashboard`                                                           | Coherencia                     | Revisión manual        |
| MEDIA     | `docs/thesis/appendix_a.md`                                  | Revisar `docker-compose` y `Kibana`                                                            | Documento académico            | Revisión manual        |
| MEDIA     | `docs/thesis/*`                                              | Revisar coherencia con documentación técnica                                                   | Académico                      | Revisión manual        |
| BAJA      | `docs/img/*`                                                 | Verificar actualidad de capturas                                                               | Evidencia visual               | Revisión manual        |
| BAJA      | `README.md` / `docs/README.md`                               | Añadir enlaces a `docs/audit/README.md`                                                        | Índice                         | -                      |

---

## 7. Checklist de actualización

```text
[ ] README.md raíz actualizado (diagrama, componentes, Wazuh Dashboard)
[x] Arquitectura validada (overview.md, docker_architecture.md)
[x] Docker documentado (docker_architecture.md, compose)
[x] Vagrant documentado (user_guide.md)
[x] Nginx/SSL documentado (nginx.conf, web-nginx.html, API_DOCUMENTATION.md)
[x] Installation guide validada (installation_guide.md)
[x] User guide actualizada (user_guide.md)
[x] API contracts revisados (api_contracts.md, API_DOCUMENTATION.md)
[x] Playbook e2e actualizado (ransomware_playbook_e2e.md)
[x] Troubleshooting actualizado (troubleshooting.md)
[x] Testing actualizado (test_suite.md, docker_testing_strategy.md)
[x] Coverage documentado (test_suite.md)
[x] KPIs documentados (docs/architecture/overview.md, Grafana docs)
[x] Dashboards documentados (architecture, operations, integrations)
[ ] Informes de auditoría clasificados y archivados (faltan mover 4 archivos)
[ ] Thesis alineada con proyecto (pendiente revisión manual)
[ ] Imágenes revisadas (pendiente revisión manual)
[x] Enlaces revisados (docs/README.md)
[x] Comandos revisados (principalmente `docker compose`)
[x] Puertos revisados ( operativa)
[ ] Rutas revisadas (apps/api docs pendientes)
```

---

## 8. Cambios recomendados

| Archivo                                                      | Cambio recomendado                                                                      | Motivo                     | Riesgo | Prioridad |
|--------------------------------------------------------------|-----------------------------------------------------------------------------------------|----------------------------|--------|-----------|
| `apps/api/docs/elasticsearch-api.html`                       | `localhost:9201` → `localhost:19200`                                                    | Puerto actual del host     | Bajo   | CRÍTICA   |
| `apps/api/docs/wazuh-api.html`                               | `localhost:55000` → `localhost:55100`                                                   | Puerto actual del host     | Bajo   | CRÍTICA   |
| `README.md`                                                  | Diagrama Mermaid con Wazuh Dashboard + Grafana/Loki/Promtail                            | Coherencia arquitectónica  | Bajo   | CRÍTICA   |
| `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_COMPLETE.md` | `git rm`                                                                                | Vacío                      | Bajo   | ALTA      |
| `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_FINAL.md`    | `git rm`                                                                                | Vacío                      | Bajo   | ALTA      |
| `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-04_V4.md`       | `git mv` a `docs/audit/legacy/`                                                         | Archivo histórico          | Bajo   | ALTA      |
| `docs/testing/CODE_ANALYSIS_REPORT_2026-07-04.md`            | `git mv` a `docs/audit/legacy/`                                                         | Archivo histórico          | Bajo   | ALTA      |
| `docs/testing/GRAFANA_CHARTS_COMPARISON_2026-07-04.md`       | `git mv` a `docs/audit/legacy/`                                                         | Archivo histórico          | Bajo   | ALTA      |
| `docs/testing/CHANGELOG_THESIS_UPDATE.md`                    | `git mv` a `docs/audit/legacy/`                                                         | Archivo histórico          | Bajo   | ALTA      |
| `docs/testing/README.md`                                     | Actualizar índice y eliminar referencias a `AUDIT_*.md` y `TECHNICAL_AUDIT_REPORT_*.md` | Coherencia                 | Bajo   | ALTA      |
| `docs/project/risks.md`                                      | Reemplazar `docker-compose` y `Kibana`                                                  | Comandos/nombres obsoletos | Bajo   | ALTA      |
| `docs/project/scope.md`                                      | Reemplazar `docker-compose` residual                                                    | Comando obsoleto           | Bajo   | ALTA      |
| `docs/testing/test_suite.md`                                 | `docker-compose down -v` → `docker compose down -v`                                     | Comando obsoleto           | Bajo   | ALTA      |
| `docs/testing/docker_testing_strategy.md`                    | `docker-compose` → `docker compose`                                                     | Comando obsoleto           | Bajo   | ALTA      |
| `docs/getting_started/installation_guide.md`                 | `docker-compose.yml` → `docker-compose*.yml`                                            | Nombre específico          | Bajo   | ALTA      |
| `docs/operations/troubleshooting.md`                         | `docker-compose.yml` → `docker-compose*.yml`                                            | Nombre específico          | Bajo   | ALTA      |
| `docs/architecture/overview.md`                              | Aclarar `kibana` como contenedor de `Wazuh Dashboard`                                   | Nomenclatura               | Bajo   | MEDIA     |
| `docs/architecture/docker_architecture.md`                   | Aclarar `kibana` como contenedor de `Wazuh Dashboard`                                   | Nomenclatura               | Bajo   | MEDIA     |
| `docs/thesis/*`                                              | REVISAR_MANUALMENTE                                                                     | Académico                  | Medio  | MEDIA     |
| `docs/img/*`                                                 | REVISAR_MANUALMENTE                                                                     | Evidencia visual           | Medio  | BAJA      |

---

## 9. Plan de edición (para aprobar)

### Archivos afectados

1. `apps/api/docs/elasticsearch-api.html`
2. `apps/api/docs/wazuh-api.html`
3. `README.md`
4. `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_COMPLETE.md`
5. `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-03_FINAL.md`
6. `docs/testing/TECHNICAL_AUDIT_REPORT_2026-07-04_V4.md`
7. `docs/testing/CODE_ANALYSIS_REPORT_2026-07-04.md`
8. `docs/testing/GRAFANA_CHARTS_COMPARISON_2026-07-04.md`
9. `docs/testing/CHANGELOG_THESIS_UPDATE.md`
10. `docs/testing/README.md`
11. `docs/project/risks.md`
12. `docs/project/scope.md`
13. `docs/testing/test_suite.md`
14. `docs/testing/docker_testing_strategy.md`
15. `docs/getting_started/installation_guide.md`
16. `docs/operations/troubleshooting.md`
17. `docs/architecture/overview.md`
18. `docs/architecture/docker_architecture.md`

### Resumen de cambios

- Reemplazo de puertos obsoletos en `apps/api/docs/`.
- Actualización del diagrama y componentes en `README.md`.
- Limpieza de informes de auditoría vacíos/históricos en `docs/testing/`.
- Actualización de `docker-compose` → `docker compose` y `Kibana` → `Wazuh Dashboard` en documentos operativos.
- Aclaración de nomenclatura `kibana` (contenedor) vs `Wazuh Dashboard` (servicio) en arquitectura.

### Riesgos

- Riesgo bajo: cambios en HTML/MD no afectan al código ni a la infraestructura.
- Riesgo medio: archivos `thesis/` no se editarán sin revisión manual.
- Riesgo medio: mover informes de auditoría puede romper enlaces si alguien los referencia directamente; se actualizará
  `docs/testing/README.md` y `docs/audit/README.md`.

### Validaciones posteriores

```bash
# Buscar puertos incorrectos restantes
Select-String -Path README.md, docs/*.md, docs/**/*.md, apps/api/docs/*.html -Pattern 'localhost:(9000|9001|9201|5001|8082|55000)\b' -ErrorAction SilentlyContinue

# Buscar comandos docker-compose restantes
Select-String -Path README.md, docs/*.md, docs/**/*.md -Pattern 'docker-compose(?!\.(yml|yaml|core|api|misp|wazuh|logging|\.))' -ErrorAction SilentlyContinue

# Buscar Kibana como servicio UI
Select-String -Path README.md, docs/*.md, docs/**/*.md -Pattern '\bKibana\b' -ErrorAction SilentlyContinue

# Verificar estructura
Get-ChildItem -Path docs -Recurse -Filter *.md | Measure-Object -Line
```

---

## 10. Conclusión final

```text
DOCUMENTACIÓN PARCIALMENTE CORRECTA
```

**Justificación:**

- La documentación técnica operativa (`getting_started`, `operations`, `integrations`, `testing`, `architecture` en su
  mayoría) refleja el estado real del repositorio tras las correcciones aplicadas.
- Persisten **puertos incorrectos** en `apps/api/docs/elasticsearch-api.html` y `wazuh-api.html`, y *
  *comandos `docker-compose` y nombres `Kibana`** en `docs/project/risks.md`, `scope.md`, `test_suite.md`,
  `docker_testing_strategy.md`, `installation_guide.md`, `troubleshooting.md` y `thesis/appendix_a.md`.
- Existen **informes de auditoría históricos/vacíos** en `docs/testing/` que deben archivarse o eliminarse.
- La documentación académica `thesis/` no ha sido revisada en profundidad y requiere `REVISAR_MANUALMENTE`.
- El `README.md` raíz necesita un pequeño ajuste en el diagrama y la lista de componentes para reflejar
  `Wazuh Dashboard`, `Grafana`, `Loki` y `Promtail`.

**Recomendación:** Aplicar los cambios CRÍTICOS y ALTAS del plan de actualización, luego realizar una re-verificación
automática con `grep` y finalmente una revisión manual de `thesis/` y `docs/img/`.
