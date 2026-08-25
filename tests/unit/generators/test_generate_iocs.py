#!/usr/bin/env python3
"""Unit tests for generate_iocs module."""

import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from soar_lab.data.generate_iocs import IOCPackageGenerator


class TestIOCPackageGenerator:
    """Tests for IOCPackageGenerator class."""

    def test_init_with_valid_dependencies(self):
        """Test initialization with valid dependencies."""
        mock_ioc_generator = Mock()
        mock_file_system = Mock()

        generator = IOCPackageGenerator(mock_ioc_generator, mock_file_system)

        assert generator.ioc_generator == mock_ioc_generator
        assert generator.file_system == mock_file_system

    def test_init_without_ioc_generator(self):
        """Test initialization without ioc_generator raises ValueError."""
        mock_file_system = Mock()

        with pytest.raises(ValueError, match="ioc_generator is required"):
            IOCPackageGenerator(None, mock_file_system)

    def test_init_without_file_system(self):
        """Test initialization without file_system raises ValueError."""
        mock_ioc_generator = Mock()

        with pytest.raises(ValueError, match="file_system is required"):
            IOCPackageGenerator(mock_ioc_generator, None)

    def test_create_ioc_package_without_output_file(self):
        """Test creating IOC package without writing to file."""
        mock_ioc_generator = Mock()
        mock_ioc_generator.create_ioc_package.return_value = {
            "malicious": {"hashes": ["abc123"]},
            "benign": {"hashes": ["def456"]},
        }
        mock_file_system = Mock()

        generator = IOCPackageGenerator(mock_ioc_generator, mock_file_system)
        result = generator.create_ioc_package(output_file=None, count=5)

        assert result == {"malicious": {"hashes": ["abc123"]}, "benign": {"hashes": ["def456"]}}
        mock_ioc_generator.create_ioc_package.assert_called_once_with(5)
        mock_file_system.write_file.assert_not_called()

    def test_create_ioc_package_with_output_file(self):
        """Test creating IOC package and writing to file."""
        mock_ioc_generator = Mock()
        mock_ioc_generator.create_ioc_package.return_value = {
            "malicious": {"hashes": ["abc123"]},
            "benign": {"hashes": ["def456"]},
        }
        mock_file_system = Mock()

        generator = IOCPackageGenerator(mock_ioc_generator, mock_file_system)
        result = generator.create_ioc_package(output_file="/tmp/iocs.json", count=10)

        assert result == {"malicious": {"hashes": ["abc123"]}, "benign": {"hashes": ["def456"]}}
        mock_ioc_generator.create_ioc_package.assert_called_once_with(10)
        mock_file_system.write_file.assert_called_once()
        # Verify the JSON was serialized
        call_args = mock_file_system.write_file.call_args
        assert "/tmp/iocs.json" in str(call_args[0])
        written_content = call_args[0][1]
        assert json.loads(written_content) == result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
