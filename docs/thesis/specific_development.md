# 4. Desarrollo específico de la contribución

## 4.1. Desarrollo de software

### 4.1.1. Identificación de requisitos

El problema abordado es la gestión manual de incidentes de ransomware en equipos de respuesta (SOC y CSIRT), donde la fragmentación de herramientas provoca tiempos de respuesta elevados, variabilidad entre analistas y dificultad para generar evidencias trazables. El contexto de uso comprende organizaciones con recursos limitados (pymes, universidades y CSIRTs en formación) que no pueden asumir licencias comerciales de plataformas SOAR propietarias. Los requisitos se han identificado a partir de la literatura revisada en el Capítulo 2, los marcos de referencia (NIST SP 800-61, ISO/IEC 27035, MITRE ATT&CK) y la experiencia en despliegue de laboratorios reproducibles con herramientas open source.

Requisitos Funcionales

Los requisitos funcionales describen las capacidades que el sistema debe ofrecer para cumplir su propósito:

- RF-01: Gestión de alertas. El sistema debe recibir notificaciones de fuentes externas (SIEM, EDR), clasificarlas
  según patrones de ransomware y dirigirlas al playbook correspondiente.
- RF-02: Análisis de indicadores de compromiso (IoCs). Hashes, dominios, IPs y archivos se enriquecen mediante analyzers
  libres de Cortex (sin API key requerida) y se almacenan en Elasticsearch para detectar patrones recurrentes.
- RF-03: Orquestación del flujo completo. Desde el análisis hasta la contención simulada y el escalado según la
  severidad del incidente.
- RF-04: Gestión de casos. Cada incidente debe generar un caso en TheHive con IoCs, etiquetas y registro de
  acciones, preservando las evidencias.
- RF-05: Monitoreo. MTTR, tasa de éxito y KPIs del playbook, visualizados en Grafana mediante logs agregados por
  Loki y Promtail, con datos indexados en Elasticsearch.
- RF-06: Simulador de alertas. Un módulo generador debe producir alertas maliciosas y benignas con IoCs realistas
  hacia el webhook de Shuffle, permitiendo repetir el experimento sin dependencias externas.
- RF-07: Contención simulada. El sistema debe ejecutar acciones de contención simulada (aislamiento de endpoint,
  bloqueo de IP) mediante endpoints mock que registran la intención sin aplicar cambios reales.
- RF-08: API REST de gestión. Una API FastAPI debe exponer endpoints para health, autenticación, backup, métricas
  analíticas, estado de servicios y operaciones SOAR, con documentación OpenAPI automática.
- RF-09: Cálculo de métricas estadísticas. El sistema debe calcular MTTR (media, mediana, percentiles p50 y p90),
  desviación estándar y coeficiente de variación a partir de las ejecuciones del playbook.

Requisitos No Funcionales

Los requisitos no funcionales fijan los criterios de calidad del sistema:

- RNF-01: Rendimiento. Reducción del MTTR ≥ 50 % respecto al baseline manual, con medición de percentiles p50 y p90
  sobre 50 ejecuciones por escenario.
- RNF-02: Reproducibilidad. Despliegue reproducible mediante Docker Compose y Makefile, con `make up` como único punto
  de entrada y `make generate-secrets` para la generación de credenciales.
- RNF-03: Seguridad. Aislamiento de red entre componentes, secretos gestionados mediante variables de entorno,
  autenticación JWT para la API, sanitización de payloads de entrada y certificados TLS autofirmados para el tráfico
  externo.
- RNF-04: Calidad del software. Suite de tests automatizada con pytest (2041 tests) y despliegue verificable con
  `make test-e2e`.
- RNF-05: Resiliencia. Circuit breaker y reintentos con backoff exponencial en las integraciones entre componentes
  para manejar fallos transitorios sin perder la alerta.
- RNF-06: Observabilidad. Health checks por servicio, logs estructurados agregados en Loki y dashboards de Grafana
  con métricas en tiempo real.

Requisitos de Integración

Los requisitos de integración especifican las conexiones entre componentes del sistema:

- RI-01: Integración entre TheHive y Cortex. Los observables creados en TheHive se envían a Cortex para su análisis
  mediante analyzers configurados, y los resultados se devuelven automáticamente.
- RI-02: Integración entre Shuffle y TheHive. Shuffle recibe alertas por webhook y crea o actualiza casos mediante API
  sin intervención manual, con reintentos ante fallos temporales.
- RI-03: Fuentes externas de threat intelligence. Analyzers libres de Cortex para reputación de IPs (DShield),
  resolución DNS (GoogleDNS) y passive DNS (Mnemonic pDNS) para infraestructura de comando y control.
- RI-04: Integración opcional con MISP. Intercambio de indicadores de amenazas con MISP para enriquecimiento
  adicional, sin ser requisito para la ejecución del playbook E2E.

Matriz de Trazabilidad de Requisitos

La matriz de trazabilidad conecta cada requisito con su componente implementador, prioridad y método de verificación:

