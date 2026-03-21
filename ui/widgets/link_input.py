"""
Smart URL input field with paste button, clear button, and debounced detection.
"""

import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk

from locales.translator import t


class LinkInput(ctk.CTkFrame):
    """
    URL input widget with:
    - Large entry field
    - Paste button
    - Clear button
    - Visual feedback (border color for valid/invalid)
    - Debounced on_change callback

    on_change(url: str) is called 500ms after the user stops typing.
    """

    DEBOUNCE_MS = 500

    def __init__(
        self,
        master,
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_change = on_change or (lambda u: None)
        self._debounce_id: Optional[str] = None

        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

        self._entry_var = tk.StringVar()
        self._entry_var.trace_add("write", self._on_text_changed)

        self._entry = ctk.CTkEntry(
            self,
            textvariable=self._entry_var,
            placeholder_text=t("paste_link"),
            height=44,
            font=ctk.CTkFont(size=14),
            corner_radius=8,
        )
        self._entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        self._paste_btn = ctk.CTkButton(
            btn_frame,
            text=t("btn_paste"),
            width=70,
            height=44,
            command=self._paste,
        )
        self._paste_btn.pack(side="left", padx=(0, 6))

        self._clear_btn = ctk.CTkButton(
            btn_frame,
            text=t("btn_clear"),
            width=70,
            height=44,
            fg_color="gray40",
            hover_color="gray30",
            command=self._clear,
        )
        self._clear_btn.pack(side="left")

    def _on_text_changed(self, *_):
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(self.DEBOUNCE_MS, self._fire_change)

    def _fire_change(self):
        self._debounce_id = None
        url = self._entry_var.get().strip()
        self._on_change(url)

    def _paste(self):
        try:
            text = self.clipboard_get()
            self._entry_var.set(text.strip())
        except Exception:
            pass

    def _clear(self):
        self._entry_var.set("")
        self.set_state("normal")

    def get(self) -> str:
        return self._entry_var.get().strip()

    def set(self, url: str):
        self._entry_var.set(url)

    def set_state(self, state: str):
        """state: 'normal', 'valid', 'invalid'"""
        color_map = {
            "normal": ("gray50", "gray60"),
            "valid": ("#2FA827", "#3DCC32"),
            "invalid": ("#C0392B", "#E74C3C"),
        }
        border_color = color_map.get(state, color_map["normal"])
        self._entry.configure(border_color=border_color)

    def refresh_text(self):
        """Refresh placeholder text after language change."""
        self._entry.configure(placeholder_text=t("paste_link"))
        self._paste_btn.configure(text=t("btn_paste"))
        self._clear_btn.configure(text=t("btn_clear"))
