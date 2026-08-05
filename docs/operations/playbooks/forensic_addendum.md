# Adenda Forense — Playbook Ransomware E2E

## 1. TheHive healthcheck: `/api/status`

TheHive expone el endpoint `GET /api/status` para verificar salud sin autenticación previa. Se usa en el healthcheck de Docker Compose para evitar falsos negativos mientras Elasticsearch prepara los índices de TheHive.

```bash
curl -f http://localhost:19000/api/status
```

Respuesta típica (JSON con `status`):

```json
{ "status": "OK", "version": "3.5.2-1" }
```

## 2. Orborus y red de analizadores

- **Orborus** (`ghcr.io/shuffle/shuffle-orborus:2.2.1`) ejecuta los contenedores de analizadores que lanza el workflow de Shuffle.
- Requiere acceso al socket Docker del host (`/var/run/docker.sock`) para crear contenedores en la misma red `soar_net`.
- El entorno `SHUFFLE_APP_NETWORK` debe apuntar a `${COMPOSE_PROJECT_NAME}_net` (por defecto `soar_net`) para que los analizadores puedan resolver `api`, `thehive`, `cortex`, `misp` y `elasticsearch` por DNS interno.
- `SHUFFLE_ORBORUS_EXECUTION_CONCURRENCY` se fija a `5` en `docker-compose.core.yml` para evitar timeouts bajo carga concurrente.

## 3. Campos forenses de `thehive_template.json`

La plantilla de caso `docs/integrations/references/thehive_template.json` incluye campos personalizados relevantes para la trazabilidad forense:

| Campo | Tipo | Propósito |
|-------|------|-----------|
| `hostname` | string | Endpoint afectado |
| `username` | string | Cuenta de usuario involucrada |
| `file_hash` | string | Hash SHA256 del archivo sospechoso |
| `src_ip` | ip | IP origen del actor de amenaza |
| `wazuh_alert_id` | string | ID de la alerta de Wazuh que originó el caso |
| `wazuh_rule_id` | string | Regla de Wazuh que generó la alerta |
| `detection_time` | date | Timestamp de detección |
| `shuffle_workflow_id` | string | ID de ejecución del workflow en Shuffle |
| `misp_event_id` | string | ID del evento MISP correlacionado |
| `containment_status` | string | Estado de la contención (`pending` / `in_progress` / `completed`) |
| `containment_action_id` | string | Identificador de la acción de contención ejecutada (ej. `network_isolation_001`) |
| `containment_status_history` | string | Historial de transiciones de estado, separado por comas |
| `mitre_tactic_id` | string | Táctica MITRE ATT&CK principal asociada (ej. `TA0040`) |
| `analyzer_score` | number | Puntuación de amenaza de los analyzers de Cortex (0-100) |

### 3.1 Simulación vs contención real

- El workflow E2E y los campos de `thehive_template.json` documentan **acciones simuladas o notificadas**.
- `containment_status`, `containment_action_id` y `containment_status_history` reflejan el estado decidido por el workflow, **no modifican directamente endpoints reales**.
- Una contención real requiere una integración con EDR/agente o firewall operativo; en este laboratorio se simula mediante `notify.sh` / llamadas a `api/v1/contain` que registran la acción sin ejecutar cambios reales en hosts de producción.

### 3.2 Campo `total_time_manual`

- `total_time_manual` no está presente en el código ni en los índices de métricas actuales.
- Fue eliminado del modelo de datos; el MTTR se calcula de forma automatizada (`mttr_seconds` en `soar-metrics`) y se almacena mediante `src/soar_lab/domain/services/kpi_analyzer.py`.
- Si aparece en documentación antigua o en `legacy/`, debe considerarse obsoleto.

## 4. MTTR y percentiles (P50 / P90)

- **MTTR (Mean Time To Respond)**: tiempo medio desde la detección de la alerta hasta el cierre o contención del incidente.
- **P50**: mediana de los tiempos de respuesta observados.
- **P90**: percentil 90; el 90% de las ejecuciones responden en menos de este valor.

Umbrales definidos en el alcance del proyecto:

| Métrica | Objetivo | Estado |
|---------|----------|--------|
| P50 | ≤ 120 s | Operativo |
| P90 | ≤ 180 s | Operativo |

El cálculo se realiza en `src/soar_lab/domain/services/kpi_analyzer.py` y se indexa en `soar-metrics` con el campo `mttr_seconds` (`float`) y `@timestamp` (`date`) para consultas en Grafana.

## 5. Definiciones: MTTR, IaC y CORS

- **MTTR**: Mean Time To Respond / Mean Time To Remediate. En este proyecto se mide desde el envío de la alerta al webhook hasta la finalización del workflow, registrado en `artifacts/logs/playbook_execution.log` e indexado en `soar-metrics`.
- **IaC (Infrastructure as Code)**: toda la infraestructura del laboratorio está declarada en archivos Docker Compose bajo `infra/docker/compose/` y en scripts de Vagrant bajo `infra/vagrant/`. No se requiere configuración manual de red o volúmenes salvo la generación de secretos y certificados.
- **CORS (Cross-Origin Resource Sharing)**: configurado en `src/soar_lab/interfaces/api/main.py` mediante `CORSMiddleware`, leyendo orígenes desde `CORS_ORIGINS` en `.env.full`. Permite que la SPA `apps/web-management` consuma la API tanto desde `https://soar.local` como desde `http://localhost:8085`.

## Referencias

- `docs/integrations/references/thehive_template.json`
- `src/soar_lab/domain/services/kpi_analyzer.py`
- `infra/docker/compose/docker-compose.core.yml`
- `src/soar_lab/interfaces/api/main.py`
