"""Structured logging utility with sensitive-data redaction and trace ID injection."""

import logging
from typing import Any

from soar_lab.common.trace_context import get_trace_id

__all__ = ["StructuredLogger"]


class StructuredLogger:
    """Logger that emits JSON-structured messages with automatic redaction of sensitive fields."""

    _SENSITIVE_KEYS = {"password", "api_key", "apikey", "token", "secret", "authorization"}

    def __init__(self, name: str = "soar_lab", level: int = logging.INFO) -> None:
        """Initialize the StructuredLogger with the given name and level.

        Args:
            name: Logger name used to retrieve the underlying ``logging.Logger``.
            level: Initial logging level (e.g. ``logging.INFO``).
        """
        self._logger = logging.getLogger(name)
        self._level = level
        self._logger.setLevel(level)

    def setLevel(self, level: int) -> None:
        """Set the logging level for both the wrapper and underlying logger.

        Args:
            level: Logging level to apply (e.g. ``logging.DEBUG``).
        """
        self._level = level
        self._logger.setLevel(level)

    def _redact(self, value: Any) -> Any:
        """Recursively redact sensitive values within nested dicts and lists.

        Args:
            value: The value to redact (dict, list, or scalar).

        Returns:
            A copy of *value* with sensitive fields replaced by ``"[REDACTED]"``.
        """
        if isinstance(value, dict):
            return {
                key: (
                    "[REDACTED]"
                    if any(s in key.lower() for s in self._SENSITIVE_KEYS)
                    else self._redact(val)
                )
                for key, val in value.items()
            }
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        return value

    def _emit(self, level: int, msg: str, **kwargs: Any) -> None:
        """Emit a log message at the given level with structured context.

        Args:
            level: Logging level for this message.
            msg: Human-readable message text.
            **kwargs: Additional keyword arguments; ``context`` and ``extra``
                are extracted into the JSON payload, the rest are forwarded to
                the underlying logger call.
        """
        context: dict[str, Any] | None = kwargs.pop("context", None)
        extra: dict[str, Any] | None = kwargs.pop("extra", None)

        if not self._logger.isEnabledFor(level):
            return

        # Both ``extra`` and ``context`` get redacted — a secret passed
        # through extra= used to ship in clear text.
        payload_extra: dict[str, Any] = self._redact(dict(extra)) if extra else {}
        if context is not None:
            payload_extra["context"] = self._redact(context)

        # Inject trace_id as a record attribute so correlation survives
        # non-JSON formatters and record-level inspection (caplog, filters).
        # The canonical _JsonFormatter additionally reads the contextvar.
        trace_id = get_trace_id()
        if trace_id is not None and "trace_id" not in payload_extra:
            payload_extra["trace_id"] = trace_id

        level_method = {
            logging.DEBUG: self._logger.debug,
            logging.INFO: self._logger.info,
            logging.WARNING: self._logger.warning,
            logging.ERROR: self._logger.error,
            logging.CRITICAL: self._logger.critical,
        }.get(level, self._logger.info)

        # BL-OBS-002: the message stays a plain string — structured fields
        # travel in the record's ``extra`` namespace so the canonical
        # _JsonFormatter emits ONE JSON object (no double-encoding) and the
        # SecretRedactorFilter can scrub the context before it ships.
        if payload_extra:
            level_method(msg, extra=payload_extra, **kwargs)
        else:
            level_method(msg, **kwargs)

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log a DEBUG-level structured message.

        Args:
            msg: Human-readable message text.
            **kwargs: Additional context forwarded to ``_emit``.
        """
        self._emit(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        """Log an INFO-level structured message.

        Args:
            msg: Human-readable message text.
            **kwargs: Additional context forwarded to ``_emit``.
        """
        self._emit(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log a WARNING-level structured message.

        Args:
            msg: Human-readable message text.
            **kwargs: Additional context forwarded to ``_emit``.
        """
        self._emit(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log an ERROR-level structured message.

        Args:
            msg: Human-readable message text.
            **kwargs: Additional context forwarded to ``_emit``.
        """
        self._emit(logging.ERROR, msg, **kwargs)

    def exception(self, msg: str, exc_info: Any = True, **kwargs: Any) -> None:
        """Log an ERROR-level message with exception information attached.

        Args:
            msg: Human-readable message text.
            exc_info: Exception info to attach; defaults to ``True`` for
                automatic capture by the logging framework.
            **kwargs: Additional context forwarded to ``_emit``.
        """
        kwargs.setdefault("exc_info", exc_info)
        self._emit(logging.ERROR, msg, **kwargs)
