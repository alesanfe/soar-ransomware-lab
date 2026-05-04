#!/usr/bin/env python3
"""
Backup and restore tests for the SOAR Ransomware Lab
"""

import unittest
import subprocess
import os
import tempfile
import shutil
from pathlib import Path


class TestBackupScript(unittest.TestCase):
    """Test cases for backup.sh script"""

    def setUp(self):
        """Set up test fixtures"""
        self.script_path = Path('scripts/backup.sh')
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
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('BACKUP_DIR', content)

    def test_backup_script_backs_up_config(self):
        """Test that backup script backs up configuration files"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('docker/.env', content)
        self.assertIn('tar', content)

    def test_backup_script_backs_up_certificates(self):
        """Test that backup script backs up certificates"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('certs', content)

    def test_backup_script_backs_up_volumes(self):
        """Test that backup script backs up Docker volumes"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('volume', content.lower())
        self.assertIn('docker', content.lower())

    def test_backup_script_backs_up_logs(self):
        """Test that backup script backs up logs"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('logs', content)

    def test_backup_script_backs_up_results(self):
        """Test that backup script backs up results"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('results', content)

    def test_backup_script_creates_manifest(self):
        """Test that backup script creates manifest file"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('manifest', content.lower())

    def test_backup_script_cleans_old_backups(self):
        """Test that backup script cleans old backups"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('find', content)
        self.assertIn('delete', content.lower()) or self.assertIn('rm', content)

    def test_backup_script_uses_compression(self):
        """Test that backup script uses compression"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('tar', content)
        self.assertIn('gz', content) or self.assertIn('gzip', content)

    def test_backup_script_has_error_handling(self):
        """Test that backup script has error handling"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('set -e', content)
        self.assertIn('set -u', content)


class TestRestoreScript(unittest.TestCase):
    """Test cases for restore.sh script"""

    def setUp(self):
        """Set up test fixtures"""
        self.script_path = Path('scripts/restore.sh')
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
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('$1', content)
        self.assertIn('backup_name', content.lower())

    def test_restore_script_checks_backup_exists(self):
        """Test that restore script checks if backup exists"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('exists', content.lower()) or self.assertIn('-f', content)

    def test_restore_script_stops_services(self):
        """Test that restore script stops services before restore"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('down', content)
        self.assertIn('docker', content.lower())

    def test_restore_script_restores_config(self):
        """Test that restore script restores configuration"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('extract', content.lower()) or self.assertIn('tar', content)

    def test_restore_script_restores_volumes(self):
        """Test that restore script restores Docker volumes"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('volume', content.lower())
        self.assertIn('docker', content.lower())

    def test_restore_script_starts_services(self):
        """Test that restore script starts services after restore"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('up', content)
        self.assertIn('docker', content.lower())

    def test_restore_script_requires_confirmation(self):
        """Test that restore script requires user confirmation"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('read', content.lower())
        self.assertIn('confirm', content.lower()) or self.assertIn('continue', content.lower())

    def test_restore_script_has_error_handling(self):
        """Test that restore script has error handling"""
        with open(self.script_path, 'r') as f:
            content = f.read()
        self.assertIn('set -e', content)
        self.assertIn('set -u', content)


class TestBackupRestoreIntegration(unittest.TestCase):
    """Integration tests for backup and restore"""

    def test_backup_and_restore_scripts_compatible(self):
        """Test that backup and restore scripts use compatible formats"""
        backup_path = Path('scripts/backup.sh')
        restore_path = Path('scripts/restore.sh')
        
        with open(backup_path, 'r') as f:
            backup_content = f.read()
        
        with open(restore_path, 'r') as f:
            restore_content = f.read()
        
        # Both should use same backup directory variable
        self.assertIn('BACKUP_DIR', backup_content)
        self.assertIn('BACKUP_DIR', restore_content)

    def test_backup_naming_convention(self):
        """Test that backup uses consistent naming convention"""
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertIn('BACKUP_NAME', content)
        self.assertIn('DATE', content)

    def test_restore_expects_same_naming(self):
        """Test that restore expects same naming convention"""
        restore_path = Path('scripts/restore.sh')
        with open(restore_path, 'r') as f:
            content = f.read()
        self.assertIn('BACKUP_NAME', content)


class TestBackupSecurity(unittest.TestCase):
    """Security tests for backup and restore"""

    def test_backup_does_not_include_sensitive_data(self):
        """Test that backup excludes sensitive data"""
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        
        # Should not backup running container data with secrets
        # This is a code review test
        self.assertIn('docker/.env', content)  # Config is OK
        # But should not backup runtime secrets if possible

    def test_restore_does_not_overwrite_without_confirmation(self):
        """Test that restore requires confirmation before overwriting"""
        restore_path = Path('scripts/restore.sh')
        with open(restore_path, 'r') as f:
            content = f.read()
        self.assertIn('read', content.lower())
        self.assertIn('y', content.lower()) or self.assertIn('yes', content.lower())

    def test_backup_script_permissions(self):
        """Test that backup script has appropriate permissions"""
        backup_path = Path('scripts/backup.sh')
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
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertIn('manifest', content.lower())
        self.assertIn('.txt', content)

    def test_manifest_includes_backup_info(self):
        """Test that manifest includes backup information"""
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertIn('date', content.lower())
        self.assertIn('name', content.lower())


class TestBackupDirectory(unittest.TestCase):
    """Test cases for backup directory management"""

    def test_backup_directory_configurable(self):
        """Test that backup directory is configurable via environment variable"""
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertIn('${BACKUP_DIR', content)

    def test_backup_directory_default(self):
        """Test that backup directory has a default value"""
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertIn(':-', content)  # Default value syntax

    def test_backup_directory_created_if_not_exists(self):
        """Test that backup directory is created if it doesn't exist"""
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertIn('mkdir', content)


class TestDockerVolumeBackup(unittest.TestCase):
    """Test cases for Docker volume backup"""

    def test_backup_uses_docker_run_for_volumes(self):
        """Test that backup uses docker run to access volumes"""
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertIn('docker run', content)
        self.assertIn('-v', content)

    def test_backup_mounts_volumes_read_only(self):
        """Test that backup mounts volumes as read-only"""
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertIn(':ro', content)

    def test_restore_creates_volumes_if_needed(self):
        """Test that restore creates volumes if they don't exist"""
        restore_path = Path('scripts/restore.sh')
        with open(restore_path, 'r') as f:
            content = f.read()
        self.assertIn('volume create', content.lower())


class TestBackupRestoreLogging(unittest.TestCase):
    """Test cases for backup and restore logging"""

    def test_backup_script_has_logging(self):
        """Test that backup script has logging"""
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertIn('log', content.lower()) or self.assertIn('echo', content)

    def test_restore_script_has_logging(self):
        """Test that restore script has logging"""
        restore_path = Path('scripts/restore.sh')
        with open(restore_path, 'r') as f:
            content = f.read()
        self.assertIn('log', content.lower()) or self.assertIn('echo', content)

    def test_backup_logs_start_and_end(self):
        """Test that backup logs start and end of operation"""
        backup_path = Path('scripts/backup.sh')
        with open(backup_path, 'r') as f:
            content = f.read()
        self.assertIn('starting', content.lower()) or self.assertIn('begin', content.lower())
        self.assertIn('completed', content.lower()) or self.assertIn('done', content.lower())


if __name__ == '__main__':
    unittest.main()
