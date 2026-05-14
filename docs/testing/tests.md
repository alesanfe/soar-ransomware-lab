# SOAR Ransomware Lab - Test Suite

Comprehensive test suite for the SOAR Ransomware Lab project, covering unit tests, integration tests, performance tests, security tests, and end-to-end (E2E) tests.

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_api_main_endpoints.py # API endpoint tests
│   ├── test_data_manager_unit.py # Data manager tests
│   ├── test_kpi_calculator_unit.py # KPI calculation tests
│   ├── test_generate_secrets_unit.py # Secret generation tests
│   ├── test_send_alert_unit.py # Alert sending tests
│   ├── test_tfm_data_enhancer_methods.py # TFM data enhancement tests
│   └── test_tfm_data_viewer_unit.py # TFM data visualization tests
├── atomic/                  # Atomic tests
│   ├── test_alert_validation.py # Alert validation tests
│   ├── test_ioc_generator.py # IOC generator tests
│   ├── test_kpi_calculator_core.py # KPI calculator core tests
│   ├── test_kpi_calculator_edge_cases.py # KPI calculator edge cases
│   ├── test_schema_validation.py # Schema validation tests
│   └── test_secrets_generator.py # Secrets generator tests
├── integration/             # Integration tests
│   ├── test_api_endpoints.py # API endpoint tests
│   ├── test_api_integration.py # API integration tests
│   ├── test_backup_restore.py # Backup/restore tests
│   ├── test_configuration.py # Configuration tests
│   ├── test_docker_browser_automation.py # Docker browser automation
│   ├── test_docker_build_validation.py # Docker build validation
│   ├── test_docker_service_contracts_live.py # Docker service contracts
│   ├── test_feature_component_contracts.py # Feature component contracts
│   ├── test_feature_workflows_comprehensive.py # Feature workflows tests
│   └── test_security.py     # Security integration tests
├── browser/                 # Browser tests (Selenium)
│   ├── mock_services.py     # Mock services for browser tests
│   ├── test_container_ports_browser.py # Container ports browser tests
│   ├── test_docs_site_browser.py # Docs site browser tests
│   ├── test_live_service_ui_smoke.py # Live service UI smoke tests
│   ├── test_live_web_services_access.py # Live web services access
│   ├── test_live_web_services_validation.py # Live web services validation
│   ├── test_mock_service_ui_structure.py # Mock service UI structure
│   ├── test_mock_soar_service_pages.py # Mock SOAR service pages
│   └── test_web_management_browser.py # Web management browser tests
├── performance/             # Performance tests
│   ├── test_load.py         # Load testing
│   └── test_stress.py       # Stress testing
├── security/                # Security tests
│   └── test_automated_security.py # Automated security tests
├── e2e/                     # End-to-end tests
│   ├── TC-01/
│   │   └── test_malicious.py # Malicious ransomware scenario
│   ├── TC-02/
│   │   └── test_benign.py    # Benign false positive scenario
│   └── TC-03/
│       └── test_edge_cases.py # Edge cases and boundary conditions
├── conftest.py              # Pytest configuration and fixtures
├── TEST_ELIMINATIONS.md     # Documentation of eliminated tests
└── runners/                 # Test execution utilities
    └── pytest_runner.py     # Pytest runner
