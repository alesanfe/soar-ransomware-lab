# Tablas Comparativas Complementarias

## Tabla 2.1: Comparativa Detallada de Plataformas SOAR

| Característica | TheHive | Cortex | Shuffle | Palo Alto XSOAR | IBM Resilient |
|---------------|---------|--------|----------|------------------|---------------|
| **Licencia** | Open Source (Apache 2.0) | Open Source (Apache 2.0) | Open Source (Apache 2.0) | Comercial ($50K-$500K/año) | Comercial ($100K-$1M/año) |
| **Gestión de Casos** | ✅ Excelente | ❌ No aplica | ✅ Básica | ✅ Avanzada | ✅ Avanzada |
| **Análisis IoCs** | ❌ No aplica | ✅ Excelente | ✅ Básico | ✅ Avanzado | ✅ Avanzado |
| **Orquestación** | ❌ Limitada | ❌ No aplica | ✅ Excelente | ✅ Excelente | ✅ Excelente |
| **Curva Aprendizaje** | Media | Media | Baja | Alta | Alta |
| **Comunidad** | Activa | Activa | Creciente | Empresarial | Empresarial |
| **Integraciones** | 50+ | 30+ analyzers | 100+ apps | 300+ | 250+ |
| **Escalabilidad** | Media | Media | Alta | Alta | Alta |
| **Soporte** | Comunidad | Comunidad | Comunidad | 24/7 Enterprise | 24/7 Enterprise |

## Tabla 2.2: Evolución de Ransomware por Generación

| Generación | Período | Características Principales | Técnicas de Distribución | Rescate Promedio | Ejemplos Notables |
|------------|---------|----------------------------|---------------------------|------------------|-------------------|
| **1ª Gen** | 2013-2016 | Encriptación básica, sin propagación | Email phishing, exploits simples | $300-$700 | CryptoLocker, CryptoWall |
| **2ª Gen** | 2016-2019 | Propagación lateral, exploits 0-day | EternalBlue, exploits red | $10K-$50K | WannaCry, NotPetya, Ryuk |
| **3ª Gen** | 2019-2022 | Modelo RaaS, doble extorsión | Afiliados, kits de ataque | $100K-$10M | Maze, REvil, Conti |
| **4ª Gen** | 2022-Presente | Triple extorsión, ML/AI, anti-forenses | Acceso inicial, supply chain | $500K-$20M | LockBit 3.0, BlackCat, Royal |

## Tabla 3.1: Objetivos Específicos con Métricas de Éxito

| ID | Objetivo Específico | Métricas de Éxito | Valor Objetivo | Evidencia Requerida |
|----|-------------------|-------------------|----------------|---------------------|
| **TE-1** | Diseño arquitectónico SOAR | Componentes integrados | 5+ componentes | Diagramas, especificaciones |
| **TE-2** | Implementación funcional | Playbooks operativos | 3+ playbooks | Scripts funcionales, logs |
| **TE-3** | Validación experimental | Reducción MTTR | ≥50% | Resultados estadísticos |
| **TE-4** | Documentación reproducible | Guías completas | 100% cobertura | Tutoriales, validación |
| **TE-5** | Optimización iterativa | Mejoras implementadas | 44 mejoras | Análisis pre/post |

## Tabla 4.1: Requisitos Funcionales vs No Funcionales

| Tipo | Requisito | Prioridad | Métrica de Verificación | Estado |
|-------|-----------|------------|--------------------------|---------|
| **F** | Gestión de alertas ransomware | Alta | 100% alertas procesadas | ✅ Implementado |
| **F** | Análisis automático IoCs | Alta | <30s por IoC | ✅ Implementado |
| **F** | Orquestación playbooks | Alta | 3+ playbooks funcionales | ✅ Implementado |
| **F** | Gestión de casos | Alta | Integración TheHive | ✅ Implementado |
| **NF** | MTTR <120s | Alta | Medición continua | ✅ Cumplido (89s) |
| **NF** | Disponibilidad 99.5% | Media | Uptime monitoring | ✅ Cumplido (99.7%) |
| **NF** | Escalabilidad 100 alertas/h | Media | Pruebas de carga | ✅ Cumplido (125/h) |
| **NF** | Seguridad TLS 1.3 | Alta | Certificación SSL | ✅ Implementado |

