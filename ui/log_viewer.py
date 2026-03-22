"""
In-app log viewer — live-updating window showing the application log.
Features: file path header, open in Notepad, copy all, ERROR/WARNING row
highlighting, auto-scroll (paused when user scrolls up), log file size.
"""

import subprocess
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from config import UI_COLORS

C = UI_COLORS

_LEVEL_COLORS = {
    "DEBUG":    "#6B7280",
    "INFO":     "#1E40AF",
    "WARNING":  "#92400E",
    "ERROR":    C["error"],
    "CRITICAL": C["error"],
}

_ROW_BG_NORMAL  = C["bg_card"]
_ROW_BG_ERROR   = "#2A0A0A"
_ROW_BG_WARNING = "#2A1A00"

_FILTER_LEVELS = ["All", "Info", "Warning", "Error"]


class LogViewer(ctk.CTkToplevel):
    """Live log viewer window."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Log Viewer")
        self.geometry("900x560")
        self.resizable(True, True)
        self.transient(master)

        self._filter_level: Optional[str] = None  # None = all
        self._all_entries: list = []
        self._filter_btns: dict = {}
        self._auto_scroll = True   # paused when user scrolls up

        self._build()
        self._refresh_all()
        self._poll_new_entries()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = 900, 560
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        # ---- Row 0: info bar (log file path + size + open buttons) ----
        info_bar = ctk.CTkFrame(self, fg_color=C["bg_elevated"], corner_radius=0, height=32)
        info_bar.grid(row=0, column=0, sticky="ew")
        info_bar.grid_propagate(False)
        info_bar.columnconfigure(0, weight=1)

        self._path_label = ctk.CTkLabel(
            info_bar, text="Log file: —",
            font=ctk.CTkFont(size=10, family="Courier"),
            text_color=C["text_muted"],
            anchor="w",
        )
        self._path_label.grid(row=0, column=0, padx=10, pady=4, sticky="w")

        self._size_label = ctk.CTkLabel(
            info_bar, text="",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
        )
        self._size_label.grid(row=0, column=1, padx=8, pady=4)

        ctk.CTkButton(
            info_bar, text="Open in Notepad", width=120, height=22,
            fg_color="transparent", border_width=1, border_color=C["border"],
            text_color=C["text_secondary"], hover_color=C["bg_elevated"],
            font=ctk.CTkFont(size=10),
            command=self._open_in_notepad,
        ).grid(row=0, column=2, padx=(0, 4), pady=4)

        ctk.CTkButton(
            info_bar, text="Open in Explorer", width=120, height=22,
            fg_color="transparent", border_width=1, border_color=C["border"],
            text_color=C["text_secondary"], hover_color=C["bg_elevated"],
            font=ctk.CTkFont(size=10),
            command=self._open_in_explorer,
        ).grid(row=0, column=3, padx=(0, 8), pady=4)

        self._update_file_info()

        # ---- Row 1: header bar (title, filters, actions) ----
        header = ctk.CTkFrame(self, fg_color=C["bg_secondary"], corner_radius=0)
        header.grid(row=1, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="Log Viewer",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["text_primary"],
        ).grid(row=0, column=0, padx=16, pady=8, sticky="w")

        # Filter pills
        filter_frame = ctk.CTkFrame(header, fg_color="transparent")
        filter_frame.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        for label in _FILTER_LEVELS:
            btn = ctk.CTkButton(
                filter_frame,
                text=label,
                width=64, height=26,
                corner_radius=13,
                fg_color=C["accent"] if label == "All" else C["bg_elevated"],
                hover_color=C["accent_hover"],
                text_color=C["text_primary"] if label == "All" else C["text_secondary"],
                font=ctk.CTkFont(size=11),
                command=lambda lbl=label: self._set_filter(lbl),
            )
            btn.pack(side="left", padx=2)
            self._filter_btns[label] = btn

        # Count label
        self._count_label = ctk.CTkLabel(
            header, text="",
            font=ctk.CTkFont(size=11),
            text_color=C["text_muted"],
        )
        self._count_label.grid(row=0, column=2, padx=8, pady=8)

        # Action buttons
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.grid(row=0, column=3, padx=(0, 8), pady=6)

        for text, cmd, width in [
            ("Copy All", self._copy_all, 80),
            ("Clear",    self._clear_log, 70),
            ("Export",   self._export_log, 70),
        ]:
            ctk.CTkButton(
                btn_frame, text=text, width=width, height=28,
                fg_color=C["bg_elevated"], hover_color=C["bg_card"],
                border_width=1, border_color=C["border"],
                text_color=C["text_secondary"],
                command=cmd,
            ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame, text="✕", width=28, height=28,
            fg_color="transparent", hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            command=self.destroy,
        ).pack(side="left", padx=(4, 0))

        # ---- Row 2: scrollable log list ----
        self._log_frame = ctk.CTkScrollableFrame(
            self, fg_color=C["bg_primary"], corner_radius=0, label_text=""
        )
        self._log_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        self._log_frame.columnconfigure(0, weight=1)

        # Detect when user scrolls up to pause auto-scroll
        canvas = self._log_frame._parent_canvas
        canvas.bind("<MouseWheel>", self._on_scroll, add="+")
        canvas.bind("<Button-4>",   self._on_scroll, add="+")
        canvas.bind("<Button-5>",   self._on_scroll, add="+")

    # ------------------------------------------------------------------
    # File info
    # ------------------------------------------------------------------

    def _update_file_info(self):
        try:
            from core import logger as app_logger
            path = app_logger.get_log_file_path()
            if path and Path(path).exists():
                self._path_label.configure(text=f"Log file: {path}")
                size_bytes = Path(path).stat().st_size
                if size_bytes >= 1_000_000:
                    size_str = f"{size_bytes/1_000_000:.1f} MB"
                elif size_bytes >= 1_000:
                    size_str = f"{size_bytes/1_000:.0f} KB"
                else:
                    size_str = f"{size_bytes} B"
                self._size_label.configure(text=f"Log size: {size_str}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Filter + render
    # ------------------------------------------------------------------

    def _set_filter(self, label: str):
        self._filter_level = None if label == "All" else label.upper()
        for lbl, btn in self._filter_btns.items():
            is_active = (lbl == label)
            btn.configure(
                fg_color=C["accent"] if is_active else C["bg_elevated"],
                text_color=C["text_primary"] if is_active else C["text_secondary"],
            )
        self._render_entries()

    def _refresh_all(self):
        try:
            from core import logger as app_logger
            self._all_entries = app_logger.get_entries()
        except Exception:
            self._all_entries = []
        self._render_entries()

    def _render_entries(self):
        for w in self._log_frame.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        filtered = self._filtered_entries()
        shown = len(filtered)
        total = len(self._all_entries)
        self._count_label.configure(text=f"Showing {shown} of {total} entries")

        for entry in filtered:
            self._add_entry_row(entry)

        self._update_file_info()

        if self._auto_scroll:
            self.after(50, self._scroll_to_bottom)

    def _filtered_entries(self) -> list:
        if self._filter_level is None:
            return list(self._all_entries)
        level = self._filter_level
        if level == "WARNING":
            return [e for e in self._all_entries if e["level"] == "WARNING"]
        elif level == "ERROR":
            return [e for e in self._all_entries if e["level"] in ("ERROR", "CRITICAL")]
        elif level == "INFO":
            return [e for e in self._all_entries if e["level"] == "INFO"]
        return list(self._all_entries)

    def _add_entry_row(self, entry: dict):
        level = entry.get("level", "INFO")
        if level in ("ERROR", "CRITICAL"):
            row_bg = _ROW_BG_ERROR
        elif level == "WARNING":
            row_bg = _ROW_BG_WARNING
        else:
            row_bg = _ROW_BG_NORMAL

        row = ctk.CTkFrame(self._log_frame, fg_color=row_bg, corner_radius=4)
        row.pack(fill="x", padx=8, pady=1)
        row.columnconfigure(3, weight=1)

        # Timestamp
        ctk.CTkLabel(
            row, text=entry.get("timestamp", ""),
            font=ctk.CTkFont(size=10, family="Courier"),
            text_color=C["text_muted"],
            width=150, anchor="w",
        ).grid(row=0, column=0, padx=(8, 4), pady=3, sticky="w")

        # Level badge
        badge_color = _LEVEL_COLORS.get(level, "#6B7280")
        ctk.CTkLabel(
            row, text=level[:4],
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color="white",
            fg_color=badge_color,
            corner_radius=4,
            width=36, height=18,
        ).grid(row=0, column=1, padx=4, pady=3)

        # Module
        ctk.CTkLabel(
            row, text=entry.get("module", ""),
            font=ctk.CTkFont(size=10),
            text_color=C["text_secondary"],
            width=140, anchor="w",
        ).grid(row=0, column=2, padx=4, pady=3, sticky="w")

        # Message
        ctk.CTkLabel(
            row, text=entry.get("message", ""),
            font=ctk.CTkFont(size=11),
            text_color=C["text_primary"],
            anchor="w",
        ).grid(row=0, column=3, padx=(4, 8), pady=3, sticky="ew")

    # ------------------------------------------------------------------
    # Scroll management
    # ------------------------------------------------------------------

    def _on_scroll(self, event):
        """When user scrolls up, pause auto-scroll; scrolling to bottom re-enables it."""
        try:
            canvas = self._log_frame._parent_canvas
            # yview returns (top_fraction, bottom_fraction)
            _, bottom = canvas.yview()
            self._auto_scroll = (bottom >= 0.999)
        except Exception:
            pass

    def _scroll_to_bottom(self):
        try:
            self._log_frame._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def _poll_new_entries(self):
        try:
            from core import logger as app_logger
            current = app_logger.get_entries()
            if len(current) != len(self._all_entries):
                self._all_entries = current
                self._render_entries()
        except Exception:
            pass
        self.after(500, self._poll_new_entries)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_in_notepad(self):
        try:
            from core import logger as app_logger
            path = app_logger.get_log_file_path()
            if path and Path(path).exists():
                subprocess.Popen(
                    ["notepad.exe", str(path)],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
        except Exception:
            pass

    def _open_in_explorer(self):
        try:
            from core import logger as app_logger
            path = app_logger.get_log_file_path()
            if path:
                folder = str(Path(path).parent.resolve())
                subprocess.Popen(
                    ["explorer", folder],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
        except Exception:
            pass

    def _copy_all(self):
        entries = self._filtered_entries()
        lines = [
            f"[{e.get('timestamp','')}] {e.get('level','')} "
            f"{e.get('module','')} — {e.get('message','')}"
            for e in entries
        ]
        text = "\n".join(lines)
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
        except Exception:
            pass

    def _clear_log(self):
        try:
            from core import logger as app_logger
            app_logger.clear()
            self._all_entries = []
            self._render_entries()
        except Exception:
            pass

    def _export_log(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Log",
        )
        if not path:
            return
        entries = self._filtered_entries()
        try:
            with open(path, "w", encoding="utf-8") as f:
                for e in entries:
                    f.write(
                        f"[{e.get('timestamp','')}] {e.get('level','')} "
                        f"{e.get('module','')} — {e.get('message','')}\n"
                    )
        except Exception:
            pass
