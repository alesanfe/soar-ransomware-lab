# SOAR Ransomware Lab - Test Suite

Comprehensive test suite for the SOAR Ransomware Lab project, covering unit tests, integration tests, performance tests, security tests, and end-to-end (E2E) tests.

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_calc_kpis.py    # KPI calculation tests
│   ├── test_generate_iocs.py # IOC generation tests
│   ├── test_generate_secrets.py # Secret generation tests
│   ├── test_schemas.py      # Schema validation tests
│   ├── test_send_alert.py   # Alert sending tests
│   ├── test_bash_scripts.py # Bash script tests
│   └── test_powershell.py   # PowerShell script tests
├── integration/             # Integration tests
│   ├── test_api_endpoints.py # API endpoint tests
│   ├── test_backup_restore.py # Backup/restore tests
│   ├── test_configuration.py # Configuration tests
│   ├── test_docker.py       # Docker integration tests
│   ├── test_docker_services.py # Docker services tests
│   └── test_security.py     # Security integration tests
├── performance/             # Performance tests
│   ├── test_load.py         # Load testing
│   └── test_stress.py       # Stress testing
├── security/                # Security tests
│   ├── test_automated_security.py # Automated security tests
│   └── test_input_validation.py # Input validation security tests
├── e2e/                     # End-to-end tests
│   ├── TC-01/
│   │   └── test_malicious.py # Malicious ransomware scenario
│   ├── TC-02/
│   │   └── test_benign.py    # Benign false positive scenario
│   └── TC-03/
│       └── test_edge_cases.py # Edge cases and boundary conditions
├── run_all_tests.py         # Comprehensive test runner
└── README.md               # This file
```

## Test Categories

### Unit Tests
Test individual components and functions in isolation.

- **test_calc_kpis.py**: Tests KPI calculation logic, MTTR metrics, and statistical analysis
- **test_generate_iocs.py**: Tests IOC generation, hash creation, and security aspects
- **test_generate_secrets.py**: Tests secret generation, password policies, and entropy
- **test_schemas.py**: Tests JSON schema validation and data structure verification
- **test_send_alert.py**: Tests alert sending functionality and payload validation
- **test_bash_scripts.py**: Tests Bash script execution and error handling
- **test_powershell.py**: Tests PowerShell script execution and cross-platform compatibility

### Integration Tests
Test interactions between different components and services.

- **test_api_endpoints.py**: Tests API connectivity, authentication, and rate limiting
- **test_backup_restore.py**: Tests backup creation and restoration functionality
- **test_configuration.py**: Tests configuration loading and validation
- **test_docker.py**: Tests Docker container management and networking
- **test_docker_services.py**: Tests Docker service health and resource usage
- **test_security.py**: Tests security integration across components

### Performance Tests
Test system performance under various load conditions.

- **test_load.py**: Load testing with concurrent requests and throughput measurement
- **test_stress.py**: Stress testing with extreme load conditions and bottleneck analysis

### Security Tests
Test security aspects and vulnerability detection.

- **test_automated_security.py**: Automated security scanning and vulnerability assessment
- **test_input_validation.py**: Input validation against common attack vectors (SQL injection, XSS, etc.)

### End-to-End Tests
Test complete workflows from start to finish.

- **TC-01/test_malicious.py**: Complete malicious ransomware alert handling workflow
- **TC-02/test_benign.py**: Complete benign alert (false positive) handling workflow
- **TC-03/test_edge_cases.py**: Edge cases, boundary conditions, and error scenarios

## Running Tests

### Quick Start

```bash
# Run all tests
make test-all

# Run specific test categories
make test-unit
make test-integration
make test-e2e

# Run with coverage
make test-coverage
```

### Individual Test Execution

```bash
# Run unit tests
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run E2E tests
python -m pytest tests/e2e/ -v

# Run specific test file
python -m pytest tests/unit/test_calc_kpis.py -v

# Run with coverage
python -m pytest tests/ --cov=scripts --cov-report=html --cov-report=term
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

- **Unit tests**: >90% coverage
- **Integration tests**: >80% coverage
- **Overall**: >85% coverage

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
docker-compose -f docker/docker-compose.test.yml up --build --abort-on-container-exit
```

## Test Results and Reports

### Result Files
- Test results: `results/test_results.json`
- Coverage reports: `htmlcov/`
- Performance reports: `results/performance/`
- Security reports: `results/security/`

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

For more information about the SOAR Ransomware Lab project, see the main [README.md](../README.md) and [project documentation](../docs/).
