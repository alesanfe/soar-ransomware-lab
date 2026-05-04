# 2. Estado del arte

## 2.1. Evolución del ransomware

### 2.1.1. Primera Generación (2013-2016)
La primera generación de ransomware se caracterizó por su simplicidad y enfoque en individuos. Ejemplos notables incluyen:

- **CryptoLocker (2013)**: Primer ransomware moderno significativo que utilizaba Bitcoin para pagos
- **CryptoWall (2014)**: Evolución con técnicas de distribución más sofisticadas
- **Locky (2016)**: Introdujo técnicas de evasion y propagación por email

**Características técnicas:**
- Algoritmos de encriptación básicos (RSA-2048, AES-256)
- Distribución principalmente por email phishing
- Sin capacidades de movimiento lateral
- Exigencia de rescates individuales ($300-$700)

### 2.1.2. Segunda Generación (2016-2019)
La segunda generación introdujo capacidades empresariales y técnicas avanzadas:

- **WannaCry (2017)**: Explotación de EternalBlue para propagación masiva
- **NotPetya (2017)**: Wiper disfrazado de ransomware con impacto sistémico
- **Ryuk (2018)**: Enfoque específico en grandes organizaciones

**Innovaciones técnicas:**
- Explotación de vulnerabilidades Zero-day
- Capacidades de movimiento lateral
- Técnicas de persistencia avanzadas
- Rescates más elevados ($10,000-$50,000)

### 2.1.3. Tercera Generación (2019-2022)
La tercera generación introdujo el modelo Ransomware-as-a-Service (RaaS):

- **Maze (2019)**: Pionero en doble extorsión (datos + encriptación)
- **REvil/Sodinokibi (2019)**: Plataforma RaaS completa con afiliados
- **Conti (2020)**: Modelo de suscripción y desarrollo continuo

**Características distintivas:**
- Modelo de negocio RaaS con afiliados
- Doble extorsión: amenaza de publicación de datos
- Infraestructura sofisticada con soporte 24/7
- Rescates empresariales ($100,000-$10M)

### 2.1.4. Cuarta Generación (2022-Presente)
La generación actual combina múltiples técnicas de extorsión:

- **LockBit 3.0 (2022)**: Plataforma RaaS más activa actualmente
- **BlackCat/ALPHV (2022)**: Ransomware escrito en Rust
- **Royal (2023)**: Triple extorsión (encriptación, publicación, DDoS)

**Capacidades avanzadas:**
- Triple extorsión: encriptación, publicación de datos, ataques DDoS
- Técnicas anti-forenses y evasión avanzada
- Integración con frameworks de acceso inicial
- Especialización por industria y geografía

## 2.2. Plataformas SOAR: Conceptos y Fundamentos

### 2.2.1. Definición y Componentes

SOAR (Security Orchestration, Automation and Response) es una tecnología que combina tres capacidades fundamentales:

**Orquestación**
- Coordinación de múltiples herramientas de seguridad
- Integración de flujos de trabajo complejos
- Gestión de casos y evidencias

**Automatización**
- Ejecución de tareas repetitivas sin intervención humana
- Aplicación de procedimientos estandarizados
- Reducción del tiempo de respuesta

**Respuesta**
- Acciones de contención y remediación
- Notificaciones y escalados automáticos
- Generación de informes y métricas

### 2.2.2. Ciclo de Vida de la Respuesta a Incidentes

Las plataformas SOAR modernas soportan el ciclo completo de respuesta a incidentes:

1. **Detección**: Recepción de alertas desde múltiples fuentes (SIEM, EDR, etc.)
2. **Triaje**: Clasificación y priorización automática de incidentes
3. **Investigación**: Análisis de IoCs y recopilación de evidencias
4. **Contención**: Ejecución de acciones de aislamiento y bloqueo
5. **Remediación**: Limpieza y recuperación de sistemas afectados
6. **Cierre**: Documentación y lecciones aprendidas

### 2.2.3. Tipos de Automatización en SOAR

**Automatización Guiada**
- Asistencia al analista con recomendaciones
- Pre-población de datos y contextos
- Validación automática de acciones

**Automatización Completa**
- Ejecución autónoma de playbooks completos
- Respuesta sin intervención humana
- Escalado automático basado en carga

**Automatización Híbrida**
- Combinación de pasos automáticos y manuales
- Decisión humana en puntos críticos
- Flexibilidad adaptativa según contexto

## 2.3. Análisis Comparativo de Plataformas SOAR

### 2.3.1. TheHive: Características y Capacidades

**Características Principales**
- Gestión de casos y colaboración forense
- Integración con Cortex para análisis de IoCs
- Interfaz web intuitiva para analistas
- API RESTful para integraciones

