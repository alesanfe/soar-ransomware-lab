# Anexo B: Playbook de Automatización SOAR en Shuffle

Aviso de sincronización: este anexo es una instantánea estática del workflow de Shuffle.
La versión canónica y actualizada se encuentra en `scripts/setup/shuffle_workflow/`
(`workflow_definition.py`, `workflow_actions.py`, y 25 scripts embebidos en `scripts/`).
En caso de discrepancia, prevalece el código del repositorio.

---

## B.1. Visión General del Workflow

El workflow SOAR se ejecuta en Shuffle 2.2.1 (Shuffle Tools, 2024) y orquesta la respuesta completa ante alertas
de ransomware. Recibe alertas vía webhook, las enriquece con TheHive (TheHive Project, 2024), Cortex (Cortex Project, 2024), MISP (MISP Project, 2024) y fuentes
de logging, calcula un score de riesgo, toma una decisión automatizada (contener u observar),
y registra métricas MTTR en Elasticsearch (Elastic, 2024).

| Parámetro | Valor |
|-----------|-------|
| **Nombre** | `SOAR-Ransomware-Response` |
| **Trigger** | Webhook (Shuffle Triggers) |
| **Acciones totales** | 45 nodos de acción + 1 trigger = 46 nodos definidos (49 ejecutados) |
| **Ramas (edges)** | 61 (59 base + 2 dinámicas) |
| **Apps usadas** | HTTP, Shuffle Tools (Python embebido) |
| **Timeout por acción** | 30-180s según nodo |
| **Concurrencia** | Análisis paralelo tras creación de caso |

---

## B.2. Arquitectura del Workflow

El workflow sigue un patrón fan-out/fan-in: tras la creación del caso en TheHive, 10 ramas paralelas ejecutan enriquecimiento (Cortex, MISP, Tenzir, Network Watcher, Redis, Loki, ES index) y registro de observables (hash, IP, tarea). Todas las señales convergen en `act_calc_decision`, que calcula el score y dispatcha a contención (score ≥ 80 OR verdict=malicious) o falso positivo (score < 80). El flujo cierra con cálculo de MTTR, enriquecimiento del caso y indexación de métricas en `soar-metrics`.

El diagrama canónico del flujo end-to-end está en el Anexo H, sección H.5 (Flujo End-to-End de Alertas) y H.7 (Respuesta Automatizada).

---

## B.3. Catálogo de Nodos del Workflow

El workflow tiene 46 nodos definidos (45 acciones + 1 trigger). Se agrupan por tipo:

### B.3.1. Nodos HTTP (integraciones externas)

| ID | Nombre | Tipo | Descripción |
|----|--------|------|-------------|
| `webhook_trigger` | Webhook | Trigger | Recibe alerta SIEM vía POST |
| `act_thehive_create_case` | Create Case | HTTP POST | `POST /api/case` — crea caso con título, descripción, severidad, TLP, tags |
| `act_thehive_add_task` | Add Task | HTTP POST | `POST /api/case/{id}/task` — añade tarea de investigación |
| `act_thehive_obs_hash` | Observable Hash | HTTP POST | `POST /api/case/{id}/artifact` — registra hash como IoC |
| `act_thehive_obs_ip` | Observable IP | HTTP POST | `POST /api/case/{id}/artifact` — registra IP como IoC |
| `act_enrich_case` | Enrich Case | HTTP PATCH | `PATCH /api/case/{id}` — actualiza descripción con resumen y tags |
| `act_cortex_hash` | Cortex Hash | HTTP POST | `analyzer/run` — analiza hash (Hashdd_Status) |
| `act_cortex_ip` | Cortex IP | HTTP POST | `analyzer/run` — geolocaliza IP (IP-API) |
| `act_cortex_ip_dshield` | DShield | HTTP POST | Reputa IP en DShield (dinámico) |
| `act_cortex_ip_mnemonic_pdns` | Mnemonic pDNS | HTTP POST | Passive DNS lookup (dinámico) |
| `act_cortex_ip_googledns` | GoogleDNS | HTTP POST | DNS resolution (dinámico) |
| `act_cortex_ip_ipapi` | IP-API (sec) | HTTP POST | Info adicional de IP (dinámico) |
| `act_misp_create_event` | MISP Create | HTTP POST | `POST /events` — crea evento con hash e IP |
| `act_misp_search` | MISP Search | HTTP POST | `POST /attributes/restSearch` — busca hash en base MISP |
| `act_tenzir_analyze` | Tenzir Analyze | HTTP POST | `POST /api/v0/pipeline/create` — pipeline de análisis de red |
| `act_tenzir_serve` | Tenzir Serve | HTTP POST | `POST /api/v0/serve` — obtiene resultados del pipeline |
| `act_network_watch` | Network Watch | HTTP GET | `GET /api/connections?ip=...` — conexiones sospechosas |
| `act_redis_cache` | Redis Cache | HTTP POST | `POST /api/v1/cache/ioc` — cachea IoC con TTL 3600s |
| `act_loki_search` | Loki Search | HTTP GET | `GET /loki/api/v1/query_range` — busca logs relacionados |
| `act_es` | ES Index Alert | HTTP POST | `POST /soar-alerts/_doc/{alert_id}` — indexa alerta |
| `act_index_metrics` | Index Metrics | HTTP POST | `POST /soar-metrics/_doc/{alert_id}` — indexa métricas |

