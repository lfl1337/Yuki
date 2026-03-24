"""
History tab — card list with search, filter pills, and action buttons.
"""

import os
import subprocess
from pathlib import Path
from tkinter import filedialog
from typing import Callable, List, Optional

import customtkinter as ctk

from config import UI_COLORS
from core.history import HistoryManager
from locales.translator import t

C = UI_COLORS

_PAGE_SIZE = 20


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


def _badge(parent, text, bg, fg):
    return ctk.CTkLabel(
        parent, text=text, fg_color=bg, text_color=fg,
        corner_radius=4, padx=6, pady=1, font=ctk.CTkFont(size=9),
    )


PLATFORM_BADGE_COLORS = {
    "YouTube":          ("#2D0A0A", "#FF4444"),
    "YouTube Shorts":   ("#2D0A0A", "#FF4444"),
    "YouTube Playlist": ("#2D0A0A", "#FF4444"),
    "Spotify":          ("#0A1F12", "#1DB954"),
    "TikTok":           (C["bg_elevated"], C["text_secondary"]),
    "SoundCloud":       ("#2D1500", "#FF5500"),
    "Instagram":        ("#2D0D1F", "#C13584"),
    "Twitter/X":        ("#0A1928", "#1DA1F2"),
}


def _platform_badge_colors(platform: str):
    return PLATFORM_BADGE_COLORS.get(platform, (C["accent_soft"], C["accent"]))


FILTER_OPTIONS = ["All", "Video", "Audio", "YouTube", "Spotify", "TikTok"]


class HistoryCard(ctk.CTkFrame):
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
        super().__init__(master, corner_radius=10, fg_color=C["bg_card"], **kwargs)
        self._entry = entry
        self.columnconfigure(1, weight=1)

        # Thumbnail placeholder
        thumb = ctk.CTkLabel(
            self, text="🎵",
            width=72, height=72,
            font=ctk.CTkFont(size=28),
            fg_color=C["bg_elevated"],
            corner_radius=6,
        )
        thumb.grid(row=0, column=0, rowspan=3, padx=12, pady=10, sticky="n")

        # Title
        title = entry.get("title", "")
        if len(title) > 50:
            title = title[:50] + "…"
        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C["text_primary"],
            anchor="w",
        ).grid(row=0, column=1, padx=4, pady=(10, 1), sticky="w")

        # Artist
        ctk.CTkLabel(
            self,
            text=entry.get("artist", ""),
            font=ctk.CTkFont(size=11),
            text_color=C["text_secondary"],
            anchor="w",
        ).grid(row=1, column=1, padx=4, pady=0, sticky="w")

        # Badge row
        badge_row = ctk.CTkFrame(self, fg_color="transparent")
        badge_row.grid(row=2, column=1, padx=4, pady=(2, 10), sticky="w")

        platform = entry.get("platform", "")
        if platform:
            bg, fg = _platform_badge_colors(platform)
            _badge(badge_row, platform, bg, fg).pack(side="left", padx=(0, 4))

        fmt = entry.get("format", "")
        if fmt:
            _badge(badge_row, fmt.upper(), C["bg_elevated"], C["text_secondary"]).pack(side="left", padx=(0, 4))

        date = entry.get("downloaded_at", "")
        if date:
            ctk.CTkLabel(
                badge_row, text=date[:10],
                font=ctk.CTkFont(size=10),
                text_color=C["text_muted"],
            ).pack(side="left", padx=(4, 0))

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=3, padx=10, pady=8, sticky="e")

        for icon, cmd in [
            ("▶", lambda: on_play(entry)),
            ("✏", lambda: on_edit(entry)),
            ("📁", lambda: on_open_folder(entry)),
            ("🗑", lambda: on_delete(entry)),
        ]:
            ctk.CTkButton(
                btn_frame, text=icon,
                width=28, height=28,
                fg_color="transparent",
                hover_color=C["bg_elevated"],
                text_color=C["text_secondary"],
                font=ctk.CTkFont(size=14),
                command=cmd,
            ).pack(pady=2)