```

## Test Categories

### Unit Tests
Test individual components and functions in isolation.

- **test_api_main_endpoints.py**: Tests API endpoint functionality
- **test_data_manager_unit.py**: Tests data management operations
- **test_kpi_calculator_unit.py**: Tests KPI calculation logic, MTTR metrics, and statistical analysis
- **test_generate_secrets_unit.py**: Tests secret generation, password policies, and entropy
- **test_send_alert_unit.py**: Tests alert sending functionality and payload validation
- **test_tfm_data_enhancer_methods.py**: Tests TFM data enhancement and analysis methods
- **test_tfm_data_viewer_unit.py**: Tests TFM data visualization and reporting

### Atomic Tests
Test individual functions and methods at the most granular level.

- **test_alert_validation.py**: Atomic alert validation tests
- **test_ioc_generator.py**: Atomic IOC generation tests
- **test_kpi_calculator_core.py**: Atomic KPI calculation core tests
- **test_kpi_calculator_edge_cases.py**: Atomic KPI calculation edge case tests
- **test_schema_validation.py**: Atomic schema validation tests
- **test_secrets_generator.py**: Atomic secrets generation tests

### Integration Tests
Test interactions between different components and services.

- **test_api_endpoints.py**: Tests API connectivity, authentication, and rate limiting
- **test_api_integration.py**: Tests API integration with external services
- **test_backup_restore.py**: Tests backup creation and restoration functionality
- **test_configuration.py**: Tests configuration loading and validation
- **test_docker_browser_automation.py**: Tests Docker browser automation
- **test_docker_build_validation.py**: Tests Docker build validation
- **test_docker_service_contracts_live.py**: Tests Docker service contracts
- **test_feature_component_contracts.py**: Tests feature component contracts
- **test_feature_workflows_comprehensive.py**: Tests feature workflows
- **test_security.py**: Tests security integration across components

### Browser Tests
Test web interfaces with Selenium automation.

- **test_container_ports_browser.py**: Tests container ports with browser
- **test_docs_site_browser.py**: Tests documentation site
- **test_live_service_ui_smoke.py**: Smoke tests for live service UI
- **test_live_web_services_access.py**: Tests live web services access
- **test_live_web_services_validation.py**: Tests live web services validation
- **test_mock_service_ui_structure.py**: Tests mock service UI structure
- **test_mock_soar_service_pages.py**: Tests mock SOAR service pages
- **test_web_management_browser.py**: Tests web management interface

### Performance Tests
Test system performance under various load conditions.

- **test_load.py**: Load testing with concurrent requests and throughput measurement
- **test_stress.py**: Stress testing with extreme load conditions and bottleneck analysis

### Security Tests
Test security aspects and vulnerability detection.

- **test_automated_security.py**: Automated security scanning and vulnerability assessment

### End-to-End Tests
Test complete workflows from start to finish.

- **TC-01/test_malicious.py**: Complete malicious ransomware alert handling workflow
- **TC-02/test_benign.py**: Complete benign alert (false positive) handling workflow
- **TC-03/test_edge_cases.py**: Edge cases, boundary conditions, and error scenarios

## Test Eliminations

Several test files have been eliminated to maintain a high signal-to-noise ratio. See [TEST_ELIMINATIONS.md](TEST_ELIMINATIONS.md) for detailed documentation.

## Running Tests

### Quick Start

```bash
# Run all tests
make test-all

# Run specific test categories
make test-unit
make test-atomic
make test-security
make test-integration
make test-performance
make test-e2e

# Run with coverage
make test-coverage
```

### Individual Test Execution

```bash
# Run unit tests
python3 -m pytest tests/unit/ -v

# Run atomic tests
python3 -m pytest tests/atomic/ -v

# Run security tests
python3 -m pytest tests/security/ -v

# Run integration tests
python3 -m pytest tests/integration/ -v

# Run performance tests
python3 -m pytest tests/performance/ -v

# Run E2E tests
python3 -m pytest tests/e2e/ -v

# Run specific test file
python3 -m pytest tests/unit/test_calc_kpis.py -v

# Run with coverage
python3 -m pytest tests/ --cov=scripts --cov=config --cov-report=html --cov-report=term --cov-fail-under=80
```

### Test Runner Script

```bash
# Run comprehensive test suite
python tests/run_all_tests.py

# Run with specific options
python tests/run_all_tests.py --unit-only
python tests/run_all_tests.py --integration-only
python tests/run_all_tests.py --e2e-only
python tests/run_all_tests.py --generate-report
```

## Test Configuration

### pytest.ini Configuration

The test suite is configured via `pytest.ini`:

```ini
[pytest]
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests
addopts = -v --strict-markers --tb=short --disable-warnings
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    docker: Tests requiring Docker
    network: Tests requiring network access
```

### Test Markers

Use markers to run specific test types:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only E2E tests
pytest -m e2e

# Skip slow tests
pytest -m "not slow"

# Run tests requiring Docker
pytest -m docker
```

## Test Data and Fixtures

### Test Data Location
- Test data files: `tests/fixtures/`
- Sample configurations: `tests/fixtures/configs/`
- Mock responses: `tests/fixtures/responses/`

### Test Fixtures
Common test fixtures are available in `tests/conftest.py`:

```python
@pytest.fixture
def sample_alert():
    """Sample ransomware alert for testing"""
    return {
        "alert_id": "TEST-001",
        "event_type": "ransomware_detection",
        "severity": "2",
        "timestamp": "2024-01-01T12:00:00Z",
        "source": "test_source"
    }

@pytest.fixture
def mock_thehive_client():
    """Mock TheHive API client"""
    with patch('scripts.send_alert.TheHiveClient') as mock:
        yield mock
```

## Coverage Reports

### Generating Coverage

