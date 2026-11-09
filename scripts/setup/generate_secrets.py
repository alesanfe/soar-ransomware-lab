#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Secret Generator Service
Generates secure passwords, API keys, and tokens for the SOAR lab

Canonical implementation lives in ``soar_lab.security.secret_generator``;
this script re-exports it so standalone usage keeps working
(scripts -> src is the allowed dependency direction).
"""

from soar_lab.security.secret_generator import (
    SecretGeneratorService,
    generate_all_secrets,
    generate_api_key,
    generate_jwt_secret,
    generate_password,
    generate_secret_key,
    generate_token,
    generate_webhook_token,
    validate_secret_format,
)

__all__ = [
    "SecretGeneratorService",
    "generate_password",
    "generate_api_key",
    "generate_webhook_token",
    "generate_jwt_secret",
    "generate_secret_key",
    "generate_token",
    "validate_secret_format",
    "generate_all_secrets",
]
