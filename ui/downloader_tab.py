"""
Main Downloader tab — Hime card style UI.
"""

import logging
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk

from config import DEFAULT_DOWNLOAD_DIR, QUALITY_OPTIONS_VIDEO, QUALITY_OPTIONS_AUDIO, UI_COLORS
from core.detector import detect_platform
from core.downloader import Downloader
from locales.translator import t
from ui.widgets.link_input import LinkInput
from ui.widgets.preview_card import PreviewCard
from ui.queue_panel import QueuePanel

logger = logging.getLogger(__name__)

C = UI_COLORS


class DownloaderTab(ctk.CTkFrame):
    """Content of the Downloader tab — Hime card style."""

    def __init__(self, master, settings: dict, on_download_complete=None, **kwargs):
        super().__init__(master, fg_color=C["bg_primary"], **kwargs)
        self._settings = settings
        self._on_complete = on_download_complete or (lambda task, fp, meta: None)
        self._detected_info: Optional[dict] = None
        self._fmt_audio_active = True

        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

        # Outer padding frame
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.grid(row=0, column=0, sticky="nsew", padx=24, pady=24)
        outer.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        row = 0

        # ---- Card 1: URL Input ----
        url_card = ctk.CTkFrame(outer, fg_color=C["bg_card"], corner_radius=12)
        url_card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        url_card.columnconfigure(0, weight=1)
        row += 1

        ctk.CTkLabel(
            url_card,
            text="DOWNLOAD",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
            anchor="w",
        ).pack(fill="x", padx=16, pady=(12, 4))

        input_row = ctk.CTkFrame(url_card, fg_color="transparent")
        input_row.pack(fill="x", padx=16, pady=(0, 8))
        input_row.columnconfigure(0, weight=1)

        self._link_input = LinkInput(input_row, on_change=self._on_url_change)
        self._link_input.grid(row=0, column=0, sticky="ew")

        self._detect_label = ctk.CTkLabel(
            url_card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=C["text_muted"],
            anchor="w",
        )
        self._detect_label.pack(fill="x", padx=16, pady=(0, 8))

        # ---- Preview Card ----
        self._preview = PreviewCard(
            outer,
            on_add_to_queue=self._add_to_queue,
        )
        self._preview.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        self._preview.grid_remove()
        row += 1

        # ---- Card 2: Options ----
        options_card = ctk.CTkFrame(outer, fg_color=C["bg_card"], corner_radius=12)
        options_card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        options_card.columnconfigure(4, weight=1)
        row += 1

        # Format pill buttons
        fmt_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        fmt_frame.pack(fill="x", padx=16, pady=(12, 8))

        self._fmt_var = ctk.StringVar(value=self._settings.get("default_format", "audio"))

        self._fmt_audio_btn = ctk.CTkButton(
            fmt_frame,
            text="🎵 MP3",
            width=90,
            height=32,
            corner_radius=16,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            text_color="#FFFFFF",
            command=lambda: self._set_format("audio"),
        )
        self._fmt_audio_btn.pack(side="left", padx=(0, 6))

        self._fmt_video_btn = ctk.CTkButton(
            fmt_frame,
            text="🎬 MP4",
            width=90,
            height=32,
            corner_radius=16,
            fg_color=C["bg_elevated"],
            hover_color=C["bg_elevated"],
            text_color=C["text_secondary"],
            command=lambda: self._set_format("video"),
        )
        self._fmt_video_btn.pack(side="left")

        # Quality + folder row
        options_row = ctk.CTkFrame(options_card, fg_color="transparent")
        options_row.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            options_row,
            text=t("quality"),
            text_color=C["text_secondary"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 6))

        self._quality_var = ctk.StringVar(
            value=self._settings.get("default_audio_quality", "320kbps")
        )
        self._quality_menu = ctk.CTkOptionMenu(
            options_row,
            variable=self._quality_var,
            values=QUALITY_OPTIONS_AUDIO,
            width=140,
            fg_color=C["bg_elevated"],
            button_color=C["border"],
            button_hover_color=C["bg_elevated"],
            text_color=C["text_primary"],
        )
        self._quality_menu.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            options_row,
            text=t("download_folder"),
            text_color=C["text_secondary"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 6))

        default_dir = self._settings.get("default_download_dir", str(DEFAULT_DOWNLOAD_DIR))
        self._folder_var = ctk.StringVar(value=default_dir)
        self._folder_entry = ctk.CTkEntry(
            options_row,
            textvariable=self._folder_var,
            fg_color=C["bg_elevated"],
            border_color=C["border"],
            text_color=C["text_primary"],
        )
        self._folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self._browse_btn = ctk.CTkButton(
            options_row,
            text=t("browse"),
            width=80,
            fg_color="transparent",
            border_width=1,
            border_color=C["border"],
            text_color=C["text_secondary"],
            hover_color=C["bg_elevated"],
            command=self._browse_folder,
        )
        self._browse_btn.pack(side="left")

        # ---- Download button ----
        self._download_btn = ctk.CTkButton(
            outer,
            text="⬇  Download",
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            corner_radius=8,
            command=self._add_to_queue,
        )
        self._download_btn.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        row += 1

        # ---- Batch toggle ----
        self._batch_visible = False
        self._batch_toggle = ctk.CTkButton(
            outer,
            text=t("add_multiple"),
            height=32,
            fg_color="transparent",
            hover_color=C["bg_elevated"],
            border_width=1,
            border_color=C["border"],
            text_color=C["text_secondary"],
            command=self._toggle_batch,
        )
        self._batch_toggle.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        row += 1

        self._batch_frame = ctk.CTkFrame(outer, fg_color="transparent")
        self._batch_text = ctk.CTkTextbox(
            self._batch_frame,
            height=100,
            fg_color=C["bg_elevated"],
            border_color=C["border"],
            border_width=1,
            text_color=C["text_primary"],
        )
        self._batch_text.pack(fill="x", pady=4)
        self._batch_add_btn = ctk.CTkButton(
            self._batch_frame,
            text=t("add_batch"),
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            command=self._add_batch,
        )
        self._batch_add_btn.pack(anchor="e", pady=4)

        # ---- Queue card ----
        queue_card = ctk.CTkFrame(outer, fg_color=C["bg_card"], corner_radius=12)
        queue_card.grid(row=row, column=0, sticky="nsew", pady=(0, 0))
        queue_card.columnconfigure(0, weight=1)
        queue_card.rowconfigure(1, weight=1)
        outer.rowconfigure(row, weight=1)
        row += 1

        queue_header = ctk.CTkFrame(queue_card, fg_color="transparent")
        queue_header.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            queue_header,
            text="QUEUE",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
        ).pack(side="left")

        self._queue = QueuePanel(
            queue_card,
            on_download_complete=self._on_download_complete,
            label_text="",
        )
        self._queue.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Init format
        self._on_format_change()

    # ------------------------------------------------------------------
    # Format toggle
    # ------------------------------------------------------------------

    def _set_format(self, fmt: str):
        self._fmt_var.set(fmt)
        self._on_format_change()

    def _on_format_change(self):
        fmt = self._fmt_var.get()
        if fmt == "audio":
            self._fmt_audio_btn.configure(fg_color=C["accent"], text_color="#FFFFFF")
            self._fmt_video_btn.configure(fg_color=C["bg_elevated"], text_color=C["text_secondary"])
            self._quality_menu.configure(values=QUALITY_OPTIONS_AUDIO)
            self._quality_var.set(self._settings.get("default_audio_quality", "320kbps"))
        else:
            self._fmt_audio_btn.configure(fg_color=C["bg_elevated"], text_color=C["text_secondary"])
            self._fmt_video_btn.configure(fg_color=C["accent"], text_color="#FFFFFF")
            self._quality_menu.configure(values=QUALITY_OPTIONS_VIDEO)
            self._quality_var.set(self._settings.get("default_video_quality", "best"))

    # ------------------------------------------------------------------
    # URL detection
    # ------------------------------------------------------------------

    def _on_url_change(self, url: str):
        if not url:
            self._detect_label.configure(text="")
            self._preview.hide()
            self._link_input.set_state("normal")
            return

        self._detect_label.configure(text=t("detecting_platform"), text_color=C["text_muted"])
        result = detect_platform(url)

        if not result["valid"]:
            logger.warning("Invalid URL: %s", url)
            self._detect_label.configure(text=t("error_invalid_url"), text_color=C["error"])
            self._link_input.set_state("invalid")
            self._preview.hide()
            return

        self._link_input.set_state("valid")
        platform = result["platform"]
        logger.info("URL pasted: %s  platform=%s", url, platform)
        self._detect_label.configure(
            text=t("platform_detected", platform=platform),
            text_color=C["text_muted"],
        )
        threading.Thread(
            target=self._fetch_info,
            args=(url,),
            daemon=True,
        ).start()

    def _fetch_info(self, url: str):
        try:
            dl = Downloader()
            info = dl.get_info(url)
            info["url"] = url
            self._detected_info = info
            self.after(0, lambda: self._preview.show(info))
        except Exception as exc:
            self.after(0, lambda: self._detect_label.configure(
                text=t("error_download_failed", reason=str(exc)[:80]),
                text_color=C["error"],
            ))

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    def _browse_folder(self):
        folder = filedialog.askdirectory(
            initialdir=self._folder_var.get(),
            title=t("download_folder"),
        )
        if folder:
            self._folder_var.set(folder)

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def _add_to_queue(self):
        if not self._detected_info:
            url = self._link_input.get()
            if not url:
                return
            result = detect_platform(url)
            if not result["valid"]:
                return
            info = {"title": url, "platform": result["platform"], "url": url,
                    "thumbnail_url": "", "duration": 0, "uploader": ""}
        else:
            info = self._detected_info

        output_dir = self._folder_var.get()
        fmt = self._fmt_var.get()
        quality = self._quality_var.get()

        if self._settings.get("ask_folder_each_time"):
            folder = filedialog.askdirectory(
                initialdir=output_dir,
                title=t("download_folder"),
            )
            if folder:
                output_dir = folder

        self._queue.add_task(
            url=info["url"],
            output_dir=output_dir,
            fmt=fmt,
            quality=quality,
            info=info,
        )
        logger.info("Download queued: %s", info.get("title", info.get("url", "")))

        self._link_input.set("")
        self._link_input.set_state("normal")
        self._detect_label.configure(text="")
        self._preview.hide()
        self._detected_info = None

    def _add_batch(self):
        text = self._batch_text.get("1.0", "end").strip()
        if not text:
            return
        urls = [line.strip() for line in text.splitlines() if line.strip()]
        for url in urls:
            result = detect_platform(url)
            if result["valid"]:
                info = {
                    "title": url, "platform": result["platform"], "url": url,
                    "thumbnail_url": "", "duration": 0, "uploader": "",
                }
                self._queue.add_task(
                    url=url,
                    output_dir=self._folder_var.get(),
                    fmt=self._fmt_var.get(),
                    quality=self._quality_var.get(),
                    info=info,
                )
        self._batch_text.delete("1.0", "end")

    def _toggle_batch(self):
        self._batch_visible = not self._batch_visible
        if self._batch_visible:
            # insert before queue card
            self._batch_frame.grid(row=4, column=0, sticky="ew")
        else:
            self._batch_frame.grid_remove()

    def _on_download_complete(self, task, filepath: str, metadata: dict):
        self._on_complete(task, filepath, metadata)

    # ------------------------------------------------------------------
    # Settings sync
    # ------------------------------------------------------------------

    def update_settings(self, settings: dict):
        self._settings = settings
        self._folder_var.set(settings.get("default_download_dir", str(DEFAULT_DOWNLOAD_DIR)))

    def refresh_text(self):
        self._link_input.refresh_text()
        self._browse_btn.configure(text=t("browse"))
        self._download_btn.configure(text="⬇  " + t("btn_download"))
        self._batch_toggle.configure(text=t("add_multiple"))
        self._batch_add_btn.configure(text=t("add_batch"))
        self._queue.refresh_text()
        self._preview.refresh_text()