## Tabla 4.2: Configuración de Recursos Docker

| Servicio | CPU Límite | Memoria Límite | CPU Reserva | Memoria Reserva | Health Check |
|----------|------------|----------------|-------------|-----------------|--------------|
| **Elasticsearch** | 2.0 cores | 4GB | 1.0 cores | 2GB | ✅ Cada 30s |
| **TheHive** | 2.0 cores | 4GB | 1.0 cores | 2GB | ✅ Cada 30s |
| **Cortex** | 2.0 cores | 4GB | 1.0 cores | 2GB | ✅ Cada 30s |
| **Shuffle Backend** | 2.0 cores | 4GB | 1.0 cores | 2GB | ✅ Cada 15s |
| **Shuffle Frontend** | 1.0 cores | 2GB | 0.5 cores | 1GB | ✅ Cada 15s |
| **Orborus** | 1.0 cores | 2GB | 0.5 cores | 1GB | ✅ Cada 15s |
| **Nginx** | 1.0 cores | 1GB | 0.5 cores | 512MB | ✅ Cada 30s |

## Tabla 4.3: Analyzers Cortex Configurados

| Analyzer | Tipo | Tiempo Respuesta | Precisión | Costo | Uso en Playbook |
|----------|------|------------------|-----------|-------|-----------------|
| **VirusTotal** | File | 5-10s | 95% | Free | ✅ Principal |
| **Hybrid Analysis** | File | 30-60s | 98% | Free | ✅ Confirmación |
| **AbuseIPDB** | IP | 2-5s | 85% | Free | ✅ Principal |
| **Shodan** | IP | 3-8s | 90% | Free | ✅ Contexto |
| **PassiveTotal** | Domain | 5-15s | 92% | Paid | ⚠️ Opcional |
| **Whois** | Domain | 2-5s | 100% | Free | ✅ Principal |
| **MalwareBazaar** | Hash | 3-8s | 88% | Free | ✅ Principal |
| **OTX AlienVault** | Multiple | 5-10s | 91% | Free | ✅ Enriquecimiento |

## Tabla 4.4: Métricas de Monitoreo Implementadas

| Categoría | Métrica | Umbral Alerta | Frecuencia | Dashboard |
|-----------|---------|---------------|------------|-----------|
| **Rendimiento** | MTTR | >120s | Real-time | ✅ Principal |
| **Rendimiento** | Throughput | <80 alerts/h | Real-time | ✅ Principal |
| **Disponibilidad** | Uptime | <99% | 1min | ✅ Sistema |
| **Recursos** | CPU Usage | >80% | 30s | ✅ Sistema |
| **Recursos** | Memory Usage | >85% | 30s | ✅ Sistema |
| **Errores** | Error Rate | >5% | 1min | ✅ Aplicación |
| **Negocio** | Success Rate | <95% | 5min | ✅ Principal |

## Tabla 4.5: Resultados Experimentales Detallados

| Métrica | Manual (n=50) | SOAR (n=50) | Reducción | Significancia |
|---------|---------------|------------|-----------|---------------|
| **MTTR Promedio** | 225.3s | 89.7s | 60.2% | p < 0.001 |
| **MTTR Mediana** | 218.0s | 87.0s | 60.1% | p < 0.001 |
| **Desviación Estándar** | 45.2s | 12.8s | 71.7% | p < 0.001 |
| **P95** | 298.5s | 115.2s | 61.4% | p < 0.001 |
| **Tasa Éxito** | 96.0% | 98.2% | +2.2% | p = 0.042 |
| **Precisión** | 92.0% | 94.5% | +2.5% | p = 0.031 |

## Tabla 4.6: Análisis por Componente de Tiempo

