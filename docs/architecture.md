# SOAR Ransomware Lab - Architecture Documentation

## Overview

SOAR Ransomware Lab is a comprehensive security orchestration platform designed specifically for ransomware incident response. This document describes the system architecture, components, and design principles.

## System Architecture

### High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Access Layer (Nginx)                            │
│  :80 Web UI  │  :8080 Reverse Proxy  │  :443 HTTPS                     │
├────────────────────────────────────────────────────────────────────────┤
│                         SOAR Orchestration Layer                         │
│  Shuffle UI :3001  │  Shuffle API :5001  │  Orborus (worker executor)  │
├────────────────────────────────────────────────────────────────────────┤
│                         Incident Response Layer                          │
│  TheHive :9000 (cases)  │  Cortex :9001 (analyzers)                    │
├────────────────────────────────────────────────────────────────────────┤
│                         SIEM / Detection Layer                           │
│  Wazuh Manager :1514-1516 (events)  │  Kibana :15601 (dashboards)      │
├────────────────────────────────────────────────────────────────────────┤
│                         Threat Intelligence Layer                        │
│  MISP :8082 (TI platform)                                               │
├────────────────────────────────────────────────────────────────────────┤
│                         Management & API Layer                           │
│  Lab API :8000 (FastAPI)  │  Docs Site :3000                           │
├────────────────────────────────────────────────────────────────────────┤
│                         Data & Infrastructure Layer                      │
│  Elasticsearch (internal)  │  Redis (internal)  │  MariaDB (MISP)      │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Overview

#### Core SOAR Services

1. **Shuffle** (`:3001` UI / `:5001` API)
   - Main SOAR orchestrator
   - Drag-and-drop workflow builder
   - Receives alerts from Wazuh via webhook
   - Executes automated response playbooks
   - Orborus executes app containers as workers

2. **TheHive** (`:9000`)
   - Incident case management platform
   - Evidence and observable tracking
   - Task assignment and timeline
   - Integrates with Cortex for enrichment

3. **Cortex** (`:9001`)
   - IoC analysis engine
   - Runs analyzers and responders
   - Integrates with MISP, VirusTotal, etc.
   - Custom Python analyzer support

#### SIEM / Detection

4. **Wazuh Manager** (`:1514-1516` events, `:55100` API internal)
   - SIEM/XDR agent-based detection
   - File integrity monitoring
   - Log collection and correlation
   - Sends alerts to Shuffle via webhook

5. **Kibana** (`:15601`)
   - Visualization frontend for Elasticsearch
   - Dashboards for Wazuh event data
   - Log exploration via Discover
   - Image: `docker.elastic.co/kibana/kibana:7.17.17`

#### Threat Intelligence

6. **MISP** (`:8082`)
   - Open-source threat intelligence platform
   - IOC sharing and management
   - Feeds integration
   - Connected to Cortex analyzers

#### Data Layer

7. **Elasticsearch** (internal Docker network)
   - `docker.elastic.co/elasticsearch/elasticsearch:7.17.17`
   - Shared backend for Shuffle, TheHive, and Kibana
   - Log aggregation and full-text search
   - Single-node setup with xpack.security enabled

8. **Redis** (internal)
   - Session and cache store for Shuffle
   - Message queuing

9. **MariaDB** (internal)
   - Database backend for MISP

#### Access & Management

10. **Nginx** (`:80`, `:443`, `:8080`)
    - Reverse proxy for all services
    - Serves web management static UI on `:80`
    - Proxies all services via path prefix on `:8080`

11. **Lab API** (`:8000`)
    - FastAPI application (`apps/api/entrypoint.py`)
    - Lab management and automation endpoints
    - Health check at `/health`

12. **Docs Site** (`:3000`)
    - Docusaurus static site
    - Served at `/docs/`

## Data Flow Architecture

### Alert Processing Pipeline

```
Alert Sources → Ingestion API → Validation → Enrichment → Scoring → Storage → Analysis → Response
```

1. **Ingestion**: Multiple alert sources (SIEM, EDR, custom APIs)
2. **Validation**: Schema validation and data normalization
3. **Enrichment**: IOC extraction, threat intelligence lookup
4. **Scoring**: Automated severity assessment
5. **Storage**: Persistent storage in TheHive/Elasticsearch
6. **Analysis**: Pattern recognition and anomaly detection
7. **Response**: Automated playbook execution

### Response Workflow

```
Alert Detection → Triage → Investigation → Containment → Eradication → Recovery → Reporting
```

