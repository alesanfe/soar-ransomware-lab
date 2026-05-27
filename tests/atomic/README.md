# Atomic Tests

This directory contains atomic test cases for individual component validation.

## Purpose

Atomic tests verify the functionality of specific components in isolation, without dependencies on other services. These
are useful for:

- Rapid development iteration
- Isolating root causes of failures
- Testing edge cases
- Validating individual service health

## Test Structure

Each atomic test should:

- Test a single component or feature
- Be independent of other tests
- Have clear pass/fail criteria
- Include cleanup procedures

## Running Tests

```bash
# Run all atomic tests
pytest tests/atomic/ -v

# Run a specific test
pytest tests/atomic/test_<component>.py -v

# Run with coverage
pytest tests/atomic/ --cov=src/soar_lab
```

## Test Categories

- **Component health** - Verify service health endpoints
- **Configuration** - Validate configuration loading
- **API endpoints** - Test individual API calls
- **Data operations** - Verify CRUD operations
