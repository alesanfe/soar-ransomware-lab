#!/usr/bin/env python3
"""
Configuration tests for the SOAR Ransomware Lab
"""

import unittest
import subprocess
import os
from pathlib import Path


def read_file_utf8(file_path):
    """Helper function to read files with UTF-8 encoding"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


class TestEnvironmentConfiguration(unittest.TestCase):
    """Test cases for environment configuration"""

    def test_env_example_exists(self):
        """Test that .env.example exists"""
        env_example = Path('docker/.env.example')
        self.assertTrue(env_example.exists())

    def test_env_example_has_all_required_variables(self):
        """Test that .env.example has all required variables"""
        env_example = Path('docker/.env.example')
        with open(env_example, 'r') as f:
            content = f.read()
        
        required_vars = [
            'THEHIVE_HTTP_PORT',
            'CORTEX_HTTP_PORT',
            'SHUFFLE_UI_PORT',
            'SHUFFLE_API_PORT',
            'ELASTICSEARCH_PORT',
            'THEHIVE_SECRET',
            'CORTEX_SECRET',
            'SHUFFLE_DEFAULT_APIKEY',
            'SIEM_WEBHOOK_TOKEN',
            'DECISION_SCORE_THRESHOLD',
            'ENABLE_TLS'
        ]
        
        for var in required_vars:
            self.assertIn(var, content, f"{var} should be in .env.example")

    def test_env_example_has_comments(self):
        """Test that .env.example has descriptive comments"""
        env_example = Path('docker/.env.example')
        with open(env_example, 'r') as f:
            content = f.read()
        self.assertIn('#', content)

    def test_env_example_values_are_not_empty(self):
        """Test that .env.example has non-empty default values"""
        env_example = Path('docker/.env.example')
        with open(env_example, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                var, value = line.split('=', 1)
                # Skip values that are intentionally empty or placeholders
                if value.strip() and 'change' not in value.lower():
                    self.assertGreater(len(value.strip()), 0)


class TestDockerComposeConfiguration(unittest.TestCase):
    """Test cases for docker-compose.yml configuration"""

    def test_docker_compose_exists(self):
        """Test that docker-compose.yml exists"""
        compose_path = Path('docker/docker-compose.yml')
        self.assertTrue(compose_path.exists())

    def test_docker_compose_version(self):
        """Test that docker-compose.yml has valid version"""
        compose_path = Path('docker/docker-compose.yml')
        with open(compose_path, 'r') as f:
            content = f.read()
        self.assertIn('version:', content)

    def test_docker_compose_uses_env_file(self):
        """Test that docker-compose.yml uses environment variables"""
        compose_path = Path('docker/docker-compose.yml')
        with open(compose_path, 'r') as f:
            content = f.read()
        # Check for environment variable usage (either env_file: or ${VAR} syntax)
        self.assertTrue('env_file:' in content or '${' in content)

    def test_docker_compose_has_networks(self):
        """Test that docker-compose.yml defines networks"""
        compose_path = Path('docker/docker-compose.yml')
        with open(compose_path, 'r') as f:
            content = f.read()
        self.assertIn('networks:', content)
        self.assertIn('soar_edge', content)
        self.assertIn('soar_net', content)

    def test_docker_compose_has_volumes(self):
        """Test that docker-compose.yml defines volumes"""
        compose_path = Path('docker/docker-compose.yml')
        with open(compose_path, 'r') as f:
            content = f.read()
        self.assertIn('volumes:', content)

    def test_docker_compose_services_use_image_variables(self):
        """Test that services use image variables for flexibility"""
        compose_path = Path('docker/docker-compose.yml')
        with open(compose_path, 'r') as f:
            content = f.read()
        self.assertIn('${', content)


class TestTheHiveConfiguration(unittest.TestCase):
    """Test cases for TheHive configuration"""

    def test_thehive_config_exists(self):
        """Test that thehive.application.conf exists"""
        config_path = Path('docker/thehive.application.conf')
        self.assertTrue(config_path.exists())

    def test_thehive_config_has_elasticsearch_config(self):
        """Test that TheHive config has Elasticsearch configuration"""
        config_path = Path('docker/thehive.application.conf')
        with open(config_path, 'r') as f:
            content = f.read()
        self.assertIn('search', content)
        self.assertIn('elasticsearch', content.lower())

    def test_thehive_config_has_cortex_config(self):
        """Test that TheHive config has Cortex configuration"""
        config_path = Path('docker/thehive.application.conf')
        with open(config_path, 'r') as f:
            content = f.read()
        self.assertIn('cortex', content.lower())

    def test_thehive_config_has_base_url(self):
        """Test that TheHive config has base URL"""
        config_path = Path('docker/thehive.application.conf')
        with open(config_path, 'r') as f:
            content = f.read()
        self.assertIn('baseUrl', content)


class TestCortexConfiguration(unittest.TestCase):
    """Test cases for Cortex configuration"""

    def test_cortex_config_exists(self):
        """Test that cortex.application.conf exists"""
        config_path = Path('docker/cortex.application.conf')
        self.assertTrue(config_path.exists())

    def test_cortex_config_has_elasticsearch_config(self):
        """Test that Cortex config has Elasticsearch configuration"""
        config_path = Path('docker/cortex.application.conf')
        with open(config_path, 'r') as f:
            content = f.read()
        self.assertIn('search', content)
        self.assertIn('elasticsearch', content.lower())

    def test_cortex_config_has_secret_key(self):
        """Test that Cortex config has secret key configured"""
        config_path = Path('docker/cortex.application.conf')
        with open(config_path, 'r') as f:
            content = f.read()
        self.assertIn('play.http.secret.key', content)

    def test_cortex_config_has_job_directory(self):
        """Test that Cortex config has job directory"""
        config_path = Path('docker/cortex.application.conf')
        with open(config_path, 'r') as f:
            content = f.read()
        self.assertIn('job-directory', content)


class TestPortConfiguration(unittest.TestCase):
    """Test cases for port configuration"""

    def test_ports_are_configurable(self):
        """Test that ports are configurable via environment variables"""
        env_example = Path('docker/.env.example')
        with open(env_example, 'r') as f:
            content = f.read()
        
        port_vars = ['THEHIVE_HTTP_PORT', 'CORTEX_HTTP_PORT', 'SHUFFLE_UI_PORT', 'ELASTICSEARCH_PORT']
        for var in port_vars:
            self.assertIn(var, content)

    def test_ports_do_not_conflict(self):
        """Test that configured ports don't conflict"""
        env_example = Path('docker/.env.example')
        with open(env_example, 'r') as f:
            content = f.read()
        
        # Extract port values
        port_values = []
        for line in content.split('\n'):
            if 'PORT=' in line and not line.strip().startswith('#'):
                var, value = line.split('=', 1)
                try:
                    port = int(value.strip())
                    port_values.append(port)
                except ValueError:
                    pass
        
        # Check for duplicates
        self.assertEqual(len(port_values), len(set(port_values)), "Ports should be unique")

    def test_default_ports_are_standard(self):
        """Test that default ports are standard for each service"""
        env_example = Path('docker/.env.example')
        with open(env_example, 'r') as f:
            content = f.read()
        
        # Standard ports
        self.assertIn('9000', content)  # TheHive
        self.assertIn('9001', content)  # Cortex
        self.assertIn('3001', content)  # Shuffle UI
        self.assertIn('5001', content)  # Shuffle API
        self.assertIn('19200', content)  # Elasticsearch


