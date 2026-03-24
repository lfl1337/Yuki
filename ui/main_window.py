"""
Root window — CTk window with tab manager, titlebar area, and bottom player bar.
"""

import logging
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from config import APP_NAME, VERSION, ASSETS_DIR
from core.history import HistoryManager
from core.updater import Updater
from locales.translator import t, load_language
from ui.downloader_tab import DownloaderTab
from ui.history_tab import HistoryTab
from ui.editor_tab import EditorTab
from ui.player_bar import PlayerBar
from ui.settings_window import SettingsWindow

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    def __init__(self, settings: dict):
        super().__init__()
        self._settings = settings
        self._history = HistoryManager()

        self._apply_theme(settings.get("theme", "dark"))
        load_language(settings.get("language", "en"))

        self._setup_window()
        self._build()
        self._start_updater()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        w = self._settings.get("window_width", 1100)
        h = self._settings.get("window_height", 700)
        self.geometry(f"{w}x{h}")
        self.minsize(900, 600)
        self.title(f"{APP_NAME}  v{VERSION}")

        # Icon
        icon_path = ASSETS_DIR / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Center
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # ---- Title bar area ----
        titlebar = ctk.CTkFrame(self, height=48, corner_radius=0)
        titlebar.grid(row=0, column=0, sticky="ew")
        titlebar.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            titlebar,
            text=f"{APP_NAME}",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=8)

        ctk.CTkLabel(
            titlebar,
            text=f"v{VERSION}",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        ).grid(row=0, column=1, padx=4, pady=8, sticky="w")

        # Theme toggle
        self._theme_btn = ctk.CTkButton(
            titlebar,
            text="🌙",
            width=36, height=36,
            fg_color="transparent",
            hover_color="gray30",
            command=self._toggle_theme,
        )
        self._theme_btn.grid(row=0, column=2, padx=4, pady=6)

        # Settings button
        self._settings_btn = ctk.CTkButton(
            titlebar,
            text="⚙",
            width=36, height=36,
            fg_color="transparent",
            hover_color="gray30",
            command=self._open_settings,
        )
        self._settings_btn.grid(row=0, column=3, padx=(4, 12), pady=6)

        # ---- Tab view ----
        self._tabs = ctk.CTkTabview(self, corner_radius=8)
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 0))

        self._tabs.add(t("tab_downloader"))
        self._tabs.add(t("tab_history"))
        self._tabs.add(t("tab_editor"))

        self._downloader_tab = DownloaderTab(
            self._tabs.tab(t("tab_downloader")),
            settings=self._settings,
            on_download_complete=self._on_download_complete,
        )
        self._downloader_tab.pack(fill="both", expand=True)

        self._history_tab = HistoryTab(
            self._tabs.tab(t("tab_history")),
            history_manager=self._history,
            on_play=self._play_from_history,
            on_edit=self._edit_from_history,
        )
        self._history_tab.pack(fill="both", expand=True)

        self._editor_tab = EditorTab(self._tabs.tab(t("tab_editor")))
        self._editor_tab.pack(fill="both", expand=True)

        # ---- Player bar (bottom) ----
        self._player_bar = PlayerBar(self)
        self._player_bar.grid(row=2, column=0, sticky="ew")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_download_complete(self, task, filepath: str, metadata: dict):
        """Called when a download finishes — add to history."""
        entry = {
            "title": metadata.get("title", task.info.get("title", "")),
            "artist": metadata.get("uploader", ""),
            "platform": metadata.get("platform", task.info.get("platform", "")),
            "format": task.fmt,
            "quality": task.quality,
            "filepath": filepath,
            "thumbnail_url": metadata.get("thumbnail_url", task.info.get("thumbnail_url", "")),
            "duration": metadata.get("duration", task.info.get("duration", 0)),
            "filesize": metadata.get("filesize", 0),
            "url": task.url,
        }
        self._history.add(entry)
        self.after(0, self._history_tab.refresh)

    def _play_from_history(self, entry: dict):
        filepath = entry.get("filepath", "")
        if filepath and Path(filepath).exists():
            title = entry.get("title", "")
            artist = entry.get("artist", "")
            self._player_bar.load_file(filepath, title=title, artist=artist)

    def _edit_from_history(self, entry: dict):
        filepath = entry.get("filepath", "")
        if filepath and Path(filepath).exists():
            self._tabs.set(t("tab_editor"))
            self._editor_tab.load_file(filepath)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _open_settings(self):
        SettingsWindow(
            self,
            current_settings=self._settings,
            on_save=self._apply_settings,
            on_language_change=self._on_language_change,
        )

    def _apply_settings(self, new_settings: dict):
        self._settings.update(new_settings)
        self._save_settings()
        self._apply_theme(self._settings.get("theme", "dark"))
        self._downloader_tab.update_settings(self._settings)
        load_language(self._settings.get("language", "en"))

    def _on_language_change(self, lang_code: str):
        """Immediate live preview of language in settings window."""
        pass  # Full reload happens on settings save

    def _apply_theme(self, theme: str):
        if theme == "system":
            try:
                import darkdetect
                theme = (darkdetect.theme() or "dark").lower()
            except Exception:
                theme = "dark"
        ctk.set_appearance_mode(theme)
        self._settings["theme"] = theme

    def _toggle_theme(self):
        current = self._settings.get("theme", "dark")
        new = "light" if current == "dark" else "dark"
        self._settings["theme"] = new
        ctk.set_appearance_mode(new)
        self._theme_btn.configure(text="☀" if new == "dark" else "🌙")
        self._save_settings()

    # ------------------------------------------------------------------
    # Updater
    # ------------------------------------------------------------------

    def _start_updater(self):
        if not self._settings.get("auto_update_ytdlp", True):
            return

        def on_available(current, latest):
            self.after(0, lambda: self._show_toast(
                t("update_available", current=current, latest=latest)
            ))

        def on_done(ok: bool):
            if ok:
                self.after(0, lambda: self._show_toast(t("update_done")))

        updater = Updater(
            on_update_available=on_available,
            on_update_done=on_done,
        )
        updater.check_and_update(auto_update=True)

    def _show_toast(self, message: str):
        """Simple non-blocking notification label that fades after 4s."""
        toast = ctk.CTkLabel(
            self,
            text=message,
            fg_color="#1DB954",
            corner_radius=8,
            padx=12,
            pady=6,
            font=ctk.CTkFont(size=12),
        )
        toast.place(relx=0.5, rely=0.95, anchor="s")
        self.after(4000, toast.destroy)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_settings(self):
        import json
        from config import SETTINGS_FILE, DATA_DIR
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error("Failed to save settings: %s", exc)

    def _on_close(self):
        # Save window size
        self._settings["window_width"] = self.winfo_width()
        self._settings["window_height"] = self.winfo_height()
        self._save_settings()
        self._player_bar.get_player().stop()
        self.destroy()
