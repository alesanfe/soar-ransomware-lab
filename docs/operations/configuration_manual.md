# Manual de Configuración del Laboratorio SOAR para Respuesta ante Ransomware

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
        - [3.1.1 Componentes del laboratorio](#311-componentes-del-laboratorio)
        - [3.1.2 Fases de configuración](#312-fases-de-configuración)
    - [3.2 Proceso de configuración](#32-proceso-de-configuración)
        - [3.2.1 Paso 1: requisitos previos](#321-paso-1-requisitos-previos)
        - [3.2.2 Paso 2: despliegue del stack core](#322-paso-2-despliegue-del-stack-core)
        - [3.2.3 Paso 3: configuración de Elasticsearch](#323-paso-3-configuración-de-elasticsearch)
        - [3.2.4 Paso 4: configuración de TheHive](#324-paso-4-configuración-de-thehive)
        - [3.2.5 Paso 5: configuración de Cortex](#325-paso-5-configuración-de-cortex)
        - [3.2.6 Paso 6: configuración de Shuffle](#326-paso-6-configuración-de-shuffle)
        - [3.2.7 Paso 7: registro de apps en Shuffle](#327-paso-7-registro-de-apps-en-shuffle)
        - [3.2.8 Paso 8: creación de workflows](#328-paso-8-creación-de-workflows)
        - [3.2.9 Paso 9: configuración de Wazuh](#329-paso-9-configuración-de-wazuh)
        - [3.2.10 Paso 10: configuración de MISP](#3210-paso-10-configuración-de-misp)
        - [3.2.11 Paso 11: pruebas end-to-end](#3211-paso-11-pruebas-end-to-end)
    - [3.3 Verificación de configuración](#33-verificación-de-configuración)
        - [3.3.1 Resumen de URLs de acceso](#331-resumen-de-urls-de-acceso)
        - [3.3.2 Scripts de automatización](#332-scripts-de-automatización)
        - [3.3.3 Arquitectura de integraciones](#333-arquitectura-de-integraciones)
    - [3.4 Troubleshooting](#34-troubleshooting)
        - [3.4.1 Workers no se conectan a soar_soar_net](#341-workers-no-se-conectan-a-soar_soar_net)
        - [3.4.2 App TheHive no funciona](#342-app-thehive-no-funciona)
        - [3.4.3 Workflow se queda en "Step is still running"](#343-workflow-se-queda-en-step-is-still-running)
    - [3.5 Mantenimiento](#35-mantenimiento)
        - [3.5.1 Backups](#351-backups)
        - [3.5.2 Actualizaciones](#352-actualizaciones)
        - [3.5.3 Monitoreo](#353-monitoreo)
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

Este manual explica paso a paso cómo configurar el laboratorio SOAR completo para respuesta automatizada ante incidentes
de ransomware.

### 1.2 Contexto

El laboratorio SOAR integra múltiples herramientas (Shuffle, TheHive, Cortex, MISP, Wazuh, Elasticsearch) para orquestar
respuestas automatizadas a incidentes de seguridad. Este manual guía el proceso completo de configuración desde los
requisitos previos hasta las pruebas end-to-end.

## 2. Alcance

### 2.1 Qué cubre

Este manual cubre:

- Requisitos previos de hardware y software
- Despliegue del stack core con Docker Compose
- Configuración de Elasticsearch, TheHive, Cortex, Shuffle, Wazuh y MISP
- Registro de apps en Shuffle
- Creación de workflows
- Pruebas end-to-end
- Troubleshooting de problemas comunes
- Referencias y proyectos de investigación

### 2.2 Límites

Este manual no cubre:

- Estrategias de seguridad avanzadas (ver docs/architecture/security.md)
- Arquitectura detallada del sistema (ver docs/architecture/overview.md)
- Planificación del proyecto (ver docs/project/plan.md)
- Gestión de riesgos (ver docs/project/risks.md)
- Detalle del playbook E2E (ver docs/operations/playbooks/ransomware_playbook_e2e.md)

### 2.3 Dependencias

Este manual depende de:

- Documentación de arquitectura (docs/architecture/overview.md)
- Documentación de Docker (docs/architecture/docker_architecture.md)
- Guía de usuario (docs/getting_started/user_guide.md)
- Especificación de APIs (docs/integrations/api_contracts.md)

## 3. Contenido principal

### 3.1 Requisitos previos

#### 3.1.1 Componentes del laboratorio

- **Shuffle**: Plataforma de automatización SOAR
- **TheHive**: Gestión de casos e incidentes
- **Cortex**: Motor de análisis de observables
- **MISP**: Plataforma de threat intelligence
- **Wazuh**: SIEM/XDR para detección de alertas
- **Elasticsearch**: Motor de búsqueda y almacenamiento
- **Redis**: Cache para Shuffle
- **PostgreSQL**: Base de datos para Shuffle
- **Nginx**: Reverse proxy

#### 3.1.2 Fases de configuración

1. **Requisitos Previos**: Verificación de hardware y software
2. **Despliegue del Stack Core**: Inicialización de contenedores
3. **Configuración de Servicios**: Elasticsearch, TheHive, Cortex, Shuffle
4. **Registro de Apps**: Integración de servicios con Shuffle
5. **Creación de Workflows**: Definición de flujos de automatización
6. **Configuración de Wazuh y MISP**: Integración SIEM y threat intelligence
7. **Pruebas End-to-End**: Validación de integraciones

### 3.2 Proceso de configuración

Esta sección describe los pasos detallados para configurar el laboratorio SOAR completo.

#### 3.2.1 Paso 1: requisitos previos

**Hardware:**

- **RAM**: 16GB+ (mínimo 8GB)
- **CPU**: 4 cores+ (mínimo 2 cores)
- **Disco**: 50GB+ SSD

**Software:**

- **Docker Engine**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+
- **Git**: para clonar el repositorio

**Verificar Instalación:**

```bash
docker --version
docker-compose --version
python --version
```

#### 3.2.2 Paso 2: despliegue del stack core

**1. Clonar el Repositorio:**

```bash
git clone <repo-url>
cd soar-ransomware-lab
```

**2. Configurar Variables de Entorno:**
Editar el archivo `.env.full` con las credenciales:

```bash
nano .env.full
```

Variables importantes a configurar:

- `ELASTIC_PASSWORD`: Contraseña de Elasticsearch
- `REDIS_PASSWORD`: Contraseña de Redis
- `SHUFFLE_DEFAULT_USERNAME`: Usuario admin de Shuffle
- `SHUFFLE_DEFAULT_PASSWORD`: Contraseña admin de Shuffle
- `THEHIVE_SECRET`: Secret de TheHive

**3. Desplegar el Stack Completo:**

```bash
make up
```

Este comando despliega: Elasticsearch, Redis, TheHive, Cortex, Shuffle (frontend + backend + orborus), Network-watcher,
Nginx.

**4. Verificar Estado de Servicios:**

```bash
docker ps
```

#### 3.2.3 Paso 3: configuración de Elasticsearch

**1. Verificar Elasticsearch esté Healthy:**

```bash
curl -u elastic:YOUR_PASSWORD http://localhost:9201/_cluster/health
```

**2. Crear Índices Iniciales:**
Elasticsearch crea automáticamente los índices cuando Shuffle inicia, pero puedes verificar:

```bash
curl -u elastic:YOUR_PASSWORD http://localhost:9201/_cat/indices?v
```

#### 3.2.4 Paso 4: configuración de TheHive

**1. Acceder a TheHive:**
URL: https://localhost/thehive/ o http://localhost:9000/

**2. Crear Usuario Admin:**

- Usuario: `admin@thehive.local`
- Contraseña: `secret`
- Cambiar contraseña al primer login

**3. Crear Organización:**

1. Ir a **Admin** > **Organizations**
2. Click en **New Organization**
3. Nombre: `SOAR Lab`
4. Descripción: `Laboratorio SOAR para ransomware`

**4. Generar API Key:**

1. Ir a tu perfil (click en tu nombre)
2. Click en **API Keys**
3. Click en **Create a new API Key**
4. Copiar la API Key (¡solo se muestra una vez!)

**IMPORTANTE**: Guardar esta API Key, se necesitará para configurar Shuffle.

**5. Configurar Webhook en TheHive:**

1. Editar `application.conf` de TheHive:

```bash
docker exec -it soar_thehive bash
vi /etc/thehive/application.conf
```

2. Agregar configuración de webhook:

```python
webhook {
  url = "http://shuffle-backend:5001/api/v1/hooks/webhook_WEBHOOK_ID"
}
```

3. Configurar notificaciones en TheHive: Ir a **Admin** > **Webhooks**, crear nuevo webhook apuntando a Shuffle,
   seleccionar eventos (Case created, Alert created, Case updated).

4. Reiniciar TheHive:

```bash
docker restart soar_thehive
```

#### 3.2.5 Paso 5: configuración de Cortex

**Sitio Oficial**: [Cortex Project](https://thehive-project.org/cortex)
**Documentación**: [Cortex Documentation](https://docs.strangebee.com/cortex/)
**GitHub**: [TheHive-Project/Cortex](https://github.com/TheHive-Project/Cortex)

**1. Acceder a Cortex:**
Similar a TheHive, el primer paso es acceder a la interfaz web de Cortex para realizar la configuración inicial.
URL: https://localhost/cortex/ o http://localhost:9001/

[CAPTURA: Screenshot de la página de login de Cortex.](https://localhost/cortex/ #screenshot-11-cortex-login)

**2. Crear Usuario Admin:**

- Usuario: `admin@cortex.local`
- Contraseña: `secret`
- Cambiar contraseña al primer login

**3. Crear Organización:**

1. Ir a **Organizations**
2. Click en **New Organization**
3. Nombre: `SOAR Lab`
4. Descripción: `Laboratorio SOAR para ransomware`

**4. Configurar Analyzers:**

1. Ir a **Organization** > **Analyzers**
2. Verificar que analyzers como `VirusTotal_3`, `MISP_Search`, `IPInfo` estén habilitados

**5. Generar API Key:**

1. Ir a tu perfil
2. Click en **API Keys**
3. Click en **Create a new API Key**
4. Copiar la API Key

**6. Configurar Analyzers Adicionales:**
Analyzers recomendados:

- Shodan (para IPs y puertos abiertos)

- Hybrid Analysis (para análisis de malware)

- AlienVault OTX (para threat intelligence)

- Have I Been Pwned (para credenciales comprometidas)
    - Requiere API Key de HIBP
    - Verifica si emails/contraseñas han sido comprometidos
    - Referencia: [Have I Been Pwned](https://haveibeenpwned.com/)

**Configuración de Analyzers:**

1. Ir a **Organization** > **Analyzers**
2. Buscar el analyzer deseado
3. Click en **Enable**
4. Configurar la API Key requerida
5. Click en **Test** para verificar conexión

**Referencia**: [Cortex Analyzers Documentation](https://docs.strangebee.com/cortex/analyzer-tutorial/)

#### 3.2.6 Paso 6: configuración de Shuffle

**Sitio Oficial**: [Shuffle SOAR](https://shuffler.io/)
**Documentación**: [Shuffle Documentation](https://shuffler.io/docs)
**GitHub**: [Shuffle/Shuffle](https://github.com/Shuffle/Shuffle)
**Apps**: [Shuffle/openapi-apps](https://github.com/Shuffle/openapi-apps)

Shuffle es la plataforma de automatización de orquestación SOAR del laboratorio. Permite crear workflows que conectan
diferentes servicios y automatizan la respuesta a incidentes. Esta sección configura Shuffle y sus componentes
principales.

**1. Acceder a Shuffle:**
El primer paso es acceder a la interfaz web de Shuffle para realizar la configuración inicial del usuario y
organización.
URL: https://localhost:8081/ o http://localhost:8081/

[CAPTURA: Screenshot de la página de login de Shuffle.](https://localhost:8081/ #screenshot-16-shuffle-login)

**2. Crear Usuario Admin:**
Si es el primer acceso a Shuffle, debes crear un usuario administrador. Las credenciales predeterminadas se pueden
modificar en el archivo `.env.full` antes del despliegue.

Si es el primer acceso:

- Usuario: `admin`
- Contraseña: `R3x#7mP9$vK4@nQ2tW8!zY5&hF1sD3` (configurado en .env.full)

[CAPTURA: Screenshot de la página de login de Shuffle con credenciales ingresadas.](https://localhost:8081/
#screenshot-17-shuffle-login-creds)

**3. Crear Organización:**
Las organizaciones en Shuffle permiten agrupar workflows, apps y configuraciones. Crear una organización específica para
el laboratorio SOAR facilita la gestión de los workflows de ransomware.

1. Ir a **Organizations**
2. Click en **New Organization**
3. Nombre: `SOAR Lab`
4. Descripción: `Laboratorio SOAR para ransomware`

[CAPTURA: Screenshot del formulario de creación de organización en Shuffle.](https://localhost:8081/organizations
#screenshot-18-shuffle-org)

**4. Verificar Networking de Workers:**
El network-watcher es un servicio que conecta automáticamente los workers de Shuffle a la red Docker `soar_soar_net`.
Esto es crucial para que los workers puedan comunicarse con otros servicios del laboratorio. Verificar que esté
funcionando correctamente:

```bash
docker network inspect soar_soar_net
```

[CAPTURA: Screenshot de la salida de
`docker network inspect soar_soar_net` mostrando los contenedores conectados.](#screenshot-19-network-inspect)

**5. Generar API Key:**
La API Key de Shuffle es necesaria para autenticar requests a la API de Shuffle, especialmente para ejecutar workflows
vía webhook. Esta clave debe guardarse de forma segura.

1. Ir a tu perfil
2. Click en **API Keys**
3. Click en **Create new API Key**
4. Nombre: `SOAR Lab Key`
5. Copiar la API Key

[CAPTURA: Screenshot de la sección de API Keys en Shuffle.](https://localhost:8081/profile
#screenshot-20-shuffle-apikey)

#### 3.2.7 Paso 7: registro de apps en Shuffle

Shuffle utiliza apps para conectarse con diferentes servicios. Esta sección configura las apps de TheHive, Cortex, MISP
y Elasticsearch para que Shuffle pueda interactuar con estos servicios.

**1. Registrar App TheHive:**
TheHive es una de las apps principales que Shuffle utilizará para crear casos y alertas. Debe descargarse y configurarse
con las credenciales generadas anteriormente.

1. Ir a **Apps** en Shuffle
2. Buscar **TheHive** en el buscador
3. Click en **TheHive** app
4. Click en **Download/Install**

[CAPTURA: Screenshot de la página de TheHive app en Shuffle mostrando el botón Download/Install.](https://localhost:8081/apps/TheHive
#screenshot-21-shuffle-thehive-app)

**2. Configurar Autenticación TheHive:**
Una vez descargada la app, debes configurar la autenticación con la API Key y URL de TheHive generadas anteriormente.

1. Después de descargar, click en **Authentication**
2. Configurar:
    - **apikey**: [Pegar la API Key de TheHive generada anteriormente]
    - **url**: `http://thehive:9000`
3. Click en **Save**
4. Click en **Test** para verificar conexión

[CAPTURA: Screenshot del formulario de autenticación de TheHive en Shuffle mostrando los campos configurados.](https://localhost:8081/apps/TheHive
#screenshot-22-shuffle-thehive-auth)

[CAPTURA: Screenshot del resultado del test de conexión mostrando "Success".](#screenshot-23-shuffle-thehive-test)

**3. Registrar App Cortex:**
Similar a TheHive, Cortex debe registrarse para que Shuffle pueda ejecutar analyzers y obtener resultados de análisis.

1. Ir a **Apps**
2. Buscar **Cortex**
3. Click en **Download/Install**
4. Click en **Authentication**
5. Configurar:
    - **apikey**: [Pegar la API Key de Cortex generada anteriormente]
    - **url**: `http://cortex:9001`
6. Click en **Save**
7. Click en **Test**

[CAPTURA: Screenshot del formulario de autenticación de Cortex en Shuffle.](https://localhost:8081/apps/Cortex
#screenshot-24-shuffle-cortex-auth)

**4. Registrar App MISP:**
MISP es la plataforma de threat intelligence del laboratorio. Registrar esta app permite a Shuffle consultar IoCs y
crear eventos en MISP.

1. Ir a **Apps**
2. Buscar **MISP**
3. Click en **Download/Install**
4. Click en **Authentication**
5. Configurar:
    - **apikey**: [API Key de MISP]
    - **url**: `http://misp:8082`
6. Click en **Save**
7. Click en **Test**

[CAPTURA: Screenshot del formulario de autenticación de MISP en Shuffle.](https://localhost:8081/apps/MISP
#screenshot-25-shuffle-misp-auth)

**Integración Adicional MISP - Shuffle:**

**¿Por qué integrar MISP con Shuffle?**

- MISP es una plataforma de threat intelligence para compartir IoCs
- Shuffle puede consultar MISP para enriquecer alertas con información de amenazas
- Permite crear eventos en MISP desde workflows de Shuffle

**Configuración de Synchronization en MISP:**

1. Acceder a MISP: http://localhost:8082
2. Ir a **Event Actions** > **Automation**
3. Crear nuevo automation rule para enviar eventos a Shuffle:
    - **Trigger**: Cuando se crea un evento
    - **Action**: POST a webhook de Shuffle
    - **Format**: JSON con datos del evento

**Acciones MISP disponibles en Shuffle:**

- **search_attributes**: Buscar IoCs en MISP (IPs, dominios, hashes, emails)
- **create_event**: Crear evento en MISP desde Shuffle
- **add_attribute**: Añadir atributo a un evento existente
- **get_event**: Obtener detalles de un evento

**Caso de uso:**

1. Wazuh detecta una IP sospechosa
2. Shuffle recibe la alerta vía webhook
3. Shuffle consulta MISP con la IP
4. MISP devuelve información de amenazas asociadas
5. Shuffle decide si crear caso en TheHive basándose en la reputación

**Referencia**: [MISP Documentation](https://www.misp-project.org/documentation/)

**5. Registrar App Elasticsearch:**
Elasticsearch se utiliza para indexar datos de incidentes y ejecuciones. Registrar esta app permite a Shuffle almacenar
y consultar datos en Elasticsearch.

1. Ir a **Apps**
2. Buscar **Elasticsearch**
3. Click en **Download/Install**
4. Click en **Authentication**
5. Configurar:
    - **username**: `elastic`
    - **password**: [Contraseña de Elasticsearch de .env.full]
    - **url**: `http://elasticsearch:9200`
6. Click en **Save**
7. Click en **Test**

[CAPTURA: Screenshot del formulario de autenticación de Elasticsearch en Shuffle.](https://localhost:8081/apps/Elasticsearch
#screenshot-26-shuffle-es-auth)

#### 3.2.8 Paso 8: creación de workflows

Los workflows en Shuffle definen la lógica de automatización para responder a incidentes. Esta sección crea un workflow
de respuesta a ransomware que integra TheHive, Cortex y Elasticsearch.

**1. Crear Workflow de Respuesta a Ransomware:**
El primer paso es crear un nuevo workflow en Shuffle que orquestará la respuesta automatizada a incidentes de
ransomware.

1. Ir a **Workflows** en Shuffle
2. Click en **New Workflow**
3. Nombre: `Ransomware Response`
4. Descripción: `Workflow automatizado para respuesta a incidentes de ransomware`

[CAPTURA: Screenshot del formulario de creación de workflow en Shuffle.](https://localhost:8081/workflows
#screenshot-27-shuffle-workflow-create)

**2. Configurar Trigger Webhook:**
El trigger webhook permite que el workflow se inicie cuando se reciba una solicitud HTTP externa, como una alerta de
Wazuh o cualquier otro sistema.

1. En el panel izquierdo, buscar **Triggers**
2. Arrastrar **Webhook** al canvas
3. Click en el trigger webhook
4. Nombre: `Ransomware Alert`
5. Guardar

[CAPTURA: Screenshot del canvas de workflow mostrando el trigger webhook.](https://localhost:8081/workflows/{workflow_id}
#screenshot-28-shuffle-webhook-trigger)

**3. Agregar Acción: Crear Caso en TheHive:**
Esta acción crea un caso en TheHive cuando el workflow se ejecuta, permitiendo documentar y gestionar el incidente de
ransomware.

1. En el panel izquierdo, buscar **TheHive** app
2. Arrastrar acción **create_case** al canvas
3. Conectar el webhook a la acción
4. Configurar la acción:
    - **title**: `$exec.alert_id` - Ransomware Detection
    - **description**: `$exec.description`
    - **severity**: `$exec.severity`
    - **tags**: `ransomware,automated`
    - **tlp**: 2 (Amber)
    - **pap**: 2 (Amber)

[CAPTURA: Screenshot de la configuración de la acción create_case de TheHive.](https://localhost:8081/workflows/{workflow_id}
#screenshot-29-shuffle-thehive-action)

**4. Agregar Acción: Analizar IoCs con Cortex:**
Esta acción utiliza Cortex para analizar observables (como hashes) con analyzers como VirusTotal, proporcionando
información adicional sobre el malware.

1. Buscar **Cortex** app
2. Arrastrar acción **run_analyzer** al canvas
3. Conectar la acción anterior a esta
4. Configurar:
    - **analyzer**: `VirusTotal_3`
    - **data**: `$exec.hash`
    - **datatype**: `hash`

[CAPTURA: Screenshot de la configuración de la acción run_analyzer de Cortex.](https://localhost:8081/workflows/{workflow_id}
#screenshot-30-shuffle-cortex-action)

**5. Agregar Acción: Indexar en Elasticsearch:**
Esta acción indexa los datos del incidente en Elasticsearch para su posterior análisis y consulta.

1. Buscar **Elasticsearch** app
2. Arrastrar acción **create_index** al canvas
3. Conectar la acción anterior a esta
4. Configurar:
    - **index**: `ransomware-alerts`
    - **document**: JSON con todos los datos del incidente

[CAPTURA: Screenshot de la configuración de la acción create_index de Elasticsearch.](https://localhost:8081/workflows/{workflow_id}
#screenshot-31-shuffle-es-action)

**6. Guardar y Activar Workflow:**
Una vez configuradas todas las acciones, es necesario guardar el workflow y activarlo para que el webhook esté
disponible para recibir solicitudes.

1. Click en **Save** (icono de disquete)
2. Click en **Start** para activar el webhook

[CAPTURA: Screenshot del workflow completo mostrando todas las acciones conectadas.](https://localhost:8081/workflows/{workflow_id}
#screenshot-32-shuffle-workflow-complete)

**7. Obtener URL del Webhook:**
La Webhook URL es necesaria para que sistemas externos (como Wazuh) puedan enviar alertas al workflow.

1. Click en el trigger webhook
2. Copiar la **Webhook URL**

[CAPTURA: Screenshot mostrando la Webhook URL del trigger.](https://localhost:8081/workflows/{workflow_id}
#screenshot-33-shuffle-webhook-url)

#### 3.2.9 Paso 9: configuración de Wazuh

**Sitio Oficial**: [Wazuh](https://wazuh.com/)
**Documentación**: [Wazuh Documentation](https://documentation.wazuh.com/)
**GitHub**: [wazuh/wazuh](https://github.com/wazuh/wazuh)

Wazuh es el SIEM/XDR del laboratorio que detecta alertas de seguridad. Esta sección configura la integración de Wazuh
con Shuffle para automatizar la respuesta a incidentes.

**1. Acceder a Wazuh Manager:**
Wazuh está desplegado pero su API está en puerto interno. Para configurar el webhook, es necesario acceder al contenedor
directamente.

```bash
docker exec -it soar_wazuh_manager bash
```

**2. Configurar Webhook hacia Shuffle:**
Wazuh puede enviar alertas directamente a Shuffle vía webhook para automatizar respuestas.

**¿Por qué integrar Wazuh con Shuffle?**

- Wazuh detecta alertas de seguridad en tiempo real
- Shuffle puede orquestar respuestas automatizadas a estas alertas
- Permite crear casos en TheHive, analizar IoCs en Cortex, y más

**Configuración:**

1. Editar `/var/ossec/etc/ossec.conf`:

```xml
<integration>
  <name>custom-webhook</name>
  <hook_url>http://shuffle-backend:5001/api/v1/hooks/webhook_WEBHOOK_ID</hook_url>
  <api_format>json</api_format>
</integration>
```

2. Configurar reglas en Wazuh para disparar webhook:

- Editar `/var/ossec/rules/local_rules.xml`
- Agregar reglas para eventos de ransomware
- Configurar alert level para disparar webhook (ej: level >= 10)

Ejemplo de regla:

```xml
<rule id="100001" level="10">
  <field name="rule.groups">ransomware</field>
  <description>Ransomware detection - Trigger Shuffle webhook</description>
</rule>
```

**Referencia
**: [Wazuh Integration Documentation](https://documentation.wazuh.com/current/user-manual/reference/integrations/webhook.html)

[CAPTURA: Screenshot del archivo ossec.conf mostrando la configuración del webhook.](#screenshot-34-wazuh-webhook)

**3. Reiniciar Wazuh:**
Después de configurar el webhook, es necesario reiniciar Wazuh para que los cambios surtan efecto.

```bash
/var/ossec/bin/ossec-control restart
```

[CAPTURA: Screenshot de terminal mostrando Wazuh reiniciándose.](#screenshot-35-wazuh-restart)

#### 3.2.10 Paso 10: configuración de MISP

**Sitio Oficial**: [MISP Project](https://www.misp-project.org/)
**Documentación**: [MISP Documentation](https://www.misp-project.org/documentation/)
**GitHub**: [MISP/MISP](https://github.com/MISP/MISP)

MISP es la plataforma de threat intelligence del laboratorio. Permite compartir y consultar IoCs para enriquecer la
respuesta a incidentes. Esta sección configura MISP para su integración con Shuffle.

**1. Acceder a MISP:**
El primer paso es acceder a la interfaz web de MISP para realizar la configuración inicial.
URL: https://localhost/misp/ o http://localhost:8082/

[CAPTURA: Screenshot de la página de login de MISP.](https://localhost/misp/ #screenshot-36-misp-login)

**2. Crear Usuario:**
Al primer acceso, MISP requiere configurar un usuario administrador. Por seguridad, es importante cambiar la contraseña
inmediatamente después del primer login.

- Usuario: `admin@misp.local`
- Contraseña: `admin`
- Cambiar contraseña al primer login

[CAPTURA: Screenshot del formulario de cambio de contraseña de MISP.](https://localhost/misp/users/edit
#screenshot-37-misp-password)

**3. Generar Auth Key:**
La Auth Key es necesaria para que Shuffle pueda autenticarse con MISP y realizar acciones como consultar IoCs y crear
eventos. Esta clave debe guardarse de forma segura.

1. Ir a **Event Actions** > **Automation**
2. Click en **New Auth Key**
3. Copiar el Auth Key

[CAPTURA: Screenshot de la sección de Auth Keys en MISP.](https://localhost/misp/auth_keys/index
#screenshot-38-misp-authkey)

#### 3.2.11 Paso 11: pruebas end-to-end

Esta sección verifica que toda la integración del laboratorio SOAR esté funcionando correctamente. Se realizan pruebas
para asegurar que los workflows se ejecuten y que los servicios se comuniquen adecuadamente.

**1. Enviar Alerta de Prueba:**
El script Python envía una alerta de prueba al webhook de Shuffle para iniciar el workflow de respuesta a ransomware.

Usar el script Python:

```bash
python src/soar_lab/integrations/shuffle/test_workflow.py
```

[CAPTURA: Screenshot de la salida del script mostrando el webhook enviado y el worker creado en soar_soar_net.](#screenshot-39-test-workflow)

**2. Verificar Ejecución en Shuffle:**
Después de enviar la alerta de prueba, es importante verificar que el workflow se haya ejecutado correctamente en
Shuffle.

1. Ir a **Workflows** en Shuffle
2. Click en el workflow `Ransomware Response`
3. Click en **Executions**
4. Ver la ejecución más reciente

[CAPTURA: Screenshot de la ejecución del workflow mostrando el estado y resultados.](https://localhost:8081/workflows/{workflow_id}/executions
#screenshot-40-shuffle-execution)

**3. Verificar Caso en TheHive:**
Es importante verificar que el workflow haya creado correctamente el caso en TheHive con los datos de la alerta.

1. Ir a TheHive en http://localhost:9000
2. Verificar que se creó el caso

[CAPTURA: Screenshot del caso creado en TheHive.](https://localhost/thehive/case/{case_id} #screenshot-41-thehive-case)

**4. Verificar Análisis en Cortex:**
Verifica que el workflow haya ejecutado el analyzer en Cortex y que los resultados estén disponibles.

1. Ir a Cortex en http://localhost:9001
2. Verificar el análisis del hash

[CAPTURA: Screenshot del análisis en Cortex.](https://localhost/cortex/job/{job_id} #screenshot-42-cortex-analysis)

**5. Verificar Datos en Elasticsearch:**
Finalmente, verifica que los datos del incidente se hayan indexado correctamente en Elasticsearch para su posterior
análisis.

```bash
curl -u elastic:YOUR_PASSWORD http://localhost:9201/ransomware-alerts/_search
```

[CAPTURA: Screenshot de la respuesta de Elasticsearch mostrando los datos indexados.](#screenshot-43-es-search)

### 3.3 Verificación de configuración

#### 3.3.1 Resumen de URLs de acceso

Esta tabla resume todas las URLs de acceso a los servicios del laboratorio SOAR, incluyendo rutas de navegación
específicas y credenciales.

**Web Management UI**: http://localhost:8085 (Panel de control centralizado)

| Servicio            | URL                                                     | Rutas de Navegación                                                                                                                      | Credenciales                           |
|---------------------|---------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------|
| **Shuffle UI**      | https://localhost:8081/ o http://localhost:8081/        | `/workflows` - Lista de workflows<br>`/apps` - Catálogo de apps<br>`/organizations` - Organizaciones                                     | admin / R3x#7mP9$vK4@nQ2tW8!zY5&hF1sD3 |
| **Shuffle API**     | https://localhost/shuffle-api/ o http://localhost:5001/ | `/api/v1/workflows` - Workflows<br>`/api/v1/apps` - Apps<br>`/api/v1/hooks` - Webhooks                                                   | API Key de Shuffle                     |
| **TheHive**         | https://localhost/thehive/ o http://localhost:9000/     | `/` - Dashboard<br>`/api/case` - Casos<br>`/api/alert` - Alertas<br>`/admin` - Administración<br>`/admin/apikey` - API Keys              | admin@thehive.local / secret           |
| **Cortex**          | https://localhost/cortex/ o http://localhost:9001/      | `/` - Dashboard<br>`/analyzer` - Analyzers<br>`/organization` - Organización<br>`/user` - Usuario<br>`/apikey` - API Keys                | admin@cortex.local / secret            |
| **MISP**            | https://localhost/misp/ o http://localhost:8082/        | `/` - Dashboard<br>`/events` - Eventos<br>`/attributes` - Atributos<br>`/event_actions` - Acciones de evento<br>`/auth_keys` - Auth Keys | admin@misp.local / admin               |
| **Wazuh Dashboard** | https://localhost/kibana/ o http://localhost:15601/     | `/app/wazuh` - Dashboard Wazuh<br>`/app/discover` - Discover<br>`/app/visualize` - Visualizaciones                                       | elastic / YOUR_PASSWORD                |
| **API REST**        | https://localhost/api/ o http://localhost:8000/         | `/health` - Health check<br>`/docs` - API documentation<br>`/backups` - Backups                                                          | API Auth Secret                        |
| **Grafana**         | https://localhost/grafana/                              | `/` - Dashboard<br>`/datasources` - Fuentes de datos<br>`/dashboards` - Dashboards                                                       | admin / admin                          |
| **Documentation**   | http://localhost:8086/ o https://localhost/        | `/` - Documentación del proyecto                                                                                                         | -                                      |
| **Nginx Health**    | https://localhost/nginx-health                          | -                                                                                                                                        | -                                      |

#### 3.3.2 Scripts de automatización

Los scripts de Shuffle workflow están en:

- `src/soar_lab/integrations/shuffle/`

Scripts disponibles:

- `activate_workflow.py` - Activa workflow y guarda info
- `test_workflow.py` - Prueba workflow y verifica networking
- `check_execution.py` - Verifica resultado de ejecución
- `fix_workflow_thehive.py` - Arregla workflow para usar app TheHive

#### 3.3.3 Arquitectura de integraciones

**Flujo de Trabajo Típico:**

```
Wazuh (SIEM) → Shuffle (SOAR) → TheHive (Case Management)
                            ↓
                          Cortex (Analysis)
                            ↓
                          MISP (Threat Intelligence)
                            ↓
                          Elasticsearch (Logging)
```

**Ejemplo de Workflow de Respuesta a Ransomware:**

```
[Trigger] Wazuh Webhook
    ↓
[Action] Consultar MISP para verificar reputación de IP/hash
    ↓
[Condition] Si es malicioso:
    ↓
[Action] Analizar con VirusTotal (Cortex)
    ↓
[Action] Crear caso en TheHive
    ↓
[Action] Indexar en Elasticsearch
    ↓
[Action] Notificar analistas por email
```

**Integraciones Configuradas:**

1. **Wazuh → Shuffle**: Webhook para alertas de seguridad en tiempo real
2. **Shuffle → MISP**: Consulta de IoCs para enriquecimiento de amenazas
3. **Shuffle → Cortex**: Análisis de malware y observables
4. **Shuffle → TheHive**: Creación de casos y alertas
5. **TheHive → Shuffle**: Notificaciones de eventos vía webhook
6. **Shuffle → Elasticsearch**: Indexación de incidentes para análisis

**Estado Actual de Integraciones:**

- Los clientes de integración están implementados en `src/soar_lab/integrations/` (Cortex, MISP, Shuffle, TheHive)
- El uso de estos clientes en la aplicación Python es limitado
- La mayoría de la integración se realiza a través de la UI de Shuffle y sus apps
- La integración programática vía Python requiere configuración adicional

### 3.4 Troubleshooting

#### 3.4.1 Workers no se conectan a soar_soar_net

Si los workers de Shuffle no se conectan a la red Docker correcta, las ejecuciones de workflows fallarán. Verificar que
el network-watcher esté funcionando correctamente:

```bash
docker logs soar_network_watcher
```

#### 3.4.2 App TheHive no funciona

Si la app de TheHive no funciona en Shuffle, puede ser un problema de autenticación o configuración. Verificar que la
app esté descargada y autenticada correctamente. Revisar la API Key y URL de TheHive.

#### 3.4.3 Workflow se queda en "Step is still running"

Este error indica que un worker no está ejecutando el paso del workflow. Puede ser un problema de networking o de
autenticación de apps. Verificar que el worker esté en la red correcta y que las apps estén autenticadas correctamente.

### 3.5 Mantenimiento

#### 3.5.1 Backups

Realizar backups regulares de configuraciones y datos:

```bash
make backup
```

#### 3.5.2 Actualizaciones

Mantener las imágenes Docker actualizadas:

```bash
docker-compose pull
docker-compose up -d
```

#### 3.5.3 Monitoreo

Verificar el estado de servicios regularmente:

```bash
docker ps
docker logs soar_thehive
docker logs soar_cortex
docker logs soar_shuffle
```

## 4. Validación

### 4.1 Verificación

La configuración del laboratorio SOAR se considera exitosa cuando:

- Todos los servicios están ejecutándose y reportan estado healthy
- Las apps de Shuffle están descargadas, autenticadas y funcionando correctamente
- El workflow de respuesta a ransomware se ejecuta sin errores
- Las pruebas end-to-end pasan exitosamente
- Los servicios se comunican correctamente entre sí
- Los webhooks están configurados y funcionando

### 4.2 Criterios de Aceptación

La configuración del laboratorio SOAR se considera exitosa cuando se cumplen los criterios de verificación descritos en
la sección 4.1.

### 4.3 Evidencias

Las evidencias de configuración exitosa incluyen:

- Logs de contenedores sin errores críticos
- Ejecuciones de workflows exitosas en Shuffle
- Casos creados en TheHive
- Análisis ejecutados en Cortex
- Datos indexados en Elasticsearch
- Webhooks configurados y funcionando

## 5. Problemas y consideraciones

### 5.1 Limitaciones

**Limitaciones de Integración:**

- Algunos analyzers de Cortex requieren API keys externas (VirusTotal, Shodan, etc.)
- La integración Wazuh-Shuffle requiere configuración manual de reglas
- MISP requiere configuración adicional para sincronización bidireccional

### 5.2 Riesgos o incidencias

**Riesgos de Seguridad:**

- Las API keys deben guardarse de forma segura
- Las contraseñas predeterminadas deben cambiarse inmediatamente
- Los webhooks deben estar protegidos con autenticación

### 5.3 Recomendaciones / troubleshooting

**Troubleshooting:**

**Workers no se conectan a soar_soar_net:**
Si los workers de Shuffle no se conectan a la red Docker correcta, las ejecuciones de workflows fallarán. Verificar que
el network-watcher esté funcionando correctamente:

```bash
docker logs soar_network_watcher
```

**App TheHive no funciona:**
Si la app de TheHive no funciona en Shuffle, puede ser un problema de autenticación o configuración. Verificar que la
app esté descargada y autenticada correctamente. Revisar la API Key y URL de TheHive.

**Workflow se queda en "Step is still running":**
Este error indica que un worker no está ejecutando el paso del workflow. Puede ser un problema de networking o de
autenticación de apps. Verificar que el worker esté en la red correcta y que las apps estén autenticadas correctamente.

**Próximos Pasos:**

Una vez configurado el laboratorio SOAR, hay varias mejoras y extensiones que puedes implementar para enriquecer las
capacidades del sistema.

1. **Crear workflows adicionales** para otros tipos de incidentes
2. **Configurar más analyzers** en Cortex
3. **Integrar Wazuh** completamente con Shuffle
4. **Crear dashboards** en Kibana para visualización
5. **Configurar alertas** automáticas desde Wazuh a Shuffle

**Soporte:**

Si encuentras problemas o tienes preguntas durante la configuración u operación del laboratorio SOAR, hay varios
recursos disponibles para obtener ayuda.

Para problemas o preguntas:

- Revisar logs: `docker logs <container_name>`
- Documentación oficial: https://shuffler.io/docs
- TheHive docs: https://docs.strangebee.com/thehive/
- Cortex docs: https://docs.strangebee.com/cortex/

## 6. Referencias

**Referencias y Proyectos de Investigación:**

**Proyectos con Integración Webhook para Shuffle:**

**TheHive + Shuffle + MISP:**

- **Descripción**: Integración real-time entre TheHive, Shuffle y MISP para automatización de IoCs
- **Referencia
  **: [Real-time executions and IoC's with Shuffle, TheHive and MISP - Medium](https://medium.com/shuffle-automation/indicators-and-webhooks-with-thehive-cortex-and-misp-open-source-soar-part-4-f70cde942e59)
- **Webhook Config**: TheHive envía alertas a Shuffle vía webhook, Shuffle procesa y consulta MISP
- **Caso de uso**: Detección de IoCs desde texto, análisis con MISP, creación de casos en TheHive

**Wazuh + Shuffle + TheHive:**

- **Descripción**: SOC automation project integrando Wazuh SIEM con Shuffle y TheHive
- **Referencia
  **: [Wazuh, TheHive, and Shuffle — SOC Automation Project - Medium](https://medium.com/@jblemard/wazuh-thehive-and-shuffle-soc-automation-project-08ff58e0a4c9)
- **Webhook Config**: Wazuh envía alertas a Shuffle, Shuffle crea casos en TheHive, analiza con VirusTotal
- **Caso de uso**: Respuesta automatizada a alertas de Wazuh, análisis de malware, notificación a analistas

**Shuffle + VirusTotal + TheHive:**

- **Descripción**: Integración de Shuffle con VirusTotal y TheHive para análisis de malware
- **Referencia
  **: [Integrating Shuffle with Virustotal and TheHive - Medium](https://medium.com/shuffle-automation/integrating-shuffle-with-virustotal-and-thehive-open-source-soar-part-3-8e2e0d3396a9)
- **Webhook Config**: Shuffle analiza archivos con VirusTotal, crea casos en TheHive
- **Caso de uso**: Análisis automatizado de malware, creación de casos en TheHive

**TheHive Webhook Configuration:**

- **Documentación**: [TheHive Webhook Setup](https://docs.strangebee.com/thehive/api-docs/)
- **Config**: Editar `application.conf` para configurar URL de webhook
- **Endpoint**: POST al webhook de Shuffle con datos del caso/alerta

**Repositorios de Apps Shuffle:**

**OpenAPI Apps:**

- **Repositorio**: [Shuffle/openapi-apps](https://github.com/Shuffle/openapi-apps)
- **Descripción**: Apps generadas desde especificaciones OpenAPI de seguridad
- **Apps Relevantes**: TheHive (OpenAPI v5), Cortex, MISP, VirusTotal, Shodan

**Python Apps:**

- **Repositorio**: [Shuffle/python-apps](https://github.com/Shuffle/python-apps)
- **Descripción**: Apps Python personalizadas para Shuffle
- **Apps Relevantes**: TheHive, Cortex, MISP (versión antigua, ahora en OpenAPI)

**Tutoriales en YouTube:**

**Shuffle SOAR Tutorials:**

- **Automate Everything with Shuffle!** - [Video Tutorial](https://www.youtube.com/watch?v=_riaZjLnoXo)
- **Host Your Own SOAR - Shuffle Install** - [Video Tutorial](https://www.youtube.com/watch?v=YDUKZojg0vk)
- **Shuffle: Automated Workflows** - [Video Tutorial](https://www.youtube.com/watch?v=toqzkIN1urA)
- **SOC Open Source, Build own SOAR with Shuffle, ELK-TheHive-Cortex-MISP
  ** - [Video Tutorial](https://www.youtube.com/watch?v=Nb9_ahZMC5U)
- **Shuffle SOAR Home-Lab | Free Security Automation Tool
  ** - [Video Tutorial](https://www.youtube.com/watch?v=i2rRDB2N2w8)

**TheHive Tutorials:**

- **Installing TheHive 4.1.x in 12 minutes** - [Video Tutorial](https://www.youtube.com/watch?v=V_toQk19PuE)
- **TheHive - Build Your Own Security Operations Center (SOC)
  ** - [Video Tutorial](https://www.youtube.com/watch?v=VqIuP0AOCBg)
- **SOC Open Source, ELK- TheHive- Cortex- MISP Complete Setup Guide
  ** - [Video Tutorial](https://www.youtube.com/watch?v=t6PqjLIVgdA)
- **#1 Cyber-SOC - Configurer TheHive et Cortex pour un SOC avec Wazuh
  ** - [Video Tutorial](https://www.youtube.com/watch?v=OiuTbNhMw1A)

**Cortex Tutorials:**

- **How to enable Cortex analyzers** - [Video Tutorial](https://www.youtube.com/watch?v=YuMn02vTe5k)
- **CORTEX - Analyze Observables (IPs, domains, etc.) at Scale!
  ** - [Video Tutorial](https://www.youtube.com/watch?v=qz6xtINwK3I)
- **TheHive and Cortex Integration** - [Video Tutorial](https://www.youtube.com/watch?v=lzsTSDJhAOw)
- **Leveraging TheHive & Cortex for automated IR** - [Video Tutorial](https://www.youtube.com/watch?v=K6K1fNpbf9w)

**MISP Tutorials:**

- **How to Build Your First MISP Instance From Scratch** - [Video Tutorial](https://www.youtube.com/watch?v=fP28LXD8IU8)
- **Cómo Instalar MISP: Configuración Rápida y Sencilla
  ** - [Video Tutorial](https://www.youtube.com/watch?v=koCj1waK9RM)
- **MISP General Usage Training - Part 1 of 2** - [Video Tutorial](https://www.youtube.com/watch?v=-NuODyh1YJE)
- **How to Create MISP Events and Add Threat Intelligence
  ** - [Video Tutorial](https://www.youtube.com/watch?v=sWOa4Ld4CQM)
- **MISP Install and Intro** - [Video Tutorial](https://www.youtube.com/watch?v=nZcTc60YsIs)

**Wazuh Tutorials:**

- **SOAR-Installation Wazuh - Open Source XDR & SIEM Part3
  ** - [Video Tutorial](https://www.youtube.com/watch?v=p2LCsizVMNI)
- **Deploy Your Open Source SOAR Platform in One Command
  ** - [Video Tutorial](https://www.youtube.com/watch?v=NtBy9u1b7MM)
- **Shuffle + Wazuh + TheHIVE + Cortex = Automation Bliss
  ** - [Video Tutorial](https://www.youtube.com/watch?v=FBISHA7V15c)
- **WAZUH – prezentacja rozwiązania SIEM/SOAR/XDR** - [Video Tutorial](https://www.youtube.com/watch?v=UO5UDG10iSk)

**Issues y Discussions Relevantes:**

**TheHive App Issues:**

- **Issue #205**: [TheHive: update/patch cases](https://github.com/Shuffle/python-apps/issues/205)
- **Descripción**: Feature request para actualizar campos de casos en TheHive desde Shuffle

**TheHive + Shuffle Integration:**

- **Issue #1502**: [Unable to integrate Shuffle with TheHive and Wazuh](https://github.com/Shuffle/Shuffle/issues/1502)
- **Descripción**: Problemas de integración entre Shuffle, TheHive y Wazuh

**Documentación Oficial de APIs:**

**TheHive API:**

- **Documentación**: [TheHive 5 API Documentation](https://docs.strangebee.com/thehive/api-docs/)
- **Endpoints Relevantes**: `POST /api/case`, `POST /api/alert`, `GET /api/case/{id}`, `PATCH /api/case/{id}`

**Cortex API:**

- **Documentación**: [Cortex API Documentation](https://docs.strangebee.com/cortex/api-docs/)
- **Endpoints Relevantes**: `POST /api/analyzer/run`, `GET /api/analyzer/{id}`

**Docker Templates de Referencia:**

**TheHive + Cortex + MISP + Shuffle:**

- **Repositorio**: [TheHive-Project/Docker-Templates](https://github.com/TheHive-Project/Docker-Templates)
- **Template
  **: [docker/thehive4-cortex3-misp-shuffle/README.md](https://github.com/TheHive-Project/Docker-Templates/blob/main/docker/thehive4-cortex3-misp-shuffle/README.md)
- **Descripción**: Configuración Docker completa para TheHive, Cortex, MISP y Shuffle

**Referencias Generales:**

- **Repositorio del Proyecto**: [alesanfe/soar-ransomware-lab](https://github.com/alesanfe/soar-ransomware-lab.git)
- **Documentación de Shuffle**: https://shuffler.io/docs
- **Documentación de TheHive**: https://docs.strangebee.com/thehive/
- **Documentación de Cortex**: https://docs.strangebee.com/cortex/
- **Documentación de MISP**: https://www.misp-project.org/documentation/
- **Documentación de Wazuh**: https://documentation.wazuh.com/
- **Documentación de Elasticsearch**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **Documentación de Docker Compose**: https://docs.docker.com/compose/
