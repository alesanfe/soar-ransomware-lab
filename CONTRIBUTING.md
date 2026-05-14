# Contributing to SOAR Ransomware Lab

> Thank you for your interest in contributing to the SOAR Ransomware Lab project! This document provides guidelines and information for contributors.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Standards](#code-standards)
4. [Testing](#testing)
5. [Submitting Changes](#submitting-changes)
6. [Review Process](#review-process)
7. [Community Guidelines](#community-guidelines)

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Git
- Make (optional but recommended)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/soar-ransomware-lab.git
   cd soar-ransomware-lab
   ```

3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/original-org/soar-ransomware-lab.git
   ```

### Create a Branch

```bash
git checkout -b feature/your-feature-name
```

---

## Development Setup

### Environment Setup

1. Copy the environment file:
   ```bash
   cp docker/.env.example docker/.env
   ```

2. Generate secure secrets:
   ```bash
   make generate-secrets
   ```

3. Start the development environment:
   ```bash
   make up
   ```

4. Install Python dependencies:
   ```bash
   make deps
   make deps-test
   ```

### Development Workflow

1. Make your changes
2. Run tests: `make test-all`
3. Check code quality: `make lint`
4. Verify functionality

### IDE Configuration

#### VS Code

Install these extensions:
- Python
- Docker
- ShellCheck
- Pylance

Configure settings in `.vscode/settings.json`:
```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

#### PyCharm

- Enable code inspection
- Configure Black as formatter
- Set up Docker integration
- Configure test runner

---

## Code Standards

### Python Code

#### Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with additional guidelines:

- Use Black for formatting
- Maximum line length: 88 characters
- Use type hints where appropriate
- Follow Google-style docstrings

#### Example

```python
#!/usr/bin/env python3
"""
Module description.

This module provides functionality for...
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class ExampleClass:
    """Example class demonstrating coding standards.
    
    Attributes:
        attr1: Description of attribute 1
        attr2: Description of attribute 2
    """
    
    def __init__(self, attr1: str, attr2: Optional[int] = None) -> None:
        """Initialize ExampleClass.
        
        Args:
            attr1: Description of attr1
            attr2: Optional description of attr2
        """
        self.attr1 = attr1
        self.attr2 = attr2
    
    def process_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process the input data.
        
        Args:
            data: List of dictionaries to process
            
        Returns:
            Processed data dictionary
            
        Raises:
            ValueError: If data is empty
        """
        if not data:
            raise ValueError("Data cannot be empty")
        
        # Implementation here
        return {"processed": True, "count": len(data)}
```

#### Type Hints

All functions should include type hints:

```python
def calculate_kpis(alerts: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate KPIs from alert data."""
    pass
```

#### Error Handling

Use specific exception types:

```python
try:
    result = process_data(data)
except ValueError as e:
    logger.error(f"Invalid data: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### Bash Scripts

#### Style Guide

- Use ShellCheck for validation
- Follow Google Shell Style Guide
- Use `set -euo pipefail`
- Quote variables properly

#### Example

```bash
#!/bin/bash

# SOAR Ransomware Lab - Example Script
# Description of script purpose

set -euo pipefail

# Configuration
LOG_FILE="${LOG_FILE:-./logs/example.log}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Main function
main() {
    log "Starting example script"
    
    # Implementation here
    
    log "Script completed successfully"
}

# Run main function
main "$@"
```

### Documentation

#### Docstrings

Use Google-style docstrings:

```python
def send_alert(alert_data: Dict[str, Any]) -> bool:
    """Send alert to SOAR platform.
    
    This function sends a ransomware detection alert to the configured
    SOAR platform webhook endpoint.
    
    Args:
        alert_data: Dictionary containing alert information including
            alert_id, hostname, src_ip, hash, severity, and other fields.
        
    Returns:
        True if alert was sent successfully, False otherwise.
        
    Raises:
        ConnectionError: If unable to connect to the webhook endpoint
        ValidationError: If alert data is invalid
        
    Example:
        >>> alert = {
        ...     "alert_id": "ALERT-1234567890-0001",
        ...     "hostname": "WIN-001",
        ...     "src_ip": "192.168.1.100",
        ...     "hash": {"sha256": "44d88612fea8a8f36de82e1278abb02f44d88612fea8a8f36de82e1278abb02f"},
        ...     "severity": "2",
        ...     "source": "siem",
        ...     "detection_time": "2024-05-03T12:34:56Z",
        ...     "event_type": "ransomware_detection",
        ...     "description": "Test alert"
        ... }
        >>> send_alert(alert)
        True
    """
    pass
```

#### Comments

- Use comments to explain complex logic
- Avoid obvious comments
- Use TODO/FIXME/HACK markers appropriately

```python
# Calculate MTTR using weighted average
# Example: Use markers for future improvements
mttr = sum(execution_times) / len(execution_times)
```

---

## Testing

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
├── performance/   # Performance tests
└── security/      # Security tests
```

### Writing Tests

#### Unit Tests

```python
import pytest
from unittest.mock import Mock, patch
from scripts.send_alert import SIEMSimulator

class TestSIEMSimulator:
    """Test cases for SIEMSimulator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.webhook_url = "http://localhost:5001/webhook"
        self.api_token = "test-token"
        self.simulator = SIEMSimulator(self.webhook_url, self.api_token)
    
    def test_generate_alert_malicious(self):
        """Test malicious alert generation."""
        alert = self.simulator.generate_alert(alert_type='malicious')
        
        assert alert['severity'] in [2, 3]
        assert alert['event_type'] == 'ransomware_detection'
        assert 'malicious' in alert['source']
    
    @patch('requests.post')
    def test_send_alert_success(self, mock_post):
        """Test successful alert sending."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        alert = self.simulator.generate_alert()
        result = self.simulator.send_alert(alert)
        
        assert result is True
        mock_post.assert_called_once()
```

#### Integration Tests

```python
import pytest
import requests
from config.settings import get_setting

class TestAPIIntegration:
    """Integration tests for API endpoints."""
    
    def test_webhook_endpoint(self):
        """Test webhook endpoint integration."""
        webhook_url = get_setting('webhook_url')
        api_token = get_setting('siem_webhook_token')
        
        alert_data = {
            "alert": {
                "alert_id": "ALERT-TEST-0001",
                "hostname": "TEST-001",
                "src_ip": "192.168.1.1",
                "hash": {"sha256": "44d88612fea8a8f36de82e1278abb02f44d88612fea8a8f36de82e1278abb02f"},
                "severity": "2",
                "source": "test",
                "detection_time": "2024-05-03T12:34:56Z",
                "event_type": "ransomware_detection",
                "description": "Test alert"
            },
            "timestamp": "2024-05-03T12:34:56Z",
            "version": "1.0"
        }
        
        response = requests.post(
            webhook_url,
            json=alert_data,
            headers={"Authorization": f"Bearer {api_token}"}
        )
        
        assert response.status_code == 200
```

### Running Tests

```bash
# Run all tests
make test-all

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/unit/test_send_alert.py -v

# Run with markers
pytest -m "unit" -v
pytest -m "integration" -v
```

### Test Coverage

- Maintain minimum 80% code coverage
- Focus on critical paths and edge cases
- Use coverage reports to identify gaps

---

## Submitting Changes

### Commit Guidelines

#### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance

#### Examples

```bash
feat(api): add webhook rate limiting
fix(security): validate input parameters
docs(readme): update installation instructions
test(unit): add alert validation tests
refactor(config): centralize configuration management
```

### Pull Request Process

1. **Update Documentation**
   - Update README if needed
   - Add/update API documentation
   - Update CHANGELOG

2. **Create Pull Request**
   - Use descriptive title
   - Fill out PR template
   - Link relevant issues

3. **Requirements**
   - All tests pass
   - Code coverage maintained
   - Documentation updated
   - No breaking changes without discussion

#### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG updated
```

---

## Review Process

### Code Review Guidelines

#### Reviewers Should Check

- **Functionality**: Does the code work as intended?
- **Security**: Are there any security implications?
- **Performance**: Will this affect performance?
- **Maintainability**: Is the code readable and maintainable?
- **Tests**: Are tests comprehensive and appropriate?

#### Review Process

1. Automated checks run first
2. At least one human reviewer required
3. Address all review comments
4. Update PR as needed
5. Get final approval

### Merge Requirements

- All automated checks pass
- At least one approval
- No merge conflicts
- Documentation updated

---

## Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please:

- Be respectful and constructive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and discussions
- **Discord/Slack**: Real-time chat (if available)

### Getting Help

- Check existing issues and documentation first
- Search for similar questions
- Provide clear, detailed information when asking for help
- Be patient and respectful

---

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH`
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes (backward compatible)

### Release Checklist

1. **Code Quality**
   - [ ] All tests pass
   - [ ] Coverage requirements met
   - [ ] No critical security issues

2. **Documentation**
   - [ ] API documentation updated
   - [ ] User guide updated
   - [ ] CHANGELOG updated

3. **Testing**
   - [ ] Manual testing completed
   - [ ] Integration tests verified
   - [ ] Performance tests passed

4. **Release**
   - [ ] Version bumped
   - [ ] Tag created
   - [ ] Release notes published
   - [ ] Deployment tested

---

## Development Tools

### Required Tools

- **Python**: Black, isort, mypy, flake8
- **Shell**: ShellCheck
- **Docker**: Docker Compose
- **Git**: Pre-commit hooks

### Pre-commit Setup

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

### Pre-commit Configuration

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.942
    hooks:
      - id: mypy

  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.8.0.4
    hooks:
      - id: shellcheck
```

---

## Troubleshooting

### Common Issues

#### Docker Issues

```bash
# Clean up Docker resources
docker system prune -a

# Rebuild containers
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

#### Python Issues

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

#### Test Issues

```bash
# Clear pytest cache
pytest --cache-clear

# Run specific test with verbose output
pytest tests/unit/test_file.py::TestClass::test_method -vvs
```

### Getting Help

1. Check the [troubleshooting guide](docs/troubleshooting.md)
2. Search existing GitHub issues
3. Create a new issue with:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details

---

## Recognition

### Contributors

All contributors are recognized in:
- README.md contributors section
- Release notes
- Annual contributor report

### Ways to Contribute

- Code contributions
- Documentation improvements
- Bug reports and feature requests
- Community support
- Testing and feedback

---

Thank you for contributing to SOAR Ransomware Lab! Your contributions help make this project better for everyone.