| ID     | Requisito          | Componente | Prioridad | Verificación                                     |
|--------|--------------------|------------|-----------|--------------------------------------------------|
| RF-01  | Gestión de Alertas | Shuffle    | Alta      | Prueba E2E del flujo completo de alertas         |
| RF-02  | Análisis de IoCs   | Cortex     | Alta      | Prueba de integración de analyzers               |
| RF-03  | Orquestación       | Shuffle    | Alta      | Prueba funcional del playbook                    |
| RF-04  | Gestión de Casos   | TheHive    | Alta      | Prueba E2E de creación y cierre de casos         |
| RF-05  | Monitoreo          | Loki/Grafana | Media   | Verificación de métricas en dashboard            |
| RF-06  | Simulador          | Python/simulator | Alta | Pruebas E2E y de carga usan el simulador    |
| RF-07  | Contención simulada | FastAPI   | Alta      | Endpoint `/api/v1/contain` en `routes_services` |
| RF-08  | API REST           | FastAPI    | Media     | Pruebas de integración de API                    |
| RF-09  | Métricas estadísticas | Python/domain | Alta | Resultados en `reports/e2e/` (n=50)          |
| RNF-01 | Rendimiento        | Sistema    | Alta      | Benchmark de MTTR (n=50 por escenario)           |
| RNF-02 | Reproducibilidad   | Docker     | Alta      | `make up` + `pytest tests/e2e/`                  |
| RNF-03 | Seguridad          | Docker/Nginx/FastAPI | Media | Revisión de config, JWT, sanitización    |
| RNF-04 | Calidad            | pytest     | Media     | Suite de tests (2041 tests)                      |
| RNF-05 | Resiliencia        | Python/resilience | Media | Prueba unit de circuit breaker             |
| RNF-06 | Observabilidad     | Loki/Grafana | Media   | Health checks y dashboards                       |
| RI-01  | TheHive ↔ Cortex   | TheHive/Cortex | Alta  | Prueba de integración de observables             |
| RI-02  | Shuffle ↔ TheHive  | Shuffle/TheHive | Alta | Prueba E2E de webhook y creación de casos        |
| RI-03  | Threat intelligence | Cortex    | Media     | Verificación de analyzers libres                 |
| RI-04  | MISP (opcional)    | MISP       | Baja      | `docker-compose.misp.yml` disponible             |

La **Tabla 4** resume el estado de cumplimiento de los requisitos.

## Tabla 4: Estado de Cumplimiento de Requisitos

| ID     | Tipo   | Requisito                     | Métrica de Verificación  | Estado             |
|--------|--------|-------------------------------|--------------------------|--------------------|
| RF-01  | **F**  | Gestión de alertas ransomware | 100% alertas procesadas  | Cumplido           |
| RF-02  | **F**  | Análisis automático IoCs      | Analyzers libres Cortex  | Cumplido           |
| RF-03  | **F**  | Orquestación playbook         | 1 playbook E2E, 2 escenarios | Cumplido      |
| RF-04  | **F**  | Gestión de casos              | Integración TheHive      | Cumplido           |
| RF-05  | **F**  | Monitoreo                     | Dashboard Grafana + Loki | Cumplido           |
| RF-06  | **F**  | Simulador de alertas          | E2E + pruebas de carga   | Cumplido           |
| RF-07  | **F**  | Contención simulada           | Endpoint mock FastAPI    | Cumplido           |
| RF-08  | **F**  | API REST de gestión           | Tests de integración API | Cumplido           |
| RF-09  | **F**  | Métricas estadísticas         | Resultados n=50 en `reports/e2e/` | Cumplido   |
| RNF-01 | **NF** | Reducción MTTR ≥ 50%          | 92.3% (n=50)             | Cumplido           |
| RNF-02 | **NF** | Reproducibilidad              | `make up` + tests E2E    | Cumplido           |
| RNF-03 | **NF** | Seguridad                     | Aislamiento, JWT, sanitización | Cumplido     |
| RNF-04 | **NF** | Calidad                       | 2041 tests automatizados | Cumplido           |
| RNF-05 | **NF** | Resiliencia                   | Circuit breaker + retry  | Cumplido           |
| RNF-06 | **NF** | Observabilidad                | Health checks + Loki     | Cumplido           |
| RI-01  | **I**  | TheHive ↔ Cortex              | Observables enriquecidos | Cumplido           |
| RI-02  | **I**  | Shuffle ↔ TheHive             | Webhook + API            | Cumplido           |
| RI-03  | **I**  | Threat intelligence           | Hashdd_Status, IP-API, DShield, Mnemonic pDNS, GoogleDNS, DomainMailSPFDMARC, ValidateObservable | Cumplido  |
| RI-04  | **I**  | MISP (opcional)               | `docker-compose.misp.yml` | Opcional          |



### 4.1.2. Descripción de la herramienta software desarrollada

Arquitectura General del Sistema

El laboratorio combina dos patrones arquitectónicos. El código Python sigue una arquitectura hexagonal (ports and adapters) que aísla el dominio de los detalles técnicos: `domain/` no importa nada de `infrastructure/`, los puertos definen qué operaciones necesita el dominio y los adaptadores las implementan contra tecnologías concretas. Pydantic (Pydantic, 2024) valida los payloads en los límites. El beneficio es doble: en tests, los adaptadores se mockean sin tocar el dominio; en producción, sustituir un proveedor (por ejemplo, Elasticsearch por OpenSearch) solo requiere reescribir un adaptador.

Para la infraestructura Docker se emplea una arquitectura en capas que mantiene la lógica de negocio desacoplada de las implementaciones concretas. La **Figura 3** muestra la arquitectura general y la **Figura 4** el despliegue Docker Compose, ambos en formato Mermaid canónico en el **Anexo H** (sección H.1).

Flujo General del Sistema

```mermaid
---
title: Flujo General del Sistema
---
graph TD     A[Generación de Alertas] --> B[Recepción en Shuffle]
    B --> C[Validación y Clasificación]
    C --> D[Análisis de Indicadores]
    D --> E[Cálculo de Riesgo]
    E --> F{Riesgo Alto?}     F -->|Sí| G[Activación de Contención]
    F -->|No| H[Marcar como falso positivo]
    G --> I[Creación de Caso en TheHive]
    H --> I     I --> J[Registro de Acciones]
    J --> K[Cálculo de KPIs]
    K --> L[Monitoreo y Dashboards]
    L --> M[Análisis de Resultados]
```

