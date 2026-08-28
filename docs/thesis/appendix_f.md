# Anexo F: Diagramas de Arquitectura y Flujos (Mermaid)

Referencia TFM: complementa el Capítulo 4 (Desarrollo específico) y el Capítulo 2 (Estado del arte),
y Anexo B (Playbook SOAR). Estos diagramas son la versión canónica extraída de
`docs/02-architecture.md`, `docs/04-operations.md`, `docs/06-project-management.md`
y `README.md`. Los diagramas de `specific_development.md` son versiones simplificadas;
los de este anexo son los completos.

---

## F.1. Arquitectura de Alto Nivel

Diagrama de componentes principales y flujo de datos del sistema SOAR. Muestra
los 23 contenedores Docker del laboratorio más el simulador SIEM (script Python,
no contenedor) y TI (sistemas externos).

```mermaid
flowchart LR
  SIEM[(SIEM simulado)] -- Webhook/Feeder --> ShuffleBE[Shuffle Backend]
  ShuffleBE -- API --> TheHive
  TheHive -- Observables --> Cortex
  Cortex -- Analyzers --> TI[(Threat Intel)]
  ShuffleBE -- Eventos/IoCs --> MISP
  ShuffleBE -- Contención + cache --> API[Lab API]
  API -- cache IoCs --> Redis[(Redis)]
  ShuffleBE -- Conexiones --> NW[Network Watcher]
  ShuffleBE -- Tráfico red --> Tenzir[Tenzir Node]
  TheHive <--> ES[Elasticsearch]
  ShuffleBE <--> OS[OpenSearch]
  API -- Metrics --> ES
  ShuffleBE -- Log search --> Loki[Loki]
  Promtail[Promtail] --> Loki
  Loki --> Grafana[Grafana]
  ES --> Grafana
  Grafana --> ES
  Grafana --> GrafanaDB[(GrafanaDB)]
  GrafanaRenderer[Grafana Renderer] --> Grafana
  ShuffleFE[Shuffle Frontend] --> ShuffleBE
  Orborus[Orborus] --> ShuffleBE
  ShuffleBE --> OS
  OSDashboards[OpenSearch Dashboards] --> OS
  MISP --> MISPDB[(MISP DB MariaDB)]
  MISP --> MISPModules[MISP Modules]
  Nginx[Nginx] --> API
  Nginx --> WebMgmt[Web Management]
  Nginx --> TheHive
  Nginx --> Cortex
  Nginx --> ShuffleBE
  DocsSite[Docs Site] --> Nginx
```

Fuente: `README.md` e `infra/docker/compose/docker-compose*.yml`

---

## F.2. Arquitectura de Despliegue Docker

Diagrama completo de la topología Docker: Nginx proxy, redes (soar_net, ti_net,
logging_net) y conexiones entre los 23 servicios.

```mermaid
graph TD
 subgraph "Acceso recomendado (soar.local 443 / Nginx)"
 User -->|https://soar.local| Nginx
 Nginx -->|/| WebMgmt[Web Management]
 Nginx -->|/api/| LabAPI[Lab API]
 Nginx -->|/thehive/| TheHive
 Nginx -->|/cortex/| Cortex
 Nginx -->|/shuffle-api/| ShuffleBackend
 end

 subgraph "Acceso directo (solo diagnóstico)"
 ShuffleUI[Shuffle UI :8081]
 MISP[MISP :8083]
 Grafana[Grafana :8084]
 DocsSite[Docs Site :8086]
 OSDashboards[OpenSearch Dashboards :5602]
 end

 subgraph "Docker network: soar_net"
 LabAPI -- HTTP --> ShuffleBackend[Shuffle Backend :5001]
 LabAPI -- HTTP --> TheHive[TheHive :9000]
 LabAPI -- HTTP --> Cortex[Cortex :9001]
 LabAPI -- HTTP --> ES[Elasticsearch :9200]
 LabAPI -- HTTP --> Redis[Redis :6379]
 LabAPI -- HTTP --> MISPInternal[MISP :80]
 LabAPI -- HTTP --> GrafanaInternal[Grafana :3000]

 Orborus -- HTTP --> ShuffleBackend
 ShuffleBackend -- HTTP --> OpenSearch
 Orborus -- HTTP --> MISPInternal
 Orborus -- HTTP --> NetworkWatcher[Network Watcher :8080]
 Orborus -- HTTP --> Tenzir[Tenzir Node :5160]
 Orborus -- HTTP --> Loki[Loki :3100]

 TheHive -- HTTP --> ES
 TheHive -- HTTP --> Cortex

 Cortex -- HTTP --> ES

 MISPInternal -- SQL --> MariaDB[MariaDB :3306]
 MISPInternal -- HTTP --> MISPModules[MISP Modules :6666]

 OSDashboards -- HTTP --> OpenSearch

 GrafanaInternal -- HTTP --> ES
 GrafanaInternal -- HTTP --> Loki
 Promtail[Promtail] --> Loki
 end

 subgraph "Docker network: ti_net (internal)"
 ES
 Redis
 LabAPI
 ShuffleBackend
 ShuffleUI
 end

 subgraph "Docker network: logging_net"
 Promtail
 Loki
 GrafanaInternal
 GrafanaRenderer[Grafana Renderer :8081]
 GrafanaDB[(GrafanaDB PostgreSQL)]
 GrafanaRenderer --> GrafanaInternal
 GrafanaInternal -- HTTP --> GrafanaDB
 LabAPI
 Nginx
 end
```

