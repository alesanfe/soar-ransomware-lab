# Anexo B: Playbook de Automatización SOAR en Shuffle

> **Aviso de sincronización**: este anexo es una instantánea estática del workflow de Shuffle.
> La versión canónica y actualizada se encuentra en `scripts/setup/shuffle_workflow/`
> (`workflow_definition.py`, `workflow_actions.py`, y 25 scripts embebidos en `scripts/`).
> En caso de discrepancia, prevalece el código del repositorio.

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

```
                         ┌─────────────┐
                         │   WEBHOOK   │  (Trigger - SIEM alert intake)
                         │  webhook_   │
                         │  trigger    │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │ NORMALIZE   │  act_normalize_inputs
                         │ INPUTS      │  (Python: valida y normaliza alerta)
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │ BUILD CASE  │  act_build_case_json
                         │ JSON        │  (Python: construye payload TheHive)
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │ THEHIVE     │  act_thehive_create_case
                         │ CREATE CASE │  (HTTP POST /api/case)
                         └──────┬──────┘
                                │
              ┌─────────────────┼─────────────────────┐
              │                 │                     │
     ┌────────▼──────┐  ┌──────▼───────┐    ┌────────▼────────┐
     │ OBS HASH      │  │ CALC TASK    │    │ OBS IP          │
     │ (TheHive)     │  │ TITLE        │    │ (TheHive)       │
     │ POST artifact │  │ (Python)     │    │ POST artifact   │
     └────────┬──────┘  └──────┬───────┘    └────────┬────────┘
              │                │                     │
     ┌────────▼──────┐  ┌──────▼───────┐            │
     │ VERIFY OBS    │  │ ADD TASK     │            │
     │ HASH          │  │ (TheHive)    │            │
     │ (Python)      │  │ POST /task   │            │
     └────────┬──────┘  └──────┬───────┘            │
              │                │                     │
              │         ┌──────▼───────┐            │
              │         │ VERIFY TASK  │            │
              │         │ (Python)     │            │
              │         └──────┬───────┘            │
              │                │                     │
     ┌────────▼──────┐         │           ┌────────▼────────┐
     │ CORTEX HASH   │         │           │ CORTEX IP       │
     │ (HTTP POST)   │         │           │ (HTTP POST)     │
     │ analyzer/run  │         │           │ analyzer/run    │
     └────────┬──────┘         │           └────────┬────────┘
              │                │                     │
     ┌────────▼──────┐         │           ┌────────▼────────┐
     │ VERIFY CORTEX │         │           │ VERIFY CORTEX   │
     │ HASH          │         │           │ IP              │
     │ (Python)      │         │           │ (Python)        │
     └────────┬──────┘         │           └────────┬────────┘
              │                │                     │
              │  ┌─────────────┼─────────────────────┤
              │  │             │                     │
              │  │  ┌──────────▼──────────┐         │
              │  │  │ MISP CREATE EVENT   │         │
              │  │  │ (HTTP POST /events) │         │
              │  │  └──────────┬──────────┘         │
              │  │             │                     │
              │  │  ┌──────────▼──────────┐         │
              │  │  │ MISP SEARCH         │         │
              │  │  │ (HTTP POST          │         │
              │  │  │  /attributes/       │         │
              │  │  │   restSearch)       │         │
              │  │  └──────────┬──────────┘         │
              │  │             │                     │
              │  │  ┌──────────▼──────────┐         │
              │  │  │ VERIFY MISP         │         │
              │  │  │ (Python)            │         │
              │  │  └──────────┬──────────┘         │
              │  │             │                     │
              │  │  ┌──────────▼──────────┐ ┌───────▼───────┐
              │  │  │ BUILD ES JSON       │ │ TENZIR        │
              │  │  │ (Python)            │ │ ANALYZE       │
              │  │  └──────────┬──────────┘ │ (HTTP POST)   │
              │  │             │            └───────┬───────┘
              │  │  ┌──────────▼──────────┐         │
              │  │  │ ES INDEX ALERT      │ ┌───────▼───────┐
              │  │  │ (HTTP POST          │ │ TENZIR SERVE  │
              │  │  │  /soar-alerts/)     │ │ (HTTP POST)   │
              │  │  └──────────┬──────────┘ └───────┬───────┘
              │  │             │            ┌───────▼───────┐
              │  │  ┌──────────▼──────────┐ │ VERIFY TENZIR │
              │  │  │ VERIFY ES           │ │ (Python)      │
              │  │  │ (Python)            │ └───────┬───────┘
              │  │  └──────────┬──────────┘         │
              │  │             │  ┌─────────────────┤
              │  │             │  │                  │
              │  │             │  │ ┌───────────────▼──────────┐
              │  │             │  │ │ NETWORK WATCHER          │
              │  │             │  │ │ (HTTP GET /api/          │
              │  │             │  │ │  connections?ip=...)     │
              │  │             │  │ └───────────┬──────────────┘
              │  │             │  │             │
              │  │             │  │ ┌───────────▼──────────────┐
              │  │             │  │ │ VERIFY NETWORK           │
              │  │             │  │ │ (Python)                 │
              │  │             │  │ └───────────┬──────────────┘
              │  │             │  │             │
              │  │             │  │ ┌───────────▼──────────────┐
              │  │             │  │ │ REDIS CACHE              │
              │  │             │  │ │ (HTTP POST /api/v1/      │
              │  │             │  │ │  cache/ioc)              │
              │  │             │  │ └───────────┬──────────────┘
              │  │             │  │             │
              │  │             │  │ ┌───────────▼──────────────┐
              │  │             │  │ │ VERIFY REDIS             │
              │  │             │  │ │ (Python)                 │
              │  │             │  │ └───────────┬──────────────┘
              │  │             │  │             │
              │  │             │  │ ┌───────────▼──────────────┐
              │  │             │  │ │ LOKI SEARCH              │
              │  │             │  │ │ (HTTP GET /loki/api/v1/  │
              │  │             │  │ │  query_range)            │
              │  │             │  │ └───────────┬──────────────┘
              │  │             │  │             │
              │  │             │  │ ┌───────────▼──────────────┐
              │  │             │  │ │ VERIFY LOKI              │
              │  │             │  │ │ (Python)                 │
              │  │             │  │ └───────────┬──────────────┘
              │  │             │  │             │
              └──┴─────────────┴──┴─────────────┤
                                              │
                                    ┌─────────▼─────────┐
                                    │  CALC DECISION    │  act_calc_decision
                                    │  (Python)         │  Score 0-100
                                    │  Score + Verdict  │  Verdict: malicious/
                                    └─────────┬─────────┘  suspicious/safe
                                              │
                          ┌───────────────────┴───────────────────┐
                          │                                       │
                 score≥80 │                              score<80 │
                          │                                       │
                 ┌────────▼────────┐                    ┌─────────▼─────────┐
                 │ CONTAINMENT     │                    │ MARK FALSE        │
                 │ (Python)        │                    │ POSITIVE          │
                 │ Lab API         │                    │ (Python)          │
                 │ POST /api/v1/   │                    │ TheHive PATCH     │
                 │  contain        │                    │ Resolved/FP       │
                 └────────┬────────┘                    └─────────┬─────────┘
                          │                                       │
                 ┌────────▼────────┐                    ┌─────────▼─────────┐
                 │ UPDATE          │                    │ NOTIFY INFO       │
                 │ INPROGRESS      │                    │ (Python)          │
                 │ (Python)        │                    │ Email notification│
                 │ Case stays Open │                    └─────────┬─────────┘
                 └────────┬────────┘                              │
                          │                                       │
                 ┌────────▼────────┐                              │
                 │ NOTIFY CRITICAL │                              │
                 │ (Python)        │                              │
                 │ Email notification│                           │
                 └────────┬────────┘                              │
                          │                                       │
                          └───────────────────┬───────────────────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │  CALC MTTR        │  act_calc_mttr
                                    │  (Python)         │  Calcula tiempo total
                                    └─────────┬─────────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │  BUILD HIVE       │  act_build_hive_summary
                                    │  SUMMARY          │  (Python: resume resultados)
                                    └─────────┬─────────┘
                                              │
                                    ┌─────────▼─────────┐
                                    │  ENRICH CASE      │  act_enrich_case
                                    │  (TheHive PATCH)  │  Actualiza descripción
                                    └─────────┬─────────┘  y tags del caso
                                              │
                                    ┌─────────▼─────────┐
                                    │  BUILD METRICS    │  act_build_metrics_json
                                    │  JSON             │  (Python: score, verdict,
                                    └─────────┬─────────┘   MTTR, decisiones)
                                              │
                                    ┌─────────▼─────────┐
                                    │  INDEX METRICS    │  act_index_metrics
                                    │  (ES POST)        │  /soar-metrics/_doc/
                                    └───────────────────┘  {alert_id}
```