#### Arquitectura de Código Python

El código en `src/soar_lab/` se organiza según el patrón hexagonal: el dominio en el centro, aislado de infraestructura y frameworks. Los diagramas canónicos completos están en el **Anexo H** (secciones H.2, H.3 y H.4).

```mermaid
---
title: Arquitectura de Código Python (patrón hexagonal)
---
graph TD
    subgraph Dominio
        D1[domain/ - entidades, puertos, servicios de dominio]
    end

    subgraph Aplicación
        A1[application/ - casos de uso y puertos input/output]
        A2[auth/ - fachada de autenticación]
    end

    subgraph Infraestructura
        I1[infrastructure/ - adaptadores: integraciones, persistencia, monitoring]
        I2[db/ - inicialización de base de datos]
        I3[logging/ - logger estructurado]
    end

    subgraph Interfaces
        IF1[interfaces/api/ - API FastAPI, CLI, static]
    end

    subgraph Soporte
        S1[config/ - settings, esquemas, logging config]
        S2[common/ - constantes, excepciones, runtime]
        S3[validation/ - validadores reutilizables]
        S4[security/ - sanitización de payloads]
        S5[resilience/ - circuit breaker, retry, timeout]
        S6[simulator/ - simulador de alertas SIEM]
        S7[data/ - cálculo de KPIs, generación de IoCs]
    end

    IF1 --> A1
    A1 --> D1
    A1 --> I1
    I1 --> D1
    A2 --> I1
    S1 --> D1
    S5 --> I1
    S6 --> IF1
    S7 --> A1
```

Las capas son:

- `domain/`: lógica de negocio pura. Define entidades (alertas, casos, IoCs), puertos (contratos de infraestructura) y servicios de dominio (cálculos de métricas).
- `application/`: casos de uso que orquestan los puertos del dominio (análisis de KPIs, autenticación, backup, salud, pruebas).
- `auth/`: fachada que re-exporta `AuthService` para acceso desde la API.
- `infrastructure/`: adaptadores concretos de los puertos. Incluye `integrations/` (clientes de TheHive, Cortex, Shuffle, MISP), `persistence/`, `monitoring/`, `messaging/`, `network_watcher/`, `security/` y `templates/`.
- `interfaces/`: API FastAPI (`api/`), CLI y recursos estáticos. Gestiona la inyección de dependencias.
- `config/`: settings, esquemas de datos y configuración de logging.
- `common/`: constantes, excepciones y utilidades de runtime compartidas.
- `validation/`: validadores de datos reutilizables.
- `security/`: sanitización de payloads de entrada.
- `resilience/`: circuit breaker, retry con backoff y timeout para integraciones.
- `simulator/`: simulador de alertas SIEM (maliciosas y benignas).
- `data/`: scripts para cálculo de KPIs y generación de IoCs.
- `db/`: inicialización y gestión de transacciones de base de datos.
- `logging/`: wrapper de logger estructurado.

#### Arquitectura de Despliegue

La infraestructura se organiza en cuatro capas:

```mermaid
---
title: Arquitectura de Despliegue (cuatro capas)
---
graph TD
    subgraph Capa de Datos
        DB1[Elasticsearch]
        DB2[Redis]
        DB3[OpenSearch]
    end

    subgraph Capa Aplicación SOAR
        APP1[TheHive]
        APP2[Cortex]
        APP3[Shuffle Frontend]
        APP4[Shuffle Backend]
        APP5[Orborus]
        APP6[Tenzir]
        APP7[Network Watcher]
    end

    subgraph Capa Integración
        INT1[Nginx]
        INT2[API FastAPI]
        INT3[Docs-site]
        INT4[Web-management]
    end

    subgraph Capa Monitoreo
        MON1[Loki]
        MON2[Promtail]
        MON3[Grafana]
        MON4[PostgreSQL]
        MON5[Grafana Renderer]
    end

    APP1 --> DB1
    APP2 --> DB1
    APP4 --> DB3
    APP4 --> DB2
    APP3 --> APP4
    APP5 --> APP4
    APP5 --> DB3
    APP5 --> Docker[Docker Socket]
    APP4 --> Docker
    INT1 --> APP1
    INT1 --> APP2
    INT1 --> APP3
    INT1 --> INT4
    INT2 --> APP1
    INT2 --> APP2
    INT2 --> APP4
    INT2 --> DB2
    MON2 --> Docker
    MON2 --> MON1
    MON3 --> MON1
    MON3 --> MON4
    MON3 --> MON5
```

La capa de datos incluye Elasticsearch (Elastic, 2024; Elastic, n.d.) para TheHive y Cortex, Redis (Redis Ltd., 2024) para colas y caché, y OpenSearch (OpenSearch Project, 2024) como motor de búsqueda de Shuffle. La capa de aplicación SOAR la forman TheHive (TheHive Project, 2024; TheHive Project, n.d.), Cortex (Cortex Project, 2024; Cortex Project, n.d.), Shuffle (frontend y backend) (Shuffle Tools, 2024; Shuffle Tools, n.d.), Orborus (ejecutor de workflows que accede al socket de Docker (Docker Inc., 2024; Docker, n.d.) para lanzar contenedores), Tenzir (procesamiento de eventos de red) y Network Watcher (monitor de la red soar_net). La capa de integración incluye Nginx (Nginx, 2024; Nginx, n.d.) como proxy inverso, la API FastAPI (FastAPI, 2024), el sitio de documentación y la interfaz web de gestión. El monitoreo usa Loki (Grafana Labs, 2024b), Promtail (Grafana Labs, 2024c), Grafana (Grafana Labs, 2024; Grafana, n.d.) con PostgreSQL como base de datos y Grafana Renderer para exportación de paneles.

