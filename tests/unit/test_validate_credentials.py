#!/usr/bin/env python3
"""
Unit tests for validate_credentials module
"""

import os
import pytest
import sys
import tempfile
from pathlib import Path

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.infrastructure.validate_credentials import (
    parse_env_file,
    extract_defaults_from_docker_compose,
    extract_defaults_from_python,
    extract_hardcoded_values,
    validate_credentials
)


class TestParseEnvFile:
    """Tests for parse_env_file function."""

    def test_parse_env_file_valid(self):
        """Test parsing a valid .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("# Comment\n")
            f.write("VAR1=value1\n")
            f.write("VAR2=value2\n")
            f.write("VAR3=value with spaces\n")
            f.flush()
            env_path = Path(f.name)

        try:
            result = parse_env_file(env_path)

            assert result == {
                'VAR1': 'value1',
                'VAR2': 'value2',
                'VAR3': 'value with spaces'
            }
        finally:
            os.unlink(env_path)

    def test_parse_env_file_not_found(self):
        """Test parsing a non-existent file."""
        env_path = Path("/nonexistent/path/.env")
        result = parse_env_file(env_path)

        assert result == {}

    def test_parse_env_file_empty(self):
        """Test parsing an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("")
            f.flush()
            env_path = Path(f.name)

        try:
            result = parse_env_file(env_path)

            assert result == {}
        finally:
            os.unlink(env_path)

    def test_parse_env_file_comments_only(self):
        """Test parsing a file with only comments."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("# Comment 1\n")
            f.write("# Comment 2\n")
            f.flush()
            env_path = Path(f.name)

        try:
            result = parse_env_file(env_path)

            assert result == {}
        finally:
            os.unlink(env_path)


class TestExtractDefaultsFromDockerCompose:
    """Tests for extract_defaults_from_docker_compose function."""

    def test_extract_defaults_valid(self):
        """Test extracting defaults from docker-compose file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("services:\n")
            f.write("  app:\n")
            f.write("    environment:\n")
            f.write("      - VAR1=${VAR1:-default1}\n")
            f.write("      - VAR2=${VAR2:-default2}\n")
            f.flush()
            compose_path = Path(f.name)

        try:
            result = extract_defaults_from_docker_compose(compose_path)

            assert result == {
                'VAR1': 'default1',
                'VAR2': 'default2'
            }
        finally:
            os.unlink(compose_path)

    def test_extract_defaults_not_found(self):
        """Test extracting from non-existent file."""
        compose_path = Path("/nonexistent/docker-compose.yml")
        result = extract_defaults_from_docker_compose(compose_path)

        assert result == {}

    def test_extract_defaults_no_matches(self):
        """Test extracting from file with no matches."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("services:\n")
            f.write("  app:\n")
            f.write("    environment:\n")
            f.write("      - VAR1=value1\n")
            f.flush()
            compose_path = Path(f.name)

        try:
            result = extract_defaults_from_docker_compose(compose_path)

            assert result == {}
        finally:
            os.unlink(compose_path)


class TestExtractDefaultsFromPython:
    """Tests for extract_defaults_from_python function."""

    def test_extract_defaults_valid(self):
        """Test extracting defaults from Python script."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("import os\n")
            f.write("VAR1 = os.environ.get('VAR1', 'default1')\n")
            f.write("VAR2 = os.environ.get(\"VAR2\", \"default2\")\n")
            f.flush()
            script_path = Path(f.name)

        try:
            result = extract_defaults_from_python(script_path)

            assert result == {
                'VAR1': 'default1',
                'VAR2': 'default2'
            }
        finally:
            os.unlink(script_path)

    def test_extract_defaults_not_found(self):
        """Test extracting from non-existent file."""
        script_path = Path("/nonexistent/script.py")
        result = extract_defaults_from_python(script_path)

        assert result == {}

    def test_extract_defaults_no_matches(self):
        """Test extracting from file with no matches."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("import os\n")
            f.write("VAR1 = 'value1'\n")
            f.flush()
            script_path = Path(f.name)

        try:
            result = extract_defaults_from_python(script_path)

            assert result == {}
        finally:
            os.unlink(script_path)


class TestExtractHardcodedValues:
    """Tests for extract_hardcoded_values function."""

    def test_extract_hardcoded_values_valid(self):
        """Test extracting hardcoded values with patterns."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write('{"key1": "value1"}\n')
            f.write('{"key2": "value2"}\n')
            f.flush()
            file_path = Path(f.name)

        try:
            patterns = [r'"([^"]+)":\s*"([^"]+)"']
            result = extract_hardcoded_values(file_path, patterns)

            assert 'key1' in result
            assert 'key2' in result
        finally:
            os.unlink(file_path)

    def test_extract_hardcoded_values_not_found(self):
        """Test extracting from non-existent file."""
        file_path = Path("/nonexistent/config.conf")
        patterns = [r'"([^"]+)":\s*"([^"]+)"']
        result = extract_hardcoded_values(file_path, patterns)

        assert result == {}

    def test_extract_hardcoded_values_no_matches(self):
        """Test extracting from file with no matches."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write("key1=value1\n")
            f.write("key2=value2\n")
            f.flush()
            file_path = Path(f.name)

        try:
            patterns = [r'"([^"]+)":\s*"([^"]+)"']
            result = extract_hardcoded_values(file_path, patterns)

            assert result == {}
        finally:
            os.unlink(file_path)

    def test_extract_hardcoded_values_non_tuple_match(self):
        """Test extracting hardcoded values with non-tuple match pattern."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as f:
            f.write('key1=value1\n')
            f.write('key2=value2\n')
            f.flush()
            file_path = Path(f.name)

        try:
            patterns = [r'(\w+)=(\w+)']
            result = extract_hardcoded_values(file_path, patterns)

            assert 'key1' in result
            assert 'key2' in result
        finally:
            os.unlink(file_path)