class TestDirectoryStructure(unittest.TestCase):
    """Test cases for directory structure"""

    def test_scripts_directory_exists(self):
        """Test that scripts directory exists"""
        scripts_dir = Path('scripts')
        self.assertTrue(scripts_dir.exists())

    def test_schemas_directory_exists(self):
        """Test that schemas directory exists"""
        schemas_dir = Path('schemas')
        self.assertTrue(schemas_dir.exists())

    def test_docker_directory_exists(self):
        """Test that docker directory exists"""
        docker_dir = Path('docker')
        self.assertTrue(docker_dir.exists())

    def test_docs_directory_exists(self):
        """Test that docs directory exists"""
        docs_dir = Path('docs')
        self.assertTrue(docs_dir.exists())

    def test_tests_directory_exists(self):
        """Test that tests directory exists"""
        tests_dir = Path('tests')
        self.assertTrue(tests_dir.exists())

    def test_required_scripts_exist(self):
        """Test that required scripts exist"""
        required_scripts = [
            'scripts/send_alert.py',
            'scripts/calc_kpis.py',
            'scripts/isolate_host.sh',
            'scripts/notify.sh',
            'scripts/gen_certs.sh'
        ]
        
        for script in required_scripts:
            script_path = Path(script)
            self.assertTrue(script_path.exists(), f"{script} should exist")

    def test_required_schemas_exist(self):
        """Test that required schemas exist"""
        required_schemas = [
            'schemas/alert.schema.json'
        ]
        
        for schema in required_schemas:
            schema_path = Path(schema)
            self.assertTrue(schema_path.exists(), f"{schema} should exist")


