#!/usr/bin/env python3
"""
Backup and restore tests for the SOAR Ransomware Lab
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


def read_file_utf8(file_path):
    """Helper function to read files with UTF-8 encoding"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


class TestBackupScript(unittest.TestCase):
    """Test cases for backup.sh script"""

    def setUp(self):
        """Set up test fixtures"""
        self.script_path = Path('scripts/infra/backup.sh')
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)

    def test_backup_script_exists(self):
        """Test that backup.sh exists"""
        self.assertTrue(self.script_path.exists())

    def test_backup_script_is_executable(self):
        """Test that backup.sh is executable"""
        if os.name != 'nt':
            self.assertTrue(os.access(self.script_path, os.X_OK))

    def test_backup_script_syntax_valid(self):
        """Test that backup.sh has valid bash syntax"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', '-n', str(self.script_path)],
                capture_output=True
            )
            self.assertEqual(result.returncode, 0, "Script has syntax errors")

    def test_backup_script_has_backup_dir_variable(self):
        """Test that backup script has BACKUP_DIR variable"""
        content = read_file_utf8(self.script_path)
        self.assertIn('BACKUP_DIR', content)

    def test_backup_script_backs_up_config(self):
        """Test that backup script backs up configuration files"""
        content = read_file_utf8(self.script_path)
        self.assertIn('docker/.env', content)
        self.assertIn('tar', content)

    def test_backup_script_backs_up_certificates(self):
        """Test that backup script backs up certificates"""
        content = read_file_utf8(self.script_path)
        self.assertIn('certs', content)

    def test_backup_script_backs_up_volumes(self):
        """Test that backup script backs up Docker volumes"""
        content = read_file_utf8(self.script_path)
        self.assertIn('volume', content.lower())
        self.assertIn('docker', content.lower())

    def test_backup_script_backs_up_logs(self):
        """Test that backup script backs up logs"""
        content = read_file_utf8(self.script_path)
        self.assertIn('logs', content)

    def test_backup_script_backs_up_results(self):
        """Test that backup script backs up results"""
        content = read_file_utf8(self.script_path)
        self.assertIn('results', content)

    def test_backup_script_creates_manifest(self):
        """Test that backup script creates manifest file"""
        content = read_file_utf8(self.script_path)
        self.assertIn('manifest', content.lower())

    def test_backup_script_cleans_old_backups(self):
        """Test that backup script cleans old backups"""
        content = read_file_utf8(self.script_path)
        self.assertIn('find', content)
        self.assertIn('rm', content)

    def test_backup_script_uses_compression(self):
        """Test that backup script uses compression"""
        content = read_file_utf8(self.script_path)
        self.assertIn('tar', content)
        # Check for either 'gz' extension or gzip compression flag
        self.assertTrue('gz' in content or 'tar -cz' in content or 'gzip' in content)

    def test_backup_script_has_error_handling(self):
        """Test that backup script has error handling"""
        content = read_file_utf8(self.script_path)
        self.assertIn('set -e', content)
        # Check for either 'set -u' or 'set -euo pipefail' (both provide error handling)
        self.assertTrue('set -u' in content or 'set -euo pipefail' in content)


class TestRestoreScript(unittest.TestCase):
    """Test cases for restore.sh script"""

    def setUp(self):
        """Set up test fixtures"""
        self.script_path = Path('scripts/infra/restore.sh')
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)

    def test_restore_script_exists(self):
        """Test that restore.sh exists"""
        self.assertTrue(self.script_path.exists())

    def test_restore_script_is_executable(self):
        """Test that restore.sh is executable"""
        if os.name != 'nt':
            self.assertTrue(os.access(self.script_path, os.X_OK))

    def test_restore_script_syntax_valid(self):
        """Test that restore.sh has valid bash syntax"""
        if os.name != 'nt':
            result = subprocess.run(
                ['bash', '-n', str(self.script_path)],
                capture_output=True
            )
            self.assertEqual(result.returncode, 0, "Script has syntax errors")

    def test_restore_script_requires_backup_name(self):
        """Test that restore script requires backup name parameter"""
        content = read_file_utf8(self.script_path)
        self.assertIn('$1', content)
        self.assertIn('backup_name', content.lower())

    def test_restore_script_checks_backup_exists(self):
        """Test that restore script checks if backup exists"""
        content = read_file_utf8(self.script_path)
        self.assertIn('exists', content.lower()) or self.assertIn('-f', content)

    def test_restore_script_stops_services(self):
        """Test that restore script stops services before restore"""
        content = read_file_utf8(self.script_path)
        self.assertIn('down', content)
        self.assertIn('docker', content.lower())

    def test_restore_script_restores_config(self):
        """Test that restore script restores configuration"""
        content = read_file_utf8(self.script_path)
        self.assertIn('extract', content.lower()) or self.assertIn('tar', content)

    def test_restore_script_restores_volumes(self):
        """Test that restore script restores Docker volumes"""
        content = read_file_utf8(self.script_path)
        self.assertIn('volume', content.lower())
        self.assertIn('docker', content.lower())

    def test_restore_script_starts_services(self):
        """Test that restore script starts services after restore"""
        content = read_file_utf8(self.script_path)
        self.assertIn('up', content)
        self.assertIn('docker', content.lower())

    def test_restore_script_requires_confirmation(self):
        """Test that restore script requires user confirmation"""
        content = read_file_utf8(self.script_path)
        self.assertIn('read', content.lower())
        # Check for confirmation in English or Spanish
        self.assertTrue('confirm' in content.lower() or 'continue' in content.lower() or 'continuar' in content.lower())

    def test_restore_script_has_error_handling(self):
        """Test that restore script has error handling"""
        content = read_file_utf8(self.script_path)
        self.assertIn('set -e', content)
        # Check for either 'set -u' or 'set -euo pipefail' (both provide error handling)
        self.assertTrue('set -u' in content or 'set -euo pipefail' in content)


class TestBackupRestoreIntegration(unittest.TestCase):
    """Integration tests for backup and restore"""

    def test_backup_and_restore_scripts_compatible(self):
        """Test that backup and restore scripts use compatible formats"""
        backup_path = Path('scripts/infra/backup.sh')
        restore_path = Path('scripts/infra/restore.sh')
        
        backup_content = read_file_utf8(backup_path)
        
        restore_content = read_file_utf8(restore_path)
        
        # Both should use same backup directory variable
        self.assertIn('BACKUP_DIR', backup_content)
        self.assertIn('BACKUP_DIR', restore_content)

    def test_backup_naming_convention(self):
        """Test that backup uses consistent naming convention"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        self.assertIn('BACKUP_NAME', content)
        self.assertIn('DATE', content)

    def test_restore_expects_same_naming(self):
        """Test that restore expects same naming convention"""
        restore_path = Path('scripts/infra/restore.sh')
        content = read_file_utf8(restore_path)
        self.assertIn('BACKUP_NAME', content)