La infraestructura se define con varios archivos Docker Compose (Docker Inc., 2024) que se combinan para desplegar el sistema completo. El archivo principal `docker-compose.yml` define cuatro redes (perimetral bridge, interna soar_net, inteligencia ti_net, monitoreo logging_net) y los volúmenes persistentes, e incluye Elasticsearch. El archivo `docker-compose.core.yml` contiene Redis, TheHive, Cortex, Shuffle, Orborus, Network Watcher y Tenzir, con verificaciones de salud, límites de recursos y dependencias. Los archivos complementarios añaden: `docker-compose.api.yml` (API FastAPI, docs-site, web-management y Nginx), `docker-compose.misp.yml` (MISP, misp-db y misp-modules) (MISP Project, 2024), `docker-compose.opensearch.yml` (OpenSearch y OpenSearch Dashboards) (OpenSearch Project, 2024) y `docker-compose.logging.yml` (Loki, Promtail, Grafana, PostgreSQL y Grafana Renderer).

La segmentación de redes sigue un modelo por zonas de seguridad: la red bridge es accesible desde el host, soar_net (10.100.0.0/16) conecta los componentes SOAR, ti_net (172.22.0.0/16, red interna) vincula Elasticsearch, Redis, Shuffle y la API, y logging_net (172.23.0.0/16) aísla el stack de logging (Grafana, Loki y Promtail conectan además a soar_net para recoger datos de los servicios). Esta separación limita el movimiento lateral en caso de compromiso. Los volúmenes usan enlaces al directorio runtime con subdirectorios por servicio; los datos sobreviven a reinicios y pueden migrarse copiando ese directorio. La **Tabla 6** detalla la configuración de recursos.

Flujo de Integración entre Componentes

```mermaid
---
title: Flujo de Integración entre Componentes
---
graph TD
    A[Simulador SIEM] -->|webhook| B[Shuffle - Orquestador]
    B --> C[Normalize + Build Case JSON]
    C --> D[TheHive - Crear caso]
    D --> E[TheHive - Observables hash/IP]
    D --> F[TheHive - Tarea de investigación]
    D --> G[Cortex - Análisis de hash]
    D --> H[Cortex - Análisis de IP]
    G --> I[Hashdd_Status / IP-API]
    H --> J[DShield / Mnemonic pDNS / GoogleDNS]
    D --> K[MISP - Búsqueda de indicadores]
    D --> L[Tenzir - Análisis de tráfico]
    D --> M[Network Watcher - Monitor de red]
    D --> N[Redis - Caché de IoCs]
    D --> O[Loki - Búsqueda de logs]
    D --> ES[Elasticsearch - Indexar alerta]
    E --> P[Calc decision - Score y verdict]
    F --> P
    I --> P
    J --> P
    K --> P
    L --> P
    M --> P
    N --> P
    O --> P
    ES --> P
    P --> Q{Score ≥ 80 o malicious?}
    Q -->|Sí| R[Contención simulada]
    Q -->|No| S[TheHive - Resolved/FalsePositive]
    R --> T[TheHive - Caso permanece Open]
    T --> V[Notificación crítica]
    S --> W[Notificación informativa]
    V --> Y[Calc MTTR]
    W --> Y
    Y --> X[TheHive - Enriquecer caso]
    X --> Z[Elasticsearch - Indexar métricas]
    Z --> AA[Reporte Final]
```

TheHive (v3.5.2) gestiona el ciclo de vida de los casos (TheHive Project, 2024) con plantillas especializadas para ransomware, asignación de tareas y registro de acciones. Su integración con Cortex permite analizar IoCs sin salir de la interfaz del caso. Las evidencias se almacenan con verificación hash para asegurar su integridad forense.

Cortex (v3.2.0) analiza IoCs en entornos aislados (Cortex Project, 2024) con 7 analyzers libres sin API key: Hashdd_Status (hashes), IP-API y DShield (IPs), GoogleDNS y DomainMailSPFDMARC (dominios), Mnemonic pDNS (passive DNS) y ValidateObservable (validación). El sistema cachea resultados para evitar consultas redundantes. La **Tabla 5** lista los analyzers con su tipo y uso en el playbook.

## Tabla 5: Analyzers Cortex Configurados

| Analyzer              | Tipo     | API Key | Uso en Playbook   |
|-----------------------|----------|---------|-------------------|
| **Hashdd_Status**     | Hash     | No      | Status lookup de hashes |
| **IP-API**            | IP       | No      | Geolocalización de IP |
| **DShield**           | IP       | No      | Reputación SANS ISC |
| **Mnemonic pDNS**     | Domain/IP| No      | Passive DNS |
| **GoogleDNS**         | Domain   | No      | Resolución DNS |
| **DomainMailSPFDMARC**| Domain   | No      | SPF/DMARC lookup |
| **ValidateObservable**| Multiple | No      | Validación de observables |

La selección prioriza analyzers libres sin API key (RF-02). Todos están integrados en el playbook, enriqueciendo cada IoC detectado.

Shuffle (v2.2.1) orquesta los flujos mediante una interfaz visual de bloques (Shuffle Tools, 2024). Orborus ejecuta workflows en paralelo entre workers y gestiona reintentos automáticos. La ejecución condicional y la programación de tareas permiten adaptar el flujo al contexto del incidente.

