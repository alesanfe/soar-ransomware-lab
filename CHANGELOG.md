# Changelog

All notable changes to the SOAR Ransomware Lab project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Prometheus + Grafana monitoring integration
- Enhanced security testing framework
- Performance benchmarking tools

---

## [1.4.0] - 2026-05-14

### 🚀 Added
- **Kibana 7.17.17** como dashboard de visualización (reemplaza Wazuh Dashboard incompatible)
- **MISP** como plataforma de Threat Intelligence integrada en el stack
- Ruta `/kibana/` en Nginx reverse proxy
- `KIBANA_ENCRYPTION_KEY` en `.env.full`
- Volumen `kibana_data` para persistencia de Kibana

### 🔧 Fixed
- **API**: corregido `CMD` del Dockerfile de `main:app` a `entrypoint:app`
- **API healthcheck**: reemplazado `wget`/`curl` por `python -c urllib.request` (imagen slim sin herramientas HTTP)
- **Nginx healthcheck**: cambiado `localhost` a `127.0.0.1` (resolución IPv6 en Alpine)
- **Nginx config**: corregida ruta del volumen de `./docker/nginx.conf` a `./nginx.conf`
- **Orborus healthcheck**: corregido endpoint de `/health` a `/api/v1/health`
- **Docs-site healthcheck**: corregido path de `/` a `/docs/` (404 en raíz)
- **Elasticsearch**: eliminado alias de red `wazuh.indexer` (no necesario con Kibana)
- **Wazuh Dashboard**: eliminado (incompatible con Elasticsearch puro, requiere OpenSearch+TLS)
- Puerto `WAZUH_DASHBOARD_PORT` cambiado de `5601` a `15601` (rango excluido por Hyper-V)
- Puerto `WAZUH_API_PORT` cambiado de `55000` a `55100` (rango excluido por Hyper-V)
- Eliminado binding de host para Wazuh API (puerto bloqueado por Windows)
- Wazuh Manager healthcheck actualizado a HTTPS con aceptación de 401
- Shuffle Backend: añadidas variables `SHUFFLE_OPENSEARCH_USERNAME/PASSWORD`
- Cortex healthcheck: cambiado de `/api/health` (501) a verificación de código HTTP en `/`
- Wazuh Dashboard dependency en Nginx: cambiado a `service_started`

### 📝 Changed
- `README.md`: tabla de servicios con URLs y puertos reales
- `docs/architecture.md`: diagrama actualizado con stack completo
- `docs/user_guide.md`: URLs correctas, guía de troubleshooting Windows
- `infra/docker/nginx.conf`: upstream `kibana`, ruta `/kibana/`

---

## [2.0.0] - 2024-05-03

### 🚀 Major Features

#### Security Enhancements
- **Implemented HTTPS/TLS with Nginx reverse proxy**
  - Added SSL/TLS termination
  - Configured security headers
  - Implemented rate limiting
  - Added WebSocket support

- **Network Firewall Configuration**
  - Created comprehensive firewall setup script
  - Configured UFW with Docker network rules
  - Added rate limiting and logging
  - Implemented automated backup and restore

- **Advanced Authentication & Authorization**
  - Enhanced token-based authentication
  - Added role-based access control
  - Implemented API key management
  - Added session management

#### Code Quality Improvements
- **Type Safety with Pydantic**
  - Added comprehensive data validation schemas
  - Implemented type hints throughout codebase
  - Added input validation for all APIs
  - Created validation helpers and utilities

- **Structured Logging System**
  - Replaced print() statements with proper logging
  - Added structured JSON logging
  - Implemented log rotation and management
  - Added centralized logging configuration

- **Exception Handling Enhancement**
  - Improved error handling in calc_kpis.py
  - Added specific exception types
  - Implemented graceful degradation
  - Added comprehensive error reporting

#### Testing Framework
- **Load & Stress Testing**
  - Created comprehensive load testing suite
  - Added stress testing for high-volume scenarios
  - Implemented performance benchmarking
  - Added concurrent request testing

- **Automated Security Testing**
  - Created automated security test suite
  - Added injection attack testing
  - Implemented XSS protection testing
  - Added authentication and authorization testing

- **Enhanced Test Coverage**
  - Implemented comprehensive coverage reporting
  - Added HTML and XML coverage reports
  - Set coverage thresholds and quality gates
  - Added annotation coverage visualization