**Ventajas**
- Código abierto y gratuito
- Comunidad activa y documentación completa
- Flexibilidad en personalización
- Buen rendimiento en entornos de mediana escala

**Limitaciones**
- Requiere configuración técnica inicial
- Capacidades de automatización limitadas vs Shuffle
- Escalabilidad dependiente de Elasticsearch
- Curva de aprendizaje moderada

### 2.3.2. Cortex: Motor de Análisis y Analyzers

**Arquitectura**
- Motor de análisis distribuido
- Sistema de analyzers modulares
- Integración con múltiples fuentes de threat intelligence
- Ejecución sandboxizada de analyzers

**Analyzers Disponibles**
- Análisis de archivos (VirusTotal, Hybrid Analysis)
- Análisis de redes (AbuseIPDB, Shodan)
- Análisis de dominios (PassiveDNS, Whois)
- Análisis de hash (VT, MalwareBazaar)

**Rendimiento**
- Procesamiento paralelo de IoCs
- Caching de resultados para optimización
- Integración con Docker para escalabilidad

### 2.3.3. Shuffle: Orquestación Visual y Workflows

**Características Destacadas**
- Interfaz visual de arrastrar y soltar
- Marketplace de apps y conectores
- Ejecución distribuida con Orborus
- Integraciones nativas con 100+ servicios

**Capacidades de Automatización**
- Workflows complejos con múltiples ramificaciones
- Ejecución condicional basada en resultados
- Manejo de errores y reintentos automáticos
- Programación de tareas y ejecución programada

**Ventajas Competitivas**
- Curva de aprendizaje baja
- Desarrollo rápido de playbooks
- Escalabilidad horizontal nativa
- Soporte para múltiples entornos

### 2.3.4. Soluciones Comerciales vs Open Source

**Soluciones Comerciales (Palo Alto Cortex XSOAR, IBM Resilient, Splunk SOAR)**
- Costo elevado ($50,000-$500,000 anuales)
- Soporte empresarial y SLAs
- Integraciones pre-construidas extensivas
- Capacidades avanzadas de ML y AI

**Soluciones Open Source (TheHive+Cortex+Shuffle)**
- Costo cero en licencias
- Flexibilidad total de personalización
- Dependencia de comunidad para soporte
- Requiere expertise técnico para implementación

## 2.4. Marco Teórico de Automatización en Respuesta a Incidentes

### 2.4.1. Principios de Diseño de Playbooks

**Principio de Menor Privilegio**
- Acciones automatizadas con permisos mínimos necesarios
- Validación de acciones críticas antes de ejecución
- Auditoría completa de todas las acciones

**Principio de Idempotencia**
- Playbooks ejecutables múltiples veces sin efectos adversos
- Verificación de estado antes de ejecutar acciones
- Manejo elegante de condiciones de error

**Principio de Resiliencia**
- Recuperación automática de fallos
- Caminos alternativos para contingencias
- Notificación de fallos y escalado manual

### 2.4.2. Métricas de Eficacia (MTTR, MTTD, etc.)

**MTTR (Mean Time to Respond)**
- Tiempo promedio desde detección hasta contención
- Métrica principal de eficacia en respuesta
- Objetivo: <120 segundos para ransomware

**MTTD (Mean Time to Detect)**
- Tiempo promedio desde ocurrencia hasta detección
- Dependiente de capacidades de SIEM/EDR
- Objetivo: <60 segundos para ransomware

**MTTI (Mean Time to Investigate)**
- Tiempo promedio para análisis inicial
- Reducible mediante automatización de IoCs
- Objetivo: <30 segundos con SOAR

**MTTC (Mean Time to Contain)**
- Tiempo promedio para acciones de contención
- Beneficiario directo de automatización
- Objetivo: <90 segundos con SOAR

### 2.4.3. Modelos de Madurez en Respuesta a Incidentes

**Nivel 1: Reactivo**
- Respuesta manual completamente
- Sin estandarización de procedimientos
- MTTR típicamente >300 segundos

**Nivel 2: Procedimental**
- Playbooks documentados pero ejecución manual
- Algunas herramientas automatizadas básicas
- MTTR mejorado a 180-240 segundos

**Nivel 3: Automatizado**
- Playbooks automatizados parciales
- Integración de herramientas clave
- MTTR reducido a 90-180 segundos

**Nivel 4: Optimizado**
- Automatización completa con ML/AI
- Respuesta predictiva y proactiva
- MTTR <60 segundos

**Nivel 5: Autónomo**
- Respuesta completamente autónoma
- Aprendizaje continuo y adaptación
- MTTR <30 segundos

Este marco teórico establece las bases para evaluar la contribución del presente trabajo, que busca mover las organizaciones desde el Nivel 2 hacia el Nivel 3-4 de madurez en respuesta a incidentes de ransomware.
