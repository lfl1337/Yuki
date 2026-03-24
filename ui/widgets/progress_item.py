"""
A single download queue item showing thumbnail, title, progress bar,
speed, ETA, status label, and cancel/retry buttons.
"""

import io
import threading
from typing import Callable, Optional

import customtkinter as ctk
import requests
from PIL import Image

from config import QUEUE_THUMB_SIZE, ASSETS_DIR, UI_COLORS
from locales.translator import t

C = UI_COLORS


def _fmt_speed(bps: float) -> str:
    if bps <= 0:
        return ""
    if bps >= 1_000_000:
        return f"{bps/1_000_000:.1f} MB/s"
    if bps >= 1_000:
        return f"{bps/1_000:.0f} KB/s"
    return f"{bps:.0f} B/s"


def _fmt_eta(seconds: int) -> str:
    if seconds <= 0:
        return ""
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"
    if seconds >= 60:
        m = seconds // 60
        s = seconds % 60
        return f"{m}m {s}s"
    return f"{seconds}s"


STATUS_COLORS = {
    "queued":      C["text_muted"],
    "downloading": C["accent"],
    "processing":  C["warning"],
    "done":        C["success"],
    "error":       C["error"],
    "cancelled":   C["text_muted"],
}


class ProgressItem(ctk.CTkFrame):
    """Single row in the download queue."""

    def __init__(
        self,
        master,
        title: str,
        platform: str,
        fmt: str,
        quality: str,
        thumbnail_url: str = "",
        on_cancel: Optional[Callable] = None,
        on_retry: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(master, corner_radius=8, fg_color=C["bg_elevated"], **kwargs)
        self._on_cancel = on_cancel or (lambda: None)
        self._on_retry = on_retry or (lambda: None)
        self._title = title
        self._platform = platform
        self._fmt = fmt
        self._quality = quality
        self._thumb_image: Optional[ctk.CTkImage] = None

        self._build(title, platform, fmt, quality)

        if thumbnail_url:
            threading.Thread(
                target=self._fetch_thumb, args=(thumbnail_url,), daemon=True
            ).start()

    def _build(self, title, platform, fmt, quality):
        self.columnconfigure(1, weight=1)

        # Thumbnail
        placeholder = self._load_placeholder()
        self._thumb_label = ctk.CTkLabel(self, text="", image=placeholder)
        self._thumb_label.grid(row=0, column=0, rowspan=3, padx=10, pady=10, sticky="n")

        # Title
        self._title_label = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C["text_primary"],
            anchor="w",
            wraplength=400,
        )
        self._title_label.grid(row=0, column=1, padx=8, pady=(10, 0), sticky="w")

        # Meta
        meta = f"{platform}  •  {fmt}  •  {quality}"
        self._meta_label = ctk.CTkLabel(
            self,
            text=meta,
            font=ctk.CTkFont(size=11),
            text_color=C["text_muted"],
            anchor="w",
        )
        self._meta_label.grid(row=1, column=1, padx=8, pady=0, sticky="w")

        # Progress bar — 3px height, ACCENT fill
        self._progress = ctk.CTkProgressBar(
            self,
            height=3,
            corner_radius=2,
            progress_color=C["accent"],
            fg_color=C["border"],
        )
        self._progress.set(0)
        self._progress.grid(row=2, column=1, padx=8, pady=(4, 0), sticky="ew")

        # Status row
        status_row = ctk.CTkFrame(self, fg_color="transparent")
        status_row.grid(row=3, column=1, padx=8, pady=(2, 8), sticky="ew")
        status_row.columnconfigure(0, weight=1)

        self._status_label = ctk.CTkLabel(
            status_row,
            text=t("status_queued"),
            font=ctk.CTkFont(size=11),
            text_color=STATUS_COLORS["queued"],
            anchor="w",
        )
        self._status_label.grid(row=0, column=0, sticky="w")

        self._speed_label = ctk.CTkLabel(
            status_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=C["text_muted"],
        )
        self._speed_label.grid(row=0, column=1, padx=8)

        self._eta_label = ctk.CTkLabel(
            status_row,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=C["text_muted"],
        )
        self._eta_label.grid(row=0, column=2, padx=(0, 8))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=4, padx=10, pady=10, sticky="ne")

        self._cancel_btn = ctk.CTkButton(
            btn_frame,
            text=t("btn_cancel"),
            width=70,
            height=28,
            fg_color="transparent",
            border_width=1,
            border_color=C["border"],
            text_color=C["text_muted"],
            hover_color=C["error"],
            command=self._on_cancel,
        )
        self._cancel_btn.pack(pady=2)

        self._retry_btn = ctk.CTkButton(
            btn_frame,
            text=t("retry"),
            width=70,
            height=28,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            command=self._on_retry,
        )
        self._retry_btn.pack(pady=2)
        self._retry_btn.pack_forget()

    def _load_placeholder(self) -> ctk.CTkImage:
        path = ASSETS_DIR / "placeholder_cover.png"
        try:
            img = Image.open(path).resize(QUEUE_THUMB_SIZE, Image.LANCZOS)
            return ctk.CTkImage(img, size=QUEUE_THUMB_SIZE)
        except Exception:
            blank = Image.new("RGB", QUEUE_THUMB_SIZE, C["bg_card"])
            return ctk.CTkImage(blank, size=QUEUE_THUMB_SIZE)

    def _fetch_thumb(self, url: str):
        try:
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img = img.resize(QUEUE_THUMB_SIZE, Image.LANCZOS)
            ctk_img = ctk.CTkImage(img, size=QUEUE_THUMB_SIZE)
            self._thumb_image = ctk_img
            self._thumb_label.after(0, lambda: self._thumb_label.configure(image=ctk_img))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public update methods
    # ------------------------------------------------------------------

    def update_progress(self, percent: float, speed: float, eta: int, filename: str = ""):
        self._progress.set(percent / 100.0)
        self._speed_label.configure(text=_fmt_speed(speed))
        self._eta_label.configure(text=_fmt_eta(eta))
        self._status_label.configure(
            text=t("status_downloading"),
            text_color=STATUS_COLORS["downloading"],
        )

    def set_status(self, status: str, message: str = ""):
        key = f"status_{status}"
        text = t(key) if not message else message
        color = STATUS_COLORS.get(status, C["text_muted"])
        self._status_label.configure(text=text, text_color=color)
        if status == "done":
            self._progress.set(1.0)
            self._cancel_btn.configure(state="disabled")
        elif status == "error":
            self._retry_btn.pack()
            self._cancel_btn.configure(state="disabled")
        elif status == "cancelled":
            self._cancel_btn.configure(state="disabled")
        elif status == "processing":
            self._progress.configure(mode="indeterminate")
            self._progress.start()

    def stop_indeterminate(self):
        self._progress.stop()
        self._progress.configure(mode="determinate")
