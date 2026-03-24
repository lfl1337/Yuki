"""
Main Downloader tab — URL input, platform detection, preview card, queue.
"""

import threading
from pathlib import Path
from tkinter import filedialog
from typing import Optional

import customtkinter as ctk

from config import DEFAULT_DOWNLOAD_DIR, QUALITY_OPTIONS_VIDEO, QUALITY_OPTIONS_AUDIO
from core.detector import detect_platform
from core.downloader import Downloader
from locales.translator import t
from ui.widgets.link_input import LinkInput
from ui.widgets.preview_card import PreviewCard
from ui.queue_panel import QueuePanel


class DownloaderTab(ctk.CTkFrame):
    """Content of the Downloader tab."""

    def __init__(self, master, settings: dict, on_download_complete=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._settings = settings
        self._on_complete = on_download_complete or (lambda task, fp, meta: None)
        self._detected_info: Optional[dict] = None
        self._detecting = False

        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)

        # ---- URL input ----
        url_frame = ctk.CTkFrame(self, fg_color="transparent")
        url_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        url_frame.columnconfigure(0, weight=1)

        self._link_input = LinkInput(url_frame, on_change=self._on_url_change)
        self._link_input.grid(row=0, column=0, sticky="ew")

        self._detect_label = ctk.CTkLabel(
            url_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        )
        self._detect_label.grid(row=1, column=0, sticky="w", padx=4, pady=2)

        # ---- Preview card ----
        self._preview = PreviewCard(
            self,
            on_add_to_queue=self._add_to_queue,
        )
        self._preview.grid(row=1, column=0, sticky="ew", padx=16, pady=4)

        # ---- Format / Quality / Output ----
        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=8)
        options_frame.columnconfigure(4, weight=1)

        # Format toggle
        self._format_var = ctk.StringVar(value=self._settings.get("default_format", "audio"))
        self._fmt_audio = ctk.CTkRadioButton(
            options_frame,
            text=t("format_audio"),
            variable=self._format_var,
            value="audio",
            command=self._on_format_change,
        )
        self._fmt_audio.grid(row=0, column=0, padx=12, pady=8)

        self._fmt_video = ctk.CTkRadioButton(
            options_frame,
            text=t("format_video"),
            variable=self._format_var,
            value="video",
            command=self._on_format_change,
        )
        self._fmt_video.grid(row=0, column=1, padx=12, pady=8)

        # Quality dropdown
        ctk.CTkLabel(options_frame, text=t("quality")).grid(
            row=0, column=2, padx=(16, 4), pady=8
        )
        self._quality_var = ctk.StringVar(
            value=self._settings.get("default_audio_quality", "320kbps")
        )
        self._quality_menu = ctk.CTkOptionMenu(
            options_frame,
            variable=self._quality_var,
            values=QUALITY_OPTIONS_AUDIO,
            width=130,
        )
        self._quality_menu.grid(row=0, column=3, padx=4, pady=8)

        # Output folder
        ctk.CTkLabel(options_frame, text=t("download_folder")).grid(
            row=0, column=4, padx=(16, 4), pady=8, sticky="e"
        )
        default_dir = self._settings.get("default_download_dir", str(DEFAULT_DOWNLOAD_DIR))
        self._folder_var = ctk.StringVar(value=default_dir)
        self._folder_entry = ctk.CTkEntry(
            options_frame, textvariable=self._folder_var, width=200
        )
        self._folder_entry.grid(row=0, column=5, padx=4, pady=8, sticky="ew")
        options_frame.columnconfigure(5, weight=1)

        self._browse_btn = ctk.CTkButton(
            options_frame,
            text=t("browse"),
            width=80,
            command=self._browse_folder,
        )
        self._browse_btn.grid(row=0, column=6, padx=(4, 12), pady=8)

        # ---- Download button ----
        self._download_btn = ctk.CTkButton(
            self,
            text=t("btn_download"),
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._add_to_queue,
        )
        self._download_btn.grid(row=3, column=0, padx=16, pady=4, sticky="ew")

        # ---- Batch input (collapsible) ----
        self._batch_visible = False
        self._batch_toggle = ctk.CTkButton(
            self,
            text=t("add_multiple"),
            height=32,
            fg_color="transparent",
            hover_color="gray20",
            border_width=1,
            command=self._toggle_batch,
        )
        self._batch_toggle.grid(row=4, column=0, padx=16, pady=(4, 0), sticky="ew")

        self._batch_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._batch_text = ctk.CTkTextbox(self._batch_frame, height=100)
        self._batch_text.insert("1.0", "")
        self._batch_text.pack(fill="x", padx=16, pady=4)
        self._batch_text.configure(state="normal")

        self._batch_add_btn = ctk.CTkButton(
            self._batch_frame,
            text=t("add_batch"),
            command=self._add_batch,
        )
        self._batch_add_btn.pack(anchor="e", padx=16, pady=4)

        # ---- Queue panel ----
        self._queue = QueuePanel(
            self,
            on_download_complete=self._on_download_complete,
            label_text="",
        )
        self._queue.grid(row=6, column=0, sticky="nsew", padx=8, pady=8)
        self.rowconfigure(6, weight=1)

        # Init format
        self._on_format_change()

    # ------------------------------------------------------------------
    # URL detection
    # ------------------------------------------------------------------

    def _on_url_change(self, url: str):
        if not url:
            self._detect_label.configure(text="")
            self._preview.hide()
            self._link_input.set_state("normal")
            return

        self._detect_label.configure(text=t("detecting_platform"))
        result = detect_platform(url)

        if not result["valid"]:
            self._detect_label.configure(text=t("error_invalid_url"), text_color="red")
            self._link_input.set_state("invalid")
            self._preview.hide()
            return

        self._link_input.set_state("valid")
        platform = result["platform"]
        self._detect_label.configure(
            text=t("platform_detected", platform=platform),
            text_color="gray60",
        )
        # Fetch metadata in background
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
                text_color="red",
            ))

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    def _on_format_change(self):
        fmt = self._format_var.get()
        if fmt == "audio":
            self._quality_menu.configure(values=QUALITY_OPTIONS_AUDIO)
            self._quality_var.set(self._settings.get("default_audio_quality", "320kbps"))
        else:
            self._quality_menu.configure(values=QUALITY_OPTIONS_VIDEO)
            self._quality_var.set(self._settings.get("default_video_quality", "best"))

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
        fmt = self._format_var.get()
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

        # Reset input
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
                    fmt=self._format_var.get(),
                    quality=self._quality_var.get(),
                    info=info,
                )
        self._batch_text.delete("1.0", "end")

    def _toggle_batch(self):
        self._batch_visible = not self._batch_visible
        if self._batch_visible:
            self._batch_frame.grid(row=5, column=0, sticky="ew")
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
        self._fmt_audio.configure(text=t("format_audio"))
        self._fmt_video.configure(text=t("format_video"))
        self._browse_btn.configure(text=t("browse"))
        self._download_btn.configure(text=t("btn_download"))
        self._batch_toggle.configure(text=t("add_multiple"))
        self._batch_add_btn.configure(text=t("add_batch"))
        self._queue.refresh_text()
        self._preview.refresh_text()
