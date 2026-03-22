"""
Root window — purple titlebar band, left sidebar, content area, bottom player bar.
"""

import logging
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from config import APP_NAME, VERSION, ASSETS_DIR, UI_COLORS
from core.history import HistoryManager
from core.updater import Updater
from locales.translator import t, load_language
from ui.sidebar import Sidebar
from ui.downloader_tab import DownloaderTab
from ui.history_tab import HistoryTab
from ui.editor_tab import EditorTab
from ui.player_bar import PlayerBar
from ui.settings_window import SettingsWindow
from ui.converter_tab import ConverterTab

logger = logging.getLogger(__name__)

C = UI_COLORS


class MainWindow(ctk.CTk):
    def __init__(self, settings: dict):
        super().__init__()
        self._settings = settings
        self._history = HistoryManager()
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_latest_x = 0
        self._drag_latest_y = 0
        self._drag_scheduled = False

        self._apply_theme(settings.get("theme", "dark"))
        load_language(settings.get("language", "en"))

        self._setup_window()
        self._build()
        self._start_updater()
        if self._settings.get("autoload_last_download"):
            self.after(400, self._autoload_last)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        w = self._settings.get("window_width", 1280)
        h = self._settings.get("window_height", 780)
        self.geometry(f"{w}x{h}")
        self.minsize(950, 650)
        self.title(f"{APP_NAME} — Media Suite")

        icon_path = ASSETS_DIR / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # ---- Row 0: Purple titlebar band ----
        self._titlebar = ctk.CTkFrame(
            self, height=36, corner_radius=0,
            fg_color=C["titlebar"],
        )
        self._titlebar.grid(row=0, column=0, sticky="ew")
        self._titlebar.columnconfigure(1, weight=1)
        self._titlebar.grid_propagate(False)

        ctk.CTkLabel(
            self._titlebar,
            text="  🌸 Yuki — Media Suite",
            font=ctk.CTkFont(size=13),
            text_color="#FFFFFF",
        ).grid(row=0, column=0, padx=8, pady=4, sticky="w")

        self._theme_btn = ctk.CTkButton(
            self._titlebar,
            text="🌙",
            width=32, height=28,
            fg_color="transparent",
            hover_color="#7C3AED",
            text_color="#FFFFFF",
            border_width=0,
            command=self._toggle_theme,
        )
        self._theme_btn.grid(row=0, column=2, padx=(4, 8), pady=4)

        # Window drag on titlebar
        self._titlebar.bind("<ButtonPress-1>", self._start_drag)
        self._titlebar.bind("<B1-Motion>", self._do_drag)

        # ---- Row 1: Sidebar + Content ----
        content_row = ctk.CTkFrame(self, corner_radius=0, fg_color=C["bg_primary"])
        content_row.grid(row=1, column=0, sticky="nsew")
        content_row.rowconfigure(0, weight=1)
        content_row.columnconfigure(1, weight=1)

        # Sidebar
        self._sidebar = Sidebar(content_row, on_navigate=self._navigate)
        self._sidebar.grid(row=0, column=0, sticky="ns")

        # Content wrapper
        self._content = ctk.CTkFrame(content_row, corner_radius=0, fg_color=C["bg_primary"])
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.rowconfigure(0, weight=1)
        self._content.columnconfigure(0, weight=1)

        # Create views
        self._downloader_tab = DownloaderTab(
            self._content,
            settings=self._settings,
            on_download_complete=self._on_download_complete,
        )
        self._history_tab = HistoryTab(
            self._content,
            history_manager=self._history,
            on_play=self._play_from_history,
            on_edit_tags=self._on_edit_tags,
            settings=self._settings,
        )
        self._editor_tab = EditorTab(
            self._content,
            on_rename=self._on_file_renamed,
        )
        self._converter_tab = ConverterTab(self._content)

        self._pages = {
            "downloader": self._downloader_tab,
            "history": self._history_tab,
            "editor": self._editor_tab,
            "converter": self._converter_tab,
        }

        # Place all pages in the same grid cell; use tkraise() to switch
        for page in self._pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        # Show default page
        self._current_page = "downloader"
        self._downloader_tab.tkraise()
        self._sidebar.set_active("downloader")

        # ---- Row 2: Player bar ----
        self._player_bar = PlayerBar(self)
        self._player_bar.grid(row=2, column=0, sticky="ew")

    def _show_page(self, name: str):
        if name in self._pages:
            self._pages[name].tkraise()
        self._current_page = name

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _navigate(self, page: str):
        if page == "settings":
            self._open_settings()
            return
        if page == "logs":
            from ui.log_viewer import LogViewer
            LogViewer(self)
            return
        logger.info("Tab switched to: %s", page)
        self._sidebar.set_active(page)
        self._show_page(page)

    # ------------------------------------------------------------------
    # Window drag
    # ------------------------------------------------------------------

    def _start_drag(self, event):
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _do_drag(self, event):
        # Always capture the latest mouse position before any early return.
        # Without this, intermediate motion events are silently dropped and
        # do_move() moves to where the mouse _was_, not where it _is_.
        self._drag_latest_x = event.x_root
        self._drag_latest_y = event.y_root
        if self._drag_scheduled:
            return
        self._drag_scheduled = True

        def do_move():
            x = self._drag_latest_x - self._drag_start_x
            y = self._drag_latest_y - self._drag_start_y
            self.geometry(f"+{x}+{y}")
            self._drag_scheduled = False

        self.after(16, do_move)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_download_complete(self, task, filepath: str, metadata: dict):
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
            self._navigate("editor")
            self._editor_tab.load_file(filepath)

    def _on_edit_tags(self, filepath: str):
        if not filepath or not Path(filepath).exists():
            self._show_toast("File not found on disk", "error")
            return
        self._navigate("editor")
        self.after(50, lambda: self._editor_tab.load_file(filepath))

    def _on_file_renamed(self, old_path: str, new_path: str):
        player = self._player_bar.get_player()
        current = player.get_filepath()
        if current and str(current) == old_path:
            player.update_filepath(new_path)
        for entry in self._history.get_all():
            if entry.get("filepath") == old_path:
                entry["filepath"] = new_path
                self._history.delete(entry["id"])
                self._history.add(entry)
                break
        self.after(0, self._history_tab.refresh)

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
        self._settings["language"] = lang_code
        self._save_settings()
        logger.debug("Language changed to: %s", lang_code)
        self._reload_ui()

    def _reload_ui(self):
        """Refresh all translatable UI text after a language change."""
        for widget in (
            self._sidebar,
            self._downloader_tab,
            self._history_tab,
            self._editor_tab,
            self._player_bar,
        ):
            try:
                widget.refresh_text()
            except Exception:
                pass

    def _apply_theme(self, theme: str):
        if theme == "system":
            try:
                import darkdetect
                theme = (darkdetect.theme() or "dark").lower()
            except Exception:
                theme = "dark"
        ctk.set_appearance_mode(theme)
        self._settings["theme"] = theme
        logger.debug("Theme changed to: %s", theme)

    def _toggle_theme(self):
        current = self._settings.get("theme", "dark")
        new = "light" if current == "dark" else "dark"
        self._settings["theme"] = new
        ctk.set_appearance_mode(new)
        self._theme_btn.configure(text="☀" if new == "dark" else "🌙")
        self._save_settings()
        logger.debug("Theme changed to: %s", new)

    # ------------------------------------------------------------------
    # Toast
    # ------------------------------------------------------------------

    def _show_toast(self, message: str, toast_type: str = "success"):
        color_map = {
            "success": C["success"],
            "info": C["accent"],
            "error": C["error"],
        }
        toast = ctk.CTkLabel(
            self,
            text=message,
            fg_color=color_map.get(toast_type, C["success"]),
            corner_radius=8,
            padx=12,
            pady=6,
            font=ctk.CTkFont(size=12),
        )
        toast.place(relx=1.0, rely=1.0, anchor="se", x=-12, y=-12)
        self.after(4000, toast.destroy)

    def show_toast(self, message: str, toast_type: str = "success"):
        self._show_toast(message, toast_type)

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

    def _autoload_last(self):
        entries = self._history.get_recent_audio(1)
        if entries:
            fp = entries[0].get("filepath", "")
            if fp and Path(fp).exists():
                self._player_bar.load_file(
                    fp,
                    title=entries[0].get("title", ""),
                    artist=entries[0].get("artist", ""),
                    autoplay=False,
                )

    def _on_close(self):
        try:
            self._downloader_tab._queue.cancel_all()
        except Exception:
            pass
        try:
            self._converter_tab.cancel_all()
        except Exception:
            pass
        try:
            self._player_bar.get_player().shutdown()
        except Exception:
            pass
        self._settings["window_width"] = self.winfo_width()
        self._settings["window_height"] = self.winfo_height()
        self._save_settings()
        self.destroy()