class HistoryTab(ctk.CTkFrame):
    def __init__(
        self,
        master,
        history_manager: HistoryManager,
        on_play: Optional[Callable] = None,
        on_edit: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color=C["bg_primary"], **kwargs)
        self._history = history_manager
        self._on_play = on_play or (lambda e: None)
        self._on_edit = on_edit or (lambda e: None)
        self._entry_widgets: List[HistoryCard] = []
        self._filter_platform: str = "All"
        self._search_job: Optional[str] = None
        self._shown_count: int = _PAGE_SIZE
        self._current_entries: list = []

        self._build()
        self.refresh()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Search + controls row
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 8))
        top.columnconfigure(0, weight=1)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search())
        self._search_entry = ctk.CTkEntry(
            top,
            textvariable=self._search_var,
            placeholder_text=t("search_placeholder"),
            height=38,
            fg_color=C["bg_elevated"],
            border_color=C["border"],
            text_color=C["text_primary"],
        )
        self._search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._export_btn = ctk.CTkButton(
            top, text=t("export_csv"), width=100, height=38,
            fg_color="transparent",
            border_width=1, border_color=C["border"],
            text_color=C["text_secondary"],
            hover_color=C["bg_elevated"],
            command=self._export_csv,
        )
        self._export_btn.grid(row=0, column=1, padx=4)

        self._clear_btn = ctk.CTkButton(
            top, text=t("clear_history"), width=110, height=38,
            fg_color="transparent",
            border_width=1, border_color=C["error"],
            text_color=C["error"],
            hover_color=C["bg_elevated"],
            command=self._clear_history,
        )
        self._clear_btn.grid(row=0, column=2, padx=4)

        # Filter pills row
        pill_row = ctk.CTkFrame(self, fg_color="transparent")
        pill_row.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 8))

        self._filter_btns: dict = {}
        for opt in FILTER_OPTIONS:
            is_active = opt == "All"
            btn = ctk.CTkButton(
                pill_row,
                text=opt,
                width=70,
                height=28,
                corner_radius=14,
                fg_color=C["accent"] if is_active else "transparent",
                text_color="#FFFFFF" if is_active else C["text_secondary"],
                border_width=0 if is_active else 1,
                border_color=C["border"],
                hover_color=C["bg_elevated"],
                command=lambda o=opt: self._set_filter(o),
            )
            btn.pack(side="left", padx=2)
            self._filter_btns[opt] = btn

        # Scrollable list
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=C["bg_primary"], label_text="")
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self._scroll.columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._scroll,
            text="🎵\n\nNo downloads yet",
            text_color=C["text_muted"],
            font=ctk.CTkFont(size=13),
            justify="center",
        )
        self._empty_label.pack(pady=60)

    def refresh(self):
        query = self._search_var.get().strip() if hasattr(self, "_search_var") else ""
        entries = self._history.search(query) if query else self._history.get_all()
        self._current_entries = self._apply_filter(entries)
        self._render_entries()

    def _apply_filter(self, entries: list) -> list:
        f = self._filter_platform
        if f == "All":
            return entries
        if f == "Video":
            return [e for e in entries if e.get("format", "").lower() in ("video", "mp4")]
        if f == "Audio":
            return [e for e in entries if e.get("format", "").lower() in ("audio", "mp3")]
        return [e for e in entries if e.get("platform", "").lower() == f.lower()]

    def _set_filter(self, opt: str):
        self._filter_platform = opt
        for name, btn in self._filter_btns.items():
            if name == opt:
                btn.configure(fg_color=C["accent"], text_color="#FFFFFF", border_width=0)
            else:
                btn.configure(fg_color="transparent", text_color=C["text_secondary"], border_width=1)
        self._shown_count = _PAGE_SIZE
        self.refresh()

    def _render_entries(self):
        for w in self._entry_widgets:
            try:
                w.destroy()
            except Exception:
                pass
        self._entry_widgets.clear()

        entries = self._current_entries
        if not entries:
            self._empty_label.pack(pady=60)
            return
        self._empty_label.pack_forget()

        visible = entries[:self._shown_count]
        for entry in visible:
            w = HistoryCard(
                self._scroll,
                entry=entry,
                on_play=self._play,
                on_edit=self._edit,
                on_open_folder=self._open_folder,
                on_delete=self._delete,
            )
            w.pack(fill="x", padx=4, pady=4)
            self._entry_widgets.append(w)

        remaining = len(entries) - self._shown_count
        if remaining > 0:
            load_btn = ctk.CTkButton(
                self._scroll,
                text=f"Load {min(remaining, _PAGE_SIZE)} more  ({remaining} remaining)",
                fg_color="transparent",
                border_width=1,
                border_color=C["border"],
                text_color=C["text_secondary"],
                hover_color=C["bg_elevated"],
                command=self._load_more,
            )
            load_btn.pack(fill="x", padx=4, pady=8)
            self._entry_widgets.append(load_btn)

    def _load_more(self):
        self._shown_count += _PAGE_SIZE
        self._render_entries()

    def _on_search(self):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(300, self._do_search)

    def _do_search(self):
        self._search_job = None
        self._shown_count = _PAGE_SIZE
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
        try:
            from CTkMessagebox import CTkMessagebox
            msg = CTkMessagebox(
                title=t("confirm_clear_history"),
                message=t("confirm_clear_history"),
                icon="warning",
                option_1=t("yes"),
                option_2=t("no"),
            )
            if msg.get() != t("yes"):
                return
        except ImportError:
            from tkinter import messagebox
            if not messagebox.askyesno(t("confirm_clear_history"), t("confirm_clear_history")):
                return
        self._history.clear_all()
        self.refresh()

    def refresh_text(self):
        self._search_entry.configure(placeholder_text=t("search_placeholder"))
        self._export_btn.configure(text=t("export_csv"))
        self._clear_btn.configure(text=t("clear_history"))
        self._empty_label.configure(text="🎵\n\n" + t("history_empty"))
        self.refresh()
