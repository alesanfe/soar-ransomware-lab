import argparse
import json
from datetime import datetime, timezone


def main() -> int:
    parser = argparse.ArgumentParser(prog="soar-lab", description="SOAR Ransomware Lab command line interface")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("version", help="Show package version")

    api_parser = subparsers.add_parser("api", help="Run the management API")
    api_parser.add_argument("--host", default="127.0.0.1")
    api_parser.add_argument("--port", type=int, default=8000)

    # Generate IOCs command
    iocs_parser = subparsers.add_parser("generate-iocs", help="Generate simulated IOCs")
    iocs_parser.add_argument("--output", "-o", help="Output file path")
    iocs_parser.add_argument("--count", "-c", type=int, default=5, help="Number of IOCs to generate")

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
        from soar_lab.api.composition import create_app as create_composed_app
        app_instance = create_composed_app()
        uvicorn.run(app_instance, host=args.host, port=args.port)
        return 0

    if args.command == "generate-iocs":
        from soar_lab.domain.ioc_generator import SimulatedIOCGenerator
        from soar_lab.infrastructure.filesystem_storage import FilesystemStorage
        from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
        from soar_lab.config.settings import create_settings

        # Create minimal composition for IOC generation
        settings = create_settings()
        config_provider = InfrastructureConfigProvider(settings)
        from pathlib import Path
        base_dir_str = config_provider.get('base_dir')
        if not base_dir_str:
            raise ValueError("base_dir must be provided in config_provider")
        base_dir = Path(base_dir_str)
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
        from soar_lab.services.generate_secrets import SecretGeneratorService
        from soar_lab.infrastructure.filesystem_storage import FilesystemStorage
        from soar_lab.infrastructure.config_provider import InfrastructureConfigProvider
        from soar_lab.config.settings import create_settings

        # Create minimal composition for secret generation
        settings = create_settings()
        config_provider = InfrastructureConfigProvider(settings)
        file_system = FilesystemStorage(config_provider=config_provider)
        secret_service = SecretGeneratorService(file_system)

        secrets_data = {
            'thehive_api_key': secret_service.generate_api_key(32),
            'cortex_api_key': secret_service.generate_api_key(32),
            'shuffle_api_key': secret_service.generate_api_key(32),
            'shuffle_webhook_token': secret_service.generate_webhook_token(64),
            'jwt_secret': secret_service.generate_jwt_secret(64),
            'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }

        if args.output:
            file_system.write_file(args.output, json.dumps(secrets_data, indent=4))
            print(f"Secrets generated in {args.output}")
        elif args.env:
            secrets_dict = {
                'ELASTIC_PASSWORD': secret_service.generate_password(32),
                'SHUFFLE_DEFAULT_PASSWORD': secret_service.generate_password(32),
                'SHUFFLE_DEFAULT_APIKEY': secret_service.generate_api_key(64),
                'THEHIVE_SECRET': secret_service.generate_secret_key(32),
                'THEHIVE_API_KEY': secret_service.generate_api_key(64),
                'CORTEX_SECRET': secret_service.generate_secret_key(32),
                'CORTEX_API_KEY': secret_service.generate_api_key(64),
                'SIEM_WEBHOOK_TOKEN': secret_service.generate_token(48),
                'EDR_SIM_TOKEN': secret_service.generate_token(48),
                'FIREWALL_SIM_TOKEN': secret_service.generate_token(48),
                'POSTGRES_PASSWORD': secret_service.generate_password(32),
                'REDIS_PASSWORD': secret_service.generate_password(32),
            }
            for key, value in secrets_dict.items():
                print(f"{key}={value}")
            print("Copy these values to your docker/.env file")
            print("DO NOT commit the .env file to version control!")
        else:
            print(json.dumps(secrets_data, indent=4))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
