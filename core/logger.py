"""
Centralized application logger — memory buffer + rotating file + live callback.
"""

import logging
import sys
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, List, Optional


_MAX_ENTRIES = 500


class _MemoryHandler(logging.Handler):
    """Stores recent log entries in a deque for in-app viewing."""

    def __init__(self, maxlen: int = _MAX_ENTRIES):
        super().__init__()
        self._entries: deque = deque(maxlen=maxlen)
        self._on_new_entry: Optional[Callable] = None
        self.setFormatter(logging.Formatter("%(asctime)s"))

    def emit(self, record: logging.LogRecord):
        entry = {
            "timestamp": self.formatter.formatTime(record, "%H:%M:%S") if self.formatter else record.asctime,
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        self._entries.append(entry)
        if self._on_new_entry:
            try:
                self._on_new_entry(entry)
            except Exception:
                pass

    def get_entries(self, level: Optional[str] = None) -> List[dict]:
        if level is None:
            return list(self._entries)
        return [e for e in self._entries if e["level"] == level.upper()]

    def clear(self):
        self._entries.clear()


_memory_handler: Optional[_MemoryHandler] = None


def install(log_file: Optional[Path] = None):
    """
    Set up root logger with memory + console + rotating file handlers.
    Call once at app startup.
    """
    global _memory_handler

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # Memory handler — captures everything for the in-app viewer
    _memory_handler = _MemoryHandler(maxlen=_MAX_ENTRIES)
    _memory_handler.setLevel(logging.DEBUG)
    _memory_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(_memory_handler)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(console)

    # Rotating file handler
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            fh = RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
            )
            root.addHandler(fh)
        except Exception:
            pass

    # Silence noisy third-party loggers
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("yt_dlp").setLevel(logging.WARNING)

    # Catch unhandled exceptions
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        root.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))

    sys.excepthook = _excepthook


def get_entries(level: Optional[str] = None) -> List[dict]:
    """Return in-memory log entries, optionally filtered by level name (e.g. 'ERROR')."""
    if _memory_handler is None:
        return []
    return _memory_handler.get_entries(level)


def clear():
    """Clear the in-memory log buffer."""
    if _memory_handler:
        _memory_handler.clear()


def set_on_new_entry(callback: Optional[Callable]):
    """Register a callback fired on each new log entry (called from logging thread)."""
    if _memory_handler:
        _memory_handler._on_new_entry = callback
