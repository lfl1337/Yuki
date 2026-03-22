"""
In-app log viewer — live-updating window showing the application log.
"""

from tkinter import filedialog
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

_FILTER_LEVELS = ["All", "Info", "Warning", "Error"]


class LogViewer(ctk.CTkToplevel):
    """Live log viewer window."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Log Viewer")
        self.geometry("780x520")
        self.resizable(True, True)
        self.transient(master)

        self._filter_level: Optional[str] = None  # None = all
        self._all_entries: list = []
        self._filter_btns: dict = {}

        self._build()
        self._refresh_all()
        self._poll_new_entries()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = 780, 520
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color=C["bg_secondary"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
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

        ctk.CTkButton(
            btn_frame, text="Clear", width=70, height=28,
            fg_color=C["bg_elevated"], hover_color=C["bg_card"],
            border_width=1, border_color=C["border"],
            text_color=C["text_secondary"],
            command=self._clear_log,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame, text="Export", width=70, height=28,
            fg_color=C["bg_elevated"], hover_color=C["bg_card"],
            border_width=1, border_color=C["border"],
            text_color=C["text_secondary"],
            command=self._export_log,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame, text="✕", width=28, height=28,
            fg_color="transparent", hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            command=self.destroy,
        ).pack(side="left", padx=(4, 0))

        # Scrollable log list
        self._log_frame = ctk.CTkScrollableFrame(
            self, fg_color=C["bg_primary"], corner_radius=0, label_text=""
        )
        self._log_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self._log_frame.columnconfigure(0, weight=1)

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
        """Load all entries from the logger."""
        try:
            from core import logger as app_logger
            self._all_entries = app_logger.get_entries()
        except Exception:
            self._all_entries = []
        self._render_entries()

    def _render_entries(self):
        """Clear and re-render the filtered entry list."""
        for w in self._log_frame.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        filtered = self._filtered_entries()
        total = len(self._all_entries)
        shown = len(filtered)
        self._count_label.configure(text=f"Showing {shown} of {total} entries")

        for entry in filtered:
            self._add_entry_row(entry)

        # Scroll to bottom
        self.after(50, self._scroll_to_bottom)

    def _filtered_entries(self) -> list:
        if self._filter_level is None:
            return list(self._all_entries)
        level = self._filter_level
        # Map filter to matching levels
        if level == "WARNING":
            return [e for e in self._all_entries if e["level"] == "WARNING"]
        elif level == "ERROR":
            return [e for e in self._all_entries if e["level"] in ("ERROR", "CRITICAL")]
        elif level == "INFO":
            return [e for e in self._all_entries if e["level"] == "INFO"]
        return list(self._all_entries)

    def _add_entry_row(self, entry: dict):
        row = ctk.CTkFrame(
            self._log_frame,
            fg_color=C["bg_card"],
            corner_radius=4,
        )
        row.pack(fill="x", padx=8, pady=1)
        row.columnconfigure(3, weight=1)

        # Timestamp
        ctk.CTkLabel(
            row, text=entry.get("timestamp", ""),
            font=ctk.CTkFont(size=10, family="Courier"),
            text_color=C["text_muted"],
            width=72, anchor="w",
        ).grid(row=0, column=0, padx=(8, 4), pady=3, sticky="w")

        # Level badge
        level = entry.get("level", "INFO")
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

    def _scroll_to_bottom(self):
        try:
            self._log_frame._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _poll_new_entries(self):
        """Check for new entries every 500ms."""
        try:
            from core import logger as app_logger
            current = app_logger.get_entries()
            if len(current) != len(self._all_entries):
                self._all_entries = current
                self._render_entries()
        except Exception:
            pass
        self.after(500, self._poll_new_entries)

    def _clear_log(self):
        try:
            from core import logger as app_logger
            app_logger.clear()
            self._all_entries = []
            self._render_entries()
        except Exception:
            pass

    def _export_log(self):
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
