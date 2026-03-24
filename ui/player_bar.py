"""
Persistent bottom player bar — cover art, title/artist, transport controls,
seekbar, and volume slider.
"""

import threading
from pathlib import Path
from typing import Callable, List, Optional

import customtkinter as ctk
from PIL import Image

from config import PLAYER_COVER_SIZE, ASSETS_DIR
from core.player import AudioPlayer
from locales.translator import t


class PlayerBar(ctk.CTkFrame):
    """80px bottom bar, full width."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=80, corner_radius=0, **kwargs)
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
        # Cover art
        self._cover_label = ctk.CTkLabel(self, text="", image=self._placeholder)
        self._cover_label.pack(side="left", padx=(12, 8), pady=8)

        # Title + artist
        info_frame = ctk.CTkFrame(self, fg_color="transparent", width=180)
        info_frame.pack(side="left", padx=4, pady=8)
        info_frame.pack_propagate(False)

        self._title_label = ctk.CTkLabel(
            info_frame,
            text=t("no_file_loaded"),
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self._title_label.pack(fill="x")

        self._artist_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
        )
        self._artist_label.pack(fill="x")

        # Controls
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.pack(side="left", padx=16, pady=8)

        self._prev_btn = ctk.CTkButton(
            ctrl_frame, text="⏮", width=36, height=36,
            command=self._prev,
            fg_color="transparent", hover_color="gray30",
        )
        self._prev_btn.pack(side="left", padx=2)

        self._play_btn = ctk.CTkButton(
            ctrl_frame, text="▶", width=44, height=44,
            command=self._toggle_play,
            font=ctk.CTkFont(size=16),
        )
        self._play_btn.pack(side="left", padx=4)

        self._stop_btn = ctk.CTkButton(
            ctrl_frame, text="⏹", width=36, height=36,
            command=self._stop,
            fg_color="transparent", hover_color="gray30",
        )
        self._stop_btn.pack(side="left", padx=2)

        self._next_btn = ctk.CTkButton(
            ctrl_frame, text="⏭", width=36, height=36,
            command=self._next,
            fg_color="transparent", hover_color="gray30",
        )
        self._next_btn.pack(side="left", padx=2)

        # Seekbar area
        seek_frame = ctk.CTkFrame(self, fg_color="transparent")
        seek_frame.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        self._seek_slider = ctk.CTkSlider(
            seek_frame,
            from_=0, to=1,
            command=self._on_seek_drag,
        )
        self._seek_slider.pack(fill="x")
        self._seek_slider.bind("<ButtonPress-1>", lambda e: setattr(self, "_seeking", True))
        self._seek_slider.bind("<ButtonRelease-1>", self._on_seek_release)

        time_row = ctk.CTkFrame(seek_frame, fg_color="transparent")
        time_row.pack(fill="x")
        self._pos_label = ctk.CTkLabel(time_row, text="0:00", font=ctk.CTkFont(size=10))
        self._pos_label.pack(side="left")
        self._dur_label = ctk.CTkLabel(time_row, text="0:00", font=ctk.CTkFont(size=10))
        self._dur_label.pack(side="right")

        # Volume
        vol_frame = ctk.CTkFrame(self, fg_color="transparent", width=120)
        vol_frame.pack(side="right", padx=12, pady=8)
        vol_frame.pack_propagate(False)

        ctk.CTkLabel(vol_frame, text="🔊", font=ctk.CTkFont(size=14)).pack(side="left")
        self._volume_slider = ctk.CTkSlider(
            vol_frame,
            from_=0, to=1,
            width=80,
            command=self._on_volume,
        )
        self._volume_slider.set(0.8)
        self._volume_slider.pack(side="left", padx=4)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_file(self, filepath: str, title: str = "", artist: str = ""):
        """Load and immediately play a file."""
        try:
            self._player.load(filepath)
            self._player.play()
            self._play_btn.configure(text="⏸")
            dur = self._player.get_duration()
            self._seek_slider.configure(to=max(dur, 1))
            self._dur_label.configure(text=self._fmt_time(dur))
            self._title_label.configure(text=title or Path(filepath).stem)
            self._artist_label.configure(text=artist)

            # Add to history
            if filepath not in self._history:
                self._history.append(filepath)
                self._history_idx = len(self._history) - 1

            # Cover art
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

    def _stop(self):
        self._player.stop()
        self._play_btn.configure(text="▶")
        self._seek_slider.set(0)
        self._pos_label.configure(text="0:00")

    def _prev(self):
        if self._history_idx > 0:
            self._history_idx -= 1
            self.load_file(self._history[self._history_idx])

    def _next(self):
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self.load_file(self._history[self._history_idx])

    def _on_seek_drag(self, value):
        pos = float(value)
        self._pos_label.configure(text=self._fmt_time(pos))

    def _on_seek_release(self, event):
        self._seeking = False
        value = self._seek_slider.get()
        self._player.seek(float(value))

    def _on_volume(self, value):
        self._player.set_volume(float(value))

    # ------------------------------------------------------------------
    # Position callback (from player thread → schedule via after)
    # ------------------------------------------------------------------

    def _on_position(self, seconds: float):
        self.after(0, self._update_seekbar, seconds)

    def _update_seekbar(self, seconds: float):
        if self._seeking:
            return
        dur = self._player.get_duration()
        if dur > 0:
            self._seek_slider.set(seconds)
        self._pos_label.configure(text=self._fmt_time(seconds))

    # ------------------------------------------------------------------
    # Cover art
    # ------------------------------------------------------------------

    def _load_cover_from_file(self, filepath: str):
        def worker():
            try:
                from core.tagger import MP3Tagger
                img = MP3Tagger().get_cover_art(filepath)
                if img:
                    img = img.resize(PLAYER_COVER_SIZE, Image.LANCZOS)
                    ctk_img = ctk.CTkImage(img, size=PLAYER_COVER_SIZE)
                    self.after(0, self._set_cover, ctk_img)
                else:
                    self.after(0, self._set_cover, None)
            except Exception:
                self.after(0, self._set_cover, None)

        threading.Thread(target=worker, daemon=True).start()

    def _set_cover(self, img: Optional[ctk.CTkImage]):
        display = img if img else self._placeholder
        self._cover_label.configure(image=display)

    def _load_placeholder(self) -> ctk.CTkImage:
        path = ASSETS_DIR / "placeholder_cover.png"
        try:
            img = Image.open(path).resize(PLAYER_COVER_SIZE, Image.LANCZOS)
            return ctk.CTkImage(img, size=PLAYER_COVER_SIZE)
        except Exception:
            blank = Image.new("RGB", PLAYER_COVER_SIZE, "#222222")
            return ctk.CTkImage(blank, size=PLAYER_COVER_SIZE)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = int(seconds)
        m = seconds // 60
        s = seconds % 60
        return f"{m}:{s:02d}"
