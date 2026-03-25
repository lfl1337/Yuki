"""
Yuki backend configuration.
Reads from YUKI_DATA_DIR env var (set by run.py before import).
"""

import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> str:
    appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return str(Path(appdata) / "Yuki")


def _resolve_ffmpeg() -> str:
    """Resolve ffmpeg.exe — works in PyInstaller bundle and dev mode."""
    if getattr(sys, "frozen", False):
        # PyInstaller --onefile: bundled files are extracted to sys._MEIPASS
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        # dev: project root is 3 levels above this file (backend/app/config.py)
        base = Path(__file__).parent.parent.parent
    return str(base / "ffmpeg" / "ffmpeg.exe")


def _resolve_ffprobe() -> str:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent.parent.parent
    return str(base / "ffmpeg" / "ffprobe.exe")


class Settings(BaseSettings):
    port: int = 9001
    data_dir: str = ""
    db_url: str = ""
    ffmpeg_path: str = ""
    ffprobe_path: str = ""
    max_concurrent_downloads: int = 3
    max_concurrent_conversions: int = 2

    model_config = SettingsConfigDict(
        env_prefix="YUKI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:
        if not self.data_dir:
            self.data_dir = os.getenv("YUKI_DATA_DIR") or _default_data_dir()
        if not self.db_url:
            self.db_url = f"sqlite+aiosqlite:///{self.data_dir}/yuki.db"
        if not self.ffmpeg_path:
            self.ffmpeg_path = _resolve_ffmpeg()
        if not self.ffprobe_path:
            self.ffprobe_path = _resolve_ffprobe()


settings = Settings()

# Player monitor interval in milliseconds
PLAYER_UPDATE_INTERVAL_MS: int = 500
