"""ChitraguptLogger — Singleton JSON logger with console and rotating file output.

Provides a single, project-wide logger instance that writes structured JSON to
both stdout and ``logs/chitragupt.log`` (with automatic rotation).
"""

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional


class _JsonFormatter(logging.Formatter):
    """Format every log record as a single-line JSON object.

    Standard fields (timestamp, level, logger, message, module, func_name)
    are always present.  Any *extra* key-value pairs passed via the ``extra``
    parameter of a logging call are merged into the JSON object automatically,
    giving callers an easy way to attach operation-specific context such as
    ``user_id``, ``chat_id``, ``command``, ``action``, ``target_id``, etc.

    Example::

        logger.info(
            "User kicked",
            extra={"user_id": 100, "target_id": 999, "chat_id": 42, "command": "/kick"},
        )

    Produces::

        {"timestamp": "…", "level": "INFO", …, "user_id": 100, "target_id": 999, …}
    """

    # Keys that belong to the standard LogRecord — everything else is extra.
    _BUILTIN_ATTRS: frozenset[str] = frozenset(vars(logging.LogRecord(
        name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None,
    )))

    def format(self, record: logging.LogRecord) -> str:
        """Serialize *record* to a JSON string with IAM-relevant keys."""
        log_entry: dict = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func_name": record.funcName,
        }

        # Merge caller-supplied extra fields into the JSON payload.
        for key, value in record.__dict__.items():
            if key not in self._BUILTIN_ATTRS and key not in log_entry:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ChitraguptLogger:
    """Singleton logger with dual handlers (console + rotating file).

    Usage::

        from core.logger import ChitraguptLogger

        logger = ChitraguptLogger.get_logger()
        logger.info("Bot started")
    """

    _instance: Optional["ChitraguptLogger"] = None
    _logger: Optional[logging.Logger] = None

    # Rotation settings
    _LOG_DIR: str = "logs"
    _LOG_FILE: str = "chitragupt.log"
    _MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB
    _BACKUP_COUNT: int = 5

    def __new__(cls, level: int = logging.INFO) -> "ChitraguptLogger":
        """Ensure only one instance is ever created (Singleton)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger(level)
        return cls._instance

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_logger(self, level: int) -> None:
        """Create the underlying :class:`logging.Logger` and attach handlers."""
        self._logger = logging.getLogger("chitragupt")
        self._logger.setLevel(level)

        # Avoid duplicate handlers if the module is reloaded.
        if self._logger.handlers:
            return

        formatter = _JsonFormatter()

        # --- Console handler (StreamHandler) ---
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        self._logger.addHandler(stream_handler)

        # --- Rotating file handler ---
        os.makedirs(self._LOG_DIR, exist_ok=True)
        log_path = os.path.join(self._LOG_DIR, self._LOG_FILE)

        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=self._MAX_BYTES,
            backupCount=self._BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def get_logger(level: int = logging.INFO) -> logging.Logger:
        """Return the shared :class:`logging.Logger` instance.

        Creates the singleton on first call; subsequent calls return the
        same logger regardless of the *level* argument.
        """
        instance = ChitraguptLogger(level)
        assert instance._logger is not None  # guaranteed by __new__
        return instance._logger

    def cleanup(self) -> None:
        """Flush and close all handlers attached to the logger."""
        if self._logger is None:
            return
        for handler in list(self._logger.handlers):
            handler.flush()
            handler.close()
            self._logger.removeHandler(handler)

    def __del__(self) -> None:
        """Best-effort cleanup on garbage collection."""
        self.cleanup()