Fuente: `docs/02-architecture.md` línea 169

---

## F.3. Arquitectura Hexagonal (Ports & Adapters)

Diagrama de la arquitectura hexagonal del código Python: capas de dominio, aplicación,
infraestructura e interfaces, con sus puertos y adaptadores.

```mermaid
flowchart TD
 subgraph Entrada["Adaptadores de entrada"]
 F[FastAPI routes<br/>39 endpoints: auth, backup, analytics,<br/>soar proxy, services, tests, ws]
 C[CLI soar-lab<br/>version, api, generate-iocs,<br/>generate-secrets]
 W[Web Management SPA<br/>apps/web-management/]
 end

 subgraph Aplicacion["Capa de aplicación"]
 AS[AuthService]
 BS[BackupService]
 ANS[AnalyticsService]
 AKU[AggregatedKpisUseCase]
 NTU[NodeTimingsUseCase]
 end

 subgraph Dominio["Capa de dominio"]
 PORTS[Puertos: AlertRepository, IocRepository,<br/>BackupDriver, TokenProviderInterface,<br/>SystemMetricsInterface,<br/>StatisticalCalculatorInterface,<br/>SyncHTTPClient, CacheInterface...]
 ALERT[AlertGenerator]
 KPI[KPIAnalyzer]
 IOC[SimulatedIOCGenerator]
 STAT[StatisticalCalculator]
 end

 subgraph Salida["Adaptadores de salida"]
 SQLITE[SqliteAlertRepository]
 TAR[TarBackupDriver]
 JWT[JWTTokenProvider]
 INTEG[Integration Clients<br/>TheHiveClient, CortexClient,<br/>MISPClient, ShuffleClient,<br/>ElasticsearchClient<br/>BaseHTTPClient SyncHTTPClient]
 SMETRICS[SystemMetricsDriver]
 HEALTH[HTTPHealthCheckAdapter<br/>AioHTTPClient]
 CFG[InfrastructureConfigProvider]
 STORAGE[FilesystemStorage<br/>BackupStorageProvider]
 end

 F -->|/auth/login| AS
 F -->|/backup/create| BS
 F -->|/analytics/kpis| ANS
 F -->|/analytics/kpis/aggregated| AKU
 F -->|/analytics/node-timings| NTU
 F -->|/soar/thehive/cases| INTEG
 F -->|/soar/cortex/jobs| INTEG
 F -->|/soar/misp/events| INTEG
 F -->|/api/v1/contain| INTEG
 F -->|/health /services/status| HEALTH
 C -->|generate-iocs| IOC
 W --> F
 AS -->|TokenProviderInterface| JWT
 AS -->|ConfigProvider| CFG
 BS -->|BackupDriver| TAR
 BS -->|BackupStorageProvider| STORAGE
 ANS -->|AlertRepository| SQLITE
 ANS -->|SystemMetricsInterface| SMETRICS
 ANS -->|StatisticalCalculatorInterface| STAT
 ANS -->|KPIAnalyzer| KPI
 KPI -->|StatisticalCalculatorInterface| STAT
```

Fuente: `docs/02-architecture.md` línea 1390

---

## F.4. Diagrama de Contexto C4

Modelo C4 de contexto mostrando los límites del sistema y las integraciones externas.

```mermaid
C4Context
 title Sistema de Contexto - SOAR Ransomware Lab
 Person(operador, "Operador / Analista")
 System(soar, "SOAR Ransomware Lab", "Orquesta detección, análisis y contención simulada de ransomware")
 System_Ext(siem, "SIEM simulado")
 System_Ext(thehive, "TheHive", "Gestión de casos")
 System_Ext(cortex, "Cortex", "Análisis de IoC")
 System_Ext(misp, "MISP", "Inteligencia de amenazas")
 System_Ext(shuffle, "Shuffle", "Workflows SOAR")
 System_Ext(es, "Elasticsearch", "Almacén de eventos y métricas")
 System_Ext(opensearch, "OpenSearch", "Datastore de ejecuciones de Shuffle")
 System_Ext(redis, "Redis", "Caché de IoCs")
 System_Ext(grafana, "Grafana / Loki", "Observabilidad")
 System_Ext(tenzir, "Tenzir", "Análisis de tráfico de red")
 System_Ext(nw, "Network Watcher", "Monitor de conexiones de red")

 Rel(operador, soar, "Accede vía navegador", "HTTPS / Web Management")
 Rel(siem, soar, "Envía alertas de ransomware", "HTTP/REST")
 Rel(soar, thehive, "Crea y actualiza casos", "HTTP/REST")
 Rel(soar, cortex, "Ejecuta analyzers", "HTTP/REST")
 Rel(soar, misp, "Enriquece IoCs", "HTTP/REST")
 Rel(soar, shuffle, "Dispara workflows y responde a contención", "HTTP/REST")
 Rel(shuffle, soar, "Contención + caché IoCs", "HTTP/REST")
 Rel(soar, es, "Lee / escribe eventos y KPIs", "HTTP/REST")
 Rel(shuffle, opensearch, "Almacena ejecuciones de workflows", "HTTP/REST")
 Rel(soar, redis, "Caché IoCs", "RESP")
 Rel(soar, tenzir, "Analiza tráfico de red", "HTTP/REST")
 Rel(soar, nw, "Consulta conexiones de red", "HTTP/REST")
 Rel(operador, grafana, "Consulta dashboards", "HTTP")
```

