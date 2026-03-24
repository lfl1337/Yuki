"""
Preview card showing thumbnail, title, uploader, duration and platform badge.
Shown after a URL is successfully resolved.
"""

import io
import threading
from pathlib import Path
from typing import Optional

import customtkinter as ctk
import requests
from PIL import Image

from config import THUMBNAIL_SIZE, ASSETS_DIR, UI_COLORS
from locales.translator import t

C = UI_COLORS


def _format_duration(seconds: int) -> str:
    if not seconds:
        return ""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


PLATFORM_COLORS = {
    "YouTube":          ("#2D0A0A", "#FF4444"),
    "YouTube Shorts":   ("#2D0A0A", "#FF4444"),
    "YouTube Playlist": ("#2D0A0A", "#FF4444"),
    "Instagram":        ("#2D0D1F", "#C13584"),
    "TikTok":           (C["bg_elevated"], C["text_secondary"]),
    "Twitter/X":        ("#0A1928", "#1DA1F2"),
    "SoundCloud":       ("#2D1500", "#FF5500"),
    "Spotify":          ("#0A1F12", "#1DB954"),
    "Facebook":         ("#0A1128", "#1877F2"),
    "Vimeo":            ("#0A1E28", "#1AB7EA"),
    "Dailymotion":      ("#0A1428", "#0066DC"),
    "Twitch":           ("#1E0A2D", "#9146FF"),
    "Reddit":           ("#2D0F00", "#FF4500"),
}


class PreviewCard(ctk.CTkFrame):
    """Displays metadata for a detected URL."""

    def __init__(self, master, on_add_to_queue=None, **kwargs):
        super().__init__(
            master, corner_radius=12,
            fg_color=C["bg_card"],
            **kwargs,
        )
        self._on_add = on_add_to_queue or (lambda: None)
        self._thumb_image: Optional[ctk.CTkImage] = None
        self._placeholder = self._load_placeholder()
        self._build()
        self.grid_remove()

    def _load_placeholder(self) -> Optional[ctk.CTkImage]:
        path = ASSETS_DIR / "placeholder_cover.png"
        try:
            img = Image.open(path).resize(THUMBNAIL_SIZE, Image.LANCZOS)
            return ctk.CTkImage(img, size=THUMBNAIL_SIZE)
        except Exception:
            blank = Image.new("RGB", THUMBNAIL_SIZE, C["bg_elevated"])
            return ctk.CTkImage(blank, size=THUMBNAIL_SIZE)

    def _build(self):
        self.columnconfigure(1, weight=1)

        # Thumbnail
        self._thumb_label = ctk.CTkLabel(self, text="", image=self._placeholder)
        self._thumb_label.grid(row=0, column=0, rowspan=4, padx=16, pady=16, sticky="n")

        # Platform badge
        self._platform_badge = ctk.CTkLabel(
            self,
            text="",
            width=120,
            height=24,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self._platform_badge.grid(row=0, column=1, padx=8, pady=(16, 2), sticky="w")

        # Title
        self._title_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["text_primary"],
            wraplength=500,
            justify="left",
            anchor="w",
        )
        self._title_label.grid(row=1, column=1, padx=8, pady=2, sticky="w")

        # Uploader + duration
        self._meta_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=C["text_secondary"],
            anchor="w",
        )
        self._meta_label.grid(row=2, column=1, padx=8, pady=2, sticky="w")

        # Add to queue button
        self._add_btn = ctk.CTkButton(
            self,
            text=t("btn_add_to_queue"),
            width=140,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            command=self._on_add,
        )
        self._add_btn.grid(row=3, column=1, padx=8, pady=(4, 16), sticky="w")

    def show(self, info: dict):
        platform = info.get("platform", "Unknown")
        title = info.get("title", "")
        uploader = info.get("uploader", "")
        duration = _format_duration(info.get("duration", 0))
        thumbnail_url = info.get("thumbnail_url", "")

        # Platform badge with soft colors
        bg, fg = PLATFORM_COLORS.get(platform, (C["accent_soft"], C["accent"]))
        self._platform_badge.configure(text=f"  {platform}  ", fg_color=bg, text_color=fg)

        self._title_label.configure(text=title)

        meta = uploader
        if duration:
            meta += f"  •  {duration}"
        self._meta_label.configure(text=meta)

        self._thumb_label.configure(image=self._placeholder)
        if thumbnail_url:
            threading.Thread(
                target=self._fetch_thumbnail,
                args=(thumbnail_url,),
                daemon=True,
            ).start()

        self.grid()

    def hide(self):
        self.grid_remove()

    def _fetch_thumbnail(self, url: str):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            img = img.resize(THUMBNAIL_SIZE, Image.LANCZOS)
            ctk_img = ctk.CTkImage(img, size=THUMBNAIL_SIZE)
            self._thumb_image = None  # release old reference
            self._thumb_image = ctk_img
            self._thumb_label.after(0, lambda: self._thumb_label.configure(image=ctk_img))
        except Exception:
            pass

    def refresh_text(self):
        self._add_btn.configure(text=t("btn_add_to_queue"))
