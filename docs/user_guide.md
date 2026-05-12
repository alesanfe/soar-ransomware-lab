# SOAR Ransomware Lab - User Guide

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Features](#core-features)
5. [Configuration](#configuration)
6. [Security Considerations](#security-considerations)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Usage](#advanced-usage)

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

2. Copy the environment configuration:
   ```bash
   cp docker/.env.example .env
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Verify installation:
   ```bash
   python -m pytest tests/integration/test_configuration.py
   ```

## Quick Start

### First Time Setup

1. Access the web management interface at `http://localhost:9000`
2. Log in with default credentials (admin/admin123)
3. Configure your first alert source
4. Create a test alert to verify functionality

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

Key configuration options in `.env`:

```bash
# Service Ports
THEHIVE_HTTP_PORT=9000
CORTEX_HTTP_PORT=9001
REDIS_PORT=6379

# Authentication
WEB_UI_USER=admin
WEB_UI_PASSWORD=admin123

# Database
POSTGRES_DB=soar_lab
POSTGRES_USER=soar_user
POSTGRES_PASSWORD=secure_password
```

### Service Configuration

- **TheHive**: `infra/docker/docker/thehive.application.conf/thehive.conf`
- **Cortex**: `infra/docker/docker/cortex.application.conf/cortex.conf`
- **Elasticsearch**: Configured via environment variables

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
# Check Docker status
docker-compose ps

# View service logs
docker-compose logs thehive
docker-compose logs cortex
```

#### Database Connection Errors

1. Verify PostgreSQL is running
2. Check connection string in `.env`
3. Restart services: `docker-compose restart`

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

**Last Updated**: $(date '+%Y-%m-%d')
**Version**: 1.0.0
**Maintainers**: SOAR Ransomware Lab Team