Nota: Los analyzers secundarios (DShield, Mnemonic pDNS, GoogleDNS, IP-API secundario)
se incluyen dinámicamente solo si están instalados en Cortex. El workflow detecta
automáticamente qué analyzers están disponibles. Adicionalmente, cualquier analyzer
instalado no listado arriba se cablea dinámicamente como `act_cortex_dyn_*` (ej.
`DomainMailSPFDMARC_1_2` para análisis de dominios SPF/DMARC, 12 jobs en la ejecución
experimental). `Virusshare_2_0` está en `_SKIP_DYNAMIC_NAMES` (fallo persistente) y no
se cablea.

### B.3.2. Nodos Python (lógica embebida)

| ID | Nombre | Descripción |
|----|--------|-------------|
| `act_normalize_inputs` | Normalize Inputs | Valida campos obligatorios, normaliza severidad, extrae hash/IP/hostname |
| `act_build_case_json` | Build Case JSON | Construye payload JSON para crear caso en TheHive |
| `act_calc_task_title` | Calc Task Title | Genera título dinámico para tarea de investigación |
| `act_verify_task` | Verify Task | Confirma que la tarea se creó correctamente |
| `act_verify_obs_hash` | Verify Obs Hash | Confirma que el observable hash se registró |
| `act_verify_obs_ip` | Verify Obs IP | Confirma que el observable IP se registró |
| `act_verify_cortex_hash` | Verify Cortex Hash | Extrae taxonomías del job de Cortex (hash) |
| `act_verify_cortex_ip` | Verify Cortex IP | Extrae taxonomías del job de Cortex (IP) |
| `act_verify_misp` | Verify MISP | Procesa resultados de búsqueda MISP |
| `act_verify_es` | Verify ES | Confirma indexación en Elasticsearch |
| `act_verify_tenzir` | Verify Tenzir | Procesa eventos de red de Tenzir |
| `act_verify_network` | Verify Network | Procesa conexiones del Network Watcher |
| `act_verify_redis` | Verify Redis | Confirma caching de IoC en Redis |
| `act_verify_loki` | Verify Loki | Procesa logs relevantes de Loki |
| `act_build_es_json` | Build ES JSON | Construye documento para indexar alerta en ES |
| `act_calc_decision` | Calc Decision | **Núcleo del workflow**: calcula score (0-100) y verdict |
| `act_containment` | Containment | Contención vía Lab API (`POST /api/v1/contain`) |
| `act_mark_false_positive` | Mark FP | Marca caso como falso positivo en TheHive |
| `act_update_inprogress` | Update InProgress | Confirma caso permanece `Open` (TheHive 3.5.2 solo soporta Open/Resolved/Deleted) |
| `act_notify_critical` | Notify Critical | Envía notificación crítica (email) |
| `act_notify_info` | Notify Info | Envía notificación informativa (email) |
| `act_calc_mttr` | Calc MTTR | Calcula tiempo total de respuesta (MTTR) |
| `act_build_hive_summary` | Build Hive Summary | Construye resumen ejecutivo para enriquecer caso |
| `act_build_metrics_json` | Build Metrics JSON | Construye documento de métricas (score, verdict, MTTR) |

Los 25 scripts Python embebidos viven como archivos `.py` independientes en `scripts/setup/shuffle_workflow/scripts/`, con nombres coincidentes a los IDs de nodo (ej. `calc_decision.py`, `containment.py`, `notify_critical.py`).

---

## B.4. Modelo de Scoring (calc_decision)

El nodo `calc_decision` es el núcleo del workflow. Calcula un score de 0 a 100 y un verdict
(malicious, suspicious, safe, unknown) agregando señales de todas las fuentes de enriquecimiento.

### B.4.1. Componentes del Score

