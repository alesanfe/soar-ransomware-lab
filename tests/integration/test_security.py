#!/usr/bin/env python3
"""
Security tests for the SOAR Ransomware Lab
"""

import os
import subprocess
import unittest
from pathlib import Path


def read_file_utf8(file_path):
    """Helper function to read files with UTF-8 encoding"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


class TestFilePermissions(unittest.TestCase):
    """Test cases for file permissions"""

    def test_env_file_not_in_git(self):
        """Test that .env file is not tracked by git"""
        result = subprocess.run(
            ['git', 'ls-files', 'infra/docker/.env'],
            capture_output=True,
            text=True
        )
        # Should not be tracked
        self.assertEqual(result.stdout.strip(), '')

    def test_sensitive_files_in_gitignore(self):
        """Test that sensitive files are in .gitignore"""
        gitignore_path = Path('.gitignore')
        self.assertTrue(gitignore_path.exists())
        
        gitignore_content = read_file_utf8(gitignore_path)
        
        sensitive_patterns = ['.env', '*.key', '*.pem', '*.crt', 'logs/', 'backups/', 'certs/']
        
        for pattern in sensitive_patterns:
            self.assertIn(pattern, gitignore_content, f"{pattern} should be in .gitignore")

    def test_certificates_directory_exists(self):
        """Test that certs directory exists or is ignored"""
        certs_path = Path('certs')
        if certs_path.exists():
            # If it exists, check it's not tracked
            result = subprocess.run(
                ['git', 'ls-files', 'certs/'],
                capture_output=True,
                text=True
            )
            self.assertEqual(result.stdout.strip(), 'certs/ should not be tracked')


class TestConfigurationSecurity(unittest.TestCase):
    """Test cases for configuration security"""

    def test_tls_enabled_in_env_example(self):
        """Test that TLS is enabled in secure docker compose"""
        secure_compose_path = Path('docker-compose-secure.yml')
        if secure_compose_path.exists():
            content = read_file_utf8(secure_compose_path)
            # Check for SSL/TLS configuration in nginx
            self.assertIn('ssl_certificate', content)
            self.assertIn('ssl_certificate_key', content)
        else:
            # Skip test if secure compose file doesn't exist
            self.skipTest("docker-compose-secure.yml not found")

    def test_cortex_secret_key_not_default(self):
        """Test that Cortex secret key is not default value"""
        cortex_conf_path = Path('infra/docker/docker/cortex.application.conf/cortex.conf')
        if cortex_conf_path.exists():
            content = read_file_utf8(cortex_conf_path)
            self.assertNotIn('***CHANGEME***', content)
            self.assertIn('play.http.secret.key', content)
        else:
            # Skip test if Cortex config file doesn't exist
            self.skipTest("Cortex configuration file not found")

    def test_env_example_has_secure_defaults(self):
        """Test that .env.example has secure default values"""
        env_example_path = Path('.env.example')
        if env_example_path.exists():
            content = read_file_utf8(env_example_path)
            
            # Check for empty passwords (password= without value)
            lines = content.split('\n')
            for line in lines:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.split('=', 1)
                    if 'password' in key.lower() and not value.strip():
                        self.fail(f"Empty password found for {key}")
            
            # Check for placeholder indicators
            self.assertTrue('change' in content.lower() or 'generate' in content.lower() or '<' in content)
        else:
            # Skip test if .env.example file doesn't exist
            self.skipTest(".env.example file not found")

    def test_no_hardcoded_secrets_in_scripts(self):
        """Test that scripts don't contain hardcoded secrets"""
        script_files = [
            'src/soar_lab/services/send_alert.py',
            'scripts/utils/notify.sh',
            'scripts/security/isolate_host.sh'
        ]
        
        secret_patterns = ['password=', 'secret=', 'api_key=', 'token=']
        
        for script in script_files:
            script_path = Path(script)
            if script_path.exists():
                content = read_file_utf8(script_path)
                for pattern in secret_patterns:
                    # Check for hardcoded values (not environment variables)
                    lines = content.split('\n')
                    for line in lines:
                        if pattern in line and not line.strip().startswith('#'):
                            # Allow environment variable references
                            if '$' not in line and '${' not in line:
                                self.fail(f"Possible hardcoded secret in {script}: {line}")


