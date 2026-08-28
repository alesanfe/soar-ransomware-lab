# Anexo F: Diagramas de Arquitectura y Flujos (Mermaid)

Referencia TFM: complementa el Capítulo 4 (Desarrollo específico) y el Capítulo 2 (Estado del arte),
y Anexo B (Playbook SOAR). Estos diagramas son la versión canónica extraída de
`docs/02-architecture.md`, `docs/04-operations.md`, `docs/06-project-management.md`
y `README.md`. Los diagramas de `specific_development.md` son versiones simplificadas;
los de este anexo son los completos.

---

## F.1. Arquitectura de Alto Nivel

Diagrama de componentes principales y flujo de datos del sistema SOAR. Muestra
13 de los 23 contenedores Docker con acciones de negocio (Shuffle, TheHive,
Cortex, MISP, Lab API, Redis, Network Watcher, Tenzir, Elasticsearch,
OpenSearch, Loki, Promtail, Grafana) más el simulador SIEM (script Python, no
contenedor) y TI (sistemas externos). Los 10 contenedores restantes (Orborus,
Shuffle UI, Nginx, Web Management, Docs Site, GrafanaDB, Grafana Renderer,
MISP DB, MISP Modules, OpenSearch Dashboards) son internos o UI y se omiten
en esta vista de alto nivel; aparecen en el diagrama de despliegue F.2.

```mermaid
flowchart LR
  SIEM[(SIEM simulado)] -- Webhook/Feeder --> Shuffle
  Shuffle -- API --> TheHive
  TheHive -- Observables --> Cortex
  Cortex -- Analyzers --> TI[(Threat Intel)]
  Shuffle -- Eventos/IoCs --> MISP[(MISP)]
  Shuffle -- Contención + cache --> API[Lab API /api/v1/contain]
  API -- cache IoCs --> Redis[(Redis)]
  Shuffle -- Conexiones --> NW[Network Watcher]
  Shuffle -- Tráfico red --> Tenzir[Tenzir Node]
  TheHive <--> Elasticsearch
  Shuffle <--> OpenSearch[OpenSearch]
  Shuffle -- Metrics --> Elasticsearch
  Shuffle -- Log search --> Loki[Loki]
  Promtail[Promtail] --> Loki
  Loki --> Grafana[Grafana]
  Elasticsearch --> Grafana
  Grafana --> Elasticsearch
```

