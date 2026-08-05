#!/usr/bin/env python3
"""
Unit tests for log_parser.py
"""

import pytest
from datetime import datetime, timezone

from soar_lab.infrastructure.log_parser import ExecutionLogParser


class TestExecutionLogParser:
    """Test ExecutionLogParser infrastructure adapter"""

    def test_parse_valid_log(self):
        """Test parsing valid log content"""
        parser = ExecutionLogParser()
        log_content = "[2024-01-01 10:00:00] STEP: Alert received\n[2024-01-01 10:00:05] STEP: Containment executed"

        result = parser.parse(log_content)

        assert 'Alert received' in result
        assert 'Containment executed' in result
        assert len(result['Alert received']) == 1
        assert len(result['Containment executed']) == 1
        assert result['Alert received'][0] == datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    def test_parse_empty_log(self):
        """Test parsing empty log content"""
        parser = ExecutionLogParser()
        log_content = ""

        result = parser.parse(log_content)

        assert result == {}

    def test_parse_log_with_empty_lines(self):
        """Test parsing log with empty lines"""
        parser = ExecutionLogParser()
        log_content = "\n\n[2024-01-01 10:00:00] STEP: Alert received\n\n"

        result = parser.parse(log_content)

        assert 'Alert received' in result
        assert len(result['Alert received']) == 1

    def test_parse_log_invalid_timestamp(self):
        """Test parsing log with invalid timestamp (should skip)"""
        parser = ExecutionLogParser()
        log_content = "[invalid-timestamp] STEP: Alert received\n[2024-01-01 10:00:00] STEP: Containment executed"

        result = parser.parse(log_content)

        assert 'Alert received' not in result  # Invalid timestamp skipped
        assert 'Containment executed' in result

    def test_parse_log_multiple_steps_same_name(self):
        """Test parsing log with multiple entries for same step"""
        parser = ExecutionLogParser()
        log_content = "[2024-01-01 10:00:00] STEP: Alert received\n[2024-01-01 10:01:00] STEP: Alert received"

        result = parser.parse(log_content)

        assert len(result['Alert received']) == 2

    def test_parse_log_no_step_format(self):
        """Test parsing log without STEP format (should skip)"""
        parser = ExecutionLogParser()
        log_content = "[2024-01-01 10:00:00] Some other log line"

        result = parser.parse(log_content)

        assert result == {}
