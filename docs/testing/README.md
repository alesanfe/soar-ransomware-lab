# Testing Documentation

This directory contains comprehensive documentation for the SOAR Ransomware Lab test suite.

## Overview

The SOAR Ransomware Lab project includes a comprehensive test suite covering unit tests, integration tests, browser tests, performance tests, security tests, and end-to-end (E2E) tests.

## Documentation Files

### [tests.md](tests.md)
Main test suite documentation covering:
- Test structure and organization
- Test categories (unit, atomic, integration, browser, performance, security, E2E)
- Running tests (commands, coverage, test runners)
- Test configuration (pytest.ini, markers, fixtures)
- Test environments (local, CI/CD, Docker)
- Best practices and troubleshooting

### [docker-testing-strategy.md](docker-testing-strategy.md)
Comprehensive Docker testing strategy covering:
- Multi-level testing approach (configuration, runtime, browser validation)
- Service coverage for current stack (Elasticsearch, TheHive, Cortex, Shuffle, Kibana, Wazuh Manager, MISP, Redis, MariaDB)
- Network validation (soar_edge, soar_net)
- Volume validation (data persistence)
- Health check validation
- Performance and security validation
- CI/CD integration examples

## Test Suite Structure

```
tests/
├── unit/                    # Unit tests for individual components
├── atomic/                  # Atomic tests for granular function validation
├── integration/             # Integration tests for component interactions
├── browser/                 # Browser tests with Selenium automation
├── performance/             # Performance and stress tests
├── security/                # Security scanning and vulnerability tests
├── e2e/                     # End-to-end workflow tests
├── conftest.py              # Pytest configuration and fixtures
├── TEST_ELIMINATIONS.md     # Documentation of eliminated tests
└── runners/                 # Test execution utilities
```

## Current Stack

The test suite validates the following services:
- **Elasticsearch** (localhost:9200) - Search and analytics engine
- **TheHive** (localhost:9000) - Incident response platform
- **Cortex** (localhost:9001) - Threat analysis engine
- **Shuffle** (localhost:3001) - Workflow orchestration
- **Kibana** (localhost:15601) - Visualization dashboard
- **Wazuh Manager** (localhost:55100) - SIEM/XDR platform
- **MISP** (localhost:8082) - Threat intelligence platform
- **Redis** - Cache and message broker
- **MariaDB** - Database for TheHive, Cortex, MISP

## Quick Start

```bash
# Run all tests
make test-all

# Run specific test categories
make test-unit
make test-atomic
make test-integration
make test-browser
make test-e2e

# Run with coverage
make test-coverage
```

## Test Eliminations

Several test files have been eliminated to maintain a high signal-to-noise ratio. See [../tests/TEST_ELIMINATIONS.md](../tests/TEST_ELIMINATIONS.md) for detailed documentation.

## Coverage Targets

- **Unit tests**: >80% coverage
- **Atomic tests**: >70% coverage
- **Integration tests**: >60% coverage
- **Browser tests**: >50% coverage
- **Security tests**: >60% coverage
- **E2E tests**: >50% coverage

## Related Documentation

- [Main project README](../../README.md)
- [Project documentation](../)
- [Architecture documentation](../architecture.md)
