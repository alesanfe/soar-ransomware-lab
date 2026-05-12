# Laboratorio SOAR para Respuesta ante Ransomware

**Trabajo Fin de Máster (TFM) - Máster en Ciberseguridad**

Este repositorio contiene la **Infraestructura como Código (IaC)** completa y los scripts necesarios para implementar un laboratorio **SOAR (Security Orchestration, Automation and Response)** especializado en la respuesta ante incidentes de ransomware. El laboratorio integra múltiples herramientas de seguridad desplegadas mediante **Docker**, con suites de pruebas completas y automatización mediante **Makefile**.

> ⚠️ **Advertencia**: Este laboratorio está diseñado exclusivamente para entornos de pruebas y formación académica. No se recomienda su uso en entornos de producción sin aplicar las guías oficiales y medidas de seguridad adicionales.

---

## 🎯 Objetivos del Laboratorio

- Simular incidentes de ransomware en un entorno controlado y seguro
- Automatizar la respuesta mediante **playbooks SOAR** con múltiples orquestadores
- Reducir el Tiempo Medio de Respuesta (**MTTR**) y mejorar la trazabilidad
- Proporcionar un entorno reproducible para pruebas y formación en ciberseguridad
- Validar la eficacia de la orquestación automatizada en incidentes reales
- Integrar herramientas de Threat Intelligence para análisis automatizado

---

## 🏗️ Arquitectura General

```mermaid
flowchart LR
  SIEM[(SIEM/XDR)] -- Webhook/Feeder --> Shuffle
  Shuffle -- API --> TheHive
  TheHive -- Observables --> Cortex
  Cortex -- Analyzers --> TI[(Threat Intel)]
  Shuffle -- Responder/API --> EDR[(EDR/Defender for Endpoint)]
  subgraph Monitoring
    Prometheus[Prometheus]
    Grafana[Grafana]
    InfluxDB[InfluxDB]
    Telegraf[Telegraf]
  end
  subgraph Threat Intelligence
    MISP[MISP]
    OpenCTI[OpenCTI]
    Redis[Redis]
  end
  subgraph Storage
    MinIO[MinIO]
    NFS[NFS Server]
  end
  TheHive <--> Postgres
  Cortex <--> Redis
  Shuffle <--> Elasticsearch
  Prometheus --> Grafana
  Telegraf --> InfluxDB
  MISP --> Redis
  OpenCTI --> Elasticsearch
```

**Componentes Principales:**
- **Shuffle**: Orquestador principal, recibiendo alertas y ejecutando flujos automatizados
- **TheHive**: Gestiona casos de incidentes y evidencias forenses
- **Cortex**: Analiza Indicadores de Compromiso (IoCs) mediante analyzers especializados
- **MISP**: Plataforma de Threat Intelligence para compartir IoCs
- **OpenCTI**: Plataforma de Threat Intelligence moderna con análisis avanzado
- **Prometheus/Grafana**: Stack de monitorización de métricas
- **Elasticsearch**: Motor de búsqueda y análisis para logs
- **MinIO**: Almacenamiento de objetos compatible S3
- **PostgreSQL** y **Redis**: Servicios de soporte para persistencia y caché

---

## 📁 Estructura del Repositorio