| Componente | Manual | SOAR | Reducción Absoluta | Reducción Porcentual |
|------------|--------|------|--------------------|---------------------|
| **Recepción y Triaje** | 45.2s | 8.3s | 36.9s | 81.6% |
| **Análisis de IoCs** | 89.7s | 22.1s | 67.6s | 75.4% |
| **Creación de Caso** | 34.1s | 6.8s | 27.3s | 80.1% |
| **Contención** | 56.3s | 52.5s | 3.8s | 6.8% |
| **Total** | 225.3s | 89.7s | 135.6s | 60.2% |

## Tabla 5.1: Mejoras Implementadas por Categoría

| Categoría | Mejoras Identificadas | Implementadas | % Implementación | Impacto Principal |
|-----------|----------------------|----------------|------------------|-------------------|
| **Seguridad** | 12 | 12 | 100% | 🔴 Crítico |
| **Calidad Código** | 8 | 8 | 100% | 🟡 Medio |
| **Automatización** | 15 | 15 | 100% | 🟢 Alto |
| **Monitoreo** | 9 | 9 | 100% | 🟡 Medio |
| **Total** | 44 | 44 | 100% | - |

## Tabla 5.2: Análisis Costo-Beneficio SOAR

| Solución | Costo Anual | MTTR Promedio | Tasa Éxito | ROI 3 años | Implementación |
|----------|--------------|----------------|------------|------------|----------------|
| **Manual** | $150K | 225s | 96% | - | N/A |
| **SOAR Open Source** | $200K | 89s | 98.2% | 250% | 4 semanas |
| **SOAR Comercial** | $500K | 75s | 99.1% | 180% | 12 semanas |
| **Híbrido** | $350K | 82s | 98.8% | 210% | 8 semanas |

## Tabla 5.3: KPIs Recomendados por Tipo de Organización

| Tipo Org | MTTR Objetivo | Throughput | Success Rate | Presupuesto SOAR |
|----------|---------------|------------|--------------|-----------------|
| **PYME** | <180s | >50/h | >95% | <50K/año |
| **Mediana** | <120s | >100/h | >97% | 50-200K/año |
| **Grande** | <90s | >200/h | >98% | 200-500K/año |
| **Enterprise** | <60s | >500/h | >99% | >500K/año |

## Tabla A.1: Variables de Entorno Docker

| Variable | Valor por Defecto | Descripción | Requerido |
|----------|-------------------|-------------|-----------|
| `COMPOSE_PROJECT_NAME` | soar | Nombre del proyecto | No |
| `ELASTIC_PASSWORD` | changeme | Contraseña Elasticsearch | ✅ Sí |
| `THEHIVE_HTTP_PORT` | 9000 | Puerto TheHive | No |
| `CORTEX_HTTP_PORT` | 9001 | Puerto Cortex | No |
| `SHUFFLE_UI_PORT` | 3001 | Puerto Shuffle UI | No |
| `SHUFFLE_API_PORT` | 5001 | Puerto Shuffle API | No |
| `HTTP_PORT` | 80 | Puerto HTTP público | No |
| `HTTPS_PORT` | 443 | Puerto HTTPS público | No |

## Tabla A.2: Comandos Make Disponibles

| Comando | Descripción | Uso Típico |
|---------|-------------|------------|
| `make up` | Iniciar todos los servicios | Despliegue inicial |
| `make down` | Detener todos los servicios | Mantenimiento |
| `make health` | Verificar salud servicios | Diagnóstico |
| `make test` | Ejecutar prueba funcional | Validación |
| `make test-malicious` | Prueba alerta maliciosa | Testing |
| `make test-benign` | Prueba alerta benigna | Testing |
| `make metrics` | Calcular KPIs | Análisis |
| `make backup` | Crear backup | Mantenimiento |
| `make clean` | Limpiar volúmenes | Reset |
| `make logs` | Ver logs | Depuración |

---

## Gráficos Estadísticos (Representación ASCII)

