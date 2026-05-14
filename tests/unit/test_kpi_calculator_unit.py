#!/usr/bin/env python3
"""
Simple unit tests for KPI Calculator
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from soar_lab.data.calc_kpis import validate_log_file, parse_log_file


class TestKPICalculator(unittest.TestCase):
    """Test KPI Calculator functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_log_content = """[2023-12-01 10:00:00] STEP: alert_received
[2023-12-01 10:01:00] STEP: alert_analysis
[2023-12-01 10:02:00] STEP: alert_triage
[2023-12-01 10:03:00] STEP: containment_initiated
[2023-12-01 10:04:00] STEP: containment_completed
[2023-12-01 10:05:00] STEP: eradication_initiated
[2023-12-01 10:06:00] STEP: eradication_completed
[2023-12-01 10:07:00] STEP: recovery_initiated
[2023-12-01 10:08:00] STEP: recovery_completed
Invalid line without timestamp
[2023-12-01 10:09:00] STEP: post_incident_review"""

    def test_validate_log_file_with_valid_file(self):
        """Test validate_log_file with a valid file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(self.test_log_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = validate_log_file(tmp_path)
            self.assertEqual(result, tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_validate_log_file_with_string_path(self):
        """Test validate_log_file with string path"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(self.test_log_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = validate_log_file(str(tmp_path))
            self.assertIsInstance(result, Path)
            self.assertEqual(result, tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_validate_log_file_none_input(self):
        """Test validate_log_file with None input"""
        # This should try to use the default LOG_PATH
        with patch('soar_lab.data.calc_kpis.LOG_PATH') as mock_log_path:
            mock_log_path.exists.return_value = True
            mock_log_path.is_file.return_value = True
            
            # Mock the file reading
            with patch('builtins.open', unittest.mock.mock_open()):
                result = validate_log_file(None)
                self.assertEqual(result, mock_log_path)

    def test_validate_log_file_nonexistent(self):
        """Test validate_log_file with non-existent file"""
        nonexistent_path = Path('/non/existent/file.log')
        
        with self.assertRaises(FileNotFoundError):
            validate_log_file(nonexistent_path)

    def test_validate_log_file_directory(self):
        """Test validate_log_file with directory path"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            dir_path = Path(tmp_dir)
            
            with self.assertRaises(ValueError):
                validate_log_file(dir_path)

    def test_validate_log_file_permission_error(self):
        """Test validate_log_file with permission error"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(self.test_log_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                with self.assertRaises(PermissionError):
                    validate_log_file(tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_parse_log_file_valid_content(self):
        """Test parse_log_file with valid content"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(self.test_log_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = parse_log_file(tmp_path)
            
            # Check structure
            self.assertIsInstance(result, dict)
            
            # Check that steps were parsed correctly
            expected_steps = [
                'alert_received', 'alert_analysis', 'alert_triage',
                'containment_initiated', 'containment_completed',
                'eradication_initiated', 'eradication_completed',
                'recovery_initiated', 'recovery_completed',
                'post_incident_review'
            ]
            
            for step in expected_steps:
                self.assertIn(step, result)
                self.assertEqual(len(result[step]), 1)
            
            # Check that invalid line was ignored
            self.assertNotIn('Invalid line without timestamp', result)
            
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_parse_log_file_empty_file(self):
        """Test parse_log_file with empty file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            result = parse_log_file(tmp_path)
            self.assertEqual(result, {})
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_parse_log_file_invalid_timestamp(self):
        """Test parse_log_file with invalid timestamp format"""
        invalid_content = """[2023-12-01 10:00:00] STEP: valid_step
[invalid-timestamp] STEP: invalid_step
[2023-12-01 10:01:00] STEP: another_valid_step"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(invalid_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = parse_log_file(tmp_path)
            
            # Should have valid steps but not invalid one
            self.assertIn('valid_step', result)
            self.assertIn('another_valid_step', result)
            self.assertNotIn('invalid_step', result)
            
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_parse_log_file_multiple_same_steps(self):
        """Test parse_log_file with multiple occurrences of same step"""
        multiple_content = """[2023-12-01 10:00:00] STEP: alert_received
[2023-12-01 10:01:00] STEP: alert_received
[2023-12-01 10:02:00] STEP: alert_received
[2023-12-01 10:03:00] STEP: other_step"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(multiple_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = parse_log_file(tmp_path)
            
            # Should have multiple timestamps for alert_received
            self.assertIn('alert_received', result)
            self.assertEqual(len(result['alert_received']), 3)
            self.assertIn('other_step', result)
            self.assertEqual(len(result['other_step']), 1)
            
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_parse_log_file_unicode_error(self):
        """Test parse_log_file with unicode decode error"""
        # Create a file with invalid unicode content
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(b'\xff\xfe Invalid unicode content')
            tmp_path = Path(tmp_file.name)
        
        try:
            with self.assertRaises(UnicodeDecodeError):
                parse_log_file(tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_parse_log_file_file_read_error(self):
        """Test parse_log_file with file read error"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(self.test_log_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            with patch('builtins.open', side_effect=IOError("Read error")):
                with self.assertRaises(IOError):
                    parse_log_file(tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_parse_log_file_step_regex_patterns(self):
        """Test parse_log_file with various step name patterns"""
        varied_content = """[2023-12-01 10:00:00] STEP: simple_step
[2023-12-01 10:01:00] STEP: step-with-dashes
[2023-12-01 10:02:00] STEP: step_with_underscores
[2023-12-01 10:03:00] STEP: step123withnumbers
[2023-12-01 10:04:00] STEP: STEP_IN_UPPERCASE"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(varied_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = parse_log_file(tmp_path)
            
            # All step names should be preserved as-is
            expected_steps = [
                'simple_step', 'step-with-dashes', 'step_with_underscores',
                'step123withnumbers', 'STEP_IN_UPPERCASE'
            ]
            
            for step in expected_steps:
                self.assertIn(step, result)
                self.assertEqual(len(result[step]), 1)
            
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_parse_log_file_different_timestamp_formats(self):
        """Test parse_log_file with different timestamp formats"""
        varied_timestamps = """[2023-12-01 10:00:00] STEP: valid_timestamp
[2023/12/01 10:01:00] STEP: invalid_format1
[12-01-2023 10:02:00] STEP: invalid_format2
[2023-12-01 10:03:00] STEP: another_valid"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(varied_timestamps)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = parse_log_file(tmp_path)
            
            # Should only parse valid timestamps
            self.assertIn('valid_timestamp', result)
            self.assertIn('another_valid', result)
            self.assertNotIn('invalid_format1', result)
            self.assertNotIn('invalid_format2', result)
            
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_parse_log_file_empty_lines(self):
        """Test parse_log_file with empty lines"""
        content_with_empty_lines = """[2023-12-01 10:00:00] STEP: step1

[2023-12-01 10:01:00] STEP: step2

[2023-12-01 10:02:00] STEP: step3

"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(content_with_empty_lines)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = parse_log_file(tmp_path)
            
            # Should parse all valid steps and ignore empty lines
            self.assertIn('step1', result)
            self.assertIn('step2', result)
            self.assertIn('step3', result)
            self.assertEqual(len(result), 3)
            
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_parse_log_file_whitespace_handling(self):
        """Test parse_log_file with various whitespace"""
        whitespace_content = """[2023-12-01 10:00:00] STEP: step1
   [2023-12-01 10:01:00] STEP: step2
[2023-12-01 10:02:00] STEP:    step3   
[2023-12-01 10:03:00] STEP: 	step4	"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
            tmp_file.write(whitespace_content)
            tmp_path = Path(tmp_file.name)
        
        try:
            result = parse_log_file(tmp_path)
            
            # Should handle whitespace properly (whitespace is preserved in step names)
            self.assertIn('step1', result)
            self.assertIn('step2', result)
            self.assertIn('   step3', result)  # Whitespace preserved
            self.assertIn('\tstep4', result)    # Tab preserved
            
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == '__main__':
    unittest.main()
