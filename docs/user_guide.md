# SOAR Ransomware Lab - User Guide

## Overview

SOAR Ransomware Lab is a comprehensive security orchestration, automation and response platform designed for ransomware incident handling. This guide will help you get started with the platform and understand its key features.

## Installation

### Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher
- Git
- At least 8GB RAM
- 20GB free disk space

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/soar-ransomware-lab.git
   cd soar-ransomware-lab
   ```

2. Review and edit environment configuration:
   ```bash
   nano .env.full
   ```

3. Start the full stack:
   ```bash
   make up
   ```

4. Verify all services are healthy:
   ```bash
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```

## Quick Start

### Service Access URLs

| Service | URL | Purpose |
|---|---|---|
| **Web Management UI** | http://localhost | Main management dashboard |
| **Nginx Proxy** | http://localhost:8080 | Unified reverse proxy to all services |
| **TheHive** | http://localhost:9000 | Incident case management |
| **Cortex** | http://localhost:9001 | IoC analysis and enrichment |
| **Shuffle UI** | http://localhost:3001 | SOAR orchestration workflows |
| **Shuffle API** | http://localhost:5001 | Shuffle REST API |
| **Kibana** | http://localhost:15601 | Log visualization and dashboards |
| **MISP** | http://localhost:8082 | Threat intelligence platform |
| **Lab API** | http://localhost:8000 | Lab management REST API |
| **Documentation** | http://localhost:3000/docs/ | Project documentation site |

### Via Nginx Proxy (port 8080)

All services are also accessible through the Nginx reverse proxy:

| Path | Proxies to |
|---|---|
| http://localhost:8080/thehive/ | TheHive |
| http://localhost:8080/cortex/ | Cortex |
| http://localhost:8080/shuffle/ | Shuffle UI |
| http://localhost:8080/kibana/ | Kibana |
| http://localhost:8080/api/ | Lab API |
| http://localhost:8080/misp/ | MISP |
| http://localhost:8080/docs/ | Documentation |

### First Time Setup

1. Access TheHive at `http://localhost:9000` — default admin credentials in `.env.full`
2. Access Kibana at `http://localhost:15601` — configure index patterns for Wazuh logs
3. Access Shuffle at `http://localhost:3001` — import or create response playbooks
4. Access MISP at `http://localhost:8082` — configure threat intelligence feeds

### Basic Workflow

1. **Alert Ingestion**: Receive alerts from various sources
2. **Analysis**: Analyze alerts using automated tools
3. **Response**: Execute response playbooks
4. **Reporting**: Generate incident reports

## Core Features

### Alert Management

- **Multi-source ingestion**: TheHive, Cortex, custom APIs
- **Alert enrichment**: IOC extraction, threat intelligence
- **Priority scoring**: Automated severity assessment
- **Case management**: Track incidents from detection to resolution

### Automation Engine

- **Playbook execution**: Automated response procedures
- **Custom workflows**: Create your own response sequences
- **Integration support**: Connect with external security tools
- **Scheduling**: Automated periodic tasks and health checks

### Analytics & Reporting

- **KPI Dashboard**: Real-time metrics and performance indicators
- **Historical analysis**: Trend analysis and incident patterns
- **Custom reports**: Export data in multiple formats
- **Compliance reporting**: Generate audit-ready documentation

### Security Features

- **Role-based access control**: Granular permissions
- **Audit logging**: Complete activity tracking
- **Encryption**: Data at rest and in transit
- **Network isolation**: Secure communication channels

## Configuration

### Environment Variables

All configuration lives in `.env.full` at the project root:

```bash
# Service Ports
THEHIVE_HTTP_PORT=9000
CORTEX_HTTP_PORT=9001
SHUFFLE_UI_PORT=3001
SHUFFLE_API_PORT=5001
WAZUH_DASHBOARD_PORT=15601   # Kibana
ELASTICSEARCH_PORT=9201      # Internal only on Docker Desktop/Windows
REDIS_PORT=6379
DOCS_PORT=3000
API_PORT=8000
HTTP_PORT=80
HTTPS_PORT=443
WEB_UI_PORT=8080

# Wazuh
WAZUH_EVENTS_PORT=1514

# Credentials (change before deploying!)
ELASTIC_PASSWORD=...
SHUFFLE_DEFAULT_PASSWORD=...
THEHIVE_SECRET=...
```