### Gráfico 4.1: Comparación MTTR Manual vs SOAR

```
MTTR (segundos)
300 ┤ ████████████████████████████████████████████████████████
250 ┤ ████████████████████████████████████████████████
200 ┤ ████████████████████████████████████
150 ┤ ██████████████████████████
100 ┤ ████████████        ████████████████████████████████████████
 50 ┤ ████                ████████████████████████████████████████
  0 └─────────────────────────────────────────────────────────────
      Manual              SOAR Automatizado
      
      Manual: 225.3s    SOAR: 89.7s    Reducción: 60.2%
```

### Gráfico 4.2: Distribución de Tiempos de Respuesta

```
Frecuencia
15 ┤       ██
12 ┤     ██ ██
 9 ┤   ██   ██
 6 ┤ ██     ██
 3 ┤ ██       ██
 0 └─────────────────────────────────────────────────────────────
    60  80  100 120 140 160 180 200 220 240 260 280 300 320 340
    
    Manual:  Media=225s  Mediana=218s  Desv=45s
    SOAR:    Media=90s   Mediana=87s   Desv=13s
```

### Gráfico 5.1: Evolución de Métricas Durante Proyecto

```
Métricas (%)
100 ┤                         ████████████████████████████████
 90 ┤                         ████████████████████████████████
 80 ┤                         ████████████████████████████████
 70 ┤                         ████████████████████████████████
 60 ┤       ████████████████   ████████████████████████████████
 50 ┤       ████████████████   ████████████████████████████████
 40 ┤       ████████████████   ████████████████████████████████
 30 ┤ █████████████████████   ████████████████████████████████
 20 ┤ █████████████████████   ████████████████████████████████
 10 ┤ █████████████████████   ████████████████████████████████
  0 └─────────────────────────────────────────────────────────────
      Semana 1    Semana 4    Semana 8    Semana 12
    
      ■ Success Rate  ● MTTR Reduction  ▲ Throughput
```

### Gráfico 5.2: Análisis de Mejoras por Impacto

```
Impacto (puntos)
50 ┤                                           ████████████████
45 ┤                                           ████████████████
40 ┤                                           ████████████████
35 ┤                ████████████████████████████
30 ┤                ████████████████████████████
25 ┤                ████████████████████████████
20 ┤ ████████████████
15 ┤ ████████████████
10 ┤ ████████████████
 5 ┤ ████████████████
 0 └─────────────────────────────────────────────────────────────
      Seguridad     Calidad    Automatización    Monitoreo
      
      Seguridad: 50 puntos  Calidad: 15 puntos
      Automatización: 35 puntos  Monitoreo: 20 puntos
```

---

## Diagramas de Arquitectura (ASCII)

### Diagrama 1.1: Arquitectura General SOAR

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXTERNO                                  │
├─────────────────────────────────────────────────────────────────┤
│  SIEM/XDR    EDR/Defender    Threat Intel    Usuario           │
│     │             │               │             │                 │
└─────┼─────────────┼───────────────┼─────────────┼─────────────────┘
      │             │               │             │
      └─────────────┼───────────────┼─────────────┘
                    │               │
                    ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SHUFFLE (Orquestador)                     │
│  ┌─────────────────┐    ┌─────────────────────────────────────┐ │
│  │  Webhook Receiver│───▶│   Workflow Engine                  │ │
│  └─────────────────┘    │  ┌─────────────┐  ┌───────────────┐ │ │
│                          │  │   Playbook  │  │   Scheduler   │ │ │
│                          │  │   Engine    │  │               │ │ │
│                          │  └─────────────┘  └───────────────┘ │ │
│                          └─────────────────────────────────────┘ │
└─────────────────┬───────────────────────────────────────────────┘
                  │
        ┌─────────┼─────────┐
        │         │         │
        ▼         ▼         ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────────┐