#### Infrastructure & Operations
- **Automated Backup System**
  - Created comprehensive backup automation
  - Added scheduled backup capabilities
  - Implemented backup verification and integrity checks
  - Added retention policies and cleanup

- **CI/CD Pipeline**
  - Implemented complete GitHub Actions workflow
  - Added automated testing and quality checks
  - Integrated security scanning with Trivy
  - Added automated deployment and release

- **Configuration Management**
  - Created centralized configuration system
  - Added environment-based configuration
  - Implemented configuration validation
  - Added configuration documentation

### 📚 Documentation & Standards

#### API Documentation
- Created comprehensive API documentation
- Added interactive API examples
- Implemented SDK documentation
- Added testing and troubleshooting guides

#### Contributing Guidelines
- Created detailed contributing guide
- Added code style and standards documentation
- Implemented review process guidelines
- Added community guidelines and code of conduct

#### Enhanced Documentation
- Updated README with latest features
- Added installation and setup guides
- Created troubleshooting documentation
- Added security best practices guide

### 🔧 Technical Improvements

#### Docker & Infrastructure
- **Enhanced Docker Configuration**
  - Improved health checks for all services
  - Added resource limits and reservations
  - Implemented log rotation policies
  - Added multi-stage build optimizations

- **Network Configuration**
  - Added internal network isolation
  - Configured proper service discovery
  - Implemented load balancing
  - Added network security policies

#### Performance Optimizations
- **Database Optimizations**
  - Added connection pooling
  - Implemented query optimization
  - Added indexing strategies
  - Configured caching layers

- **API Performance**
  - Added response caching
  - Implemented request compression
  - Added connection keep-alive
  - Optimized serialization

### 🛡️ Security Improvements

#### Enhanced Security Measures
- **Input Validation**
  - Added comprehensive input sanitization
  - Implemented SQL injection prevention
  - Added XSS protection mechanisms
  - Created file upload security

- **Authentication & Authorization**
  - Enhanced token validation
  - Added session management
  - Implemented role-based access
  - Added audit logging

- **Infrastructure Security**
  - Configured secure defaults
  - Added network segmentation
  - Implemented firewall rules
  - Added security monitoring

#### Vulnerability Management
- **Automated Scanning**
  - Integrated Trivy vulnerability scanning
  - Added dependency scanning
  - Implemented security reporting
  - Added remediation tracking

### 🔄 Breaking Changes

#### Configuration Changes
- **Environment Variables**
  - Renamed several environment variables for clarity
  - Added new required security configurations
  - Changed default security settings
  - Updated configuration validation

#### API Changes
- **Authentication**
  - Changed authentication header format
  - Updated token validation logic
  - Modified error response format
  - Added new required fields

#### Docker Changes
- **Service Configuration**
  - Updated service names and networking
  - Changed default ports and URLs
  - Modified volume mounting strategies
  - Updated health check endpoints

### 📦 Dependencies

#### Added
- `pydantic` - Data validation and serialization
- `aiohttp` - Async HTTP client/server
- `pytest-asyncio` - Async testing support
- `pytest-cov` - Coverage reporting
- `black` - Code formatting
- `isort` - Import sorting
- `mypy` - Type checking
- `trivy` - Security scanning

#### Updated
- Updated all Docker images to latest stable versions
- Upgraded Python dependencies to latest versions
- Updated security patches and vulnerabilities
- Improved dependency security scanning

#### Removed
- Deprecated utility functions
- Legacy configuration options
- Unused dependencies
- Outdated testing utilities

### 🐛 Bug Fixes

#### Core Functionality
- Fixed hash validation in send_alert.py
- Resolved memory leaks in long-running processes
- Fixed race conditions in concurrent operations
- Resolved database connection issues

#### Security Fixes
- Fixed authentication bypass vulnerabilities
- Resolved input validation issues
- Fixed XSS vulnerabilities in web interface
- Patched information disclosure issues

#### Performance Fixes
- Resolved performance bottlenecks
- Fixed memory usage issues
- Optimized database queries
- Improved response times

### 📈 Metrics & Monitoring

#### New Metrics
- Added application performance metrics
- Implemented security event tracking
- Added business intelligence metrics
- Created operational dashboards

#### Monitoring Enhancements
- Enhanced health check endpoints
- Added performance monitoring
- Implemented alerting mechanisms
- Created monitoring documentation

---

## [1.2.0] - 2024-04-15

### Added
- Enhanced testing framework with 150+ tests
- Added integration and E2E test suites
- Implemented comprehensive test coverage
- Added performance testing capabilities