Fuente: `docs/04-operations.md` línea 1296

---

## F.5. Flujo End-to-End de Alertas (Sequence Diagram)

Diagrama de secuencia completo del flujo de una alerta desde el simulador SIEM hasta
la indexación de métricas en Elasticsearch, pasando por Shuffle, TheHive, Cortex y MISP.

```mermaid
sequenceDiagram
 participant Sim as Simulador SIEM
 participant Shuffle as Shuffle webhook
 participant Backend as Shuffle backend
 participant TheHive as TheHive
 participant Cortex as Cortex
 participant MISP as MISP
 participant NW as Network Watcher
 participant Tenzir as Tenzir Node
 participant Loki as Loki
 participant API as Lab API
 participant Redis as Redis
 participant ES as Elasticsearch

 Sim->>Shuffle: POST /api/v1/hooks/webhook_{trigger_id}
 Shuffle->>Backend: Reenvía payload de alerta
 Backend->>Backend: normalize_inputs
 Backend->>Backend: build_case_json
 Backend->>TheHive: POST /api/case
 TheHive-->>Backend: caseId
 par En paralelo (16 ramas desde case creation)
   Backend->>TheHive: POST observables (hash, IP)
   Backend->>Backend: calc_task_title (severity >= 3 aislar)
   Backend->>TheHive: POST task (titulo IR)
   Backend->>Cortex: POST /api/analyzer/{id}/run (hash: Hashdd, VirusShare)
   Backend->>Cortex: POST /api/analyzer/{id}/run (IP: DShield, Mnemonic pDNS, IP-API, GoogleDNS)
   Backend->>MISP: POST /events (crear evento)
   Backend->>MISP: POST /attributes/restSearch (buscar hash)
   Backend->>NW: GET /api/connections?ip={src_ip}&limit=50
   Backend->>Tenzir: POST /api/v0/pipeline/create
   Backend->>Tenzir: POST /api/v0/serve (publicar resultados)
   Backend->>API: POST /api/v1/cache/ioc (caché Redis)
   API->>Redis: SET ioc:{hash} {alert_id} TTL 3600
   Backend->>Loki: GET /loki/api/v1/query_range
   Backend->>Backend: build_es_json
   Backend->>ES: POST /soar-alerts/_doc/{alert_id}
 end
 Note over Backend: 11 nodos verify_* validan cada rama<br/>antes de calc_decision
 Backend->>Backend: calc_decision (score + verdict)
 Note over Backend: Shuffle no soporta alt nativo ambas ramas se ejecutan<br/>y los scripts Python deciden segun decision
 alt score >= 80 OR verdict == "malicious"
   Backend->>API: POST /api/v1/contain (contención simulada)
   API-->>Backend: Contención confirmada (modo simulation)
   Backend->>Backend: update_inprogress (case stays Open, no PATCH)
   Backend->>Backend: notify_critical (email CRITICAL)
 else score < 80 y verdict != malicious
   Backend->>TheHive: PATCH /api/case (Resolved/FalsePositive)
   Backend->>Backend: notify_info (email INFO)
 end
 Backend->>Backend: calc_mttr
 Backend->>Backend: build_hive_summary
 Backend->>TheHive: PATCH /api/case (enrich: summary + tags)
 Backend->>Backend: build_metrics_json (mttr_seconds, score, verdict)
 Backend->>ES: POST /soar-metrics/_doc/{alert_id} (mttr_seconds, ...)
 Note over API: Post-workflow: operador consulta resultados via Lab API
 API->>ES: GET /analytics/kpis/aggregated
 API->>TheHive: GET /soar/thehive/cases
 API->>Cortex: GET /soar/cortex/jobs
 API->>MISP: GET /soar/misp/events
```

Fuente: `docs/04-operations.md` línea 1380

---

## F.6. Árbol de Decisión del Playbook

Flowchart del playbook SOAR mostrando la lógica de decisión: validación, creación de caso,
análisis con Cortex, y branching entre contención (malicioso) y falso positivo (benigno).