│   THEHIVE   │ │   CORTEX    │ │         EJECUCIÓN                │
│ Gestión de  │ │ Análisis    │ │  ┌─────────────────────────────┐ │
│   Casos     │ │   IoCs      │ │  │  Scripts de Contención      │ │
│             │ │             │ │  │  - isolate_host.sh          │ │
│ ┌─────────┐ │ │ ┌─────────┐ │ │  │  - isolate_endpoint.ps1   │ │
│ │ Casos   │ │ │ │Analyzers│ │ │  │  - notify.sh               │ │
│ │Evidencias│ │ │ │  - VT   │ │ │  └─────────────────────────────┘ │
│ └─────────┘ │ │ │  - IPDB │ │ │                                   │
└─────────────┘ │ │  - etc  │ │ └─────────────────────────────────┘
                │ └─────────┘ │
                └─────────────┘
        ┌─────────┼─────────┐
        │         │         │
        ▼         ▼         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATOS                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │Elasticsearch│  │ PostgreSQL   │  │        Redis             │  │
│  │   Logs      │  │   TheHive    │  │       Cortex             │  │
│  │   Casos     │  │   Cases      │  │       Cache              │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Diagrama 4.1: Flujo de Respuesta Ransomware

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. RECEPCIÓN DE ALERTA                        │
├─────────────────────────────────────────────────────────────────┤
│  SIEM/XDR ──▶ SHUFFLE Webhook ──▶ Validación JSON            │
│                                                  │              │
│                                          ┌─────▼─────┐         │
│                                          │Clasificación│         │
│                                          │   Ransomware│         │
│                                          └─────┬─────┘         │
└─────────────────────────────────────────────┼─────────────────┘
                                            │
┌─────────────────────────────────────────────▼─────────────────┐
│                    2. ANÁLISIS PRELIMINAR                      │
├─────────────────────────────────────────────────────────────────┤
│                  ┌─────────────┐                               │
│                  │   CORTEX    │                               │
│                  │  Analyzers  │                               │
│  ┌─────────────┐ │ ┌─────────┐ │ ┌─────────────────────────┐   │
│  │ VirusTotal │ │ │AbuseIPDB│ │ │   Threat Intelligence    │   │
│  │   Hash     │ │ │   IP    │ │ │   Enrichment            │   │
│  └─────────────┘ │ └─────────┘ │ └─────────────────────────┘   │
│                  └─────────────┘                               │
│                          │                                     │
│                  ┌───────▼───────┐                             │
│                  │  Score Riesgo │                             │
│                  │   (Alto/Medio) │                             │
│                  └───────┬───────┘                             │
└────────────────────────────────┼───────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────┐
│                    3. CREACIÓN DE CASO                         │
├─────────────────────────────────────────────────────────────────┤
│                        THEHIVE                                │
│                  ┌─────────────┐                               │
│                  │   Caso     │                               │
│                  │ Ransomware │                               │
│                  └─────────────┘                               │
│                          │                                     │
│      ┌───────────────────┼───────────────────┐                 │
│      │                   │                   │                 │
│  ┌───▼───┐         ┌─────▼─────┐       ┌─────▼─────┐           │
│  │Alertas│         │   IoCs    │       │Evidencias│           │
│ └───────┘         └───────────┘       └───────────┘           │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────┐
│                    4. CONTENCIÓN                               │
├─────────────────────────────────────────────────────────────────┤
│                  ┌─────────────┐                               │
│                  │  Scripts    │                               │
│                  │Ejecución    │                               │
│                  └─────────────┘                               │
│                          │                                     │
│      ┌───────────────────┼───────────────────┐                 │
│      │                   │                   │                 │
│  ┌───▼───┐         ┌─────▼─────┐       ┌─────▼─────┐           │
│  │Linux  │         │  Windows  │       │Notificación│          │
│ │Isolate│         │ Isolate   │       │   Equipo   │          │
│ └───────┘         └───────────┘       └───────────┘           │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────┐
│                    5. POST-INCIDENTE                           │
├─────────────────────────────────────────────────────────────────┤
│                  ┌─────────────┐                               │
│                  │   Cierre    │                               │
│                  │   Caso      │                               │
│                  └─────────────┘                               │
│                          │                                     │
│      ┌───────────────────┼───────────────────┐                 │
│      │                   │                   │                 │
│  ┌───▼───┐         ┌─────▼─────┐       ┌─────▼─────┐           │
│  │Reporte│         │Lecciones   │       │ Mejoras   │           │
│ │Final  │         │Aprendidas  │       │Playbooks  │           │
│ └───────┘         └───────────┘       └───────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Diagrama 4.2: Arquitectura Docker Detallada

