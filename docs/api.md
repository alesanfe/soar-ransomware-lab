
# Integraciones mínimas/simuladas

> **Propósito**: especificar qué APIs son **reales** (TheHive/Cortex/Shuffle) y cuáles son **simuladas** (SIEM/EDR/Firewall), definiendo **endpoints**, **autenticación por tokens en `.env`**, **payloads de ejemplo** y **límites de uso**.

---

## 1. Inventario de APIs

Esta sección ofrece una vista de alto nivel de todas las integraciones del laboratorio, diferenciando claramente entre servicios **reales** que operan en el entorno (TheHive, Cortex, Shuffle) y **simulaciones** utilizadas para probar el flujo sin depender de productos comerciales (SIEM, EDR, Firewall). Sirve como mapa inicial para comprender qué componentes se consumen directamente y cuáles funcionan como *mock*.

| Integración | Tipo | Descripción breve |
|---|---|---|
| **TheHive** | **Real** | Gestión de casos, observables, adjuntos y estados. Consumida por Shuffle API/Orchestrator. |
| **Cortex** | **Real** | Ejecución de *analyzers* (hash/IP/hostname), retorno de `score`/`verdict`. |
| **Shuffle** | **Real** | Webhook de entrada y orquestación del flujo E2E. |
| **SIEM simulado** | **Simulada** | Emite alertas hacia `/webhook` (Shuffle). No hay SIEM comercial real. |
| **EDR simulado** | **Simulada** | Acciones de contención **simuladas** (aislar host). Sin agente EDR comercial. |
| **Firewall simulado** | **Simulada** | Acciones **simuladas** de bloqueo IP/egress. |

> Nota: las integraciones simuladas se implementan como **endpoints de mock** atendidos por el propio Shuffle (HTTP App/flow dedicado) o por un microservicio local sencillo, y **no** interactúan con sistemas de producción.

---

## 2. Autenticación y secretos (.env)

Definir los tokens y bases URL en `.env` (no versionado). Ejemplo:

```env
# Bases URL
THEHIVE_BASE_URL=http://localhost:9000
CORTEX_BASE_URL=http://localhost:9001
SHUFFLE_BASE_URL=http://localhost:5001

# Autenticación
THEHIVE_API_KEY=***
CORTEX_API_KEY=***
SHUFFLE_API_TOKEN=***

# Webhook (SIEM → Shuffle)
SIEM_WEBHOOK_TOKEN=***

# Simulados (EDR/Firewall)
EDR_SIM_TOKEN=***
FIREWALL_SIM_TOKEN=***

# Parámetros de decisión
DECISION_SCORE_THRESHOLD=80
```

**Política mínima**:
- Los tokens se **rotan** cada 90 días y se almacenan sólo en `.env` o *vault* local.
- Los servicios reales (TheHive/Cortex/Shuffle) usan **API key** en cabecera `Authorization: Bearer <TOKEN>`.
- Los simulados usan un **token separado** para evitar confusiones y probar rutas de autenticación.

---

## 3. Endpoints — **Reales**

Los endpoints reales son los contratos que el flujo E2E consume en tiempo de ejecución. Están pensados para ser **predecibles**, **versionados** y **parametrizables** mediante variables de entorno. A continuación se detallan las rutas principales para crear y actualizar casos en TheHive, ejecutar analyzers en Cortex y recibir alertas en Shuffle.

> Las rutas se parametrizan con las variables `*_BASE_URL`. Los ejemplos asumen `localhost` y puertos por defecto del laboratorio.

### 3.1 TheHive (Real)

TheHive actúa como el sistema de registro del incidente. Aquí definimos cómo **crear** el caso, **adjuntar** observables (IoCs) y **actualizar** su estado para reflejar la decisión tomada por el playbook.

- **Crear caso**
  - `POST ${THEHIVE_BASE_URL}/api/case`
  - **Auth**: `Authorization: Bearer ${THEHIVE_API_KEY}`
  - **Body (JSON)**:
    ```json
    {
      "title": "Ransomware alert",
      "severity": 2,
      "tags": ["ransomware", "demo"],
      "description": "Caso generado desde webhook"
    }
    ```
- **Añadir observable**
  - `POST ${THEHIVE_BASE_URL}/api/observable`
  - **Body**:
    ```json
    {
      "caseId": "<CASE_UUID>",
      "dataType": "hash",
      "data": "<SHA256>",
      "tags": ["ioc"]
    }
    ```
- **Actualizar caso (estado)**
  - `PATCH ${THEHIVE_BASE_URL}/api/case/<CASE_UUID>`
  - **Body**:
    ```json
    {
      "status": "Contained",
      "summary": "Contención simulada ejecutada",
      "tags": ["contained"]
    }
    ```

> **Idempotencia**: antes de crear caso, buscar por `alert_id`/`hash` en ventana T; si existe, adjuntar/actualizar en lugar de crear.

### 3.2 Cortex (Real)

Cortex provee la **inteligencia** necesaria para la decisión del flujo. Este apartado documenta cómo solicitar la ejecución de analyzers sobre distintos tipos de IoC y cómo interpretar su resultado (`score`, `verdict`).

- **Ejecutar analyzer por hash**
  - `POST ${CORTEX_BASE_URL}/api/analyzers/run`
  - **Auth**: `Authorization: Bearer ${CORTEX_API_KEY}`
  - **Body**:
    ```json
    {
      "analyzer": "HashInfo",
      "input": {
        "type": "hash",
        "value": "<SHA256>"
      }
    }
    ```
  - **Respuesta (ejemplo)**:
    ```json
    {
      "score": 85,
      "verdict": "malicious",
      "raw": {"source": "demo"}
    }
    ```