## Security Architecture

### Defense in Depth

1. **Network Security**
   - Container network isolation
   - Firewall rules
   - TLS encryption
   - VPN access for remote management

2. **Application Security**
   - Input validation
   - SQL injection prevention
   - XSS protection
   - CSRF tokens

3. **Data Security**
   - Encryption at rest
   - Encryption in transit
   - Key management
   - Access controls

4. **Identity Security**
   - Multi-factor authentication
   - Role-based access control
   - Session management
   - Audit logging

### Security Zones

```
┌─────────────────────────────────────────────────────────────┐
│                    DMZ Zone                                   │
│  Web UI  │  API Gateway  │  Load Balancer                    │
├─────────────────────────────────────────────────────────────┤
│                    Application Zone                           │
│  FastAPI  │  Business Logic  │  Authentication               │
├─────────────────────────────────────────────────────────────┤
│                    Data Zone                                  │
│  TheHive  │  Cortex  │  Elasticsearch  │  PostgreSQL         │
├─────────────────────────────────────────────────────────────┤
│                    Management Zone                             │
│  Docker  │  Monitoring  │  Logging  │  Backup                 │
└─────────────────────────────────────────────────────────────┘
```

## Scalability Architecture

### Horizontal Scaling

- **API Layer**: Multiple FastAPI instances behind load balancer
- **Processing Layer**: Distributed alert processing
- **Database Layer**: Read replicas and sharding
- **Storage Layer**: Distributed file storage

### Performance Optimization

1. **Caching Strategy**
   - Redis for frequently accessed data
   - Application-level caching
   - CDN for static assets
   - Database query optimization

2. **Load Balancing**
   - Round-robin API distribution
   - Database connection pooling
   - Async processing queues
   - Resource monitoring

3. **Resource Management**
   - Container resource limits
   - Auto-scaling policies
   - Health checks
   - Graceful degradation

## Integration Architecture

### External Integrations

1. **Security Tools**
   - SIEM systems (Splunk, ELK)
   - EDR solutions (CrowdStrike, SentinelOne)
   - Threat intelligence platforms
   - Vulnerability scanners

2. **Communication Systems**
   - Email notifications
   - Slack/Teams integration
   - SMS alerts
   - Webhook callbacks

3. **Infrastructure**
   - Cloud providers (AWS, Azure, GCP)
   - Container orchestration (Kubernetes)
   - Logging platforms (Splunk, ELK)

### Integration Patterns

1. **API-based Integration**
   - RESTful APIs
   - GraphQL interfaces
   - Webhook subscriptions
   - Event-driven architecture

2. **Message-based Integration**
   - RabbitMQ queues
   - Apache Kafka streams
   - Redis pub/sub
   - Event sourcing

3. **File-based Integration**
   - CSV/JSON imports
   - Log file parsing
   - Configuration synchronization
   - Backup/restore operations

## Deployment Architecture

### Deployed Stack (`infra/docker/docker-compose.yml`)

| Container | Image | Ports (host) |
|---|---|---|
| `soar_nginx` | nginx:1.25-alpine | 80, 443, 8080 |
| `soar_thehive` | strangebee/thehive:5 | 9000 |
| `soar_cortex` | thehive4py/cortex:latest | 9001 |
| `soar_shuffle_backend` | ghcr.io/shuffle/shuffle-backend | 5001 |
| `soar_shuffle_frontend` | ghcr.io/shuffle/shuffle-frontend | 3001 |
| `soar_orborus` | ghcr.io/shuffle/shuffle-orborus | — |
| `soar_wazuh_manager` | wazuh/wazuh-manager:4.8.2 | 1514-1516 |
| `soar_wazuh_dashboard` | kibana:7.17.17 | 15601 |
| `soar_misp` | ghcr.io/misp/misp-docker | 8082 |
| `soar_elasticsearch` | elasticsearch:7.17.17 | internal |
| `soar_redis` | redis:7-alpine | internal |
| `soar_misp_db` | mariadb | internal |
| `soar_api` | build: apps/api | 8000 |
| `soar_docs_site` | build: apps/docs-site | 3000 |

### Docker Networks

- `soar_net` — red interna principal (todos los servicios)
- `soar_edge` — red de acceso externo (nginx, servicios con UI)
- `ti_net` — red de threat intelligence (elasticsearch, MISP)

### Configuration