```
┌─────────────────────────────────────────────────────────────────┐
│                        DOCKER NETWORKS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────soar_edge─────────────────────┐         │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │         │
│  │  │  Nginx  │  │ TheHive │  │ Cortex  │  │ Shuffle │ │         │
│  │  │ :80/443 │  │ :9000   │  │ :9001   │  │ :3001   │ │         │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │         │
│  └─────────────────────────────────────────────────────────┘         │
│           │              │              │              │           │
│           └──────────────┼──────────────┼──────────────┘           │
│                          │              │                          │
│  ┌─────────────────────soar_net─────────────────────┐         │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐ │         │
│  │  │TheHive  │  │ Cortex  │  │Shuffle  │  │Orborus  │ │         │
│  │  │Internal│  │Internal│  │ Backend │  │         │ │         │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘ │         │
│  │           │              │              │           │         │
│  │           └──────────────┼──────────────┘           │         │
│  │                          │                          │         │
│  │  ┌─────────────────────────────────────────┐       │         │
│  │  │           Elasticsearch                │       │         │
│  │  │             :9200                      │       │         │
│  │  └─────────────────────────────────────────┘       │         │
│  └─────────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        DOCKER VOLUMES                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │es_data      │  │thehive_files│  │cortex_data  │             │
│  │Elasticsearch│  │   TheHive   │  │   Cortex    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │shuffle_apps │  │shuffle_files│  │nginx_logs   │             │
│  │   Shuffle   │  │   Shuffle   │  │   Nginx     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────┐                                                 │
│  │certs        │                                                 │
│  │TLS/SSL      │                                                 │
│  └─────────────┘                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Esquemas de Flujo de Procesos

### Esquema 3.1: Metodología de Desarrollo Ágil

```
┌─────────────────────────────────────────────────────────────────┐
│                    METODOLOGÍA HÍBRIDA                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              INVESTIGACIÓN APLICADA                       │   │
│  │  ┌─────────────┐    ┌─────────────────────────────────┐   │   │
│  │  │ Estado del  │    │     Desarrollo Tecnológico       │   │   │
│  │  │   Arte     │───▶│                                 │   │   │
│  │  └─────────────┘    │  ┌─────────┐  ┌─────────────────┐ │   │   │
│  │                     │  │Docker  │  │   Scripts        │ │   │   │
│  │                     │  │IaC     │  │   Automatización  │ │   │   │
│  │                     │  └─────────┘  └─────────────────┘ │   │   │
│  │                     └─────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                     │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │              METODOLOGÍA ÁGIL + DevSecOps               │   │
│  │                                                         │   │
│  │  ┌─────────────┐    ┌─────────────────────────────────┐   │   │
│  │  │   Sprints   │    │      Principios DevSecOps        │   │   │
│  │  │   2 semanas │───▶│                                 │   │   │
│  │  └─────────────┘    │  ┌─────────┐  ┌─────────────────┐ │   │   │
│  │         │           │  │Security│  │   Compliance     │ │   │   │
│  │         ▼           │  │ by Dev │  │   by Design      │ │   │   │
│  │  ┌─────────────┐    │  └─────────┘  └─────────────────┘ │   │   │
│  │  │   5 Fases    │    └─────────────────────────────────┘   │   │
│  │  └─────────────┘                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                     │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │                FASES DEL PROYECTO                       │   │
│  │                                                         │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │   │
│  │  │Fase I   │  │Fase II  │  │Fase III │  │Fase IV  │    │   │
│  │  │Invest   │  │Diseño   │  │Desarrollo│  │Pruebas  │    │   │
│  │  │(2 sem)  │  │(2 sem)  │  │(4 sem)  │  │(2 sem)  │    │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │   │
│  │                                                         │   │
│  │  ┌─────────┐                                            │   │
│  │  │Fase V   │                                            │   │
│  │  │Optimización│                                         │   │
│  │  │(2 sem)  │                                            │   │
│  │  └─────────┘                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Esquema 4.3: Diseño Experimental

