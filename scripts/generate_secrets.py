#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Secret Generator
Generates secure passwords, API keys, and tokens for the SOAR lab
"""

import secrets
import string
import sys
from pathlib import Path


def generate_password(length: int = 32) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_api_key(length: int = 64) -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(length)


def generate_secret_key(length: int = 32) -> str:
    """Generate a secret key for applications"""
    return secrets.token_hex(length)


def generate_token(length: int = 48) -> str:
    """Generate a secure token"""
    return secrets.token_urlsafe(length)


def main():
    """Generate all secrets and output to stdout or file"""
    print("Generating secure secrets for SOAR Ransomware Lab...")
    print("=" * 60)
    
    secrets_dict = {
        'ELASTIC_PASSWORD': generate_password(32),
        'SHUFFLE_DEFAULT_PASSWORD': generate_password(32),
        'SHUFFLE_DEFAULT_APIKEY': generate_api_key(64),
        'THEHIVE_SECRET': generate_secret_key(32),
        'THEHIVE_API_KEY': generate_api_key(64),
        'CORTEX_SECRET': generate_secret_key(32),
        'CORTEX_API_KEY': generate_api_key(64),
        'SIEM_WEBHOOK_TOKEN': generate_token(48),
        'EDR_SIM_TOKEN': generate_token(48),
        'FIREWALL_SIM_TOKEN': generate_token(48),
        'POSTGRES_PASSWORD': generate_password(32),
        'REDIS_PASSWORD': generate_password(32),
    }
    
    # Output as .env format
    for key, value in secrets_dict.items():
        print(f"{key}={value}")
    
    print("=" * 60)
    print("Copy these values to your docker/.env file")
    print("DO NOT commit the .env file to version control!")
    
    # Optionally write to file
    if len(sys.argv) > 1 and sys.argv[1] == '--output-file':
        env_file = Path('docker/.env')
        with open(env_file, 'a') as f:
            f.write("\n# === Auto-generated secrets ===\n")
            for key, value in secrets_dict.items():
                f.write(f"{key}={value}\n")
        print(f"\nSecrets appended to {env_file}")


if __name__ == '__main__':
    main()