| Fuente | Contribución | Descripción |
|--------|-------------|-------------|
| **Cortex taxonomies** | max(level value) | Score máximo entre todos los analyzers de Cortex |
| **MISP IoCs** | +15 si hay matches | Suma fija si MISP encuentra coincidencias |
| **Webhook confidence** | base score | Confianza declarada por el SIEM en la alerta |
| **Severidad** | 1->20, 2->40, 3->60 | Mapeo directo de severidad (Low/Medium/High) |
| **Tipo de alerta** | ransomware +25, malware/phishing/intrusion +15 | Bonus según tipo de alerta |
| **Event type** | +10 si contiene "ransomware" | Bonus adicional para eventos de ransomware |
| **MITRE high-risk** | +10 por técnica | Técnicas de alto riesgo (T1486, T1485, T1490, etc.) |
| **Tenzir** | +5 a +25 | Patrones de red sospechosos |
| **Network Watcher** | +5 a +20 | Conexiones sospechosas detectadas |
| **Loki** | +3 a +30 | Indicadores de ransomware en logs (fórmula: `min(30, matches*3 + critical*10)`) |

### B.4.2. Umbral de Decisión

| Condición | Verdict | Decision | Acción |
|-----------|---------|----------|--------|
| `score ≥ 80` OR `verdict == "malicious"` | malicious | **contain** | Contención vía Lab API (`POST /api/v1/contain`), caso permanece `Open`, notify critical |
| `score < 80` AND `verdict != "malicious"` | suspicious/safe | **observe** | Marcar caso como `Resolved`/`FalsePositive` en TheHive, notify info |

Nota: La condición de contención es `score >= 80 OR verdict == "malicious"`, no solo `score >= 80`.
Esto permite que un verdict "malicious" de Cortex (independientemente del score) dispare contención.

### B.4.3. Técnicas MITRE de Alto Riesgo

Las técnicas de alto riesgo se basan en el framework MITRE ATT&CK (MITRE, 2025):

```python
HIGH_RISK_TECHNIQUES = {
    "T1486": "Data Encrypted for Impact",
    "T1485": "Data Destroyed",
    "T1490": "Inhibit System Recovery",
    "T1059": "Command and Scripting Interpreter",
    "T1218": "System Binary Proxy Execution",
    "T1071": "Application Layer Protocol",
    "T1571": "Non-Standard Port",
    "T1572": "Protocol Tunneling",
    "T1573": "Encrypted Channel",
}
```

Cada técnica de alto riesgo detectada suma **+10 puntos** al score.

---

## B.5. Ramas (Edges) del Workflow

El workflow tiene **61 ramas** (59 base + 2 dinámicas) que conectan los nodos en un patrón fan-out/fan-in:

| Flujo | Descripción |
|-------|-------------|
| Principal | webhook → normalize → build_case → thehive_create_case → fan-out a 10 ramas paralelas (Cortex hash/IP, MISP, Tenzir, Network Watcher, Redis, Loki, ES index, obs hash/IP, task) |
| Decisión | Todas las verificaciones convergen en `act_calc_decision` → dispatch a `act_containment` (score ≥ 80) o `act_mark_false_positive` (score < 80) |
| Cierre | notify → calc_mttr → build_hive_summary → enrich_case → build_metrics_json → index_metrics |

Nota técnica: Shuffle 2.2.1 no evalúa condiciones en las ramas nativamente.
Ambas ramas (contain y observe) se ejecutan incondicionalmente, pero cada nodo
downstream verifica internamente `$calc_decision.message.decision` y ejecuta
su lógica solo si el verdict corresponde.

---

## B.6. Resultados Experimentales del Workflow

Datos medidos en ejecución experimental (n=50 alertas, 2026-08-24, fuente: `docs/thesis/reports/e2e_report.json`):

| Métrica | Valor |
|---------|-------|
| Workflows completados | 50/50 (100%) |
| MTTR medio | 277.15s |
| MTTR P50 | 193.19s |
| MTTR P90 | 621.83s |
| MTTR min/max | 65.38s / 652.92s |
| Tasa de contención (score ≥ 80) | 92.0% (46/50) |
| Tasa de observación (score < 80) | 8.0% (4/50) |
| Nodos por ejecución | 49 (reportado por Shuffle; 46 definidos + 3 dinámicos) |
| Ramas definidas | 61 (59 base + 2 dinámicas) |
| Jobs de Cortex | 257 (255 success, 2 failure) |
| Casos TheHive | 50 (46 Open, 4 Resolved) |
| Tasa de automatización | 100% (sin intervención humana) |
