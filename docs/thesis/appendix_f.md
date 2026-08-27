# Anexo F: Diagramas de Arquitectura y Flujos (Mermaid)

Referencia TFM: complementa el Capítulo 4 (Desarrollo específico) y el Capítulo 2 (Estado del arte),
y Anexo B (Playbook SOAR). Estos diagramas son la versión canónica extraída de
`docs/02-architecture.md`, `docs/04-operations.md`, `docs/06-project-management.md`
y `README.md`. Los diagramas de `specific_development.md` son versiones simplificadas;
los de este anexo son los completos.

---

## F.1. Arquitectura de Alto Nivel

Diagrama de componentes principales y flujo de datos del sistema SOAR.

```mermaid
flowchart LR
  SIEM[(SIEM simulado)] -- Webhook/Feeder --> Shuffle
  Shuffle -- API --> TheHive
  TheHive -- Observables --> Cortex
  Cortex -- Analyzers --> TI[(Threat Intel)]
  Shuffle -- Contención Lab API --> API[Lab API /api/v1/contain]
  TheHive <--> Elasticsearch
  Cortex <--> Redis
  Shuffle <--> OpenSearch[OpenSearch]
  Shuffle -- Metrics --> Elasticsearch
  Elasticsearch --> Grafana[Grafana]
  Promtail[Promtail] --> Loki[Loki]
  Loki --> Grafana
  Promtail --> Elasticsearch
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
 LabAPI -- HTTP --> OpenSearch[OpenSearch :9200]
 LabAPI -- HTTP --> NetworkWatcher[Network Watcher :8080]
 LabAPI -- HTTP --> Tenzir[Tenzir Node :5160]

 ShuffleBackend -- HTTP --> ES
 ShuffleBackend -- HTTP --> Redis
 ShuffleBackend -- HTTP --> Orborus[Orborus :5000]
 ShuffleBackend -- HTTP --> OpenSearch

 TheHive -- HTTP --> ES
 TheHive -- HTTP --> Cortex

 Cortex -- HTTP --> ES
 Cortex -- HTTP --> MISPInternal

 MISPInternal -- SQL --> MariaDB[MariaDB :3306]

 GrafanaInternal -- HTTP --> ES
 GrafanaInternal -- HTTP --> Loki[Loki :3100]
 GrafanaInternal -- HTTP --> GrafanaDB[(GrafanaDB PostgreSQL)]
 Promtail[Promtail] --> Loki
 GrafanaRenderer[Grafana Renderer :8081] --> GrafanaInternal
 end

 subgraph "Docker network: ti_net"
 MISPInternal
 MISPDB[MISP DB MariaDB :3306]
 MISPModules[MISP Modules :6666]
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
 PORTS[Puertos: AlertRepository<br/>BackupDriver, TokenProvider<br/>SystemMetricsInterface...]
 ALERT[Alert / IOC]
 KPI[KPIAnalyzer]
 IOC[SimulatedIOCGenerator]
 end

 subgraph Salida["Adaptadores de salida"]
 SQLITE[SqliteAlertRepository]
 TAR[TarBackupDriver]
 JWT[JWTTokenProvider]
 HTTP[HTTPClient -> Shuffle/TheHive/Cortex/MISP/ES]
 end

 F -->|/auth/login| AS
 F -->|/backup/create| BS
 F -->|/analytics/kpis| ANS
 C --> AS
 W --> F
 AS -->|TokenProviderInterface| JWT
 BS -->|BackupDriver| TAR
 ANS -->|AlertRepository| SQLITE
 ANS -->|SystemMetricsInterface| HTTP
 KPI -->|StatisticalCalculatorInterface| STAT[StatisticalCalculator]
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
 System_Ext(grafana, "Grafana / Loki", "Observabilidad")

 Rel(operador, soar, "Accede vía navegador", "HTTPS / Web Management")
 Rel(soar, siem, "Recibe alertas o consulta agentes", "HTTP/REST")
 Rel(soar, thehive, "Crea y actualiza casos", "HTTP/REST")
 Rel(soar, cortex, "Ejecuta analyzers", "HTTP/REST")
 Rel(soar, misp, "Enriquece IoCs", "HTTP/REST")
 Rel(soar, shuffle, "Dispara workflows y recibe métricas", "HTTP/REST + WebSocket")
 Rel(soar, es, "Lee / escribe eventos y KPIs", "HTTP/REST")
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
 participant ES as Elasticsearch
 participant API as Lab API

 Sim->>Shuffle: POST /api/v1/hooks/{workflow_id}
 Shuffle->>Backend: Reenvía payload de alerta
 Backend->>TheHive: POST /api/case
 TheHive-->>Backend: caseId
 Backend->>Cortex: POST /api/analyzer/run
 Cortex-->>Backend: resultados (score/veredicto)
 Backend->>MISP: POST /events/add (IoC)
 MISP-->>Backend: eventId
 alt score >= 80 OR verdict == "malicious"
 Backend->>Backend: POST /api/v1/contain (contención Lab API)
 Backend->>TheHive: Case stays Open (no PATCH)
 else score < 80 y verdict != malicious
 Backend->>TheHive: PATCH /api/case (marcar Resolved/FalsePositive)
 end
 Backend->>ES: Indexa métricas KPI (@timestamp, mttr_seconds, ...)
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
 A([Webhook POST /webhook]) --> B[N1: Validar esquema]
 B -->|schema inválido| ERR1([Abort + log error])
 B -->|OK| C[N2: Extraer IoCs]
 C --> D[N3: Crear caso TheHive]
 D -->|API error x3| ERR2([Abort + notificar crítico])
 D -->|OK case_id| E[N4: Adjuntar observables]
 E --> F[N5: Ejecutar analyzers Cortex]
 F --> G{N6: score ≥ 80\no verdict == malicious?}

 G -->|SÍ| H[N7: POST /api/v1/contain<br/>(contención Lab API)]
 H --> I[N8: Case stays Open<br/>(no PATCH)]
 I --> J[N9: Notificación CRITICAL email]
 J --> K[N10: Registrar MTTR + métricas ES]
 K --> Z([FIN — caso contenido])

 G -->|NO| H2[N7b: TheHive -> FalsePositive]
 H2 --> I2[N8b: TheHive -> Resolved]
 I2 --> J2[N9b: Notificación INFO]
 J2 --> K2[N10b: Registrar MTTR + métricas ES]
 K2 --> Z2([FIN — falso positivo resuelto])
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
 Shuffle->>TheHive: Case stays Open (no PATCH)
 Shuffle->>ES: Indexa métricas (soar-metrics)
 else Score < 80 y verdict benigno
 Shuffle->>TheHive: PATCH /api/case (Resolved/FalsePositive)
 end
 Shuffle-->>TheHive: Actualización final del caso
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
 Objetivo 1: Laboratorio desplegado :active, obj1, 2026-04-27, 14d
 Objetivo 7: Seguridad del Entorno :obj7, after obj1, 7d
 Objetivo 8: Automatización configurada :obj8, after obj7, 7d
 Objetivo 17: API del Laboratorio :obj17, after obj8, 7d
 Objetivo 18: CLI del Laboratorio :obj18, after obj17, 5d
 section Fase 2: Diseño
 Objetivo 2: Playbook E2E :obj2, 2026-05-11, 28d
 Objetivo 5: Integración SIEM :obj5, after obj2, 7d
 Objetivo 6: Contención simulada :obj6, after obj5, 7d
 Objetivo 19: Sitio de Documentación :obj19, after obj6, 7d
 Objetivo 20: Interfaz Web de Gestión :obj20, after obj19, 7d
 section Fase 3: Desarrollo
 Objetivo 3: Métricas MTTR :obj3, 2026-06-22, 14d
 Objetivo 9: Pruebas Atómicas :obj9, after obj3, 5d
 Objetivo 10: Pruebas de Integración :obj10, after obj9, 7d
 Objetivo 11: Pruebas de Seguridad :obj11, after obj10, 5d
 Objetivo 12: Pruebas de Rendimiento :obj12, after obj11, 5d
 Objetivo 13: Pruebas de Producción :obj13, after obj12, 3d
 Objetivo 14: KPIs y Análisis :obj14, after obj13, 7d
 section Fase 4: Validación
 Objetivo 4: Documentación técnica :obj4, 2026-08-03, 7d
 Objetivo 15: Preparación defensa TFM :obj15, after obj4, 7d
 Objetivo 16: Evidencia aprobación :obj16, after obj15, 7d
```