Fuente: `README.md` línea 51

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
 end

 subgraph "Docker network: soar_net"
 LabAPI -- HTTP --> ShuffleBackend[Shuffle Backend :5001]
 LabAPI -- HTTP --> TheHive[TheHive :9000]
 LabAPI -- HTTP --> Cortex[Cortex :9001]
 LabAPI -- HTTP --> ES[Elasticsearch :9200]
 LabAPI -- HTTP --> Redis[Redis :6379]
 LabAPI -- HTTP --> MISPInternal[MISP :80]
 LabAPI -- HTTP --> GrafanaInternal[Grafana :3000]

 ShuffleBackend -- HTTP --> ES
 ShuffleBackend -- HTTP --> Redis
 ShuffleBackend -- HTTP --> Orborus[Orborus :5000]
 ShuffleBackend -- HTTP --> OpenSearch
 ShuffleBackend -- HTTP --> MISPInternal
 ShuffleBackend -- HTTP --> NetworkWatcher[Network Watcher :8080]
 ShuffleBackend -- HTTP --> Tenzir[Tenzir Node :5160]
 ShuffleBackend -- HTTP --> Loki[Loki :3100]

 TheHive -- HTTP --> ES
 TheHive -- HTTP --> Cortex

 Cortex -- HTTP --> ES

 MISPInternal -- SQL --> MariaDB[MariaDB :3306]
 MISPInternal -- HTTP --> MISPModules[MISP Modules :6666]

 OpenSearch -- HTTP --> OSDashboards[OpenSearch Dashboards :5601]

 GrafanaInternal -- HTTP --> ES
 GrafanaInternal -- HTTP --> Loki
 GrafanaInternal -- HTTP --> GrafanaDB[(GrafanaDB PostgreSQL)]
 Promtail[Promtail] --> Loki
 GrafanaRenderer[Grafana Renderer :8081] --> GrafanaInternal
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
 GrafanaRenderer
 GrafanaDB
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
 F[FastAPI routes<br/>src/soar_lab/interfaces/api/main.py]
 C[CLI soar-lab<br/>src/soar_lab/interfaces/api/cli.py]
 W[Web Management SPA<br/>apps/web-management/]
 end

 subgraph Aplicacion["Capa de aplicación"]
 AS[AuthService]
 BS[BackupService]
 ANS[AnalyticsService]
 end

 subgraph Dominio["Capa de dominio"]
 PORTS[Puertos: AlertRepository<br/>BackupDriver, TokenProviderInterface<br/>SystemMetricsInterface<br/>StatisticalCalculatorInterface...]
 ALERT[AlertGenerator]
 KPI[KPIAnalyzer]
 IOC[SimulatedIOCGenerator]
 end

 subgraph Salida["Adaptadores de salida"]
 SQLITE[SqliteAlertRepository]
 TAR[TarBackupDriver]
 JWT[JWTTokenProvider]
 HTTP[HTTPClient -> Shuffle/TheHive/Cortex/MISP/ES]
 SMETRICS[SystemMetricsDriver]
 STAT[StatisticalCalculator]
 end

 F -->|/auth/login| AS
 F -->|/backup/create| BS
 F -->|/analytics/kpis| ANS
 C -->|generate-iocs| IOC
 W --> F
 AS -->|TokenProviderInterface| JWT
 BS -->|BackupDriver| TAR
 ANS -->|AlertRepository| SQLITE
 ANS -->|SystemMetricsInterface| SMETRICS
 ANS -->|StatisticalCalculatorInterface| STAT
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
 System_Ext(redis, "Redis", "Caché de IoCs")
 System_Ext(grafana, "Grafana / Loki", "Observabilidad")

 Rel(operador, soar, "Accede vía navegador", "HTTPS / Web Management")
 Rel(siem, soar, "Envía alertas de ransomware", "HTTP/REST")
 Rel(soar, thehive, "Crea y actualiza casos", "HTTP/REST")
 Rel(soar, cortex, "Ejecuta analyzers", "HTTP/REST")
 Rel(soar, misp, "Enriquece IoCs", "HTTP/REST")
 Rel(soar, shuffle, "Dispara workflows y responde a contención", "HTTP/REST")
 Rel(shuffle, soar, "Contención + caché IoCs", "HTTP/REST")
 Rel(soar, es, "Lee / escribe eventos y KPIs", "HTTP/REST")
 Rel(soar, redis, "Caché IoCs", "RESP")
 Rel(operador, grafana, "Consulta dashboards", "HTTPS")
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
 Backend->>Backend: normalize_inputs + build_case_json
 Backend->>TheHive: POST /api/case
 TheHive-->>Backend: caseId
 par En paralelo
   Backend->>TheHive: POST observables (hash, IP)
   Backend->>TheHive: POST task (tareas IR)
   Backend->>Cortex: POST /api/analyzer/{id}/run (hash)
   Backend->>Cortex: POST /api/analyzer/{id}/run (IP)
   Backend->>MISP: POST /events (crear evento)
   Backend->>MISP: POST /attributes/restSearch (buscar IoCs)
   Backend->>NW: GET /api/connections?ip={src_ip}
   Backend->>Tenzir: POST /api/v0/pipeline/create
   Backend->>API: POST /api/v1/cache/ioc (caché Redis)
   API->>Redis: SET ioc:{hash} {alert_id} TTL 3600
   Backend->>Loki: GET /loki/api/v1/query_range
   Backend->>ES: POST /soar-alerts/_doc/{alert_id}
 end
 Backend->>Backend: calc_decision (score + verdict)
 alt score >= 80 OR verdict == "malicious"
   Backend->>API: POST /api/v1/contain (contención)
   API-->>Backend: Contención confirmada
   Backend->>TheHive: Case stays Open (no PATCH)
   Backend->>Backend: notify_critical (email)
 else score < 80 y verdict != malicious
   Backend->>TheHive: PATCH /api/case (Resolved/FalsePositive)
   Backend->>Backend: notify_info (email)
 end
 Backend->>Backend: calc_mttr + build_hive_summary
 Backend->>TheHive: PATCH /api/case (enrich: summary + tags)
 Backend->>ES: POST /soar-metrics/_doc/{alert_id} (mttr_seconds, ...)
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
 A([Webhook POST /webhook_{trigger_id}]) --> B[N1: normalize_inputs<br/>validar esquema + extraer IoCs]
 B -->|schema inválido| ERR1([Abort + log error])
 B -->|OK| B2[N1b: build_case_json]
 B2 --> D[N2: Crear caso TheHive<br/>POST /api/case]
 D -->|API error| ERR2([Abort + notificar crítico])
 D -->|OK case_id| E[N3: Adjuntar observables<br/>hash + IP + task IR]
 D --> F[N4: Ejecutar analyzers Cortex<br/>hash + IP + dinámicos]
 D --> G[N5: MISP crear evento + buscar IoCs]
 D --> H[N6: ES indexar alerta<br/>POST /soar-alerts]
 D --> I[N7: Network Watcher + Tenzir + Loki + Redis]

 F --> J{N8: calc_decision<br/>score ≥ 80 o verdict == malicious?}
 G --> J
 H --> J
 I --> J

 J -->|SÍ| K[N9: POST /api/v1/contain<br/>(contención Lab API)]
 K --> L[N10: Case stays Open<br/>(no PATCH)]
 L --> M[N11: Notificación CRITICAL email]
 M --> N[N12: calc_mttr + build_summary]
 N --> O[N13: enrich_case<br/>PATCH /api/case summary+tags]
 O --> P[N14: Indexar métricas ES<br/>POST /soar-metrics]
 P --> Z([FIN — caso contenido])

 J -->|NO| K2[N9b: mark_false_positive<br/>PATCH Resolved/FalsePositive]
 K2 --> L2[N10b: Notificación INFO]
 L2 --> N