- Variables de entorno: `.env.full` (raíz del proyecto)
- Compose file: `infra/docker/docker-compose.yml`
- Nginx config: `infra/docker/nginx.conf`
- Cortex config: `infra/docker/docker/cortex.application.conf`

### Environment Configuration

1. **Development Environment**
   - Local Docker Compose
   - Hot reloading
   - Debug logging
   - Test data fixtures

2. **Staging Environment**
   - Production-like setup
   - Performance testing
   - Security scanning
   - Integration testing

3. **Production Environment**
   - High availability setup
   - Load balancing
   - Monitoring and alerting
   - Backup and recovery

## Monitoring Architecture

### Observability Stack

1. **Metrics Collection**
   - Application metrics (response time, error rate)
   - Infrastructure metrics (CPU, memory, disk)
   - Business metrics (alert volume, resolution time)
   - Custom KPIs

2. **Logging Strategy**
   - Structured logging (JSON format)
   - Centralized log aggregation
   - Log rotation and retention
   - Real-time log analysis

3. **Tracing System**
   - Distributed tracing
   - Request correlation IDs
   - Performance profiling
   - Error tracking

### Alerting Strategy

1. **System Alerts**
   - Service health checks
   - Resource utilization thresholds
   - Error rate monitoring
   - Availability tracking

2. **Business Alerts**
   - Alert volume anomalies
   - Response time SLA breaches
   - Security incident triggers
   - Compliance violations

## Backup and Recovery Architecture

### Backup Strategy

1. **Data Backups**
   - PostgreSQL database dumps
   - Elasticsearch snapshots
   - File system backups
   - Configuration backups

2. **Backup Schedule**
   - Incremental backups (hourly)
   - Full backups (daily)
   - Offsite replication (weekly)
   - Retention policy (30 days)

3. **Recovery Procedures**
   - Disaster recovery plan
   - Failover testing
   - Data validation
   - Service restoration

## Development Architecture

### Code Organization

```
src/soar_lab/
├── api/                 # FastAPI application
├── analytics/           # Data processing modules
├── config/              # Configuration management
├── data/                # Data access layer
├── services/            # Business logic services
└── schemas/             # Data validation schemas
```

### Development Workflow

1. **Feature Development**
   - Feature branches
   - Code reviews
   - Automated testing
   - Continuous integration

2. **Testing Strategy**
   - Unit tests (pytest)
   - Integration tests
   - End-to-end tests
   - Performance tests

3. **Quality Assurance**
   - Static code analysis
   - Security scanning
   - Dependency checking
   - Documentation validation

## Technology Stack

### Core Technologies

- **Backend**: Python 3.11, FastAPI (`apps/api/entrypoint.py`)
- **Frontend**: Static HTML/JS (web-management), React (Shuffle)
- **SIEM**: Wazuh Manager 4.8.2
- **Visualization**: Kibana 7.17.17
- **SOAR**: Shuffle (backend + frontend + orborus)
- **Case Management**: TheHive 5 + Cortex
- **Threat Intel**: MISP
- **Search**: Elasticsearch 7.17.17
- **Cache**: Redis 7
- **Proxy**: Nginx 1.25
- **Docs**: Docusaurus 3
- **Containerization**: Docker Compose 2

### Security Technologies

- **Authentication**: JWT, OAuth 2.0
- **Encryption**: TLS 1.3, AES-256
- **Vulnerability Scanning**: OWASP ZAP, Snyk
- **Secret Management**: HashiCorp Vault

### Development Tools

- **Version Control**: Git, GitHub
- **CI/CD**: GitHub Actions, Jenkins
- **Testing**: pytest, Selenium, Playwright
- **Documentation**: MkDocs, Swagger

## Future Architecture Considerations

### Scalability Improvements

1. **Microservices Migration**
   - Service decomposition
   - API gateway implementation
   - Service mesh adoption
   - Event-driven architecture

2. **Cloud Native Transition**
   - Kubernetes orchestration
   - Cloud provider integration
   - Managed services adoption
   - Multi-cloud strategy

### Technology Evolution

1. **AI/ML Integration**
   - Machine learning models
   - Anomaly detection
   - Predictive analytics
   - Natural language processing

2. **Advanced Security**
   - Zero-trust architecture
   - Advanced threat detection
   - Automated response
   - Security orchestration

---

**Document Version**: 1.4.0  
**Last Updated**: 2026-05-14  
**Maintainers**: SOAR Ransomware Lab Architecture Team  
**Review Cycle**: Quarterly