```bash
# Generate HTML coverage report
make test-coverage

# View coverage report
open htmlcov/index.html
```

### Coverage Targets

- **Unit tests**: >80% coverage
- **Atomic tests**: >70% coverage
- **Integration tests**: >60% coverage
- **Browser tests**: >50% coverage
- **Security tests**: >60% coverage
- **Performance tests**: N/A (performance benchmarks)
- **E2E tests**: >50% coverage

## Test Environments

### Local Development
```bash
# Setup test environment
make deps-test

# Run tests locally
make test-all
```

### CI/CD Pipeline
Tests run automatically on:
- Pull requests
- Push to main branch
- Daily scheduled runs

### Docker Test Environment
```bash
# Run tests in Docker
docker-compose -f infra/docker/docker-compose.yml up
python -m pytest tests/ -v
```

## Test Results and Reports

### Result Files
- Test results: `artifacts/results/test_results.json`
- Coverage reports: `artifacts/coverage/htmlcov/`
- Performance reports: `artifacts/results/performance/`
- Security reports: `artifacts/results/security/`

### Report Formats
- JSON: Machine-readable results
- HTML: Human-readable coverage reports
- JUnit XML: CI/CD integration
- Console: Real-time output

## Troubleshooting

### Common Issues

#### Tests Fail Due to Missing Services
```bash
# Start required services
make up

# Check service health
make health
```

#### Permission Issues
```bash
# Fix test permissions
chmod +x tests/**/*.py
```

#### Docker Test Issues
```bash
# Clean Docker environment
docker system prune -f
docker-compose down -v
```

### Debugging Tests

#### Verbose Output
```bash
pytest -v -s tests/unit/test_calc_kpis.py
```

#### Debug Mode
```bash
pytest --pdb tests/unit/test_calc_kpis.py
```

#### Stop on First Failure
```bash
pytest -x tests/
```

## Best Practices

### Writing Tests

1. **Descriptive Names**: Use clear, descriptive test names
2. **Arrange-Act-Assert**: Structure tests clearly
3. **Test Isolation**: Tests should not depend on each other
4. **Mock External Dependencies**: Use mocks for external services
5. **Test Edge Cases**: Include boundary conditions and error scenarios

### Test Organization

1. **Group Related Tests**: Organize by functionality
2. **Use Fixtures**: Share common setup code
3. **Parameterize Tests**: Test multiple scenarios with one test
4. **Clear Assertions**: Use descriptive assertion messages

### Performance Testing

1. **Baseline Measurements**: Establish performance baselines
2. **Isolate Tests**: Run performance tests separately
3. **Measure Resources**: Monitor CPU, memory, and network usage
4. **Statistical Analysis**: Use statistical methods for performance validation

## Continuous Integration

### GitHub Actions
Tests run on:
- Ubuntu and Windows runners
- Python 3.9+
- Multiple Docker versions

### Test Matrix
```yaml
strategy:
  matrix:
    python-version: [3.9, '3.10', 3.11]
    os: [ubuntu-latest, windows-latest]
```

### Quality Gates
- All tests must pass
- Coverage threshold must be met
- Security scans must be clean
- Performance tests must meet baselines

## Contributing

When adding new tests:

1. **Follow Naming Conventions**: Use `test_*.py` naming
2. **Add Documentation**: Document complex test scenarios
3. **Update Coverage**: Maintain coverage thresholds
4. **Test Categories**: Use appropriate markers
5. **Include Examples**: Provide usage examples in docstrings

## Security Testing

### Automated Scans
- **Bandit**: Python security scanner
- **Safety**: Dependency vulnerability scanner
- **Semgrep**: Static analysis for security bugs

### Manual Testing
- **Penetration Testing**: Regular security assessments
- **Threat Modeling**: Identify potential attack vectors
- **Compliance Checks**: Verify security compliance

## Performance Testing

### Load Testing
- **Concurrent Users**: Test with 10, 50, 100 concurrent users
- **Response Times**: Verify <2s response times
- **Throughput**: Measure requests per second

### Stress Testing
- **Resource Limits**: Test system limits and degradation
- **Memory Leaks**: Check for memory leaks
- **Database Performance**: Test query performance under load

## Test Documentation

### Inline Documentation
- Use docstrings for test functions
- Document complex scenarios
- Include examples in docstrings

### External Documentation
- Update this README for major changes
- Document test requirements and setup
- Include troubleshooting guides

---

For more information about the SOAR Ransomware Lab project, see the main [README.md](../../README.md) and [project documentation](../).
