# Estrategia de Pruebas de Docker - Validación Completa del Entorno

## Índice

- [1. Resumen](#1-resumen)
  - [1.1 Objetivo](#11-objetivo)
  - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
  - [2.1 Qué cubre](#21-qué-cubre)
  - [2.2 Límites](#22-límites)
  - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 Estrategia de pruebas](#31-estrategia-de-pruebas)
    - [3.1.1 Niveles de pruebas](#311-niveles-de-pruebas)
    - [3.1.2 Fases de ejecución](#312-fases-de-ejecución)
  - [3.2 Tipos de pruebas](#32-tipos-de-pruebas)
    - [3.2.1 Fase 1: pruebas de configuración](#321-fase-1-pruebas-de-configuración)
    - [3.2.2 Fase 2: pruebas de runtime](#322-fase-2-pruebas-de-runtime)
    - [3.2.3 Fase 3: pruebas de navegador](#323-fase-3-pruebas-de-navegador)
  - [3.3 Herramientas y frameworks](#33-herramientas-y-frameworks)
    - [3.3.1 Cobertura de servicios](#331-cobertura-de-servicios)
    - [3.3.2 Validación de red](#332-validación-de-red)
    - [3.3.3 Validación de volúmenes](#333-validación-de-volúmenes)
  - [3.4 Ejecución de pruebas](#34-ejecución-de-pruebas)
    - [3.4.1 Comandos de ejecución](#341-comandos-de-ejecución)
    - [3.4.2 Integración CI/CD](#342-integración-cicd)
  - [3.5 Reportes y métricas](#35-reportes-y-métricas)
    - [3.5.1 Reportes generados](#351-reportes-generados)
    - [3.5.2 Métricas clave](#352-métricas-clave)
- [4. Validación](#4-validación)
  - [4.1 Verificación](#41-verificación)
    - [4.1.1 Validación de health checks](#411-validación-de-health-checks)
    - [4.1.2 Validación de rendimiento](#412-validación-de-rendimiento)
    - [4.1.3 Validación de seguridad](#413-validación-de-seguridad)
  - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
  - [4.3 Evidencias](#43-evidencias)
- [5. Problemas y consideraciones](#5-problemas-y-consideraciones)
  - [5.1 Limitaciones](#51-limitaciones)
    - [5.1.1 Limitaciones de pruebas de configuración](#511-limitaciones-de-pruebas-de-configuración)
    - [5.1.2 Limitaciones de pruebas de runtime](#512-limitaciones-de-pruebas-de-runtime)
    - [5.1.3 Limitaciones de pruebas de navegador](#513-limitaciones-de-pruebas-de-navegador)
  - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
    - [5.2.1 Docker daemon not running](#521-docker-daemon-not-running)
    - [5.2.2 Port conflicts](#522-port-conflicts)
    - [5.2.3 Resource constraints](#523-resource-constraints)
    - [5.2.4 Network connectivity](#524-network-connectivity)
    - [5.2.5 Volume mounting](#525-volume-mounting)
  - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones--troubleshooting)
    - [5.3.1 Comandos de debug](#531-comandos-de-debug)
    - [5.3.2 Integración CI/CD](#532-integración-cicd)
    - [5.3.3 Mejoras futuras](#533-mejoras-futuras)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Este documento describe la estrategia integral de pruebas de Docker para el proyecto SOAR Ransomware Lab, incluyendo validación de configuración y runtime para garantizar que el entorno Docker completo funcione correctamente.

### 1.2 Contexto

La estrategia de pruebas incluye tres niveles: validación de configuración (sin requerir Docker daemon), validación de runtime (con contenedores reales) y validación de navegador/UI (con automatización de navegador). Este enfoque multicapa proporciona confianza en que el entorno Docker funcionará correctamente en producción.

## 2. Alcance

### 2.1 Qué cubre

Este documento cubre:
- Estrategia de pruebas de Docker en tres niveles (configuración, runtime, navegador)
- Validación de servicios SOAR core (Elasticsearch, TheHive, Cortex, Shuffle, Kibana, Wazuh)
- Validación de servicios de threat intelligence (MISP, Redis, MariaDB)
- Validación de redes, volúmenes, health checks, rendimiento y seguridad
- Integración con CI/CD mediante GitHub Actions
- Troubleshooting de problemas comunes
- Mejoras futuras planeadas

### 2.2 Límites

Este documento no cubre:
- Estrategias de seguridad avanzadas del proyecto (ver docs/architecture/security.md)
- Arquitectura detallada del sistema (ver docs/architecture/overview.md)
- Detalle de casos de prueba específicos (ver docs/testing/test_suite.md)
- Guía de usuario para ejecutar pruebas (ver docs/testing/README.md)

### 2.3 Dependencias

Este documento depende de:
- Documentación de arquitectura (docs/architecture/overview.md)
- Documentación de Docker (docs/architecture/docker_architecture.md)
- Guía de pruebas (docs/testing/README.md)
- Especificación de casos de prueba (docs/testing/test_suite.md)

## 3. Contenido principal

### 3.1 Estrategia de pruebas

#### 3.1.1 Niveles de pruebas

**Nivel 1: Validación de Configuración**
- Archivos: `tests/unit/test_docker_services_validation.py`, `tests/unit/test_docker_services_validation_real.py`
- Propósito: Validar configuración de docker-compose.yml sin requerir Docker daemon
- Ventajas: Ejecución rápida, puede ejecutarse en cualquier entorno, amigable para CI/CD
- Limitaciones: No valida inicio real de servicios, conectividad de red real, funcionalidad de servicios

**Nivel 2: Validación de Runtime**
- Archivo: `tests/integration/test_docker_runtime_validation.py`
- Propósito: Validar funcionalidad del entorno Docker real
- Requisitos: Docker daemon ejecutándose, docker-compose disponible, recursos suficientes

**Nivel 3: Validación de Navegador/UI**
- Archivo: `tests/browser/test_live_web_services_validation.py`
- Propósito: Validar interfaces web con automatización de navegador real
- Requisitos: Selenium WebDriver, navegador Chrome/Chromium, servicios Docker ejecutándose

#### 3.1.2 Fases de ejecución

1. **Fase 1**: Pruebas de configuración (siempre ejecutar)
2. **Fase 2**: Pruebas de runtime (cuando Docker esté disponible)
3. **Fase 3**: Pruebas de navegador (cuando los servicios estén ejecutándose)

### 3.2 Tipos de pruebas

#### 3.2.1 Fase 1: pruebas de configuración

```bash
python -m pytest tests/unit/test_docker_services_validation*.py -v
```

- Validación rápida de docker-compose.yml
- Puede ejecutarse durante el desarrollo
- Integración en pipeline CI/CD

#### 3.2.2 Fase 2: pruebas de runtime

```bash
python -m pytest tests/integration/test_docker_runtime_validation.py -v
```

- Validación completa del entorno Docker
- Verificación de inicio de servicios
- Prueba de conectividad de red
- Validación de uso de recursos

#### 3.2.3 Fase 3: pruebas de navegador

```bash
python -m pytest tests/browser/test_live_web_services_validation.py -v
```

- Validación de interfaces web
- Prueba de experiencia de usuario
- Validación de rendimiento y seguridad

### 3.3 Herramientas y frameworks

#### 3.3.1 Cobertura de servicios

### Servicios SOAR Core

| Servicio | Puerto | Configuración | Runtime | Navegador |
|----------|--------|---------------|---------|-----------|
| **Elasticsearch** | 9200 | Imagen, puertos, volúmenes, entorno | Salud del cluster, accesibilidad de API | No aplicable (solo API) |
| **TheHive** | 9000 | Imagen, puertos, volúmenes, redes | Salud del contenedor, endpoints de API | Interfaz de login, UI de gestión de casos |
| **Cortex** | 9001 | Imagen, puertos, volúmenes, redes | Container health, analyzer endpoints | Login interface, analyzer management |
| **Shuffle** | 3001 | Imagen, puertos, volúmenes, redes | Container health, workflow engine | Login interface, workflow builder |
| **Kibana** | 15601 | Imagen, puertos, volúmenes, redes | Dashboard rendering, Elasticsearch integration | Login interface, visualization dashboards |
| **Wazuh Manager** | 55100 | Imagen, puertos, volúmenes, redes | SIEM/XDR functionality, API endpoints | No aplicable (API only) |

### Threat Intelligence

| Servicio | Configuración | Runtime | Navegador |
|----------|---------------|---------|-----------|
| **MISP** | Imagen, puertos, volúmenes, redes | Threat intelligence platform | Login interface, threat data management |
| **Redis** | Imagen, puertos, volúmenes, redes | Cache and message broker | No aplicable (data service) |
| **MariaDB** | Imagen, puertos, volúmenes, redes | Database for TheHive, Cortex, MISP | No aplicable (data service) |

#### 3.3.2 Validación de red

**Redes Esperadas:**
- **soar_edge**: External connectivity
- **soar_net**: Internal service communication

**Pruebas de Red:**
- Network creation and configuration
- Container connectivity within networks
- Inter-network communication rules
- DNS resolution within networks
- Port exposure and routing

#### 3.3.3 Validación de volúmenes

**Volúmenes Esperados:**
- **es_data**: Elasticsearch data persistence
- **thehive_files**: TheHive case files
- **cortex_data**: Cortex analyzer data
- **shuffle_app_storage**: Shuffle workflow apps
- **shuffle_file_storage**: Shuffle workflow files
- **misp_data**: MISP database and files
- **misp_logs**: MISP logs
- **misp_uploads**: MISP file uploads
- **misp_gpg**: MISP GPG keys
- **misp_smime**: MISP S/MIME keys
- **misp_ca**: MISP CA certificates
- **redis_data**: Redis persistence
- **mariadb_data**: MariaDB database persistence

**Pruebas de Volúmenes:**
- Volume creation and mounting
- Data persistence across restarts
- File permissions and ownership
- Backup and restore capabilities

### 3.4 Ejecución de pruebas

#### 3.4.1 Comandos de ejecución

**Ejecutar todas las pruebas:**
```bash
make test
```

**Ejecutar solo pruebas de configuración:**
```bash
python -m pytest tests/unit/test_docker_services_validation*.py -v
```

**Ejecutar solo pruebas de runtime:**
```bash
python -m pytest tests/integration/test_docker_runtime_validation.py -v
```

**Ejecutar solo pruebas de navegador:**
```bash
python -m pytest tests/browser/test_live_web_services_validation.py -v
```

#### 3.4.2 Integración CI/CD

Las pruebas se integran en GitHub Actions mediante workflows en `.github/workflows/`:
- Ejecución automática en cada PR
- Validación de configuración en todas las ramas
- Validación de runtime en rama main
- Reportes de cobertura de código

### 3.5 Reportes y métricas

#### 3.5.1 Reportes generados

- **Reportes pytest**: Resultados de ejecución de pruebas
- **Cobertura de código**: Porcentaje de código cubierto por pruebas
- **Logs de contenedores**: Registros de ejecución de servicios
- **Capturas de pantalla**: Evidencias de pruebas de navegador
- **Métricas de rendimiento**: Tiempos de respuesta, uso de recursos

#### 3.5.2 Métricas clave

| Métrica | Objetivo | Método de Medida |
|---------|----------|-------------------|
| **Tasa de éxito** | ≥ 95% | Porcentaje de pruebas pasadas |
| **Cobertura de código** | ≥ 80% | pytest-cov |
| **Tiempo de ejecución** | ≤ 5 min | pytest --durations |
| **Tiempo de inicio de contenedores** | ≤ 2 min | docker ps + timestamps |

## 4. Validación

### 4.1 Verificación

#### 4.1.1 Validación de health checks

**Métodos de Health Check:**
- Docker native health checks
- HTTP endpoint validation
- TCP port connectivity
- Service-specific health endpoints

**Pruebas de Health Check:**
- Container startup time
- Health check frequency
- Failure detection and recovery
- Health status reporting para servicios core (Elasticsearch, TheHive, Cortex, Shuffle, Kibana, MISP)

#### 4.1.2 Validación de rendimiento

**Métricas Recopiladas:**
- Container startup time
- Memory usage patterns
- CPU utilization
- Network I/O
- Disk I/O
- Response times

**Pruebas de Rendimiento:**
- Resource limit validation
- Performance regression detection
- Scalability testing
- Load testing scenarios

#### 4.1.3 Validación de seguridad

**Headers de Seguridad Probados:**
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Strict-Transport-Security
- Content-Security-Policy

**Pruebas de Seguridad:**
- Authentication endpoint validation
- Authorization testing
- SSL/TLS certificate validation
- Secure communication testing
- Vulnerability scanning integration

### 4.2 Criterios de Aceptación

Las pruebas de Docker se consideran exitosas cuando:
- Todas las pruebas de configuración pasan sin errores
- Todos los contenedores inician correctamente y reportan estado healthy
- Todos los servicios son accesibles en sus puertos esperados
- La comunicación entre servicios funciona correctamente
- Los volúmenes se montan correctamente y persisten datos
- Las interfaces web cargan sin errores de consola
- Los headers de seguridad están configurados correctamente
- Las métricas de rendimiento están dentro de los límites aceptables

### 4.3 Evidencias

Las evidencias de ejecución de pruebas incluyen:
- Reportes de pytest con resultados de pruebas
- Logs de contenedores sin errores críticos
- Capturas de pantalla de interfaces web (para pruebas de navegador)
- Métricas de rendimiento recopiladas
- Reportes de seguridad (headers, vulnerabilidades)

## 5. Problemas y consideraciones

### 5.1 Limitaciones

#### 5.1.1 Limitaciones de pruebas de configuración
- No valida el inicio real de servicios
- No prueba la conectividad de red real
- No valida la funcionalidad de servicios

#### 5.1.2 Limitaciones de pruebas de runtime
- Requiere Docker daemon ejecutándose
- Requiere recursos del sistema suficientes
- Puede ser lento en comparación con pruebas de configuración

#### 5.1.3 Limitaciones de pruebas de navegador
- Requiere instalación de navegador y WebDriver
- Puede ser frágil debido a cambios en UI
- Requiere servicios ejecutándose

### 5.2 Riesgos o incidencias

#### 5.2.1 Docker daemon not running
   - Start Docker service
   - Check Docker permissions
   - Verify Docker installation

#### 5.2.2 Port conflicts
   - Check port availability
   - Update port mappings
   - Stop conflicting services

#### 5.2.3 Resource constraints
   - Check system resources
   - Adjust memory limits
   - Monitor disk space

#### 5.2.4 Network connectivity
   - Verify network creation
   - Check firewall rules
   - Validate DNS resolution

#### 5.2.5 Volume mounting
   - Check volume permissions
   - Verify mount points
   - Validate disk space

### 5.3 Recomendaciones / troubleshooting

#### 5.3.1 Comandos de debug

**Comandos de Debug:**
```bash
# Check Docker status
docker version
docker info

# Check running containers
docker ps
docker-compose ps

# Check container logs
docker logs <container_name>
docker-compose logs <service_name>

# Check network status
docker network ls
docker network inspect <network_name>

# Check volume status
docker volume ls
docker volume inspect <volume_name>

# Check resource usage
docker stats
docker system df
```

#### 5.3.2 Integración CI/CD

**Integración CI/CD:**

La estrategia de pruebas se integra con GitHub Actions mediante tres jobs:
- `docker-config`: Ejecuta pruebas de configuración sin Docker
- `docker-runtime`: Ejecuta pruebas de runtime con Docker-in-Docker
- `browser-tests`: Ejecuta pruebas de navegador con Chrome

#### 5.3.3 Mejoras futuras
1. Multi-platform testing (Windows, Linux, cross-platform)
2. Performance benchmarking (baseline metrics, regression detection)
3. Security scanning (container image vulnerability, network security)
4. Monitoring integration (real-time monitoring, alert integration)
5. Automated remediation (self-healing tests, automatic issue detection)

## 6. Referencias

- **Project Repository**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Docker Documentation**: https://docs.docker.com/
- **Docker Compose Documentation**: https://docs.docker.com/compose/
- **Pytest Documentation**: https://docs.pytest.org/
- **Playwright Documentation**: https://playwright.dev/
- **GitHub Actions Documentation**: https://docs.github.com/en/actions
- **Shuffle Documentation**: https://shuffler.io/docs
- **TheHive Documentation**: https://docs.strangebee.com/thehive/
- **Cortex Documentation**: https://docs.strangebee.com/cortex/
