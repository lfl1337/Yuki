"""
MP3 tag editor tab — file picker, cover art display, all tag fields, save/reset.
"""

import os
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk
from PIL import Image

from config import COVER_ART_SIZE, ASSETS_DIR
from core.tagger import MP3Tagger
from locales.translator import t
from ui.widgets.tag_editor_fields import TagField


class EditorTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._tagger = MP3Tagger()
        self._filepath: Optional[str] = None
        self._original_tags: dict = {}
        self._cover_image: Optional[ctk.CTkImage] = None
        self._has_changes = False

        self._build()

    def _build(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ---- Left panel ----
        left = ctk.CTkFrame(self, width=320)
        left.grid(row=0, column=0, sticky="ns", padx=(16, 8), pady=16)
        left.pack_propagate(False)

        self._open_btn = ctk.CTkButton(
            left, text=t("open_file"), command=self._open_file
        )
        self._open_btn.pack(fill="x", padx=12, pady=(12, 8))

        self._filepath_label = ctk.CTkLabel(
            left, text="", font=ctk.CTkFont(size=10), text_color="gray50",
            wraplength=280,
        )
        self._filepath_label.pack(fill="x", padx=12, pady=(0, 8))

        # Cover art
        placeholder = self._load_placeholder()
        self._cover_label = ctk.CTkLabel(left, text="", image=placeholder)
        self._cover_label.pack(pady=8)

        self._change_cover_btn = ctk.CTkButton(
            left, text=t("change_cover"), command=self._change_cover
        )
        self._change_cover_btn.pack(fill="x", padx=12, pady=4)

        self._cover_url_entry = ctk.CTkEntry(
            left, placeholder_text=t("cover_from_url")
        )
        self._cover_url_entry.pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(
            left, text="→", width=40, command=self._cover_from_url
        ).pack(anchor="e", padx=12)

        # Open in explorer
        self._explore_btn = ctk.CTkButton(
            left,
            text=t("open_folder"),
            fg_color="gray40", hover_color="gray30",
            command=self._open_in_explorer,
        )
        self._explore_btn.pack(fill="x", padx=12, pady=(8, 12))

        # Unsaved indicator
        self._unsaved_label = ctk.CTkLabel(
            left, text="", text_color="#F0A83D", font=ctk.CTkFont(size=11)
        )
        self._unsaved_label.pack()

        # ---- Right panel ----
        right = ctk.CTkScrollableFrame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)
        right.columnconfigure(0, weight=1)

        tag_defs = [
            ("editor_title", "title"),
            ("editor_artist", "artist"),
            ("editor_album", "album"),
            ("editor_album_artist", "album_artist"),
            ("editor_year", "year"),
            ("editor_genre", "genre"),
            ("editor_track", "track_number"),
            ("editor_total_tracks", "total_tracks"),
            ("editor_disc", "disc_number"),
            ("editor_bpm", "bpm"),
            ("editor_composer", "composer"),
            ("editor_comment", "comment"),
        ]
        self._fields: dict[str, TagField] = {}
        for i, (label_key, tag_key) in enumerate(tag_defs):
            field = TagField(right, label_key=label_key)
            field.pack(fill="x", padx=8, pady=3)
            self._fields[tag_key] = field
            field._entry.bind("<KeyRelease>", lambda e: self._mark_changed())

        # Bottom buttons
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(fill="x", padx=8, pady=12)

        self._save_btn = ctk.CTkButton(
            btn_row,
            text=t("save_tags"),
            command=self._save_tags,
            font=ctk.CTkFont(weight="bold"),
        )
        self._save_btn.pack(side="left", padx=4)

        self._reset_btn = ctk.CTkButton(
            btn_row,
            text=t("reset_tags"),
            fg_color="gray40", hover_color="gray30",
            command=self._reset_tags,
        )
        self._reset_btn.pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _open_file(self):
        path = filedialog.askopenfilename(
            title=t("open_file"),
            filetypes=[("Audio files", "*.mp3 *.m4a *.mp4"), ("All files", "*.*")],
        )
        if path:
            self.load_file(path)

    def load_file(self, filepath: str):
        self._filepath = filepath
        self._filepath_label.configure(text=Path(filepath).name)
        threading.Thread(
            target=self._load_tags_thread, args=(filepath,), daemon=True
        ).start()

    def _load_tags_thread(self, filepath: str):
        try:
            tags = self._tagger.read_tags(filepath)
            cover = self._tagger.get_cover_art(filepath)
            self._original_tags = dict(tags)
            self.after(0, lambda: self._populate_fields(tags, cover))
        except Exception as exc:
            self.after(0, lambda: self._show_error(str(exc)))

    def _populate_fields(self, tags: dict, cover: Optional[Image.Image]):
        for tag_key, field in self._fields.items():
            field.set(tags.get(tag_key, ""))

        if cover:
            cover_resized = cover.resize(COVER_ART_SIZE, Image.LANCZOS)
            ctk_img = ctk.CTkImage(cover_resized, size=COVER_ART_SIZE)
            self._cover_image = ctk_img
            self._cover_label.configure(image=ctk_img)
        else:
            self._cover_label.configure(image=self._load_placeholder())

        self._has_changes = False
        self._unsaved_label.configure(text="")

    def _show_error(self, msg: str):
        self._filepath_label.configure(text=t("error_corrupt_file"), text_color="red")

    # ------------------------------------------------------------------
    # Save / Reset
    # ------------------------------------------------------------------

    def _save_tags(self):
        if not self._filepath:
            return
        tags = {key: field.get() for key, field in self._fields.items()}
        try:
            self._tagger.write_tags(self._filepath, tags)
            for field in self._fields.values():
                field.mark_saved()
            self._has_changes = False
            self._unsaved_label.configure(text="✓  " + t("success_tags_saved"), text_color="#2FA827")
        except Exception as exc:
            self._unsaved_label.configure(
                text=t("error_download_failed", reason=str(exc)[:60]),
                text_color="red",
            )

    def _reset_tags(self):
        for key, field in self._fields.items():
            field.set(self._original_tags.get(key, ""))
        self._has_changes = False
        self._unsaved_label.configure(text="")

    def _mark_changed(self):
        if not self._has_changes:
            self._has_changes = True
            self._unsaved_label.configure(text="● " + t("unsaved_changes"), text_color="#F0A83D")

    # ------------------------------------------------------------------
    # Cover art
    # ------------------------------------------------------------------

    def _change_cover(self):
        if not self._filepath:
            return
        path = filedialog.askopenfilename(
            title=t("change_cover"),
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp"), ("All files", "*.*")],
        )
        if path:
            self._apply_cover(path)

    def _cover_from_url(self):
        if not self._filepath:
            return
        url = self._cover_url_entry.get().strip()
        if url:
            self._apply_cover(url)

    def _apply_cover(self, source: str):
        def worker():
            try:
                self._tagger.set_cover_art(self._filepath, source)
                img = self._tagger.get_cover_art(self._filepath)
                if img:
                    img = img.resize(COVER_ART_SIZE, Image.LANCZOS)
                    ctk_img = ctk.CTkImage(img, size=COVER_ART_SIZE)
                    self.after(0, lambda: self._cover_label.configure(image=ctk_img))
            except Exception as exc:
                self.after(0, lambda: self._unsaved_label.configure(
                    text=str(exc)[:80], text_color="red"
                ))
        threading.Thread(target=worker, daemon=True).start()

    def _open_in_explorer(self):
        if self._filepath:
            folder = str(Path(self._filepath).parent)
            try:
                os.startfile(folder)
            except Exception:
                subprocess.Popen(["explorer", folder])

    def _load_placeholder(self) -> ctk.CTkImage:
        path = ASSETS_DIR / "placeholder_cover.png"
        try:
            img = Image.open(path).resize(COVER_ART_SIZE, Image.LANCZOS)
            return ctk.CTkImage(img, size=COVER_ART_SIZE)
        except Exception:
            blank = Image.new("RGB", COVER_ART_SIZE, "#2a2a2a")
            return ctk.CTkImage(blank, size=COVER_ART_SIZE)

    def refresh_text(self):
        self._open_btn.configure(text=t("open_file"))
        self._change_cover_btn.configure(text=t("change_cover"))
        self._cover_url_entry.configure(placeholder_text=t("cover_from_url"))
        self._explore_btn.configure(text=t("open_folder"))
        self._save_btn.configure(text=t("save_tags"))
        self._reset_btn.configure(text=t("reset_tags"))
        for field in self._fields.values():
            field.refresh_label()
