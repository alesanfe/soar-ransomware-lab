import json
import logging
from typing import Any, Dict, Optional


class StructuredLogger:
    _SENSITIVE_KEYS = {"password", "api_key", "apikey", "token", "secret", "authorization"}

    def __init__(self, name: str = "soar_lab", level: int = logging.INFO) -> None:
        self._logger = logging.getLogger(name)
        self._level = level
        self._logger.setLevel(level)

    def setLevel(self, level: int) -> None:
        self._level = level
        self._logger.setLevel(level)

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if any(s in key.lower() for s in self._SENSITIVE_KEYS) else self._redact(val)
                for key, val in value.items()
            }
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        return value

    def _emit(self, level: int, msg: str, **kwargs: Any) -> None:
        context: Optional[Dict[str, Any]] = kwargs.pop("context", None)
        extra: Optional[Dict[str, Any]] = kwargs.pop("extra", None)

        if level < self._level and level != logging.DEBUG:
            return

        payload_extra: Dict[str, Any] = dict(extra) if extra else {}
        if context is not None:
            payload_extra["context"] = self._redact(context)

        level_method = {
            logging.DEBUG: self._logger.debug,
            logging.INFO: self._logger.info,
            logging.WARNING: self._logger.warning,
            logging.ERROR: self._logger.error,
            logging.CRITICAL: self._logger.critical,
        }.get(level, self._logger.info)

        if payload_extra:
            payload = json.dumps({"message": msg, **payload_extra})
        else:
            payload = msg

        if payload_extra:
            level_method(payload, extra=payload_extra, **kwargs)
        else:
            level_method(payload, **kwargs)

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._emit(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._emit(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._emit(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._emit(logging.ERROR, msg, **kwargs)

    def exception(self, msg: str, exc_info: Any = True, **kwargs: Any) -> None:
        kwargs.setdefault("exc_info", exc_info)
        self._emit(logging.ERROR, msg, **kwargs)