```mermaid
flowchart TD
 A(["Webhook POST /webhook_{trigger_id}"]) --> B["N1: normalize_inputs<br/>validar severity + extraer IoCs<br/>+ DNS warmup"]
 B -->|fallo| ERR1([Workflow aborta])
 B -->|OK| B2[N1b: build_case_json]
 B2 --> D[N2: Crear caso TheHive<br/>POST /api/case]
 D -->|fallo| ERR2([Workflow aborta])
 D -->|OK case_id| E[N3: Adjuntar observables<br/>hash + IP]
 D --> E2[N3b: calc_task_title<br/>severity >= 3 aislar<br/>severity < 3 investigar]
 E2 --> E3[N3c: POST task IR<br/>titulo calculado]
 D --> F[N4: Ejecutar analyzers Cortex<br/>hash Hashdd + VirusShare<br/>IP DShield + Mnemonic pDNS<br/>+ IP-API + GoogleDNS]
 D --> G[N5: MISP crear evento<br/>+ buscar hash]
 D --> H[N6: build_es_json + ES indexar<br/>POST /soar-alerts]
 D --> I[N7: Network Watcher + Tenzir<br/>pipeline/create + serve<br/>+ Loki + Redis]

 E --> J{N8: calc_decision<br/>score >= 80 o verdict == malicious?}
 E3 --> J
 F --> J
 G --> J
 H --> J
 I --> J

 J -->|SÍ| K["N9: POST /api/v1/contain<br/>(contención simulada Lab API)"]
 K --> L["N10: update_inprogress<br/>case stays Open sin PATCH"]
 L --> M[N11: Notificación CRITICAL email]
 M --> N[N12: calc_mttr]
 N --> N2[N12b: build_hive_summary]
 N2 --> O[N13: enrich_case<br/>PATCH /api/case summary+tags]
 O --> P[N14: build_metrics_json + Indexar ES<br/>POST /soar-metrics]
 P --> Z([FIN — caso contenido])

 J -->|NO| K2[N9b: mark_false_positive<br/>PATCH Resolved/FalsePositive]
 K2 --> L2[N10b: Notificación INFO]
 L2 --> N
```

Fuente: `docs/04-operations.md` línea 4302

---

## F.7. Respuesta Automatizada (Sequence Diagram)

Diagrama de secuencia del zoom sobre la rama de decisión del playbook: tras
`calc_decision`, el workflow ejecuta contención (malicioso) o marca falso positivo
(benigno), seguido del enriquecimiento del caso y la indexación de métricas.

```mermaid
sequenceDiagram
 participant Shuffle as Shuffle Orborus
 participant TheHive as TheHive
 participant API as Lab API (/api/v1/contain)
 participant ES as Elasticsearch

 Note over Shuffle: calc_decision ya ejecutado<br/>score y verdict disponibles
 Note over Shuffle: Shuffle no soporta alt nativo ambas ramas se ejecutan<br/>y los scripts Python deciden segun decision
 alt score >= 80 o verdict == malicious
 Shuffle->>API: POST /api/v1/contain (contención simulada)
 API-->>Shuffle: Contención confirmada (modo simulation)
 Shuffle->>Shuffle: update_inprogress (case stays Open, no PATCH)
 Shuffle->>Shuffle: notify_critical (JSON channel=email severity=CRITICAL)
 else score < 80 y verdict != malicious
 Shuffle->>TheHive: PATCH /api/case (status=Resolved, resolutionStatus=FalsePositive)
 Shuffle->>Shuffle: notify_info (JSON channel=email severity=INFO)
 end
 Shuffle->>Shuffle: calc_mttr
 Shuffle->>Shuffle: build_hive_summary (Markdown)
 Shuffle->>TheHive: PATCH /api/case (enrich: description + tags)
 Shuffle->>Shuffle: build_metrics_json (mttr_seconds, score, verdict + 17 campos)
 Shuffle->>ES: POST /soar-metrics/_doc/{alert_id}
```

Fuente: `docs/02-architecture.md` línea 519

---

## F.8. Cronograma de Objetivos SMART (Gantt)

Diagrama Gantt del cronograma de los 20 objetivos SMART distribuidos en 4 fases
(planificación inicial 12 semanas, aumentada a 15 tras diseño, ejecución real 18 semanas,
27 abr - 31 ago 2026).

```mermaid
gantt
 title Cronograma de Objetivos SMART - SOAR Ransomware Lab
 dateFormat YYYY-MM-DD
 section Fase 1 - Investigación
 Objetivo 1 - Laboratorio desplegado :active, obj1, 2026-04-27, 7d
 Objetivo 7 - Seguridad del Entorno :obj7, after obj1, 4d
 Objetivo 8 - Automatización configurada :obj8, after obj7, 4d
 Objetivo 17 - API del Laboratorio :obj17, after obj8, 3d
 Objetivo 18 - CLI del Laboratorio :obj18, after obj17, 3d
 section Fase 2 - Diseño
 Objetivo 2 - Playbook E2E :obj2, 2026-05-18, 7d
 Objetivo 5 - Integración SIEM :obj5, after obj2, 4d
 Objetivo 6 - Contención simulada :obj6, after obj5, 4d
 Objetivo 19 - Sitio de Documentación :obj19, after obj6, 3d
 Objetivo 20 - Interfaz Web de Gestión :obj20, after obj19, 3d
 section Fase 3 - Desarrollo
 Objetivo 3 - Métricas MTTR :obj3, 2026-06-08, 7d
 Objetivo 9 - Pruebas Atómicas :obj9, after obj3, 5d
 Objetivo 10 - Pruebas de Integración :obj10, after obj9, 7d
 Objetivo 11 - Pruebas de Seguridad :obj11, after obj10, 5d
 Objetivo 12 - Pruebas de Rendimiento :obj12, after obj11, 5d
 Objetivo 13 - Pruebas de Producción :obj13, after obj12, 5d
 Objetivo 14 - KPIs y Análisis :obj14, after obj13, 8d
 section Fase 4 - Validación
 Objetivo 4 - Documentación técnica :obj4, 2026-07-20, 14d
 Objetivo 15 - Preparación defensa TFM :obj15, after obj4, 14d
 Objetivo 16 - Evidencia aprobación :obj16, after obj15, 14d
```

