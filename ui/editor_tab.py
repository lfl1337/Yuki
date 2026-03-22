"""
MP3 tag editor tab — two-column Hime panel style.
"""

import os
import re
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk
from PIL import Image

from config import COVER_ART_SIZE, ASSETS_DIR, UI_COLORS
from core.tagger import MP3Tagger
from locales.translator import t
from ui.widgets.tag_editor_fields import TagField

C = UI_COLORS


class EditorTab(ctk.CTkFrame):
    def __init__(self, master, on_rename=None, **kwargs):
        super().__init__(master, fg_color=C["bg_primary"], **kwargs)
        self._tagger = MP3Tagger()
        self._filepath: Optional[str] = None
        self._original_tags: dict = {}
        self._cover_image: Optional[ctk.CTkImage] = None
        self._has_changes = False
        self._on_rename = on_rename
        self._placeholder_img = self._load_placeholder()

        self._build()

    def _build(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ---- Left card (280px) ----
        left = ctk.CTkFrame(
            self, width=280, corner_radius=12,
            fg_color=C["bg_card"],
        )
        left.grid(row=0, column=0, sticky="ns", padx=(16, 8), pady=16)
        left.pack_propagate(False)

        # Cover art
        self._cover_label = ctk.CTkLabel(left, text="", image=self._placeholder_img)
        self._cover_label.pack(pady=(16, 8))

        # Cover buttons
        cover_btns = ctk.CTkFrame(left, fg_color="transparent")
        cover_btns.pack(fill="x", padx=12, pady=(0, 8))

        self._change_cover_btn = ctk.CTkButton(
            cover_btns, text=t("change_cover"),
            fg_color="transparent", border_width=1,
            border_color=C["border"], hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            command=self._change_cover,
        )
        self._change_cover_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            cover_btns, text="From URL", width=80,
            fg_color="transparent", border_width=1,
            border_color=C["border"], hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            command=self._cover_from_url_dialog,
        ).pack(side="left")

        # File info
        self._filepath_label = ctk.CTkLabel(
            left, text="",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
            wraplength=248,
            anchor="w",
        )
        self._filepath_label.pack(fill="x", padx=12, pady=(0, 4))

        # Divider
        ctk.CTkFrame(left, height=1, fg_color=C["border"]).pack(fill="x", padx=12, pady=8)

        # Rename section
        ctk.CTkLabel(
            left, text="FILENAME",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
            anchor="w",
        ).pack(fill="x", padx=12, pady=(4, 2))

        rename_row = ctk.CTkFrame(left, fg_color="transparent")
        rename_row.pack(fill="x", padx=12, pady=2)
        rename_row.columnconfigure(0, weight=1)

        self._rename_entry = ctk.CTkEntry(
            rename_row,
            placeholder_text="filename",
            fg_color=C["bg_elevated"],
            border_color=C["border"],
            text_color=C["text_primary"],
        )
        self._rename_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._ext_label = ctk.CTkLabel(
            rename_row, text="", width=40, anchor="w",
            font=ctk.CTkFont(size=11), text_color=C["text_secondary"],
        )
        self._ext_label.pack(side="left")

        rename_btn_row = ctk.CTkFrame(left, fg_color="transparent")
        rename_btn_row.pack(fill="x", padx=12, pady=(2, 4))

        ctk.CTkButton(
            rename_btn_row, text="✏️ Rename", width=110,
            fg_color="transparent", border_width=1,
            border_color=C["border"], hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            command=self._do_rename,
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            rename_btn_row, text="Auto-name from Tags",
            fg_color="transparent", border_width=1,
            border_color=C["border"], hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            command=self._autoname_from_tags,
        ).pack(side="left")

        self._rename_status = ctk.CTkLabel(
            left, text="", font=ctk.CTkFont(size=10), wraplength=248,
        )
        self._rename_status.pack(fill="x", padx=12, pady=(0, 4))

        # Open in Explorer
        self._explore_btn = ctk.CTkButton(
            left,
            text=t("open_folder"),
            fg_color="transparent",
            text_color=C["accent"],
            hover_color=C["bg_elevated"],
            command=self._open_in_explorer,
        )
        self._explore_btn.pack(fill="x", padx=12, pady=(8, 4))

        # Unsaved indicator
        self._unsaved_label = ctk.CTkLabel(
            left, text="", text_color=C["warning"], font=ctk.CTkFont(size=11),
        )
        self._unsaved_label.pack(padx=12, pady=(0, 12))

        # ---- Right card (scrollable) ----
        right = ctk.CTkFrame(self, corner_radius=12, fg_color=C["bg_card"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        # File picker at top
        self._open_btn = ctk.CTkButton(
            right, text=t("open_file"),
            fg_color=C["accent"], hover_color=C["accent_hover"],
            command=self._open_file,
        )
        self._open_btn.pack(fill="x", padx=16, pady=(16, 8))

        # Tag fields in scrollable frame
        scroll = ctk.CTkScrollableFrame(right, fg_color="transparent", label_text="")
        scroll.pack(fill="both", expand=True, padx=8, pady=4)
        scroll.columnconfigure(0, weight=1)

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
            field = TagField(scroll, label_key=label_key)
            field.pack(fill="x", padx=8, pady=3)
            self._fields[tag_key] = field
            field._entry.bind("<KeyRelease>", lambda e: self._mark_changed())

        # Save/Reset buttons
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8, 16))

        self._save_btn = ctk.CTkButton(
            btn_row,
            text="💾 " + t("save_tags"),
            height=40,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            font=ctk.CTkFont(weight="bold"),
            command=self._save_tags,
        )
        self._save_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._reset_btn = ctk.CTkButton(
            btn_row,
            text="↺ " + t("reset_tags"),
            fg_color=C["bg_elevated"],
            hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            command=self._reset_tags,
        )
        self._reset_btn.pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _open_file(self):
        path = filedialog.askopenfilename(
            parent=self,  # ensures dialog appears in front of the main window
            title=t("open_file"),
            filetypes=[
                ("Audio files", "*.mp3 *.flac *.wav *.m4a *.ogg *.aac *.opus *.wma *.mp4"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.load_file(path)

    def load_file(self, filepath: str):
        p = Path(filepath)
        if not p.exists():
            self._filepath_label.configure(
                text=f"File not found: {p.name}", text_color=C["error"]
            )
            return
        self._filepath = str(filepath)
        self._filepath_label.configure(text=p.name, text_color=C["text_muted"])
        self._rename_entry.delete(0, "end")
        self._rename_entry.insert(0, p.stem)
        self._ext_label.configure(text=p.suffix)
        self._rename_status.configure(text="")
        self._unsaved_label.configure(text="")
        # Show placeholder immediately while tags load in background
        self._cover_label.configure(image=self._placeholder_img)
        threading.Thread(
            target=self._load_tags_thread, args=(str(filepath),), daemon=True
        ).start()

    def _load_tags_thread(self, filepath: str):
        try:
            tags = self._tagger.read_tags(filepath)
            cover = self._tagger.get_cover_art(filepath)
            self._original_tags = dict(tags)
            self.after(0, lambda: self._populate_fields(tags, cover))
        except Exception as exc:
            self.after(0, lambda: self._show_error(str(exc)))

    def _populate_fields(self, tags: dict, cover):
        for tag_key, field in self._fields.items():
            field.set(tags.get(tag_key, ""))
        if cover:
            cover_resized = cover.resize(COVER_ART_SIZE, Image.LANCZOS)
            ctk_img = ctk.CTkImage(cover_resized, size=COVER_ART_SIZE)
            self._cover_image = ctk_img
            self._cover_label.configure(image=ctk_img)
        else:
            self._cover_label.configure(image=self._placeholder_img)
        self._has_changes = False
        self._unsaved_label.configure(text="")

    def _show_error(self, msg: str):
        self._filepath_label.configure(text=t("error_corrupt_file"), text_color=C["error"])

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
            self._unsaved_label.configure(
                text="✓  " + t("success_tags_saved"), text_color=C["success"]
            )
        except Exception as exc:
            self._unsaved_label.configure(
                text=t("error_download_failed", reason=str(exc)[:60]),
                text_color=C["error"],
            )

    def _reset_tags(self):
        for key, field in self._fields.items():
            field.set(self._original_tags.get(key, ""))
        self._has_changes = False
        self._unsaved_label.configure(text="")

    def _mark_changed(self):
        if not self._has_changes:
            self._has_changes = True
            self._unsaved_label.configure(
                text="● " + t("unsaved_changes"), text_color=C["warning"]
            )

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

    def _cover_from_url_dialog(self):
        if not self._filepath:
            return
        dialog = ctk.CTkInputDialog(
            text="Enter image URL:", title="Cover from URL"
        )
        url = dialog.get_input()
        if url:
            self._apply_cover(url.strip())

    def _cover_from_url(self):
        pass  # Legacy compat

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
                    text=str(exc)[:80], text_color=C["error"]
                ))
        threading.Thread(target=worker, daemon=True).start()

    def _do_rename(self):
        if not self._filepath:
            return
        new_name = self._rename_entry.get().strip()
        if not new_name:
            self._rename_entry.configure(border_color=C["error"])
            self._rename_status.configure(text="Filename cannot be empty", text_color=C["error"])
            return
        if re.search(r'[\\/:*?"<>|]', new_name):
            self._rename_entry.configure(border_color=C["error"])
            self._rename_status.configure(
                text='Illegal characters: \\ / : * ? " < > |',
                text_color=C["error"],
            )
            return
        self._rename_entry.configure(border_color=C["border"])
        old_path = self._filepath
        ok, result = self._tagger.rename_file(old_path, new_name)
        if ok:
            self._filepath = result
            self._filepath_label.configure(text=Path(result).name)
            self._rename_entry.delete(0, "end")
            self._rename_entry.insert(0, Path(result).stem)
            self._ext_label.configure(text=Path(result).suffix)
            self._rename_status.configure(text="✓ Renamed successfully", text_color=C["success"])
            if self._on_rename:
                self._on_rename(old_path, result)
        else:
            self._rename_status.configure(text=result, text_color=C["error"])

    def _autoname_from_tags(self):
        artist = self._fields.get("artist", None)
        title = self._fields.get("title", None)
        artist_val = artist.get().strip() if artist else ""
        title_val = title.get().strip() if title else ""
        if artist_val and title_val:
            name = f"{artist_val} - {title_val}"
        elif title_val:
            name = title_val
        elif artist_val:
            name = artist_val
        else:
            self._rename_status.configure(text="No artist or title tag found", text_color=C["text_muted"])
            return
        name = re.sub(r'[\\/:*?"<>|]', "", name)
        self._rename_entry.delete(0, "end")
        self._rename_entry.insert(0, name)
        self._rename_status.configure(text="Auto-filled — click Rename to apply", text_color=C["text_muted"])

    def _open_in_explorer(self):
        if not self._filepath:
            self._rename_status.configure(text="No file loaded", text_color=C["text_muted"])
            return
        # Path.resolve() converts forward slashes (from filedialog) to backslashes
        # required by explorer /select,
        path = str(Path(self._filepath).resolve())
        subprocess.Popen(['explorer', f'/select,{path}'])

    def _load_placeholder(self) -> ctk.CTkImage:
        path = ASSETS_DIR / "placeholder_cover.png"
        try:
            img = Image.open(path).resize(COVER_ART_SIZE, Image.LANCZOS)
            return ctk.CTkImage(img, size=COVER_ART_SIZE)
        except Exception:
            blank = Image.new("RGB", COVER_ART_SIZE, C["bg_elevated"])
            return ctk.CTkImage(blank, size=COVER_ART_SIZE)

    def refresh_text(self):
        self._open_btn.configure(text=t("open_file"))
        self._change_cover_btn.configure(text=t("change_cover"))
        self._explore_btn.configure(text=t("open_folder"))
        self._save_btn.configure(text="💾 " + t("save_tags"))
        self._reset_btn.configure(text="↺ " + t("reset_tags"))
        for field in self._fields.values():
            field.refresh_label()