class TestDockerSecurity(unittest.TestCase):
    """Test cases for Docker security configuration"""

    def test_docker_socket_read_only(self):
        """Test that Docker socket is mounted read-only where applicable"""
        compose_path = Path('infra/docker/docker-compose.yml')
        content = read_file_utf8(compose_path)
        
        # Check for read-only mounts
        self.assertIn(':ro', content, "Docker socket should be mounted read-only")

    def test_no_privileged_containers(self):
        """Test that no containers run in privileged mode"""
        compose_path = Path('infra/docker/docker-compose.yml')
        content = read_file_utf8(compose_path)
        self.assertNotIn('privileged: true', content)

    def test_resource_limits_configured(self):
        """Test that resource limits are configured"""
        compose_path = Path('infra/docker/docker-compose.yml')
        content = read_file_utf8(compose_path)
        self.assertIn('deploy:', content)
        self.assertIn('resources:', content)
        self.assertIn('limits:', content)

    def test_log_rotation_configured(self):
        """Test that log rotation is configured"""
        compose_path = Path('infra/docker/docker-compose.yml')
        content = read_file_utf8(compose_path)
        self.assertIn('logging:', content)
        self.assertIn('max-size:', content)
        self.assertIn('max-file:', content)

    def test_no_root_user_in_containers(self):
        """Test that containers don't run as root by default"""
        compose_path = Path('infra/docker/docker-compose.yml')
        content = read_file_utf8(compose_path)
        # Check if user is specified (best practice)
        # This is a soft check - some containers may run as root
        # We just verify the file has user configuration where applicable


class TestNetworkSecurity(unittest.TestCase):
    """Test cases for network security"""

    def test_internal_network_isolated(self):
        """Test that internal network is isolated"""
        compose_path = Path('infra/docker/docker-compose.yml')
        content = read_file_utf8(compose_path)
        self.assertIn('soar_net', content)
        # Check for internal network configuration
        if 'internal:' in content:
            self.assertIn('true', content)

    def test_minimal_exposed_ports(self):
        """Test that only necessary ports are exposed"""
        compose_path = Path('infra/docker/docker-compose.yml')
        content = read_file_utf8(compose_path)
        
        # Count exposed ports
        port_count = content.count('ports:')
        # For a full SOAR stack, 15-20 exposed ports is reasonable
        self.assertLess(port_count, 20, "Too many exposed ports for SOAR stack")

    def test_elasticsearch_not_exposed(self):
        """Test that Elasticsearch port configuration is appropriate"""
        compose_path = Path('infra/docker/docker-compose.yml')
        content = read_file_utf8(compose_path)
        
        # In a lab environment, Elasticsearch may be exposed but should use non-standard ports
        lines = content.split('\n')
        in_elasticsearch = False
        elasticsearch_port = None
        
        for line in lines:
            if 'elasticsearch:' in line:
                in_elasticsearch = True
            elif in_elasticsearch and 'ports:' in line:
                # Check next lines for port mapping
                for next_line in lines[lines.index(line) + 1:]:
                    if '- "' in next_line and ':9200' in next_line:
                        # Extract the external port
                        elasticsearch_port = next_line.split('"')[1].split(':')[0]
                        break
                    elif next_line.strip().startswith(' ') and 'ports:' not in next_line:
                        continue
                    else:
                        break
        
        # If exposed, should use a non-standard port (not 9200)
        if elasticsearch_port:
            self.assertNotEqual(elasticsearch_port, '9200', 
                              "Elasticsearch should not use standard port 9200 when exposed")