#### Scripts de Automatización Desarrollados

```mermaid
---
title: Capacidades de Automatización
---
graph TD
    subgraph Provisionamiento
        P1[Generación de secretos]
        P2[Renderizado de configuración]
        P3[Inicialización de servicios]
        P4[Instalación de analyzers e IoCs]
    end

    subgraph Orquestación de Workflows
        O1[Definición del workflow]
        O2[Cableado de integraciones]
        O3[Scripts embebidos en Shuffle]
    end

    subgraph Simulación
        SM1[Generación de alertas]
        SM2[IoCs realistas CISA/MITRE]
        SM3[Envío al webhook]
    end

    subgraph Mantenimiento
        M1[Limpieza de ejecuciones stale]
        M2[Espera de workflows]
        M3[Verificación de imágenes]
        M4[Limpieza de casos TheHive]
        M5[Warmup de Shuffle]
    end

    subgraph Observabilidad
        OB1[notify.log + Elasticsearch]
        OB2[StatisticalCalculator]
        OB3[MTTR / P50 / P90 / Medias]
        OB4[KPIAnalyzer]
        OB5[kpis.csv]
        OB6[Dashboard Grafana]
        OB7[Reportes E2E]
    end

    subgraph Calidad y CI
        Q1[Análisis estático]
        Q2[Mutation testing]
        Q3[Calidad de documentación]
        Q4[Revisión holística]
    end

    subgraph Seguridad operacional
        SF1[Preservación de credenciales]
        SF2[Restauración de credenciales]
    end

    P3 --> O1
    O1 --> O2
    O2 --> O3
    P4 --> O2
    SM3 --> O1
    O3 --> OB1
    OB1 --> OB2
    OB2 --> OB3
    OB3 --> OB4
    OB4 --> OB5
    OB5 --> OB6
    M1 --> O1
    M2 --> OB7
    M5 --> O1
    Q1 --> Q4
    Q2 --> Q4
    Q3 --> Q4
    SF1 --> SF2
    SF2 --> P3
```

La automatización se organiza en siete capacidades. El **provisionamiento** genera secretos, renderiza configuración desde plantillas, inicializa TheHive/Cortex/Shuffle y instala los analyzers de Cortex junto con los IoCs en MISP, de forma que un único comando (`make up`) deja el laboratorio operativo. La **orquestación de workflows** define el playbook completo (46 nodos, 60 ramas) y cablea cada integración; 21 scripts Python embebidos se ejecutan dentro de Shuffle para normalizar, decidir y enriquecer.

La **simulación** genera alertas de ransomware con IoCs realistas (hashes SHA256 de advisories CISA, IPs C2, técnicas MITRE ATT&CK) y las envía al webhook de Shuffle vía HTTP, permitiendo configurar tipo, volumen y frecuencia. El **mantenimiento** limpia ejecuciones stale de Shuffle y casos de TheHive, hace warmup del orquestador antes de los tests, espera a que los workflows terminen para sincronizar los tests E2E y verifica la integridad de las imágenes Docker.

La **observabilidad** calcula KPIs (MTTR, percentiles P50/P90, medias, desviaciones) desde los logs y Elasticsearch, los exporta a CSV y los visualiza en dashboards de Grafana; genera además informes automáticos de los tests E2E. La **calidad y CI** ejecuta análisis estático (bandit, ruff, pylint, radon, vulture), mutation testing, control de calidad y terminología de la documentación, y una revisión holística del proyecto en 15 dimensiones. La **seguridad operacional** preserva y restaura las credenciales de los servicios entre resets, evitando rotaciones manuales de API keys.



#### Sistema de Monitoreo

```mermaid
---
title: Sistema de Monitoreo
---
graph TD
    subgraph Recopilación
        P1[Promtail]
    end

    subgraph Almacenamiento
        L1[Loki]
        ES[Elasticsearch soar-metrics]
    end

    subgraph Visualización
        G1[Grafana]
        GR[Grafana Renderer]
        PG[PostgreSQL]
    end

    subgraph Fuentes
        DK[Docker Socket]
        SH[Shuffle Workflow]
        API2[API FastAPI]
    end

    DK --> P1
    P1 --> L1
    SH --> ES
    G1 --> L1
    G1 --> ES
    G1 --> API2
    G1 --> PG
    G1 --> GR
```

El monitoreo usa Loki (Grafana Labs, 2024b), Promtail (Grafana Labs, 2024c), Grafana (Grafana Labs, 2024) con PostgreSQL como base de datos y Grafana Renderer para exportación de paneles. Promtail descubre automáticamente todos los contenedores vía Docker socket (`docker_sd_configs`) y los envía a Loki. El workflow de Shuffle indexa métricas en Elasticsearch (índice `soar-metrics`). Grafana consulta tres datasources: Loki para logs, Elasticsearch para KPIs y la API FastAPI para datos en tiempo real, usando PostgreSQL para su configuración.

El dashboard de Grafana (`SOAR KPI Dashboard`) implementa 15 paneles con las métricas reales del proyecto: MTTR (medio, P50, P90, max/min, rango, percentiles P50/P75/P90/P95), total de alertas procesadas, alertas críticas (severity=3), tasa de éxito por tipo de alerta, tasa de éxito por servicio (TheHive/Cortex/MISP), tasa de éxito por severidad, alertas por severidad, throughput por hora, evolución temporal de MTTR, evolución de alertas por tipo y comparación de MTTR por tipo de alerta. La **Tabla 7** resume las métricas con sus umbrales.

## Tabla 7: Métricas del Dashboard de Grafana

