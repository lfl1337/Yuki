"""
Settings window — sidebar + content layout.
"""

import webbrowser
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Optional

import customtkinter as ctk

from config import APP_NAME, VERSION, GITHUB_URL, LANGUAGES, THEMES, UI_COLORS
from core.autostart import enable_autostart, disable_autostart, is_autostart_enabled
from core.updater import Updater
from locales.translator import t, load_language

C = UI_COLORS


class SettingsWindow(ctk.CTkToplevel):
    """
    Modal settings window with sidebar navigation.
    """

    NAV_ITEMS = [
        ("appearance", "🎨  Appearance"),
        ("downloads",  "⬇  Downloads"),
        ("system",     "⚙  System"),
        ("about",      "ℹ  About"),
    ]

    def __init__(
        self,
        master,
        current_settings: dict,
        on_save: Optional[Callable[[dict], None]] = None,
        on_language_change: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(master)
        self._settings = dict(current_settings)
        self._on_save = on_save or (lambda s: None)
        self._on_lang_change = on_language_change or (lambda lc: None)

        self.title(t("settings"))
        self.geometry("680x480")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._active_section = "appearance"
        self._section_frames: dict = {}
        self._nav_btns: dict = {}

        self._build()
        self._show_section("appearance")
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = 680, 480
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # ---- Left nav panel ----
        nav = ctk.CTkFrame(self, width=160, corner_radius=0, fg_color=C["bg_secondary"])
        nav.grid(row=0, column=0, rowspan=2, sticky="ns")
        nav.pack_propagate(False)

        ctk.CTkLabel(
            nav, text="Settings",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C["text_primary"],
        ).pack(fill="x", padx=12, pady=(16, 8))

        ctk.CTkFrame(nav, height=1, fg_color=C["border"]).pack(fill="x", padx=8, pady=(0, 8))

        for section_key, label in self.NAV_ITEMS:
            btn = ctk.CTkButton(
                nav,
                text=label,
                anchor="w",
                height=36,
                corner_radius=8,
                fg_color="transparent",
                hover_color=C["bg_elevated"],
                text_color=C["text_secondary"],
                font=ctk.CTkFont(size=12),
                command=lambda k=section_key: self._show_section(k),
            )
            btn.pack(fill="x", padx=4, pady=1)
            self._nav_btns[section_key] = btn

        # ---- Right content area ----
        self._content = ctk.CTkScrollableFrame(
            self, fg_color=C["bg_card"], corner_radius=0, label_text=""
        )
        self._content.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self._content.columnconfigure(0, weight=1)

        # Build all sections
        self._build_appearance()
        self._build_downloads()
        self._build_system()
        self._build_about()

        # ---- Save / Cancel row ----
        btn_row = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=0)
        btn_row.grid(row=1, column=1, sticky="ew", padx=0, pady=0)

        ctk.CTkButton(
            btn_row, text=t("ok"), width=120,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            command=self._save,
        ).pack(side="right", padx=(4, 16), pady=8)

        ctk.CTkButton(
            btn_row, text=t("btn_cancel"), width=100,
            fg_color=C["bg_elevated"],
            hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            command=self.destroy,
        ).pack(side="right", padx=4, pady=8)

    def _build_appearance(self):
        frame = ctk.CTkFrame(self._content, fg_color="transparent")
        self._section_frames["appearance"] = frame

        self._section_title(frame, t("appearance"))

        # Theme
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row, text=t("theme"), width=160, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._theme_var = ctk.StringVar(value=self._settings.get("theme", "dark"))
        for theme in THEMES:
            ctk.CTkRadioButton(
                row, text=theme.capitalize(),
                variable=self._theme_var, value=theme,
                command=self._apply_theme,
            ).pack(side="left", padx=8)

        # Language
        row2 = ctk.CTkFrame(frame, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row2, text=t("language"), width=160, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        lang_names = list(LANGUAGES.values())
        self._lang_var = ctk.StringVar(
            value=LANGUAGES.get(self._settings.get("language", "en"), "English")
        )
        self._lang_menu = ctk.CTkOptionMenu(
            row2, variable=self._lang_var, values=lang_names, width=180,
            fg_color=C["bg_elevated"], button_color=C["border"],
            text_color=C["text_primary"],
            command=self._apply_language,
        )
        self._lang_menu.pack(side="left")

    def _build_downloads(self):
        frame = ctk.CTkFrame(self._content, fg_color="transparent")
        self._section_frames["downloads"] = frame

        self._section_title(frame, t("downloads"))

        row3 = ctk.CTkFrame(frame, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row3, text=t("default_folder"), width=160, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._folder_var = ctk.StringVar(value=self._settings.get("default_download_dir", ""))
        ctk.CTkEntry(
            row3, textvariable=self._folder_var, width=200,
            fg_color=C["bg_elevated"], border_color=C["border"],
            text_color=C["text_primary"],
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            row3, text=t("browse"), width=70,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            command=self._browse_folder,
        ).pack(side="left")

        row4 = ctk.CTkFrame(frame, fg_color="transparent")
        row4.pack(fill="x", padx=16, pady=4)
        self._ask_folder_var = ctk.BooleanVar(value=self._settings.get("ask_folder_each_time", False))
        ctk.CTkCheckBox(row4, text=t("ask_folder"), variable=self._ask_folder_var).pack(side="left")

        row_autoload = ctk.CTkFrame(frame, fg_color="transparent")
        row_autoload.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_autoload, text="Auto-load last download in player",
                     width=240, anchor="w", text_color=C["text_secondary"]).pack(side="left")
        self._autoload_var = ctk.BooleanVar(value=self._settings.get("autoload_last_download", False))
        ctk.CTkSwitch(row_autoload, text="", variable=self._autoload_var,
                      onvalue=True, offvalue=False).pack(side="left")

    def _build_system(self):
        frame = ctk.CTkFrame(self._content, fg_color="transparent")
        self._section_frames["system"] = frame

        self._section_title(frame, t("system"))

        row5 = ctk.CTkFrame(frame, fg_color="transparent")
        row5.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row5, text=t("autostart"), width=200, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._autostart_var = ctk.BooleanVar(value=is_autostart_enabled())
        ctk.CTkSwitch(row5, text="", variable=self._autostart_var,
                      onvalue=True, offvalue=False).pack(side="left")

        row6 = ctk.CTkFrame(frame, fg_color="transparent")
        row6.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row6, text=t("auto_update_ytdlp"), width=200, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._auto_update_var = ctk.BooleanVar(value=self._settings.get("auto_update_ytdlp", True))
        ctk.CTkSwitch(row6, text="", variable=self._auto_update_var,
                      onvalue=True, offvalue=False).pack(side="left")

        row7 = ctk.CTkFrame(frame, fg_color="transparent")
        row7.pack(fill="x", padx=16, pady=8)
        self._update_btn = ctk.CTkButton(
            row7, text=t("update_ytdlp"),
            fg_color=C["bg_elevated"], hover_color=C["bg_elevated"],
            border_width=1, border_color=C["border"],
            text_color=C["text_secondary"],
            command=self._manual_update,
        )
        self._update_btn.pack(side="left")
        self._update_status = ctk.CTkLabel(
            row7, text="", font=ctk.CTkFont(size=11), text_color=C["text_muted"]
        )
        self._update_status.pack(side="left", padx=8)

    def _build_about(self):
        frame = ctk.CTkFrame(self._content, fg_color="transparent")
        self._section_frames["about"] = frame

        self._section_title(frame, t("about"))

        about_frame = ctk.CTkFrame(frame, fg_color="transparent")
        about_frame.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(
            about_frame, text=f"{APP_NAME}  v{VERSION}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=C["accent"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            about_frame, text=f"{t('github')}: {GITHUB_URL}",
            font=ctk.CTkFont(size=11), text_color=C["text_muted"],
        ).pack(anchor="w", pady=4)
        ctk.CTkButton(
            about_frame, text=t("open_github"), width=160,
            fg_color="transparent", border_width=1, border_color=C["accent"],
            text_color=C["accent"], hover_color=C["bg_elevated"],
            command=lambda: webbrowser.open(GITHUB_URL),
        ).pack(anchor="w", pady=4)

        ctk.CTkButton(
            about_frame, text="View Logs", width=160,
            fg_color="transparent", border_width=1,
            border_color=C["border"], text_color=C["text_secondary"],
            hover_color=C["bg_elevated"],
            command=self._open_log_viewer,
        ).pack(anchor="w", pady=4)

    def _section_title(self, parent, title: str):
        ctk.CTkLabel(
            parent, text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C["text_primary"],
            anchor="w",
        ).pack(fill="x", padx=16, pady=(16, 4))
        ctk.CTkFrame(parent, height=1, fg_color=C["border"]).pack(fill="x", padx=16, pady=(0, 8))

    def _show_section(self, key: str):
        for k, frame in self._section_frames.items():
            frame.pack_forget()
        if key in self._section_frames:
            self._section_frames[key].pack(fill="both", expand=True)

        for k, btn in self._nav_btns.items():
            if k == key:
                btn.configure(fg_color=C["accent_soft"], text_color=C["text_primary"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text_secondary"])

        self._active_section = key

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _apply_theme(self):
        theme = self._theme_var.get()
        if theme == "system":
            try:
                import darkdetect
                theme = (darkdetect.theme() or "dark").lower()
            except Exception:
                theme = "dark"
        ctk.set_appearance_mode(theme)

    def _apply_language(self, lang_name: str):
        code = next((k for k, v in LANGUAGES.items() if v == lang_name), "en")
        load_language(code)
        self._on_lang_change(code)

    def _browse_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self._folder_var.get(), title=t("default_folder")
        )
        if folder:
            self._folder_var.set(folder)

    def _manual_update(self):
        self._update_btn.configure(state="disabled")
        self._update_status.configure(text=t("updating"), text_color=C["text_muted"])

        def on_done(ok: bool):
            self.after(0, lambda: self._update_status.configure(
                text=t("update_done") if ok else t("update_failed"),
                text_color=C["success"] if ok else C["error"],
            ))
            self.after(0, lambda: self._update_btn.configure(state="normal"))

        updater = Updater(on_update_done=on_done)
        updater.manual_update()

    def _open_log_viewer(self):
        from ui.log_viewer import LogViewer
        LogViewer(self)

    def _save(self):
        if self._autostart_var.get():
            enable_autostart()
        else:
            disable_autostart()

        lang_name = self._lang_var.get()
        lang_code = next((k for k, v in LANGUAGES.items() if v == lang_name), "en")

        new_settings = {
            "theme": self._theme_var.get(),
            "language": lang_code,
            "default_download_dir": self._folder_var.get(),
            "ask_folder_each_time": self._ask_folder_var.get(),
            "autostart": self._autostart_var.get(),
            "auto_update_ytdlp": self._auto_update_var.get(),
            "autoload_last_download": self._autoload_var.get(),
        }
        self._settings.update(new_settings)
        self._on_save(self._settings)
        self.destroy()