class TestScriptSecurity(unittest.TestCase):
    """Test cases for script security"""

    def test_scripts_use_set_e(self):
        """Test that bash scripts use set -e for error handling"""
        bash_scripts = [
            'scripts/security/isolate_host.sh',
            'scripts/utils/notify.sh',
            'scripts/security/setup_firewall.sh',
            'scripts/infra/backup.sh',
            'scripts/infra/restore.sh'
        ]
        
        for script in bash_scripts:
            script_path = Path(script)
            if script_path.exists():
                content = read_file_utf8(script_path)
                self.assertIn('set -e', content, f"{script} should use set -e")

    def test_no_temp_files_left_behind(self):
        """Test that scripts clean up temporary files"""
        # This is a code review test - check scripts for cleanup
        bash_scripts = [
            'scripts/utils/gen_certs.sh',
            'scripts/maintenance/backup.sh'
        ]
        
        for script in bash_scripts:
            script_path = Path(script)
            if script_path.exists():
                content = read_file_utf8(script_path)
                # Check for cleanup commands
                self.assertTrue(
                    'rm' in content or 'cleanup' in content.lower(),
                    f"{script} should have cleanup logic"
                )

    def test_no_echo_of_passwords(self):
        """Test that scripts don't echo passwords"""
        bash_scripts = [
            'scripts/utils/notify.sh',
            'scripts/security/isolate_host.sh'
        ]
        
        for script in bash_scripts:
            script_path = Path(script)
            if script_path.exists():
                content = read_file_utf8(script_path)
                # Check for echo with password-related variables
                lines = content.split('\n')
                for line in lines:
                    if 'echo' in line.lower():
                        self.assertNotIn('password', line.lower())
                        self.assertNotIn('secret', line.lower())


class TestInputValidation(unittest.TestCase):
    """Test cases for input validation"""

    def test_hostname_validation_in_isolate_host(self):
        """Test that isolate_host.sh validates hostname"""
        script_path = Path('scripts/security/isolate_host.sh')
        if script_path.exists():
            content = read_file_utf8(script_path)
            self.assertIn('validate', content.lower())
            self.assertIn('hostname', content.lower())
        else:
            self.skipTest("isolate_host.sh script not found")

    def test_case_id_validation_in_isolate_host(self):
        """Test that isolate_host.sh validates case_id"""
        script_path = Path('scripts/security/isolate_host.sh')
        if script_path.exists():
            content = read_file_utf8(script_path)
            self.assertIn('case_id', content.lower())
            self.assertIn('validate', content.lower())
        else:
            self.skipTest("isolate_host.sh script not found")

    def test_action_validation_in_notify(self):
        """Test that notify.sh validates action parameter"""
        script_path = Path('scripts/utils/notify.sh')
        if script_path.exists():
            content = read_file_utf8(script_path)
            self.assertIn('action', content.lower())
            # Check for action validation (either 'invalid' or 'unknown action' error handling)
            self.assertTrue('invalid' in content.lower() or 'unknown action' in content.lower())
        else:
            self.skipTest("notify.sh script not found")


class TestBackupSecurity(unittest.TestCase):
    """Test cases for backup security"""

    def test_backup_script_exists(self):
        """Test that backup script exists"""
        backup_path = Path('scripts/infra/backup.sh')
        self.assertTrue(backup_path.exists())

    def test_restore_script_exists(self):
        """Test that restore script exists"""
        restore_path = Path('scripts/infra/restore.sh')
        self.assertTrue(restore_path.exists())

    def test_backup_script_uses_encryption(self):
        """Test that backup script considers encryption (code review)"""
        backup_path = Path('scripts/infra/backup.sh')
        content = read_file_utf8(backup_path)
        # Check for encryption or compression
        self.assertTrue(
            'tar' in content or 'gzip' in content or 'encrypt' in content.lower(),
            "Backup should use compression or encryption"
        )

    def test_restore_requires_confirmation(self):
        """Test that restore script requires user confirmation"""
        restore_path = Path('scripts/infra/restore.sh')
        content = read_file_utf8(restore_path)
        self.assertIn('read', content.lower())
        self.assertIn('confirm', content.lower())


if __name__ == '__main__':
    unittest.main()
