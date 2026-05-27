# Guía de Instalación del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
  - [1.1 Objetivo](#11-objetivo)
  - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
  - [2.1 Qué cubre](#21-qué-cubre)
  - [2.2 Límites](#22-límites)
  - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 Requisitos previos](#31-requisitos-previos)
    - [3.1.1 Requisitos de hardware](#311-requisitos-de-hardware)
    - [3.1.2 Requisitos de software](#312-requisitos-de-software)
    - [3.1.3 Verificación de instalación](#313-verificación-de-instalación)
  - [3.2 Proceso de instalación](#32-proceso-de-instalación)
    - [3.2.1 Clonar el repositorio](#321-clonar-el-repositorio)
    - [3.2.2 Configurar variables de entorno](#322-configurar-variables-de-entorno)
    - [3.2.3 Desplegar el stack completo](#323-desplegar-el-stack-completo)
    - [3.2.4 Verificar estado de servicios](#324-verificar-estado-de-servicios)
  - [3.3 Configuración inicial](#33-configuración-inicial)
    - [3.3.1 Configuración de Shuffle](#331-configuración-de-shuffle)
    - [3.3.2 Configuración de TheHive](#332-configuración-de-thehive)
    - [3.3.3 Configuración de Cortex](#333-configuración-de-cortex)
  - [3.4 Verificación de instalación](#34-verificación-de-instalación)
    - [3.4.1 Verificación de servicios](#341-verificación-de-servicios)
    - [3.4.2 Verificación de integraciones](#342-verificación-de-integraciones)
  - [3.5 Solución de problemas](#35-solución-de-problemas)
    - [3.5.1 Docker daemon not running](#351-docker-daemon-not-running)
    - [3.5.2 Puertos bloqueados](#352-puertos-bloqueados)
    - [3.5.3 Recursos insuficientes](#353-recursos-insuficientes)
- [4. Validación](#4-validación)
  - [4.1 Verificación](#41-verificación)
  - [4.2 Criterios de aceptación](#42-criterios-de-aceptación)
  - [4.3 Evidencias](#43-evidencias)
- [5. Problemas y consideraciones](#5-problemas-y-consideraciones)
  - [5.1 Limitaciones](#51-limitaciones)
  - [5.2 Riesgos o incidencias](#52-riesgos-o-incidencias)
  - [5.3 Recomendaciones / troubleshooting](#53-recomendaciones--troubleshooting)
- [6. Referencias](#6-referencias)

---

## 1. Resumen

### 1.1 Objetivo

Esta guía proporciona instrucciones paso a paso para instalar y configurar el SOAR Ransomware Lab en tu entorno local.

### 1.2 Contexto

El laboratorio SOAR Ransomware Lab se basa en Docker Compose para desplegar múltiples servicios de seguridad orquestación (SOAR) en un entorno controlado. Esta guía asume que tienes conocimientos básicos de Docker y línea de comandos.

## 2. Alcance

### 2.1 Qué cubre

Esta guía cubre:
- Requisitos de hardware y software
- Instalación de dependencias
- Clonación del repositorio
- Configuración de variables de entorno
- Despliegue del stack con Docker Compose
- Verificación de la instalación

### 2.2 Límites

Esta guía no cubre:
- Configuración avanzada de cada servicio
- Integración con sistemas externos
- Despliegue en entornos de producción
- Hardening de seguridad adicional

### 2.3 Dependencias

Esta guía depende de:
- [overview.md](overview.md) - Visión general del laboratorio
- [user_guide.md](user_guide.md) - Guía de usuario detallada
- [architecture/docker_architecture.md](../architecture/docker_architecture.md) - Arquitectura Docker detallada

## 3. Contenido principal

### 3.1 Requisitos previos

#### 3.1.1 Requisitos de hardware

- **RAM**: 16GB+ (mínimo 8GB)
- **CPU**: 4 cores+ (mínimo 2 cores)
- **Disco**: 50GB+ SSD

#### 3.1.2 Requisitos de software

- **Docker Engine**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+
- **Git**: para clonar el repositorio

#### 3.1.3 Verificación de instalación

```bash
docker --version
docker-compose --version
python --version
git --version
```

### 3.2 Proceso de instalación

#### 3.2.1 Clonar el repositorio

```bash
git clone https://github.com/alesanfe/soar-ransomware-lab.git
cd soar-ransomware-lab
```

#### 3.2.2 Configurar variables de entorno

Editar el archivo `.env.full` con las credenciales necesarias:

```bash
nano .env.full
```

Variables importantes a configurar:
- `ELASTIC_PASSWORD`: Contraseña de Elasticsearch
- `REDIS_PASSWORD`: Contraseña de Redis
- `SHUFFLE_DEFAULT_USERNAME`: Usuario admin de Shuffle
- `SHUFFLE_DEFAULT_PASSWORD`: Contraseña admin de Shuffle
- `THEHIVE_SECRET`: Secret de TheHive

#### 3.2.3 Desplegar el stack completo

```bash
make up
```

Este comando despliega todos los servicios definidos en los archivos Docker Compose:
- Elasticsearch, Redis, TheHive, Cortex
- Shuffle (frontend + backend + orborus)
- MISP, MISP DB, MISP Modules
- Wazuh Manager, Kibana
- Lab API, Docs Site, Web Management, Nginx
- Grafana, Grafana DB, Loki, Promtail (logging stack)

**Nota:** El comando `make up` usa el archivo `.env.full` para configuración de variables de entorno.

#### 3.2.4 Verificar estado de servicios

```bash
docker ps
```

### 3.3 Configuración inicial

#### 3.3.1 Configuración de Shuffle

1. Acceder a Shuffle: https://localhost:3001/
2. Iniciar sesión con credenciales configuradas
3. Registrar las apps de TheHive, Cortex y otras integraciones
4. Crear el workflow de respuesta a ransomware

#### 3.3.2 Configuración de TheHive

1. Acceder a TheHive: http://localhost:9000/
2. Iniciar sesión con credenciales configuradas
3. Configurar usuarios y organizaciones
4. Configurar alertas y webhooks

#### 3.3.3 Configuración de Cortex

1. Acceder a Cortex: http://localhost:9001/
2. Iniciar sesión con credenciales configuradas
3. Configurar analyzers
4. Configurar API keys para servicios externos (opcional)

### 3.4 Verificación de instalación

#### 3.4.1 Verificación de servicios

```bash
# Verificar Elasticsearch
curl -u elastic:YOUR_PASSWORD http://localhost:9200/_cluster/health

# Verificar TheHive
curl http://localhost:9000/api/status

# Verificar Cortex
curl http://localhost:9001/api/status

# Verificar Shuffle
curl https://localhost:3001/api/v1/status
```

#### 3.4.2 Verificación de integraciones

- Ejecutar el playbook de prueba E2E
- Verificar que se crean casos en TheHive
- Verificar que se ejecutan analyzers en Cortex
- Verificar que los workflows de Shuffle se ejecutan correctamente

### 3.5 Solución de problemas

#### 3.5.1 Docker daemon not running

**Síntoma**: Error al ejecutar comandos de Docker

**Solución**:
```bash
# Iniciar Docker Desktop (Windows)
# O iniciar servicio Docker (Linux)
sudo systemctl start docker
```

#### 3.5.2 Puertos bloqueados

**Síntoma**: Error al iniciar servicios debido a puertos en uso

**Solución**:
```bash
# Verificar puertos en uso
netstat -tuln | grep LISTEN

# Cambiar puertos en .env.full si es necesario
```

#### 3.5.3 Recursos insuficientes

**Síntoma**: Servicios se cierran o fallan al iniciar

**Solución**:
- Aumentar RAM disponible
- Ajustar límites de recursos en docker-compose.yml
- Desactivar servicios no críticos

## 4. Validación

### 4.1 Verificación

La instalación se considera exitosa cuando:
- Todos los servicios se inician y reportan estado healthy
- Los servicios son accesibles en sus puertos esperados
- Las integraciones básicas funcionan correctamente

### 4.2 Criterios de aceptación

La instalación se considera aceptada cuando:
- El stack completo se despliega sin errores
- Todos los servicios son accesibles vía web o API
- Las credenciales configuradas funcionan correctamente
- El playbook E2E se ejecuta sin errores

### 4.3 Evidencias

Las evidencias de instalación exitosa incluyen:
- Logs de contenedores sin errores críticos
- Acceso web a todos los servicios
- Ejecución exitosa del playbook E2E
- Métricas de rendimiento dentro de umbrales

## 5. Problemas y consideraciones

### 5.1 Limitaciones

**Limitaciones de la Guía:**
- Asume entorno Windows + Docker Desktop
- No cubre configuración avanzada
- No cubre integración con sistemas externos

### 5.2 Riesgos o incidencias

**Riesgos de Instalación:**
- Dependencia de servicios externos (Docker Hub)
- Conflictos de puertos con otros servicios
- Requisitos de recursos no cumplidos

### 5.3 Recomendaciones / troubleshooting

**Recomendaciones:**
- Leer la documentación oficial de cada herramienta
- Verificar requisitos antes de instalar
- Usar entornos aislados para pruebas
- Mantener actualizaciones de seguridad

**Recursos de Soporte:**
- Documentación oficial de Docker: https://docs.docker.com/
- Documentación de Shuffle: https://shuffler.io/docs
- Documentación de TheHive: https://docs.strangebee.com/thehive/
- Documentación de Cortex: https://docs.strangebee.com/cortex/

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Docker**: https://docs.docker.com/
- **Documentación de Docker Compose**: https://docs.docker.com/compose/
