"""
Yuki — Universal Media Downloader & MP3 Suite
Global configuration, constants, and paths.
"""

from pathlib import Path

APP_NAME = "Yuki"
VERSION = "1.0.0"
GITHUB_REPO = "lfl1337/Yuki"
GITHUB_URL = f"https://github.com/{GITHUB_REPO}"

BASE_DIR = Path(__file__).parent
FFMPEG_PATH = BASE_DIR / "ffmpeg" / "ffmpeg.exe"
FFPROBE_PATH = BASE_DIR / "ffmpeg" / "ffprobe.exe"
ASSETS_DIR = BASE_DIR / "assets"
LOCALES_DIR = BASE_DIR / "locales"
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "yuki.log"
HISTORY_FILE = DATA_DIR / "history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "Yuki"

SUPPORTED_PLATFORMS = [
    "YouTube",
    "YouTube Playlist",
    "YouTube Shorts",
    "Instagram",
    "TikTok",
    "Twitter/X",
    "SoundCloud",
    "Spotify",
    "Facebook",
    "Vimeo",
    "Dailymotion",
    "Twitch",
    "Reddit",
]

QUALITY_OPTIONS_VIDEO = ["best", "1080p", "720p", "480p", "360p"]
QUALITY_OPTIONS_AUDIO = ["best", "320kbps", "192kbps", "128kbps"]

THEMES = ["dark", "light", "system"]

LANGUAGES = {
    "en": "English",
    "de": "Deutsch",
    "tr": "Türkçe",
    "ja": "日本語",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
}

MAX_CONCURRENT_DOWNLOADS = 3
MAX_HISTORY_ENTRIES = 1000
PLAYER_UPDATE_INTERVAL_MS = 500
URL_DEBOUNCE_MS = 500
THUMBNAIL_SIZE = (150, 150)
COVER_ART_SIZE = (300, 300)
PLAYER_COVER_SIZE = (50, 50)
QUEUE_THUMB_SIZE = (60, 60)

DEFAULT_SETTINGS = {
    "theme": "dark",
    "language": "en",
    "default_download_dir": str(DEFAULT_DOWNLOAD_DIR),
    "ask_folder_each_time": False,
    "autostart": False,
    "auto_update_ytdlp": True,
    "default_video_quality": "best",
    "default_audio_quality": "320kbps",
    "default_format": "audio",
    "window_width": 1100,
    "window_height": 700,
    "volume": 0.8,
}

# Video format string for yt-dlp
FORMAT_VIDEO = {
    "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]",
    "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
    "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]",
    "360p": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]",
}

# Audio bitrate for yt-dlp postprocessor
AUDIO_QUALITY_MAP = {
    "best": "0",
    "320kbps": "320",
    "192kbps": "192",
    "128kbps": "128",
}
