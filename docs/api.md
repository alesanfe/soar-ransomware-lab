# SOAR Ransomware Lab - API Documentation

> Complete API documentation for the SOAR Ransomware Lab components, including real integrations (TheHive, Cortex, Shuffle) and simulated services (SIEM, EDR, Firewall).

## Table of Contents

1. [Overview](#overview)
2. [Integration Inventory](#integration-inventory)
3. [Authentication](#authentication)
4. [Real APIs](#real-apis)
5. [Simulated APIs](#simulated-apis)
6. [Alert Schema](#alert-schema)
7. [Response Codes](#response-codes)
8. [Rate Limiting](#rate-limiting)
9. [Error Handling](#error-handling)
10. [Examples](#examples)
11. [Testing](#testing)

---

## Overview

The SOAR Ransomware Lab provides REST APIs for integrating with various security components. The system differentiates between **real services** (TheHive, Cortex, Shuffle) that operate in the environment and **simulated services** (SIEM, EDR, Firewall) used for testing without commercial dependencies.

### Base URLs

- **Development**: `http://localhost:5001/api/v1`
- **Production**: `https://your-domain.com/api/v1`

### API Versions

- **v1**: Current stable version
- **v2**: Beta version (experimental)

---

## Integration Inventory

This section provides a high-level view of all integrations, clearly distinguishing between **real** services operating in the environment and **simulations** used for testing flows.

| Integration | Type | Description |
|---|---|---|
| **TheHive** | **Real** | Case management, observables, attachments, and status updates. Consumed by Shuffle API/Orchestrator. |
| **Cortex** | **Real** | Execution of analyzers (hash/IP/hostname), returning `score`/`verdict`. |
| **Shuffle** | **Real** | Input webhook and E2E flow orchestration. |
| **SIEM simulado** | **Simulated** | Emits alerts to `/webhook` (Shuffle). No real commercial SIEM. |
| **EDR simulado** | **Simulated** | Simulated containment actions (isolate host). No commercial EDR agent. |
| **Firewall simulado** | **Simulated** | Simulated IP/egress blocking actions. |

> **Note**: Simulated integrations are implemented as **mock endpoints** served by Shuffle itself (HTTP App/flow) or a simple local microservice, and **do not** interact with production systems.

---

## Authentication

All API requests require authentication using Bearer tokens configured in `.env` (not versioned).

### Environment Variables

```env
# Base URLs
THEHIVE_BASE_URL=http://localhost:9000
CORTEX_BASE_URL=http://localhost:9001
SHUFFLE_BASE_URL=http://localhost:5001

# Authentication
THEHIVE_API_KEY=***
CORTEX_API_KEY=***
SHUFFLE_API_TOKEN=***

# Webhook (SIEM → Shuffle)
SIEM_WEBHOOK_TOKEN=***

# Simulated (EDR/Firewall)
EDR_SIM_TOKEN=***
FIREWALL_SIM_TOKEN=***

# Decision parameters
DECISION_SCORE_THRESHOLD=80
```

### Headers

```http
Authorization: Bearer <your-api-token>
Content-Type: application/json
```

### Security Policy

- Tokens are **rotated** every 90 days and stored only in `.env` or local vault
- Real services (TheHive/Cortex/Shuffle) use **API key** in `Authorization: Bearer <TOKEN>` header
- Simulated services use **separate tokens** to avoid confusion and test authentication routes

---

## Real APIs

### TheHive API

TheHive acts as the incident recording system. Create cases, attach observables (IoCs), and update status.

#### Create Case
```http
POST ${THEHIVE_BASE_URL}/api/case
Authorization: Bearer ${THEHIVE_API_KEY}
Content-Type: application/json

{
  "title": "Ransomware alert",
  "severity": 2,
  "tags": ["ransomware", "demo"],
  "description": "Case generated from webhook"
}
```

#### Add Observable
```http
POST ${THEHIVE_BASE_URL}/api/observable
Authorization: Bearer ${THEHIVE_API_KEY}
Content-Type: application/json

{
  "caseId": "<CASE_UUID>",
  "dataType": "hash",
  "data": "<SHA256>",
  "tags": ["ioc"]
}
```

#### Update Case Status
```http
PATCH ${THEHIVE_BASE_URL}/api/case/<CASE_UUID>
Authorization: Bearer ${THEHIVE_API_KEY}
Content-Type: application/json

{
  "status": "Contained",
  "summary": "Simulated containment executed",
  "tags": ["contained"]
}
```

> **Idempotency**: Before creating case, search by `alert_id`/`hash` in time window T; if exists, attach/update instead of creating.

### Cortex API

Cortex provides the intelligence needed for flow decisions. Request analyzer execution on different IoC types.

#### Execute Hash Analyzer
```http
POST ${CORTEX_BASE_URL}/api/analyzers/run
Authorization: Bearer ${CORTEX_API_KEY}
Content-Type: application/json

{
  "analyzer": "HashInfo",
  "input": {
    "type": "hash",
    "value": "<SHA256>"
  }
}
```

#### Response Example
```json
{
  "score": 85,
  "verdict": "malicious",
  "raw": {"source": "demo"}
}
```

### Shuffle API

Shuffle is the system entry point and playbook orchestrator. Receives alerts via webhook, validates payload, and coordinates actions with TheHive and Cortex.

#### Alert Webhook (Input)
```http
POST ${SHUFFLE_BASE_URL}/webhook
Authorization: Bearer ${SIEM_WEBHOOK_TOKEN}
Content-Type: application/json

{
  "alert_id": "A-2025-000123",
  "hostname": "WIN-001",
  "ip": "10.0.0.20",
  "hash": "<SHA256>",
  "severity": 2,
  "source": "siem-sim"
}
```

#### Health Check (Optional)
```http
GET ${SHUFFLE_BASE_URL}/health
```

---

## Simulated APIs

Simulated endpoints allow validating playbook decisions without executing actions on real infrastructure. Their purpose is to **record** the intention (isolate, block) and **attach evidence** in TheHive, returning controlled responses for testing.

### SIEM Simulated → Shuffle

Emulates a commercial SIEM sending alerts to Shuffle webhook. Useful for ingestion testing, schema validation, and rate limiting without third-party dependencies.

- **Description**: External **simulated** service emitting POST to Shuffle webhook
- **Endpoint**: `POST ${SHUFFLE_BASE_URL}/webhook`
- **Auth**: `Authorization: Bearer ${SIEM_WEBHOOK_TOKEN}`
- **Payload**: See [Alert Schema](#alert-schema)

### EDR Simulated

Represents **endpoint containment** actions without commercial agent.

#### Isolate Host (Simulated)
```http
POST ${SHUFFLE_BASE_URL}/simulate/edr/isolate
Authorization: Bearer ${EDR_SIM_TOKEN}
Content-Type: application/json

{
  "case_id": "<CASE_UUID>",
  "hostname": "WIN-001",
  "reason": "Malicious score ≥ threshold"
}
```

#### Response
```json
{
  "status": "accepted",
  "action": "isolate",
  "simulation": true
}
```

### Firewall Simulated

Allows testing **IP/egress** blocking as response to detections without touching a real firewall.

#### Block IP (Simulated)
```http
POST ${SHUFFLE_BASE_URL}/simulate/firewall/block
Authorization: Bearer ${FIREWALL_SIM_TOKEN}
Content-Type: application/json

{
  "case_id": "<CASE_UUID>",
  "ip": "10.0.0.20",
  "ttl_minutes": 15
}
```

#### Response
```json
{
  "status": "accepted",
  "action": "block",
  "ip": "10.0.0.20",
  "simulation": true
}
```

> **Implementation**: These endpoints can be handled by a **HTTP flow** in Shuffle that only **records** the action, attaches evidence in TheHive, and returns `202`.

---

## Alert Schema

### Minimal Schema (for Simulation)
```json
{
  "alert_id": "string",
  "hostname": "string",
  "ip": "ipv4",
  "hash": "sha256",
  "severity": "0-3",
  "source": "string"
}
```

### Complete Schema (Production)
```json
{
  "alert": {
    "alert_id": "ALERT-20240503123456-0001",
    "hostname": "WIN-001",
    "src_ip": "192.168.1.100",
    "hash": {
      "sha256": "44d88612fea8a8f36de82e1278abb02f44d88612fea8a8f36de82e1278abb02f",
      "md5": "d41d8cd98f00b204e9800998ecf8427e",
      "sha1": "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    },
    "severity": "2",
    "source": "siem-ransomware-detection",
    "detection_time": "2024-05-03T12:34:56Z",
    "event_type": "ransomware_detection",
    "description": "Ransomware activity detected on WIN-001",
    "affected_files": [
      {
        "path": "C:\\Users\\Documents\\important.docx",
        "name": "important.docx",
        "size": 1024000,
        "extension": "docx",
        "encrypted": true
      }
    ],
    "mitre_tactics": ["TA0040"],
    "mitre_techniques": ["T1486"],
    "network_events": [
      {
        "src_ip": "192.168.1.100",
        "dst_ip": "185.220.101.182",
        "dst_port": 443,
        "protocol": "TCP"
      }
    ]
  },
  "metadata": {
    "source_system": "splunk",
    "rule_name": "ransomware_detection_v2",
    "confidence": 95
  },
  "timestamp": "2024-05-03T12:34:56Z",
  "version": "1.0"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| alert_id | string | Yes | Alert ID in format `ALERT-timestamp-sequence` |
| hostname | string | Yes | Target hostname |
| src_ip | string | Yes | Source IP address |
| hash | object | Yes | File hash information |
| severity | string | Yes | Severity level (0-3) |
| source | string | Yes | Alert source |
| detection_time | string | Yes | ISO 8601 timestamp |
| event_type | string | Yes | Event type |
| description | string | Yes | Alert description |
| affected_files | array | No | List of affected files |
| mitre_tactics | array | No | MITRE ATT&CK tactics |
| mitre_techniques | array | No | MITRE ATT&CK techniques |
| network_events | array | No | Network events |

---

## Response Codes

### Success Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created |
| 202 | Accepted - Request accepted for processing |

### Client Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request - Invalid request format |
| 401 | Unauthorized - Authentication failed |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |

### Server Error Codes

| Code | Meaning |
|------|---------|
| 500 | Internal Server Error |
| 502 | Bad Gateway |
| 503 | Service Unavailable |
| 504 | Gateway Timeout |

---

## Rate Limiting

### Limits

- **Webhook (Shuffle)**: Rate limit **60 req/min**; Payload size ≤ **64 KB**
- **Cortex (analyzers)**: **Maximum concurrency 3**; `timeout` per job **≤ 30 s**; **retry: 1**
- **TheHive**: `retry: 1` on 5xx; **Idempotent** operations on `alert_id`
- **Simulated services**: Accept requests but **do not** execute real actions

### Headers

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1714767890
```

### Rate Limit Exceeded Response

```json
{
  "status": "error",
  "message": "Rate limit exceeded",
  "retry_after": 60,
  "timestamp": "2024-05-03T12:34:57Z"
}
```

---

## Error Handling

### Standard Error Response Format

All error responses follow this format:

```json
{
  "status": "error",
  "message": "Human-readable error message",
  "error_code": "VALIDATION_ERROR",
  "errors": [
    {
      "field": "field.name",
      "message": "Specific field error"
    }
  ],
  "timestamp": "2024-05-03T12:34:57Z",
  "request_id": "req_1234567890"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| VALIDATION_ERROR | Request validation failed |
| AUTHENTICATION_ERROR | Authentication failed |
| AUTHORIZATION_ERROR | Insufficient permissions |
| RATE_LIMIT_ERROR | Rate limit exceeded |
| INTERNAL_ERROR | Internal server error |
| SERVICE_UNAVAILABLE | Service temporarily unavailable |

---

## Examples

### Python Example

```python
import requests
import json
from datetime import datetime, timezone

# Configuration
WEBHOOK_URL = "http://localhost:5001/api/v1/webhooks/siem"
API_TOKEN = "your-siem-webhook-token"

# Alert data
alert_data = {
    "alert": {
        "alert_id": "ALERT-20240503123456-0001",
        "hostname": "WIN-001",
        "src_ip": "192.168.1.100",
        "hash": {
            "sha256": "44d88612fea8a8f36de82e1278abb02f44d88612fea8a8f36de82e1278abb02f"
        },
        "severity": "2",
        "source": "siem-ransomware-detection",
        "detection_time": datetime.now(timezone.utc).isoformat(),
        "event_type": "ransomware_detection",
        "description": "Ransomware activity detected on WIN-001"
    },
    "metadata": {
        "source_system": "splunk",
        "rule_name": "ransomware_detection_v2"
    },
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "version": "1.0"
}

# Headers
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Send request
response = requests.post(WEBHOOK_URL, json=alert_data, headers=headers)

if response.status_code == 200:
    print("Alert sent successfully")
    print(f"Response: {response.json()}")
else:
    print(f"Error: {response.status_code}")
    print(f"Response: {response.json()}")
```

### curl Example

```bash
#!/bin/bash

WEBHOOK_URL="http://localhost:5001/api/v1/webhooks/siem"
API_TOKEN="your-siem-webhook-token"

curl -X POST "$WEBHOOK_URL" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alert": {
      "alert_id": "ALERT-20240503123456-0001",
      "hostname": "WIN-001",
      "src_ip": "192.168.1.100",
      "hash": {
        "sha256": "44d88612fea8a8f36de82e1278abb02f44d88612fea8a8f36de82e1278abb02f"
      },
      "severity": "2",
      "source": "siem-ransomware-detection",
      "detection_time": "2024-05-03T12:34:56Z",
      "event_type": "ransomware_detection",
      "description": "Ransomware activity detected on WIN-001"
    },
    "metadata": {
      "source_system": "splunk",
      "rule_name": "ransomware_detection_v2"
    },
    "timestamp": "2024-05-03T12:34:56Z",
    "version": "1.0"
  }'
```

### PowerShell Example

```powershell
# Configuration
$WebhookUrl = "http://localhost:5001/api/v1/webhooks/siem"
$ApiToken = "your-siem-webhook-token"

# Alert data
$AlertData = @{
    alert = @{
        alert_id = "ALERT-20240503123456-0001"
        hostname = "WIN-001"
        src_ip = "192.168.1.100"
        hash = @{
            sha256 = "44d88612fea8a8f36de82e1278abb02f44d88612fea8a8f36de82e1278abb02f"
        }
        severity = "2"
        source = "siem-ransomware-detection"
        detection_time = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        event_type = "ransomware_detection"
        description = "Ransomware activity detected on WIN-001"
    }
    metadata = @{
        source_system = "splunk"
        rule_name = "ransomware_detection_v2"
    }
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    version = "1.0"
}

# Headers
$Headers = @{
    "Authorization" = "Bearer $ApiToken"
    "Content-Type" = "application/json"
}

# Send request
try {
    $Response = Invoke-RestMethod -Uri $WebhookUrl -Method Post -Body ($AlertData | ConvertTo-Json) -Headers $Headers
    Write-Host "Alert sent successfully"
    Write-Host "Response: $($Response | ConvertTo-Json -Depth 3)"
}
catch {
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host "Status Code: $($_.Exception.Response.StatusCode)"
}
```

---

## Testing

### Test Environment

- **URL**: `http://localhost:5001/api/v1/webhooks/siem`
- **Token**: `test-token`
- **Rate Limit**: 1000 requests per minute

### Test Cases

#### Valid Alert Test

```bash
curl -X POST "http://localhost:5001/api/v1/webhooks/siem" \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{"alert":{"alert_id":"ALERT-TEST-0001","hostname":"TEST-001","src_ip":"192.168.1.1","hash":{"sha256":"44d88612fea8a8f36de82e1278abb02f44d88612fea8a8f36de82e1278abb02f"},"severity":"2","source":"test","detection_time":"2024-05-03T12:34:56Z","event_type":"ransomware_detection","description":"Test alert"}}'
```

#### Invalid Alert Test

```bash
curl -X POST "http://localhost:5001/api/v1/webhooks/siem" \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{"alert":{"alert_id":"INVALID","hostname":"TEST-001"}}'
```

### Success Response

```json
{
  "status": "success",
  "message": "Alert processed successfully",
  "alert_id": "ALERT-20240503123456-0001",
  "case_id": "CASE-12345",
  "timestamp": "2024-05-03T12:34:57Z"
}
```

### Error Response

```json
{
  "status": "error",
  "message": "Validation failed",
  "errors": [
    {
      "field": "alert.hash.sha256",
      "message": "Invalid SHA256 hash format"
    }
  ],
  "timestamp": "2024-05-03T12:34:57Z"
}
```

---

## SDK and Libraries

### Python SDK

```python
# Install the SOAR SDK
pip install soar-ransomware-sdk

# Usage
from soar_sdk import SOARClient

client = SOARClient(
    webhook_url="http://localhost:5001/api/v1/webhooks/siem",
    api_token="your-token"
)

# Send alert
response = client.send_alert(alert_data)
print(f"Alert sent: {response.alert_id}")
```

### JavaScript SDK

```javascript
// Install the SOAR SDK
npm install soar-ransomware-sdk

// Usage
import { SOARClient } from 'soar-ransomware-sdk';

const client = new SOARClient({
  webhookUrl: 'http://localhost:5001/api/v1/webhooks/siem',
  apiToken: 'your-token'
});

// Send alert
const response = await client.sendAlert(alertData);
console.log(`Alert sent: ${response.alertId}`);
```

---

## Changelog

### v1.0.0 (2024-05-03)

- Initial release
- Webhook API for alert ingestion
- Authentication with Bearer tokens
- Basic rate limiting
- Error handling and validation
- Real and simulated API documentation

### v1.1.0 (Planned)

- Enhanced validation rules
- Additional webhook endpoints
- Improved error messages
- Performance optimizations

---

## Support

### Documentation

- [User Guide](user_guide.md)
- [Troubleshooting](troubleshooting.md)
- [Security Guide](security.md)

### Contact

- **Issues**: [GitHub Issues](https://github.com/your-org/soar-ransomware-lab/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/soar-ransomware-lab/discussions)
- **Email**: support@your-domain.com

### Status

- **API Status**: [status.your-domain.com](https://status.your-domain.com)
- **Uptime Monitoring**: [uptime.your-domain.com](https://uptime.your-domain.com)
