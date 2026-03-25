"""File + in-memory logger for Yuki backend."""

import logging
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Optional

_memory: deque = deque(maxlen=500)
_callback: Optional[Callable] = None

APP_LOGGER = "yuki"


class _MemoryHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        entry = {
            "level": record.levelname,
            "module": record.name,
            "message": self.format(record),
            "timestamp": self.formatter.formatTime(record) if self.formatter else "",
        }
        _memory.append(entry)
        if _callback:
            try:
                _callback(entry)
            except Exception:
                pass


def setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # In-memory handler
    mh = _MemoryHandler()
    mh.setLevel(logging.DEBUG)
    mh.setFormatter(fmt)
    root.addHandler(mh)

    # Silence noisy libraries
    for noisy in ("PIL", "urllib3", "requests", "yt_dlp", "spotdl",
                  "httpx", "httpcore", "multipart",
                  "sse_starlette", "sse_starlette.sse"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    # ConnectionResetError on SSE disconnect is normal — silence asyncio noise
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)


def get_entries() -> list:
    return list(_memory)


def set_on_new_entry(cb: Optional[Callable]) -> None:
    global _callback
    _callback = cb
