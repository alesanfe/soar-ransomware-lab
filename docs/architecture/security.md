# Seguridad del SOAR Ransomware Lab

## Índice

- [1. Resumen](#1-resumen)
    - [1.1 Objetivo](#11-objetivo)
    - [1.2 Contexto](#12-contexto)
- [2. Alcance](#2-alcance)
    - [2.1 Qué cubre](#21-qué-cubre)
    - [2.2 Límites](#22-límites)
    - [2.3 Dependencias](#23-dependencias)
- [3. Contenido principal](#3-contenido-principal)
    - [3.1 Principios de seguridad](#31-principios-de-seguridad)
    - [3.2 Modelo de amenazas](#32-modelo-de-amenazas)
    - [3.3 Controles implementados](#33-controles-implementados)
    - [3.4 Cumplimiento y protección de datos](#34-cumplimiento-y-protección-de-datos)
    - [3.5 Diagramas o matrices](#35-diagramas-o-matrices)
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

Este documento describe la estrategia de seguridad defensa en profundidad implementada para proteger contra ataques de
ransomware y garantizar la integridad de las operaciones de seguridad del SOAR Ransomware Lab.

### 1.2 Contexto

El SOAR Ransomware Lab implementa una estrategia de seguridad defensa en profundidad para proteger contra ataques de
ransomware y garantizar la integridad de las operaciones de seguridad. Este documento describe los controles de
seguridad, políticas y procedimientos implementados en la plataforma.

**Principios de Seguridad:**

- **Arquitectura Zero Trust**: Nunca confiar, siempre verificar
- **Principio de Mínimo Privilegio**: Acceso mínimo requerido
- **Defensa en Profundidad**: Múltiples capas de seguridad
- **Seguridad por Diseño**: Seguridad integrada en cada componente
- **Monitoreo Continuo**: Detección de amenazas en tiempo real

## 2. Alcance

### 2.1 Qué cubre

Este documento cubre:

- Modelo de amenazas y vectores de ataque
- Arquitectura de seguridad y zonas de seguridad
- Autenticación y autorización (MFA, SSO, RBAC)
- Protección de datos (clasificación, encriptación, gestión del ciclo de vida)
- Seguridad de red (firewalls, IDS/IPS, segmentación)
- Seguridad de aplicación (SDLC, validación de entrada)
- Seguridad de infraestructura (contenedores, cloud)
- Cumplimiento regulatorio (GDPR, SOC 2, ISO 27001)
- Operaciones de seguridad (monitoreo, mantenimiento)
- Respuesta a incidentes (procedimientos, protocolos)
- Pruebas de seguridad (evaluaciones, pentesting)

### 2.2 Límites

Este documento no cubre:

- Detalles de configuración específicos de cada herramienta (ver documentación individual)
- Procedimientos operativos paso a paso (ver user_guide.md)
- Estrategias de pruebas específicas (ver testing/)
- Planificación del proyecto (ver docs/project/)
- Contratos de API detallados (ver docs/integrations/api_contracts.md)

### 2.3 Dependencias

Este documento depende de:

- Documentación oficial de cada componente (Shuffle, TheHive, Cortex, MISP, Wazuh)
- Documentación de arquitectura (docs/architecture/overview.md)
- Guía de usuario (docs/getting_started/user_guide.md)
- Estrategia de Docker (docs/architecture/docker_architecture.md)
- Documentación de pruebas (docs/testing/)
- Contratos de API (docs/integrations/api_contracts.md)

## 3. Contenido principal

### 3.1 Principios de seguridad

Los principios de seguridad fundamentales que guían el diseño y operación del SOAR Ransomware Lab son:

- **Arquitectura Zero Trust**: Nunca confiar, siempre verificar
- **Principio de Mínimo Privilegio**: Acceso mínimo requerido
- **Defensa en Profundidad**: Múltiples capas de seguridad
- **Seguridad por Diseño**: Seguridad integrada en cada componente
- **Monitoreo Continuo**: Detección de amenazas en tiempo real

### 3.2 Modelo de amenazas

#### Amenazas Principales

**Amenazas Principales:**

1. **Ataques de Ransomware**
    - Encriptación de archivos
    - Exfiltración de datos
    - Disrupción del sistema
    - Impacto de negocio

2. **Amenazas Internas**
    - Insiders maliciosos
    - Exposición accidental de datos
    - Escalada de privilegios
    - Robo de datos

3. **Ataques Externos**
    - Intrusión de red
    - Abuso de API
    - Denegación de servicio
    - Ataques a la cadena de suministro

4. **Violaciones de Datos**
    - Acceso no autorizado
    - Fuga de datos
    - Violaciones de privacidad
    - Incumplimiento regulatorio

#### Arquitectura de Seguridad

**Zonas de Seguridad:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Zona DMZ                                   │
│  Load Balancer  │  Web Firewall  │  SSL Termination           │
├─────────────────────────────────────────────────────────────┤
│                    Zona de Aplicación                           │
│  API Gateway   │  WAF           │  Rate Limiting               │
├─────────────────────────────────────────────────────────────┤
│                    Zona de Datos                                  │
│  Database       │  File Storage  │  Encryption                 │
├─────────────────────────────────────────────────────────────┤
│                    Zona de Gestión                             │
│  Monitoring     │  Logging       │  Backup Systems             │
└─────────────────────────────────────────────────────────────┘
```

**Controles de Seguridad:**

1. **Controles Preventivos**
    - Firewalls y segmentación de red
    - Validación y saneamiento de entrada
    - Mecanismos de control de acceso
    - Encriptación y protección de datos

2. **Controles Detectivos**
    - Sistemas de detección de intrusiones
    - Monitoreo de seguridad y logging
    - Algoritmos de detección de anomalías
    - Analytics de comportamiento de usuario

3. **Controles Correctivos**
    - Procedimientos de respuesta a incidentes
    - Mecanismos de recuperación de sistemas
    - Gestión de parches de seguridad
    - Herramientas de análisis forense

#### Seguridad de Infraestructura

**Seguridad de Contenedores:**

1. **Seguridad de Imágenes**
    - Escaneo de imágenes base
    - Evaluación de vulnerabilidades
    - Superficie de ataque mínima
    - Actualizaciones regulares

2. **Seguridad en Runtime**
    - Aislamiento de contenedores
    - Límites de recursos
    - Políticas de red
    - Monitoreo en runtime

3. **Seguridad de Orquestación**
    - Implementación de RBAC
    - Gestión de secrets
    - Segmentación de red
    - Logging de auditoría

### 3.3 Controles implementados

#### Autenticación y Autorización

**Métodos de Autenticación:**

1. **Autenticación Multi-Factor (MFA)**
    - OTP basado en tiempo (TOTP)
    - Verificación basada en SMS
    - Tokens de hardware
    - Autenticación biométrica

2. **Single Sign-On (SSO)**
    - Integración SAML 2.0
    - OAuth 2.0 / OpenID Connect
    - LDAP/Active Directory
    - Proveedores de identidad personalizados

3. **Gestión de Sesiones**
    - Tokens de sesión seguros
    - Políticas de timeout de sesión
    - Límites de sesiones concurrentes
    - Procedimientos de logout seguro

**Políticas de Control de Acceso:**

1. **Principio de Mínimo Privilegio**
    - Permisos mínimos requeridos
    - Acceso just-in-time
    - Escalada temporal de privilegios
    - Procedimientos de revisión de acceso

2. **Separación de Deberes**
    - Segregación de tareas críticas
    - Workflows de aprobación
    - Prevención de conflictos
    - Mantenimiento de rastro de auditoría

#### Protección de Datos

**Gestión del Ciclo de Vida de Datos:**

1. **Retención de Datos**
    - Políticas de retención automatizadas
    - Procedimientos de legal hold
    - Eliminación segura de datos
    - Documentación de cumplimiento

2. **Privacidad de Datos**
    - Identificación y enmascaramiento de PII
    - Cumplimiento GDPR
    - Principios de minimización de datos
    - Privacidad por diseño

#### Seguridad de Aplicación

**Ciclo de Vida de Desarrollo Seguro:**

1. **Fase de Diseño**
    - Modelado de amenazas
    - Revisión de arquitectura de seguridad
    - Definición de requisitos de seguridad
    - Evaluación de impacto de privacidad

2. **Fase de Desarrollo**
    - Estándares de codificación segura
    - Procesos de revisión de código
    - Escaneo de análisis estático
    - Escaneo de vulnerabilidades de dependencias

3. **Fase de Pruebas**
    - Automatización de pruebas de seguridad
    - Pruebas de penetración
    - Evaluación de vulnerabilidades
    - Pruebas de regresión de seguridad

4. **Fase de Despliegue**
    - Revisión de configuración de seguridad
    - Hardening de producción
    - Configuración de monitoreo de seguridad
    - Preparación de respuesta a incidentes

#### Respuesta a Incidentes

**Proceso de Respuesta a Incidentes:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Ciclo de Vida de Respuesta a Incidentes                │
├─────────────────────────────────────────────────────────────┤
│  Preparación → Detección → Análisis → Contención → Erradicación │
├─────────────────────────────────────────────────────────────┤
│  Recuperación → Post-incidente → Lecciones Aprendidas → Mejora    │
└─────────────────────────────────────────────────────────────┘
```

**Procedimientos de Respuesta:**

1. **Respuesta a Ransomware**
    - Aislamiento inmediato
    - Preservación de evidencia
    - Protocolos de comunicación
    - Procedimientos de recuperación

2. **Respuesta a Violación de Datos**
    - Medidas de contención
    - Evaluación de impacto
    - Procedimientos de notificación
    - Acciones de remediación

3. **Respuesta a Incidente de Seguridad**
    - Triage y priorización
    - Procedimientos de investigación
    - Análisis forense
    - Requisitos de documentación

#### Procedimientos Específicos de Respuesta a Ransomware

**Fase 1: Detección y Aislamiento (0-15 minutos)**

```bash
# 1. Identificar sistemas afectados
docker ps | grep -E "thehive|cortex|shuffle"

# 2. Aislar contenedores afectados
docker stop soar_thehive soar_cortex soar_shuffle_backend

# 3. Preservar evidencia forense
docker commit soar_thehive soar_thehive_forensic_<timestamp>
docker logs soar_thehive > artifacts/forensic/thehive_<timestamp>.log
```

**Fase 2: Análisis y Contención (15-60 minutos)**

```bash
# 1. Analizar logs de alertas
cat artifacts/logs/notify.log | grep -i ransomware

# 2. Verificar integridad de datos
python3 -m soar_lab.security.scan_vulnerabilities

# 3. Ejecutar scripts de contención simulada
python3 -m src.soar_lab.services.containment_service <hostname>
```

**Fase 3: Erradicación y Recuperación (1-4 horas)**

```bash
# 1. Restaurar desde backup limpio
bash scripts/infra/restore.sh BACKUP=<clean_backup_name>

# 2. Verificar integridad de servicios
make health

# 3. Actualizar credenciales comprometidas
python3 -m soar_lab.services.generate_secrets
```

### 3.4 Cumplimiento y protección de datos

#### Clasificación de Datos

```
┌─────────────────────────────────────────────────────────────┐
│                    Clasificación de Datos                          │
├─────────────────────────────────────────────────────────────┤
│  Público         │  Interno       │  Confidencial    │  Secreto │
│  - Marketing    │  - Operaciones   │  - Datos de Cliente │  - Claves  │
│  - Documentación│  - Procedimientos│  - Incidentes     │  - Cripto│
│  - APIs Públicas  │  - Documentos Internos│  - Forensics     │  - Admin │
└─────────────────────────────────────────────────────────────┘
```

#### Matriz de Trazabilidad: Controles de Seguridad vs Requisitos Regulatorios

| Control de Seguridad        | GDPR Art. 32 | SOC 2 CC6.1 | ISO 27001 A.12 | NIST CSF PR.AC | Implementación                                              |
|-----------------------------|--------------|-------------|----------------|----------------|-------------------------------------------------------------|
| Autenticación MFA           | ✓            | ✓           | ✓              | ✓              | Shuffle, TheHive (pendiente)                                |
| Encriptación AES-256        | ✓            | ✓           | ✓              | ✓              | Elasticsearch (pendiente)                                   |
| TLS 1.3 en tránsito         | ✓            | ✓           | ✓              | ✓              | Nginx (pendiente)                                           |
| RBAC                        | ✓            | ✓           | ✓              | ✓              | Todos los servicios (parcial)                               |
| Logging de auditoría        | ✓            | ✓           | ✓              | ✓              | Docker logs (implementado)                                  |
| Retención de datos          | ✓            | ✓           | ✓              | ✓              | Configuración por definir                                   |
| Respuesta a incidentes      | ✓            | ✓           | ✓              | ✓              | Playbook E2E (implementado)                                 |
| Backups automatizados       | ✓            | ✓           | ✓              | ✓              | scripts/infra/backup.sh (implementado)                      |
| Escaneo de vulnerabilidades | ✓            | ✓           | ✓              | ✓              | src/soar_lab/services/containment_service.py (implementado) |

**Nota:** Los controles marcados como "pendiente" son recomendaciones para producción que no están implementados en el
laboratorio actual.

#### Cumplimiento Regulatorio

El laboratorio cumple con:

- **GDPR**: Protección de datos personales
- **SOC 2**: Seguridad y disponibilidad
- **ISO 27001**: Gestión de seguridad de la información

### 3.5 Diagramas o matrices

#### Vectores de Ataque

```
┌─────────────────────────────────────────────────────────────┐
│                    Superficie de Ataque                            │
├─────────────────────────────────────────────────────────────┤
│  Web Interface  │  API Endpoints  │  File Uploads  │  Email  │
├─────────────────────────────────────────────────────────────┤
│  Network Ports  │  Authentication  │  Data Storage  │  Logs    │
├─────────────────────────────────────────────────────────────┤
│  Third-party    │  Dependencies    │  Backups       │  Config  │
└─────────────────────────────────────────────────────────────┘
```

#### Procedimientos de Hardening por Componente

**Shuffle SOAR:**

- Cambiar credenciales por defecto (SHUFFLE_DEFAULT_APIKEY)
- Habilitar autenticación multi-factor
- Configurar HTTPS con certificados TLS válidos
- Limitar acceso a IPs específicas
- Deshabilitar analyzers no necesarios

**TheHive:**

- Cambiar credenciales por defecto de admin
- Configurar HTTPS con certificados TLS
- Implementar políticas de retención de datos
- Habilitar auditoría de acciones
- Configurar CORS restrictivo

**Cortex:**

- Cambiar credenciales por defecto
- Limitar analyzers activos
- Configurar rate limiting
- Habilitar autenticación fuerte
- Revisar y actualizar analyzers regularmente

**Elasticsearch:**

- Habilitar xpack.security (actualmente deshabilitado para desarrollo)
- Configurar autenticación básica o TLS
- Implementar encriptación de datos en reposo
- Configurar firewall de red
- Limitar acceso a puertos (9201)

**MISP:**

- Cambiar credenciales por defecto
- Configurar HTTPS
- Implementar autenticación SAML/LDAP
- Configurar políticas de feed
- Habilitar logging de auditoría

**Wazuh:**

- Configurar autenticación API
- Implementar reglas de firewall
- Configurar políticas de retención
- Habilitar encriptación de comunicaciones
- Limitar acceso a puertos (15141-1516)

**Nginx:**

- Configurar HTTPS con TLS 1.3
- Implementar HSTS
- Configurar WAF básico
- Limitar tamaño de uploads
- Configurar rate limiting

#### Framework de Autorización (RBAC)

```python
# Control de acceso basado en roles (RBAC)
ROLES = {
    'admin': ['read', 'write', 'delete', 'manage'],
    'analyst': ['read', 'write', 'analyze'],
    'operator': ['read', 'execute'],
    'viewer': ['read']
}

PERMISSIONS = {
    'alerts': ['read', 'write', 'delete'],
    'cases': ['read', 'write', 'delete', 'assign'],
    'playbooks': ['read', 'write', 'execute'],
    'users': ['read', 'write', 'delete'],
    'system': ['read', 'write', 'manage']
}
```

#### Estándares de Encriptación

**Datos en Reposo:**

- Encriptación AES-256
- Encriptación de disco completo
- Encriptación de base de datos
- Encriptación de filesystem

**Datos en Tránsito:**

- TLS 1.3 para todas las comunicaciones
- Certificate pinning
- Autenticación TLS mutua
- VPN para acceso remoto

**Gestión de Claves:**

- Módulos de Seguridad de Hardware (HSM)
- Políticas de rotación de claves
- Almacenamiento seguro de claves
- Procedimientos de escrow y recuperación

#### Seguridad de Red

**Arquitectura de Red:**

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet                                   │
├─────────────────────────────────────────────────────────────┤
│  Firewall  │  IDS/IPS  │  Load Balancer  │  WAF              │
├─────────────────────────────────────────────────────────────┤
│                    Red DMZ                               │
│  Web Servers  │  API Gateways  │  Reverse Proxies           │
├─────────────────────────────────────────────────────────────┤
│                    Red de Aplicación                        │
│  App Servers  │  Microservices  │  Internal APIs              │
├─────────────────────────────────────────────────────────────┤
│                    Red de Datos                               │
│  Databases    │  File Storage   │  Backup Systems             │
└─────────────────────────────────────────────────────────────┘
```

#### Marcos Regulatorios

**GDPR (Regulación General de Protección de Datos):**

- Derechos del sujeto de datos
- Gestión de consentimiento
- Notificación de violación de datos
- Privacidad por diseño

**SOC 2 (Service Organization Control 2):**

- Controles de seguridad
- Controles de disponibilidad
- Integridad de procesamiento
- Controles de privacidad

**ISO 27001 (Gestión de Seguridad de la Información):**

- Implementación de ISMS
- Gestión de riesgos
- Mejora continua
- Mantenimiento de certificación

## 4. Validación

### 4.1 Verificación

La seguridad se verifica mediante:

- Escaneos automatizados de vulnerabilidades
- Pruebas de penetración periódicas
- Auditorías de seguridad internas y externas
- Revisiones de código de seguridad
- Monitoreo continuo de seguridad
- Evaluaciones de cumplimiento

### 4.2 Criterios de aceptación

La seguridad se considera válida cuando:

- Todos los controles de seguridad están implementados
- Las pruebas de seguridad pasan sin vulnerabilidades críticas
- El monitoreo de seguridad detecta anomalías
- Los procedimientos de respuesta a incidentes están documentados y probados
- El cumplimiento regulatorio se mantiene
- Los usuarios están capacitados en políticas de seguridad

### 4.3 Evidencias

Las evidencias de validación incluyen:

- Reportes de escaneo de vulnerabilidades
- Reportes de pruebas de penetración
- Logs de auditoría de seguridad
- Certificados de cumplimiento
- Documentación de políticas y procedimientos
- Registros de capacitación de seguridad

## 5. Problemas y consideraciones

### 5.1 Limitaciones

- **Configuración por defecto**: Las configuraciones por defecto de las herramientas pueden no ser adecuadas para
  producción
- **Recursos limitados**: Monitoreo y respuesta a incidentes requieren personal dedicado
- **Dependencias de terceros**: Seguridad depende de la seguridad de componentes de terceros
- **Evolución de amenazas**: Las amenazas evolucionan constantemente, requiriendo actualizaciones continuas

### 5.2 Riesgos o incidencias

- **Falta de hardening**: Configuraciones inseguras pueden exponer vulnerabilidades
- **Fuga de datos**: Brechas de seguridad pueden resultar en pérdida de datos sensibles
- **Disponibilidad**: Ataques DDoS pueden afectar la disponibilidad del sistema
- **Cumplimiento**: Falta de cumplimiento puede resultar en sanciones regulatorias
- **Insiders**: Usuarios maliciosos internos pueden eludir controles de seguridad

### 5.3 Recomendaciones / troubleshooting

- **Hardening**: Implementar hardening de seguridad antes de despliegue en producción
- **Monitoreo**: Configurar alertas de seguridad para detección temprana
- **Capacitación**: Proporcionar capacitación regular de seguridad a todos los usuarios
- **Actualizaciones**: Mantener todos los componentes actualizados con parches de seguridad
- **Pruebas**: Ejecutar pruebas de seguridad regularmente para identificar vulnerabilidades

## 6. Referencias

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Seguridad de Shuffle**: https://shuffler.io/docs/security
- **Documentación de Seguridad de TheHive**: https://docs.strangebee.com/thehive/admin-guide/security/
- **Documentación de Seguridad de Cortex**: https://docs.strangebee.com/cortex/admin-guide/security/
- **Documentación de Seguridad de MISP**: https://www.misp-project.org/guides/admin/
- **Documentación de Seguridad de Wazuh**: https://documentation.wazuh.com/current/user-manual/security/index.html
- **Documentación de Seguridad de Elasticsearch
  **: https://www.elastic.co/guide/en/elasticsearch/reference/current/security-settings.html
- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **Marco de Ciberseguridad NIST**: https://www.nist.gov/cyberframework
- **Benchmarks CIS**: https://www.cisecurity.org/cis-benchmarks/
- **Documentación de Arquitectura**: [docs/architecture/overview.md](overview.md)
- **Guía de Usuario**: [docs/getting_started/user_guide.md](../getting_started/user_guide.md)

---

**Mejoras implementadas:**

- Corregidas referencias a docs/core/ a rutas correctas (docs/architecture/, docs/getting_started/)
- Añadidos procedimientos detallados de hardening para cada componente (Shuffle, TheHive, Cortex, Elasticsearch, MISP,
  Wazuh, Nginx)
- Documentados procedimientos específicos de respuesta a ransomware con 3 fases (detección, análisis, recuperación)
- Añadida matriz de trazabilidad entre controles de seguridad y requisitos regulatorios (GDPR, SOC 2, ISO 27001, NIST
  CSF)

