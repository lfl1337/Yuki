"""
Persistent bottom player bar — rounded cover, title/artist, transport controls,
seekbar with time labels, volume slider.
"""

import threading
from pathlib import Path
from tkinter import filedialog
from typing import List, Optional

import customtkinter as ctk
from PIL import Image, ImageDraw

from config import PLAYER_COVER_SIZE, ASSETS_DIR, UI_COLORS
from core.player import AudioPlayer
from locales.translator import t

C = UI_COLORS


def _make_rounded(img: Image.Image, size: tuple, radius: int = 8) -> Image.Image:
    """Crop PIL image into a rounded rectangle with transparent background."""
    img = img.resize(size, Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    result = Image.new("RGBA", size, (0, 0, 0, 0))
    result.paste(img, mask=mask)
    return result


class PlayerBar(ctk.CTkFrame):
    """Bottom player bar with rounded cover and seekbar."""

    COVER_SIZE = (48, 48)

    def __init__(self, master, **kwargs):
        super().__init__(
            master, height=72, corner_radius=0,
            fg_color=C["bg_secondary"],
            border_width=1, border_color=C["border"],
            **kwargs,
        )
        self.pack_propagate(False)

        self._player = AudioPlayer(position_callback=self._on_position)
        self._history: List[str] = []
        self._history_idx: int = -1
        self._seeking: bool = False
        self._placeholder = self._load_placeholder()

        self._build()
        self._set_cover(None)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self):
        # Open file button
        self._open_btn = ctk.CTkButton(
            self,
            text="Open",
            width=70, height=36,
            fg_color=C["bg_elevated"],
            hover_color=C["bg_elevated"],
            border_width=1, border_color=C["border"],
            command=self._open_file,
            font=ctk.CTkFont(size=12),
        )
        self._open_btn.pack(side="left", padx=(8, 2), pady=8)

        # Rounded cover art
        self._cover_label = ctk.CTkLabel(self, text="", image=self._placeholder)
        self._cover_label.pack(side="left", padx=(4, 8), pady=8)

        # Title + artist
        info_frame = ctk.CTkFrame(self, fg_color="transparent", width=190)
        info_frame.pack(side="left", padx=4, pady=8)
        info_frame.pack_propagate(False)

        self._title_label = ctk.CTkLabel(
            info_frame,
            text=t("no_file_loaded"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C["text_primary"],
            anchor="w",
        )
        self._title_label.pack(fill="x")

        self._artist_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=C["text_secondary"],
            anchor="w",
        )
        self._artist_label.pack(fill="x")

        # Controls
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(side="left", padx=12, pady=8)

        for text, cmd, size in [
            ("⏮", self._prev, 32),
            ("◀◀", self._rewind, 32),
        ]:
            ctk.CTkButton(
                ctrl_frame, text=text, width=size, height=size,
                command=cmd,
                fg_color="transparent",
                hover_color=C["bg_elevated"],
                text_color=C["text_secondary"],
            ).pack(side="left", padx=2)

        self._play_btn = ctk.CTkButton(
            ctrl_frame, text="▶", width=44, height=44,
            command=self._toggle_play,
            font=ctk.CTkFont(size=16),
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            corner_radius=22,
            text_color=C["text_primary"],
        )
        self._play_btn.pack(side="left", padx=6)

        for text, cmd, size in [
            ("▶▶", self._forward, 32),
            ("⏭", self._next, 32),
        ]:
            ctk.CTkButton(
                ctrl_frame, text=text, width=size, height=size,
                command=cmd,
                fg_color="transparent",
                hover_color=C["bg_elevated"],
                text_color=C["text_secondary"],
            ).pack(side="left", padx=2)

        # Seekbar area (expands)
        seek_frame = ctk.CTkFrame(self, fg_color="transparent")
        seek_frame.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        self._seek_slider = ctk.CTkSlider(
            seek_frame,
            from_=0, to=1,
            command=self._on_seek_drag,
            button_color=C["accent"],
            button_hover_color=C["accent_hover"],
            progress_color=C["accent"],
            fg_color=C["border"],
        )
        self._seek_slider.pack(fill="x")
        self._seek_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "_seeking", True))
        self._seek_slider.bind("<ButtonRelease-1>", self._on_seek_release)

        time_row = ctk.CTkFrame(seek_frame, fg_color="transparent")
        time_row.pack(fill="x")
        self._pos_label = ctk.CTkLabel(
            time_row, text="0:00",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
        )
        self._pos_label.pack(side="left")
        self._dur_label = ctk.CTkLabel(
            time_row, text="0:00",
            font=ctk.CTkFont(size=10),
            text_color=C["text_muted"],
        )
        self._dur_label.pack(side="right")

        # Volume
        vol_frame = ctk.CTkFrame(self, fg_color="transparent", width=120)
        vol_frame.pack(side="right", padx=12, pady=8)
        vol_frame.pack_propagate(False)

        ctk.CTkLabel(
            vol_frame, text="🔊",
            font=ctk.CTkFont(size=14),
            text_color=C["text_secondary"],
        ).pack(side="left")
        self._volume_slider = ctk.CTkSlider(
            vol_frame,
            from_=0, to=1,
            width=80,
            command=self._on_volume,
            button_color=C["accent"],
            button_hover_color=C["accent_hover"],
            progress_color=C["accent"],
            fg_color=C["border"],
        )
        self._volume_slider.set(0.8)
        self._volume_slider.pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_file(self, filepath: str, title: str = "", artist: str = "", autoplay: bool = True):
        try:
            self._player.load(filepath)
            if autoplay:
                self._player.play()
                self._play_btn.configure(text="⏸")
            dur = self._player.get_duration()
            self._seek_slider.configure(to=max(dur, 1))
            self._dur_label.configure(text=self._fmt_time(dur))

            if not title or not artist:
                self._load_tags_async(filepath, title, artist)
            else:
                self._title_label.configure(text=title)
                self._artist_label.configure(text=artist)

            if filepath not in self._history:
                self._history.append(filepath)
                self._history_idx = len(self._history) - 1
            else:
                self._history_idx = self._history.index(filepath)

            self._load_cover_from_file(filepath)
        except Exception as exc:
            self._title_label.configure(text=str(exc))

    def get_player(self) -> AudioPlayer:
        return self._player

    def refresh_text(self):
        if not self._player.get_filepath():
            self._title_label.configure(text=t("no_file_loaded"))

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Open Audio File",
            filetypes=[("Audio files", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.opus"), ("All files", "*.*")],
        )
        if path:
            self.load_file(path)

    def _toggle_play(self):
        if self._player.is_playing():
            self._player.pause()
            self._play_btn.configure(text="▶")
        elif self._player.is_paused():
            self._player.resume()
            self._play_btn.configure(text="⏸")
        else:
            self._player.play()
            self._play_btn.configure(text="⏸")

    def _prev(self):
        if self._history_idx > 0:
            self._history_idx -= 1
            self.load_file(self._history[self._history_idx])

    def _next(self):
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self.load_file(self._history[self._history_idx])

    def _rewind(self):
        pos = self._player.get_position()
        self._player.seek(max(0, pos - 10))

    def _forward(self):
        pos = self._player.get_position()
        dur = self._player.get_duration()
        self._player.seek(min(dur, pos + 10))

    def _on_seek_drag(self, value):
        self._pos_label.configure(text=self._fmt_time(float(value)))

    def _on_seek_release(self, event):
        self._seeking = False
        value = self._seek_slider.get()
        self._player.seek(float(value))

    def _on_volume(self, value):
        self._player.set_volume(float(value))

    # ------------------------------------------------------------------
    # Position callback
    # ------------------------------------------------------------------

    def _on_position(self, seconds: float):
        try:
            self.after(0, self._update_seekbar, seconds)
        except Exception:
            pass

    def _update_seekbar(self, seconds: float):
        try:
            if self._seeking:
                return
            dur = self._player.get_duration()
            if dur > 0:
                self._seek_slider.set(seconds)
            self._pos_label.configure(text=self._fmt_time(seconds))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Tags async
    # ------------------------------------------------------------------

    def _load_tags_async(self, filepath: str, fallback_title: str, fallback_artist: str):
        def worker():
            try:
                from core.tagger import MP3Tagger
                tags = MP3Tagger().read_tags(filepath)
                title = tags.get("title") or fallback_title or Path(filepath).stem
                artist = tags.get("artist") or fallback_artist or ""
                self.after(0, lambda: self._title_label.configure(text=title))
                self.after(0, lambda: self._artist_label.configure(text=artist))
            except Exception:
                title = fallback_title or Path(filepath).stem
                self.after(0, lambda: self._title_label.configure(text=title))
                self.after(0, lambda: self._artist_label.configure(text=fallback_artist))
        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Cover art
    # ------------------------------------------------------------------

    def _load_cover_from_file(self, filepath: str):
        def worker():
            try:
                from core.tagger import MP3Tagger
                img = MP3Tagger().get_cover_art(filepath)
                if img:
                    rounded = _make_rounded(img, self.COVER_SIZE, radius=8)
                    ctk_img = ctk.CTkImage(rounded, size=self.COVER_SIZE)
                    self.after(0, self._set_cover, ctk_img)
                else:
                    self.after(0, self._set_cover, None)
            except Exception:
                self.after(0, self._set_cover, None)
        threading.Thread(target=worker, daemon=True).start()

    def _set_cover(self, img):
        try:
            display = img if img else self._placeholder
            self._cover_label.configure(image=display)
        except Exception:
            pass

    def _load_placeholder(self) -> ctk.CTkImage:
        path = ASSETS_DIR / "placeholder_cover.png"
        try:
            img = Image.open(path)
            rounded = _make_rounded(img, self.COVER_SIZE, radius=8)
            return ctk.CTkImage(rounded, size=self.COVER_SIZE)
        except Exception:
            blank = Image.new("RGBA", self.COVER_SIZE, (28, 28, 40, 255))
            rounded = _make_rounded(blank, self.COVER_SIZE, radius=8)
            return ctk.CTkImage(rounded, size=self.COVER_SIZE)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = int(max(0, seconds))
        m = seconds // 60
        s = seconds % 60
        return f"{m}:{s:02d}"
