"""
JSON-based download history manager.
Thread-safe, auto-saves on every change, max 1000 entries.
"""

import csv
import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import HISTORY_FILE, MAX_HISTORY_ENTRIES

logger = logging.getLogger(__name__)


class HistoryManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._entries: List[dict] = []
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, entry: dict) -> dict:
        """Add a new history entry. Returns the saved entry with id and timestamp."""
        entry = dict(entry)
        entry.setdefault("id", str(uuid.uuid4()))
        entry.setdefault("downloaded_at", datetime.now().isoformat())
        with self._lock:
            self._entries.insert(0, entry)
            if len(self._entries) > MAX_HISTORY_ENTRIES:
                self._entries = self._entries[:MAX_HISTORY_ENTRIES]
            self._save()
        return entry

    def get_all(self) -> List[dict]:
        with self._lock:
            return list(self._entries)

    def get_recent(self, n: int) -> List[dict]:
        with self._lock:
            return self._entries[:n]

    def delete(self, entry_id: str):
        with self._lock:
            self._entries = [e for e in self._entries if e.get("id") != entry_id]
            self._save()

    def clear_all(self):
        with self._lock:
            self._entries = []
            self._save()

    def search(self, query: str) -> List[dict]:
        query = query.lower()
        with self._lock:
            return [
                e for e in self._entries
                if query in (e.get("title") or "").lower()
                or query in (e.get("artist") or "").lower()
                or query in (e.get("platform") or "").lower()
            ]

    def export_csv(self, output_path: str):
        fields = [
            "id", "title", "artist", "platform", "format", "quality",
            "filepath", "duration", "filesize", "downloaded_at", "url",
        ]
        with self._lock:
            entries = list(self._entries)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(entries)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self):
        path = Path(HISTORY_FILE)
        if not path.exists():
            self._entries = []
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._entries = data if isinstance(data, list) else []
        except Exception as exc:
            logger.error("Failed to load history: %s", exc)
            self._entries = []

    def _save(self):
        path = Path(HISTORY_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("Failed to save history: %s", exc)
