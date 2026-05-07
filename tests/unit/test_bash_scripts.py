#!/usr/bin/env python3
"""
Unit tests for shell scripts headers and generic aspects
"""

import unittest
import os
from pathlib import Path


class TestScriptHeaders(unittest.TestCase):
    """Test cases for script headers (shebang, description)"""

    def setUp(self):
        self.scripts = [
            Path('scripts/isolate_host.sh'),
            Path('scripts/notify.sh'),
            Path('scripts/gen_certs.sh')
        ]

    def test_isolate_host_has_shebang(self):
        with open(Path('scripts/isolate_host.sh'), 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith('#!'))

    def test_notify_has_shebang(self):
        with open(Path('scripts/notify.sh'), 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith('#!'))

    def test_gen_certs_has_shebang(self):
        with open(Path('scripts/gen_certs.sh'), 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith('#!'))

    def test_scripts_have_description(self):
        for script in self.scripts:
            with open(script, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            # Look for a comment description in the first 10 lines
            lines = content.split('\n')[:10]
            has_description = any(len(line) > 5 and line.startswith('#') and not line.startswith('#!') for line in lines)
            self.assertTrue(has_description, f"Script {script} should have a description comment")


class TestScriptErrorHandling(unittest.TestCase):
    """Test cases for script error handling"""

    def test_isolate_host_has_error_handling(self):
        with open(Path('scripts/isolate_host.sh'), 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        self.assertIn('set -u', content)

    def test_notify_has_error_handling(self):
        with open(Path('scripts/notify.sh'), 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        self.assertIn('set -u', content)

    def test_gen_certs_has_error_handling(self):
        with open(Path('scripts/gen_certs.sh'), 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        self.assertIn('set -u', content)


if __name__ == '__main__':
    unittest.main()