### Service Configuration Files

- **Nginx**: `infra/docker/nginx.conf`
- **Cortex**: `infra/docker/docker/cortex.application.conf`
- **TheHive**: configured via environment variables
- **Kibana**: configured via environment variables in `docker-compose.yml`
- **Elasticsearch**: configured via environment variables

### Custom Integrations

Add new integrations by:

1. Creating configuration files in `infra/docker/docker/`
2. Updating Docker Compose services
3. Adding validation tests in `tests/integration/`

## Security Considerations

### Network Security

- All services run in isolated Docker networks
- External access controlled via firewall rules
- SSL/TLS encryption for all communications

### Data Protection

- Sensitive data encrypted at rest
- Regular automated backups
- Secure key management

### Access Control

- Multi-factor authentication support
- Role-based permissions
- Session timeout policies

### Compliance

- GDPR compliance features
- Audit trail maintenance
- Data retention policies

## Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check status of all containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# View logs for a specific service
docker logs soar_thehive --tail 50
docker logs soar_elasticsearch --tail 50

# Restart the full stack
make down && make up
```

#### Port Already Allocated (Windows/Docker Desktop)

Some ports may be reserved by Hyper-V on Windows. Check excluded ranges:
```powershell
netsh int ipv4 show excludedportrange protocol=tcp
```
If a port is in an excluded range, change it in `.env.full` and re-run `make up`.

#### Elasticsearch Not Accessible from Host (Windows)

This is a known Docker Desktop bug on Windows with custom networks. Elasticsearch is only accessible internally. All services that need it (Kibana, Shuffle, TheHive) connect through the Docker network and work correctly.

#### Performance Issues

1. Monitor resource usage: `docker stats`
2. Check Elasticsearch cluster health
3. Review log files for errors

### Debug Mode

Enable debug logging:

```bash
# Set log level
LOG_LEVEL=DEBUG

# View detailed logs
docker-compose logs -f --tail=100
```

### Getting Help

- Check the [Architecture Documentation](docs/architecture.md)
- Review [Security Guidelines](docs/security.md)
- Open an issue on GitHub
- Join our community Discord

## Advanced Usage

### Custom Playbooks

Create custom response playbooks:

```python
# Example: Custom ransomware response playbook
def ransomware_response(alert):
    """
    Automated response to ransomware alerts
    """
    # Isolate affected host
    isolate_host(alert.hostname)
    
    # Collect forensic evidence
    collect_evidence(alert.hostname)
    
    # Notify security team
    send_notification(alert)
    
    # Create incident case
    create_case(alert)
```

### API Integration

Use the REST API for programmatic access:

```bash
# Get all alerts
curl -X GET "http://localhost:9000/api/alerts" \
     -H "Authorization: Bearer $TOKEN"

# Create new alert
curl -X POST "http://localhost:9000/api/alerts" \
     -H "Content-Type: application/json" \
     -d '{"alert_type": "ransomware", "severity": "high"}'
```

### Performance Optimization

- Tune Elasticsearch settings
- Optimize database queries
- Implement caching strategies
- Monitor resource usage

### Scaling Considerations

- Horizontal scaling with multiple instances
- Load balancing configuration
- Database optimization
- Storage capacity planning

## Best Practices

### Operational

1. **Regular Updates**: Keep dependencies current
2. **Backup Strategy**: Daily automated backups
3. **Monitoring**: Set up alerting for critical metrics
4. **Testing**: Regular security drills and simulations

### Security

1. **Principle of Least Privilege**: Minimal required permissions
2. **Regular Audits**: Quarterly security assessments
3. **Incident Response**: Maintain updated response plans
4. **Training**: Regular security awareness training

### Development

1. **Code Review**: All changes require peer review
2. **Testing**: Comprehensive test coverage
3. **Documentation**: Keep docs updated with features
4. **Version Control**: Semantic versioning practices

## Support and Community

- **Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/)
- **Tests**: [tests/](tests/)
- **Issues**: [GitHub Issues](https://github.com/your-org/soar-ransomware-lab/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/soar-ransomware-lab/discussions)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Code standards
- Testing requirements
- Documentation updates
- Security considerations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Last Updated**: 2026-05-14
**Version**: 1.4.0
**Maintainers**: SOAR Ransomware Lab Team