```
soar-ransomware-lab/
├── README.md                    # Documentación principal del proyecto
├── LICENSE                      # Licencia del proyecto
├── Makefile                     # Comandos rápidos: up/down/test/metrics
├── pyproject.toml               # Configuración de proyecto Python
├── pytest.ini                  # Configuración de pytest
├── requirements-test.txt         # Dependencias para testing
├── .gitignore                  # Archivos ignorados por git
├── .env.full                   # Variables de entorno completas
├── CHANGELOG.md                # Historial de cambios
├── CONTRIBUTING.md              # Guía de contribución
├── apps/                       # Aplicaciones Docker
│   ├── api/                   # API REST del proyecto
│   ├── docs-site/              # Sitio de documentación
│   └── web-management/         # Interfaz web de gestión
├── infra/                      # Infraestructura como código
│   ├── docker/                # Configuración Docker Compose
│   │   ├── docker-compose.yml  # Stack completo SOAR
│   │   └── nginx.conf         # Configuración reverse proxy
│   ├── logging/               # Configuración ELK stack
│   ├── monitoring/            # Configuración Prometheus/Grafana
│   └── vagrant/              # Automatización opcional con Vagrant
├── src/soar_lab/             # Código fuente principal
│   ├── analytics/             # Módulos de análisis de datos
│   ├── api/                   # API FastAPI
│   ├── config/                # Configuración y esquemas
│   ├── data/                  # Gestión de datos y KPIs
│   ├── schemas/               # Esquemas de validación
│   └── services/              # Servicios principales
├── scripts/                    # Scripts de automatización
│   ├── infra/                # Scripts de infraestructura
│   ├── security/              # Scripts de seguridad
│   ├── testing/               # Scripts de testing
│   └── utils/                # Scripts de utilidad y migración
├── tests/                      # Suite de pruebas completa
│   ├── unit/                  # Pruebas unitarias
│   ├── integration/           # Pruebas de integración
│   ├── e2e/                  # Pruebas end-to-end
│   ├── performance/           # Pruebas de rendimiento
│   ├── security/              # Pruebas de seguridad
│   ├── atomic/                # Pruebas atómicas
│   ├── browser/               # Pruebas de navegador
│   ├── fixtures/              # Datos de prueba y fixtures
│   └── runners/               # Scripts de ejecución de pruebas
├── docs/                       # Documentación completa
│   ├── architecture/          # Documentación de arquitectura
│   ├── operations/            # Guías operativas
│   ├── references/            # Referencias y esquemas
│   ├── security/              # Documentación de seguridad
│   └── user-guide/            # Guía de usuario
└── artifacts/                  # Artefactos generados
    ├── backups/               # Copias de seguridad
    ├── coverage/              # Reportes de cobertura
    ├── debug/                 # Scripts de debug
    ├── logs/                  # Logs de ejecución
    └── results/               # Resultados de pruebas
```

---

## 📚 Documentación del Proyecto

Este proyecto incluye documentación académica completa estructurada según las directrices de Trabajo Fin de Máster (TFM):

### 1. Documentación Fundamental del TFM
1. **[Alcance del Proyecto](docs/scope.md)** - Definición de qué incluye y excluye el TFM
2. **[Objetivos SMART](docs/objectives.md)** - Objetivos medibles con ubicación de evidencias
3. **[Planificación del Proyecto](docs/plan.md)** - Cronograma, hitos y ruta crítica
4. **[Análisis de Riesgos](docs/risks.md)** - Riesgos técnicos y temporales con mitigaciones

### 2. Documentación Técnica y Arquitectónica
5. **[Arquitectura](docs/architecture.md)** - Diseño detallado del sistema y relaciones entre componentes
6. **[Integraciones de APIs](docs/api.md)** - APIs reales vs simuladas con detalles de configuración
7. **[Guía Técnica](docs/technical.md)** - Configuración completa, despliegue y resolución de problemas
8. **[Manual del Playbook](docs/playbook_manual.md)** - Documentación detallada del flujo en Shuffle

### 3. Resultados y Análisis del Proyecto
9. **[Informe de Pruebas](docs/test_report.md)** - Resultados de pruebas E2E, KPIs y análisis de rendimiento
10. **[Cierre del Proyecto](docs/closure.md)** - Lecciones aprendidas y recomendaciones futuras
11. **[Guía de Seguridad](docs/security.md)** - Mejores prácticas de seguridad y checklist

### 4. Guías de Usuario y Operativas
12. **[Guía de Usuario](docs/user_guide.md)** - Manual completo de operación del laboratorio
13. **[Resolución de Problemas](docs/troubleshooting.md)** - Guía completa de diagnóstico y soluciones

### 5. Documentación de Mejoras Implementadas
14. **[Análisis de Mejoras](docs/improvement_recommendations.md)** - Análisis completo de 44 mejoras identificadas
15. **[Implementación de Mejoras](docs/improvements_implementation.md)** - Documentación de todas las mejoras implementadas
16. **[Reporte Final de Implementación](docs/final_implementation_report.md)** - Reporte completo del proyecto transformado

### 6. Documentación API y Desarrollo
17. **[Documentación API](docs/api.md)** - Documentación completa de endpoints REST
18. **[Guía de Contribución](CONTRIBUTING.md)** - Guía para desarrolladores y contribuidores
19. **[CHANGELOG](CHANGELOG.md)** - Historial de cambios y versiones del proyecto

### 7. Archivos de Configuración y Plantillas
20. **[Plantilla TheHive](docs/thehive_template.json)** - Plantilla de casos para incidentes de ransomware
21. **[Analyzers Cortex](docs/cortex_analyzers.md)** - Configuración y documentación de analyzers

---

## 🚀 Instalación Rápida

