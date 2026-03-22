"""
Smart URL input field with paste button, clear button, and debounced detection.
"""

import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk

from config import UI_COLORS
from locales.translator import t

C = UI_COLORS


class LinkInput(ctk.CTkFrame):
    """
    URL input widget with visual feedback and debounced on_change callback.
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
            height=42,
            font=ctk.CTkFont(size=14),
            corner_radius=8,
            fg_color=C["bg_elevated"],
            border_color=C["border"],
            border_width=1,
            text_color=C["text_primary"],
        )
        self._entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        self._paste_btn = ctk.CTkButton(
            btn_frame,
            text=t("btn_paste"),
            width=80,
            height=42,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            command=self._paste,
        )
        self._paste_btn.pack(side="left", padx=(0, 6))

        self._clear_btn = ctk.CTkButton(
            btn_frame,
            text=t("btn_clear"),
            width=60,
            height=42,
            fg_color=C["bg_elevated"],
            hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            border_width=1,
            border_color=C["border"],
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
            "normal": C["border"],
            "valid":  C["success"],
            "invalid": C["error"],
        }
        border_color = color_map.get(state, C["border"])
        self._entry.configure(border_color=border_color)

    def refresh_text(self):
        self._entry.configure(placeholder_text=t("paste_link"))
        self._paste_btn.configure(text=t("btn_paste"))
        self._clear_btn.configure(text=t("btn_clear"))