Fuente: `docs/thesis/objectives_and_methodology.md` líneas 86-116 (cronograma 18 semanas 2026), `docs/06-project-management.md` líneas 171-203 (objetivos SMART)

---

## F.9. Roadmap Semanal (Gantt)

Diagrama Gantt simplificado del roadmap semanal con ruta crítica marcada.

```mermaid
gantt
title Roadmap por Semanas - SOAR Ransomware Lab
dateFormat YYYY-MM-DD
axisFormat %d/%m
section Inicio
Inicio del proyecto :milestone, m1, 2026-04-27, 0d
section Fase 1: Investigación
Literatura y requisitos :active, a1, 2026-04-27, 3w
section Fase 2: Diseño
Arquitectura y contratos :a2, after a1, 3w
section Fase 3: Desarrollo
Playbook, integraciones y API :crit, a3, after a2, 6w
Versión funcional :milestone, m2, after a3, 0d
section Fase 4: Validación
Pruebas E2E :a4, after a3, 2w
Experimentos :a5, after a4, 3w
Análisis estadístico :a6, after a5, 1w
Cierre del proyecto :milestone, m3, after a6, 0d
```

Nota: La planificación inicial era de 12 semanas, aumentada a 15 tras
la fase de diseño (integración de Cortex con analyzers externos y stack de
monitoreo no contemplados inicialmente). La ejecución real se extendió a
18 semanas (27 abr - 31 ago 2026, 3+3+6+6) debido a la ampliación de la
suite de tests (2233 tests coleccionados, 1905 seleccionados) y la ejecución del experimento (n=50).
Ver `objectives_and_methodology.md` para el cronograma real.

Fuente: `docs/thesis/objectives_and_methodology.md` líneas 90-116 (Gantt 18 semanas 2026)

---

## F.10. Matriz de Priorización de Riesgos

Diagrama de la matriz de riesgos del proyecto, clasificados por probabilidad e impacto.

```mermaid
flowchart TD
    classDef mitigado fill:#d4edda,stroke:#28a745,color:#155724,stroke-width:2px
    classDef activo fill:#fff3cd,stroke:#ffc107,color:#856404,stroke-width:2px
    classDef critico fill:#f8d7da,stroke:#dc3545,color:#721c24,stroke-width:2px

    subgraph Row1["Alta Probabilidad"]
        direction LR
        subgraph AA["Alto Impacto — CRITICOS (5)"]
            direction TB
            R1["R1: Puertos Hyper-V — Mitigado"]:::mitigado
            R2["R2: Recursos RAM — Activo"]:::critico
            R11["R11: LaLiga/Cloudflare — Activo"]:::critico
            R18["R18: Docs desactualizado — Activo"]:::critico
            R21["R21: Credenciales estaticas — Mitigado"]:::mitigado
        end
        subgraph AB["Bajo Impacto (1)"]
            R6["R6: MISP arranque lento — Conocido"]:::mitigado
        end
    end

    subgraph Row2["Media Probabilidad"]
        direction LR
        subgraph MA["Alto Impacto (8)"]
            direction TB
            R3["R3: Analyzers timeout — Activo"]:::activo
            R4["R4: Integracion tokens — Activo"]:::activo
            R7["R7: Umbrales MTTR — Activo"]:::activo
            R12["R12: API no disponible — Activo"]:::activo
            R13["R13: Certificados SSL — Activo"]:::activo
            R16["R16: CI/CD failures — Activo"]:::activo
            R22["R22: Seguridad ES/OS — Activo"]:::activo
            R24["R24: Network Watcher — Activo"]:::activo
        end
        subgraph MM["Medio Impacto (6)"]
            direction TB
            R5["R5: ES compat — Mitigado"]:::mitigado
            R8["R8: APIs externas — Activo"]:::activo
            R14["R14: Validacion esquemas — Activo"]:::activo
            R15["R15: Cobertura pruebas — Activo"]:::activo
            R19["R19: Web-management UX — Activo"]:::activo
            R23["R23: Mappings metricas — Mitigado"]:::mitigado
        end
    end

    subgraph Row3["Baja Probabilidad"]
        direction LR
        subgraph BA["Alto Impacto (1)"]
            R9["R9: Perdida config — Activo"]:::activo
        end
        subgraph BM["Medio Impacto (3)"]
            direction TB
            R10["R10: Deriva alcance — Mitigado"]:::mitigado
            R17["R17: CLI inusable — Activo"]:::activo
            R20["R20: Analytics fallan — Activo"]:::activo
        end
    end

    Row1 --> Row2 --> Row3
```

