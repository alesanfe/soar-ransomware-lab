#!/usr/bin/env python3
"""SOAR Ransomware Lab - Centralized Logging Configuration.

Single place to configure logging for all modules.
"""

import json
import logging
import logging.config
import logging.handlers
import os
import re
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any

from soar_lab.common.trace_context import get_trace_id

_TEXT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_JSON_FORMAT = (
    '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s",'
    '"module":"%(module)s","function":"%(funcName)s","line":%(lineno)d,'
    '"message":"%(message)s"}'
)
_DATEFMT = "%Y-%m-%dT%H:%M:%S"

_LOGGING_YAML = Path(__file__).parents[3] / "infra" / "logging" / "logging.yaml"


class _JsonFormatter(logging.Formatter):
    """Serialize log records as single-line JSON with proper escaping.

    A %-style JSON template produces invalid JSON whenever a message or
    field contains quotes or newlines, so the record is serialized with
    :func:`json.dumps` instead.
    """

    def format(self, record: logging.LogRecord) -> str:

        payload = {
            "timestamp": self.formatTime(record, _DATEFMT),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        # BL-OBS-001: correlation — every record emitted inside a request
        # scope carries the request's trace_id so logs join across layers.
        trace_id = get_trace_id()
        if trace_id:
            payload["trace_id"] = trace_id
        # BL-OBS-002: structured context attached via ``extra={"context": ...}``
        # (StructuredLogger or a direct logger call) lands in the payload
        # instead of being silently dropped.
        context = getattr(record, "context", None)
        if isinstance(context, dict) and context:
            payload["context"] = context
        return json.dumps(payload, default=str)


class SecretRedactorFilter(logging.Filter):
    """LOG-001: redact credentials/tokens from every emitted log record.

    A leaked ``Authorization:`` header or JWT in a log line is a real
    secret-disclosure vector (logs are shipped to Loki/ELK). Patterns
    cover Bearer/JWT tokens, API keys, passwords, cookies and common
    ``*_TOKEN``/``*_KEY`` env-style values.
    """

    _PATTERNS: tuple[re.Pattern[str], ...] = (
        # Bearer <token> / Authorization: Bearer <token>
        re.compile(r"(?i)(bearer\s+)[A-Za-z0-9_\-\.=]+"),
        # JWT-shaped tokens (three base64url segments)
        re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"),
        # key=value secrets — optional auth-scheme keyword is part of the
        # credential ("Authorization=Basic QWxh..." redacts ALL of it)
        re.compile(
            r"(?i)\b(api[_-]?key|apikey|secret|password|passwd|token|"
            r"auth|authorization|x-service-token|cookie|set-cookie)"
            r"([\s]*[=:\"']+[\s]*)(\s*(?:basic|bearer|digest|token)\s+)?"
            # bare %-format placeholders (%s, %d, %(name)s…) are not secrets —
            # eating them orphans record.args and breaks msg formatting
            r"(?!%[a-zA-Z(])[^\s,\"']+"
        ),
        # AWS-style access keys
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    )

    def _redact(self, text: str) -> str:
        out = text
        out = self._PATTERNS[0].sub(r"\1***REDACTED***", out)
        out = self._PATTERNS[1].sub("***REDACTED***", out)
        out = self._PATTERNS[2].sub(r"\1\2***REDACTED***", out)
        out = self._PATTERNS[3].sub("***REDACTED***", out)
        return out

    def filter(self, record: logging.LogRecord) -> bool:
        # redaction must never break logging
        with suppress(Exception):
            record.msg = self._redact(str(record.msg))
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        k: self._redact(v) if isinstance(v, str) else v
                        for k, v in record.args.items()
                    }
                else:
                    # Preserve non-str arg types — int/float args feed
                    # %-format placeholders like %d and must stay typed.
                    record.args = tuple(
                        self._redact(a) if isinstance(a, str) else a for a in record.args
                    )
            if record.exc_text:
                record.exc_text = self._redact(record.exc_text)
            # BL-OBS-002: context dicts can smuggle credentials past the
            # message-level redaction — scrub string values recursively.
            context = getattr(record, "context", None)
            if isinstance(context, dict):
                record.context = self._redact_value(context)
        return True

    def _redact_value(self, value: Any) -> Any:
        """Recursively redact string leaves in dicts/lists (context payloads)."""
        if isinstance(value, str):
            return self._redact(value)
        if isinstance(value, dict):
            return {k: self._redact_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return type(value)(self._redact_value(v) for v in value)
        return value


_REDACTOR = SecretRedactorFilter()


def _make_formatter(log_format: str) -> logging.Formatter:
    """Create a logging formatter for the given format name.

    Args:
        log_format: ``"json"`` for JSON output, any other value for text.

    Returns:
        A configured ``logging.Formatter`` instance.
    """
    if log_format.lower() == "json":
        return _JsonFormatter()
    return logging.Formatter(fmt=_TEXT_FORMAT, datefmt=_DATEFMT)


def _handler_key(handler: logging.Handler) -> tuple:
    """Identity key for deduplicating handlers.

    Type-only comparison dropped a second ``RotatingFileHandler`` pointed
    at a different file, so key by what makes a handler distinct: target
    file for file handlers, target stream for stream handlers, class
    otherwise.
    """
    base_filename = getattr(handler, "baseFilename", None)
    if base_filename is not None:
        return ("file", base_filename)
    stream = getattr(handler, "stream", None)
    if stream is not None:
        return ("stream", id(stream))
    return ("class", type(handler))


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "text",
    log_dir: Path | None = None,
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
        try:
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
        except OSError as exc:
            # Non-root containers can hit unwritable bind-mounted log dirs
            # (created by a previous root-run). File logging is best-effort —
            # never let it crash the process; console output still flows.
            console.handle(
                logging.LogRecord(
                    __name__,
                    logging.WARNING,
                    __file__,
                    0,
                    f"File logging disabled (cannot write {log_dir}): {exc}",
                    (),
                    None,
                )
            )

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=level, handlers=handlers)
    else:
        root.setLevel(level)
        for handler in handlers:
            if not any(_handler_key(handler) == _handler_key(h) for h in root.handlers):
                root.addHandler(handler)

    for handler in root.handlers:
        handler.setFormatter(formatter)
        handler.addFilter(_REDACTOR)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    _apply_level_overrides()


def _apply_level_overrides() -> None:
    """Apply per-logger level overrides from ``SOAR_LOG_OVERRIDES``.

    Format: comma-separated ``logger=LEVEL`` pairs, e.g.
    ``SOAR_LOG_OVERRIDES=soar_lab.infrastructure.messaging=DEBUG,noisy=ERROR``.
    Lets operators silence or amplify one module without raising the
    global ``LOG_LEVEL``. Invalid pairs are skipped with a warning.
    """
    raw = os.getenv("SOAR_LOG_OVERRIDES", "").strip()
    if not raw:
        return
    for pair in raw.split(","):
        pair = pair.strip()
        if "=" not in pair:
            continue
        name, level_name = pair.rsplit("=", 1)
        level = getattr(logging, level_name.strip().upper(), None)
        if not name.strip() or not isinstance(level, int):
            logging.getLogger(__name__).warning("Invalid SOAR_LOG_OVERRIDES entry: %r", pair)
            continue
        logging.getLogger(name.strip()).setLevel(level)


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
