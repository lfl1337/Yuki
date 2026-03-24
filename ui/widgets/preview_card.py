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
from PIL import Image, ImageTk

from config import THUMBNAIL_SIZE, ASSETS_DIR
from locales.translator import t


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
    "YouTube": "#FF0000",
    "YouTube Shorts": "#FF0000",
    "YouTube Playlist": "#FF0000",
    "Instagram": "#C13584",
    "TikTok": "#000000",
    "Twitter/X": "#1DA1F2",
    "SoundCloud": "#FF5500",
    "Spotify": "#1DB954",
    "Facebook": "#1877F2",
    "Vimeo": "#1AB7EA",
    "Dailymotion": "#0066DC",
    "Twitch": "#9146FF",
    "Reddit": "#FF4500",
}


class PreviewCard(ctk.CTkFrame):
    """Displays metadata for a detected URL."""

    def __init__(self, master, on_add_to_queue=None, **kwargs):
        super().__init__(master, corner_radius=12, **kwargs)
        self._on_add = on_add_to_queue or (lambda: None)
        self._thumb_image: Optional[ctk.CTkImage] = None
        self._placeholder = self._load_placeholder()
        self._build()
        self.grid_remove()  # Hidden by default

    def _load_placeholder(self) -> Optional[ctk.CTkImage]:
        path = ASSETS_DIR / "placeholder_cover.png"
        try:
            img = Image.open(path).resize(THUMBNAIL_SIZE, Image.LANCZOS)
            return ctk.CTkImage(img, size=THUMBNAIL_SIZE)
        except Exception:
            return None

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
            text_color="gray60",
            anchor="w",
        )
        self._meta_label.grid(row=2, column=1, padx=8, pady=2, sticky="w")

        # Add to queue button
        self._add_btn = ctk.CTkButton(
            self,
            text=t("btn_add_to_queue"),
            width=140,
            command=self._on_add,
        )
        self._add_btn.grid(row=3, column=1, padx=8, pady=(4, 16), sticky="w")

    def show(self, info: dict):
        """Populate and show the card with metadata dict."""
        platform = info.get("platform", "Unknown")
        title = info.get("title", "")
        uploader = info.get("uploader", "")
        duration = _format_duration(info.get("duration", 0))
        thumbnail_url = info.get("thumbnail_url", "")

        # Platform badge
        color = PLATFORM_COLORS.get(platform, "#555555")
        self._platform_badge.configure(text=f"  {platform}  ", fg_color=color)

        # Title
        self._title_label.configure(text=title)

        # Uploader + duration
        meta = uploader
        if duration:
            meta += f"  •  {duration}"
        self._meta_label.configure(text=meta)

        # Show placeholder, then load real thumbnail
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
            self._thumb_image = ctk_img
            self._thumb_label.after(0, lambda: self._thumb_label.configure(image=ctk_img))
        except Exception:
            pass

    def refresh_text(self):
        self._add_btn.configure(text=t("btn_add_to_queue"))
