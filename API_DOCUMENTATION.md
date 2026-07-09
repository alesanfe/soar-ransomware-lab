# SOAR Ransomware Lab - API Documentation

This document provides comprehensive API documentation for all services and containers in the SOAR Ransomware Lab
environment.

## Table of Contents

- [SOAR Lab Management API](#soar-lab-management-api)
- [TheHive API](#thehive-api)
- [Cortex API](#cortex-api)
- [Shuffle API](#shuffle-api)
- [Shuffle Orborus API](#shuffle-orborus-api)
- [MISP API](#misp-api)
- [MISP Modules API](#misp-modules-api)
- [Wazuh API](#wazuh-api)
- [Elasticsearch API](#elasticsearch-api)
- [Kibana API](#kibana-api)
- [Redis API](#redis-api)
- [Docker API](#docker-api)
- [Network Watcher](#network-watcher)
- [Web Management UI](#web-management-ui)
- [Nginx Reverse Proxy](#nginx-reverse-proxy)
- [Non-API Services](#non-api-services)

---

## SOAR Lab Management API

**Container:** `soar_api`  
**Port:** 8000  
**Base URL:** `http://localhost:8000`  
**Documentation:** `http://localhost:8000/docs` (FastAPI auto-generated)

### Authentication

The API uses JWT token-based authentication. Login to obtain a token, then include it in the `Authorization` header.

**Login Endpoint:**

```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "X9e#5mP3$vL7@nQ4tW8!zY2&hF6sD1"
}
```

**Response:**

```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "Login successful",
  "token_type": "Bearer"
}
```

**Using the token:**

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Endpoints

#### Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2026-05-23T09:23:15.813140Z",
  "version": "1.0.0"
}
```

#### System Metrics

```http
GET /analytics/metrics
```

**Response:**

```json
{
  "cpu": 1.6,
  "memory": 44.1,
  "disk": 5.5,
  "timestamp": "2026-05-23T09:23:15.813140Z"
}
```

#### KPI Metrics

```http
GET /analytics/kpis?log_file_path=/path/to/log
```

**Response:**

```json
{
  "mttr": 3600,
  "mttd": 1800,
  "alert_volume": 150,
  "resolution_rate": 0.85
}
```

#### Services Status

```http
GET /services/status
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2026-05-23T09:23:15.813140Z",
  "version": "1.0.0"
}
```

#### Create Backup

```http
POST /backup/create
Content-Type: application/json

{
  "backup_name": "backup_20260523.tar.gz"
}
```

**Response:**

```json
{
  "backup_name": "backup_20260523.tar.gz",
  "status": "success",
  "message": "Backup created successfully"
}
```

#### List Backups

```http
GET /backup/list
```

**Response:**

```json
{
  "backups": [
    {
      "name": "backup_20260523.tar.gz",
      "size": "1.2GB",
      "date": "2026-05-23T09:00:00Z"
    }
  ]
}
```

#### Restore Backup

```http
POST /backup/restore
Content-Type: application/json

{
  "backup_name": "backup_20260523.tar.gz"
}
```

**Response:**

```json
{
  "backup_name": "backup_20260523.tar.gz",
  "status": "success",
  "message": "Backup restored successfully"
}
```

#### Run Tests

```http
POST /tests/run
Content-Type: application/json

{
  "category": "unit"
}
```

**Valid categories:** `unit`, `integration`, `e2e`, `atomic`, `performance`, `security`, `smoke`, `all`

**Response:**

```json
{
  "category": "unit",
  "passed": 657,
  "failed": 6,
  "skipped": 0,
  "coverage": 75.5,
  "output": "Test execution output...",
  "duration": 6.47
}
```

#### WebSocket Logs

```websocket
WS /ws/logs
```

Streams log entries in real-time:

```json
{
  "timestamp": "2026-05-23T09:23:15.813140Z",
  "level": "INFO",
  "message": "Simulated log entry"
}
```

---

## TheHive API

**Container:** `soar_thehive`  
**Port:** 9000  
**Base URL:** `http://localhost:9000/api`  
**Documentation:** [TheHive API Documentation](https://docs.strangebee.com/thehive/api-docs/)

### Authentication

TheHive uses API key authentication. Include the API key in the `Authorization` header.

```http
Authorization: Bearer <THEHIVE_API_KEY>
```

### Key Endpoints

#### Create Alert

```http
POST /api/alert
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "title": "Suspicious Activity Detected",
  "description": "Malware signature detected on endpoint",
  "type": "external",
  "source": "EDR",
  "sourceRef": "alert-12345",
  "tags": ["malware", "ransomware"],
  "severity": 2,
  "date": 1653300000000
}
```

#### List Alerts

```http
GET /api/alert
Authorization: Bearer <api_key>
```

#### Get Alert

```http
GET /api/alert/{alert_id}
Authorization: Bearer <api_key>
```

#### Create Case

```http
POST /api/case
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "title": "Ransomware Investigation",
  "description": "Investigation of ransomware incident",
  "severity": 2,
  "tags": ["ransomware", "incident"],
  "tlp": 2
}
```

#### List Cases

```http
GET /api/case
Authorization: Bearer <api_key>
```

#### Get Case

```http
GET /api/case/{case_id}
Authorization: Bearer <api_key>
```

#### Update Case

```http
PATCH /api/case/{case_id}
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "title": "Updated Case Title",
  "status": "Open",
  "severity": 2
}
```

#### Close Case

```http
PATCH /api/case/{case_id}
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "status": "Closed",
  "resolutionStatus": "TruePositive"
}
```

#### Add Observable

```http
POST /api/case/{case_id}/observable
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "dataType": "ip",
  "data": "192.168.1.100",
  "message": "Suspicious IP address",
  "tags": ["suspicious"]
}
```

#### Delete Observable

```http
DELETE /api/case/{case_id}/observable/{observable_id}
Authorization: Bearer <api_key>
```

#### Add Task

```http
POST /api/case/{case_id}/task
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "title": "Investigate IP address",
  "description": "Analyze the suspicious IP",
  "status": "InProgress"
}
```

#### List Tasks

```http
GET /api/case/{case_id}/task
Authorization: Bearer <api_key>
```

#### Update Task

```http
PATCH /api/case/{case_id}/task/{task_id}
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "title": "Updated task title",
  "status": "Completed"
}
```

#### Delete Task

```http
DELETE /api/case/{case_id}/task/{task_id}
Authorization: Bearer <api_key>
```

#### Promote Alert to Case

```http
POST /api/alert/{alert_id}/case
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "title": "Case from alert",
  "description": "Case description"
}
```

#### Merge Alert into Case

```http
POST /api/alert/{alert_id}/merge/{case_id}
Authorization: Bearer <api_key>
```

#### List Case Templates

```http
POST /api/case/_search
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "query": {}
}
```

#### Get Case Template

```http
GET /api/case/_search
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "query": {
    "_and": [
      {"_parent": {"_type": "case"}}
    ]
  }
}
```

**Note:** TheHive API uses search endpoints instead of direct list endpoints for templates.

#### Create Case from Template

```http
POST /api/case/_fromTemplate/{template_id}
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "title": "Case from template",
  "customFields": {
    "field1": "value1"
  }
}
```

#### List Custom Fields

```http
GET /api/case/{case_id}/customFields
Authorization: Bearer <api_key>
```

#### Update Custom Fields

```http
PATCH /api/case/{case_id}/customFields
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "field1": "new value"
}
```

#### Mark Observable as IOC

```http
PATCH /api/case/{case_id}/observable/{observable_id}
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "ioc": true,
  "sighted": true
}
```

#### Set PAP Level

```http
PATCH /api/case/{case_id}
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "pap": 2
}
```

**PAP Levels:**

- 0: White (no restrictions)
- 1: Green (minimal restrictions)
- 2: Amber (moderate restrictions)
- 3: Red (severe restrictions)

#### Share with MISP

```http
POST /api/case/{case_id}/export/misp
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "mispConfigId": "misp-config-id"
}
```

---

## Cortex API

**Container:** `soar_cortex`  
**Port:** 9001  
**Base URL:** `http://localhost:9001/api`  
**Documentation:** [Cortex API Guide](https://docs.strangebee.com/cortex/api/api-guide/)

**Note:** Cortex requires initial user configuration via the web interface before API endpoints are accessible. Access
`http://localhost:9001` to create the initial admin user. The first user must be created through the web UI - there is
no API endpoint or configuration file option for initial user creation.

**Important:** Do NOT use "cortex" as the organization name when creating the initial user. This is a known bug in
Cortex that causes an Elasticsearch mapping error (`unknown join name [user] for field [relations]`). Use any other
organization name (e.g., "SOAR Lab", "My Org", etc.).

### Authentication

Cortex uses API key authentication.

```http
Authorization: Bearer <CORTEX_API_KEY>
```

### Key Endpoints

#### List Analyzers

```http
GET /api/analyzer
Authorization: Bearer <api_key>
```

**Response:**

```json
[
  {
    "id": "VirusTotal_3_0",
    "name": "VirusTotal",
    "description": "Scan files and URLs with VirusTotal",
    "version": "3.0"
  }
]
```

#### Run Analyzer

```http
POST /api/analyzer/{analyzer_id}/run
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "data": [
    {
      "dataType": "ip",
      "data": "8.8.8.8",
      "tlp": 2
    }
  ]
}
```

**Response:**

```json
{
  "jobId": "job-12345",
  "status": "Waiting"
}
```

#### Get Job Status

```http
GET /api/job/{job_id}
Authorization: Bearer <api_key>
```

**Response:**

```json
{
  "id": "job-12345",
  "status": "Success",
  "analyzerId": "VirusTotal_3_0",
  "artifacts": [
    {
      "dataType": "ip",
      "data": "8.8.8.8"
    }
  ],
  "report": {
    "summary": {
      "taxonomies": [
        {
          "namespace": "VirusTotal",
          "predicate": "Suspicious",
          "value": "High"
        }
      ]
    }
  }
}
```

#### Get Job Report

```http
GET /api/job/{job_id}/report
Authorization: Bearer <api_key>
```

#### Delete Job

```http
DELETE /api/job/{job_id}
Authorization: Bearer <api_key>
```

#### List Responders

```http
GET /api/responder
Authorization: Bearer <api_key>
```

#### Run Responder

```http
POST /api/responder/{responder_id}/run
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "observableId": "observable-id",
  "caseId": "case-id"
}
```

#### List Organizations

```http
GET /api/organization
Authorization: Bearer <api_key>
```

#### Get User

```http
GET /api/user/me
Authorization: Bearer <api_key>
```

#### Create User

```http
POST /api/user
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "login": "username",
  "name": "Full Name",
  "role": "read",
  "organization": "org-id"
}
```

#### Update User

```http
PATCH /api/user/{user_id}
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "role": "analyze"
}
```

#### Delete User

```http
DELETE /api/user/{user_id}
Authorization: Bearer <api_key>
```

#### List Roles

```http
GET /api/role
Authorization: Bearer <api_key>
```

**Default Roles:**

- `read`: Read-only access
- `analyze`: Can run analyzers and responders
- `orgAdmin`: Full organization management

#### Get Analyzer Configuration

```http
GET /api/analyzer/{analyzer_id}/config
Authorization: Bearer <api_key>
```

#### Update Analyzer Configuration

```http
PATCH /api/analyzer/{analyzer_id}/config
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "configuration": {
    "api_key": "your-api-key",
    "proxy_http": "http://proxy:8080",
    "proxy_https": "https://proxy:8080"
  },
  "rateLimit": 10,
  "maxTlp": 2,
  "maxPap": 2
}
```

**TLP Levels:**

- 0: White (public)
- 1: Green (community)
- 2: Amber (restricted)
- 3: Red (confidential)

**PAP Levels:**

- 0: White (no restrictions)
- 1: Green (minimal restrictions)
- 2: Amber (moderate restrictions)
- 3: Red (severe restrictions)

#### Get Analyzer Report

```http
GET /api/analyzer/{analyzer_id}/report/{report_id}
Authorization: Bearer <api_key>
```

#### List Jobs by Analyzer

```http
GET /api/analyzer/{analyzer_id}/job
Authorization: Bearer <api_key>
```

#### Get Job Wait

```http
GET /api/job/{job_id}/wait
Authorization: Bearer <api_key>
```

Waits for job completion and returns the result.

#### Get Job Report

```http
GET /api/job/{job_id}/report
Authorization: Bearer <api_key>
```

#### Health Check

```http
GET /api/health
```

---

## Shuffle API

**Container:** `soar_shuffle_backend`  
**Port:** 5001  
**Base URL:** `http://localhost:5001/api/v1`  
**Documentation:** [Shuffle API Documentation](https://github.com/shuffle/shuffle-docs/blob/master/docs/API.md)

**Note:** Shuffle requires session-based authentication. First login via `/api/v1/users/login` to obtain a session
token, then use that token for subsequent requests.

### Authentication

```http
Authorization: Bearer <SHUFFLE_API_KEY>
```

### Key Endpoints

#### Login

```http
POST /api/v1/users/login
Content-Type: application/json

{
  "username": "admin",
  "password": "ChangeMe!"
}
```

#### List Workflows

```http
GET /api/v1/workflows
Authorization: Bearer <api_key>
```

**Response:**

```json
[
  {
    "id": "workflow-12345",
    "name": "Malware Analysis Workflow",
    "description": "Automated malware analysis pipeline",
    "status": "active"
  }
]
```

#### Get Workflow

```http
GET /api/v1/workflows/{workflow_id}
Authorization: Bearer <api_key>
```

#### Execute Workflow

```http
POST /api/v1/workflows/{workflow_id}/execute
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "execution_argument": "trigger-data",
  "source": "api"
}
```

#### List Apps

```http
GET /api/v1/apps
Authorization: Bearer <api_key>
```

#### Send Webhook

```http
POST /api/v1/hooks/{hook_id}
Content-Type: application/json

{
  "data": {
    "alert_id": "12345",
    "severity": "high"
  }
}
```

#### Get Execution Results

```http
POST /api/v1/streams/results
Content-Type: application/json

{
  "execution_id": "execution-id",
  "authorization": "authorization-key"
}
```

#### Abort Workflow

```http
POST /api/v1/workflows/{workflow_id}/abort
Authorization: Bearer <api_key>
```

#### Create New Workflow

```http
POST /api/v1/workflows
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "name": "New Workflow",
  "description": "Workflow description"
}
```

#### Save Workflow

```http
PUT /api/v1/workflows/{workflow_id}
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "actions": [],
  "branches": [],
  "triggers": [],
  "id": "workflow-id",
  "name": "Workflow Name",
  "description": "Description"
}
```

#### Delete Workflow

```http
DELETE /api/v1/workflows/{workflow_id}
Authorization: Bearer <api_key>
```

#### List Workflow Executions

```http
GET /api/v1/workflows/{workflow_id}/executions
Authorization: Bearer <api_key>
```

#### List Apps

```http
GET /api/v1/apps
Authorization: Bearer <api_key>
```

#### Upload App

```http
POST /api/v1/apps
Authorization: Bearer <api_key>
Content-Type: multipart/form-data
```

#### Delete App

```http
DELETE /api/v1/apps/{app_id}
Authorization: Bearer <api_key>
```

#### List Triggers

```http
GET /api/v1/triggers
Authorization: Bearer <api_key>
```

#### Create Schedule

```http
POST /api/v1/triggers/schedule
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "workflow_id": "workflow-id",
  "crontab": "0 0 * * *"
}
```

#### Delete Schedule

```http
DELETE /api/v1/triggers/schedule/{schedule_id}
Authorization: Bearer <api_key>
```

#### Create Webhook

```http
POST /api/v1/triggers/webhook
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "workflow_id": "workflow-id",
  "input": "{}"
}
```

#### Delete Webhook

```http
DELETE /api/v1/triggers/webhook/{webhook_id}
Authorization: Bearer <api_key>
```

#### List Organizations

```http
GET /api/v1/organizations
Authorization: Bearer <api_key>
```

#### Get Organization

```http
GET /api/v1/organizations/{org_id}
Authorization: Bearer <api_key>
```

#### Create Organization

```http
POST /api/v1/organizations
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "name": "New Organization",
  "description": "Organization description"
}
```

#### List Users

```http
GET /api/v1/users
Authorization: Bearer <api_key>
```

#### Create User

```http
POST /api/v1/users/register
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "username": "newuser",
  "password": "password",
  "email": "user@example.com"
}
```

#### Update User

```http
PATCH /api/v1/users/{user_id}
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "role": "admin"
}
```

#### List Environments

```http
GET /api/v1/environments
Authorization: Bearer <api_key>
```

#### Create Environment

```http
POST /api/v1/environments
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "name": "production",
  "description": "Production environment"
}
```

#### List Workflow Variables

```http
GET /api/v1/workflows/{workflow_id}/variables
Authorization: Bearer <api_key>
```

#### Set Workflow Variable

```http
POST /api/v1/workflows/{workflow_id}/variables
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "key": "variable_name",
  "value": "variable_value"
}
```

#### Get Execution Queue

```http
GET /api/v1/queue
Authorization: Bearer <api_key>
```

#### Clear Execution Queue

```http
DELETE /api/v1/queue
Authorization: Bearer <api_key>
```

#### Get Orborus Status

```http
GET /api/v1/orborus
Authorization: Bearer <api_key>
```

#### Health Check

```http
GET /api/v1/health
```

---

## Shuffle Orborus API

**Container:** `soar_orborus`  
**Base URL:** Internal service (no direct HTTP API)  
**Documentation:** [Shuffle Orborus](https://github.com/Shuffle/Shuffle)

### Overview

Orborus is the workflow execution scheduler for Shuffle. It polls the Shuffle backend for workflow executions and
manages worker nodes. It does not expose a direct HTTP API but communicates with the Shuffle backend API.

### Communication

Orborus communicates with:

- **Shuffle Backend API** (`http://shuffle-backend:5001/api/v1`) for job scheduling
- **Docker API** (via `/var/run/docker.sock`) for container management
- **Elasticsearch** for logging and metrics

### Key Functions

- Polls Shuffle backend for pending workflow executions
- Manages worker containers (shuffle-workers)
- Handles workflow execution lifecycle
- Executes cleanup of completed containers
- Manages app service deployments

### Environment Variables

- `BASE_URL`: Shuffle backend URL
- `SHUFFLE_PIPELINE_AUTH`: API key for authentication
- `SHUFFLE_SWARM_CONFIG`: Docker/swarm configuration
- `CLEANUP`: Whether to cleanup containers after execution
- `SHUFFLE_WORKER_IMAGE`: Worker container image to use

### Monitoring

Orborus health is monitored via the Shuffle backend health check:

```bash
# Check Orborus status via Shuffle backend
curl http://localhost:5001/api/v1/orborus
```

---

## MISP API

**Container:** `soar_misp`  
**Port:** 8083  
**Base URL:** `https://localhost:8083`  
**Documentation:** [MISP Automation & API](https://www.circl.lu/doc/misp/automation/)

**Note:** MISP requires HTTPS. Access via HTTP will fail. You may need to configure SSL certificates or access via the
reverse proxy at `https://localhost/misp/`.

### Authentication

MISP uses API key authentication.

```http
Authorization: <MISP_API_KEY>
```

### Key Endpoints

#### Search Events

```http
POST /events/restSearch
Authorization: <api_key>
Content-Type: application/json

{
  "returnFormat": "json",
  "limit": 10,
  "page": 1
}
```

**Response:**

```json
{
  "response": [
    {
      "Event": {
        "id": "1",
        "info": "Ransomware Campaign",
        "threat_level_id": "3",
        "analysis": "1",
        "date": "2026-05-23"
      }
    }
  ]
}
```

#### Create Event

```http
POST /events
Authorization: <api_key>
Content-Type: application/json

{
  "Event": {
    "info": "New Ransomware Variant",
    "threat_level_id": "3",
    "analysis": "1",
    "distribution": "1"
  }
}
```

#### Add Attribute

```http
POST /attributes/add/{event_id}
Authorization: <api_key>
Content-Type: application/json

{
  "type": "ip-dst",
  "value": "192.168.1.100",
  "category": "Network activity",
  "to_ids": true
}
```

#### Search Attributes

```http
POST /attributes/restSearch
Authorization: <api_key>
Content-Type: application/json

{
  "returnFormat": "json",
  "type": "ip-dst",
  "value": "192.168.1.100"
}
```

**Advanced Search Parameters:**

- `limit`: Limit number of results
- `page`: Page number for pagination
- `type`: Attribute type (ip-src, ip-dst, domain, url, etc.)
- `category`: Attribute category
- `tags`: Filter by tags (use `!` to exclude)
- `from`: Events after this date (format: 2015-02-15)
- `to`: Events before this date
- `publish_timestamp`: Filter by publish timestamp
- `withAttachments`: Include attachments as base64
- `metadata`: Return only metadata (no attributes)

#### Add Attribute

```http
POST /attributes/add/{event_id}
Authorization: <api_key>
Content-Type: application/json

{
  "type": "ip-dst",
  "value": "192.168.1.100",
  "category": "Network activity",
  "to_ids": true,
  "comment": "Suspicious IP"
}
```

#### Delete Attribute

```http
POST /attributes/delete/{attribute_id}
Authorization: <api_key>
```

#### Add Tag to Attribute

```http
POST /attributes/addTag
Authorization: <api_key>
Content-Type: application/json

{
  "attribute_id": "attribute-id",
  "tag": "tlp:amber"
}
```

#### Get Event

```http
GET /events/{event_id}
Authorization: <api_key>
```

#### Update Event

```http
POST /events/{event_id}
Authorization: <api_key>
Content-Type: application/json

{
  "Event": {
    "info": "Updated event info",
    "distribution": "1"
  }
}
```

#### Delete Event

```http
DELETE /events/{event_id}
Authorization: <api_key>
```

#### Add Tag to Event

```http
POST /events/addTag
Authorization: <api_key>
Content-Type: application/json

{
  "event_id": "event-id",
  "tag": "ransomware"
}
```

#### Remove Tag from Event

```http
POST /events/removeTag
Authorization: <api_key>
Content-Type: application/json

{
  "event_id": "event-id",
  "tag": "ransomware"
}
```

#### Get Attribute Types

```http
GET /attributes/describeTypes
Authorization: <api_key>
```

#### Get Tags Statistics

```http
GET /tags/tagStatistics
Authorization: <api_key>
```

#### Get Warninglists

```http
GET /warninglists/index
Authorization: <api_key>
```

#### Get Sighting

```http
GET /sightings
Authorization: <api_key>
```

#### Add Sighting

```http
POST /sightings/add
Authorization: <api_key>
Content-Type: application/json

{
  "value": "192.168.1.100",
  "type": "ip-dst",
  "source": "internal"
}
```

#### Get Server Info

```http
GET /servers/getVersion
Authorization: <api_key>
```

#### Get Server Settings

```http
GET /servers/settings
Authorization: <api_key>
```

#### List Organizations

```http
GET /organisations/index
Authorization: <api_key>
```

#### Get Organization

```http
GET /organisations/view/{org_id}
Authorization: <api_key>
```

#### Create Organization

```http
POST /organisations/add
Authorization: <api_key>
Content-Type: application/json

{
  "name": "New Organization",
  "uuid": "uuid-here",
  "local": true
}
```

#### List Users

```http
GET /admin/users/index
Authorization: <api_key>
```

#### Get User

```http
GET /admin/users/view/{user_id}
Authorization: <api_key>
```

#### Create User

```http
POST /admin/users/add
Authorization: <api_key>
Content-Type: application/json

{
  "email": "user@example.com",
  "org_id": 1,
  "role_id": 3,
  "password": "password"
}
```

#### List Roles

```http
GET /roles/index
Authorization: <api_key>
```

#### List Sharing Groups

```http
GET /sharing_groups/index
Authorization: <api_key>
```

#### Create Sharing Group

```http
POST /sharing_groups/add
Authorization: <api_key>
Content-Type: application/json

{
  "name": "Sharing Group Name",
  "organisation_uuid": "org-uuid",
  "active": true
}
```

#### List Feeds

```http
GET /feeds/index
Authorization: <api_key>
```

#### Enable Feed

```http
POST /feeds/add/{feed_id}
Authorization: <api_key>
```

#### Fetch Feed

```http
POST /feeds/fetchFromFeed/{feed_id}
Authorization: <api_key>
```

#### List Feed Caches

```http
GET /feeds/cacheFeeds
Authorization: <api_key>
```

#### Get Feed Metadata

```http
GET /feeds/previewIndex/{feed_id}
Authorization: <api_key>
```

#### Export Feed

```http
GET /feeds/exportFeeds
Authorization: <api_key>
```

#### List Galaxies

```http
GET /galaxies/index
Authorization: <api_key>
```

#### Get Galaxy Clusters

```http
GET /galaxies/view/{galaxy_id}
Authorization: <api_key>
```

#### Update Galaxies

```http
POST /galaxies/update
Authorization: <api_key>
```

#### Attach Galaxy to Event

```http
POST /events/addTag
Authorization: <api_key>
Content-Type: application/json

{
  "event_id": "event-id",
  "tag": "misp-galaxy:threat-actor=\"APT28\""
}
```

#### List Object Templates

```http
GET /objectTemplates/index
Authorization: <api_key>
```

#### Get Object Template

```http
GET /objectTemplates/view/{template_id}
Authorization: <api_key>
```

#### Add Object to Event

```http
POST /objects/add/{event_id}
Authorization: <api_key>
Content-Type: application/json

{
  "Object": {
    "template_id": "template-id",
    "Attribute": [
      {
        "type": "ip-src",
        "value": "192.168.1.1"
      }
    ]
  }
}
```

#### Get Event Graph

```http
GET /events/viewGraph/{event_id}
Authorization: <api_key>
```

#### Get Event Correlations

```http
GET /events/viewCorrelation/{event_id}
Authorization: <api_key>
```

#### Get Event Proposals

```http
GET /shadow_attributes/index/{event_id}
Authorization: <api_key>
```

#### Accept Proposal

```http
POST /shadow_attributes/accept/{proposal_id}
Authorization: <api_key>
```

#### Discard Proposal

```http
POST /shadow_attributes/discard/{proposal_id}
Authorization: <api_key>
```

#### Export Event to STIX

```http
GET /events/stix/download/{event_id}
Authorization: <api_key>
```

#### Export Event to XML

```http
GET /events/xml/download/{event_id}
Authorization: <api_key>
```

#### Export Event to JSON

```http
GET /events/json/download/{event_id}
Authorization: <api_key>
```

#### Export Attributes to CSV

```http
POST /attributes/csv/download
Authorization: <api_key>
Content-Type: application/json

{
  "event_id": "event-id",
  "type": "ip-src"
}
```

#### Get Taxonomies

```http
GET /taxonomies/index
Authorization: <api_key>
```

#### Update Taxonomies

```http
POST /taxonomies/update
Authorization: <api_key>
```

#### Enable Taxonomy

```http
POST /taxonomies/enable/{taxonomy_id}
Authorization: <api_key>
```

#### Health Check

```http
GET /users/heartbeat
```

---

## MISP Modules API

**Container:** `soar_misp_modules`  
**Port:** 6666 (internal)  
**Base URL:** `http://localhost:6666`  
**Documentation:** [MISP Modules Documentation](https://misp.github.io/misp-modules/)

### Authentication

MISP Modules typically run without authentication by default. Configure authentication in the module settings if needed.

### Key Endpoints

#### List All Modules

```http
GET /modules
```

**Response:**

```json
{
  "modules": [
    {
      "name": "censys",
      "type": "expansion",
      "description": "Censys expansion module",
      "meta": {
        "input": "ip, hostname",
        "output": "text"
      }
    }
  ]
}
```

#### List Expansion Modules

```http
GET /modules/expansion
```

#### List Export Modules

```http
GET /modules/export
```

#### List Import Modules

```http
GET /modules/import
```

#### List Action Modules

```http
GET /modules/action
```

#### Get Module Info

```http
GET /modules/{module_name}
```

#### Run Expansion Module

```http
POST /modules/{module_name}
Content-Type: application/json

{
  "ip": "8.8.8.8",
  "hostname": "example.com"
}
```

**Response:**

```json
{
  "results": [
    {
      "types": ["text"],
      "values": ["Enriched data here"]
    }
  ]
}
```

#### Run Export Module

```http
POST /modules/{module_name}
Content-Type: application/json

{
  "event_id": "123",
  "format": "stix"
}
```

#### Run Import Module

```http
POST /modules/{module_name}
Content-Type: application/json

{
  "data": "import data here",
  "format": "json"
}
```

#### Run Action Module

```http
POST /modules/{module_name}
Content-Type: application/json

{
  "action": "execute",
  "parameters": {}
}
```

#### Get Module Health

```http
GET /modules/{module_name}/health
```

#### Get Module Statistics

```http
GET /modules/{module_name}/stats
```

---

## Wazuh API

**Container:** `soar_wazuh_manager`  
**Port:** 55100 (host) / 55000 (container)  
**Base URL:** `https://localhost:55100`  
**Documentation:** [Wazuh Server API](https://documentation.wazuh.com/current/user-manual/api/index.html)

**Note:** Wazuh API requires HTTPS. Access via HTTP will fail. Use `-k` flag with curl to ignore SSL certificate
warnings for testing.

### Authentication

Wazuh uses JWT token authentication. Login to obtain a token.

```http
POST /security/user/authenticate?raw=true
Content-Type: application/json

{
  "username": "wazuh-wui",
  "password": "<WAZUH_API_PASSWORD>"
}
```

**Response:**

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Key Endpoints

#### Get Agents

```http
GET /agents
Authorization: Bearer <token>
```

**Response:**

```json
{
  "data": {
    "items": [
      {
        "id": "000",
        "name": "wazuh-manager",
        "ip": "127.0.0.1",
        "status": "active"
      }
    ]
  }
}
```

#### Get Agent Info

```http
GET /agents/{agent_id}
Authorization: Bearer <token>
```

#### Add Agent

```http
POST /agents
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "new-agent",
  "ip": "192.168.1.100"
}
```

#### Get Agent Events

```http
GET /agents/{agent_id}/events
Authorization: Bearer <token>
```

#### Get FIM Events

```http
GET /fim/{agent_id}/events
Authorization: Bearer <token>
```

#### Restart Agent

```http
PUT /agents/{agent_id}/restart
Authorization: Bearer <token>
```

#### Get Manager Info

```http
GET /manager/info
Authorization: Bearer <token>
```

#### Get Cluster Status

```http
GET /cluster/status
Authorization: Bearer <token>
```

#### Get Cluster Nodes

```http
GET /cluster/nodes
Authorization: Bearer <token>
```

#### Get Active Response

```http
GET /active-response
Authorization: Bearer <token>
```

#### Run Active Response

```http
PUT /active-response
Authorization: Bearer <token>
Content-Type: application/json

{
  "command": "restart-wazuh",
  "arguments": ["agent-id"]
}
```

#### Get Decoders

```http
GET /decoders
Authorization: Bearer <token>
```

#### Get Rules

```http
GET /rules
Authorization: Bearer <token>
```

#### Get Syscheck Files

```http
GET /syscheck/{agent_id}
Authorization: Bearer <token>
```

#### Get Syscheck Changes

```http
GET /syscheck/{agent_id}/last_scan
Authorization: Bearer <token>
```

#### Get Rootcheck

```http
GET /rootcheck/{agent_id}
Authorization: Bearer <token>
```

#### Get Vulnerabilities

```http
GET /vulnerability/{agent_id}
Authorization: Bearer <token>
```

#### Get CIS Benchmarks

```http
GET /ciscat/{agent_id}
Authorization: Bearer <token>
```

#### Get MITRE Att&CK Data

```http
GET /mitre
Authorization: Bearer <token>
```

#### Get Security Configuration Assessment

```http
GET /sca/{agent_id}
Authorization: Bearer <token>
```

#### Get API Configuration

```http
GET /security/config
Authorization: Bearer <token>
```

#### Update API Configuration

```http
PUT /security/config
Authorization: Bearer <token>
Content-Type: application/json

{
  "auth_token_exp_timeout": 3600,
  "rbac_mode": "white"
}
```

#### List Users

```http
GET /security/users
Authorization: Bearer <token>
```

#### Get User

```http
GET /security/users/{username}
Authorization: Bearer <token>
```

#### Create User

```http
POST /security/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "newuser",
  "password": "password"
}
```

#### Update User

```http
PUT /security/users/{username}
Authorization: Bearer <token>
Content-Type: application/json

{
  "password": "newpassword"
}
```

#### Delete User

```http
DELETE /security/users/{username}
Authorization: Bearer <token>
```

#### List Roles

```http
GET /security/roles
Authorization: Bearer <token>
```

#### Get Role

```http
GET /security/roles/{role_id}
Authorization: Bearer <token>
```

#### Create Role

```http
POST /security/roles
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "analyst",
  "policies": [
    {
      "policy": {
        "name": "policy-name",
        "actions": ["agent:read", "agent:delete"]
      }
    }
  ]
}
```

#### List Policies

```http
GET /security/policies
Authorization: Bearer <token>
```

#### Get Policy

```http
GET /security/policies/{policy_id}
Authorization: Bearer <token>
```

#### List Rules

```http
GET /rules
Authorization: Bearer <token>
```

#### Get Rule

```http
GET /rules/{rule_id}
Authorization: Bearer <token>
```

#### List Decoders

```http
GET /decoders
Authorization: Bearer <token>
```

#### Get Decoder

```http
GET /decoders/{decoder_id}
Authorization: Bearer <token>
```

#### List Lists (CDB Lists)

```http
GET /lists
Authorization: Bearer <token>
```

#### Get List

```http
GET /lists/{list_name}
Authorization: Bearer <token>
```

#### Create List

```http
POST /lists
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "ip-blacklist",
  "path": "/etc/lists/blacklist",
  "type": "ip"
}
```

#### Update List

```http
PUT /lists/{list_name}
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "192.168.1.1\n10.0.0.1"
}
```

#### Get Upgrade Agents

```http
GET /agents/upgrade/agents
Authorization: Bearer <token>
```

#### Upgrade Agent

```http
PUT /agents/{agent_id}/upgrade
Authorization: Bearer <token>
Content-Type: application/json

{
  "version": "4.14.0",
  "upgrade_type": "upgrade"
}
```

#### Get Upgrade Status

```http
GET /agents/{agent_id}/upgrade/result
Authorization: Bearer <token>
```

#### Get Agent Groups

```http
GET /groups
Authorization: Bearer <token>
```

#### Get Group

```http
GET /groups/{group_id}
Authorization: Bearer <token>
```

#### Create Group

```http
POST /groups
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "web-servers"
}
```

#### Add Agent to Group

```http
PUT /groups/{group_id}/agents/{agent_id}
Authorization: Bearer <token>
```

#### Remove Agent from Group

```http
DELETE /groups/{group_id}/agents/{agent_id}
Authorization: Bearer <token>
```

#### Delete Group

```http
DELETE /groups/{group_id}
Authorization: Bearer <token>
```

#### Get Configuration

```http
GET /agents/{agent_id}/config/sca
Authorization: Bearer <token>
```

#### Update Agent Configuration

```http
PUT /agents/{agent_id}/config/sca
Authorization: Bearer <token>
Content-Type: application/json

{
  "enabled": true,
  "scan_on_start": true,
  "interval": "1d"
}
```

---

## Elasticsearch API

**Container:** `soar_elasticsearch`  
**Port:** 9201  
**Base URL:** `http://localhost:9201`  
**Documentation:** [Elasticsearch REST API](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/rest-apis.html)

### Authentication

No authentication configured (xpack.security.enabled=false).

### Key Endpoints

#### Cluster Health

```http
GET /_cluster/health
```

**Response:**

```json
{
  "cluster_name": "docker-cluster",
  "status": "yellow",
  "number_of_nodes": 1,
  "active_shards": 10
}
```

#### Search

```http
POST /{index}/_search
Content-Type: application/json

{
  "query": {
    "match": {
      "message": "ransomware"
    }
  }
}
```

#### Create Index

```http
PUT /{index}
Content-Type: application/json

{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  }
}
```

#### Get Index

```http
GET /{index}
```

#### List Indices

```http
GET /_cat/indices?v
```

#### Bulk Index

```http
POST /_bulk
Content-Type: application/x-ndjson

{ "index" : { "_index" : "test" } }
{ "field1" : "value1" }
```

#### Index Document

```http
POST /{index}/_doc/{doc_id}
Content-Type: application/json

{
  "field1": "value1",
  "field2": "value2"
}
```

#### Get Document

```http
GET /{index}/_doc/{doc_id}
```

#### Update Document

```http
POST /{index}/_update/{doc_id}
Content-Type: application/json

{
  "doc": {
    "field1": "new_value"
  }
}
```

#### Delete Document

```http
DELETE /{index}/_doc/{doc_id}
```

#### Delete Index

```http
DELETE /{index}
```

#### Aggregations

```http
POST /{index}/_search
Content-Type: application/json

{
  "size": 0,
  "aggs": {
    "by_category": {
      "terms": {
        "field": "category.keyword"
      }
    }
  }
}
```

#### Multi-Search

```http
POST /_msearch
Content-Type: application/x-ndjson

{"index": "index1"}
{"query": {"match_all": {}}}
{"index": "index2"}
{"query": {"match": {"field": "value"}}}
```

#### Cluster State

```http
GET /_cluster/state
```

#### Cluster Stats

```http
GET /_cluster/stats
```

#### Node Stats

```http
GET /_nodes/stats
```

#### Index Stats

```http
GET /{index}/_stats
```

#### Indices Settings

```http
GET /{index}/_settings
```

#### Update Index Settings

```http
PUT /{index}/_settings
Content-Type: application/json

{
  "index": {
    "number_of_replicas": 1
  }
}
```

#### Index Mappings

```http
GET /{index}/_mapping
```

#### Create Index Mapping

```http
PUT /{index}
Content-Type: application/json

{
  "mappings": {
    "properties": {
      "field1": {
        "type": "text"
      },
      "field2": {
        "type": "keyword"
      }
    }
  }
}
```

#### Refresh Index

```http
POST /{index}/_refresh
```

#### Flush Index

```http
POST /{index}/_flush
```

#### Reindex

```http
POST /_reindex
Content-Type: application/json

{
  "source": {
    "index": "old_index"
  },
  "dest": {
    "index": "new_index"
  }
}
```

---

## Kibana API

**Container:** `soar_kibana`  
**Port:** 15601  
**Base URL:** `http://localhost:15601`  
**Documentation:** [Kibana Saved Objects API](https://www.elastic.co/guide/en/kibana/7.17/saved-objects-api.html)

### Authentication

Kibana uses Elasticsearch authentication. No authentication configured in this lab (xpack.security.enabled=false).

### Key Endpoints

#### Get Saved Object

```http
GET /api/saved_objects/{type}/{id}
```

**Valid types:** `dashboard`, `visualization`, `index-pattern`, `search`, `map`, `ml-job`, etc.

#### Create Saved Object

```http
POST /api/saved_objects/{type}
Content-Type: application/json

{
  "attributes": {
    "title": "My Dashboard",
    "description": "Dashboard description"
  }
}
```

#### Update Saved Object

```http
PUT /api/saved_objects/{type}/{id}
Content-Type: application/json

{
  "attributes": {
    "title": "Updated Title"
  }
}
```

#### Delete Saved Object

```http
DELETE /api/saved_objects/{type}/{id}
```

#### List Saved Objects

```http
GET /api/saved_objects/_find?type={type}&search={search_term}
```

#### Export Saved Objects

```http
POST /api/saved_objects/_export
Content-Type: application/json

{
  "type": ["dashboard", "visualization"],
  "includeReferences": true
}
```

#### Import Saved Objects

```http
POST /api/saved_objects/_import
Content-Type: multipart/form-data
```

#### Create Index Pattern

```http
POST /api/saved_objects/index-pattern
Content-Type: application/json

{
  "attributes": {
    "title": "logs-*",
    "timeFieldName": "@timestamp"
  }
}
```

#### Get Index Patterns

```http
GET /api/saved_objects/_find?type=index-pattern
```

#### Create Visualization

```http
POST /api/saved_objects/visualization
Content-Type: application/json

{
  "attributes": {
    "title": "My Visualization",
    "visState": "{\"type\":\"histogram\"}",
    "uiState": "{}",
    "description": "Visualization description"
  }
}
```

#### Create Dashboard

```http
POST /api/saved_objects/dashboard
Content-Type: application/json

{
  "attributes": {
    "title": "My Dashboard",
    "panelsJSON": "[{\"panelIndex\":1}]",
    "optionsJSON": "{}",
    "description": "Dashboard description"
  }
}
```

#### Get Kibana Status

```http
GET /api/status
```

#### Get Kibana Info

```http
GET /api/kibana/info
```

---

## Redis API

**Container:** `soar_redis`  
**Port:** 6379  
**Base URL:** `redis://localhost:6379`  
**Password:** `M5x#3mP8$vR7@nQ1tW9!zY4&hF2sD6`

### Authentication

Redis uses password authentication.

```bash
redis-cli -a M5x#3mP8$vR7@nQ1tW9!zY4&hF2sD6
```

### Key Commands

#### Set Value

```bash
SET key value
```

#### Get Value

```bash
GET key
```

#### Delete Key

```bash
DEL key
```

#### List Keys

```bash
KEYS *
```

#### Set with Expiration

```bash
SETEX key 3600 value
```

#### Check Health

```bash
PING
```

**Response:**

```
PONG
```

#### Set Multiple Values

```bash
MSET key1 value1 key2 value2
```

#### Get Multiple Values

```bash
MGET key1 key2
```

#### Increment

```bash
INCR counter
```

#### Increment by Value

```bash
INCRBY counter 10
```

#### Decrement

```bash
DECR counter
```

#### Hash Set

```bash
HSET user:1 name "John" age 30
```

#### Hash Get

```bash
HGET user:1 name
```

#### Hash Get All

```bash
HGETALL user:1
```

#### Hash Delete

```bash
HDEL user:1 name
```

#### List Push (Left)

```bash
LPUSH mylist value1
```

#### List Push (Right)

```bash
RPUSH mylist value2
```

#### List Pop (Left)

```bash
LPOP mylist
```

#### List Range

```bash
LRANGE mylist 0 -1
```

#### Set Add

```bash
SADD myset value1
```

#### Set Members

```bash
SMEMBERS myset
```

#### Set Remove

```bash
SREM myset value1
```

#### Sorted Set Add

```bash
ZADD myzset 1 member1
```

#### Sorted Set Range

```bash
ZRANGE myzset 0 -1 WITHSCORES
```

#### Sorted Set Remove

```bash
ZREM myzset member1
```

#### Publish Message

```bash
PUBLISH channel "message"
```

#### Subscribe to Channel

```bash
SUBSCRIBE channel
```

#### Database Size

```bash
DBSIZE
```

#### Flush Database

```bash
FLUSHDB
```

#### Flush All Databases

```bash
FLUSHALL
```

#### Server Info

```bash
INFO
```

#### Slow Log

```bash
SLOWLOG GET 10
```

#### Monitor Commands

```bash
MONITOR
```

#### Save to Disk

```bash
SAVE
```

#### Background Save

```bash
BGSAVE
```

#### Last Save Time

```bash
LASTSAVE
```

---

## Docker API

**Access:** Via Docker socket mounted at `/var/run/docker.sock`  
**Base URL:** `unix:///var/run/docker.sock` or `http://localhost:2375`  
**Documentation:** [Docker Engine API](https://docs.docker.com/engine/api/)

### Authentication

Docker API uses TLS certificates or Unix socket authentication. In this lab, the Docker socket is mounted directly.

### Key Endpoints

#### List Containers

```http
GET /containers/json
```

**Response:**

```json
[
  {
    "Id": "container-id",
    "Names": ["/soar_api"],
    "Image": "soar-api:latest",
    "State": "running",
    "Status": "Up 2 hours"
  }
]
```

#### Get Container Info

```http
GET /containers/{container_id}/json
```

#### Start Container

```http
POST /containers/{container_id}/start
```

#### Stop Container

```http
POST /containers/{container_id}/stop
```

#### Restart Container

```http
POST /containers/{container_id}/restart
```

#### Pause Container

```http
POST /containers/{container_id}/pause
```

#### Unpause Container

```http
POST /containers/{container_id}/unpause
```

#### Remove Container

```http
DELETE /containers/{container_id}
```

#### Get Container Logs

```http
GET /containers/{container_id}/logs
```

#### Get Container Stats

```http
GET /containers/{container_id}/stats
```

**Response:**

```json
{
  "cpu_stats": {
    "cpu_usage": {
      "total_usage": 12345678
    }
  },
  "memory_stats": {
    "usage": 12345678,
    "limit": 2147483648
  }
}
```

#### Get Container Processes

```http
GET /containers/{container_id}/top
```

#### Exec Create

```http
POST /containers/{container_id}/exec
Content-Type: application/json

{
  "AttachStdin": false,
  "AttachStdout": true,
  "AttachStderr": true,
  "Cmd": ["ls", "-la"]
}
```

#### Exec Start

```http
POST /exec/{exec_id}/start
```

#### List Images

```http
GET /images/json
```

#### Get Image Info

```http
GET /images/{image_id}/json
```

#### Pull Image

```http
POST /images/create?fromImage=ubuntu&tag=latest
```

#### Remove Image

```http
DELETE /images/{image_id}
```

#### List Networks

```http
GET /networks
```

#### Create Network

```http
POST /networks/create
Content-Type: application/json

{
  "Name": "my-network",
  "Driver": "bridge"
}
```

#### Remove Network

```http
DELETE /networks/{network_id}
```

#### List Volumes

```http
GET /volumes
```

#### Create Volume

```http
POST /volumes/create
Content-Type: application/json

{
  "Name": "my-volume",
  "Driver": "local"
}
```

#### Remove Volume

```http
DELETE /volumes/{volume_name}
```

#### Get System Info

```http
GET /info
```

**Response:**

```json
{
  "Containers": 10,
  "Images": 5,
  "ServerVersion": "20.10.0",
  "NCPU": 4,
  "MemTotal": 17179869184
}
```

#### Get Docker Version

```http
GET /version
```

#### Get Events

```http
GET /events
```

#### Get Health Check Status

```http
GET /containers/{container_id}/healthcheck
```

---

## Network Watcher

**Container:** `soar_network_watcher`  
**Base URL:** Internal service (no direct HTTP API)  
**Purpose:** Monitors network traffic in the SOAR lab environment

### Overview

Network Watcher is a custom service that monitors the Docker network `soar_soar_net` for network activity and events. It
provides visibility into network communications between containers.

### Communication

Network Watcher communicates with:

- **Docker API** (via `/var/run/docker.sock`) for network monitoring
- **Docker Network** `soar_soar_net` for traffic inspection

### Environment Variables

- `TARGET_NETWORK`: The Docker network to monitor (default: `soar_soar_net`)

### Key Functions

- Monitors network traffic between containers
- Detects new connections and communication patterns
- Logs network events for analysis
- Provides network visibility for security monitoring

### Monitoring

Network Watcher runs as a background service. Check its status via Docker:

```bash
docker logs soar_network_watcher
docker ps | filter soar_network_watcher
```

---

## Web Management UI

**Container:** `soar_web_management`
**Port:** 8085
**Base URL:** `http://localhost:8085`

### Endpoints

The web management UI provides a frontend interface to the SOAR Lab Management API.

#### Dashboard

```http
GET /
```

#### Login

```http
POST /api/login
Content-Type: application/json

{
  "username": "admin",
  "password": "X9e#5mP3$vL7@nQ4tW8!zY2&hF6sD1"
}
```

#### Metrics

```http
GET /api/metrics
```

#### Services Status

```http
GET /api/services/status
```

#### Test Execution

```http
POST /api/tests/run
Content-Type: application/json

{
  "category": "unit"
}
```

---

## Nginx Reverse Proxy

**Container:** `soar_nginx`
**Ports:** 80, 443
**Base URL:** `http://localhost`

### Port Mappings

- **Port 80:** HTTP reverse proxy to all services (redirects to HTTPS)
- **Port 443:** HTTPS reverse proxy (SSL configured)

Note: Services are now accessed directly on their respective ports:
- Docs site: http://localhost:8086
- Shuffle frontend: http://localhost:8081
- Web Management UI: http://localhost:8085

### Service Routes

Nginx routes requests to backend services based on path:

- `/thehive` → TheHive (9000)
- `/cortex` → Cortex (9001)
- `/shuffle` → Shuffle (5001)
- `/misp` → MISP (8082)
- `/wazuh` → Wazuh Dashboard (15601)
- `/kibana` → Kibana (15601)
- `/api` → SOAR Lab Management API (8000)
- `/` → Web Management UI (8085)

### Health Check

```http
GET /nginx-health
```

---

## Non-API Services

These services are part of the SOAR Ransomware Lab but do not expose HTTP APIs for external consumption.

### Elasticsearch

**Container:** `soar_elasticsearch`  
**Port:** 9201  
**Purpose:** Data storage and search engine

Used by:

- TheHive (case data)
- Cortex (job results)
- Shuffle (workflow executions)
- Wazuh (SIEM logs)
- Kibana (visualization)

**Access:** Via Elasticsearch API (documented above)

### Redis

**Container:** `soar_redis`  
**Port:** 6379  
**Purpose:** In-memory data store and cache

Used by:

- TheHive (session management)
- MISP (caching)
- SOAR Lab API (caching, queues)

**Access:** Via Redis commands (documented above)

### MISP Database

**Container:** `soar_misp_db`  
**Image:** mariadb:10.11  
**Purpose:** Database backend for MISP

**Access:** Direct database access via MySQL protocol on port 3306 (internal only)

### Shuffle Frontend

**Container:** `soar_shuffle_frontend`
**Port:** 80 (internal)
**Purpose:** Web UI for Shuffle workflow editor

**Access:** Via Nginx reverse proxy at `https://localhost:8081`

### Docs Site

**Container:** `soar_docs_site`
**Port:** 8080 (internal)
**Purpose:** Documentation site (Docusaurus)

**Access:** Via Nginx reverse proxy at `https://localhost`

---

## Environment Variables

### API Service

- `API_PORT`: 8000
- `API_AUTH_SECRET`: JWT secret key
- `WEB_UI_USER`: admin
- `WEB_UI_PASSWORD`: X9e#5mP3$vL7@nQ4tW8!zY2&hF6sD1
- `REDIS_PASSWORD`: M5x#3mP8$vR7@nQ1tW9!zY4&hF2sD6
- `THEHIVE_API_KEY`: TheHive API key
- `CORTEX_API_KEY`: Cortex API key
- `SHUFFLE_DEFAULT_APIKEY`: Shuffle API key
- `MISP_API_KEY`: MISP API key

### TheHive

- `THEHIVE_SECRET`: TheHive secret key
- `THEHIVE_HTTP_PORT`: 9000

### Cortex

- `CORTEX_SECRET`: Cortex secret key
- `CORTEX_HTTP_PORT`: 9001

### Shuffle

- `SHUFFLE_API_PORT`: 5001
- `SHUFFLE_DEFAULT_USERNAME`: admin
- `SHUFFLE_DEFAULT_PASSWORD`: ChangeMe!

### MISP

- `MISP_PORT`: 8082
- `MISP_ADMIN_PASSWORD`: MispAdminPassword123!@#
- `MISP_API_KEY`: MISP API key

### Wazuh

- `WAZUH_API_USERNAME`: wazuh-wui
- `WAZUH_API_PASSWORD`: Wazuh API password
- `WAZUH_DASHBOARD_PORT`: 15601

### Elasticsearch

- `ELASTICSEARCH_PORT`: 9201
- `ELASTIC_PASSWORD`: Elastic password

---

## Network Architecture

### Networks

- **bridge**: External Docker bridge network
- **soar_edge**: Edge network for external connectivity
- **soar_net**: Internal SOAR services network (172.20.0.0/16)
- **ti_net**: Threat intelligence network (172.21.0.0/16) - internal only
- **logging_net**: Centralized logging network

### Service Placement

- **ti_net (isolated):** Redis, Elasticsearch, MISP
- **soar_net (internal):** TheHive, Cortex, Shuffle, Wazuh, API, Nginx
- **bridge (external):** All services with external port mappings

---

## Testing APIs

### Using curl

```bash
# SOAR Lab API - Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"X9e#5mP3$vL7@nQ4tW8!zY2&hF6sD1"}'

# SOAR Lab API - Get Metrics
curl -X GET http://localhost:8000/analytics/metrics \
  -H "Authorization: Bearer <token>"

# TheHive - List Alerts
curl -X GET http://localhost:9000/api/alert \
  -H "Authorization: Bearer <THEHIVE_API_KEY>"

# Cortex - List Analyzers
curl -X GET http://localhost:9001/api/analyzer \
  -H "Authorization: Bearer <CORTEX_API_KEY>"

# MISP - Search Events
curl -X POST http://localhost:8083/events/restSearch \
  -H "Authorization: <MISP_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"returnFormat":"json","limit":10}'
```

### Using Python requests

```python
import requests

# SOAR Lab API
response = requests.post(
    'http://localhost:8000/auth/login',
    json={'username': 'admin', 'password': 'X9e#5mP3$vL7@nQ4tW8!zY2&hF6sD1'}
)
token = response.json()['token']

headers = {'Authorization': f'Bearer {token}'}
response = requests.get('http://localhost:8000/analytics/metrics', headers=headers)
print(response.json())
```

---

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure the container is running and healthy
   ```bash
   docker ps
   docker logs <container_name>
   ```

2. **Authentication Failed**: Verify API keys and credentials in `.env.full`

3. **Service Unavailable**: Check health status
   ```bash
   docker-compose ps
   ```

4. **Network Issues**: Verify containers are on correct networks
   ```bash
   docker network inspect soar_soar_net
   ```

### Health Checks

```bash
# Check all services health
docker-compose ps

# Check specific service health
docker inspect soar_api --format='{{.State.Health.Status}}'
```

---

## Additional Resources

- [TheHive Documentation](https://docs.strangebee.com/thehive/)
- [Cortex Documentation](https://docs.strangebee.com/cortex/)
- [Shuffle Documentation](https://shuffler.io/docs)
- [MISP Documentation](https://www.misp-project.org/documentation/)
- [Wazuh Documentation](https://documentation.wazuh.com/)
- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/7.17/index.html)
- [Redis Documentation](https://redis.io/documentation)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Last Updated:** 2026-05-23  
**Version:** 1.0.0
