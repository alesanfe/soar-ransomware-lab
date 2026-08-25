"""Command-line interface for the SOAR Ransomware Lab."""

import argparse
import json
from datetime import UTC, datetime

from soar_lab.common.constants import (
    ENV_CORTEX_API_KEY,
    ENV_EDR_SIM_TOKEN,
    ENV_ELASTIC_PASSWORD,
    ENV_FIREWALL_SIM_TOKEN,
    ENV_JWT_ALGORITHM,
    ENV_JWT_EXPIRATION_MINUTES,
    ENV_JWT_SECRET_KEY,
    ENV_POSTGRES_PASSWORD,
    ENV_REDIS_PASSWORD,
    ENV_SHUFFLE_API_KEY,
    ENV_SHUFFLE_DEFAULT_PASSWORD,
    ENV_SIEM_WEBHOOK_TOKEN,
    ENV_THEHIVE_API_KEY,
    JWT_ALGORITHM_DEFAULT,
    SECRET_LENGTH_API_KEY,
    SECRET_LENGTH_JWT,
    SECRET_LENGTH_PASSWORD,
    SECRET_LENGTH_TOKEN,
    SECRET_LENGTH_WEBHOOK_TOKEN,
)
from soar_lab.config.logging import configure_from_env

__all__ = ["configure_from_env", "main"]


def main() -> int:
    """Entry point for the ``soar-lab`` CLI.

    Parses subcommands (version, api, generate-iocs, generate-secrets) and
    dispatches to the appropriate handler.

    Returns:
        Process exit code (0 on success).
    """
    configure_from_env()
    parser = argparse.ArgumentParser(
        prog="soar-lab", description="SOAR Ransomware Lab command line interface"
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Show package version")

    api_parser = subparsers.add_parser("api", help="Run the management API")
    api_parser.add_argument("--host", default="127.0.0.1")
    api_parser.add_argument("--port", type=int, default=8000)

    # Generate IOCs command
    iocs_parser = subparsers.add_parser("generate-iocs", help="Generate simulated IOCs")
    iocs_parser.add_argument("--output", "-o", help="Output file path")
    iocs_parser.add_argument(
        "--count", "-c", type=int, default=5, help="Number of IOCs to generate"
    )

    # Generate secrets command
    secrets_parser = subparsers.add_parser("generate-secrets", help="Generate secure secrets")
    secrets_parser.add_argument("--output", "-o", help="Output file path (JSON format)")
    secrets_parser.add_argument("--env", action="store_true", help="Output in .env format")

    args = parser.parse_args()

    if args.command == "version":
        from soar_lab import __version__

        print(__version__)
        return 0

    if args.command == "api":
        import uvicorn

        from soar_lab.interfaces.api.composition import create_app as create_composed_app

        app_instance = create_composed_app()
        uvicorn.run(app_instance, host=args.host, port=args.port)
        return 0

    if args.command == "generate-iocs":
        from soar_lab.config.settings import create_settings
        from soar_lab.domain.services.ioc_generator import SimulatedIOCGenerator
        from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
        from soar_lab.infrastructure.filesystem_storage import FilesystemStorage

        # Create minimal composition for IOC generation
        settings = create_settings()
        config_provider = InfrastructureConfigProvider(settings)
        from pathlib import Path

        base_dir_str = config_provider.get("base_dir")
        if not base_dir_str:
            raise ValueError("base_dir must be provided in config_provider")
        Path(base_dir_str)
        file_system = FilesystemStorage(config_provider=config_provider)
        ioc_generator = SimulatedIOCGenerator()

        from soar_lab.data.generate_iocs import IOCPackageGenerator

        generator = IOCPackageGenerator(ioc_generator, file_system)
        iocs = generator.create_ioc_package(output_file=args.output, count=args.count)

        if not args.output:
            print(json.dumps(iocs, indent=4))
        else:
            print(f"IOC package created: {args.output}")
        return 0

    if args.command == "generate-secrets":
        from scripts.setup.generate_secrets import (  # pylint: disable=import-error,no-name-in-module
            SecretGeneratorService,
        )
        from soar_lab.config.settings import create_settings
        from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
        from soar_lab.infrastructure.filesystem_storage import FilesystemStorage

        # Create minimal composition for secret generation
        settings = create_settings()
        config_provider = InfrastructureConfigProvider(settings)
        file_system = FilesystemStorage(config_provider=config_provider)
        secret_service = SecretGeneratorService(file_system)

        secrets_data = {
            "thehive_api_key": secret_service.generate_api_key(SECRET_LENGTH_PASSWORD),
            "cortex_api_key": secret_service.generate_api_key(SECRET_LENGTH_PASSWORD),
            "shuffle_api_key": secret_service.generate_api_key(SECRET_LENGTH_PASSWORD),
            "shuffle_webhook_token": secret_service.generate_webhook_token(
                SECRET_LENGTH_WEBHOOK_TOKEN
            ),
            "jwt_secret": secret_service.generate_jwt_secret(SECRET_LENGTH_JWT),
            "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }

        if args.output:
            file_system.write(args.output, json.dumps(secrets_data, indent=4).encode())
            print(f"Secrets generated in {args.output}")
        elif args.env:
            secrets_dict = {
                ENV_ELASTIC_PASSWORD: secret_service.generate_password(SECRET_LENGTH_PASSWORD),
                ENV_SHUFFLE_DEFAULT_PASSWORD: secret_service.generate_password(
                    SECRET_LENGTH_PASSWORD
                ),
                ENV_SHUFFLE_API_KEY: secret_service.generate_api_key(SECRET_LENGTH_API_KEY),
                "THEHIVE_SECRET": secret_service.generate_secret_key(SECRET_LENGTH_PASSWORD),
                ENV_THEHIVE_API_KEY: secret_service.generate_api_key(SECRET_LENGTH_API_KEY),
                "CORTEX_SECRET": secret_service.generate_secret_key(SECRET_LENGTH_PASSWORD),
                ENV_CORTEX_API_KEY: secret_service.generate_api_key(SECRET_LENGTH_API_KEY),
                ENV_SIEM_WEBHOOK_TOKEN: secret_service.generate_token(SECRET_LENGTH_TOKEN),
                ENV_EDR_SIM_TOKEN: secret_service.generate_token(SECRET_LENGTH_TOKEN),
                ENV_FIREWALL_SIM_TOKEN: secret_service.generate_token(SECRET_LENGTH_TOKEN),
                ENV_POSTGRES_PASSWORD: secret_service.generate_password(SECRET_LENGTH_PASSWORD),
                ENV_REDIS_PASSWORD: secret_service.generate_password(SECRET_LENGTH_PASSWORD),
                ENV_JWT_SECRET_KEY: secret_service.generate_jwt_secret(SECRET_LENGTH_JWT),
                ENV_JWT_EXPIRATION_MINUTES: "60",
                ENV_JWT_ALGORITHM: JWT_ALGORITHM_DEFAULT,
            }
            for key, value in secrets_dict.items():
                print(f"{key}={value}")
            print("# Redirect these values to your .env.full file, for example:")
            print("#   soar-lab generate-secrets --env > .env.full")
            print("# DO NOT commit the .env file to version control!")
        else:
            print(json.dumps(secrets_data, indent=4))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
