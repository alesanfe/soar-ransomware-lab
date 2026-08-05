#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Centralized Logging Configuration
Single place to configure logging for all modules.
"""

import logging.config
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

import logging

_TEXT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_JSON_FORMAT = (
    '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s",'
    '"module":"%(module)s","function":"%(funcName)s","line":%(lineno)d,'
    '"message":"%(message)s"}'
)
_DATEFMT = "%Y-%m-%dT%H:%M:%S"

_LOGGING_YAML = Path(__file__).parents[3] / "infra" / "logging" / "logging.yaml"


def _make_formatter(log_format: str) -> logging.Formatter:
    fmt = _JSON_FORMAT if log_format.lower() == "json" else _TEXT_FORMAT
    return logging.Formatter(fmt=fmt, datefmt=_DATEFMT)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "text",
    log_dir: Optional[Path] = None,
    log_filename: str = "soar_lab.log",
) -> None:
    """Configure logging for the entire application.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format — ``"json"`` for structured JSON, any other
            value for human-readable text.
        log_dir: Directory for rotating log files. If None, only console
            logging is used.
        log_filename: Name of the log file when *log_dir* is provided.
    """
    if log_level is None:
        log_level = "INFO"
    if log_format is None:
        log_format = "text"
    level = getattr(logging, log_level.upper(), logging.INFO)
    formatter = _make_formatter(log_format)

    handlers: list[logging.Handler] = []

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    handlers.append(console)

    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / log_filename,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=level, handlers=handlers)
    else:
        root.setLevel(level)
        for handler in handlers:
            if not any(type(handler) is type(h) for h in root.handlers):
                root.addHandler(handler)

    for handler in root.handlers:
        handler.setFormatter(formatter)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def configure_from_env() -> None:
    """Bootstrap logging from environment variables (LOG_LEVEL, LOG_FORMAT).

    Convenience wrapper called at process start before any other import
    that might trigger logging.
    """
    setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_format=os.getenv("LOG_FORMAT", "text"),
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Args:
        name: Typically ``__name__`` of the calling module.
    """
    return logging.getLogger(name)
