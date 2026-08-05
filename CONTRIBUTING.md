# Contributing to SOAR Ransomware Lab

> Thank you for your interest in contributing to the SOAR Ransomware Lab project! This document provides guidelines and
> information for contributors.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Code Standards](#code-standards)
4. [Herramientas de calidad y CI](#herramientas-de-calidad-y-ci)
5. [Testing](#testing)
6. [Seguridad y gestión de secretos](#seguridad-y-gesti%C3%B3n-de-secretos)
7. [Submitting Changes](#submitting-changes)
8. [Review Process](#review-process)
9. [Community Guidelines](#community-guidelines)

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
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

1. Copy the environment template to the canonical file `.env.full`:
   ```bash
   cp .env.example .env.full
   ```

2. Generate secure secrets and append them to `.env.full`:
   ```bash
   make generate-secrets >> .env.full
   # o desde el entorno Python:
   soar-lab generate-secrets --env >> .env.full
   ```

3. Add a strong JWT secret manually (`generate-secrets` does not emit it):
   ```bash
   # Linux/macOS/PowerShell:
   echo "JWT_SECRET_KEY=$(openssl rand -base64 64 | tr -d '\n')" >> .env.full
   ```

4. Validate the environment file:
   ```bash
   make validate-credentials
   ```

5. (Opcional) Install pre-commit hooks:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

6. Start the development environment:
   ```bash
   make up
   ```

7. Install Python dependencies from `pyproject.toml`:
   ```bash
   make deps       # pip install -e .
   make deps-test  # pip install -e ".[test]"
   ```

8. Build and preview documentation locally (Docusaurus):
   ```bash
   make docs-build
   make docs-serve
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
- Maximum line length: 100 characters (matches `pyproject.toml`)
- Use isort for import sorting
- Use type hints where appropriate
- Follow Google-style docstrings
- Respect the hexagonal architecture under `src/soar_lab/`: `domain/`, `application/`, `infrastructure/`, `interfaces/`
- Wire dependencies through the Composition Root (`src/soar_lab/interfaces/api/composition.py`)
- Keep domain code free of infrastructure imports

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
BACKUP_DIR="${BACKUP_DIR:-./artifacts/backups}"

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

## Herramientas de calidad y CI

El proyecto usa **Python 3.11+**. Las herramientas y versiones se declaran en `pyproject.toml` y se ejecutan en `.github/workflows/ci.yml`:

- **Black** (`>=23.0.0`, `line-length = 100`, `target-version = ['py311']`)
- **isort** (`>=5.12.0`, perfil `black`, longitud 100)
- **flake8** (`>=6.0.0`; en CI se ejecutan dos pasos: `E9,F63,F7,F82` y `max-line-length=100`)
- **mypy** (`>=1.0.0`, `python_version = "3.11"`, `warn_return_any`, `warn_unused_configs`)
- **pytest** (`>=7.0.0`, con `pytest-asyncio`, `pytest-cov`, `pytest-mock`, `pytest-timeout`)
- **pre-commit** (`>=3.0.0`)

Para ejecutar localmente las comprobaciones equivalentes a CI:

```bash
# Instalar entorno de desarrollo
pip install -e ".[dev]"

# Formateo y ordenación de imports
black src/soar_lab
isort src/soar_lab

# Lint (dos pasos como en CI)
flake8 src/soar_lab --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 src/soar_lab --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics

# Comprobación de tipos
mypy src/soar_lab --ignore-missing-imports

# Tests unitarios con cobertura
pytest tests/unit/ -v --cov=src.soar_lab --cov-report=xml
```

> **Nota**: `make lint` y `make test-all` en los Makefiles ejecutan estos pasos de forma agrupada según la plataforma.

---

## Testing

### Estructura de tests

```
tests/
├── unit/          # Tests unitarios (sin dependencias externas)
├── integration/   # Tests de integración
├── e2e/           # Tests end-to-end (workflows completos)
├── atomic/        # Validaciones rápidas
├── smoke/         # Tests post-despliegue
├── performance/   # Benchmarks y KPIs
├── security/      # Tests de seguridad
└── general/       # Tests transversales
```

> Los conteos exactos varían con el código. Para obtener el número real de casos recogidos usar:
> ```bash
> python -m pytest tests/ --collect-only -q
> ```

### Writing Tests

#### Unit Tests

```python
import pytest
from unittest.mock import Mock, patch
from src.soar_lab.simulator.simulate_alerts import SIEMSimulator

class TestSIEMSimulator:
    """Test cases for SIEMSimulator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.webhook_url = "http://localhost:15001/api/v1/hooks/<workflow_id>"
        self.api_token = "<test-token>"
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

### Configuración de pre-commit

El archivo `.pre-commit-config.yaml` del repositorio ejecuta automáticamente
Black, isort, flake8, markdownlint, detect-secrets y el comprobador de
terminología propio (`src/soar_lab/scripts/ci/terminology_check.py`):

Ver el archivo `.pre-commit-config.yaml` del repositorio para la configuración exacta. Resumen de los hooks activos:

- `pre-commit-hooks`: elimina espacios finales, valida YAML/JSON y ficheros grandes.
- `black` (`python3.11`, `--line-length 100`).
- `isort` (`--profile black`).
- `flake8` (`--max-line-length=100`, `--extend-ignore=E203,W503`).
- `detect-secrets` con baseline `.secrets.baseline`.
- `markdownlint-cli` con configuración `.markdownlint.json`.
- Hook local `terminology-check` ejecutando `python src/soar_lab/scripts/ci/terminology_check.py`.

> Asegúrate de que `python3.11` esté disponible para Black y de que los
> archivos Markdown no contengan términos legacy tras el `terminology-check`.

---

## Seguridad y gestión de secretos

### Credenciales y API keys

- **Nunca incluir valores reales** de credenciales, API keys, JWT tokens, contraseñas, workflow IDs, trigger IDs u org IDs en documentación, commits, capturas de pantalla ni scripts versionados.
- Usar **placeholders inequívocos** del estilo `<JWT_SECRET_KEY>`, `<THEHIVE_API_KEY>`, `<SHUFFLE_DEFAULT_APIKEY>`, `<...>`.
- Las credenciales operativas se almacenan únicamente en `.env.full` (ignorado por Git) y se generan mediante:
  ```bash
  make generate-secrets >> .env.full
  # o
  soar-lab generate-secrets --env >> .env.full
  ```
- Las variables canónicas para JWT son:
  - `JWT_SECRET_KEY` (clave primaria, `>= 32` caracteres; `generate-secrets` produce 64 caracteres alfanuméricos).
  - `API_AUTH_SECRET` (compatibilidad legacy; `AuthService` y `Settings` lo usan como fallback).
  - `JWT_EXPIRATION_MINUTES` (por defecto `60`).
  - `JWT_ALGORITHM` (`HS256`).

### Prevención de fugas en commits

- `detect-secrets` (hook de `pre-commit` y workflow de CI) escanea cambios en busca de secretos conocidos usando `.secrets.baseline`.
- `docs_quality.py` (`src/soar_lab/scripts/ci/docs_quality.py`) verifica que la documentación no incluya patrones prohibidos como `SiemToken` ni URLs/credenciales obsoletas.
- Si `detect-secrets` o `docs_quality.py` bloquean un cambio, auditar el historial del repositorio y **rotar cualquier valor expuesto**; no basta con corregir el archivo actual.

### Referencias

- `docs/architecture/security.md` — matriz de controles y estado de implementación.
- `.pre-commit-config.yaml` — hooks activos, incluido `detect-secrets`.
- `.github/workflows/ci.yml` — validación de secretos y documentación en CI.

---

## Troubleshooting

### Common Issues

#### Docker Issues

```bash
# Clean up Docker resources
docker system prune -a

# Rebuild containers
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

#### Python Issues

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .
pip install -e .[test]
```

#### Test Issues

```bash
# Clear pytest cache
pytest --cache-clear

# Run specific test with verbose output
pytest tests/unit/test_file.py::TestClass::test_method -vvs
```

### Getting Help

1. Check the [troubleshooting guide](docs/operations/troubleshooting.md)
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
