"""
URL platform detection — identifies the source platform and media type
from a given URL string.
"""

import re
from urllib.parse import urlparse


PLATFORM_PATTERNS = [
    # YouTube Shorts
    (r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+", "YouTube Shorts", "short"),
    # YouTube Playlist
    (r"(?:https?://)?(?:www\.)?youtube\.com/(?:playlist|watch)\?.*list=[\w-]+", "YouTube Playlist", "playlist"),
    # YouTube watch / youtu.be
    (r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=[\w-]+", "YouTube", "video"),
    (r"(?:https?://)?youtu\.be/[\w-]+", "YouTube", "video"),
    # YouTube channel/user (treat as playlist)
    (r"(?:https?://)?(?:www\.)?youtube\.com/@[\w.-]+(?:/videos)?", "YouTube Playlist", "playlist"),
    # Instagram reel
    (r"(?:https?://)?(?:www\.)?instagram\.com/reel/[\w-]+", "Instagram", "reel"),
    # Instagram post/story
    (r"(?:https?://)?(?:www\.)?instagram\.com/p/[\w-]+", "Instagram", "video"),
    (r"(?:https?://)?(?:www\.)?instagram\.com/stories/[\w.-]+/\d+", "Instagram", "reel"),
    # TikTok
    (r"(?:https?://)?(?:www\.)?tiktok\.com/@[\w.-]+/video/\d+", "TikTok", "short"),
    (r"(?:https?://)?vm\.tiktok\.com/[\w-]+", "TikTok", "short"),
    # Twitter / X
    (r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/\w+/status/\d+", "Twitter/X", "tweet"),
    # SoundCloud
    (r"(?:https?://)?(?:www\.)?soundcloud\.com/[\w-]+/[\w-]+", "SoundCloud", "audio"),
    (r"(?:https?://)?(?:www\.)?soundcloud\.com/[\w-]+/sets/[\w-]+", "SoundCloud", "playlist"),
    # Spotify track
    (r"(?:https?://)?open\.spotify\.com/track/[\w-]+", "Spotify", "audio"),
    # Spotify album
    (r"(?:https?://)?open\.spotify\.com/album/[\w-]+", "Spotify", "playlist"),
    # Spotify playlist
    (r"(?:https?://)?open\.spotify\.com/playlist/[\w-]+", "Spotify", "playlist"),
    # Facebook
    (r"(?:https?://)?(?:www\.)?facebook\.com/.+/videos/\d+", "Facebook", "video"),
    (r"(?:https?://)?(?:www\.)?fb\.watch/[\w-]+", "Facebook", "video"),
    # Vimeo
    (r"(?:https?://)?(?:www\.)?vimeo\.com/\d+", "Vimeo", "video"),
    # Dailymotion
    (r"(?:https?://)?(?:www\.)?dailymotion\.com/video/[\w-]+", "Dailymotion", "video"),
    # Twitch clips
    (r"(?:https?://)?(?:www\.)?twitch\.tv/\w+/clip/[\w-]+", "Twitch", "video"),
    (r"(?:https?://)?clips\.twitch\.tv/[\w-]+", "Twitch", "video"),
    # Reddit video
    (r"(?:https?://)?(?:www\.)?reddit\.com/r/\w+/comments/[\w-]+", "Reddit", "video"),
    (r"(?:https?://)?v\.redd\.it/[\w-]+", "Reddit", "video"),
]


def _is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url.strip())
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


def detect_platform(url: str) -> dict:
    """
    Detect the platform and media type from a URL.

    Returns:
        dict with keys:
            - platform (str): Platform name or "Unknown"
            - type (str): "video", "audio", "playlist", "reel", "short", "tweet"
            - valid (bool): Whether the URL is usable
            - url (str): Cleaned URL
    """
    url = url.strip()

    if not _is_valid_url(url):
        return {"platform": "Unknown", "type": "video", "valid": False, "url": url}

    for pattern, platform, media_type in PLATFORM_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return {
                "platform": platform,
                "type": media_type,
                "valid": True,
                "url": url,
            }

    # Unknown but valid URL — let yt-dlp try
    return {
        "platform": "Unknown",
        "type": "video",
        "valid": True,
        "url": url,
    }