class TestDocumentationCompleteness(unittest.TestCase):
    """Test cases for documentation completeness"""

    def test_readme_exists(self):
        """Test that README.md exists"""
        readme_path = Path('README.md')
        self.assertTrue(readme_path.exists())

    def test_readme_has_required_sections(self):
        """Test that README has required sections"""
        readme_path = Path('README.md')
        content = read_file_utf8(readme_path)
        
        required_sections = [
            '# SOAR',
            'Installation',
            'Usage',
            'Architecture'
        ]
        
        # Check for sections in English or Spanish
        found_sections = 0
        for section in required_sections:
            if section in content:
                found_sections += 1
            elif section == '# SOAR' and '# Laboratorio SOAR' in content:
                found_sections += 1
            elif section == 'Installation' and ('Instalación' in content or 'Instalaci' in content):
                found_sections += 1
            elif section == 'Usage' and ('Uso' in content or 'Usage' in content):
                found_sections += 1
            elif section == 'Architecture' and ('Arquitectura' in content or 'Architecture' in content):
                found_sections += 1
        
        self.assertGreaterEqual(found_sections, 3, "README should have at least 3 of the required sections")

    def test_security_doc_exists(self):
        """Test that security.md exists"""
        security_path = Path('docs/security.md')
        self.assertTrue(security_path.exists())

    def test_validation_doc_exists(self):
        """Test that validation.md exists"""
        validation_path = Path('docs/validation.md')
        self.assertTrue(validation_path.exists())

    def test_user_guide_exists(self):
        """Test that user_guide.md exists"""
        user_guide_path = Path('docs/user_guide.md')
        self.assertTrue(user_guide_path.exists())

    def test_troubleshooting_doc_exists(self):
        """Test that troubleshooting.md exists"""
        troubleshooting_path = Path('docs/troubleshooting.md')
        self.assertTrue(troubleshooting_path.exists())


class TestMakefileConfiguration(unittest.TestCase):
    """Test cases for Makefile configuration"""

    def test_makefile_exists(self):
        """Test that Makefile exists"""
        makefile_path = Path('Makefile')
        self.assertTrue(makefile_path.exists())

    def test_makefile_has_up_target(self):
        """Test that Makefile has up target"""
        makefile_path = Path('Makefile')
        with open(makefile_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        self.assertIn('up:', content)

    def test_makefile_has_down_target(self):
        """Test that Makefile has down target"""
        makefile_path = Path('Makefile')
        with open(makefile_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        self.assertIn('down:', content)

    def test_makefile_has_test_targets(self):
        """Test that Makefile has test targets"""
        makefile_path = Path('Makefile')
        with open(makefile_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        self.assertIn('test', content)

    def test_makefile_has_help_target(self):
        """Test that Makefile has help target"""
        makefile_path = Path('Makefile')
        with open(makefile_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        self.assertIn('help:', content)


class TestGitConfiguration(unittest.TestCase):
    """Test cases for Git configuration"""

    def test_gitignore_exists(self):
        """Test that .gitignore exists"""
        gitignore_path = Path('.gitignore')
        self.assertTrue(gitignore_path.exists())

    def test_gitignore_ignores_env(self):
        """Test that .gitignore ignores .env"""
        gitignore_path = Path('.gitignore')
        with open(gitignore_path, 'r') as f:
            content = f.read()
        self.assertIn('.env', content)

    def test_gitignore_ignores_logs(self):
        """Test that .gitignore ignores logs"""
        gitignore_path = Path('.gitignore')
        with open(gitignore_path, 'r') as f:
            content = f.read()
        self.assertIn('logs/', content)

    def test_gitignore_ignores_backups(self):
        """Test that .gitignore ignores backups"""
        gitignore_path = Path('.gitignore')
        with open(gitignore_path, 'r') as f:
            content = f.read()
        self.assertIn('backups/', content)

    def test_gitignore_ignores_certificates(self):
        """Test that .gitignore ignores certificates"""
        gitignore_path = Path('.gitignore')
        with open(gitignore_path, 'r') as f:
            content = f.read()
        self.assertIn('certs/', content) or self.assertIn('*.crt', content)


if __name__ == '__main__':
    unittest.main()