Leyenda: Sí Mitigado o Conocido · Parcial En seguimiento / Activo

Fuente: `docs/06-project-management.md` línea 1381 (tabla detallada R1-R24, fuente autoritativa)

---

## F.11. Caso de Estudio: GMinst4ll (Flujo de Infección)

Diagrama del flujo completo de infección del malware **GMinst4ll 2.03.rar** (884 MB,
InfoStealer/Loader), analizado forensemente entre el 11-13 de junio de 2026 en un
sandbox aislado (Ubuntu 20.04 + Windows Server 2016 con Vagrant, red aislada, Sysmon).
El caso de estudio valida el laboratorio SOAR con IoCs reales: 4 hashes SHA256, 7 URLs
C2, 9 IPs, 1 clave de registro, 66 dominios bloqueados y 7 técnicas MITRE ATT&CK.

| Atributo | Valor |
|----------|-------|
| Actor | `boycots563` (GitHub user ID 193230682, 1 repo, 0 stars, 1 watcher) |
| Origen | Eslovaquia (subida a MediaFire 2026-06-10 23:57:07) |
| Repo C2 | `github.com/boycots563/wlt56` — público y activo, 253 commits (ago 2026) |
| Operador Telegram | @KJL4999S (Chat ID 6820575341, bot `buchstys4_bot` ID 7675556882) |
| Sofisticación | RAR anidado, ConfuserEx, servicios legítimos para C2 |


```mermaid
graph TD
 subgraph Distrib["1. Distribucion"]
   A[YouTube/Tumblr/Discord<br/>canal: асьминог] -->|Engaño| B[MediaFire]
 end
 subgraph Payload["2. Payload principal"]
   B -->|RAR pw: 4204| C[GMinst4ll 2.03.rar<br/>884 MB RAR5 anidado]
   C -->|Ejecucion| D[TREZ_cor 4.52.3.exe<br/>835 MB + 13 DLLs motor grafico]
   D --> S[InfoStealer:<br/>Chrome/Edge/Firefox Login Data<br/>Metamask/Trust/Atomic wallets]
 end
 subgraph C2["3. C2 - servicios legitimos abusados"]
   D --> E{C2 Check}
   E -->|Pastebin raw/FgUMQ9vE| F[Config dinamica<br/>Token TG + Chat ID 6820575341]
   E -->|Dropbox| G[SystemSP.rar pw: zoroz<br/>4 KB, 4 scripts]
   E -->|Reddit Over_Media6257| H[Dead drop resolver<br/>403 Forbidden en analisis]
   E -->|Telegram Bot 7675556882| I[Exfiltracion Bot API<br/>sendDocument]
   F -.->|Token + Chat ID| I
 end
 subgraph Persist["4. Persistencia y evasion"]
   G --> J[4 Scripts VBS/BAT]
   J --> K[max.vbs<br/>Launcher/watchdog<br/>Exclusiones Defender]
   J --> L[babuchen.bat<br/>Killer AV<br/>14 srv + 34 suites + WU]
   J --> M[rodendron.vbs<br/>GitHub C2 download<br/>Tarea programada]
   J --> N[WinStatChecking.bat<br/>DNS block<br/>66 dominios + DNS 8.8.8.8]
 end
 subgraph RAT["5. Pulsar RAT v1.6.6.0"]
   M -->|github.com/boycots563/wlt56<br/>253 commits, publico| O[Win Compat Agent.exe<br/>Python 3.13, 12.4 MB]
   O -->|beket.rar contiene| P[appy_patched.exe .NET 4.7.2<br/>ConfuserEx, 1.86 MB]
   P --> Q[Capacidades:<br/>HVNC SharpDX / Keylogger MouseKeyHook v5.7<br/>Webcam AForge / Audio NAudio<br/>Clipboard / Remote desktop<br/>Wallet clipper XMR + 9 inferidas]
   P --> R[Evasion:<br/>25+ checks anti-VM/anti-debug<br/>2 blobs AES-GCM 1808B entropia 7.92<br/>Config C2 NO recuperable]
 end
 style A fill:#ff6b6b
 style C fill:#ff6b6b
 style D fill:#ff6b6b
 style S fill:#ff9800
 style P fill:#ff6b6b
 style Q fill:#ff6b6b
 style R fill:#ff6b6b
 style K fill:#fff3cd
 style L fill:#fff3cd
 style N fill:#fff3cd
 style H fill:#d6d6d6
```