---

## B.3. Catálogo de Nodos del Workflow

### B.3.1. Nodos de Entrada y Normalización

| ID | Nombre | Tipo | Descripción |
|----|--------|------|-------------|
| `webhook_trigger` | Webhook | Trigger | Recibe alerta SIEM vía POST |
| `act_normalize_inputs` | Normalize Inputs | Python | Valida campos obligatorios, normaliza severidad, extrae hash/IP/hostname |
| `act_build_case_json` | Build Case JSON | Python | Construye payload JSON para crear caso en TheHive |

### B.3.2. Nodos de TheHive (Gestión de Casos)

| ID | Nombre | Tipo | Descripción |
|----|--------|------|-------------|
| `act_thehive_create_case` | Create Case | HTTP POST | `POST /api/case` — crea caso con título, descripción, severidad, TLP, tags |
| `act_calc_task_title` | Calc Task Title | Python | Genera título dinámico para tarea de investigación |
| `act_thehive_add_task` | Add Task | HTTP POST | `POST /api/case/{id}/task` — añade tarea de investigación |
| `act_thehive_obs_hash` | Observable Hash | HTTP POST | `POST /api/case/{id}/artifact` — registra hash como IoC |
| `act_thehive_obs_ip` | Observable IP | HTTP POST | `POST /api/case/{id}/artifact` — registra IP como IoC |
| `act_enrich_case` | Enrich Case | HTTP PATCH | `PATCH /api/case/{id}` — actualiza descripción con resumen y tags |
| `act_update_inprogress` | Update InProgress | Python | Confirma que el caso permanece `Open` durante la contención (TheHive 3.5.2 solo soporta Open/Resolved/Deleted; no se hace PATCH) |
| `act_mark_false_positive` | Mark FP | Python | Marca caso como falso positivo en TheHive (vía HTTP PATCH) |

