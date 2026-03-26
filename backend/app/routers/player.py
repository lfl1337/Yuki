"""Player router — audio playback control + SSE position stream."""

import asyncio
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from ..schemas import PlayerLoadRequest, PlayerSeekRequest, PlayerVolumeRequest, PlayerStatus
from ..services import player as player_svc
from ..services.player_engine import AudioPlayer

logger = logging.getLogger("yuki.routers.player")
router = APIRouter(prefix="/player", tags=["player"])

_ALLOWED_AUDIO_EXTENSIONS = frozenset({
    ".mp3", ".flac", ".wav", ".ogg", ".aac", ".m4a", ".opus",
    ".wma", ".mp4", ".mkv", ".avi", ".mov", ".webm",
})

_FORBIDDEN_PATH_PREFIXES = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
    "c:\\system volume information",
)


def _get() -> AudioPlayer:
    return player_svc.get_player()


async def _validate_audio_filepath(filepath: str) -> str:
    """
    Sanitize and validate a user-supplied file path.

    Returns the normalized absolute path as a plain string.
    All callers MUST use this return value — never the original user input.

    Sanitization: normpath+abspath (pure-string, no filesystem), extension
    allowlist, forbidden-dir blocklist — all before any filesystem access.
    Filesystem checks (exists, is_file) are performed on the sanitized string.
    """
    normalized = os.path.normpath(os.path.abspath(filepath))

    _, ext = os.path.splitext(normalized)
    if ext.lower() not in _ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")

    normalized_lower = normalized.lower()
    for forbidden in _FORBIDDEN_PATH_PREFIXES:
        if normalized_lower.startswith(forbidden):
            raise HTTPException(
                status_code=403,
                detail="Access to system directories is not allowed",
            )

    p = Path(normalized)
    if not await asyncio.to_thread(p.exists):
        raise HTTPException(status_code=404, detail="File not found")
    if not await asyncio.to_thread(p.is_file):
        raise HTTPException(status_code=400, detail="Path is not a file")

    return normalized


@router.post("/load")
async def load(body: PlayerLoadRequest):
    safe = await _validate_audio_filepath(body.filepath)
    try:
        await asyncio.to_thread(_get().load, safe)
        # Warm the tag cache immediately so SSE never reads from disk
        await asyncio.to_thread(player_svc.notify_loaded, safe)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/play")
async def play():
    """Resume if paused, otherwise start from beginning."""
    p = _get()
    if p.is_paused():
        await asyncio.to_thread(p.resume)
    else:
        await asyncio.to_thread(p.play)
    return {"ok": True}


@router.post("/pause")
async def pause():
    await asyncio.to_thread(_get().pause)
    return {"ok": True}


@router.post("/stop")
async def stop():
    await asyncio.to_thread(_get().stop)
    return {"ok": True}


@router.post("/seek")
async def seek(body: PlayerSeekRequest):
    await asyncio.to_thread(_get().seek, body.position)
    return {"ok": True}


@router.post("/volume")
async def volume(body: PlayerVolumeRequest):
    await asyncio.to_thread(_get().set_volume, body.volume)
    return {"ok": True}


@router.get("/status", response_model=PlayerStatus)
async def status():
    data = await asyncio.to_thread(player_svc.get_status_dict)
    return PlayerStatus(**data)


@router.get("/stream")
async def stream(request: Request):
    """SSE: player position updates every 500ms."""
    return EventSourceResponse(player_svc.sse_generator(request))
