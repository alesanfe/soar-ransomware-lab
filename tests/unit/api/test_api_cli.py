"""Unit tests for api.cli module."""

from unittest.mock import Mock, patch

import pytest

from soar_lab.interfaces.api.cli import main


class TestMain:
    """Tests for main function."""

    def test_main_version_command(self, capsys):
        """Test main with version command."""
        with (
            patch("soar_lab.interfaces.api.cli.configure_from_env"),
            patch("soar_lab.interfaces.api.cli.argparse.ArgumentParser.parse_args") as mock_parse,
        ):
            mock_args = Mock()
            mock_args.command = "version"
            mock_parse.return_value = mock_args

            with patch("soar_lab.__version__", "1.0.0"):
                result = main()

                captured = capsys.readouterr()
                assert "1.0.0" in captured.out
                assert result == 0

    def test_main_no_command(self, capsys):
        """Test main with no command (prints help)."""
        with (
            patch("soar_lab.interfaces.api.cli.configure_from_env"),
            patch("soar_lab.interfaces.api.cli.argparse.ArgumentParser.parse_args") as mock_parse,
        ):
            mock_args = Mock()
            mock_args.command = None
            mock_parse.return_value = mock_args

            result = main()

            assert result == 0

    def test_main_generate_iocs_missing_base_dir(self):
        """Test generate-iocs command when base_dir is not provided."""
        with patch("soar_lab.interfaces.api.cli.configure_from_env"):
            with patch(
                "soar_lab.interfaces.api.cli.argparse.ArgumentParser.parse_args"
            ) as mock_parse:
                mock_args = Mock()
                mock_args.command = "generate-iocs"
                mock_args.output = None
                mock_args.count = 5
                mock_parse.return_value = mock_args

                with patch("soar_lab.config.settings.create_settings") as mock_settings:
                    mock_settings.return_value = {}

                    with patch(
                        "soar_lab.infrastructure.config_provider.InfrastructureConfigProvider"
                    ) as mock_config_provider:
                        mock_config = Mock()
                        mock_config.get.return_value = None  # base_dir is None
                        mock_config_provider.return_value = mock_config

                        with pytest.raises(ValueError):
                            main()

    def test_main_generate_secrets_env_format(self, capsys):
        """Test generate-secrets command with env format."""
        with patch("soar_lab.interfaces.api.cli.configure_from_env"):
            with patch(
                "soar_lab.interfaces.api.cli.argparse.ArgumentParser.parse_args"
            ) as mock_parse:
                mock_args = Mock()
                mock_args.command = "generate-secrets"
                mock_args.output = None
                mock_args.env = True
                mock_parse.return_value = mock_args

                with patch("soar_lab.config.settings.create_settings") as mock_settings:
                    mock_settings.return_value = {}

                    with patch(
                        "soar_lab.infrastructure.config_provider.InfrastructureConfigProvider"
                    ) as mock_config_provider:
                        mock_config = Mock()
                        mock_config.get.return_value = "/tmp/test"
                        mock_config_provider.return_value = mock_config

                        with patch(
                            "soar_lab.infrastructure.filesystem_storage.FilesystemStorage"
                        ) as mock_storage:
                            mock_storage.return_value = Mock()

                            with patch(
                                "scripts.setup.generate_secrets.SecretGeneratorService"
                            ) as mock_secret_service:
                                mock_service = Mock()
                                mock_service.generate_api_key.return_value = "test_api_key"
                                mock_service.generate_webhook_token.return_value = "test_token"
                                mock_service.generate_jwt_secret.return_value = "test_secret"
                                mock_service.generate_password.return_value = "test_pass"
                                mock_service.generate_secret_key.return_value = "test_key"
                                mock_service.generate_token.return_value = "test_token"
                                mock_secret_service.return_value = mock_service

                                result = main()

                                captured = capsys.readouterr()
                                assert "ELASTIC_PASSWORD=" in captured.out
                                assert result == 0

    def test_main_api_command(self):
        """Test api command."""
        with patch("soar_lab.interfaces.api.cli.configure_from_env"):
            with patch(
                "soar_lab.interfaces.api.cli.argparse.ArgumentParser.parse_args"
            ) as mock_parse:
                mock_args = Mock()
                mock_args.command = "api"
                mock_args.host = "127.0.0.1"
                mock_args.port = 8000
                mock_parse.return_value = mock_args

                with patch("uvicorn.run") as mock_uvicorn:
                    with patch("soar_lab.interfaces.api.composition.create_app") as mock_create_app:
                        mock_app = Mock()
                        mock_create_app.return_value = mock_app

                        result = main()

                        assert result == 0
                        mock_uvicorn.assert_called_once()

    def test_main_generate_iocs_with_base_dir(self, capsys):
        """Test generate-iocs command with valid base_dir."""
        with patch("soar_lab.interfaces.api.cli.configure_from_env"):
            with patch(
                "soar_lab.interfaces.api.cli.argparse.ArgumentParser.parse_args"
            ) as mock_parse:
                mock_args = Mock()
                mock_args.command = "generate-iocs"
                mock_args.output = None
                mock_args.count = 5
                mock_parse.return_value = mock_args

                with patch("soar_lab.config.settings.create_settings") as mock_settings:
                    mock_settings_instance = Mock()
                    mock_settings.return_value = mock_settings_instance

                    with patch(
                        "soar_lab.infrastructure.config_provider.InfrastructureConfigProvider"
                    ) as mock_config_provider:
                        mock_config = Mock()
                        mock_config.get.return_value = "/tmp/test"
                        mock_config_provider.return_value = mock_config

                        with patch("pathlib.Path") as mock_path:
                            mock_path_instance = Mock()
                            mock_path.return_value = mock_path_instance

                            with patch(
                                "soar_lab.infrastructure.filesystem_storage.FilesystemStorage"
                            ) as mock_storage:
                                mock_storage.return_value = Mock()

                                with patch(
                                    "soar_lab.domain.services.ioc_generator.SimulatedIOCGenerator"
                                ) as mock_ioc_gen:
                                    mock_ioc_gen.return_value = Mock()

                                    with patch(
                                        "soar_lab.data.generate_iocs.IOCPackageGenerator"
                                    ) as mock_package_gen:
                                        mock_generator = Mock()
                                        mock_generator.create_ioc_package.return_value = {
                                            "test": "data"
                                        }
                                        mock_package_gen.return_value = mock_generator

                                        result = main()

                                        capsys.readouterr()
                                        assert result == 0

    def test_main_generate_iocs_with_output(self, capsys):
        """Test generate-iocs command with output file."""
        with patch("soar_lab.interfaces.api.cli.configure_from_env"):
            with patch(
                "soar_lab.interfaces.api.cli.argparse.ArgumentParser.parse_args"
            ) as mock_parse:
                mock_args = Mock()
                mock_args.command = "generate-iocs"
                mock_args.output = "/tmp/iocs.json"
                mock_args.count = 5
                mock_parse.return_value = mock_args

                with patch("soar_lab.config.settings.create_settings") as mock_settings:
                    mock_settings_instance = Mock()
                    mock_settings.return_value = mock_settings_instance

                    with patch(
                        "soar_lab.infrastructure.config_provider.InfrastructureConfigProvider"
                    ) as mock_config_provider:
                        mock_config = Mock()
                        mock_config.get.return_value = "/tmp/test"
                        mock_config_provider.return_value = mock_config

                        with patch("pathlib.Path") as mock_path:
                            mock_path_instance = Mock()
                            mock_path.return_value = mock_path_instance

                            with patch(
                                "soar_lab.infrastructure.filesystem_storage.FilesystemStorage"
                            ) as mock_storage:
                                mock_storage.return_value = Mock()

                                with patch(
                                    "soar_lab.domain.services.ioc_generator.SimulatedIOCGenerator"
                                ) as mock_ioc_gen:
                                    mock_ioc_gen.return_value = Mock()

                                    with patch(
                                        "soar_lab.data.generate_iocs.IOCPackageGenerator"
                                    ) as mock_package_gen:
                                        mock_generator = Mock()
                                        mock_generator.create_ioc_package.return_value = {
                                            "test": "data"
                                        }
                                        mock_package_gen.return_value = mock_generator

                                        result = main()

                                        captured = capsys.readouterr()
                                        assert "IOC package created" in captured.out
                                        assert result == 0

    def test_main_generate_secrets_with_output(self, capsys):
        """Test generate-secrets command with output file."""
        with patch("soar_lab.interfaces.api.cli.configure_from_env"):
            with patch(
                "soar_lab.interfaces.api.cli.argparse.ArgumentParser.parse_args"
            ) as mock_parse:
                mock_args = Mock()
                mock_args.command = "generate-secrets"
                mock_args.output = "/tmp/secrets.json"
                mock_args.env = False
                mock_parse.return_value = mock_args

                with patch("soar_lab.config.settings.create_settings") as mock_settings:
                    mock_settings_instance = Mock()
                    mock_settings.return_value = mock_settings_instance

                    with patch(
                        "soar_lab.infrastructure.config_provider.InfrastructureConfigProvider"
                    ) as mock_config_provider:
                        mock_config = Mock()
                        mock_config.get.return_value = "/tmp/test"
                        mock_config_provider.return_value = mock_config

                        with patch(
                            "soar_lab.infrastructure.filesystem_storage.FilesystemStorage"
                        ) as mock_storage:
                            mock_storage_instance = Mock()
                            mock_storage.return_value = mock_storage_instance

                            with patch(
                                "scripts.setup.generate_secrets.SecretGeneratorService"
                            ) as mock_secret_service:
                                mock_service = Mock()
                                mock_service.generate_api_key.return_value = "test_api_key"
                                mock_service.generate_webhook_token.return_value = "test_token"
                                mock_service.generate_jwt_secret.return_value = "test_secret"
                                mock_secret_service.return_value = mock_service

                                result = main()

                                captured = capsys.readouterr()
                                assert "Secrets generated" in captured.out
                                assert result == 0

    def test_main_generate_secrets_default_json(self, capsys):
        """Test generate-secrets command with default JSON output."""
        with patch("soar_lab.interfaces.api.cli.configure_from_env"):
            with patch(
                "soar_lab.interfaces.api.cli.argparse.ArgumentParser.parse_args"
            ) as mock_parse:
                mock_args = Mock()
                mock_args.command = "generate-secrets"
                mock_args.output = None
                mock_args.env = False
                mock_parse.return_value = mock_args

                with patch("soar_lab.config.settings.create_settings") as mock_settings:
                    mock_settings_instance = Mock()
                    mock_settings.return_value = mock_settings_instance

                    with patch(
                        "soar_lab.infrastructure.config_provider.InfrastructureConfigProvider"
                    ) as mock_config_provider:
                        mock_config = Mock()
                        mock_config.get.return_value = "/tmp/test"
                        mock_config_provider.return_value = mock_config

                        with patch(
                            "soar_lab.infrastructure.filesystem_storage.FilesystemStorage"
                        ) as mock_storage:
                            mock_storage.return_value = Mock()

                            with patch(
                                "scripts.setup.generate_secrets.SecretGeneratorService"
                            ) as mock_secret_service:
                                mock_service = Mock()
                                mock_service.generate_api_key.return_value = "test_api_key"
                                mock_service.generate_webhook_token.return_value = "test_token"
                                mock_service.generate_jwt_secret.return_value = "test_secret"
                                mock_secret_service.return_value = mock_service

                                result = main()

                                capsys.readouterr()
                                assert result == 0