### Changed
- Improved error handling and logging
- Enhanced Docker configuration
- Updated documentation and guides
- Optimized resource usage

### Fixed
- Resolved container startup issues
- Fixed network connectivity problems
- Patched security vulnerabilities
- Improved data validation

---

## [1.1.0] - 2024-03-20

### Added
- Basic CI/CD pipeline with GitHub Actions
- Added automated testing workflows
- Implemented security scanning
- Added code quality checks

### Changed
- Updated Docker images to latest versions
- Improved configuration management
- Enhanced logging and monitoring
- Updated dependencies and packages

### Fixed
- Fixed container networking issues
- Resolved permission problems
- Patched memory leaks
- Improved error handling

---

## [1.0.0] - 2024-02-01

### Added
- Initial SOAR Ransomware Lab release
- Basic Docker Compose setup
- Core SOAR components (TheHive, Cortex, Shuffle)
- Elasticsearch integration
- Basic alert processing pipeline
- Initial documentation
- Basic testing framework

### Security
- Default security configurations
- Basic authentication mechanisms
- Network isolation
- Data encryption at rest

### Documentation
- README with installation guide
- Basic user documentation
- API documentation
- Troubleshooting guide

---

## Version History Summary

| Version | Release Date | Major Changes |
|---------|--------------|---------------|
| 2.0.0 | 2024-05-03 | Complete security overhaul, advanced testing, CI/CD |
| 1.2.0 | 2024-04-15 | Enhanced testing framework, performance improvements |
| 1.1.0 | 2024-03-20 | CI/CD pipeline, security scanning, code quality |
| 1.0.0 | 2024-02-01 | Initial release, basic SOAR functionality |

---

## Migration Guide

### From 1.x to 2.0

#### Breaking Changes
1. **Environment Variables**
   ```bash
   # Old format
   SHUFFLE_DEFAULT_PASSWORD=ChangeMe!
   
   # New format
   SHUFFLE_DEFAULT_PASSWORD=<GENERATE_STRONG_PASSWORD_HERE>
   ```

2. **Authentication**
   ```bash
   # Old format
   Authorization: Basic <base64-token>
   
   # New format
   Authorization: Bearer <api-token>
   ```

3. **API Endpoints**
   ```bash
   # Old endpoints
   /webhook/siem
   
   # New endpoints
   /api/v1/webhooks/siem
   ```

#### Migration Steps
1. Backup existing configuration
2. Update environment variables
3. Generate new security tokens
4. Update API client code
5. Test new authentication
6. Verify functionality

#### Required Actions
- [ ] Generate new secrets using `make generate-secrets`
- [ ] Update API authentication methods
- [ ] Test all integrations
- [ ] Update monitoring and alerting
- [ ] Review security configurations

---

## Security Advisory

### Critical Security Updates

#### Version 2.0.0
- **CVE-2024-XXXXX**: Fixed authentication bypass
- **CVE-2024-XXXXY**: Patched XSS vulnerability
- **CVE-2024-XXXXZ**: Resolved information disclosure

#### Recommended Actions
1. Update to version 2.0.0 immediately
2. Rotate all API keys and tokens
3. Review access logs for suspicious activity
4. Update firewall rules
5. Enable enhanced monitoring

---

## Support and Maintenance

### Supported Versions
- **2.0.x**: Current stable version (full support)
- **1.2.x**: Legacy version (security updates only)
- **1.1.x**: End of life (no support)
- **1.0.x**: End of life (no support)

### Maintenance Schedule
- **2.0.x**: Active development and support
- **1.2.x**: Security patches only (until 2024-12-31)
- **Older versions**: No maintenance

### Upgrade Path
- Always upgrade to the latest 2.0.x version
- Review breaking changes in release notes
- Test in staging environment first
- Backup before upgrading

---

## Contributing to Changelog

### Guidelines
- Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format
- Use semantic versioning
- Include security advisories for critical issues
- Document breaking changes clearly

### Adding Entries
1. Choose appropriate section (Added/Changed/Deprecated/Removed/Fixed/Security)
2. Use clear, concise descriptions
3. Include relevant issue numbers
4. Add impact assessment for breaking changes

### Example Entry
```markdown
### Fixed
- Fixed authentication token validation (#123)
- Resolved memory leak in alert processing (#124)
```

---

For more detailed information about specific releases, please refer to the [GitHub Releases](https://github.com/your-org/soar-ransomware-lab/releases) page.