El malware se distribuye mediante engaño social en cuatro plataformas: YouTube (canal
"асьминог", octopus en ruso, vídeo `okNhSxfa__U` reciclado posteriormente para
distribuir "RPG Maker MZ"), Tumblr (`@tutorialsfrommax`, tutoriales falsos de minería),
MediaFire (`GMinstall_4.11.rar`, variante 4.11 vs 2.03) y Discord (`sub4unlock.io/ajLvu`,
trust score 10/100, scam CPA). El ejecutable principal `TREZ_cor 4.52.3.exe` (835 MB)
incluye 13 DLLs de motor gráfico (core_init, physics_core, mesh_processor, renderer,
etc.) y actúa como InfoStealer robando credenciales de navegadores (Chrome, Edge,
Brave, Opera, Firefox — `Login Data` y `logins.json`) y wallets (Metamask, Trust
Wallet, Atomic). Tras el robo de datos, realiza un C2 check contra cuatro servicios
legítimos abusados: Pastebin (configuración dinámica con token Telegram y Chat ID),
Dropbox (payload SystemSP.rar), Reddit (user `Over_Media6257`, dead drop resolver, 403
Forbidden) y Telegram Bot API (exfiltración vía `sendDocument`).

SystemSP.rar (4 KB, contraseña "zoroz") contiene cuatro scripts VBS/BAT para
persistencia y evasión:

| Script | Tipo | Función |
|--------|------|---------|
| `max.vbs` | VBScript | Launcher/watchdog, exclusiones de Windows Defender para `appy.exe` |
| `babuchen.bat` | Batch | Killer AV: detiene 14 servicios, destruye 34 suites, elimina Windows Update |
| `rodendron.vbs` | VBScript | Descarga `Windows Compatibility Agent.exe` desde GitHub C2, tarea programada recurrente |
| `WinStatChecking.bat` | Batch | Bloquea 66 dominios AV en hosts, fuerza DNS a 8.8.8.8 |

El repositorio GitHub C2 (`github.com/boycots563/wlt56`, público y activo, 253 commits
entre octubre 2025 y agosto 2026) contiene nueve archivos:

| Archivo | Tipo | Tamaño | Notas |
|---------|------|--------|-------|
| `Windows Compatibility Agent.exe` | Python 3.13 | 12.4 MB | Imports USER32/KERNEL32/ADVAPI32, packer MachO_File_pyinstaller |
| `Windows Compatibility Agent Host.exe` | Python 3.14 | 8.5 MB | Mismos imports + OpenProcessToken/GetTokenInformation |
| `kamzat.exe` | Python 3.13 | 12.4 MB | PyCryptodome completo (AES, SHA, HMAC, BLAKE2, keccak) + asyncio |
| `postevak.exe` | Python 3.13 | 7.9 MB | HTTP básico, sin criptografía avanzada |
| `appy.exe` | Rust | 719 KB | Launcher, imports ntdll.dll (NtWriteFile, NtCreateNamedPipeFile) |
| `beket.rar` | RAR | — | Contiene `appy_patched.exe` (Pulsar RAT .NET 1.86 MB) |
| `PROMOTIO.BAT` | Batch | — | Actualizado 3-nov-2025 |
| `maximusz.bat` | Batch | — | Actualizado 3 veces el 17-oct-2025 |
| `README.md` | Markdown | — | Disclaimer falso "PoC educativo" añadido 2-ago-2026 |

El patrón de commits revela ciclos repetidos de "Add files via upload" + "Delete
appy.exe"/"Delete kamzat.exe" (oct-nov 2025, dic 2025, abr 2026), indicando rotación de
payloads para evadir detección. Ningún ejecutable Python contiene URLs/IPs directas en
strings — la configuración C2 está probablemente cifrada.



Las hipótesis de atribución indican una campaña activa desde 2025 (múltiples variantes:
versiones 2.03, 4.11, 4.52.3, rotación de payloads en GitHub mediante ciclos
Add/Delete), un operador rusohablante (cirílico "асьминог" en YouTube, nombres temáticos
eslavos: babuchen, rodendron, kamzat, postevak, maximusz) y monetización múltiple (robo
de wallets, venta de credenciales en foros, ingresos por sub4unlock.io CPA).

Fuente: `github.com/alesanfe/gminst4ll-forensics` (README.md, 01_INFORME_PRINCIPAL,
02_BITACORA_FASES, 03_IOCS_Y_DETECCION, 04_OSINT_Y_CAMPANA, 05_PENDIENTES_Y_PLAN,
06_METADATOS_ANALISIS). Estado del repo C2 verificado directamente en
`github.com/boycots563/wlt56` (agosto 2026).

---

## F.12. Pipeline SOAR para IoCs de GMinst4ll

Diagrama del pipeline SOAR procesando IoCs reales extraídos del análisis forense de
GMinst4ll (`github.com/alesanfe/gminst4ll-forensics`) a través de Cortex, MISP, TheHive
y Elasticsearch. Validado con **TC-33** (10 subtests): hashes SHA256 (GMinst4ll, TREZ_cor,
SystemSP, appy_patched), URLs C2 (Pastebin, Dropbox, Reddit, Telegram, GitHub, MediaFire),
dominios (pastebin.com, dropbox.com, reddit.com, telegram.org, github.com, mediafire.com),
IPs (172.66.171.73, 104.20.29.150, 162.125.248.18, 151.101.129.140, 151.101.65.140,
149.154.166.110, 149.154.167.99), Telegram (Bot ID 7675556882, Chat ID 6820575341),
claves de registro (HKLM Winlogon UserInit), MITRE ATT&CK (7 técnicas: T1566.002,
T1059.001, T1547.001, T1562.001, T1056.001, T1102, T1567.002).