### 3.3 Shuffle (Real)

Shuffle es la **puerta de entrada** del sistema y el **orquestador** del playbook. Recibe la alerta vía webhook, valida el payload y coordina las acciones con TheHive y Cortex.

- **Webhook de alerta (entrada)**
  - `POST ${SHUFFLE_BASE_URL}/webhook`
  - **Auth (token simple)**: `Authorization: Bearer ${SIEM_WEBHOOK_TOKEN}`
  - **Body (JSON)** — *schema mínimo*:
    ```json
    {
      "alert_id": "A-2025-000123",
      "hostname": "WIN-001",
      "ip": "10.0.0.20",
      "hash": "<SHA256>",
      "severity": 2,
      "source": "siem-sim"
    }
    ```
- **Salud del orquestador** (opcional)
  - `GET ${SHUFFLE_BASE_URL}/health`

---

## 4. Endpoints — **Simulados**

Los endpoints simulados permiten validar decisiones del playbook sin ejecutar acciones en infraestructura real. Su objetivo es **registrar** la intención (aislar, bloquear) y **adjuntar evidencias** en TheHive, devolviendo respuestas controladas para pruebas.

### 4.1 SIEM simulado → Shuffle

 Emula un producto SIEM enviando alertas al webhook de Shuffle. Es útil para pruebas de ingestión, validación de esquema y *rate‑limit* sin depender de terceros.

- **Descripción**: servicio externo **simulado** que emite POST al webhook de Shuffle.
- **Endpoint**: `POST ${SHUFFLE_BASE_URL}/webhook`
- **Auth**: `Authorization: Bearer ${SIEM_WEBHOOK_TOKEN}`
- **Payload**: ver 3.3.

### 4.2 EDR simulado

Representa acciones de **contención de endpoint** sin agente comercial. 

- **Aislar host (simulado)**
  - `POST ${SHUFFLE_BASE_URL}/simulate/edr/isolate`
  - **Auth**: `Authorization: Bearer ${EDR_SIM_TOKEN}`
  - **Body**:
    ```json
    {
      "case_id": "<CASE_UUID>",
      "hostname": "WIN-001",
      "reason": "Malicious score ≥ threshold"
    }
    ```
  - **Respuesta**: `202 Accepted`
    ```json
    {"status": "accepted", "action": "isolate", "simulation": true}
    ```

### 4.3 Firewall simulado

Permite ensayar bloqueos de **IP/egress** como respuesta a detecciones sin tocar un firewall real. Sirve para comprobar *payloads*, permisos y *timeouts*.

- **Bloquear IP (simulado)**
  - `POST ${SHUFFLE_BASE_URL}/simulate/firewall/block`
  - **Auth**: `Authorization: Bearer ${FIREWALL_SIM_TOKEN}`
  - **Body**:
    ```json
    {
      "case_id": "<CASE_UUID>",
      "ip": "10.0.0.20",
      "ttl_minutes": 15
    }
    ```
  - **Respuesta**: `202 Accepted`
    ```json
    {"status": "accepted", "action": "block", "ip": "10.0.0.20", "simulation": true}
    ```

> **Implementación**: estos endpoints pueden ser manejados por un **flow HTTP** en Shuffle que únicamente **registra** la acción, adjunta evidencia en TheHive y retorna `202`.

---

## 5. Esquema de payload (referencia)

- **Alerta (SIEM simulado)**
  ```json
  {
    "alert_id": "string",
    "hostname": "string",
    "ip": "ipv4",
    "hash": "sha256",
    "severity": 0-3,
    "source": "string"
  }
  ```
- **Analyzer request (Cortex)**
  ```json
  {
    "analyzer": "string",
    "input": {"type": "hash|ip|hostname", "value": "string"}
  }
  ```
- **Contención simulada (EDR/Firewall)**
  ```json
  {
    "case_id": "uuid",
    "hostname": "string",
    "ip": "ipv4",
    "reason": "string",
    "ttl_minutes": 0-60
  }
  ```

---

## 6. Límites de uso y *timeouts*

Establecer límites y *timeouts* evita la **degradación** del sistema bajo carga, protege servicios reales y produce métricas consistentes para el TFM. Estos valores pueden ajustarse según resultados de prueba.

- **Webhook (Shuffle)**: rate‑limit **60 req/min**; tamaño de payload ≤ **64 KB**.
- **Cortex (analyzers)**: **concurrencia máxima 3**; `timeout` por job **≤ 30 s**; **retry: 1**.
- **TheHive**: `retry: 1` en 5xx; operaciones **idempotentes** sobre `alert_id`.
- **Simulados**: aceptan peticiones pero **no** ejecutan acciones reales.

---

## 7. Manejo de errores (estándar)

Un formato de errores consistente y códigos HTTP estándar permiten diagnósticos rápidos, *fallbacks* adecuados y una mejor experiencia de pruebas.

- `400 Bad Request`: schema inválido / campos faltantes.
- `401 Unauthorized`: token ausente/incorrecto.
- `403 Forbidden`: token válido sin permisos.
- `404 Not Found`: recurso inexistente.
- `429 Too Many Requests`: límite superado.
- `5xx`: error de servicio → aplicar política de **retry** documentada.

**Formato de error**:
```json
{"error": {"code": 400, "message": "validation_failed", "details": {"field": "hash"}}}
```