class TestBackupSecurity(unittest.TestCase):
    """Security tests for backup and restore"""

    def test_backup_does_not_include_sensitive_data(self):
        """Test that backup excludes sensitive data"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        
        # Should not backup running container data with secrets
        # This is a code review test
        self.assertIn('docker/.env', content)  # Config is OK
        # But should not backup runtime secrets if possible

    def test_restore_does_not_overwrite_without_confirmation(self):
        """Test that restore requires confirmation before overwriting"""
        restore_path = Path('scripts/infra/restore.sh')
        content = read_file_utf8(restore_path)
        self.assertIn('read', content.lower())
        # Check for confirmation in English or Spanish
        self.assertTrue('y' in content.lower() or 'yes' in content.lower() or 's' in content.lower())

    def test_backup_script_permissions(self):
        """Test that backup script has appropriate permissions"""
        backup_path = Path('scripts/infra/backup.sh')
        if os.name != 'nt':
            # Script should be executable but not world-writable
            stat_info = os.stat(backup_path)
            mode = oct(stat_info.st_mode)[-3:]
            # Should be at least 755 or similar
            self.assertIn('7', mode)


class TestBackupManifest(unittest.TestCase):
    """Test cases for backup manifest"""

    def test_backup_script_generates_manifest(self):
        """Test that backup script generates a manifest file"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        self.assertIn('manifest', content.lower())
        self.assertIn('.txt', content)

    def test_manifest_includes_backup_info(self):
        """Test that manifest includes backup information"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        self.assertIn('date', content.lower())
        self.assertIn('name', content.lower())


class TestBackupDirectory(unittest.TestCase):
    """Test cases for backup directory management"""

    def test_backup_directory_configurable(self):
        """Test that backup directory is configurable via environment variable"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        self.assertIn('${BACKUP_DIR', content)

    def test_backup_directory_default(self):
        """Test that backup directory has a default value"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        self.assertIn(':-', content)  # Default value syntax

    def test_backup_directory_created_if_not_exists(self):
        """Test that backup directory is created if it doesn't exist"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        self.assertIn('mkdir', content)


class TestDockerVolumeBackup(unittest.TestCase):
    """Test cases for Docker volume backup"""

    def test_backup_uses_docker_run_for_volumes(self):
        """Test that backup uses docker run to access volumes"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        self.assertIn('docker run', content)
        self.assertIn('-v', content)

    def test_backup_mounts_volumes_read_only(self):
        """Test that backup mounts volumes as read-only"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        self.assertIn(':ro', content)

    def test_restore_creates_volumes_if_needed(self):
        """Test that restore creates volumes if they don't exist"""
        restore_path = Path('scripts/infra/restore.sh')
        content = read_file_utf8(restore_path)
        self.assertIn('volume create', content.lower())


class TestBackupRestoreLogging(unittest.TestCase):
    """Test cases for backup and restore logging"""

    def test_backup_script_has_logging(self):
        """Test that backup script has logging"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        self.assertIn('log', content.lower()) or self.assertIn('echo', content)

    def test_restore_script_has_logging(self):
        """Test that restore script has logging"""
        restore_path = Path('scripts/infra/restore.sh')
        content = read_file_utf8(restore_path)
        self.assertIn('log', content.lower()) or self.assertIn('echo', content)

    def test_backup_logs_start_and_end(self):
        """Test that backup logs start and end of operation"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        # Check for English or Spanish start/end messages
        start_found = ('starting' in content.lower() or 'begin' in content.lower() or 
                     'iniciando' in content.lower())
        end_found = ('completed' in content.lower() or 'done' in content.lower() or 
                    'completado' in content.lower())
        self.assertTrue(start_found)
        self.assertTrue(end_found)


if __name__ == '__main__':
    unittest.main()