class TestValidateCredentials:
    """Tests for validate_credentials function."""

    @pytest.fixture
    def mock_repo_structure(self, tmp_path):
        """Create a mock repo structure for testing."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        infra = repo_root / "infra" / "docker" / "compose"
        infra.mkdir(parents=True)
        src = repo_root / "src" / "soar_lab" / "infrastructure"
        src.mkdir(parents=True)
        return repo_root

    def test_validate_credentials_missing_env_file(self, mock_repo_structure):
        """Test validate_credentials when .env.full is missing."""
        from unittest.mock import patch

        with patch('soar_lab.infrastructure.validate_credentials.Path') as mock_path:
            mock_path.return_value.parent.parent.parent.parent = mock_repo_structure
            result = validate_credentials()
            assert result is False

    def test_validate_credentials_success(self, mock_repo_structure):
        """Test validate_credentials with synchronized credentials."""
        from unittest.mock import patch

        # Create .env.full
        env_full = mock_repo_structure / ".env.full"
        env_full.write_text("ELASTIC_PASSWORD=testpass\nTHEHIVE_SECRET=testsecret\n")

        # Create docker-compose file with matching defaults
        compose_file = mock_repo_structure / "infra" / "docker" / "compose" / "docker-compose.core.yml"
        compose_file.write_text(
            "services:\n  app:\n    environment:\n      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD:-testpass}\n")

        with patch('soar_lab.infrastructure.validate_credentials.Path') as mock_path:
            mock_path.return_value.parent.parent.parent.parent = mock_repo_structure
            result = validate_credentials()
            assert result is True

    def test_validate_credentials_mismatch(self, mock_repo_structure):
        """Test validate_credentials with mismatched credentials."""
        from unittest.mock import patch

        # Create .env.full
        env_full = mock_repo_structure / ".env.full"
        env_full.write_text("ELASTIC_PASSWORD=testpass\nTHEHIVE_SECRET=testsecret\n")

        # Create docker-compose file with different defaults
        compose_file = mock_repo_structure / "infra" / "docker" / "compose" / "docker-compose.core.yml"
        compose_file.write_text(
            "services:\n  app:\n    environment:\n      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD:-differentpass}\n")

        with patch('soar_lab.infrastructure.validate_credentials.Path') as mock_path:
            mock_path.return_value.parent.parent.parent.parent = mock_repo_structure
            result = validate_credentials()
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