| Categoría          | Métrica              | Objetivo       | Panel |
|--------------------|----------------------|----------------|-------|
| **Rendimiento**    | MTTR medio           | ≤ 120s         | MTTR Medio (s) |
| **Rendimiento**    | MTTR P50 (mediana)   | ≤ 120s         | MTTR p50 |
| **Rendimiento**    | MTTR P90             | ≤ 180s         | MTTR p90 |
| **Rendimiento**    | MTTR max/min         | —              | MTTR Max / Min |
| **Rendimiento**    | Percentiles P50/P75/P90/P95 | —       | Análisis de Percentiles |
| **Rendimiento**    | Throughput           | —              | Alertas procesadas por hora |
| **Negocio**        | Total alertas        | —              | Total Alerts Processed |
| **Negocio**        | Alertas críticas     | —              | Alertas Criticas (severity=3) |
| **Negocio**        | Tasa de éxito por tipo | 100%         | Tasa de Exito por Tipo |
| **Negocio**        | Tasa de éxito por servicio | 100%    | Tasa de Exito Servicios |
| **Negocio**        | Alertas por severidad | —             | Alertas por Severidad |
| **Negocio**        | Evolución MTTR diario | —            | Evolucion MTTR |
| **Negocio**        | MTTR por tipo de alerta | —           | MTTR por Tipo de Alerta |
| **Negocio**        | Tasa de éxito por severidad | 100%   | Tasa de Exito por Severidad |
| **Negocio**        | Evolución de alertas por tipo | —     | Evolucion de Alertas por Tipo |

El stack se inicia con `make up` y la interfaz de Grafana está disponible en el puerto configurado con credenciales del archivo de entorno.

### 4.1.3. Evaluación

#### 4.1.3.1. Diseño Experimental

La evaluación compara la respuesta manual con la automatizada SOAR. La variable independiente es el tipo de respuesta; la dependiente, el MTTR en segundos (desde recepción de la alerta hasta contención simulada). Las variables controladas comprenden el entorno Docker Compose, el hardware, la configuración de los componentes y el conjunto de alertas.

**Justificación del baseline manual.** El valor de 3600 s (1 hora) se fundamenta en datos de la industria. CrowdStrike establece el benchmark ideal 1-10-60: detectar en 1 minuto, investigar en 10 y contener en 60 (CrowdStrike, 2021), aunque la media real de las organizaciones encuestadas es de 16 horas. ReliaQuest reporta un MTTR tradicional de 2.3 días sin automatización (ReliaQuest, 2024). La SANS SOC Survey 2025 sitúa el tiempo mediano de triaje en 260 minutos (SANS Institute, 2025). El valor de 3600 s adoptado se alinea con el benchmark de CrowdStrike y es conservador frente a las medias reales, evitando sobreestimar la reducción lograda.

#### 4.1.3.2. Procedimiento de Evaluación

Fase 1 (baseline manual): el analista recibe la alerta simulada, revisa la información en TheHive, consulta Cortex manualmente, decide la contención, ejecuta los scripts de aislamiento y documenta el caso.

Fase 2 (respuesta SOAR): Shuffle recibe la alerta por webhook, clasifica el incidente, lanza los analyzers de Cortex en paralelo, crea el caso en TheHive mediante API y activa la contención simulada si el score supera el umbral. El analista no interviene durante la ejecución.

`AnalyticsService` calcula las métricas desde los logs mediante `ExecutionLogParser`, `KPIAnalyzer` y `StatisticalCalculator`. La métrica principal recogida es el MTTR total (desde recepción de la alerta hasta contención o clasificación), indexada en Elasticsearch como `mttr_seconds`. Los resultados se exportan a CSV con `CSVKPIFormatter`.

Comandos de ejecución:

- `make up` (despliegue del stack completo)
- `make test-e2e-tc01` (escenario malicioso, 11 subtests)
- `make test-e2e-tc02` (escenario benigno / falso positivo, 5 subtests)
- `make test-e2e-tc03` (casos de borde E2E)
- `make test-e2e` (suite completa: 33 casos de test + 5 tests de KPI)
- `make simulate-batch N=50` (envío de lote de 50 alertas para experimentos)
- `make metrics` (cálculo de KPIs y exportación a CSV)

Los resultados experimentales se almacenan en `reports/e2e/` y `reports/validation/results/kpis.csv`.

#### 4.1.3.3. Resultados Experimentales

El experimento ejecutó 50 runs del playbook en dos escenarios (malicioso y benigno) sobre el entorno Docker aislado. La **Figura 6** muestra la comparación visual del MTTR.

**Cumplimiento de objetivos.** La tabla resume los umbrales definidos frente a los valores medidos:

| Objetivo | Umbral | Valor medido | Cumple |
|----------|--------|--------------|--------|
| MTTR P50 (mediana) | ≤ 120 s | 193.19 s | No |
| MTTR P90 | ≤ 180 s | 621.83 s | No |
| Tasa de éxito | ≥ 95 % | 100 % | Sí |
| Dataset (n ejecuciones) | ≥ 50 | 50 | Sí |
| Reducción MTTR vs manual | ≥ 50 % | 92.3 % | Sí |

**Cumplimiento global: 3 de 5 objetivos.**

La **Tabla 8** presenta los resultados experimentales detallados del experimento con n=50 ejecuciones, contrastando las métricas de la respuesta manual estimada con la respuesta SOAR automatizada.

## Tabla 8: Resultados Experimentales Detallados

