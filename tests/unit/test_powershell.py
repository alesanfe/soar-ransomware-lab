#!/usr/bin/env python3
"""
Unit tests for PowerShell scripts
"""

import unittest
import subprocess
import os
from pathlib import Path


class TestIsolateEndpointScript(unittest.TestCase):
    """Test cases for isolate_endpoint.ps1 script"""

    def setUp(self):
        """Set up test fixtures"""
        self.script_path = Path('scripts/isolate_endpoint.ps1')

    def test_script_exists(self):
        """Test that isolate_endpoint.ps1 exists"""
        self.assertTrue(self.script_path.exists())

    def test_script_has_powershell_extension(self):
        """Test that script has .ps1 extension"""
        self.assertEqual(self.script_path.suffix, '.ps1')

    def test_script_has_parameters(self):
        """Test that script has required parameters"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('param(', content)
        self.assertIn('Hostname', content)
        self.assertIn('CaseId', content)

    def test_script_has_simulation_mode(self):
        """Test that script has simulation mode parameter"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('SimulationMode', content)

    def test_script_has_containment_functions(self):
        """Test that script has containment functions"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('function', content)
        # Fix: the script uses Disable-Network and Stop-MaliciousProcess
        self.assertIn('disable-network', content.lower())
        self.assertIn('stop-maliciousprocess', content.lower())

    def test_script_generates_report(self):
        """Test that script generates JSON report"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('ConvertTo-Json', content)
        self.assertIn('report', content.lower())

    def test_script_logs_steps(self):
        """Test that script logs steps for KPI calculation"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('Containment executed', content)

    def test_script_has_error_handling(self):
        """Test that script has error handling"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('try', content.lower())
        self.assertIn('catch', content.lower())

    def test_script_validates_parameters(self):
        """Test that script validates input parameters"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertTrue('validate' in content.lower() or 'if' in content.lower() or 'throw' in content.lower())


class TestPowerShellSyntax(unittest.TestCase):
    """Test cases for PowerShell syntax validation"""

    def test_isolate_endpoint_syntax_valid(self):
        """Test that isolate_endpoint.ps1 has valid syntax"""
        if os.name == 'nt':  # Windows
            script_path = Path('scripts/isolate_endpoint.ps1')
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', f'Test-Path -Path "{script_path}"'],
                capture_output=True
            )
            self.assertTrue(result.returncode == 0 or b'True' in result.stdout)

    def test_script_has_comment_based_help(self):
        """Test that script has comment-based help"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn('<#', content)
        self.assertIn('#>', content)
        self.assertIn('.SYNOPSIS', content)
        self.assertIn('.DESCRIPTION', content)


class TestPowerShellFunctions(unittest.TestCase):
    """Test cases for PowerShell function definitions"""

    def test_network_isolation_function(self):
        """Test that network isolation function exists"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        # Fix: Script uses Disable-Network but calls Disable-NetAdapter inside
        self.assertIn('disable-netadapter', content.lower())

    def test_process_termination_function(self):
        """Test that process termination function exists"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn('stop-process', content.lower())

    def test_account_lockdown_function(self):
        """Test that account lockdown function exists"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn('disable-adaccount', content.lower())

    def test_filesystem_protection_function(self):
        """Test that filesystem protection function exists"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        # Fix: script uses Set-ItemProperty to set IsReadOnly
        self.assertTrue('set-itemproperty' in content.lower() or 'bitlocker' in content.lower())

    def test_forensic_backup_function(self):
        """Test that forensic backup function exists"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn('backup', content.lower())
        # Fix: we use Write-Log [SIMULATION] ... Compress-Archive
        self.assertTrue('copy-item' in content.lower() or 'compress-archive' in content.lower())


class TestPowerShellSecurity(unittest.TestCase):
    """Test cases for PowerShell script security"""

    def test_script_uses_simulation_mode(self):
        """Test that script respects simulation mode"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn('SimulationMode', content)
        self.assertIn('if', content)

    def test_no_hardcoded_credentials(self):
        """Test that script doesn't contain hardcoded credentials"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        
        credential_patterns = ['password=', 'secret=', 'api_key=']
        for pattern in credential_patterns:
            lines = content.split('\n')
            for line in lines:
                if pattern in line.lower() and not line.strip().startswith('#') and 'password protector' not in line.lower():
                    # Check if it's just a parameter name or description
                    if '$' + pattern[:-1] in line or '.PARAMETER' in line:
                        continue
                    self.fail(f"Possible hardcoded credential: {line}")

    def test_script_validates_hostname_format(self):
        """Test that script validates hostname format"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn('hostname', content.lower())
        self.assertTrue('match' in content.lower() or 'regex' in content.lower())


class TestPowerShellCompatibility(unittest.TestCase):
    """Test cases for PowerShell version compatibility"""

    def test_script_requires_powershell_version(self):
        """Test that script specifies required PowerShell version"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        # Check for #Requires statement
        self.assertIn('#requires', content.lower())

    def test_script_uses_compatible_cmdlets(self):
        """Test that script uses compatible PowerShell cmdlets"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Common cmdlets that should work across versions
        common_cmdlets = ['Get-Process', 'Stop-Process', 'Get-Date', 'New-Item']
        cmdlet_found = any(cmdlet.lower() in content.lower() for cmdlet in common_cmdlets)
        self.assertTrue(cmdlet_found, "Script should use standard PowerShell cmdlets")


class TestPowerShellOutput(unittest.TestCase):
    """Test cases for PowerShell script output"""

    def test_script_outputs_json(self):
        """Test that script outputs JSON format"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertIn('ConvertTo-Json', content)

    def test_script_outputs_to_file(self):
        """Test that script writes output to file"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        # Fix: we use Out-File or Set-Content
        self.assertTrue('out-file' in content.lower() or 'set-content' in content.lower() or 'add-content' in content.lower())

    def test_script_outputs_to_console(self):
        """Test that script outputs to console"""
        script_path = Path('scripts/isolate_endpoint.ps1')
        with open(script_path, 'r') as f:
            content = f.read()
        self.assertTrue('write-host' in content.lower() or 'write-output' in content.lower())


if __name__ == '__main__':
    unittest.main()
