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

C = UI_COLORS

_COVER_DISPLAY_SIZE = (240, 240)  # display only; tagger still uses COVER_ART_SIZE


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


class _Field:
    """Minimal get/set wrapper around CTkEntry or CTkTextbox."""

    def __init__(self, widget):
        self._w = widget
        self._original = ""

    def get(self) -> str:
        if isinstance(self._w, ctk.CTkTextbox):
            return self._w.get("1.0", "end").strip()
        return self._w.get().strip()

    def set(self, value: str):
        v = str(value) if value else ""
        if isinstance(self._w, ctk.CTkTextbox):
            self._w.delete("1.0", "end")
            self._w.insert("1.0", v)
        else:
            self._w.delete(0, "end")
            self._w.insert(0, v)
        self._original = v

    def mark_saved(self):
        self._original = self.get()

    def is_modified(self) -> bool:
        return self.get() != self._original


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
        self._fields: dict[str, _Field] = {}

        self._build()

    def _build(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ---- Left card (280px fixed) ----
        left = ctk.CTkFrame(self, width=280, corner_radius=12, fg_color=C["bg_card"])
        left.grid(row=0, column=0, sticky="ns", padx=(16, 8), pady=16)
        left.pack_propagate(False)

        # 1. Cover art (240×240)
        self._cover_label = ctk.CTkLabel(
            left, text="", image=self._placeholder_img,
            width=240, height=240,
        )
        self._cover_label.pack(pady=(16, 8))

        # 2. Cover buttons row
        cover_btns = ctk.CTkFrame(left, fg_color="transparent")
        cover_btns.pack(fill="x", padx=16, pady=(0, 12))

        self._change_cover_btn = ctk.CTkButton(
            cover_btns, text=t("change_cover"), height=34, corner_radius=8,
            fg_color=C["bg_elevated"], hover_color=C["accent_hover"],
            text_color=C["text_secondary"],
            command=self._change_cover,
        )
        self._change_cover_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            cover_btns, text="From URL", height=34, corner_radius=8,
            fg_color=C["bg_elevated"], hover_color=C["accent_hover"],
            text_color=C["text_secondary"],
            command=self._cover_from_url_dialog,
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # 3. Divider
        ctk.CTkFrame(left, height=1, fg_color=C["border"]).pack(fill="x", padx=16, pady=4)

        # 4. File info section
        info_frame = ctk.CTkFrame(left, fg_color="transparent")
        info_frame.pack(fill="x", padx=16, pady=(8, 8))

        self._info_filename = ctk.CTkLabel(
            info_frame, text="",
            font=ctk.CTkFont(size=11),
            text_color=C["text_muted"],
            anchor="w",
        )
        self._info_filename.pack(fill="x")

        self._info_filesize = ctk.CTkLabel(
            info_frame, text="",
            font=ctk.CTkFont(size=11),
            text_color=C["text_muted"],
            anchor="w",
        )
        self._info_filesize.pack(fill="x")

        self._info_duration = ctk.CTkLabel(
            info_frame, text="",
            font=ctk.CTkFont(size=11),
            text_color=C["text_muted"],
            anchor="w",
        )
        self._info_duration.pack(fill="x")

        # 5. Divider
        ctk.CTkFrame(left, height=1, fg_color=C["border"]).pack(fill="x", padx=16, pady=4)

        # 7. Bottom buttons (packed side="bottom" so spacer fills above)
        bottom_btns = ctk.CTkFrame(left, fg_color="transparent")
        bottom_btns.pack(side="bottom", fill="x", padx=16, pady=(0, 16))

        self._open_btn = ctk.CTkButton(
            bottom_btns, text=t("open_file"), height=36, corner_radius=8,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            command=self._open_file,
        )
        self._open_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._explore_btn = ctk.CTkButton(
            bottom_btns, text=t("open_folder"), height=36, corner_radius=8,
            fg_color=C["bg_elevated"], hover_color=C["accent_hover"],
            text_color=C["text_secondary"],
            command=self._open_in_explorer,
        )
        self._explore_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # 6. Spacer (fills remaining space above the bottom buttons)
        ctk.CTkFrame(left, fg_color="transparent").pack(fill="both", expand=True)

        # ---- Right card ----
        right = ctk.CTkFrame(self, corner_radius=12, fg_color=C["bg_card"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)

        # FILENAME section (outside scrollable, at top)
        filename_frame = ctk.CTkFrame(right, fg_color="transparent")
        filename_frame.pack(fill="x", padx=16, pady=(16, 0))

        ctk.CTkLabel(
            filename_frame, text="FILENAME",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        fname_row = ctk.CTkFrame(filename_frame, fg_color="transparent")
        fname_row.pack(fill="x", pady=(0, 4))

        self._rename_entry = ctk.CTkEntry(
            fname_row,
            placeholder_text="filename",
            fg_color=C["bg_elevated"],
            border_color=C["border"],
            text_color=C["text_primary"],
            height=36,
            corner_radius=8,
        )
        self._rename_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._ext_label = ctk.CTkLabel(
            fname_row, text="", width=40, anchor="w",
            font=ctk.CTkFont(size=11), text_color=C["text_secondary"],
        )
        self._ext_label.pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            fname_row, text="Rename", width=80, corner_radius=8,
            fg_color=C["bg_elevated"], hover_color=C["accent_hover"],
            text_color=C["text_secondary"],
            command=self._do_rename,
        ).pack(side="left")

        ctk.CTkButton(
            filename_frame, text="Auto-name from Tags", height=32, corner_radius=8,
            fg_color=C["bg_elevated"], hover_color=C["accent_hover"],
            text_color=C["text_secondary"],
            command=self._autoname_from_tags,
        ).pack(fill="x", pady=(0, 4))

        self._rename_status = ctk.CTkLabel(
            filename_frame, text="",
            font=ctk.CTkFont(size=11),
            text_color=C["text_muted"],
            anchor="w",
        )
        self._rename_status.pack(fill="x")

        # Divider after filename section
        ctk.CTkFrame(right, height=1, fg_color=C["border"]).pack(fill="x", padx=16, pady=(12, 0))

        # Scrollable tag fields
        scroll = ctk.CTkScrollableFrame(right, fg_color="transparent", label_text="")
        scroll.pack(fill="both", expand=True, padx=8, pady=4)

        self._build_tag_fields(scroll)

        # Divider before status/buttons
        ctk.CTkFrame(right, height=1, fg_color=C["border"]).pack(fill="x", padx=16, pady=(4, 0))

        # Status label
        self._status_label = ctk.CTkLabel(
            right, text="",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self._status_label.pack(fill="x", padx=16, pady=(4, 0))

        # Save / Reset buttons
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(8, 16))

        self._save_btn = ctk.CTkButton(
            btn_row,
            text="💾 " + t("save_tags"),
            height=40, corner_radius=8,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            font=ctk.CTkFont(weight="bold"),
            command=self._save_tags,
        )
        self._save_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._reset_btn = ctk.CTkButton(
            btn_row,
            text="↺ " + t("reset_tags"),
            width=90, height=40, corner_radius=8,
            fg_color=C["bg_elevated"],
            hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            command=self._reset_tags,
        )
        self._reset_btn.pack(side="left", padx=(4, 0))

    def _build_tag_fields(self, scroll):
        """Build two-column tag field grid inside the scrollable frame."""

        def lbl(parent, text):
            return ctk.CTkLabel(
                parent, text=text.upper(),
                font=ctk.CTkFont(size=10),
                text_color=C["text_muted"],
                anchor="w",
            )

        def entry(parent):
            return ctk.CTkEntry(
                parent,
                fg_color=C["bg_elevated"],
                corner_radius=8,
                border_color=C["border"],
                border_width=1,
                height=36,
                text_color=C["text_primary"],
            )

        def single(label_text, key):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", padx=16, pady=(0, 12))
            lbl(f, label_text).pack(fill="x", pady=(0, 2))
            e = entry(f)
            e.pack(fill="x")
            self._fields[key] = _Field(e)
            e.bind("<KeyRelease>", lambda ev: self._mark_changed())

        def pair(left_label, left_key, right_label, right_key):
            f = ctk.CTkFrame(scroll, fg_color="transparent")
            f.pack(fill="x", padx=16, pady=(0, 12))
            f.columnconfigure(0, weight=1)
            f.columnconfigure(1, weight=1)

            lbl(f, left_label).grid(row=0, column=0, sticky="w", pady=(0, 2))
            le = entry(f)
            le.grid(row=1, column=0, sticky="ew", padx=(0, 4))
            self._fields[left_key] = _Field(le)
            le.bind("<KeyRelease>", lambda ev: self._mark_changed())

            lbl(f, right_label).grid(row=0, column=1, sticky="w", pady=(0, 2), padx=(4, 0))
            re_ = entry(f)
            re_.grid(row=1, column=1, sticky="ew", padx=(4, 0))
            self._fields[right_key] = _Field(re_)
            re_.bind("<KeyRelease>", lambda ev: self._mark_changed())

        # Layout order
        single("Title", "title")
        pair("Artist", "artist", "Album Artist", "album_artist")
        pair("Album", "album", "Year", "year")
        pair("Genre", "genre", "Track / Total", "track_combined")
        pair("BPM", "bpm", "Disc", "disc_number")
        single("Composer", "composer")

        # Comment — CTkTextbox
        cf = ctk.CTkFrame(scroll, fg_color="transparent")
        cf.pack(fill="x", padx=16, pady=(0, 12))
        lbl(cf, "Comment").pack(fill="x", pady=(0, 2))
        comment_box = ctk.CTkTextbox(
            cf, height=60,
            fg_color=C["bg_elevated"],
            text_color=C["text_primary"],
            wrap="word",
            border_color=C["border"],
            border_width=1,
        )
        comment_box.pack(fill="x")
        self._fields["comment"] = _Field(comment_box)
        comment_box.bind("<KeyRelease>", lambda ev: self._mark_changed())

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def _open_file(self):
        path = filedialog.askopenfilename(
            parent=self,
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
            self._info_filename.configure(
                text=f"File not found: {p.name}", text_color=C["error"]
            )
            return
        self._filepath = str(filepath)
        self._rename_entry.delete(0, "end")
        self._rename_entry.insert(0, p.stem)
        self._ext_label.configure(text=p.suffix)
        self._rename_status.configure(text="")
        self._status_label.configure(text="")
        self._cover_label.configure(image=self._placeholder_img)
        threading.Thread(
            target=self._load_tags_thread, args=(str(filepath),), daemon=True
        ).start()

    def _load_tags_thread(self, filepath: str):
        try:
            tags = self._tagger.read_tags(filepath)
            cover = self._tagger.get_cover_art(filepath)
            self._original_tags = dict(tags)
            size = Path(filepath).stat().st_size
            duration = 0
            try:
                import mutagen
                audio = mutagen.File(filepath)
                if audio and hasattr(audio, "info"):
                    duration = int(audio.info.length)
            except Exception:
                pass
            self.after(0, lambda: self._populate_fields(tags, cover, size, duration))
        except Exception as exc:
            self.after(0, lambda: self._show_error(str(exc)))

    def _populate_fields(self, tags: dict, cover, size: int = 0, duration: int = 0):
        for key, field in self._fields.items():
            if key == "track_combined":
                track = tags.get("track_number", "")
                total = tags.get("total_tracks", "")
                combined = f"{track}/{total}" if total else str(track)
                field.set(combined)
            else:
                field.set(tags.get(key, ""))

        if cover:
            cover_resized = cover.resize(_COVER_DISPLAY_SIZE, Image.LANCZOS)
            ctk_img = ctk.CTkImage(cover_resized, size=_COVER_DISPLAY_SIZE)
            self._cover_image = ctk_img
            self._cover_label.configure(image=ctk_img)
        else:
            self._cover_label.configure(image=self._placeholder_img)

        name = Path(self._filepath).name
        self._info_filename.configure(
            text=(name[:30] + "…") if len(name) > 30 else name,
            text_color=C["text_muted"],
        )
        self._info_filesize.configure(text=_fmt_filesize(size))
        self._info_duration.configure(text=_fmt_duration(duration))

        self._has_changes = False
        self._status_label.configure(text="")

    def _show_error(self, msg: str):
        self._status_label.configure(text=t("error_corrupt_file"), text_color=C["error"])

    # ------------------------------------------------------------------
    # Save / Reset
    # ------------------------------------------------------------------

    def _save_tags(self):
        if not self._filepath:
            return
        tags = {}
        for key, field in self._fields.items():
            if key == "track_combined":
                raw = field.get()
                if "/" in raw:
                    parts = raw.split("/", 1)
                    tags["track_number"] = parts[0].strip()
                    tags["total_tracks"] = parts[1].strip()
                else:
                    tags["track_number"] = raw
                    tags["total_tracks"] = ""
            else:
                tags[key] = field.get()
        try:
            self._tagger.write_tags(self._filepath, tags)
            for field in self._fields.values():
                field.mark_saved()
            self._has_changes = False
            self._status_label.configure(
                text="✓  " + t("success_tags_saved"), text_color=C["success"]
            )
        except Exception as exc:
            self._status_label.configure(
                text=t("error_download_failed", reason=str(exc)[:60]),
                text_color=C["error"],
            )

    def _reset_tags(self):
        for key, field in self._fields.items():
            if key == "track_combined":
                track = self._original_tags.get("track_number", "")
                total = self._original_tags.get("total_tracks", "")
                combined = f"{track}/{total}" if total else str(track)
                field.set(combined)
            else:
                field.set(self._original_tags.get(key, ""))
        self._has_changes = False
        self._status_label.configure(text="")

    def _mark_changed(self):
        if not self._has_changes:
            self._has_changes = True
            self._status_label.configure(
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
                    img = img.resize(_COVER_DISPLAY_SIZE, Image.LANCZOS)
                    ctk_img = ctk.CTkImage(img, size=_COVER_DISPLAY_SIZE)
                    self.after(0, lambda: self._cover_label.configure(image=ctk_img))
            except Exception as exc:
                self.after(0, lambda: self._status_label.configure(
                    text=str(exc)[:80], text_color=C["error"]
                ))
        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Rename
    # ------------------------------------------------------------------

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
            name = Path(result).name
            self._info_filename.configure(
                text=(name[:30] + "…") if len(name) > 30 else name,
                text_color=C["text_muted"],
            )
            self._rename_entry.delete(0, "end")
            self._rename_entry.insert(0, Path(result).stem)
            self._ext_label.configure(text=Path(result).suffix)
            self._rename_status.configure(text="✓ Renamed successfully", text_color=C["success"])
            if self._on_rename:
                self._on_rename(old_path, result)
        else:
            self._rename_status.configure(text=result, text_color=C["error"])

    def _autoname_from_tags(self):
        artist = self._fields.get("artist")
        title = self._fields.get("title")
        artist_val = artist.get() if artist else ""
        title_val = title.get() if title else ""
        if artist_val and title_val:
            name = f"{artist_val} - {title_val}"
        elif title_val:
            name = title_val
        elif artist_val:
            name = artist_val
        else:
            self._rename_status.configure(
                text="No artist or title tag found", text_color=C["text_muted"]
            )
            return
        name = re.sub(r'[\\/:*?"<>|]', "", name)
        self._rename_entry.delete(0, "end")
        self._rename_entry.insert(0, name)
        self._rename_status.configure(
            text="Auto-filled — click Rename to apply", text_color=C["text_muted"]
        )

    def _open_in_explorer(self):
        if not self._filepath:
            self._rename_status.configure(text="No file loaded", text_color=C["text_muted"])
            return
        path = str(Path(self._filepath).resolve())
        subprocess.Popen(['explorer', f'/select,"{path}"'], creationflags=subprocess.CREATE_NO_WINDOW)

    def _load_placeholder(self) -> ctk.CTkImage:
        path = ASSETS_DIR / "placeholder_cover.png"
        try:
            img = Image.open(path).resize(_COVER_DISPLAY_SIZE, Image.LANCZOS)
            return ctk.CTkImage(img, size=_COVER_DISPLAY_SIZE)
        except Exception:
            blank = Image.new("RGB", _COVER_DISPLAY_SIZE, C["bg_elevated"])
            return ctk.CTkImage(blank, size=_COVER_DISPLAY_SIZE)

    def refresh_text(self):
        self._open_btn.configure(text=t("open_file"))
        self._change_cover_btn.configure(text=t("change_cover"))
        self._explore_btn.configure(text=t("open_folder"))
        self._save_btn.configure(text="💾 " + t("save_tags"))
        self._reset_btn.configure(text="↺ " + t("reset_tags"))