### B.3.3. Nodos de Verificación (Python)

| ID | Nombre | Descripción |
|----|--------|-------------|
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

### B.3.4. Nodos de Cortex (Análisis de IoCs)

| ID | Nombre | Analyzer | Tipo | Descripción |
|----|--------|----------|------|-------------|
| `act_cortex_hash` | Cortex Hash | Hashdd_Status | HTTP POST | Analiza hash del proceso |
| `act_cortex_ip` | Cortex IP | IP-API | HTTP POST | Geolocaliza IP source |
| `act_cortex_ip_dshield` | DShield | DShield_lookup | HTTP POST | Reputa IP en DShield |
| `act_cortex_ip_mnemonic_pdns` | Mnemonic pDNS | Mnemonic_pDNS_Public | HTTP POST | Passive DNS lookup |
| `act_cortex_ip_googledns` | GoogleDNS | GoogleDNS_resolve | HTTP POST | DNS resolution |
| `act_cortex_ip_ipapi` | IP-API (sec) | IP-API | HTTP POST | Info adicional de IP |

> **Nota**: Los analyzers secundarios (DShield, Mnemonic pDNS, GoogleDNS, IP-API secundario)
> se incluyen dinámicamente solo si están instalados en Cortex. El workflow detecta
> automáticamente qué analyzers están disponibles. Adicionalmente, cualquier analyzer
> instalado no listado arriba se cablea dinámicamente como `act_cortex_dyn_*` (ej.
> `DomainMailSPFDMARC_1_2` para análisis de dominios SPF/DMARC, 12 jobs en la ejecución
> experimental). `Virusshare_2_0` está en `_SKIP_DYNAMIC_NAMES` (fallo persistente) y no
> se cablea.

### B.3.5. Nodos de MISP (Threat Intelligence)

| ID | Nombre | Tipo | Descripción |
|----|--------|------|-------------|
| `act_misp_create_event` | MISP Create | HTTP POST | `POST /events` — crea evento con hash e IP como atributos |
| `act_misp_search` | MISP Search | HTTP POST | `POST /attributes/restSearch` — busca hash en base MISP |

