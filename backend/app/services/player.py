"""
Player service — thin async wrapper around AudioPlayer (pygame.mixer).
AudioPlayer lives in player_engine.py (ported verbatim from legacy core/player.py).
All pygame calls are fast synchronous ops; we wrap with asyncio.to_thread() at
the router level to avoid blocking the event loop.
"""

import asyncio
import base64
import io
import logging
import threading
from pathlib import Path
from typing import Optional

from .player_engine import AudioPlayer
from .tagger import MP3Tagger

logger = logging.getLogger("yuki.player")

_player: Optional[AudioPlayer] = None
_tagger = MP3Tagger()

# Tag cache — populated once when a file is loaded, cleared when filepath changes.
# Avoids re-reading tags from disk on every 500ms SSE tick.
_tag_cache: dict = {
    "filepath": "",
    "title": "",
    "artist": "",
    "cover_b64": None,
}
_cache_lock = threading.Lock()


def get_player() -> AudioPlayer:
    global _player
    if _player is None:
        _player = AudioPlayer()
    return _player


def _refresh_tag_cache(filepath_str: str) -> None:
    """Read tags + cover art from disk and store in module-level cache.
    Only called when the loaded filepath actually changes."""
    global _tag_cache
    fp = Path(filepath_str)
    title = ""
    artist = ""
    cover_b64: Optional[str] = None

    try:
        tags = _tagger.read_tags(filepath_str)
        title = tags.get("title", "") or fp.stem
        artist = tags.get("artist", "")
    except Exception:
        title = fp.stem

    try:
        img = _tagger.get_cover_art(filepath_str)
        if img:
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=85)
            cover_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        pass

    with _cache_lock:
        _tag_cache = {
            "filepath": filepath_str,
            "title": title,
            "artist": artist,
            "cover_b64": cover_b64,
        }
    logger.debug("Tag cache refreshed for: %s", fp.name)


def notify_loaded(filepath_str: str) -> None:
    """Called by the player router after a successful /load to warm the cache."""
    if filepath_str and Path(filepath_str).exists():
        _refresh_tag_cache(filepath_str)


def get_status_dict() -> dict:
    """Return current player state as a plain dict (called from SSE generator).
    Tags are served from cache — never re-read from disk here."""
    p = get_player()
    fp = p.get_filepath()
    filepath_str = str(fp) if fp else ""

    # If filepath changed (e.g. external load), refresh cache once
    with _cache_lock:
        cached_filepath = _tag_cache["filepath"]
    if filepath_str and filepath_str != cached_filepath:
        _refresh_tag_cache(filepath_str)

    with _cache_lock:
        title = _tag_cache["title"] if filepath_str else ""
        artist = _tag_cache["artist"] if filepath_str else ""
        cover_b64 = _tag_cache["cover_b64"] if filepath_str else None

    return {
        "is_playing": p.is_playing(),
        "is_paused": p.is_paused(),
        "position": p.get_position(),
        "duration": p.get_duration(),
        "volume": p._volume,
        "filepath": filepath_str,
        "title": title,
        "artist": artist,
        "cover_art_b64": cover_b64,
    }


async def sse_generator(request):
    """Async generator that yields player status every 500ms for SSE."""
    while True:
        if await request.is_disconnected():
            break
        try:
            status = await asyncio.to_thread(get_status_dict)
            import json
            yield {"data": json.dumps(status)}
        except Exception as exc:
            logger.debug("Player SSE error: %s", exc)
        await asyncio.sleep(0.5)