```

Fuente: `docs/04-operations.md` línea 4302

---

## F.7. Respuesta Automatizada (Sequence Diagram)

Diagrama de secuencia de la respuesta automatizada con lógica de contención basada en
score y verdict de Cortex.

```mermaid
sequenceDiagram
 participant Shuffle as Shuffle Orborus
 participant TheHive as TheHive
 participant Cortex as Cortex
 participant API as Lab API (/api/v1/contain)
 participant ES as Elasticsearch

 Shuffle->>TheHive: Consulta caso y observables
 TheHive-->>Shuffle: Datos del caso
 Shuffle->>Cortex: Ejecuta analyzers en IoCs
 Cortex-->>Shuffle: Resultados (score, verdict)
 alt Score ≥ 80 o verdict malicioso
 Shuffle->>API: POST /api/v1/contain (Lab API)
 API-->>Shuffle: Contención confirmada
 Shuffle->>Shuffle: update_inprogress (case stays Open)
 Shuffle->>Shuffle: notify_critical (email CRITICAL)
 else Score < 80 y verdict benigno
 Shuffle->>TheHive: PATCH /api/case (Resolved/FalsePositive)
 Shuffle->>Shuffle: notify_info (email INFO)
 end
 Shuffle->>Shuffle: calc_mttr + build_hive_summary
 Shuffle->>TheHive: PATCH /api/case (enrich: summary + tags)
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
 section Fase 1: Investigación
 Objetivo 1: Laboratorio desplegado :active, obj1, 2026-04-27, 7d
 Objetivo 7: Seguridad del Entorno :obj7, after obj1, 4d
 Objetivo 8: Automatización configurada :obj8, after obj7, 4d
 Objetivo 17: API del Laboratorio :obj17, after obj8, 3d
 Objetivo 18: CLI del Laboratorio :obj18, after obj17, 3d
 section Fase 2: Diseño
 Objetivo 2: Playbook E2E :obj2, 2026-05-18, 7d
 Objetivo 5: Integración SIEM :obj5, after obj2, 4d
 Objetivo 6: Contención simulada :obj6, after obj5, 4d
 Objetivo 19: Sitio de Documentación :obj19, after obj6, 3d
 Objetivo 20: Interfaz Web de Gestión :obj20, after obj19, 3d
 section Fase 3: Desarrollo
 Objetivo 3: Métricas MTTR :obj3, 2026-06-08, 7d
 Objetivo 9: Pruebas Atómicas :obj9, after obj3, 5d
 Objetivo 10: Pruebas de Integración :obj10, after obj9, 7d
 Objetivo 11: Pruebas de Seguridad :obj11, after obj10, 5d
 Objetivo 12: Pruebas de Rendimiento :obj12, after obj11, 5d
 Objetivo 13: Pruebas de Producción :obj13, after obj12, 5d
 Objetivo 14: KPIs y Análisis :obj14, after obj13, 8d
 section Fase 4: Validación
 Objetivo 4: Documentación técnica :obj4, 2026-07-20, 14d
 Objetivo 15: Preparación defensa TFM :obj15, after obj4, 14d
 Objetivo 16: Evidencia aprobación :obj16, after obj15, 14d