### B.3.6. Nodos de Enriquecimiento Avanzado

| ID | Nombre | Tipo | Descripción |
|----|--------|------|-------------|
| `act_tenzir_analyze` | Tenzir Analyze | HTTP POST | `POST /api/v0/pipeline/create` — crea pipeline de análisis de red |
| `act_tenzir_serve` | Tenzir Serve | HTTP POST | `POST /api/v0/serve` — obtiene resultados del pipeline |
| `act_network_watch` | Network Watch | HTTP GET | `GET /api/connections?ip=...` — conexiones de red sospechosas |
| `act_redis_cache` | Redis Cache | HTTP POST | `POST /api/v1/cache/ioc` — cachea IoC con TTL 3600s |
| `act_loki_search` | Loki Search | HTTP GET | `GET /loki/api/v1/query_range` — busca logs relacionados |

### B.3.7. Nodos de Decisión y Respuesta

| ID | Nombre | Tipo | Descripción |
|----|--------|------|-------------|
| `act_calc_decision` | Calc Decision | Python | **Núcleo del workflow**: calcula score (0-100) y verdict |
| `act_containment` | Containment | Python | Contención vía Lab API (`POST /api/v1/contain` al servicio `api:8000`) |
| `act_notify_critical` | Notify Critical | Python | Envía notificación crítica (email) |
| `act_notify_info` | Notify Info | Python | Envía notificación informativa (email) |

### B.3.8. Nodos de Métricas y Cierre

| ID | Nombre | Tipo | Descripción |
|----|--------|------|-------------|
| `act_build_es_json` | Build ES JSON | Python | Construye documento para indexar alerta en ES |
| `act_es` | ES Index Alert | HTTP POST | `POST /soar-alerts/_doc/{alert_id}` — indexa alerta |
| `act_calc_mttr` | Calc MTTR | Python | Calcula tiempo total de respuesta (MTTR) |
| `act_build_hive_summary` | Build Hive Summary | Python | Construye resumen ejecutivo para enriquecer caso |
| `act_build_metrics_json` | Build Metrics JSON | Python | Construye documento de métricas (score, verdict, MTTR, decisiones) |
| `act_index_metrics` | Index Metrics | HTTP POST | `POST /soar-metrics/_doc/{alert_id}` — indexa métricas |

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

> **Nota**: La condición de contención es `score >= 80 OR verdict == "malicious"`, no solo `score >= 80`.
> Esto permite que un verdict "malicious" de Cortex (independientemente del score) dispare contención.

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

El workflow tiene **61 ramas** (59 base + 2 dinámicas) que conectan los nodos. Las principales son:

### B.5.1. Flujo Principal

| Origen | Destino | Descripción |
|--------|---------|-------------|
| webhook_trigger | act_normalize_inputs | Webhook -> normalización |
| act_normalize_inputs | act_build_case_json | Normalización -> construcción de caso |
| act_build_case_json | act_thehive_create_case | JSON -> creación de caso en TheHive |
| act_thehive_create_case | act_thehive_obs_hash | Caso -> observable hash (paralelo) |
| act_thehive_create_case | act_thehive_obs_ip | Caso -> observable IP (paralelo) |
| act_thehive_create_case | act_calc_task_title | Caso -> cálculo título tarea (paralelo) |
| act_thehive_create_case | act_cortex_hash | Caso -> análisis Cortex hash (paralelo) |
| act_thehive_create_case | act_cortex_ip | Caso -> análisis Cortex IP (paralelo) |
| act_thehive_create_case | act_misp_create_event | Caso -> creación evento MISP (paralelo) |
| act_thehive_create_case | act_build_es_json | Caso -> indexación ES (paralelo) |
| act_thehive_create_case | act_tenzir_analyze | Caso -> análisis Tenzir (paralelo) |
| act_thehive_create_case | act_network_watch | Caso -> Network Watcher (paralelo) |
| act_thehive_create_case | act_redis_cache | Caso -> Redis cache (paralelo) |
| act_thehive_create_case | act_loki_search | Caso -> Loki search (paralelo) |

### B.5.2. Flujo de Decisión