```mermaid
graph LR
 A[Webhook Shuffle<br/>TC-33: 10 subtests<br/>IoCs GMinst4ll reales] --> B[Workflow SOAR]
 B --> C[Cortex: analisis hash/IP<br/>Hashdd + VirusShare + DShield<br/>+ Mnemonic pDNS + IP-API + GoogleDNS]
 B --> D[MISP: crear evento hash+IP<br/>+ buscar hash en DB]
 B --> E[TheHive: caso + observables<br/>hash + IP + URL + tarea IR]
 B --> F[Elasticsearch: soar-alerts + soar-metrics]
 B --> M[Network Watcher + Tenzir<br/>+ Loki + Redis]
 C --> G[Resultados: reputation<br/>hash hits + IP geo + PDNS]
 D --> H[Correlacion amenazas<br/>eventos MISP existentes]
 E --> I[Tareas IR: severity >=3 aislar<br/>severity <3 investigar + preservar]
 E --> J{calc_decision<br/>score >= 80 o malicious?}
 G -.->|enriquece score| J
 H -.->|enriquece score| J
 J -->|Si| K[POST /api/v1/contain<br/>modo simulation]
 J -->|No| L[PATCH /api/case<br/>Resolved/FalsePositive]
 K --> N[calc_mttr + build_hive_summary<br/>+ enrich_case + soar-metrics]
 L --> N
 N -.->|indexa| F
 style A fill:#2196F3
 style E fill:#4CAF50
 style I fill:#ff6b6b
 style K fill:#ff6b6b
```

Nota: Para IoCs de GMinst4ll sin enriquecimiento previo de Cortex/MISP, el score
base de `calc_decision` es 60 (severity=3 → +60), veredicto `suspicious`, decisión
`observe`. La contención se activa cuando los analyzers de Cortex (Hashdd/VirusShare
encuentran el hash) o la correlación de MISP (evento existente para la IP) elevan el
score a >=80 o el veredicto a `malicious`. Los IoCs de GMinst4ll son especialmente
valiosos para validación porque incluyen hashes reales con reputation en VirusShare,
IPs de servicios legítimos abusados (Pastebin, Dropbox, Reddit, Telegram) y técnicas
MITRE ATT&CK mapeadas desde análisis estático confirmado.

Los IoCs validados en TC-33 (10 subtests) se distribuyen por tipo como sigue:

| Tipo | Cantidad | Ejemplos |
|------|----------|----------|
| Hashes SHA256 | 4 | GMinst4ll `d70c31b0...`, TREZ_cor `a75def53...`, SystemSP `a50e0785...`, appy_patched `eabe4c16...` |
| URLs C2 | 7 | `pastebin.com/raw/FgUMQ9vE`, `pastebin.com/raw/E3s5iTTz`, `dropbox.com/scl/fi/.../SystemSP.rar`, `reddit.com/user/Over_Media6257/...`, `api.telegram.org/bot7675556882/...`, `github.com/boycots563/wlt56/`, `mediafire.com/.../GMinstall_4.11.rar` |
| Dominios | 6 | pastebin.com, dropbox.com, reddit.com, telegram.org, github.com, mediafire.com |
| IPs | 9 | 172.66.171.73, 104.20.29.150 (Pastebin), 162.125.248.18 (Dropbox), 151.101.129.140, 151.101.65.140, 151.101.193.140, 151.101.1.140 (Reddit), 149.154.166.110, 149.154.167.99 (Telegram) |
| Telegram | 2 | Bot ID 7675556882 (buchstys4_bot), Chat ID 6820575341 |
| Registry | 1 | `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\UserInit` |
| MITRE ATT&CK | 7 | T1566.002, T1059.001, T1547.001, T1562.001, T1056.001, T1102, T1567.002 |

Las consultas SIEM para hunting incluyen `pastebin.com` (o URLs específicas
`/raw/FgUMQ9vE`, `/raw/E3s5iTTz`), `dropbox.com/scl/fi/` (path SystemSP.rar),
`reddit.com/user/Over_Media6257/`, `api.telegram.org/bot7675556882` y
`github.com/boycots563/wlt56/`. Los patrones de proceso a monitorizar son `TREZ_cor`
en línea de comandos, `wscript.exe` ejecutando `.vbs` desde `%PROGRAMDATA%` y PowerShell
con `-Verb RunAs` tras ejecutar archivos sospechosos.

Fuente: `github.com/alesanfe/gminst4ll-forensics` (03_IOCS_Y_DETECCION_GMINST4LL.md —
Apéndice A con origen exacto de cada IoC: archivo fuente + línea). Pipeline SOAR:
`docs/04-operations.md` línea 4807, TC-33: `tests/e2e/TC-33/`.

