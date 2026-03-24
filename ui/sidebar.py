"""
Sidebar navigation panel — Hime style left nav.
"""

import customtkinter as ctk

from config import VERSION, UI_COLORS


C = UI_COLORS


class Sidebar(ctk.CTkFrame):
    """Left sidebar with logo, nav buttons, and status row."""

    NAV_ITEMS = [
        ("downloader", "⬇  Downloader"),
        ("history",    "🕐  History"),
        ("editor",     "✏️  MP3 Editor"),
        ("converter",  "  Converter"),
    ]

    def __init__(self, master, on_navigate=None, **kwargs):
        super().__init__(
            master,
            width=180,
            corner_radius=0,
            fg_color=C["bg_secondary"],
            **kwargs,
        )
        self.pack_propagate(False)
        self._on_navigate = on_navigate or (lambda p: None)
        self._active_page: str = "downloader"
        self._nav_buttons: dict = {}
        self._accent_bars: dict = {}

        self._build()

    def _build(self):
        # Top section
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(8, 0))

        # Logo
        ctk.CTkLabel(
            top,
            text="雪",
            font=ctk.CTkFont(size=36),
            text_color=C["accent"],
        ).pack(pady=(16, 2))

        ctk.CTkLabel(
            top,
            text="Yuki",
            font=ctk.CTkFont(size=11),
            text_color=C["text_secondary"],
        ).pack(pady=(0, 12))

        # Divider
        ctk.CTkFrame(top, height=1, fg_color=C["border"]).pack(fill="x", padx=8)

        # Nav buttons
        for page, label in self.NAV_ITEMS:
            self._make_nav_btn(top, page, label)

        # Bottom section
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=(0, 8))

        ctk.CTkFrame(bottom, height=1, fg_color=C["border"]).pack(fill="x", padx=8, pady=(0, 4))

        # Logs button with status dot
        logs_row = ctk.CTkFrame(bottom, fg_color="transparent")
        logs_row.pack(fill="x", pady=1)

        self._make_nav_btn(logs_row, "logs", "📋  Logs")

        self._log_dot = ctk.CTkLabel(
            logs_row,
            text="●",
            font=ctk.CTkFont(size=8),
            text_color=C["text_muted"],
            width=14,
        )
        self._log_dot.place(relx=1.0, x=-18, rely=0.5, anchor="e")
        self._poll_log_status()

        # Settings button
        self._make_nav_btn(bottom, "settings", "⚙  Settings")

        # Status row
        status_row = ctk.CTkFrame(bottom, fg_color="transparent")
        status_row.pack(fill="x", padx=12, pady=(4, 2))

        ctk.CTkLabel(
            status_row,
            text="●",
            font=ctk.CTkFont(size=8),
            text_color=C["success"],
        ).pack(side="left")

        ctk.CTkLabel(
            status_row,
            text="  Ready",
            font=ctk.CTkFont(size=11),
            text_color=C["text_secondary"],
        ).pack(side="left")

        ctk.CTkLabel(
            bottom,
            text=f"Yuki v{VERSION}",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
        ).pack(padx=12, anchor="w")

    def _make_nav_btn(self, parent, page: str, label: str):
        container = ctk.CTkFrame(parent, fg_color="transparent", height=40)
        container.pack(fill="x", pady=1)
        container.pack_propagate(False)

        btn = ctk.CTkButton(
            container,
            text=label,
            anchor="w",
            height=40,
            corner_radius=8,
            fg_color="transparent",
            hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            font=ctk.CTkFont(size=13),
            command=lambda p=page: self._on_click(p),
        )
        btn.pack(fill="both", expand=True, padx=4)

        # Accent bar (hidden by default)
        bar = ctk.CTkFrame(container, width=3, fg_color=C["accent"], corner_radius=0)
        # place() at left edge, full height
        bar.place(x=0, rely=0, relheight=1)
        bar.place_forget()

        self._nav_buttons[page] = btn
        self._accent_bars[page] = bar

    def _on_click(self, page: str):
        # Navigate immediately — set_active() provides the visual highlight.
        # A flash-then-settle pattern doesn't work here: set_active() is called
        # synchronously inside _on_navigate and overwrites the flash color before
        # the event loop can render even one frame, so the flash is never visible
        # and only adds perceived latency.
        self._on_navigate(page)

    def _poll_log_status(self):
        try:
            from core import logger as app_logger
            entries = app_logger.get_entries()
            has_error = any(e["level"] == "ERROR" or e["level"] == "CRITICAL" for e in entries)
            has_warning = any(e["level"] == "WARNING" for e in entries)
            if has_error:
                color = C["error"]
            elif has_warning:
                color = C.get("warning", "#F59E0B")
            else:
                color = C["text_muted"]
            self._log_dot.configure(text_color=color)
        except Exception:
            pass
        self.after(2000, self._poll_log_status)

    def set_active(self, page: str):
        """Highlight the active nav button."""
        # Deactivate previous
        if self._active_page in self._nav_buttons:
            self._nav_buttons[self._active_page].configure(
                fg_color="transparent",
                text_color=C["text_secondary"],
            )
            self._accent_bars[self._active_page].place_forget()

        self._active_page = page

        if page in self._nav_buttons:
            self._nav_buttons[page].configure(
                fg_color=C["accent_soft"],
                text_color=C["text_primary"],
            )
            self._accent_bars[page].place(x=4, rely=0, relheight=1)
