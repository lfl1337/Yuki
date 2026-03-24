"""
History tab — searchable, scrollable list of past downloads.
"""

import os
import subprocess
from pathlib import Path
from tkinter import filedialog
from typing import Callable, List, Optional

import customtkinter as ctk

from core.history import HistoryManager
from locales.translator import t


def _fmt_filesize(size: int) -> str:
    if not size:
        return ""
    if size >= 1_000_000:
        return f"{size/1_000_000:.1f} MB"
    if size >= 1_000:
        return f"{size/1_000:.0f} KB"
    return f"{size} B"


def _fmt_duration(seconds: int) -> str:
    if not seconds:
        return ""
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


class HistoryEntry(ctk.CTkFrame):
    def __init__(
        self,
        master,
        entry: dict,
        on_play: Callable,
        on_edit: Callable,
        on_open_folder: Callable,
        on_delete: Callable,
        **kwargs,
    ):
        super().__init__(master, corner_radius=8, **kwargs)
        self._entry = entry
        self.columnconfigure(1, weight=1)

        # Thumbnail placeholder
        placeholder = ctk.CTkLabel(self, text="🎵", width=48, font=ctk.CTkFont(size=24))
        placeholder.grid(row=0, column=0, rowspan=2, padx=12, pady=8)

        # Title + meta
        title = entry.get("title", "")
        self._title_lbl = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self._title_lbl.grid(row=0, column=1, padx=4, pady=(8, 0), sticky="w")

        parts = []
        if entry.get("platform"):
            parts.append(entry["platform"])
        if entry.get("format"):
            parts.append(entry["format"].upper())
        if entry.get("downloaded_at"):
            parts.append(entry["downloaded_at"][:10])
        if entry.get("filesize"):
            parts.append(_fmt_filesize(entry["filesize"]))
        if entry.get("duration"):
            parts.append(_fmt_duration(entry["duration"]))

        self._meta_lbl = ctk.CTkLabel(
            self,
            text="  •  ".join(parts),
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
        )
        self._meta_lbl.grid(row=1, column=1, padx=4, pady=(0, 8), sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=2, padx=8, pady=8, sticky="e")

        ctk.CTkButton(
            btn_frame, text=t("play"), width=60, height=28,
            command=lambda: on_play(entry),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame, text=t("edit_tags"), width=80, height=28,
            command=lambda: on_edit(entry),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame, text=t("open_folder"), width=100, height=28,
            fg_color="gray40", hover_color="gray30",
            command=lambda: on_open_folder(entry),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame, text=t("delete"), width=60, height=28,
            fg_color="#C0392B", hover_color="#E74C3C",
            command=lambda: on_delete(entry),
        ).pack(side="left", padx=2)


class HistoryTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        history_manager: HistoryManager,
        on_play: Optional[Callable] = None,
        on_edit: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._history = history_manager
        self._on_play = on_play or (lambda e: None)
        self._on_edit = on_edit or (lambda e: None)
        self._entry_widgets: List[HistoryEntry] = []

        self._build()
        self.refresh()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top bar
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        top.columnconfigure(0, weight=1)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search())
        self._search_entry = ctk.CTkEntry(
            top,
            textvariable=self._search_var,
            placeholder_text=t("search_placeholder"),
            height=36,
        )
        self._search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._export_btn = ctk.CTkButton(
            top, text=t("export_csv"), width=100, height=36,
            command=self._export_csv,
        )
        self._export_btn.grid(row=0, column=1, padx=4)

        self._clear_btn = ctk.CTkButton(
            top, text=t("clear_history"), width=110, height=36,
            fg_color="#C0392B", hover_color="#E74C3C",
            command=self._clear_history,
        )
        self._clear_btn.grid(row=0, column=2, padx=4)

        # Scrollable list
        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self._scroll.columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._scroll,
            text=t("history_empty"),
            text_color="gray50",
            font=ctk.CTkFont(size=13),
        )
        self._empty_label.pack(pady=40)

    def refresh(self):
        """Reload all entries from history manager."""
        query = self._search_var.get().strip() if hasattr(self, "_search_var") else ""
        entries = self._history.search(query) if query else self._history.get_all()
        self._render_entries(entries)

    def _render_entries(self, entries: List[dict]):
        for w in self._entry_widgets:
            w.destroy()
        self._entry_widgets.clear()

        if not entries:
            self._empty_label.pack(pady=40)
            return
        self._empty_label.pack_forget()

        for entry in entries:
            w = HistoryEntry(
                self._scroll,
                entry=entry,
                on_play=self._play,
                on_edit=self._edit,
                on_open_folder=self._open_folder,
                on_delete=self._delete,
            )
            w.pack(fill="x", padx=4, pady=3)
            self._entry_widgets.append(w)

    def _on_search(self):
        self.refresh()

    def _play(self, entry: dict):
        filepath = entry.get("filepath", "")
        if filepath and Path(filepath).exists():
            self._on_play(entry)

    def _edit(self, entry: dict):
        self._on_edit(entry)

    def _open_folder(self, entry: dict):
        filepath = entry.get("filepath", "")
        if filepath:
            folder = str(Path(filepath).parent)
            try:
                os.startfile(folder)
            except Exception:
                subprocess.Popen(["explorer", folder])

    def _delete(self, entry: dict):
        self._history.delete(entry.get("id", ""))
        self.refresh()

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title=t("export_csv"),
        )
        if path:
            self._history.export_csv(path)

    def _clear_history(self):
        from CTkMessagebox import CTkMessagebox
        msg = CTkMessagebox(
            title=t("confirm_clear_history"),
            message=t("confirm_clear_history"),
            icon="warning",
            option_1=t("yes"),
            option_2=t("no"),
        )
        if msg.get() == t("yes"):
            self._history.clear_all()
            self.refresh()

    def refresh_text(self):
        self._search_entry.configure(placeholder_text=t("search_placeholder"))
        self._export_btn.configure(text=t("export_csv"))
        self._clear_btn.configure(text=t("clear_history"))
        self._empty_label.configure(text=t("history_empty"))
        self.refresh()
