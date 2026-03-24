"""
Audio player using pygame.mixer.
Runs a background thread that fires position_callback every 500ms.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import pygame
    _PYGAME_AVAILABLE = True
except ImportError:
    _PYGAME_AVAILABLE = False
    logger.warning("pygame not available — audio player disabled")


class AudioPlayer:
    """Thread-safe audio player wrapper around pygame.mixer."""

    def __init__(self, position_callback: Optional[Callable[[float], None]] = None):
        self._position_cb = position_callback or (lambda s: None)
        self._filepath: Optional[Path] = None
        self._duration: float = 0.0
        self._position: float = 0.0
        self._playing: bool = False
        self._paused: bool = False
        self._volume: float = 0.8
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitor = threading.Event()

        if _PYGAME_AVAILABLE:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            except Exception as exc:
                logger.error("pygame.mixer.init failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, filepath: str):
        """Load an audio file. Does not start playback."""
        if not _PYGAME_AVAILABLE:
            return
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        self.stop()
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
        try:
            pygame.mixer.music.load(str(filepath))
            self._filepath = filepath
            self._position = 0.0
            self._duration = self._get_duration(filepath)
            self._playing = False
            self._paused = False
            logger.info("Player loaded: %s", filepath)
        except Exception as exc:
            logger.error("load failed: %s", exc)
            raise RuntimeError(f"Cannot load audio file: {exc}") from exc

    def play(self):
        """Start playback from the beginning or resume if paused."""
        if not _PYGAME_AVAILABLE or self._filepath is None:
            return
        try:
            if self._paused:
                pygame.mixer.music.unpause()
                self._paused = False
            else:
                pygame.mixer.music.play()
                self._position = 0.0
            self._playing = True
            pygame.mixer.music.set_volume(self._volume)
            self._start_monitor()
            logger.info("Playback started")
        except Exception as exc:
            logger.error("play failed: %s", exc)

    def pause(self):
        """Pause playback."""
        if not _PYGAME_AVAILABLE:
            return
        try:
            pygame.mixer.music.pause()
            self._paused = True
            self._playing = False
            logger.info("Playback paused at %.1fs", self._position)
        except Exception as exc:
            logger.error("pause failed: %s", exc)

    def resume(self):
        """Resume paused playback."""
        if not _PYGAME_AVAILABLE:
            return
        try:
            pygame.mixer.music.unpause()
            self._paused = False
            self._playing = True
        except Exception as exc:
            logger.error("resume failed: %s", exc)

    def stop(self):
        """Stop playback and reset position."""
        if not _PYGAME_AVAILABLE:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self._playing = False
        self._paused = False
        self._position = 0.0
        logger.info("Playback stopped")
        self._stop_monitor.set()

    def seek(self, seconds: float):
        """Seek to position in seconds."""
        if not _PYGAME_AVAILABLE or self._filepath is None:
            return
        try:
            seconds = max(0.0, min(seconds, self._duration))
            was_playing = self._playing
            pygame.mixer.music.play(start=seconds)
            self._position = seconds
            if not was_playing:
                pygame.mixer.music.pause()
                self._playing = False
                self._paused = True
        except Exception as exc:
            logger.error("seek failed: %s", exc)

    def get_position(self) -> float:
        """Return current playback position in seconds."""
        if not _PYGAME_AVAILABLE or not self._playing:
            return self._position
        try:
            ms = pygame.mixer.music.get_pos()
            if ms < 0:
                return self._position
            return self._position + ms / 1000.0
        except Exception:
            return self._position

    def get_duration(self) -> float:
        """Return total duration in seconds."""
        return self._duration

    def set_volume(self, volume: float):
        """Set volume between 0.0 and 1.0."""
        self._volume = max(0.0, min(1.0, volume))
        if _PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.set_volume(self._volume)
            except Exception:
                pass

    def is_playing(self) -> bool:
        """Return True if currently playing (not paused, not stopped)."""
        if not _PYGAME_AVAILABLE:
            return False
        try:
            return pygame.mixer.music.get_busy() and not self._paused
        except Exception:
            return False

    def is_paused(self) -> bool:
        return self._paused

    def get_filepath(self) -> Optional[Path]:
        return self._filepath

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_duration(self, filepath: Path) -> float:
        ext = filepath.suffix.lower()
        try:
            if ext in (".mp3",):
                from mutagen.mp3 import MP3 as MuMP3
                return MuMP3(filepath).info.length
            elif ext in (".m4a", ".mp4", ".aac"):
                from mutagen.mp4 import MP4 as MuMP4
                return MuMP4(filepath).info.length
            else:
                from mutagen import File as MuFile
                audio = MuFile(filepath)
                if audio is not None and hasattr(audio, "info") and hasattr(audio.info, "length"):
                    return audio.info.length
                if _PYGAME_AVAILABLE:
                    return pygame.mixer.Sound(str(filepath)).get_length()
                return 0.0
        except Exception:
            try:
                if _PYGAME_AVAILABLE:
                    return pygame.mixer.Sound(str(filepath)).get_length()
            except Exception:
                pass
            return 0.0

    def shutdown(self):
        """Stop playback and release all pygame resources."""
        self.stop()
        if _PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.unload()
                pygame.mixer.quit()
                pygame.quit()
            except Exception:
                pass

    def update_filepath(self, new_path: str):
        """Update stored filepath after a rename without reloading audio."""
        self._filepath = Path(new_path)

    def _start_monitor(self):
        self._stop_monitor.clear()
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="player-monitor"
        )
        self._monitor_thread.start()

    def _monitor_loop(self):
        from config import PLAYER_UPDATE_INTERVAL_MS
        interval = PLAYER_UPDATE_INTERVAL_MS / 1000.0
        # Use wait() instead of sleep() so the loop exits immediately when
        # _stop_monitor is set (e.g. on stop/shutdown), rather than waiting
        # up to `interval` seconds for the next sleep cycle to complete.
        while not self._stop_monitor.wait(interval):
            if self._playing and not self._paused:
                pos = self.get_position()
                self._position_cb(pos)
                # Check if playback ended naturally
                if _PYGAME_AVAILABLE:
                    try:
                        if not pygame.mixer.music.get_busy():
                            self._playing = False
                            self._position = 0.0
                            self._position_cb(0.0)
                            break
                    except Exception:
                        pass