| Origen | Destino | Descripción |
|--------|---------|-------------|
| Todas las verificaciones | act_calc_decision | Convergencia: todas las señales -> decisión |
| act_calc_decision | act_containment | Decisión -> contención (score ≥ 80 OR verdict=malicious) |
| act_calc_decision | act_mark_false_positive | Decisión -> falso positivo (score < 80 AND verdict≠malicious) |
| act_containment | act_update_inprogress | Contención -> caso permanece Open |
| act_update_inprogress | act_notify_critical | Confirmación Open -> notificación crítica |
| act_mark_false_positive | act_notify_info | FP (Resolved/FalsePositive) -> notificación informativa |

### B.5.3. Flujo de Cierre

| Origen | Destino | Descripción |
|--------|---------|-------------|
| act_notify_critical | act_calc_mttr | Notificación -> cálculo MTTR |
| act_notify_info | act_calc_mttr | Notificación -> cálculo MTTR |
| act_calc_mttr | act_build_hive_summary | MTTR -> resumen del caso |
| act_build_hive_summary | act_enrich_case | Resumen -> enriquecer caso TheHive |
| act_enrich_case | act_build_metrics_json | Enriquecer -> construir métricas |
| act_build_metrics_json | act_index_metrics | Métricas -> indexar en ES |

> **Nota técnica**: Shuffle 2.2.1 no evalúa condiciones en las ramas nativamente.
> Ambas ramas (contain y observe) se ejecutan incondicionalmente, pero cada nodo
> downstream verifica internamente `$calc_decision.message.decision` y ejecuta
> su lógica solo si el verdict corresponde.

---

## B.6. Scripts Embebidos (Python)

El workflow incluye **25 scripts Python embebidos** en nodos Shuffle Tools.
Cada script vive como archivo `.py` independiente en `scripts/setup/shuffle_workflow/scripts/`:

| Script | Función |
|--------|---------|
| `normalize_inputs.py` | Valida y normaliza campos de la alerta entrante |
| `thehive_create_case_idempotent.py` | Crea caso en TheHive con búsqueda previa (idempotencia) |
| `build_case_json.py` | Construye payload JSON para TheHive |
| `calc_task_title.py` | Genera título dinámico para tarea |
| `verify_task.py` | Verifica creación de tarea |
| `verify_obs_hash.py` | Verifica observable hash |
| `verify_obs_ip.py` | Verifica observable IP |
| `verify_cortex_hash.py` | Extrae taxonomías de Cortex (hash) |
| `verify_cortex_ip.py` | Extrae taxonomías de Cortex (IP) |
| `verify_misp.py` | Procesa resultados MISP |
| `verify_es.py` | Verifica indexación ES |
| `verify_tenzir.py` | Procesa eventos Tenzir |
| `verify_network.py` | Procesa conexiones Network Watcher |
| `verify_redis.py` | Verifica cache Redis |
| `verify_loki.py` | Procesa logs Loki |
| `build_es_json.py` | Construye documento ES para alerta |
| `calc_decision.py` | **Núcleo**: calcula score y verdict |
| `containment.py` | Contención vía Lab API (`POST /api/v1/contain`) |
| `mark_false_positive.py` | Marca caso como FP en TheHive |
| `update_inprogress.py` | Confirma caso permanece Open (sin PATCH) |
| `notify_critical.py` | Notificación crítica (email) |
| `notify_info.py` | Notificación informativa (email) |
| `calc_mttr.py` | Calcula MTTR total |
| `build_hive_summary.py` | Construye resumen ejecutivo |
| `build_metrics_json.py` | Construye documento de métricas |

---

## B.7. Idempotencia

El workflow está diseñado para ser idempotente:

- **TheHive**: usa `thehive_create_case_idempotent.py` que busca casos existentes
  por `alert_id` antes de crear uno nuevo
- **Elasticsearch**: usa `alert_id` como `_doc` ID en `soar-alerts` y `soar-metrics`,
  evitando duplicados en reintentos
- **Cortex**: los jobs no son idempotentes nativamente (cada `POST /api/analyzer/{id}/run`
  crea un job nuevo). Los scripts `verify_cortex_*.py` toleran re-ejecuciones procesando
  solo el job más reciente y manejando errores gracefully
- **MISP**: el evento se crea con `info: "SOAR alert {alert_id}"`, permitiendo
  búsqueda previa antes de crear

---

## B.8. Resultados Experimentales del Workflow

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
