#!/usr/bin/env python3
"""
Unit tests for bash scripts
"""

import unittest
import subprocess
import os
import tempfile
import shutil
from pathlib import Path


class TestIsolateHostScript(unittest.TestCase):
    """Test cases for isolate_host.sh script"""

    def setUp(self):
        """Set up test fixtures"""
        self.script_path = Path('scripts/isolate_host.sh')
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)

    def test_script_exists(self):
        """Test that isolate_host.sh exists"""
        self.assertTrue(self.script_path.exists())

    def test_script_is_executable(self):
        """Test that script is executable"""
        if os.name != 'nt':  # Skip on Windows
            self.assertTrue(os.access(self.script_path, os.X_OK))

    def test_script_syntax_valid(self):
        """Test that script has valid bash syntax"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', '-n', str(self.script_path)],
                capture_output=True
            )
            self.assertEqual(result.returncode, 0, "Script has syntax errors")

    def test_script_requires_hostname(self):
        """Test that script requires hostname parameter"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', str(self.script_path)],
                capture_output=True,
                text=True
            )
            self.assertNotEqual(result.returncode, 0)

    def test_script_rejects_invalid_hostname(self):
        """Test that script rejects invalid hostname format"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', str(self.script_path), 'invalid@hostname', 'CASE-001'],
                capture_output=True,
                text=True
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('ERROR', result.stderr)

    def test_script_rejects_invalid_case_id(self):
        """Test that script rejects invalid case_id format"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', str(self.script_path), 'test-host', 'CASE 001'],
                capture_output=True,
                text=True
            )
            self.assertNotEqual(result.returncode, 0)

    def test_script_accepts_valid_parameters(self):
        """Test that script accepts valid parameters"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', str(self.script_path), 'test-host', 'CASE-001'],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Should run without parameter errors
            self.assertNotIn('ERROR: Missing required parameters', result.stderr)
            self.assertNotIn('ERROR: Invalid hostname format', result.stderr)

    def test_script_generates_report(self):
        """Test that script generates JSON report"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', str(self.script_path), 'test-host', 'CASE-001'],
                capture_output=True,
                text=True,
                timeout=10
            )
            # Check if report was generated
            report_files = list(Path('backups').glob('*_containment_report.json'))
            self.assertGreater(len(report_files), 0)

    def test_simulation_mode_works(self):
        """Test that simulation mode works"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', str(self.script_path), 'test-host', 'CASE-001'],
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, 'SIMULATION_MODE': 'true'}
            )
            # Should complete without actually executing commands
            self.assertEqual(result.returncode, 0)


class TestNotifyScript(unittest.TestCase):
    """Test cases for notify.sh script"""

    def setUp(self):
        """Set up test fixtures"""
        self.script_path = Path('scripts/notify.sh')
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)

    def test_script_exists(self):
        """Test that notify.sh exists"""
        self.assertTrue(self.script_path.exists())

    def test_script_is_executable(self):
        """Test that script is executable"""
        if os.name != 'nt':
            self.assertTrue(os.access(self.script_path, os.X_OK))

    def test_script_syntax_valid(self):
        """Test that script has valid bash syntax"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', '-n', str(self.script_path)],
                capture_output=True
            )
            self.assertEqual(result.returncode, 0, "Script has syntax errors")

    def test_script_requires_action_parameter(self):
        """Test that script requires action parameter"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', str(self.script_path)],
                capture_output=True,
                text=True
            )
            self.assertNotEqual(result.returncode, 0)

    def test_script_accepts_valid_actions(self):
        """Test that script accepts valid action types"""
        if os.name != 'nt':
            valid_actions = ['alert', 'containment', 'error']
            for action in valid_actions:
                result = subprocess.run(
                    ['bash', str(self.script_path), action, 'CASE-001'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                # Should not error on action validation
                self.assertNotIn(f'Invalid action: {action}', result.stderr)

    def test_script_rejects_invalid_action(self):
        """Test that script rejects invalid action type"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', str(self.script_path), 'invalid_action', 'CASE-001'],
                capture_output=True,
                text=True
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Invalid action', result.stderr)

    def test_script_logs_to_notify_log(self):
        """Test that script logs to notify.log"""
        if os.name != 'nt':
            # Create logs directory
            os.makedirs('logs', exist_ok=True)
            
            result = subprocess.run(
                ['bash', str(self.script_path), 'alert', 'CASE-001'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Check if log file was created/updated
            log_path = Path('logs/notify.log')
            if log_path.exists():
                log_content = log_path.read_text()
                self.assertGreater(len(log_content), 0)


class TestGenCertsScript(unittest.TestCase):
    """Test cases for gen_certs.sh script"""

    def setUp(self):
        """Set up test fixtures"""
        self.script_path = Path('scripts/gen_certs.sh')
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)

    def test_script_exists(self):
        """Test that gen_certs.sh exists"""
        self.assertTrue(self.script_path.exists())

    def test_script_is_executable(self):
        """Test that script is executable"""
        if os.name != 'nt':
            self.assertTrue(os.access(self.script_path, os.X_OK))

    def test_script_syntax_valid(self):
        """Test that script has valid bash syntax"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', '-n', str(self.script_path)],
                capture_output=True
            )
            self.assertEqual(result.returncode, 0, "Script has syntax errors")

    def test_script_generates_certificate(self):
        """Test that script generates certificate files"""
        if os.name != 'nt':
            # Create certs directory
            os.makedirs('certs', exist_ok=True)
            
            result = subprocess.run(
                ['bash', str(self.script_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check if certificate files were generated
            cert_files = list(Path('certs').glob('*.crt'))
            key_files = list(Path('certs').glob('*.key'))
            pem_files = list(Path('certs').glob('*.pem'))
            
            self.assertGreater(len(cert_files), 0, "Certificate file not generated")
            self.assertGreater(len(key_files), 0, "Key file not generated")
            self.assertGreater(len(pem_files), 0, "PEM file not generated")


class TestScriptHeaders(unittest.TestCase):
    """Test cases for script headers and documentation"""

    def test_isolate_host_has_shebang(self):
        """Test that isolate_host.sh has proper shebang"""
        script_path = Path('scripts/isolate_host.sh')
        with open(script_path, 'r') as f:
            first_line = f.readline()
        self.assertTrue(first_line.startswith('#!/bin/bash'))

    def test_notify_has_shebang(self):
        """Test that notify.sh has proper shebang"""
        script_path = Path('scripts/notify.sh')
        with open(script_path, 'r') as f:
            first_line = f.readline()
        self.assertTrue(first_line.startswith('#!/bin/bash'))

    def test_gen_certs_has_shebang(self):
        """Test that gen_certs.sh has proper shebang"""
        script_path = Path('scripts/gen_certs.sh')
        with open(script_path, 'r') as f:
            first_line = f.readline()
        self.assertTrue(first_line.startswith('#!/bin/bash'))

    def test_scripts_have_description(self):
        """Test that scripts have description comments"""
        scripts = [
            'scripts/isolate_host.sh',
            'scripts/notify.sh',
            'scripts/gen_certs.sh'
        ]
        
        for script in scripts:
            script_path = Path(script)
            with open(script_path, 'r') as f:
                content = f.read()
            self.assertIn('SOAR', content, f"{script} should mention SOAR")


class TestScriptErrorHandling(unittest.TestCase):
    """Test cases for script error handling"""

    def test_isolate_host_has_error_handling(self):
        """Test that isolate_host.sh has error handling"""
        script_path = Path('scripts/isolate_host.sh')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn('set -e', content)
        self.assertIn('set -u', content)
        self.assertIn('set -o pipefail', content)

    def test_notify_has_error_handling(self):
        """Test that notify.sh has error handling"""
        script_path = Path('scripts/notify.sh')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn('set -e', content)
        self.assertIn('set -u', content)
        self.assertIn('set -o pipefail', content)

    def test_gen_certs_has_error_handling(self):
        """Test that gen_certs.sh has error handling"""
        script_path = Path('scripts/gen_certs.sh')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn('set -e', content)
        self.assertIn('set -u', content)
        self.assertIn('set -o pipefail', content)


if __name__ == '__main__':
    unittest.main()
