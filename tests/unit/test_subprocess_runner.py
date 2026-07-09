"""Unit tests for infrastructure.subprocess_runner module."""

import pytest
from unittest.mock import Mock, patch

from soar_lab.infrastructure.subprocess_runner import SubprocessResult, SubprocessRunner


class TestSubprocessResult:
    """Tests for SubprocessResult class."""

    def test_subprocess_result_to_dict(self):
        """Test SubprocessResult.to_dict method."""
        result = SubprocessResult(
            success=True,
            returncode=0,
            stdout="test output",
            stderr="test error",
            duration=1.5
        )
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["returncode"] == 0
        assert result_dict["stdout"] == "test output"
        assert result_dict["stderr"] == "test error"
        assert result_dict["duration"] == 1.5


class TestSubprocessRunner:
    """Tests for SubprocessRunner class."""

    def test_subprocess_runner_init(self):
        """Test SubprocessRunner initialization."""
        runner = SubprocessRunner(cwd="/tmp", default_timeout=60)
        
        assert runner.cwd == "/tmp"
        assert runner.default_timeout == 60
