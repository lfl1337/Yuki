"""
Settings modal window — appearance, downloads, system, about.
"""

import webbrowser
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Optional

import customtkinter as ctk

from config import APP_NAME, VERSION, GITHUB_URL, LANGUAGES, THEMES
from core.autostart import enable_autostart, disable_autostart, is_autostart_enabled
from core.updater import Updater
from locales.translator import t, load_language


class SettingsWindow(ctk.CTkToplevel):
    """
    Modal settings window.
    on_save(new_settings: dict) is called when user clicks Save.
    on_language_change(lang_code: str) is called immediately on language change.
    """

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
        self.geometry("520x640")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._build()
        self._load_values()
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = 520, 640
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self, label_text="")
        scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        scroll.columnconfigure(0, weight=1)

        self._scroll = scroll

        # ---- APPEARANCE ----
        self._section(scroll, t("appearance"))

        # Theme
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row, text=t("theme"), width=160, anchor="w").pack(side="left")
        self._theme_var = ctk.StringVar(value=self._settings.get("theme", "dark"))
        for theme in THEMES:
            ctk.CTkRadioButton(
                row, text=theme.capitalize(), variable=self._theme_var, value=theme,
                command=self._apply_theme,
            ).pack(side="left", padx=8)

        # Language
        row2 = ctk.CTkFrame(scroll, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row2, text=t("language"), width=160, anchor="w").pack(side="left")
        lang_names = list(LANGUAGES.values())
        self._lang_var = ctk.StringVar(
            value=LANGUAGES.get(self._settings.get("language", "en"), "English")
        )
        self._lang_menu = ctk.CTkOptionMenu(
            row2,
            variable=self._lang_var,
            values=lang_names,
            width=180,
            command=self._apply_language,
        )
        self._lang_menu.pack(side="left")

        # ---- DOWNLOADS ----
        self._section(scroll, t("downloads"))

        row3 = ctk.CTkFrame(scroll, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row3, text=t("default_folder"), width=160, anchor="w").pack(side="left")
        self._folder_var = ctk.StringVar(
            value=self._settings.get("default_download_dir", "")
        )
        ctk.CTkEntry(row3, textvariable=self._folder_var, width=200).pack(side="left", padx=4)
        ctk.CTkButton(
            row3, text=t("browse"), width=70,
            command=self._browse_folder,
        ).pack(side="left")

        row4 = ctk.CTkFrame(scroll, fg_color="transparent")
        row4.pack(fill="x", padx=16, pady=4)
        self._ask_folder_var = ctk.BooleanVar(
            value=self._settings.get("ask_folder_each_time", False)
        )
        ctk.CTkCheckBox(
            row4, text=t("ask_folder"), variable=self._ask_folder_var
        ).pack(side="left")

        # ---- SYSTEM ----
        self._section(scroll, t("system"))

        row5 = ctk.CTkFrame(scroll, fg_color="transparent")
        row5.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row5, text=t("autostart"), width=200, anchor="w").pack(side="left")
        self._autostart_var = ctk.BooleanVar(
            value=is_autostart_enabled()
        )
        ctk.CTkSwitch(
            row5, text="", variable=self._autostart_var,
            onvalue=True, offvalue=False,
        ).pack(side="left")

        row6 = ctk.CTkFrame(scroll, fg_color="transparent")
        row6.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row6, text=t("auto_update_ytdlp"), width=200, anchor="w").pack(side="left")
        self._auto_update_var = ctk.BooleanVar(
            value=self._settings.get("auto_update_ytdlp", True)
        )
        ctk.CTkSwitch(
            row6, text="", variable=self._auto_update_var,
            onvalue=True, offvalue=False,
        ).pack(side="left")

        row7 = ctk.CTkFrame(scroll, fg_color="transparent")
        row7.pack(fill="x", padx=16, pady=8)
        self._update_btn = ctk.CTkButton(
            row7, text=t("update_ytdlp"), command=self._manual_update
        )
        self._update_btn.pack(side="left")
        self._update_status = ctk.CTkLabel(
            row7, text="", font=ctk.CTkFont(size=11), text_color="gray60"
        )
        self._update_status.pack(side="left", padx=8)

        # ---- ABOUT ----
        self._section(scroll, t("about"))

        about_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        about_frame.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(
            about_frame,
            text=f"{APP_NAME}  v{VERSION}",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            about_frame,
            text=f"{t('github')}: {GITHUB_URL}",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        ).pack(anchor="w", pady=4)
        ctk.CTkButton(
            about_frame,
            text=t("open_github"),
            width=160,
            command=lambda: webbrowser.open(GITHUB_URL),
        ).pack(anchor="w", pady=4)

        # ---- Save / Cancel ----
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", padx=16, pady=12)

        ctk.CTkButton(
            btn_row, text=t("ok"), width=120, command=self._save
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            btn_row, text=t("btn_cancel"), width=100,
            fg_color="gray40", hover_color="gray30",
            command=self.destroy,
        ).pack(side="right", padx=4)

    def _section(self, parent, title: str):
        ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=16, pady=(16, 4))
        ctk.CTkFrame(parent, height=1, fg_color="gray30").pack(fill="x", padx=16)

    def _load_values(self):
        pass  # Values set in _build()

    def _apply_theme(self):
        theme = self._theme_var.get()
        if theme == "system":
            import darkdetect
            theme = darkdetect.theme() or "dark"
            theme = theme.lower()
        ctk.set_appearance_mode(theme)

    def _apply_language(self, lang_name: str):
        code = next(
            (k for k, v in LANGUAGES.items() if v == lang_name), "en"
        )
        load_language(code)
        self._on_lang_change(code)

    def _browse_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self._folder_var.get(),
            title=t("default_folder"),
        )
        if folder:
            self._folder_var.set(folder)

    def _manual_update(self):
        self._update_btn.configure(state="disabled")
        self._update_status.configure(text=t("updating"), text_color="gray60")

        def on_done(ok: bool):
            self.after(0, lambda: self._update_status.configure(
                text=t("update_done") if ok else t("update_failed"),
                text_color="#2FA827" if ok else "#E74C3C",
            ))
            self.after(0, lambda: self._update_btn.configure(state="normal"))

        updater = Updater(on_update_done=on_done)
        updater.manual_update()

    def _save(self):
        # Autostart
        if self._autostart_var.get():
            enable_autostart()
        else:
            disable_autostart()

        lang_name = self._lang_var.get()
        lang_code = next(
            (k for k, v in LANGUAGES.items() if v == lang_name), "en"
        )

        new_settings = {
            "theme": self._theme_var.get(),
            "language": lang_code,
            "default_download_dir": self._folder_var.get(),
            "ask_folder_each_time": self._ask_folder_var.get(),
            "autostart": self._autostart_var.get(),
            "auto_update_ytdlp": self._auto_update_var.get(),
        }
        self._settings.update(new_settings)
        self._on_save(self._settings)
        self.destroy()