### Requisitos Previos
- Docker Engine 20.10+
- Docker Compose 2.0+
- Python 3.8+
- 8GB+ RAM (16GB+ recomendado)
- 50GB+ SSD (100GB+ recomendado)

### Pasos de Instalación

1. **Configurar Variables de Entorno**:
   ```bash
   # Copiar plantilla de configuración
   cp infra/docker/.env.example infra/docker/.env
   
   # Editar configuración con credenciales seguras
   nano infra/docker/.env
   ```

2. **Generar Certificados TLS**:
   ```bash
   # Generar certificados autofirmados
   ./scripts/gen_certs.sh
   ```

3. **Iniciar Servicios**:
   ```bash
   # Iniciar todos los servicios
   make up
   
   # Verificar estado de los contenedores
   docker compose ps
   ```

4. **Detener Servicios**:
   ```bash
   # Detener todos los servicios
   make down
   ```

---

## 🔧 Automatización Opcional

### Vagrant
```bash
# Crear entorno automatizado
vagrant up

# Incluir máquina Windows opcional
vagrant up windows
```

### Ansible
```bash
# Despliegue en múltiples hosts
ansible-playbook -i ansible/inventory.ini ansible/playbook.yml
```

---

## 🛡️ Buenas Prácticas

- No subir archivos `.env` ni certificados al repositorio (usar `.gitignore`)
- Documentar pruebas en `tests/e2e` y resultados en `docs/test_report.md`
- Utilizar TLS y credenciales seguras en todo momento
- Realizar copias de seguridad periódicas de la configuración
- Mantener actualizadas las dependencias y Docker images

---

## 📊 Métricas y Pruebas

### Ejecución de Pruebas
Para ejecutar pruebas, consultar la documentación completa en **[docs/tests.md](docs/tests.md)**:

```bash
# Ejecutar todas las pruebas
make test-all

# Ejecutar categorías específicas
make test-unit
make test-atomic
make test-security
make test-integration
make test-performance
make test-e2e

# Ejecutar con cobertura (mínimo 80% requerido)
make test-coverage

# Enviar alerta maliciosa de prueba
python3 scripts/send_alert.py --type malicious --single

# Enviar alerta benigna de prueba
python3 scripts/send_alert.py --type benign --single
```

### Cálculo de KPIs
```bash
# Calcular métricas MTTR
make metrics

# Análisis completo con generación de datos
make metrics-full

# Ver resultados
cat artifacts/results/kpis.csv
```

### Análisis de Datos
```bash
# Ver estado de datos disponibles
make data-status

# Generar análisis completo
make data-generate

# Ver todos los datos disponibles
make data-view

# Monitorear cambios en tiempo real
make data-watch
```

### Análisis de Resultados
- Documentar resultados en `artifacts/results/kpis.csv` y `docs/test_report.md`
- Verificar cumplimiento de umbrales: p50 ≤ 120s, p90 ≤ 180s
- Analizar logs de ejecución en `artifacts/logs/notify.log`
- Ver documentación completa de pruebas en **[docs/tests.md](docs/tests.md)**

---

## 🎓 Contexto Académico

Este laboratorio SOAR ha sido desarrollado como **Trabajo Fin de Máster** en el área de ciberseguridad, cumpliendo con los siguientes objetivos académicos:

- **Aplicación Práctica**: Implementación de conceptos teóricos de SOAR en entorno realista
- **Investigación Aplicada**: Validación de la eficacia de la automatización en respuesta a incidentes
- **Innovación Tecnológica**: Desarrollo de un laboratorio reproducible para formación especializada
- **Contribución Académica**: Creación de recursos educativos reutilizables

---

## 🔗 Referencias Clave

### Documentación Oficial
- [TheHive Docker](https://docs.strangebee.com/thehive/installation/docker/)
- [Cortex Analyzers](https://docs.strangebee.com/cortex/)
- [Shuffle SOAR](https://shuffler.io/docs)

### Tecnologías Utilizadas
- [Docker Volumes](https://docs.docker.com/engine/storage/volumes/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres/)
- [Redis Docker](https://hub.docker.com/_/redis/)
- [Docker Compose](https://docs.docker.com/compose/)

---

## 📄 Licencia y Uso

Este proyecto está licenciado bajo los términos especificados en el archivo `LICENSE`. El uso académico y educativo está fomentado, siempre que se cite adecuadamente la fuente.

---

**Autor**: [Nombre del Autor]  
**Director/a**: [Nombre del Director/a]  
**Universidad**: [Nombre de la Universidad]  
**Año Académico**: 2024-2025  
**Versión**: 1.3.0
