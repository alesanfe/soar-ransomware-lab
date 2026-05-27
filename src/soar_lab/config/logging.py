#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Centralized Logging Configuration
Single place to configure logging for all modules.
"""

import sys
from pathlib import Path
from typing import Optional

import logging


def setup_logging(
        log_level: str = "INFO",
        log_dir: Optional[Path] = None,
        log_filename: str = "soar_lab.log",
) -> None:
    """Configure logging for the entire application.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files. If None, only console logging is used.
        log_filename: Name of the log file when log_dir is provided.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_dir / log_filename))

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=handlers,
        )
    else:
        root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        for handler in handlers:
            if not any(type(handler) == type(h) for h in root.handlers):
                root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Args:
        name: Typically __name__ of the calling module.
    """
    return logging.getLogger(name)
