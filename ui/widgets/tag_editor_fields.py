"""
Reusable tag input field widget — label + entry in a row.
"""

import customtkinter as ctk
from locales.translator import t


class TagField(ctk.CTkFrame):
    """Single label + entry row for a tag field."""

    def __init__(self, master, label_key: str, width: int = 300, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._label_key = label_key
        self._label = ctk.CTkLabel(self, text=t(label_key), width=120, anchor="w")
        self._label.pack(side="left", padx=(0, 8))
        self._entry = ctk.CTkEntry(self, width=width)
        self._entry.pack(side="left", fill="x", expand=True)
        self._original: str = ""

    def get(self) -> str:
        return self._entry.get().strip()

    def set(self, value: str):
        self._entry.delete(0, "end")
        self._entry.insert(0, str(value) if value else "")
        self._original = str(value) if value else ""

    def clear(self):
        self._entry.delete(0, "end")
        self._original = ""

    def is_modified(self) -> bool:
        return self.get() != self._original

    def mark_saved(self):
        self._original = self.get()

    def refresh_label(self):
        self._label.configure(text=t(self._label_key))
