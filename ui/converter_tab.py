"""
Converter tab — audio and video conversion via bundled ffmpeg.
"""

import json
import re
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Dict, Optional

import customtkinter as ctk

from config import FFMPEG_PATH, FFPROBE_PATH, UI_COLORS

C = UI_COLORS

AUDIO_FORMATS = {"mp3", "wav", "flac", "ogg", "aac", "opus", "m4a", "wma"}
VIDEO_FORMATS = {"mp4", "mkv", "avi", "mov", "webm", "gif"}

AUDIO_FORMAT_LABELS = ["MP3", "WAV", "FLAC", "OGG", "AAC", "OPUS", "M4A", "WMA"]
VIDEO_FORMAT_LABELS = ["MP4", "MKV", "AVI", "MOV", "WEBM", "GIF"]
BITRATE_OPTIONS = ["128k", "192k", "256k", "320k"]
SAMPLE_RATE_OPTIONS = ["44100", "48000", "96000"]
RESOLUTION_OPTIONS = ["480p", "720p", "1080p", "Original"]
CODEC_OPTIONS = ["H.264", "H.265", "VP9"]
VIDEO_AUDIO_BITRATE_OPTIONS = ["128k", "192k", "320k"]

_SEM = threading.Semaphore(2)


class ConversionItem:
    def __init__(self, input_path: str, cmd: list, update_fn, cancel_event: threading.Event):
        self.input_path = input_path
        self.cmd = cmd
        self.update_fn = update_fn
        self.cancel_event = cancel_event


class ConverterTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=C["bg_primary"], **kwargs)
        self._files: list = []
        self._output_format: str = "mp3"
        self._audio_bitrate: str = "320k"
        self._sample_rate: str = "44100"
        self._resolution: str = "Original"
        self._codec: str = "H.264"
        self._video_audio_bitrate: str = "192k"
        self._output_dir: str = ""
        self._create_subfolder: bool = False
        self._filename_mode: str = "keep"
        self._filename_suffix: str = ""
        self._filename_pattern: str = "{name}_{format}_{date}"
        self._conversion_items: Dict[str, ConversionItem] = {}
        self._file_rows: list = []
        self._progress_rows: dict = {}
        self._converting: bool = False
        self._count_lock = threading.Lock()

        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        outer = ctk.CTkScrollableFrame(self, fg_color=C["bg_primary"], label_text="")
        outer.pack(fill="both", expand=True, padx=0, pady=0)
        outer.columnconfigure(0, weight=1)

        self._build_input_card(outer)
        self._build_settings_card(outer)
        self._build_controls_card(outer)

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=C["bg_card"], corner_radius=12)
        card.pack(fill="x", padx=16, pady=(8, 0))
        ctk.CTkLabel(
            card, text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C["text_muted"],
            anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkFrame(card, height=1, fg_color=C["border"]).pack(fill="x", padx=16, pady=(0, 8))
        return card

    def _build_input_card(self, parent):
        card = self._card(parent, "INPUT FILES")

        # Drop zone
        drop_zone = ctk.CTkFrame(
            card, fg_color=C["bg_elevated"], corner_radius=8,
            border_width=1, border_color=C["border"], height=90,
        )
        drop_zone.pack(fill="x", padx=16, pady=4)
        drop_zone.pack_propagate(False)
        ctk.CTkLabel(
            drop_zone, text="Drop files here or click to browse",
            text_color=C["text_muted"], font=ctk.CTkFont(size=12),
        ).place(relx=0.5, rely=0.5, anchor="center")
        drop_zone.bind("<Button-1>", lambda e: self._add_files())

        # File list
        self._file_list_frame = ctk.CTkScrollableFrame(
            card, fg_color="transparent", height=180, label_text=""
        )
        self._file_list_frame.pack(fill="x", padx=16, pady=4)
        self._file_list_frame.columnconfigure(0, weight=1)

        self._no_files_label = ctk.CTkLabel(
            self._file_list_frame, text="No files added yet",
            text_color=C["text_muted"], font=ctk.CTkFont(size=11),
        )
        self._no_files_label.pack(pady=8)

        # Button row
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkButton(
            btn_row, text="Add Files", width=110,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            command=self._add_files,
        ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(
            btn_row, text="Add Folder", width=110,
            fg_color="transparent", border_width=1, border_color=C["border"],
            hover_color=C["bg_elevated"], text_color=C["text_secondary"],
            command=self._add_folder,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row, text="Clear All", width=90,
            fg_color="transparent", border_width=1, border_color=C["border"],
            hover_color=C["bg_elevated"], text_color=C["text_secondary"],
            command=self._clear_files,
        ).pack(side="left", padx=4)

    def _build_settings_card(self, parent):
        card = self._card(parent, "CONVERSION SETTINGS")

        # Output format
        ctk.CTkLabel(
            card, text="Output Format",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text_secondary"], anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 2))

        audio_row = ctk.CTkFrame(card, fg_color="transparent")
        audio_row.pack(fill="x", padx=16, pady=2)
        self._format_btns: dict = {}
        for label in AUDIO_FORMAT_LABELS:
            fmt = label.lower()
            btn = ctk.CTkButton(
                audio_row, text=label, width=60, height=28,
                corner_radius=14,
                fg_color=C["accent"] if fmt == self._output_format else C["bg_elevated"],
                hover_color=C["accent_hover"],
                text_color=C["text_primary"],
                font=ctk.CTkFont(size=11),
                command=lambda f=fmt: self._select_format(f),
            )
            btn.pack(side="left", padx=2)
            self._format_btns[fmt] = btn

        video_row = ctk.CTkFrame(card, fg_color="transparent")
        video_row.pack(fill="x", padx=16, pady=2)
        for label in VIDEO_FORMAT_LABELS:
            fmt = label.lower()
            btn = ctk.CTkButton(
                video_row, text=label, width=60, height=28,
                corner_radius=14,
                fg_color=C["accent"] if fmt == self._output_format else C["bg_elevated"],
                hover_color=C["accent_hover"],
                text_color=C["text_primary"],
                font=ctk.CTkFont(size=11),
                command=lambda f=fmt: self._select_format(f),
            )
            btn.pack(side="left", padx=2)
            self._format_btns[fmt] = btn

        # Audio quality section
        self._audio_quality_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._audio_quality_frame.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            self._audio_quality_frame, text="Audio Quality",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text_secondary"], anchor="w",
        ).pack(fill="x", pady=(4, 2))

        br_row = ctk.CTkFrame(self._audio_quality_frame, fg_color="transparent")
        br_row.pack(fill="x")
        ctk.CTkLabel(br_row, text="Bitrate:", width=70, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._bitrate_btns: dict = {}
        for br in BITRATE_OPTIONS:
            btn = ctk.CTkButton(
                br_row, text=br, width=56, height=26, corner_radius=13,
                fg_color=C["accent"] if br == self._audio_bitrate else C["bg_elevated"],
                hover_color=C["accent_hover"],
                text_color=C["text_primary"],
                font=ctk.CTkFont(size=11),
                command=lambda b=br: self._select_bitrate(b),
            )
            btn.pack(side="left", padx=2)
            self._bitrate_btns[br] = btn

        sr_row = ctk.CTkFrame(self._audio_quality_frame, fg_color="transparent")
        sr_row.pack(fill="x", pady=4)
        ctk.CTkLabel(sr_row, text="Sample rate:", width=90, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._sample_rate_var = ctk.StringVar(value=self._sample_rate)
        ctk.CTkOptionMenu(
            sr_row, variable=self._sample_rate_var,
            values=SAMPLE_RATE_OPTIONS, width=120,
            fg_color=C["bg_elevated"], button_color=C["border"],
            text_color=C["text_primary"],
            command=lambda v: setattr(self, "_sample_rate", v),
        ).pack(side="left")

        # Video quality section
        self._video_quality_frame = ctk.CTkFrame(card, fg_color="transparent")

        ctk.CTkLabel(
            self._video_quality_frame, text="Video Quality",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text_secondary"], anchor="w",
        ).pack(fill="x", pady=(4, 2))

        res_row = ctk.CTkFrame(self._video_quality_frame, fg_color="transparent")
        res_row.pack(fill="x")
        ctk.CTkLabel(res_row, text="Resolution:", width=90, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._resolution_btns: dict = {}
        for r in RESOLUTION_OPTIONS:
            btn = ctk.CTkButton(
                res_row, text=r, width=70, height=26, corner_radius=13,
                fg_color=C["accent"] if r == self._resolution else C["bg_elevated"],
                hover_color=C["accent_hover"],
                text_color=C["text_primary"],
                font=ctk.CTkFont(size=11),
                command=lambda res=r: self._select_resolution(res),
            )
            btn.pack(side="left", padx=2)
            self._resolution_btns[r] = btn

        codec_row = ctk.CTkFrame(self._video_quality_frame, fg_color="transparent")
        codec_row.pack(fill="x", pady=4)
        ctk.CTkLabel(codec_row, text="Codec:", width=70, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._codec_var = ctk.StringVar(value=self._codec)
        ctk.CTkOptionMenu(
            codec_row, variable=self._codec_var,
            values=CODEC_OPTIONS, width=120,
            fg_color=C["bg_elevated"], button_color=C["border"],
            text_color=C["text_primary"],
            command=lambda v: setattr(self, "_codec", v),
        ).pack(side="left")

        vabr_row = ctk.CTkFrame(self._video_quality_frame, fg_color="transparent")
        vabr_row.pack(fill="x", pady=4)
        ctk.CTkLabel(vabr_row, text="Audio bitrate:", width=90, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._video_abr_btns: dict = {}
        for br in VIDEO_AUDIO_BITRATE_OPTIONS:
            btn = ctk.CTkButton(
                vabr_row, text=br, width=56, height=26, corner_radius=13,
                fg_color=C["accent"] if br == self._video_audio_bitrate else C["bg_elevated"],
                hover_color=C["accent_hover"],
                text_color=C["text_primary"],
                font=ctk.CTkFont(size=11),
                command=lambda b=br: self._select_video_abr(b),
            )
            btn.pack(side="left", padx=2)
            self._video_abr_btns[br] = btn

        # Output folder
        folder_row = ctk.CTkFrame(card, fg_color="transparent")
        folder_row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(folder_row, text="Output folder:", width=100, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._output_dir_var = ctk.StringVar(value=self._output_dir)
        ctk.CTkEntry(
            folder_row, textvariable=self._output_dir_var,
            placeholder_text="Same as input file",
            fg_color=C["bg_elevated"], border_color=C["border"],
            text_color=C["text_primary"], width=220,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            folder_row, text="Browse", width=70,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            command=self._browse_output,
        ).pack(side="left")

        # Subfolder checkbox
        sub_row = ctk.CTkFrame(card, fg_color="transparent")
        sub_row.pack(fill="x", padx=16, pady=2)
        self._subfolder_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            sub_row, text="Create subfolder 'Yuki Converted'",
            variable=self._subfolder_var,
            text_color=C["text_secondary"],
        ).pack(side="left")

        # Filename options
        fname_row = ctk.CTkFrame(card, fg_color="transparent")
        fname_row.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(fname_row, text="Filename:", width=80, anchor="w",
                     text_color=C["text_secondary"]).pack(side="left")
        self._filename_mode_var = ctk.StringVar(value="keep")
        for val, label in [("keep", "Keep original"), ("suffix", "Add suffix"), ("custom", "Custom pattern")]:
            ctk.CTkRadioButton(
                fname_row, text=label,
                variable=self._filename_mode_var, value=val,
                text_color=C["text_secondary"],
                command=self._on_filename_mode_change,
            ).pack(side="left", padx=6)

        self._filename_custom_entry = ctk.CTkEntry(
            card,
            placeholder_text="{name}_{format}_{date}",
            fg_color=C["bg_elevated"], border_color=C["border"],
            text_color=C["text_primary"],
        )

        self._update_quality_visibility()

    def _build_controls_card(self, parent):
        card = self._card(parent, "CONVERT")

        ctk.CTkButton(
            card, text="Convert All", height=44,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_conversion,
        ).pack(fill="x", padx=16, pady=8)

        # Progress section (hidden until conversion starts)
        self._progress_section = ctk.CTkFrame(card, fg_color="transparent")

        self._overall_label = ctk.CTkLabel(
            self._progress_section, text="",
            text_color=C["text_secondary"], font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self._overall_label.pack(fill="x", padx=16, pady=(4, 2))

        self._overall_bar = ctk.CTkProgressBar(
            self._progress_section, height=4,
            progress_color=C["accent"], fg_color=C["border"],
        )
        self._overall_bar.set(0)
        self._overall_bar.pack(fill="x", padx=16, pady=2)

        self._per_file_frame = ctk.CTkScrollableFrame(
            self._progress_section, fg_color="transparent", height=280, label_text=""
        )
        self._per_file_frame.pack(fill="x", padx=16, pady=4)
        self._per_file_frame.columnconfigure(0, weight=1)

        self._open_output_btn = ctk.CTkButton(
            card, text="Open Output Folder",
            fg_color="transparent", border_width=1, border_color=C["accent"],
            text_color=C["accent"], hover_color=C["bg_elevated"],
            command=self._open_output_folder,
        )

    # ------------------------------------------------------------------
    # Format / quality selection
    # ------------------------------------------------------------------

    def _select_format(self, fmt: str):
        prev = self._output_format
        self._output_format = fmt
        if prev in self._format_btns:
            self._format_btns[prev].configure(fg_color=C["bg_elevated"])
        if fmt in self._format_btns:
            self._format_btns[fmt].configure(fg_color=C["accent"])
        self._update_quality_visibility()

    def _select_bitrate(self, br: str):
        if self._audio_bitrate in self._bitrate_btns:
            self._bitrate_btns[self._audio_bitrate].configure(fg_color=C["bg_elevated"])
        self._audio_bitrate = br
        self._bitrate_btns[br].configure(fg_color=C["accent"])

    def _select_resolution(self, res: str):
        if self._resolution in self._resolution_btns:
            self._resolution_btns[self._resolution].configure(fg_color=C["bg_elevated"])
        self._resolution = res
        self._resolution_btns[res].configure(fg_color=C["accent"])

    def _select_video_abr(self, br: str):
        if self._video_audio_bitrate in self._video_abr_btns:
            self._video_abr_btns[self._video_audio_bitrate].configure(fg_color=C["bg_elevated"])
        self._video_audio_bitrate = br
        self._video_abr_btns[br].configure(fg_color=C["accent"])

    def _update_quality_visibility(self):
        is_audio = self._output_format in AUDIO_FORMATS
        if is_audio:
            self._audio_quality_frame.pack(fill="x", padx=16, pady=4)
            self._video_quality_frame.pack_forget()
        else:
            self._audio_quality_frame.pack_forget()
            self._video_quality_frame.pack(fill="x", padx=16, pady=4)

    def _on_filename_mode_change(self):
        mode = self._filename_mode_var.get()
        if mode == "custom":
            self._filename_custom_entry.pack(fill="x", padx=16, pady=(0, 8))
        else:
            self._filename_custom_entry.pack_forget()

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select Files to Convert",
            filetypes=[
                ("Audio/Video files",
                 "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.opus *.wma "
                 "*.mp4 *.mkv *.avi *.mov *.webm *.gif"),
                ("All files", "*.*"),
            ],
        )
        for p in paths:
            if p not in self._files:
                self._files.append(p)
                self._add_file_row(p)
        self._refresh_no_files_label()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if not folder:
            return
        exts = {
            ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wma",
            ".mp4", ".mkv", ".avi", ".mov", ".webm", ".gif",
        }
        for f in Path(folder).iterdir():
            if f.is_file() and f.suffix.lower() in exts:
                if str(f) not in self._files:
                    self._files.append(str(f))
                    self._add_file_row(str(f))
        self._refresh_no_files_label()

    def _add_file_row(self, path: str):
        p = Path(path)
        row = ctk.CTkFrame(self._file_list_frame, fg_color=C["bg_elevated"], corner_radius=6, height=32)
        row.pack(fill="x", pady=2)
        row.pack_propagate(False)

        ctk.CTkLabel(
            row, text=p.name, anchor="w",
            font=ctk.CTkFont(size=11), text_color=C["text_primary"],
        ).pack(side="left", padx=8, fill="x", expand=True)

        ext_label = ctk.CTkLabel(
            row, text=p.suffix.upper().lstrip("."),
            fg_color=C["accent_soft"], corner_radius=4,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["accent"], width=36,
        )
        ext_label.pack(side="left", padx=4)

        try:
            size = p.stat().st_size
            size_str = f"{size / 1024 / 1024:.1f} MB" if size > 1024 * 1024 else f"{size / 1024:.0f} KB"
        except Exception:
            size_str = ""
        ctk.CTkLabel(
            row, text=size_str, width=60,
            font=ctk.CTkFont(size=10), text_color=C["text_muted"],
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            row, text="x", width=24, height=24, corner_radius=12,
            fg_color="transparent", hover_color=C["error"],
            text_color=C["text_muted"], font=ctk.CTkFont(size=11),
            command=lambda p=path, r=row: self._remove_file(p, r),
        ).pack(side="right", padx=4)

        self._file_rows.append((path, row))

    def _remove_file(self, path: str, row):
        if path in self._files:
            self._files.remove(path)
        self._file_rows = [(p, r) for p, r in self._file_rows if p != path]
        try:
            row.destroy()
        except Exception:
            pass
        self._refresh_no_files_label()

    def _clear_files(self):
        self._files.clear()
        for _, row in self._file_rows:
            try:
                row.destroy()
            except Exception:
                pass
        self._file_rows.clear()
        self._refresh_no_files_label()

    def _refresh_no_files_label(self):
        if self._files:
            self._no_files_label.pack_forget()
        else:
            self._no_files_label.pack(pady=8)

    # ------------------------------------------------------------------
    # Output folder
    # ------------------------------------------------------------------

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self._output_dir_var.set(folder)
            self._output_dir = folder

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def _start_conversion(self):
        if not Path(FFMPEG_PATH).exists():
            self._progress_section.pack(fill="x", padx=0, pady=4)
            self._overall_label.configure(
                text="ffmpeg not found. Place ffmpeg.exe in /ffmpeg/",
                text_color=C["error"],
            )
            return
        if not self._files:
            return
        if self._converting:
            return
        self._converting = True
        self._conversion_items.clear()
        self._progress_rows.clear()

        for w in self._per_file_frame.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        self._progress_section.pack(fill="x", padx=0, pady=4)
        self._overall_label.configure(text=f"Converting 0 of {len(self._files)} files")
        self._overall_bar.set(0)
        self._open_output_btn.pack_forget()

        for fp in self._files:
            self._add_progress_row(fp)

        self._completed_count = 0
        self._total_count = len(self._files)

        for fp in self._files:
            cancel_event = threading.Event()
            out_path = self._resolve_output_path(fp)
            settings = {
                "bitrate": self._audio_bitrate,
                "sample_rate": self._sample_rate,
                "resolution": self._resolution,
                "audio_bitrate": self._video_audio_bitrate,
                "scale": self._resolution.replace("p", "") if self._resolution != "Original" else "480",
            }
            cmd = self._build_ffmpeg_cmd(fp, out_path, self._output_format, settings)
            item_id = fp

            def make_update_fn(iid):
                def fn(pct):
                    self.after(0, lambda: self._update_progress_row(iid, pct))
                return fn

            item = ConversionItem(fp, cmd, make_update_fn(item_id), cancel_event)
            self._conversion_items[item_id] = item

            threading.Thread(
                target=self._run_one,
                args=(item_id, item),
                daemon=True,
            ).start()

    def _run_one(self, item_id: str, item: ConversionItem):
        _SEM.acquire()
        try:
            self.after(0, lambda: self._set_row_status(item_id, "converting"))
            result = self._run_conversion(item, item.cancel_event)
            if result == "done":
                self.after(0, lambda: self._set_row_status(item_id, "done"))
            elif result == "cancelled":
                self.after(0, lambda: self._set_row_status(item_id, "cancelled"))
            else:
                self.after(0, lambda: self._set_row_status(item_id, "failed"))
        except Exception:
            self.after(0, lambda: self._set_row_status(item_id, "failed"))
        finally:
            _SEM.release()
            with self._count_lock:
                self._completed_count += 1
                done = self._completed_count
            total = self._total_count
            self.after(0, lambda: self._on_one_done(done, total))

    def _on_one_done(self, done: int, total: int):
        self._overall_label.configure(text=f"Converting {done} of {total} files")
        self._overall_bar.set(done / total if total > 0 else 0)
        if done >= total:
            self._converting = False
            self._overall_label.configure(text=f"Done — {total} file(s) converted")
            self._open_output_btn.pack(fill="x", padx=16, pady=(0, 8))

    def _resolve_output_path(self, input_path: str) -> str:
        p = Path(input_path)
        out_dir = self._output_dir_var.get().strip() or str(p.parent)
        if self._subfolder_var.get():
            out_dir = str(Path(out_dir) / "Yuki Converted")
            Path(out_dir).mkdir(parents=True, exist_ok=True)
        mode = self._filename_mode_var.get()
        if mode == "keep":
            stem = p.stem
        elif mode == "suffix":
            suffix = self._filename_custom_entry.get().strip() or self._output_format
            stem = f"{p.stem}_{suffix}"
        else:
            from datetime import date
            pattern = self._filename_custom_entry.get().strip() or "{name}_{format}_{date}"
            stem = pattern.replace("{name}", p.stem).replace(
                "{format}", self._output_format).replace("{date}", str(date.today()))
        return str(Path(out_dir) / f"{stem}.{self._output_format}")

    def _build_ffmpeg_cmd(self, input_path: str, output_path: str, fmt: str, settings: dict) -> list:
        cmd = [str(FFMPEG_PATH), "-i", input_path, "-y"]
        if fmt in AUDIO_FORMATS:
            if fmt == "mp3":
                cmd += ["-codec:a", "libmp3lame", "-b:a", settings["bitrate"]]
            elif fmt == "flac":
                cmd += ["-codec:a", "flac"]
            elif fmt == "wav":
                cmd += ["-codec:a", "pcm_s16le"]
            elif fmt == "ogg":
                cmd += ["-codec:a", "libvorbis", "-b:a", settings["bitrate"]]
            elif fmt == "opus":
                cmd += ["-codec:a", "libopus", "-b:a", settings["bitrate"]]
            elif fmt == "aac":
                cmd += ["-codec:a", "aac", "-b:a", settings["bitrate"]]
            elif fmt == "m4a":
                cmd += ["-codec:a", "aac", "-b:a", settings["bitrate"]]
            elif fmt == "wma":
                cmd += ["-codec:a", "wmav2", "-b:a", settings["bitrate"]]
            if fmt not in ("flac", "wav"):
                cmd += ["-ar", settings.get("sample_rate", "44100")]
        else:
            if fmt == "gif":
                fps = 15
                scale = settings.get("scale", "480")
                cmd += ["-vf", f"fps={fps},scale={scale}:-1:flags=lanczos", "-loop", "0"]
            else:
                codec_map = {
                    "mp4": "libx264", "mkv": "libx264", "avi": "libxvid",
                    "mov": "libx264", "webm": "libvpx-vp9",
                }
                vcodec = codec_map.get(fmt, "libx264")
                user_codec = settings.get("codec_name", "")
                if user_codec == "H.265":
                    vcodec = "libx265"
                elif user_codec == "VP9":
                    vcodec = "libvpx-vp9"
                cmd += ["-codec:v", vcodec, "-b:a", settings.get("audio_bitrate", "192k")]
                if settings.get("resolution") not in ("Original", ""):
                    h = settings["resolution"].replace("p", "")
                    cmd += ["-vf", f"scale=-2:{h}"]
        cmd.append(output_path)
        return cmd

    def _get_duration(self, path: str) -> float:
        try:
            cmd = [
                str(FFPROBE_PATH), "-v", "quiet", "-print_format", "json",
                "-show_format", path,
            ]
            result = subprocess.run(
                cmd, capture_output=True,
                encoding="utf-8", errors="replace",
                timeout=30, creationflags=subprocess.CREATE_NO_WINDOW,
            )
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0))
        except Exception:
            return 0.0

    def _run_conversion(self, item: ConversionItem, cancel_event: threading.Event) -> str:
        duration = self._get_duration(item.input_path)
        try:
            proc = subprocess.Popen(
                item.cmd,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            return "error"
        for line in proc.stderr:
            if cancel_event.is_set():
                proc.kill()
                return "cancelled"
            m = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
            if m and duration > 0:
                h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
                elapsed = h * 3600 + mi * 60 + s
                pct = min(elapsed / duration * 100, 99.0)
                item.update_fn(pct)
        proc.wait()
        if cancel_event.is_set():
            return "cancelled"
        return "done" if proc.returncode == 0 else "error"

    # ------------------------------------------------------------------
    # Per-file progress rows
    # ------------------------------------------------------------------

    def _add_progress_row(self, filepath: str):
        p = Path(filepath)
        row = ctk.CTkFrame(self._per_file_frame, fg_color=C["bg_elevated"], corner_radius=6)
        row.pack(fill="x", pady=2)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(6, 2))

        ctk.CTkLabel(
            top, text=p.name, anchor="w",
            font=ctk.CTkFont(size=11), text_color=C["text_primary"],
        ).pack(side="left")

        ctk.CTkLabel(
            top, text=" → ",
            font=ctk.CTkFont(size=11), text_color=C["text_muted"],
        ).pack(side="left")

        ctk.CTkLabel(
            top, text=self._output_format.upper(),
            fg_color=C["accent_soft"], corner_radius=4,
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=C["accent"], width=36,
        ).pack(side="left")

        status_label = ctk.CTkLabel(
            top, text="Waiting",
            font=ctk.CTkFont(size=10), text_color=C["text_muted"],
        )
        status_label.pack(side="right", padx=4)

        bar = ctk.CTkProgressBar(
            row, height=3,
            progress_color=C["accent"], fg_color=C["border"],
        )
        bar.set(0)
        bar.pack(fill="x", padx=8, pady=(2, 6))

        self._progress_rows[filepath] = {"bar": bar, "status": status_label}

    def _update_progress_row(self, filepath: str, pct: float):
        row_data = self._progress_rows.get(filepath)
        if row_data:
            row_data["bar"].set(pct / 100.0)
            row_data["status"].configure(
                text=f"{pct:.0f}%", text_color=C["accent"]
            )

    def _set_row_status(self, filepath: str, status: str):
        row_data = self._progress_rows.get(filepath)
        if not row_data:
            return
        status_map = {
            "waiting": ("Waiting", C["text_muted"]),
            "converting": ("Converting", C["accent"]),
            "done": ("Done", C["success"]),
            "failed": ("Failed", C["error"]),
            "cancelled": ("Cancelled", C["text_muted"]),
        }
        text, color = status_map.get(status, (status.capitalize(), C["text_secondary"]))
        row_data["status"].configure(text=text, text_color=color)
        if status == "done":
            row_data["bar"].set(1.0)

    # ------------------------------------------------------------------
    # Open output folder
    # ------------------------------------------------------------------

    def _open_output_folder(self):
        import subprocess as sp
        folder = self._output_dir_var.get().strip()
        if not folder and self._files:
            folder = str(Path(self._files[0]).parent)
            if self._subfolder_var.get():
                folder = str(Path(folder) / "Yuki Converted")
        if folder and Path(folder).exists():
            sp.Popen(f'explorer "{folder}"')

    # ------------------------------------------------------------------
    # Cancel all
    # ------------------------------------------------------------------

    def cancel_all(self):
        for item in self._conversion_items.values():
            item.cancel_event.set()