Fuente: `docs/06-project-management.md` línea 171

---

## F.9. Roadmap por Semanas (Gantt)

Diagrama Gantt simplificado del roadmap semanal con ruta crítica marcada.

```mermaid
gantt
title Roadmap por Semanas
dateFormat WW
axisFormat "S%V"
section Fases
Fase 1: Investigación :active, f1, 01, 3w
Fase 2: Diseño :crit, f2, after f1, 3w
Fase 3: Desarrollo :crit, f3, after f2, 6w
Fase 4: Validación :crit, f4, after f3, 6w
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
 A[Alta Prob / Alto Impacto] -->|Críticos| R1(Puertos Hyper-V Sí) & R2(Recursos RAM Parcial) & R11(LaLiga/Cloudflare Parcial)
 B[Alta Prob / Bajo Impacto] --> R6(MISP arranque lento Sí)
 C[Media Prob / Alto Impacto] --> R3(Analyzers timeout Parcial) & R4(Integración tokens Parcial) & R7(Umbrales MTTR Parcial) & R12(API no disponible Parcial) & R13(Certificados SSL Parcial) & R16(CI/CD failures Parcial)
 D[Media Prob / Medio Impacto] --> R5(ES compat Sí) & R8(APIs externas Parcial) & R14(Validación esquemas Parcial) & R15(Cobertura pruebas Parcial) & R19(Web-management UX Parcial) & R20(Analytics fallan Parcial)
 E[Baja Prob / Alto Impacto] --> R9(Pérdida config Parcial)
 F[Baja Prob / Medio Impacto] --> R10(Deriva alcance Sí) & R17(CLI inusable Parcial) & R18(Docs-site desactualizado Parcial)
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
 C -->|Ejecución TREZ_cor| D{C2 Check}
 D -->|Pastebin| E[Config Telegram]
 D -->|Dropbox| F[SystemSP.rar pw: zoroz]
 D -->|Reddit| G[IoCs/Dead drop]
 D -->|Telegram| H[Exfiltración]
 F --> I[max.vbs - Persistencia]
 F --> J[babuchen.bat - Killer AV]
 F --> K[rodendron.vbs - GitHub C2]
 F --> L[WinStatChecking.bat - DNS block]
 K --> M[Windows Compatibility Agent.exe]
 M --> N[Pulsar RAT v1.6.6.0]
 N --> O[HVNC, Keylogger, Webcam, Wallet Clipper]
 style A fill:#ff6b6b
 style C fill:#ff6b6b
 style N fill:#ff6b6b
 style O fill:#ff6b6b
```

Fuente: `docs/04-operations.md` línea 4720

---

## F.12. Pipeline SOAR para IoCs de GMinst4ll

Diagrama del pipeline SOAR procesando IoCs reales del caso GMinst4ll a través de
Cortex, MISP, TheHive y Elasticsearch.

```mermaid
graph LR
 A[Webhook Shuffle] --> B[Workflow SOAR]
 B --> C[Cortex: análisis hash/IP]
 B --> D[MISP: búsqueda IoCs]
 B --> E[TheHive: caso + observables]
 B --> F[Elasticsearch: indexación]
 C --> G[Analyzers: Hashdd,<br/>DShield, Mnemonic pDNS,<br/>IP-API, GoogleDNS]
 D --> H[Correlación amenazas]
 E --> I[Tareas IR: contener, notificar, preservar]
 style A fill:#2196F3
 style E fill:#4CAF50
 style I fill:#ff6b6b
```

Fuente: `docs/04-operations.md` línea 4807

