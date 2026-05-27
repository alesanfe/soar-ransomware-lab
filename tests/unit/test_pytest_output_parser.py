#!/usr/bin/env python3
"""
Unit tests for pytest_output_parser.py
"""

import pytest

from soar_lab.infrastructure.pytest_output_parser import PytestOutputParser


class TestPytestOutputParser:
    """Test PytestOutputParser infrastructure adapter"""

    def test_parse_passed_tests(self):
        """Test parsing output with passed tests"""
        parser = PytestOutputParser()
        output = "10 passed in 2.5s"
        
        result = parser.parse(output)
        
        assert result['passed'] == 10
        assert result['failed'] == 0
        assert result['skipped'] == 0

    def test_parse_failed_tests(self):
        """Test parsing output with failed tests"""
        parser = PytestOutputParser()
        output = "5 passed, 2 failed in 3.0s"
        
        result = parser.parse(output)
        
        assert result['passed'] == 5
        assert result['failed'] == 2
        assert result['skipped'] == 0

    def test_parse_skipped_tests(self):
        """Test parsing output with skipped tests"""
        parser = PytestOutputParser()
        output = "5 passed, 1 skipped in 2.0s"
        
        result = parser.parse(output)
        
        assert result['passed'] == 5
        assert result['failed'] == 0
        assert result['skipped'] == 1

    def test_parse_all_results(self):
        """Test parsing output with all result types"""
        parser = PytestOutputParser()
        output = "5 passed, 2 failed, 1 skipped in 4.0s"
        
        result = parser.parse(output)
        
        assert result['passed'] == 5
        assert result['failed'] == 2
        assert result['skipped'] == 1

    def test_parse_with_coverage(self):
        """Test parsing output with coverage"""
        parser = PytestOutputParser()
        output = "10 passed in 2.5s\nTOTAL 100 50 50%"
        
        result = parser.parse(output)
        
        assert result['passed'] == 10
        assert result['coverage'] == 50.0

    def test_parse_empty_output(self):
        """Test parsing empty output"""
        parser = PytestOutputParser()
        output = ""
        
        result = parser.parse(output)
        
        assert result['passed'] == 0
        assert result['failed'] == 0
        assert result['skipped'] == 0
        assert result['coverage'] == 0.0

    def test_parse_no_test_results(self):
        """Test parsing output without test results"""
        parser = PytestOutputParser()
        output = "Some random log output"
        
        result = parser.parse(output)
        
        assert result['passed'] == 0
        assert result['failed'] == 0
        assert result['skipped'] == 0