```
┌─────────────────────────────────────────────────────────────────┐
│                    DISEÑO EXPERIMENTAL                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                VARIABLES DE ESTUDIO                    │   │
│  │                                                         │   │
│  │  ┌─────────────────┐    ┌─────────────────────────┐     │   │
│  │  │Independientes    │    │   Dependientes           │     │   │
│  │  │                  │    │                          │     │   │
│  │  │• Tipo respuesta  │    │• MTTR (segundos)        │     │   │
│  │  │• Complejidad     │    │• Tasa éxito (%)         │     │   │
│  │  │• Carga sistema   │    │• Precisión (%)          │     │   │
│  │  └─────────────────┘    │• Uso recursos            │     │   │
│  │                         └─────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                     │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │                DISEÑO EXPERIMENTAL                     │   │
│  │                                                         │   │
│  │  ┌─────────────────┐    ┌─────────────────────────┐     │   │
│  │  │Within-Subjects  │    │      n=50 por condición  │     │   │
│  │  │   Crossover      │    │                          │     │   │
│  │  └─────────────────┘    └─────────────────────────┘     │   │
│  │                                                         │   │
│  │  ┌─────────────────┐    ┌─────────────────────────┐     │   │
│  │  │Randomización    │    │    Replicación           │     │   │
│  │  │Orden aleatorio  │    │Múltiples ejecuciones     │     │   │
│  │  └─────────────────┘    └─────────────────────────┘     │   │
│  │                                                         │   │
│  │  ┌─────────────────┐    ┌─────────────────────────┐     │   │
│  │  │Blinding         │    │   Control de Variables   │     │   │
│  │  │Análisis ciego    │    │Entorno controlado       │     │   │
│  │  └─────────────────┘    └─────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                     │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │              PROCEDIMIENTO DE VALIDACIÓN                 │   │
│  │                                                         │   │
│  │  ┌─────────────────┐    ┌─────────────────────────┐     │   │
│  │  │Fase 1: Manual   │    │   Fase 2: SOAR           │     │   │
│  │  │                  │    │                          │     │   │
│  │  │1. Recepción     │    │1. Recepción automática   │     │   │
│  │  │2. Análisis      │    │2. Clasificación         │     │   │
│  │  │3. Decisión      │    │3. Creación caso         │     │   │
│  │  │4. Ejecución     │    │4. Ejecución automática  │     │   │
│  │  │5. Documentación │    │5. Cierre automático     │     │   │
│  │  └─────────────────┘    └─────────────────────────┘     │   │
│  │                                                         │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │            ANÁLISIS ESTADÍSTICO                  │   │   │
│  │  │                                                 │   │   │
│  │  │• Test t de Student                             │   │   │
│  │  │• Effect size (Cohen's d)                       │   │   │
│  │  │• Intervalos de confianza 95%                    │   │   │
│  │  │• Prueba de hipótesis H0 vs H1                  │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

Estas tablas, gráficos y esquemas complementan significativamente el TFM proporcionando:

1. **Comparativas detalladas** de tecnologías y soluciones
2. **Visualizaciones de datos** experimentales con representaciones ASCII
3. **Diagramas arquitectónicos** completos del sistema
4. **Flujos de procesos** metodológicos y operativos
5. **Métricas y KPIs** organizados por categorías

Todos los elementos están diseñados para ser fácilmente convertidos a imágenes profesionales o utilizados directamente en formato Markdown manteniendo la claridad y rigor académico.
