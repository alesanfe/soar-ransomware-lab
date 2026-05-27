# Guía de Troubleshooting del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
  - [1.1 Objetivo](#11-objetivo)
  - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
  - [2.1 Qué cubre](#21-qué-cubre)
  - [2.2 Límites](#22-límites)
  - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
  - [3.1 Problemas comunes de Docker](#31-problemas-comunes-de-docker)
    - [3.1.1 Docker daemon not running](#311-docker-daemon-not-running)
    - [3.1.2 Puertos bloqueados](#312-puertos-bloqueados)
    - [3.1.3 Recursos insuficientes](#313-recursos-insuficientes)
    - [3.1.4 Imágenes no disponibles](#314-imágenes-no-disponibles)
  - [3.2 Problemas de servicios](#32-problemas-de-servicios)
    - [3.2.1 Elasticsearch no inicia](#321-elasticsearch-no-inicia)
    - [3.2.2 TheHive no responde](#322-thehive-no-responde)
    - [3.2.3 Cortex analyzers fallan](#323-cortex-analyzers-fallan)
    - [3.2.4 Shuffle workflows fallan](#324-shuffle-workflows-fallan)
  - [3.3 Problemas de integración](#33-problemas-de-integración)
    - [3.3.1 Integración Shuffle → TheHive rota](#331-integración-shuffle--thehive-rota)
    - [3.3.2 Integración Shuffle → Cortex rota](#332-integración-shuffle--cortex-rota)
    - [3.3.3 Webhooks no funcionan](#333-webhooks-no-funcionan)
  - [3.4 Problemas de rendimiento](#34-problemas-de-rendimiento)
    - [3.4.1 Tiempo de respuesta excesivo](#341-tiempo-de-respuesta-excesivo)
    - [3.4.2 Alto uso de CPU/Memoria](#342-alto-uso-de-cpu-memoria)
    - [3.4.3 MISP lento en arranque](#343-misp-lento-en-arranque)
  - [3.5 Recursos de soporte](#35-recursos-de-soporte)
    - [3.5.1 Logs de servicios](#351-logs-de-servicios)
    - [3.5.2 Comandos de diagnóstico](#352-comandos-de-diagnóstico)
    - [3.5.3 Documentación oficial](#353-documentación-oficial)
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

Esta guía proporciona soluciones a problemas comunes que pueden surgir durante la operación del SOAR Ransomware Lab.

### 1.2 Contexto

El laboratorio SOAR Ransomware Lab integra múltiples servicios que pueden presentar problemas de configuración, integración o rendimiento. Esta guía cubre los problemas más frecuentes y sus soluciones.

## 2. Alcance

### 2.1 Qué cubre

Esta guía cubre:
- Problemas comunes de Docker y Docker Compose
- Problemas de inicio y configuración de servicios
- Problemas de integración entre servicios
- Problemas de rendimiento y recursos
- Recursos de soporte adicionales

### 2.2 Límites

Esta guía no cubre:
- Problemas específicos de cada servicio no documentados
- Configuración avanzada de servicios
- Problemas de hardware o red externos
- Problemas de seguridad de producción

### 2.3 Dependencias

Esta guía depende de:
- [configuration_manual.md](configuration_manual.md) - Manual de configuración completo
- [architecture/docker_architecture.md](../architecture/docker_architecture.md) - Arquitectura Docker detallada
- [user_guide.md](../getting_started/user_guide.md) - Guía de usuario

## 3. Contenido principal

### 3.1 Problemas comunes de Docker

#### 3.1.1 Docker daemon not running

**Síntoma**: Error al ejecutar comandos de Docker

**Solución**:
```bash
# Windows: Iniciar Docker Desktop
# Linux: Iniciar servicio Docker
sudo systemctl start docker

# Verificar estado
docker ps
```

#### 3.1.2 Puertos bloqueados

**Síntoma**: Error al iniciar servicios debido a puertos en uso

**Solución**:
```bash
# Verificar puertos en uso
netstat -tuln | grep LISTEN

# Cambiar puertos en .env.full si es necesario
# Ejemplo: THEHIVE_HTTP_PORT=9001
```

#### 3.1.3 Recursos insuficientes

**Síntoma**: Servicios se cierran o fallan al iniciar

**Solución**:
- Aumentar RAM disponible (mínimo 8GB, recomendado 16GB)
- Ajustar límites de recursos en docker-compose.yml
- Desactivar servicios no críticos (MISP, Wazuh)

#### 3.1.4 Imágenes no disponibles

**Síntoma**: Error al descargar imágenes Docker

**Solución**:
```bash
# Verificar conexión a Docker Hub
docker pull hello-world

# Usar VPN si hay bloqueo LaLiga/Cloudflare
# Pre-descargar imágenes cuando no hay bloqueo
docker pull thehiveproject/thehive:latest
docker pull cortexproject/cortex:latest
docker pull shuffler/shuffle:latest
```

### 3.2 Problemas de servicios

#### 3.2.1 Elasticsearch no inicia

**Síntoma**: Elasticsearch falla al iniciar

**Solución**:
```bash
# Verificar logs
docker logs soar_elasticsearch

# Verificar memoria disponible
free -h

# Aumentar heap size en docker-compose.yml
# ES_JAVA_OPTS=-Xms512m -Xmx512m
```

#### 3.2.2 TheHive no responde

**Síntoma**: TheHive no es accesible vía web

**Solución**:
```bash
# Verificar logs
docker logs soar_thehive

# Verificar estado del servicio
docker ps | grep thehive

# Reiniciar servicio
docker restart soar_thehive
```

#### 3.2.3 Cortex analyzers fallan

**Síntoma**: Analyzers de Cortex no se ejecutan o fallan

**Solución**:
```bash
# Verificar logs de Cortex
docker logs soar_cortex

# Verificar configuración de analyzers
# Acceder a http://localhost:9001/#/organization/analyzer

# Verificar API keys de servicios externos
# (VirusTotal, Shodan, etc.)
```

#### 3.2.4 Shuffle workflows fallan

**Síntoma**: Workflows de Shuffle se quedan en "Step is still running"

**Solución**:
```bash
# Verificar logs de Shuffle
docker logs soar_shuffle_backend

# Verificar logs de orborus
docker logs soar_orborus

# Verificar conexión a redes Docker
docker network inspect soar_net

# Reiniciar servicios
docker restart soar_shuffle_backend soar_orborus
```

#### 3.2.5 Docs Site no inicia

**Síntoma**: Contenedor `soar_docs_site` se reinicia continuamente

**Solución**:
```bash
# Verificar logs de docs-site
docker logs soar_docs_site --tail 50

# Error común: IDs de documentos en sidebars.js no coinciden con archivos reales
# Verificar que los archivos en docs/thesis/ coinciden con sidebars.js

# Si hay error de IDs, reconstruir el contenedor
docker-compose -f infra/docker/compose/docker-compose.yml -f infra/docker/compose/docker-compose.core.yml -f infra/docker/compose/docker-compose.misp.yml -f infra/docker/compose/docker-compose.wazuh.yml -f infra/docker/compose/docker-compose.api.yml -f infra/docker/compose/logging/docker-compose.logging.yml --env-file .env.full up -d --build docs-site
```

### 3.3 Problemas de integración

#### 3.3.1 Integración Shuffle → TheHive rota

**Síntoma**: Error al crear casos en TheHive desde Shuffle

**Solución**:
- Verificar API Key de TheHive en Shuffle
- Verificar URL de TheHive en configuración de Shuffle
- Validar esquema de datos del caso
- Ejecutar tests de contrato en `tests/integration/`

#### 3.3.2 Integración Shuffle → Cortex rota

**Síntoma**: Error al ejecutar analyzers desde Shuffle

**Solución**:
- Verificar API Key de Cortex en Shuffle
- Verificar URL de Cortex en configuración de Shuffle
- Validar que los analyzers estén habilitados en Cortex
- Verificar que los analyzers necesarios estén instalados

#### 3.3.3 Webhooks no funcionan

**Síntoma**: Webhooks no se reciben o procesan

**Solución**:
- Verificar configuración de webhooks en Shuffle
- Verificar que el puerto del webhook esté abierto
- Validar el token de autenticación
- Verificar logs de Shuffle para errores de webhook

### 3.4 Problemas de rendimiento

#### 3.4.1 Tiempo de respuesta excesivo

**Síntoma**: Playbook E2E tarda más de 180s (p90)

**Solución**:
- Reducir número de analyzers activos
- Priorizar analyzers offline (FileInfo, DomainMailSPFRecord)
- Aumentar timeout en configuración de Cortex
- Verificar uso de recursos del host

#### 3.4.2 Alto uso de CPU/Memoria

**Síntoma**: Host se vuelve lento o inestable

**Solución**:
- Verificar uso de recursos por contenedor
```bash
docker stats
```
- Ajustar límites de recursos en docker-compose.yml
- Desactivar servicios no críticos
- Aumentar recursos del host si es posible

#### 3.4.3 MISP lento en arranque

**Síntoma**: MISP tarda más de 3 minutos en iniciar

**Solución**:
- Este comportamiento es conocido y documentado
- `depends_on: condition: service_healthy` configurado
- Esperar a que MISP esté healthy antes de ejecutar workflows
- Documentado en README.md

### 3.5 Recursos de soporte

#### 3.5.1 Logs de servicios

```bash
# Ver logs de todos los servicios
docker logs soar_thehive
docker logs soar_cortex
docker logs soar_shuffle
docker logs soar_orborus
docker logs soar_elasticsearch
docker logs soar_misp
```

#### 3.5.2 Comandos de diagnóstico

```bash
# Ver estado de contenedores
docker ps -a

# Ver uso de recursos
docker stats

# Ver redes Docker
docker network ls
docker network inspect soar_net

# Ver volúmenes Docker
docker volume ls
```

#### 3.5.3 Documentación oficial

- **Docker**: https://docs.docker.com/
- **Shuffle**: https://shuffler.io/docs
- **TheHive**: https://docs.strangebee.com/thehive/
- **Cortex**: https://docs.strangebee.com/cortex/
- **MISP**: https://www.misp-project.org/documentation/
- **Wazuh**: https://documentation.wazuh.com/
- **Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html

## 4. Validación

### 4.1 Verificación

La solución de un problema se considera exitosa cuando:
- El servicio o funcionalidad afectado se restaura
- Los logs no muestran errores críticos
- El playbook E2E se ejecuta sin errores
- Las métricas de rendimiento cumplen los umbrales

### 4.2 Criterios de aceptación

El troubleshooting se considera aceptado cuando:
- El problema se resuelve sin afectar otros servicios
- La solución se documenta para futuras referencias
- Se identifican las causas raíz del problema
- Se implementan medidas preventivas

### 4.3 Evidencias

Las evidencias de solución exitosa incluyen:
- Logs de servicios sin errores
- Ejecuciones exitosas de workflows
- Métricas de rendimiento dentro de umbrales
- Documentación de la solución aplicada

## 5. Problemas y consideraciones

### 5.1 Limitaciones

**Limitaciones de la Guía:**
- No cubre todos los problemas posibles
- Las soluciones pueden variar según el entorno
- Algunos problemas requieren conocimientos avanzados

### 5.2 Riesgos o incidencias

**Riesgos de Troubleshooting:**
- Modificaciones de configuración pueden afectar otros servicios
- Reiniciar servicios puede causar pérdida de datos no persistidos
- Cambios en red pueden afectar conectividad

### 5.3 Recomendaciones / troubleshooting

**Recomendaciones:**
- Documentar todas las modificaciones de configuración
- Realizar backups antes de cambios importantes
- Probar soluciones en entorno de prueba primero
- Mantener actualizada la documentación del problema

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Docker**: https://docs.docker.com/
- **Documentación de Docker Compose**: https://docs.docker.com/compose/
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