| Métrica                 | Manual (estimado) | SOAR (n=50)  | Reducción |
|-------------------------|-------------------|--------------|-----------|
| **MTTR Promedio**       | 3600s             | 277.15s      | 92.3%     |
| **MTTR Mediana (P50)**  | 3600s             | 193.19s      | 94.6%     |
| **Desviación Estándar** | N/A               | 187.61s      | N/A       |
| **Coef. Variación**     | N/A               | 67.7%        | N/A       |
| **P90**                 | 3600s             | 621.83s      | 82.7%     |
| **P95**                 | 3600s             | 644.46s      | 82.1%     |
| **Tasa Éxito**          | ~80% (est.)       | 100%         | +20pp     |
| **Tasa Contención**     | N/A               | 92.0%        | N/A       |
| **Score Promedio**      | N/A               | 96.2/100     | N/A       |
| **Falsos Positivos**    | N/A               | 8.0%         | N/A       |
| **Recursos (mem pico)** | N/A               | 2.58 GiB     | N/A       |

La tasa de éxito del 100 % (50/50) y la contención del 92.0 % (46/50 con score >= 80) indican que la automatización no sacrifica calidad por velocidad. El score promedio de 96.2/100 confirma el motor de scoring basado en threat intelligence (Cortex Project, 2024; MISP Project, 2024; Tenzir, 2024; Grafana Labs, 2024b; MITRE, 2025). El tiempo mínimo fue 65.38 s. La **Figura 7** muestra los tiempos por fase.

![Figura 7: Tiempos por componente del workflow](figures/GE1_component_timings.png)

**Figura 7**: Tiempos medios por componente del workflow E2E (ingesta, triage, análisis de IoCs, creación de caso,
contención y cierre).

El análisis por componente de tiempo se detalla en la **Tabla 9**, que desglosa la duración de cada fase del workflow automatizado frente a la condición manual.

## Tabla 9: Análisis por Componente de Tiempo

| Componente             | Manual | SOAR    | Reducción Absoluta | Reducción Porcentual |
|------------------------|--------|---------|--------------------|----------------------|
| **Recepción y Triaje** | N/A    | 103.92s | N/A                | N/A                  |
| **Análisis de IoCs**   | N/A    | 2393.46s| N/A                | N/A                  |
| **Creación de Caso**   | N/A    | 2773.48s| N/A                | N/A                  |
| **Contención**         | N/A    | 422.0s  | N/A                | N/A                  |
| **MTTR medio**         | 3600s  | 277.15s | 3322.85s           | 92.3%                |

La reducción del 92.3 % en MTTR medio se concentra en la eliminación del tiempo de espera humano entre pasos. Los tiempos por fase son acumulativos con solapamiento entre nodos paralelos, por lo que su suma excede el MTTR wall-clock de 277.15 s. Esto identifica oportunidades de mejora en caché de resultados y ejecución concurrente de analyzers.

![Figura 8: Análisis de percentiles MTTR](figures/grafana_panel_5_Grafico_4_4___Analisis_de_Percentiles_MTTR__distri.png)

**Figura 8**: Distribución de percentiles MTTR capturada desde el dashboard de Grafana.

**Decisiones automatizadas.** El verdict fue *malicious* en 13 casos (score medio 97.3) y *suspicious* en 37 (score medio 95.8). La **Figura 9** muestra la distribución de decisiones y la **Figura 5** el estado de los jobs de Cortex.

![Figura 9: Distribución de decisiones del playbook](figures/decision_distribution.png)

**Figura 9**: Distribución de decisiones automatizadas (malicious, suspicious, benign) sobre las 50 ejecuciones.

![Figura 5: Estado de jobs de Cortex](figures/cortex_job_status.png)

**Figura 5**: Estado de los jobs de Cortex (255/257 completados, 99.2 % de éxito).

**Servicios e integraciones.** Los 10 servicios críticos estuvieron healthy en el 100 % de las ejecuciones. Se completaron 50/50 workflows, 50/50 casos en TheHive y 255/257 jobs en Cortex (99.2 %). El workflow incluye 46 nodos y la automatización fue del 100 %, sin intervención humana.

**Precisión.** La tasa de falsos positivos fue del 8.0 % (4/50 clasificadas como *observe* cuando se esperaba *contain*), mejorando el promedio reportado por SANS 2024 (64 % de organizaciones identifican los falsos positivos como problema mayor). La precisión del motor de scoring fue del 92.0 % (46/50 decisiones acertadas).

**Uso de recursos.** El consumo medido con `docker stats` se mantuvo dentro de los límites configurados. Elasticsearch (2.28 GiB) y OpenSearch (2.58 GiB) fueron los servicios con mayor consumo de memoria; Tenzir mostró el mayor uso de CPU (15.54 %). Ningún contenedor superó su límite, confirmando la viabilidad en un host con 16 GiB RAM. La validación consolidada (Quality Score 92.2/100, HPR 96.0/100) se detalla en el **Anexo E** (sección E.1).

#### 4.1.3.4. Evaluación de Calidad del Sistema

El laboratorio cumple los requisitos funcionales y de calidad, aunque dos umbrales de rendimiento (MTTR P50 y P90) no se alcanzaron (§4.1.3.3). La cobertura de tests se verifica con `make test-coverage` en `reports/coverage/`. La estrategia de testing (2041 tests, pirámide, 9 marcadores pytest, coverage 84.6 %, quality gates, 49 TCs E2E) se detalla en el **Anexo G** (sección G.1). La validación consolidada (Quality Score 92.2/100, HPR 96.0/100) está en el **Anexo E** (sección E.1).

Comandos de prueba disponibles:

