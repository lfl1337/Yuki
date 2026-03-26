"""Player router — audio playback control + SSE position stream."""

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from ..schemas import PlayerLoadRequest, PlayerSeekRequest, PlayerVolumeRequest, PlayerStatus
from ..services import player as player_svc
from ..services.player_engine import AudioPlayer

logger = logging.getLogger("yuki.routers.player")
router = APIRouter(prefix="/player", tags=["player"])


def _get() -> AudioPlayer:
    return player_svc.get_player()


_ALLOWED_AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".wav", ".ogg", ".aac", ".m4a", ".opus",
    ".wma", ".mp4", ".mkv", ".avi", ".mov", ".webm",
}

_FORBIDDEN_PATH_PREFIXES = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
    "c:\\system volume information",
)


async def _validate_audio_filepath(filepath: str) -> Path:
    """Resolve and validate a user-supplied file path."""
    p = Path(filepath).resolve()
    # Validate extension whitelist before any filesystem operations
    if p.suffix.lower() not in _ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="File type not allowed")
    # Reject access to system directories before touching the filesystem
    p_str = str(p).lower()
    for forbidden in _FORBIDDEN_PATH_PREFIXES:
        if p_str.startswith(forbidden):
            raise HTTPException(status_code=403, detail="Access to system directories is not allowed")
    exists = await asyncio.to_thread(p.exists)
    if not exists:
        raise HTTPException(status_code=404, detail="File not found")
    is_file = await asyncio.to_thread(p.is_file)
    if not is_file:
        raise HTTPException(status_code=400, detail="Path is not a file")
    return p


@router.post("/load")
async def load(body: PlayerLoadRequest):
    await _validate_audio_filepath(body.filepath)
    try:
        await asyncio.to_thread(_get().load, body.filepath)
        # Warm the tag cache immediately so SSE never reads from disk
        await asyncio.to_thread(player_svc.notify_loaded, body.filepath)
        return {"ok": True}
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