```

Fuente: `docs/06-project-management.md` línea 171

---

## F.9. Roadmap por Semanas (Gantt)

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

Fuente: `docs/06-project-management.md` línea 861

---

## F.10. Matriz de Priorización de Riesgos

Diagrama de la matriz de riesgos del proyecto, clasificados por probabilidad e impacto.

```mermaid
graph TD
 A[Alta Prob / Alto Impacto] -->|Críticos| R1(Puertos Hyper-V Sí) & R2(Recursos RAM Parcial) & R11(LaLiga/Cloudflare Parcial) & R18(Docs desincronizada Parcial) & R21(Credenciales estáticas Sí)
 B[Alta Prob / Bajo Impacto] --> R6(MISP arranque lento Sí)
 C[Media Prob / Alto Impacto] --> R3(Analyzers timeout Parcial) & R4(Integración tokens Parcial) & R7(Umbrales MTTR Parcial) & R12(API no disponible Parcial) & R13(Certificados SSL Parcial) & R16(CI/CD failures Parcial) & R22(Seguridad ES/OS Parcial) & R24(Network Watcher Parcial)
 D[Media Prob / Medio Impacto] --> R5(ES compat Sí) & R8(APIs externas Parcial) & R14(Validación esquemas Parcial) & R15(Cobertura pruebas Parcial) & R19(Web-management UX Parcial) & R23(Mappings métricas Sí)
 E[Baja Prob / Alto Impacto] --> R9(Pérdida config Parcial)
 F[Baja Prob / Medio Impacto] --> R10(Deriva alcance Sí) & R17(CLI inusable Parcial) & R20(Analytics fallan Parcial)
```

Leyenda: Sí Mitigado · Parcial En seguimiento

Fuente: `docs/06-project-management.md` línea 1390

---

## F.11. Caso de Estudio: GMinst4ll (Flujo de Infección)

Diagrama del flujo completo de infección del malware GMinst4ll, desde la distribución
hasta el despliegue del RAT, usado como caso de estudio real para validar el laboratorio.

```mermaid
graph TD
 A[YouTube/Tumblr] -->|Engaño| B[MediaFire]
 B -->|Descarga RAR pw: 4204| C[GMinst4ll 2.03.rar]
 C -->|Ejecución| D[TREZ_cor 4.52.3.exe]
 D -->|C2 Check| E{C2 Check}
 E -->|Pastebin| F[Configuración dinámica]
 E -->|Dropbox| G[SystemSP.rar pw: zoroz]
 E -->|Reddit| H[IoCs/Dead drop]
 E -->|Telegram| I[Exfiltración]
 G --> J[4 Scripts VBS/BAT]
 J --> K[max.vbs - Persistencia]
 J --> L[babuchen.bat - Killer AV]
 J --> M[rodendron.vbs - GitHub C2]
 J --> N[WinStatChecking.bat - DNS block]
 M -->|github.com/boycots563/wlt56| O[Windows Compatibility Agent.exe]
 O --> P[Pulsar RAT v1.6.6.0]
 P --> Q[HVNC, Keylogger, Webcam, Wallet Clipper]
 style A fill:#ff6b6b
 style C fill:#ff6b6b
 style D fill:#ff6b6b
 style P fill:#ff6b6b
 style Q fill:#ff6b6b
```

Fuente: `docs/04-operations.md` línea 4720

---

## F.12. Pipeline SOAR para IoCs de GMinst4ll

Diagrama del pipeline SOAR procesando IoCs reales del caso GMinst4ll a través de
Cortex, MISP, TheHive y Elasticsearch.

```mermaid
graph LR
 A[Webhook Shuffle] --> B[Workflow SOAR]
 B --> C[Cortex: análisis hash/IP/domain]
 B --> D[MISP: búsqueda IoCs]
 B --> E[TheHive: caso + observables]
 B --> F[Elasticsearch: indexación]
 C --> G[Analyzers: Hashdd,<br/>DShield, Mnemonic pDNS,<br/>IP-API, GoogleDNS]
 D --> H[Correlación amenazas]
 E --> I[Tareas IR: aislar, investigar, preservar]
 style A fill:#2196F3
 style E fill:#4CAF50
 style I fill:#ff6b6b
```

Fuente: `docs/04-operations.md` línea 4807