- `make test-all`: suite completa
- `make test-unit`: pruebas unitarias
- `make test-integration`: pruebas de integración
- `make test-e2e`: flujos E2E
- `make test-atomic`: tests de componentes aislados
- `make test-security`: análisis de vulnerabilidades
- `make test-performance`: latencia y throughput
- `make test-smoke`: validación rápida post-despliegue
- `make test-coverage`: informe de cobertura

En usabilidad, el tiempo de aprendizaje es asumible con formación inicial mínima. La reducción de errores humanos es consistente con la literatura sobre automatización en SOC (Kinyua & Awuah, 2021; Mohammad & Lakshmisri, 2018).

#### 4.1.3.5. Discusión

La reducción del MTTR medio (3600 s a 277.15 s) respalda la hipótesis de que la automatización SOAR acorta los tiempos de respuesta, coherente con la literatura: Kinyua y Awuah identifican MTTR como métrica habitual de valor operativo de SOAR (Kinyua & Awuah, 2021), y Obuse et al. reportan mejoras en automatización de respuesta en infraestructuras críticas (Obuse et al., 2023).

Sin embargo, P50 (193.19 s) y P90 (621.83 s) no alcanzaron los umbrales (≤ 120 s y ≤ 180 s). Esta discrepancia indica una distribución asimétrica con cola larga: la mayoría de ejecuciones se completan rápido, pero un subconjunto experimenta latencias elevadas por saturación del worker de Cortex y timeouts de APIs externas (DShield, Mnemonic pDNS, GoogleDNS). El workflow lanza analyzers concurrentes (fan-out), pero la acumulación de jobs en colas sucesivas degrada el tiempo de respuesta. Un escalado horizontal del worker de Cortex, propuesto como trabajo futuro, debería acercar P50/P90 a los umbrales.

**Consistencia.** El coeficiente de variación del MTTR fue del 67.7 % (σ = 187.61 s, μ = 277.15 s). Aunque refleja la cola larga, debe contrastarse con la variabilidad inherente de la respuesta manual, donde las diferencias entre analistas, fatiga y contexto hacen la consistencia prácticamente inmedible. La automatización garantiza que cada ejecución sigue el mismo flujo y registra las mismas evidencias, lo que supone una mejora de consistencia estructural.

**Análisis por subconjuntos.** Las primeras 12 alertas (n=12, antes de la degradación por acumulación de jobs) presentan P50 = 128.40 s y P90 = 163.90 s. En este subconjunto el P90 cumple el umbral (≤ 180 s) y el P50 se sitúa cerca (128 s vs 120 s). Esto sugiere que los umbrales son alcanzables en condiciones de baja carga, y que la degradación en el conjunto completo (n=50) responde a saturación progresiva más que a una limitación intrínseca del diseño.

El resultado negativo (2 de 5 objetivos no cumplidos) no invalida la contribución: la reducción del MTTR medio supera ampliamente el 50 %, y la tasa de éxito del 100 % confirma la fiabilidad funcional. El laboratorio demuestra viabilidad y cuantifica mejoras, pero no puede generalizarse a entornos productivos sin ajustes adicionales.

Comparado con Núñez Fernández (2023), que despliega una plataforma SIRP similar con TheHive, Cortex, MISP y Wazuh, este TFM aporta evidencia cuantitativa adicional (n=50, percentiles, análisis estadístico) que complementa su validación cualitativa. La diferencia es que Núñez Fernández se centra en pymes, mientras que este trabajo fija el contexto en un laboratorio académico reproducible.

Stevens et al. concluyen que los playbooks comunitarios suelen requerir adaptación antes de ser operativos (Stevens et al., 2022). El playbook E2E de este TFM confirma esa observación: la adaptación al contexto (simulación de contención, umbral de score ajustable, integraciones mock) fue necesaria para lograr la tasa de éxito del 100 %.

#### 4.1.3.6. Limitaciones

Las limitaciones principales son la validación en laboratorio (no en producción real) y el alcance restringido a ransomware. La dependencia de APIs externas (DShield, Mnemonic pDNS) requiere estrategias de caché para entornos productivos. Los resultados muestran que el laboratorio cumple los requisitos definidos y puede emplearse como base reproducible para respuesta automatizada a ransomware.

---

## Índice de Figuras del Capítulo 4

| Figura    | Título                                          | Archivo                                    |
|-----------|-------------------------------------------------|--------------------------------------------|
| Figura 3 | Arquitectura General del Laboratorio SOAR      | Anexo H (H.2)                              |
| Figura 4 | Diagrama de Despliegue Docker Compose          | Anexo H (H.3)                              |
| Figura 5 | Estado de jobs de Cortex                       | `figures/cortex_job_status.png`            |
| Figura 6 | Resultados de MTTR (manual vs automatizado)    | `figures/Fig5_1_mttr_results.png`          |
| Figura 7 | Tiempos por componente del workflow            | `figures/GE1_component_timings.png`        |
| Figura 8 | Análisis de percentiles MTTR (Grafana)         | `figures/grafana_panel_5_..._Percentiles_MTTR.png` |
| Figura 9 | Distribución de decisiones del playbook        | `figures/decision_distribution.png`        |
| Figura 10 | Distribución de mejoras por categoría          | `figures/Fig5_2_improvements_category.png` |

## Índice de Tablas del Capítulo 4

| Tabla    | Título                                          |
|----------|-------------------------------------------------|
| Tabla 4  | Requisitos Funcionales vs No Funcionales        |
| Tabla 5  | Analyzers Cortex Configurados                   |
| Tabla 6  | Configuración de Recursos Docker                |
| Tabla 7  | Métricas de Monitoreo Implementadas             |
| Tabla 8  | Resultados Experimentales Detallados            |
| Tabla 9  | Análisis por Componente de Tiempo               |
